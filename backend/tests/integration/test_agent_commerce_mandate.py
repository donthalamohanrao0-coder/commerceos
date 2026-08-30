"""External AI-buyer payment: the delegated-mandate check and the hosted
checkout / settlement path (the AP2/ACP/UAP model the Razorpay brief points at).

  * a confirmed request without a mandate still works and always returns a
    hosted checkout_url (a Payment Link is best-effort — test mode caps it at 30);
  * a mandate whose ceiling is below the order total refuses the charge, nothing
    written;
  * an expired mandate refuses the charge;
  * a valid mandate is accepted and recorded verbatim in the PAYMENT_CREATED audit row;
  * settling by payment id (simulated payment_link.paid webhook / hosted-checkout
    callback, matched on the payment id) flips the order to `paid` with a
    PAYMENT_SUCCEEDED audit row.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.schemas import BuyerIn, LineItemIn, PaymentMandateIn
from app.agent_commerce.service import AgentCommerceService
from app.audit.models import AuditEvent
from app.domains.cart.service import CartService
from app.domains.customers.models import Customer
from app.domains.orders.models import Order
from app.domains.orders.service import OrderService
from app.domains.payments.models import Payment
from app.domains.payments.service import PaymentService

pytestmark = pytest.mark.asyncio


async def _order_id(db: AsyncSession, merchant, product) -> uuid.UUID:
    carts = CartService(db)
    cart = await carts.create_fresh_cart(merchant.id)
    await carts.add_item(merchant.id, cart.id, product_id=product.id, quantity=1)
    order = await OrderService(db).create_order_from_cart(
        merchant.id, cart.id, agent_session_id=None, actor_type="external_agent", actor_id=None
    )
    return order.id


def _svc(db: AsyncSession) -> AgentCommerceService:
    return AgentCommerceService(db, actor_id="agent_key:test")


async def test_confirmed_without_mandate_returns_checkout_url(
    db: AsyncSession, merchant, cheap_product
) -> None:
    oid = await _order_id(db, merchant, cheap_product)
    out = await _svc(db).request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True
    )
    assert out.status == "payment_created"
    assert out.provider_order_id
    # checkout_url is unconditional — it needs no Razorpay call at request time.
    assert out.checkout_url and out.checkout_url.endswith(f"/pay/{out.payment_id}")
    # a Payment Link is a bonus; when it cannot be minted, link_error says why.
    assert bool(out.payment_link_url) == (out.link_error is None)


async def test_mandate_ceiling_below_total_refuses(
    db: AsyncSession, merchant, cheap_product
) -> None:
    oid = await _order_id(db, merchant, cheap_product)
    order = await db.get(Order, oid)
    mandate = PaymentMandateIn(
        consent_reference="mrc-consent-1",
        max_amount_paise=max(1, order.total_paise - 1),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    out = await _svc(db).request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True, mandate=mandate
    )
    assert out.status == "mandate_exceeded"
    assert not list(await db.scalars(select(Payment).where(Payment.order_id == oid)))


async def test_expired_mandate_refuses(db: AsyncSession, merchant, cheap_product) -> None:
    oid = await _order_id(db, merchant, cheap_product)
    order = await db.get(Order, oid)
    mandate = PaymentMandateIn(
        consent_reference="mrc-consent-2",
        max_amount_paise=order.total_paise + 10_000,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    out = await _svc(db).request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True, mandate=mandate
    )
    assert out.status == "mandate_expired"
    assert not list(await db.scalars(select(Payment).where(Payment.order_id == oid)))


async def test_valid_mandate_recorded_in_audit(db: AsyncSession, merchant, cheap_product) -> None:
    oid = await _order_id(db, merchant, cheap_product)
    order = await db.get(Order, oid)
    mandate = PaymentMandateIn(
        consent_reference="mrc-consent-3",
        max_amount_paise=order.total_paise + 50_000,
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    out = await _svc(db).request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True, mandate=mandate
    )
    assert out.status == "payment_created"

    row = await db.scalar(
        select(AuditEvent).where(AuditEvent.order_id == oid, AuditEvent.action == "PAYMENT_CREATED")
    )
    assert row is not None
    assert row.input == {"mandate": mandate.model_dump(mode="json")}


async def test_settle_by_payment_id_settles_order(
    db: AsyncSession, merchant, cheap_product
) -> None:
    oid = await _order_id(db, merchant, cheap_product)
    out = await _svc(db).request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True
    )
    assert out.payment_id is not None

    # what the webhook handler (payment_link.paid, notes carry our payment id) and
    # the hosted-checkout callback both funnel into.
    settled = await PaymentService(db).confirm_captured_by_payment_id(payment_id=out.payment_id)
    assert settled.status == "paid"

    order = await db.get(Order, oid)
    assert order.status == "paid"
    assert await db.scalar(
        select(AuditEvent).where(
            AuditEvent.order_id == oid, AuditEvent.action == "PAYMENT_SUCCEEDED"
        )
    )


async def test_reconcile_settles_when_provider_says_paid(
    db: AsyncSession, merchant, cheap_product
) -> None:
    """The safety net for a missed / mis-signed settlement webhook: ask Razorpay
    directly and settle if it says the payment link cleared."""
    from app.domains.payments.models import Payment
    from app.domains.payments.state_machine import transition
    from app.integrations.razorpay.fake_client import FakeRazorpayClient

    oid = await _order_id(db, merchant, cheap_product)
    order = await db.get(Order, oid)
    payment = Payment(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        order_id=oid,
        amount_paise=order.total_paise,
        status="created",
        provider_order_id="order_recon_x",
        payment_link_id="plink_recon_x",
        payment_link_url="https://rzp.test/i/plink_recon_x",
    )
    transition(payment, "pending")
    db.add(payment)
    await db.flush()

    fake = FakeRazorpayClient()
    svc = PaymentService(db, fake)

    assert (await svc.reconcile(merchant.id, payment.id))["action"] == "no_change"

    fake.mark_link_paid("plink_recon_x")  # the buyer pays the hosted link
    assert (await svc.reconcile(merchant.id, payment.id))["action"] == "settled"

    await db.refresh(order)
    assert order.status == "paid"


async def test_buyer_block_creates_customer_and_shipping_address(
    db: AsyncSession, merchant, cheap_product
) -> None:
    from app.domains.orders.models import Order as OrderModel

    buyer = BuyerIn(
        name="Asha Rao",
        email="asha.rao@example.com",
        phone="+91-9000000001",
        line1="12 MG Road",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        country="IN",
    )
    out = await _svc(db).create_order(
        merchant.id,
        [LineItemIn(product_id=cheap_product.id, quantity=1)],
        buyer_ref="po-778",
        buyer=buyer,
    )
    assert out.shipping_address is not None
    assert out.shipping_address["city"] == "Bengaluru"
    assert out.shipping_address["postal_code"] == "560001"

    order = await db.get(OrderModel, out.order_id)
    assert order.shipping_address["line1"] == "12 MG Road"
    assert order.customer_id is not None

    customer = await db.get(Customer, order.customer_id)
    assert customer.email == "asha.rao@example.com"
    assert customer.phone == "+91-9000000001"
