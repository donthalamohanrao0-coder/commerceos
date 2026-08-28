"""Deterministic pricing + inventory reservation against the live schema."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cart.service import CartService
from app.domains.catalog.inventory_service import InventoryService
from app.domains.orders.service import (
    FREE_SHIPPING_THRESHOLD_PAISE,
    STANDARD_SHIPPING_PAISE,
    OrderService,
)

pytestmark = pytest.mark.asyncio


async def test_quote_matches_created_order_and_applies_shipping_rule(
    db: AsyncSession, merchant, cheap_product
) -> None:
    carts = CartService(db)
    cart = await carts.create_fresh_cart(merchant.id)
    await carts.add_item(merchant.id, cart.id, product_id=cheap_product.id, quantity=1)

    quote = await OrderService(db).quote_cart(merchant.id, cart.id)
    # cheap product is well under the free-shipping threshold
    assert quote.subtotal_paise == cheap_product.price_paise
    assert quote.subtotal_paise < FREE_SHIPPING_THRESHOLD_PAISE
    assert quote.shipping_paise == STANDARD_SHIPPING_PAISE
    assert (
        quote.total_paise == quote.subtotal_paise - quote.discount_paise + STANDARD_SHIPPING_PAISE
    )

    order = await OrderService(db).create_order_from_cart(
        merchant.id, cart.id, agent_session_id=None, actor_type="customer", actor_id=None
    )
    assert (order.subtotal_paise, order.shipping_paise, order.total_paise) == (
        quote.subtotal_paise,
        quote.shipping_paise,
        quote.total_paise,
    )
    assert order.status == "created"


async def test_order_reserves_inventory(db: AsyncSession, merchant, cheap_product) -> None:
    inv = InventoryService(db)
    variant = await CartService(db)._catalog.get_default_variant(merchant.id, cheap_product.id)
    before = await inv.check_available(merchant.id, variant.id, 1)
    assert before is True

    carts = CartService(db)
    cart = await carts.create_fresh_cart(merchant.id)
    await carts.add_item(merchant.id, cart.id, product_id=cheap_product.id, quantity=2)
    await OrderService(db).create_order_from_cart(
        merchant.id, cart.id, agent_session_id=None, actor_type="customer", actor_id=None
    )

    from sqlalchemy import select

    from app.domains.catalog.models import Inventory

    row = await db.scalar(select(Inventory).where(Inventory.product_variant_id == variant.id))
    assert row is not None and row.quantity_reserved >= 2
