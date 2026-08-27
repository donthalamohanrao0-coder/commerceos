"""Payment creation + webhook confirmation (ADR-005, payment-security.md).

No payment executes solely from inferred natural-language intent: this service
requires an authoritative server-side order, a policy pass, and — enforced one layer
up by the approvals module — explicit customer confirmation before it is even called.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import ActorType, AuditService
from app.core.idempotency import with_idempotency
from app.domains.orders.models import Order
from app.domains.payments.exceptions import PaymentNotFound, PaymentPolicyDenied
from app.domains.payments.models import Payment
from app.domains.payments.state_machine import transition
from app.integrations.razorpay.base import RazorpayClient
from app.integrations.razorpay.factory import get_razorpay_client
from app.policies.engine import PolicyEngine


class PaymentService:
    def __init__(
        self, session: AsyncSession, razorpay_client: RazorpayClient | None = None
    ) -> None:
        self._session = session
        self._razorpay = razorpay_client or get_razorpay_client()
        self._policy_engine = PolicyEngine(session)
        self._audit = AuditService(session)

    async def create_payment_intent(
        self,
        merchant_id: uuid.UUID,
        order_id: uuid.UUID,
        *,
        idempotency_key: str,
        agent_session_id: uuid.UUID | None,
        actor_type: ActorType,
        actor_id: str | None,
    ) -> dict[str, object]:
        """Returns a JSON-serializable dict (not the ORM Payment) because the
        response must be cacheable verbatim by with_idempotency for replay on a
        duplicate request. Use get_payment() for the ORM row."""
        order = await self._session.get(Order, order_id)
        if order is None or order.merchant_id != merchant_id:
            raise PaymentNotFound(str(order_id))

        policy_decision = await self._policy_engine.check_transaction_amount(
            merchant_id, order.total_paise
        )
        if not policy_decision.allowed:
            await self._audit.record(
                merchant_id=merchant_id,
                actor_type=actor_type,
                actor_id=actor_id,
                session_id=agent_session_id,
                order_id=order.id,
                action="PAYMENT_FAILED",
                input={"reason": "policy_denied"},
                policy_decision={"allowed": False, "reason": policy_decision.reason},
            )
            raise PaymentPolicyDenied(policy_decision.reason)

        async def _execute() -> dict[str, object]:
            existing = await self._session.scalar(
                select(Payment).where(Payment.order_id == order.id)
            )
            payment = existing or Payment(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                order_id=order.id,
                amount_paise=order.total_paise,
            )
            if existing is None:
                self._session.add(payment)
                await self._session.flush()

            razorpay_order = self._razorpay.create_order(
                amount_paise=order.total_paise,
                receipt=order.order_number,
                notes={"merchant_id": str(merchant_id), "order_id": str(order.id)},
            )
            payment.provider_order_id = razorpay_order.provider_order_id
            transition(payment, "pending")
            await self._session.flush()

            await self._audit.record(
                merchant_id=merchant_id,
                actor_type=actor_type,
                actor_id=actor_id,
                session_id=agent_session_id,
                order_id=order.id,
                action="PAYMENT_CREATED",
                result={
                    "payment_id": str(payment.id),
                    "provider_order_id": payment.provider_order_id,
                },
                policy_decision={"allowed": True, "reason": policy_decision.reason},
            )

            return {
                "payment_id": str(payment.id),
                "provider_order_id": payment.provider_order_id,
                "amount_paise": payment.amount_paise,
                "currency": payment.currency,
            }

        return await with_idempotency(
            self._session,
            merchant_id=merchant_id,
            operation="create_payment",
            idempotency_key=idempotency_key,
            request_payload={"order_id": str(order_id)},
            execute=_execute,
        )

    async def get_payment(self, merchant_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
        payment = await self._session.get(Payment, payment_id)
        if payment is None or payment.merchant_id != merchant_id:
            raise PaymentNotFound(str(payment_id))
        return payment

    async def confirm_captured(self, *, provider_order_id: str) -> Payment:
        """Called by the webhook handler after signature verification + dedup."""
        payment = await self._session.scalar(
            select(Payment).where(Payment.provider_order_id == provider_order_id)
        )
        if payment is None:
            raise PaymentNotFound(provider_order_id)

        if payment.status == "paid":
            return payment  # duplicate webhook delivery — no-op (payment-security.md #6)

        transition(payment, "processing")
        transition(payment, "paid")
        payment.razorpay_signature_verified = True

        order = await self._session.get(Order, payment.order_id)
        if order is not None:
            order.status = "paid"

        await self._session.flush()

        await self._audit.record(
            merchant_id=payment.merchant_id,
            actor_type="system",
            order_id=payment.order_id,
            action="PAYMENT_SUCCEEDED",
            result={"payment_id": str(payment.id)},
        )
        return payment

    async def confirm_failed(self, *, provider_order_id: str, reason: str) -> Payment:
        payment = await self._session.scalar(
            select(Payment).where(Payment.provider_order_id == provider_order_id)
        )
        if payment is None:
            raise PaymentNotFound(provider_order_id)

        if payment.status == "failed":
            return payment  # duplicate webhook delivery — no-op (payment-security.md #6)

        transition(payment, "processing")
        transition(payment, "failed")
        payment.failure_reason = reason

        order = await self._session.get(Order, payment.order_id)
        if order is not None:
            order.status = "failed"

        await self._session.flush()

        await self._audit.record(
            merchant_id=payment.merchant_id,
            actor_type="system",
            order_id=payment.order_id,
            action="PAYMENT_FAILED",
            result={"payment_id": str(payment.id), "reason": reason},
        )
        return payment
