"""Razorpay webhook: receive -> verify signature -> deduplicate -> validate state
transition -> update DB -> audit (payment-security.md #5, exact sequence)."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.envelope import ok
from app.domains.payments.exceptions import PaymentNotFound
from app.domains.payments.service import PaymentService
from app.integrations.razorpay.base import RazorpayClient
from app.integrations.razorpay.factory import get_razorpay_client
from app.webhooks.models import WebhookEvent

_log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    body = await request.body()
    razorpay_client: RazorpayClient = get_razorpay_client()

    signature_valid = razorpay_client.verify_webhook_signature(
        body=body, signature=x_razorpay_signature
    )

    payload = await request.json()
    provider_event_id = payload.get("id") or payload.get("event_id", "")
    event_type = payload.get("event", "unknown")

    if not signature_valid:
        _log.warning(
            "razorpay webhook signature INVALID (event=%s, id=%s, sig_prefix=%s). "
            "Check RAZORPAY_WEBHOOK_SECRET matches the dashboard webhook secret.",
            event_type,
            provider_event_id,
            (x_razorpay_signature or "")[:8],
        )

    async with session.begin():
        existing = await session.scalar(
            select(WebhookEvent).where(
                WebhookEvent.provider == "razorpay",
                WebhookEvent.provider_event_id == provider_event_id,
            )
        )
        if existing is not None:
            # Duplicate delivery — Razorpay retries webhooks; never reprocess
            # (payment-security.md #6).
            return ok({"status": "duplicate_ignored"})

        event = WebhookEvent(
            provider="razorpay",
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
            signature_verified=signature_valid,
            processing_status="received",
        )
        session.add(event)
        await session.flush()

        if not signature_valid:
            event.processing_status = "error"
            await session.flush()
            return ok({"status": "signature_invalid"})

        payment_service = PaymentService(session, razorpay_client)
        entities = payload.get("payload", {})
        payment_entity = entities.get("payment", {}).get("entity", {})
        link_entity = entities.get("payment_link", {}).get("entity", {})
        order_entity = entities.get("order", {}).get("entity", {})

        # notes ride on whichever entity carries them; the payment-link path stamps
        # our own payment id there because the link runs its own internal order.
        notes = (
            payment_entity.get("notes")
            or link_entity.get("notes")
            or order_entity.get("notes")
            or {}
        )
        co_payment_id = notes.get("co_payment_id") if isinstance(notes, dict) else None
        provider_order_id = payment_entity.get("order_id") or order_entity.get("id")

        paid_events = {"payment.captured", "order.paid", "payment_link.paid"}
        outcome = "ignored"
        try:
            if event_type in paid_events:
                if co_payment_id:
                    await payment_service.confirm_captured_by_payment_id(
                        payment_id=UUID(str(co_payment_id))
                    )
                    outcome = "settled_by_payment_id"
                elif provider_order_id:
                    await payment_service.confirm_captured(provider_order_id=provider_order_id)
                    outcome = "settled_by_order_id"
                else:
                    outcome = "no_match_key"
            elif event_type == "payment.failed" and provider_order_id:
                reason = payment_entity.get("error_description", "payment_failed")
                await payment_service.confirm_failed(
                    provider_order_id=provider_order_id, reason=reason
                )
                outcome = "marked_failed"
        except PaymentNotFound:
            # e.g. a payment.captured for a payment link's internal order that we
            # never track — the matching payment_link.paid event settles it instead.
            outcome = "payment_not_found"

        event.processing_status = "processed"
        event.processed_at = datetime.now(UTC)
        await session.flush()

    _log.info(
        "razorpay webhook: event=%s id=%s sig_ok=%s co_payment_id=%s order_id=%s -> %s",
        event_type,
        provider_event_id,
        signature_valid,
        co_payment_id,
        provider_order_id,
        outcome,
    )
    return ok({"status": "processed", "outcome": outcome})
