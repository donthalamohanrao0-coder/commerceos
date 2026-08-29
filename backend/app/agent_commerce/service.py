"""AgentCommerceService — the deterministic operations an external AI buyer can
perform (ADR-006). Thin wrapper over the same domain services the internal API
uses; it never exposes internal endpoints and tags every mutation with
actor_type='external_agent' for the audit trail.
"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.schemas import (
    BuyerIn,
    CatalogSearchIn,
    LineItemIn,
    OrderOut,
    PaymentMandateIn,
    PaymentOut,
    ProductOut,
    QuoteLineOut,
    QuoteOut,
)
from app.audit.service import AuditService
from app.domains.cart.models import Cart
from app.domains.cart.service import CartService
from app.domains.catalog.inventory_service import InventoryService
from app.domains.catalog.models import Product
from app.domains.catalog.service import CatalogService
from app.domains.customers.models import Customer
from app.domains.orders.exceptions import OrderNotFound
from app.domains.orders.service import OrderService
from app.domains.payments.exceptions import PaymentPolicyDenied
from app.domains.payments.service import PaymentService
from app.integrations.razorpay.factory import get_razorpay_client
from app.policies.engine import PolicyEngine


class AgentOrderNotFound(Exception):
    pass


@dataclass(frozen=True)
class CatalogPage:
    products: list[ProductOut]
    next_cursor: str | None


def _encode_cursor(name: str, product_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{name}\x1f{product_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str]:
    name, pid = base64.urlsafe_b64decode(cursor.encode()).decode().split("\x1f", 1)
    return name, pid


class AgentCommerceService:
    def __init__(self, session: AsyncSession, *, actor_id: str) -> None:
        self._session = session
        self._actor_id = actor_id
        self._catalog = CatalogService(session)
        self._inventory = InventoryService(session)
        self._orders = OrderService(session)
        self._audit = AuditService(session)

    async def _to_product_out(self, merchant_id: uuid.UUID, p: Product) -> ProductOut:
        variant = await self._catalog.get_default_variant(merchant_id, p.id)
        in_stock = await self._inventory.check_available(merchant_id, variant.id, 1)
        return ProductOut(
            product_id=p.id,
            external_code=p.external_product_code,
            name=p.name,
            brand=p.brand,
            category=p.category,
            description=p.description,
            price_paise=p.price_paise,
            rating=float(p.rating) if p.rating is not None else None,
            in_stock=in_stock,
            tags=list(p.tags or []),
        )

    async def list_catalog(
        self, merchant_id: uuid.UUID, *, cursor: str | None, limit: int
    ) -> CatalogPage:
        stmt = (
            select(Product)
            .where(Product.merchant_id == merchant_id, Product.status == "active")
            .order_by(Product.name, Product.id)
            .limit(limit + 1)
        )
        if cursor:
            name, pid = _decode_cursor(cursor)
            stmt = stmt.where(
                (Product.name, Product.id) > (name, uuid.UUID(pid))  # type: ignore[operator]
            )
        rows = list(await self._session.scalars(stmt))
        has_more = len(rows) > limit
        rows = rows[:limit]
        products = [await self._to_product_out(merchant_id, p) for p in rows]
        next_cursor = _encode_cursor(rows[-1].name, rows[-1].id) if has_more and rows else None
        return CatalogPage(products=products, next_cursor=next_cursor)

    async def get_product(self, merchant_id: uuid.UUID, product_id: uuid.UUID) -> ProductOut:
        product = await self._catalog.get_product(merchant_id, product_id)
        return await self._to_product_out(merchant_id, product)

    async def search_catalog(
        self, merchant_id: uuid.UUID, body: CatalogSearchIn
    ) -> list[ProductOut]:
        products = await self._catalog.search_products(
            merchant_id,
            query=body.query,
            category=body.category,
            max_price_paise=body.max_price_paise,
            limit=body.limit,
        )
        return [await self._to_product_out(merchant_id, p) for p in products]

    async def _build_cart(self, merchant_id: uuid.UUID, items: list[LineItemIn]) -> uuid.UUID:
        cart_svc = CartService(self._session)
        cart = await cart_svc.create_fresh_cart(merchant_id)
        for item in items:
            await cart_svc.add_item(
                merchant_id,
                cart.id,
                product_id=item.product_id,
                quantity=item.quantity,
                added_reason="external_agent",
            )
        return cart.id

    async def quote(self, merchant_id: uuid.UUID, items: list[LineItemIn]) -> QuoteOut:
        cart_id = await self._build_cart(merchant_id, items)
        pricing = await self._orders.quote_cart(merchant_id, cart_id)
        await self._audit.record(
            merchant_id=merchant_id,
            actor_type="external_agent",
            actor_id=self._actor_id,
            action="DISCOUNT_CALCULATED",
            input={"items": [item.model_dump(mode="json") for item in items]},
            result={"total_paise": pricing.total_paise, "discount_paise": pricing.discount_paise},
        )
        return QuoteOut(
            lines=[
                QuoteLineOut(
                    product_id=ln.product_id,
                    name=ln.name,
                    quantity=ln.quantity,
                    unit_price_paise=ln.unit_price_paise,
                    line_total_paise=ln.line_total_paise,
                    in_stock=ln.in_stock,
                )
                for ln in pricing.lines
            ],
            subtotal_paise=pricing.subtotal_paise,
            discount_paise=pricing.discount_paise,
            shipping_paise=pricing.shipping_paise,
            tax_paise=pricing.tax_paise,
            total_paise=pricing.total_paise,
            campaign=pricing.campaign_name,
            discount_reason=pricing.discount_reason,
        )

    async def create_order(
        self,
        merchant_id: uuid.UUID,
        items: list[LineItemIn],
        *,
        buyer_ref: str | None,
        buyer: BuyerIn | None = None,
    ) -> OrderOut:
        cart_id = await self._build_cart(merchant_id, items)

        shipping_address: dict[str, str] | None = None
        if buyer is not None:
            customer = await self._session.scalar(
                select(Customer).where(
                    Customer.merchant_id == merchant_id,
                    (Customer.email == buyer.email) | (Customer.phone == buyer.phone),
                )
            )
            if customer is None:
                customer = Customer(
                    id=uuid.uuid4(), merchant_id=merchant_id, name=buyer.name
                )
                self._session.add(customer)
            customer.name, customer.email, customer.phone, customer.city = (
                buyer.name,
                buyer.email,
                buyer.phone,
                buyer.city,
            )
            await self._session.flush()
            cart = await self._session.get(Cart, cart_id)
            if cart is not None:
                cart.customer_id = customer.id
            shipping_address = {
                "name": buyer.name,
                "phone": buyer.phone,
                "email": buyer.email,
                "line1": buyer.line1,
                "line2": buyer.line2 or "",
                "city": buyer.city,
                "state": buyer.state or "",
                "postal_code": buyer.postal_code,
                "country": buyer.country,
            }

        order = await self._orders.create_order_from_cart(
            merchant_id,
            cart_id,
            agent_session_id=None,
            actor_type="external_agent",
            actor_id=self._actor_id,
            source="external_ai_buyer",
            buyer_ref=buyer_ref,
            shipping_address=shipping_address,
        )
        return OrderOut(
            order_id=order.id,
            order_number=order.order_number,
            status=order.status,
            subtotal_paise=order.subtotal_paise,
            discount_paise=order.discount_paise,
            shipping_paise=order.shipping_paise,
            tax_paise=order.tax_paise,
            total_paise=order.total_paise,
            shipping_address=order.shipping_address,
        )

    async def get_order(self, merchant_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
        try:
            order = await self._orders.get_order(merchant_id, order_id)
        except OrderNotFound as exc:
            raise AgentOrderNotFound(str(order_id)) from exc
        return OrderOut(
            order_id=order.id,
            order_number=order.order_number,
            status=order.status,
            subtotal_paise=order.subtotal_paise,
            discount_paise=order.discount_paise,
            shipping_paise=order.shipping_paise,
            tax_paise=order.tax_paise,
            total_paise=order.total_paise,
            shipping_address=order.shipping_address,
        )

    async def request_payment(
        self,
        merchant_id: uuid.UUID,
        order_id: uuid.UUID,
        *,
        idempotency_key: str,
        confirmed: bool,
        mandate: PaymentMandateIn | None = None,
    ) -> PaymentOut:
        """First call (confirmed=False) returns approval_required if the merchant
        policy demands confirmation; the buyer's explicit second call
        (confirmed=True) is the consent signal (AP2/ACP/UAP mandate model).

        On the confirmed call the backend creates the Razorpay payment intent and
        a hosted Razorpay Payment Link for the exact amount — paying that link
        fires the webhook that settles the order. An optional ``mandate`` is the
        buyer's delegated authorisation: the charge is refused outside it, and it
        is recorded verbatim in the audit trail.
        """
        try:
            order = await self._orders.get_order(merchant_id, order_id)
        except OrderNotFound as exc:
            raise AgentOrderNotFound(str(order_id)) from exc

        needs_confirmation = await PolicyEngine(self._session).requires_customer_confirmation(
            merchant_id
        )
        if needs_confirmation and not confirmed:
            return PaymentOut(
                order_id=order.id,
                status="approval_required",
                amount_paise=order.total_paise,
                message=(
                    "Merchant policy requires explicit buyer confirmation. Re-call with "
                    "confirmed=true (optionally with a mandate) to authorise payment."
                ),
            )

        mandate_dict: dict[str, object] | None = None
        if mandate is not None:
            if mandate.expires_at <= datetime.now(UTC):
                return PaymentOut(
                    order_id=order.id,
                    status="mandate_expired",
                    amount_paise=order.total_paise,
                    message="The payment mandate has expired. Obtain a fresh authorisation.",
                )
            if mandate.max_amount_paise < order.total_paise:
                return PaymentOut(
                    order_id=order.id,
                    status="mandate_exceeded",
                    amount_paise=order.total_paise,
                    message=(
                        f"Mandate authorises up to {mandate.max_amount_paise} paise but the "
                        f"order total is {order.total_paise} paise."
                    ),
                )
            mandate_dict = mandate.model_dump(mode="json")

        try:
            result = await PaymentService(self._session).create_payment_intent(
                merchant_id,
                order_id,
                idempotency_key=idempotency_key,
                agent_session_id=None,
                actor_type="external_agent",
                actor_id=self._actor_id,
                mandate=mandate_dict,
            )
        except PaymentPolicyDenied as exc:
            return PaymentOut(
                order_id=order.id,
                status="policy_denied",
                amount_paise=order.total_paise,
                message=exc.reason,
            )

        payment_id = uuid.UUID(str(result["payment_id"]))
        link_url: str | None = None
        link_id: str | None = None
        try:
            link = get_razorpay_client().create_payment_link(
                amount_paise=int(str(result["amount_paise"])),
                reference_id=f"{order.order_number}-{str(payment_id)[:8]}",
                description=f"CommerceOS order {order.order_number}",
                notes={
                    "co_payment_id": str(payment_id),
                    "co_order_id": str(order.id),
                    "co_merchant_id": str(merchant_id),
                },
            )
            link_url, link_id = link.short_url, link.link_id
            await PaymentService(self._session).attach_payment_link(
                payment_id, link_id=link.link_id, link_url=link.short_url
            )
        except Exception:  # noqa: BLE001 - link is a convenience; the intent already exists
            link_url = None

        return PaymentOut(
            payment_id=payment_id,
            order_id=order.id,
            status="payment_created",
            amount_paise=int(str(result["amount_paise"])),
            provider_order_id=str(result["provider_order_id"]),
            payment_link_url=link_url,
            payment_link_id=link_id,
            message=(
                "Pay the payment_link_url to complete the charge (test card "
                "4111 1111 1111 1111). The order settles when Razorpay confirms."
                if link_url
                else "Payment intent created; complete it against provider_order_id."
            ),
        )
