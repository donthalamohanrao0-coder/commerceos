import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_merchant_id, get_session
from app.api.envelope import ok
from app.domains.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


class CreateOrderRequest(BaseModel):
    cart_id: uuid.UUID


@router.post("")
async def create_order(
    body: CreateOrderRequest,
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    async with session.begin():
        order = await OrderService(session).create_order_from_cart(
            merchant_id,
            body.cart_id,
            agent_session_id=None,
            actor_type="customer",
            actor_id=None,
        )
    return ok(
        {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "subtotal_paise": order.subtotal_paise,
            "discount_paise": order.discount_paise,
            "shipping_paise": order.shipping_paise,
            "total_paise": order.total_paise,
        }
    )


@router.get("/{order_id}")
async def get_order(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    order = await OrderService(session).get_order(merchant_id, order_id)
    return ok(
        {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "total_paise": order.total_paise,
        }
    )
