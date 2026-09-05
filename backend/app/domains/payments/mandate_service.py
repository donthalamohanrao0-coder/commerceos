"""MandateService — the lifecycle of a buyer's standing spending mandate.

A human authorises a ceiling + expiry once (Razorpay UPI AutoPay `as_presented`
variable mandate / card / e-mandate token); afterwards an external AI buyer's
confirmed payment call charges within it with no per-purchase checkout hand-off.

  create()  -> pending_authorization + a one-time authorization_url
  activate() -> active (from the hosted approval callback or a token.confirmed webhook)
  cancel()   -> cancelled (from a token.cancelled/rejected webhook or a merchant action)
  find_chargeable() -> the active, unexpired, ceiling-covering mandate for an order
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.domains.customers.models import Customer
from app.domains.payments.models import PaymentMandate
from app.integrations.razorpay.base import RazorpayClient
from app.integrations.razorpay.factory import get_razorpay_client

# Razorpay UPI AutoPay: `as_presented` == variable amount, decided per debit
# (each charge must be <= the mandate's max_amount). The right shape for carts.
_FREQUENCY = "as_presented"


class MandateNotFound(Exception):
    pass


class MandateService:
    def __init__(
        self, session: AsyncSession, *, razorpay_client: RazorpayClient | None = None
    ) -> None:
        self._session = session
        self._razorpay = razorpay_client or get_razorpay_client()
        self._audit = AuditService(session)

    async def create(
        self,
        merchant_id: uuid.UUID,
        *,
        customer: Customer,
        max_amount_paise: int,
        expires_at: datetime,
        consent_reference: str,
        actor_id: str | None,
    ) -> PaymentMandate:
        provider_customer_id = self._razorpay.create_customer(
            name=customer.name,
            email=customer.email or "",
            contact=customer.phone or "",
        )
        mandate_id = uuid.uuid4()
        order = self._razorpay.create_mandate_order(
            provider_customer_id=provider_customer_id,
            max_amount_paise=max_amount_paise,
            expire_at_unix=int(expires_at.timestamp()),
            frequency=_FREQUENCY,
            notes={"co_mandate_id": str(mandate_id), "co_merchant_id": str(merchant_id)},
        )
        mandate = PaymentMandate(
            id=mandate_id,
            merchant_id=merchant_id,
            customer_id=customer.id,
            provider_customer_id=provider_customer_id,
            provider_order_id=order.provider_order_id,
            max_amount_paise=max_amount_paise,
            consent_reference=consent_reference,
            status="pending_authorization",
            expires_at=expires_at,
        )
        self._session.add(mandate)
        await self._session.flush()

        await self._audit.record(
            merchant_id=merchant_id,
            actor_type="external_agent",
            actor_id=actor_id,
            action="MANDATE_REQUESTED",
            input={
                "mandate_id": str(mandate_id),
                "max_amount_paise": max_amount_paise,
                "expires_at": expires_at.isoformat(),
                "consent_reference": consent_reference,
            },
        )
        return mandate

    async def get(self, merchant_id: uuid.UUID, mandate_id: uuid.UUID) -> PaymentMandate:
        mandate = await self._session.get(PaymentMandate, mandate_id)
        if mandate is None or mandate.merchant_id != merchant_id:
            raise MandateNotFound(str(mandate_id))
        return mandate

    async def activate(
        self, mandate: PaymentMandate, *, provider_token_id: str
    ) -> PaymentMandate:
        if mandate.status == "active":
            return mandate  # idempotent: callback + webhook may both arrive
        mandate.provider_token_id = provider_token_id
        mandate.status = "active"
        mandate.authorized_at = datetime.now(UTC)
        await self._session.flush()
        await self._audit.record(
            merchant_id=mandate.merchant_id,
            actor_type="customer",
            action="MANDATE_AUTHORIZED",
            result={"mandate_id": str(mandate.id), "token_id": provider_token_id},
        )
        return mandate

    async def activate_by_provider_customer(
        self, provider_customer_id: str, *, provider_token_id: str
    ) -> PaymentMandate | None:
        """Webhook path (token.confirmed): unscoped session, matched on the
        Razorpay customer id we stored."""
        mandate = await self._session.scalar(
            select(PaymentMandate).where(
                PaymentMandate.provider_customer_id == provider_customer_id,
                PaymentMandate.status == "pending_authorization",
            )
        )
        if mandate is None:
            return None
        return await self.activate(mandate, provider_token_id=provider_token_id)

    async def cancel(self, mandate: PaymentMandate, *, reason: str) -> PaymentMandate:
        if mandate.status == "cancelled":
            return mandate
        mandate.status = "cancelled"
        mandate.cancelled_at = datetime.now(UTC)
        await self._session.flush()
        await self._audit.record(
            merchant_id=mandate.merchant_id,
            actor_type="system",
            action="MANDATE_CANCELLED",
            result={"mandate_id": str(mandate.id), "reason": reason},
        )
        return mandate

    async def cancel_by_provider_customer(
        self, provider_customer_id: str, *, reason: str
    ) -> PaymentMandate | None:
        mandate = await self._session.scalar(
            select(PaymentMandate).where(
                PaymentMandate.provider_customer_id == provider_customer_id,
                PaymentMandate.status.in_(("pending_authorization", "active")),
            )
        )
        if mandate is None:
            return None
        return await self.cancel(mandate, reason=reason)

    async def find_chargeable(
        self, merchant_id: uuid.UUID, customer_id: uuid.UUID, amount_paise: int
    ) -> PaymentMandate | None:
        """The active, unexpired mandate for this buyer whose ceiling covers the
        order. Lazily marks a lapsed mandate `expired`."""
        rows = await self._session.scalars(
            select(PaymentMandate)
            .where(
                PaymentMandate.merchant_id == merchant_id,
                PaymentMandate.customer_id == customer_id,
                PaymentMandate.status == "active",
            )
            .order_by(PaymentMandate.created_at.desc())
        )
        now = datetime.now(UTC)
        for mandate in rows:
            if mandate.expires_at <= now:
                mandate.status = "expired"
                await self._session.flush()
                continue
            if mandate.max_amount_paise >= amount_paise:
                return mandate
        return None
