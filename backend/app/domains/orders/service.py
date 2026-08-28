"""Order creation — re-fetches authoritative prices/inventory at order time (never
trusts the cart snapshot as final), computes subtotal/discount/shipping/tax/total
server-side (system-architecture.md trust boundary #6, security-architecture.md #4).
"""

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import ActorType, AuditService
from app.domains.campaigns.service import CampaignService
from app.domains.cart.models import Cart, CartItem
from app.domains.catalog.inventory_service import InventoryService
from app.domains.catalog.models import Product, ProductVariant
from app.domains.customers.models import Customer
from app.domains.orders.exceptions import EmptyCart, OrderNotFound
from app.domains.orders.models import Order, OrderItem

FREE_SHIPPING_THRESHOLD_PAISE = 200_000  # 2,000 INR (business_policies.md)
STANDARD_SHIPPING_PAISE = 9_900  # 99 INR

OrderSource = Literal["customer", "ai_assisted", "external_ai_buyer"]


@dataclass(frozen=True)
class QuoteLine:
    product_id: uuid.UUID
    product_variant_id: uuid.UUID
    name: str
    quantity: int
    unit_price_paise: int
    line_total_paise: int
    in_stock: bool


@dataclass(frozen=True)
class PricingBreakdown:
    lines: list[QuoteLine]
    subtotal_paise: int
    discount_paise: int
    shipping_paise: int
    tax_paise: int
    total_paise: int
    campaign_name: str | None
    campaign_id: uuid.UUID | None
    discount_reason: str


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._inventory = InventoryService(session)
        self._campaigns = CampaignService(session)
        self._audit = AuditService(session)

    async def _next_order_number(self, merchant_id: uuid.UUID) -> str:
        # Random suffix rather than a sequential counter for the demo; a production
        # sequence/counter table would avoid any theoretical collision window.
        suffix = uuid.uuid4().hex[:6].upper()
        return f"ORD-{suffix}"

    async def _price(
        self,
        merchant_id: uuid.UUID,
        cart_items: list[CartItem],
        *,
        customer_segment: str | None,
    ) -> PricingBreakdown:
        """Deterministic pricing for a set of cart lines. Re-fetches the
        authoritative variant price + stock — never trusts the cart snapshot."""
        subtotal_paise = 0
        lines: list[QuoteLine] = []
        for item in cart_items:
            variant = await self._session.get(ProductVariant, item.product_variant_id)
            assert variant is not None, (
                f"cart item references missing variant {item.product_variant_id}"
            )
            product = await self._session.get(Product, variant.product_id)
            assert product is not None, f"variant references missing product {variant.product_id}"
            in_stock = await self._inventory.check_available(merchant_id, variant.id, item.quantity)
            line_total = variant.price_paise * item.quantity
            subtotal_paise += line_total
            lines.append(
                QuoteLine(
                    product_id=product.id,
                    product_variant_id=variant.id,
                    name=product.name,
                    quantity=item.quantity,
                    unit_price_paise=variant.price_paise,
                    line_total_paise=line_total,
                    in_stock=in_stock,
                )
            )

        campaign_eval = await self._campaigns.evaluate_campaigns_for_cart(
            merchant_id,
            cart_items=cart_items,
            subtotal_paise=subtotal_paise,
            customer_segment=customer_segment,
        )
        shipping_paise = (
            0 if subtotal_paise >= FREE_SHIPPING_THRESHOLD_PAISE else STANDARD_SHIPPING_PAISE
        )
        return PricingBreakdown(
            lines=lines,
            subtotal_paise=subtotal_paise,
            discount_paise=campaign_eval.discount_paise,
            shipping_paise=shipping_paise,
            tax_paise=0,  # prices are tax-inclusive per merchant_profile.json
            total_paise=subtotal_paise - campaign_eval.discount_paise + shipping_paise,
            campaign_name=campaign_eval.campaign.name if campaign_eval.campaign else None,
            campaign_id=campaign_eval.campaign.id if campaign_eval.campaign else None,
            discount_reason=campaign_eval.reason,
        )

    async def quote_cart(self, merchant_id: uuid.UUID, cart_id: uuid.UUID) -> PricingBreakdown:
        """Read-only price preview for a cart — no order, no inventory reservation."""
        cart = await self._session.get(Cart, cart_id)
        if cart is None or cart.merchant_id != merchant_id:
            raise OrderNotFound(str(cart_id))
        items = list(
            await self._session.scalars(select(CartItem).where(CartItem.cart_id == cart.id))
        )
        if not items:
            raise EmptyCart(str(cart_id))
        segment = None
        if cart.customer_id is not None:
            customer = await self._session.get(Customer, cart.customer_id)
            segment = customer.segment if customer else None
        return await self._price(merchant_id, items, customer_segment=segment)

    async def create_order_from_cart(
        self,
        merchant_id: uuid.UUID,
        cart_id: uuid.UUID,
        *,
        agent_session_id: uuid.UUID | None,
        actor_type: ActorType,
        actor_id: str | None,
        source: OrderSource | None = None,
        buyer_ref: str | None = None,
    ) -> Order:
        cart = await self._session.get(Cart, cart_id)
        if cart is None or cart.merchant_id != merchant_id:
            raise OrderNotFound(str(cart_id))

        cart_items = list(
            await self._session.scalars(select(CartItem).where(CartItem.cart_id == cart.id))
        )
        if not cart_items:
            raise EmptyCart(str(cart_id))

        segment = None
        if cart.customer_id is not None:
            customer = await self._session.get(Customer, cart.customer_id)
            segment = customer.segment if customer else None

        pricing = await self._price(merchant_id, cart_items, customer_segment=segment)
        out_of_stock = [ln for ln in pricing.lines if not ln.in_stock]
        if out_of_stock:
            raise ValueError(f"insufficient stock for variant {out_of_stock[0].product_variant_id}")

        resolved_source: OrderSource = source or ("ai_assisted" if agent_session_id else "customer")
        order = Order(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=cart.customer_id,
            cart_id=cart.id,
            order_number=await self._next_order_number(merchant_id),
            status="created",
            subtotal_paise=pricing.subtotal_paise,
            discount_paise=pricing.discount_paise,
            shipping_paise=pricing.shipping_paise,
            tax_paise=pricing.tax_paise,
            total_paise=pricing.total_paise,
            campaign_id=pricing.campaign_id,
            source=resolved_source,
            agent_session_id=agent_session_id,
        )
        self._session.add(order)
        await self._session.flush()

        for line in pricing.lines:
            self._session.add(
                OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_variant_id=line.product_variant_id,
                    product_name_snapshot=line.name,
                    quantity=line.quantity,
                    unit_price_paise=line.unit_price_paise,
                    line_total_paise=line.line_total_paise,
                )
            )
            await self._inventory.reserve(merchant_id, line.product_variant_id, line.quantity)

        cart.status = "converted"
        await self._session.flush()

        await self._audit.record(
            merchant_id=merchant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            session_id=agent_session_id,
            order_id=order.id,
            action="ORDER_CREATED",
            input={
                "cart_id": str(cart_id),
                "source": resolved_source,
                **({"buyer_ref": buyer_ref} if buyer_ref else {}),
            },
            result={"order_number": order.order_number, "total_paise": pricing.total_paise},
            policy_decision={"discount_reason": pricing.discount_reason},
        )
        return order

    async def get_order(self, merchant_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        order = await self._session.get(Order, order_id)
        if order is None or order.merchant_id != merchant_id:
            raise OrderNotFound(str(order_id))
        return order
