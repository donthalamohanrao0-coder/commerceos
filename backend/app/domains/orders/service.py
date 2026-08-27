"""Order creation — re-fetches authoritative prices/inventory at order time (never
trusts the cart snapshot as final), computes subtotal/discount/shipping/tax/total
server-side (system-architecture.md trust boundary #6, security-architecture.md #4).
"""

import uuid

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

    async def create_order_from_cart(
        self,
        merchant_id: uuid.UUID,
        cart_id: uuid.UUID,
        *,
        agent_session_id: uuid.UUID | None,
        actor_type: ActorType,
        actor_id: str | None,
    ) -> Order:
        cart = await self._session.get(Cart, cart_id)
        if cart is None or cart.merchant_id != merchant_id:
            raise OrderNotFound(str(cart_id))

        items_result = await self._session.scalars(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )
        cart_items = list(items_result.all())
        if not cart_items:
            raise EmptyCart(str(cart_id))

        # Re-validate authoritative price + stock for every line item — never trust
        # the cart's snapshotted unit_price_paise as final.
        subtotal_paise = 0
        order_item_specs: list[tuple[ProductVariant, Product, int, int]] = []
        for item in cart_items:
            variant = await self._session.get(ProductVariant, item.product_variant_id)
            assert variant is not None, (
                f"cart item references missing variant {item.product_variant_id}"
            )
            product = await self._session.get(Product, variant.product_id)
            assert product is not None, f"variant references missing product {variant.product_id}"
            if not await self._inventory.check_available(merchant_id, variant.id, item.quantity):
                raise ValueError(f"insufficient stock for variant {variant.id}")
            line_total = variant.price_paise * item.quantity
            subtotal_paise += line_total
            order_item_specs.append((variant, product, item.quantity, variant.price_paise))

        customer_segment = None
        if cart.customer_id is not None:
            customer = await self._session.get(Customer, cart.customer_id)
            customer_segment = customer.segment if customer else None

        campaign_eval = await self._campaigns.evaluate_campaigns_for_cart(
            merchant_id,
            cart_items=cart_items,
            subtotal_paise=subtotal_paise,
            customer_segment=customer_segment,
        )
        discount_paise = campaign_eval.discount_paise

        shipping_paise = (
            0 if subtotal_paise >= FREE_SHIPPING_THRESHOLD_PAISE else STANDARD_SHIPPING_PAISE
        )
        total_paise = subtotal_paise - discount_paise + shipping_paise

        order = Order(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=cart.customer_id,
            cart_id=cart.id,
            order_number=await self._next_order_number(merchant_id),
            status="created",
            subtotal_paise=subtotal_paise,
            discount_paise=discount_paise,
            shipping_paise=shipping_paise,
            tax_paise=0,  # prices are tax-inclusive per merchant_profile.json
            total_paise=total_paise,
            campaign_id=campaign_eval.campaign.id if campaign_eval.campaign else None,
            source="ai_assisted" if agent_session_id else "customer",
            agent_session_id=agent_session_id,
        )
        self._session.add(order)
        await self._session.flush()

        for variant, product, quantity, unit_price in order_item_specs:
            self._session.add(
                OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_variant_id=variant.id,
                    product_name_snapshot=product.name,
                    quantity=quantity,
                    unit_price_paise=unit_price,
                    line_total_paise=unit_price * quantity,
                )
            )
            await self._inventory.reserve(merchant_id, variant.id, quantity)

        cart.status = "converted"
        await self._session.flush()

        await self._audit.record(
            merchant_id=merchant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            session_id=agent_session_id,
            order_id=order.id,
            action="ORDER_CREATED",
            input={"cart_id": str(cart_id)},
            result={"order_number": order.order_number, "total_paise": total_paise},
            policy_decision={"discount_reason": campaign_eval.reason},
        )

        return order

    async def get_order(self, merchant_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        order = await self._session.get(Order, order_id)
        if order is None or order.merchant_id != merchant_id:
            raise OrderNotFound(str(order_id))
        return order
