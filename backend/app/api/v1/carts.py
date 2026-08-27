import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_merchant_id, get_session
from app.api.envelope import ok
from app.domains.cart.service import CartService

router = APIRouter(prefix="/carts", tags=["carts"])


class CreateCartRequest(BaseModel):
    customer_id: uuid.UUID | None = None


class AddItemRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = 1


@router.post("")
async def create_cart(
    body: CreateCartRequest,
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    async with session.begin():
        cart = await CartService(session).get_or_create_cart(
            merchant_id, customer_id=body.customer_id, agent_session_id=None
        )
    return ok({"cart_id": str(cart.id), "status": cart.status})


@router.post("/{cart_id}/items")
async def add_item(
    cart_id: uuid.UUID,
    body: AddItemRequest,
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    async with session.begin():
        item = await CartService(session).add_item(
            merchant_id, cart_id, product_id=body.product_id, quantity=body.quantity
        )
    return ok(
        {
            "item_id": str(item.id),
            "product_variant_id": str(item.product_variant_id),
            "quantity": item.quantity,
            "unit_price_paise": item.unit_price_paise,
        }
    )


@router.get("/{cart_id}")
async def get_cart_totals(
    cart_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    service = CartService(session)
    await service.get_cart(merchant_id, cart_id)  # tenant ownership check
    totals = await service.get_totals(cart_id)
    return ok({"subtotal_paise": totals.subtotal_paise, "item_count": totals.item_count})
