"""The browser-side Razorpay Checkout result is verified server-side before any
capture — a good signature captures (Payment + Order -> paid, audited); a bad or
mismatched one raises and captures nothing."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cart.service import CartService
from app.domains.orders.models import Order
from app.domains.orders.service import OrderService
from app.domains.payments.exceptions import PaymentVerificationFailed
from app.domains.payments.models import Payment
from app.domains.payments.service import PaymentService
from app.integrations.razorpay.fake_client import FakeRazorpayClient

pytestmark = pytest.mark.asyncio


async def _seed_payment(db: AsyncSession, merchant, cheap_product) -> tuple[Payment, Order, str]:
    carts = CartService(db)
    cart = await carts.create_fresh_cart(merchant.id)
    await carts.add_item(merchant.id, cart.id, product_id=cheap_product.id, quantity=1)
    order = await OrderService(db).create_order_from_cart(
        merchant.id, cart.id, agent_session_id=None, actor_type="customer", actor_id=None
    )
    provider_order_id = f"order_test_{uuid.uuid4().hex[:12]}"
    payment = Payment(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        order_id=order.id,
        amount_paise=order.total_paise,
        status="pending",
        provider_order_id=provider_order_id,
    )
    db.add(payment)
    await db.flush()
    return payment, order, provider_order_id


async def test_valid_signature_captures_payment_and_order(
    db: AsyncSession, merchant, cheap_product
) -> None:
    payment, order, provider_order_id = await _seed_payment(db, merchant, cheap_product)
    fake = FakeRazorpayClient()
    rzp_payment_id = "pay_test_ok"
    signature = FakeRazorpayClient.sign_payment(provider_order_id, rzp_payment_id)

    result = await PaymentService(db, fake).verify_and_capture(
        merchant.id,
        payment.id,
        razorpay_payment_id=rzp_payment_id,
        razorpay_order_id=provider_order_id,
        razorpay_signature=signature,
    )

    assert result["status"] == "paid"
    await db.refresh(payment)
    await db.refresh(order)
    assert payment.status == "paid"
    assert payment.provider_payment_id == rzp_payment_id
    assert payment.razorpay_signature_verified is True
    assert order.status == "paid"


async def test_bad_signature_raises_and_captures_nothing(
    db: AsyncSession, merchant, cheap_product
) -> None:
    payment, order, provider_order_id = await _seed_payment(db, merchant, cheap_product)

    with pytest.raises(PaymentVerificationFailed):
        await PaymentService(db, FakeRazorpayClient()).verify_and_capture(
            merchant.id,
            payment.id,
            razorpay_payment_id="pay_test_bad",
            razorpay_order_id=provider_order_id,
            razorpay_signature="not-a-real-signature",
        )

    await db.refresh(payment)
    assert payment.status == "pending"


async def test_order_id_mismatch_raises(db: AsyncSession, merchant, cheap_product) -> None:
    payment, _order, provider_order_id = await _seed_payment(db, merchant, cheap_product)
    signature = FakeRazorpayClient.sign_payment("order_someone_else", "pay_x")

    with pytest.raises(PaymentVerificationFailed):
        await PaymentService(db, FakeRazorpayClient()).verify_and_capture(
            merchant.id,
            payment.id,
            razorpay_payment_id="pay_x",
            razorpay_order_id="order_someone_else",
            razorpay_signature=signature,
        )
