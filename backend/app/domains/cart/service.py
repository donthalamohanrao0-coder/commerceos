"""Cart service. Prices are snapshotted at add-time but always re-validated at
checkout by orders.service (never trusts a stale cart snapshot as authoritative)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cart.exceptions import CartItemNotFound, CartNotFound
from app.domains.cart.models import Cart, CartItem
from app.domains.catalog.inventory_service import InsufficientStock, InventoryService
from app.domains.catalog.service import CatalogService


@dataclass(frozen=True)
class CartTotals:
    subtotal_paise: int
    item_count: int


class CartService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._catalog = CatalogService(session)
        self._inventory = InventoryService(session)

    async def get_or_create_cart(
        self,
        merchant_id: uuid.UUID,
        *,
        customer_id: uuid.UUID | None,
        agent_session_id: uuid.UUID | None,
    ) -> Cart:
        stmt = select(Cart).where(Cart.merchant_id == merchant_id, Cart.status == "active")
        if agent_session_id is not None:
            stmt = stmt.where(Cart.agent_session_id == agent_session_id)
        elif customer_id is not None:
            stmt = stmt.where(Cart.customer_id == customer_id)

        existing = await self._session.scalar(stmt)
        if existing is not None:
            return existing

        cart = Cart(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer_id,
            agent_session_id=agent_session_id,
        )
        self._session.add(cart)
        await self._session.flush()
        return cart

    async def create_fresh_cart(
        self, merchant_id: uuid.UUID, *, customer_id: uuid.UUID | None = None
    ) -> Cart:
        """Always a new cart. Used for stateless flows (external AI buyers) where
        reusing a lingering anonymous active cart would leak items between requests."""
        cart = Cart(id=uuid.uuid4(), merchant_id=merchant_id, customer_id=customer_id)
        self._session.add(cart)
        await self._session.flush()
        return cart

    async def get_cart(self, merchant_id: uuid.UUID, cart_id: uuid.UUID) -> Cart:
        cart = await self._session.scalar(
            select(Cart).where(Cart.id == cart_id, Cart.merchant_id == merchant_id)
        )
        if cart is None:
            raise CartNotFound(str(cart_id))
        return cart

    async def add_item(
        self,
        merchant_id: uuid.UUID,
        cart_id: uuid.UUID,
        *,
        product_id: uuid.UUID,
        quantity: int,
        added_reason: str = "customer_request",
    ) -> CartItem:
        cart = await self.get_cart(merchant_id, cart_id)
        variant = await self._catalog.get_default_variant(merchant_id, product_id)

        if not await self._inventory.check_available(merchant_id, variant.id, quantity):
            raise InsufficientStock(str(variant.id))

        existing_item = await self._session.scalar(
            select(CartItem).where(
                CartItem.cart_id == cart.id, CartItem.product_variant_id == variant.id
            )
        )
        if existing_item is not None:
            existing_item.quantity += quantity
            await self._session.flush()
            return existing_item

        item = CartItem(
            id=uuid.uuid4(),
            cart_id=cart.id,
            product_variant_id=variant.id,
            quantity=quantity,
            unit_price_paise=variant.price_paise,
            added_reason=added_reason,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def remove_item(
        self, merchant_id: uuid.UUID, cart_id: uuid.UUID, item_id: uuid.UUID
    ) -> None:
        await self.get_cart(merchant_id, cart_id)  # tenant ownership check
        item = await self._session.get(CartItem, item_id)
        if item is None or item.cart_id != cart_id:
            raise CartItemNotFound(str(item_id))
        await self._session.delete(item)
        await self._session.flush()

    async def get_items(self, cart_id: uuid.UUID) -> list[CartItem]:
        result = await self._session.scalars(select(CartItem).where(CartItem.cart_id == cart_id))
        return list(result.all())

    async def get_totals(self, cart_id: uuid.UUID) -> CartTotals:
        items = await self.get_items(cart_id)
        subtotal = sum(item.unit_price_paise * item.quantity for item in items)
        return CartTotals(subtotal_paise=subtotal, item_count=sum(i.quantity for i in items))
