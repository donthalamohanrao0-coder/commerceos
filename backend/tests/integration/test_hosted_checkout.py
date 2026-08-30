"""The hosted checkout page (`/pay/{payment_id}`) an external AI buyer hands to a
human: the GET renders a Razorpay Checkout page for an unpaid order, a paid order
shows a terminal state, an unknown id 404s, and the signed callback settles the
order the same way a webhook would."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pay import (
    CheckoutCallbackIn,
    checkout_page,
    render_checkout_page,
    settle_from_checkout,
)
from app.domains.cart.service import CartService
from app.domains.orders.models import Order
from app.domains.orders.service import OrderService
from app.domains.payments.models import Payment
from app.integrations.razorpay.fake_client import FakeRazorpayClient

pytestmark = pytest.mark.asyncio


async def _seed(db: AsyncSession, merchant, cheap_product) -> tuple[Payment, Order, str]:
    carts = CartService(db)
    cart = await carts.create_fresh_cart(merchant.id)
    await carts.add_item(merchant.id, cart.id, product_id=cheap_product.id, quantity=1)
    order = await OrderService(db).create_order_from_cart(
        merchant.id,
        cart.id,
        agent_session_id=None,
        actor_type="external_agent",
        actor_id="ack_test",
        shipping_address={
            "name": "Demo Buyer",
            "email": "demo.buyer@example.com",
            "phone": "+91-9000000000",
            "line1": "1 Demo Street",
            "city": "Bengaluru",
            "postal_code": "560001",
            "country": "IN",
        },
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


async def test_render_checkout_page_has_checkout_js_and_order(
    db: AsyncSession, merchant, cheap_product
) -> None:
    payment, order, provider_order_id = await _seed(db, merchant, cheap_product)
    html = render_checkout_page(payment, order, key_id="rzp_test_abc123")

    assert "https://checkout.razorpay.com/v1/checkout.js" in html
    assert "rzp_test_abc123" in html
    assert provider_order_id in html
    assert order.order_number in html
    assert str(payment.id) in html
    assert "demo.buyer@example.com" in html  # prefill from shipping address


async def test_get_page_unpaid_returns_200(db: AsyncSession, merchant, cheap_product) -> None:
    payment, _order, _poid = await _seed(db, merchant, cheap_product)
    resp = await checkout_page(payment.id, session=db)
    assert resp.status_code == 200
    assert b"Pay now" in resp.body


async def test_get_page_paid_shows_terminal_state(
    db: AsyncSession, merchant, cheap_product
) -> None:
    payment, _order, _poid = await _seed(db, merchant, cheap_product)
    payment.status = "paid"
    await db.flush()
    resp = await checkout_page(payment.id, session=db)
    assert resp.status_code == 200
    assert b"already been settled" in resp.body
    assert b"checkout.razorpay.com" not in resp.body


async def test_get_page_unknown_id_404s(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as ei:
        await checkout_page(uuid.uuid4(), session=db)
    assert ei.value.status_code == 404


async def test_callback_valid_signature_settles_order(
    db: AsyncSession, merchant, cheap_product, monkeypatch
) -> None:
    payment, order, provider_order_id = await _seed(db, merchant, cheap_product)
    monkeypatch.setattr(
        "app.domains.payments.service.get_razorpay_client", lambda: FakeRazorpayClient()
    )
    rzp_payment_id = "pay_hosted_ok"
    signature = FakeRazorpayClient.sign_payment(provider_order_id, rzp_payment_id)

    result = await settle_from_checkout(
        db,
        payment.id,
        CheckoutCallbackIn(
            razorpay_payment_id=rzp_payment_id,
            razorpay_order_id=provider_order_id,
            razorpay_signature=signature,
        ),
    )

    assert result["status"] == "paid"
    await db.refresh(payment)
    await db.refresh(order)
    assert payment.status == "paid"
    assert order.status == "paid"


async def test_callback_bad_signature_400s_and_charges_nothing(
    db: AsyncSession, merchant, cheap_product, monkeypatch
) -> None:
    payment, _order, provider_order_id = await _seed(db, merchant, cheap_product)
    monkeypatch.setattr(
        "app.domains.payments.service.get_razorpay_client", lambda: FakeRazorpayClient()
    )
    with pytest.raises(HTTPException) as ei:
        await settle_from_checkout(
            db,
            payment.id,
            CheckoutCallbackIn(
                razorpay_payment_id="pay_x",
                razorpay_order_id=provider_order_id,
                razorpay_signature="not-a-real-signature",
            ),
        )
    assert ei.value.status_code == 400
    await db.refresh(payment)
    assert payment.status == "pending"
