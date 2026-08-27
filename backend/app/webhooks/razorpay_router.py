"""Razorpay webhook: receive -> verify signature -> deduplicate -> validate state
transition -> update DB -> audit (payment-security.md #5, exact sequence)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.envelope import ok
from app.domains.payments.service import PaymentService
from app.integrations.razorpay.base import RazorpayClient
from app.integrations.razorpay.factory import get_razorpay_client
from app.webhooks.models import WebhookEvent

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
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        provider_order_id = entity.get("order_id")

        if provider_order_id:
            if event_type == "payment.captured":
                await payment_service.confirm_captured(provider_order_id=provider_order_id)
            elif event_type == "payment.failed":
                reason = entity.get("error_description", "payment_failed")
                await payment_service.confirm_failed(
                    provider_order_id=provider_order_id, reason=reason
                )

        event.processing_status = "processed"
        event.processed_at = datetime.now(UTC)
        await session.flush()

    return ok({"status": "processed"})
