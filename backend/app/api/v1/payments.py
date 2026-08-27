import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_merchant_id, get_session
from app.api.envelope import ok
from app.domains.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


class CreatePaymentRequest(BaseModel):
    order_id: uuid.UUID


@router.post("")
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
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


@router.get("/{payment_id}")
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    payment = await PaymentService(session).get_payment(merchant_id, payment_id)
    return ok(
        {
            "payment_id": str(payment.id),
            "status": payment.status,
            "amount_paise": payment.amount_paise,
            "provider_order_id": payment.provider_order_id,
        }
    )
