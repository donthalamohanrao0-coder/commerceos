import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_merchant_id, get_tenant_session
from app.api.envelope import ok
from app.core.config import get_settings
from app.domains.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

_SESSION = Depends(get_tenant_session)
_MERCHANT = Depends(get_current_merchant_id)


class CreatePaymentRequest(BaseModel):
    order_id: uuid.UUID


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


@router.get("/razorpay-config")
async def razorpay_config() -> dict:
    """Public Razorpay Checkout config for the browser. Only the *publishable*
    key id is exposed — the secret never leaves the backend."""
    settings = get_settings()
    return ok({"key_id": settings.razorpay_key_id or "", "enabled": bool(settings.razorpay_key_id)})


@router.post("")
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    async with session.begin():
        result = await PaymentService(session).create_payment_intent(
            merchant_id,
            body.order_id,
            idempotency_key=idempotency_key,
            agent_session_id=None,
            actor_type="customer",
            actor_id=None,
        )
    return ok(result)


@router.post("/{payment_id}/verify")
async def verify_payment(
    payment_id: uuid.UUID,
    body: VerifyPaymentRequest,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    """Called after Razorpay Checkout succeeds in the browser. Verifies the
    signature server-side, then captures (same path a webhook would take)."""
    async with session.begin():
        result = await PaymentService(session).verify_and_capture(
            merchant_id,
            payment_id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_order_id=body.razorpay_order_id,
            razorpay_signature=body.razorpay_signature,
        )
    return ok(result)


@router.get("/{payment_id}")
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    payment = await PaymentService(session).get_payment(merchant_id, payment_id)
    return ok(
        {
            "payment_id": str(payment.id),
            "status": payment.status,
            "amount_paise": payment.amount_paise,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
        }
    )
