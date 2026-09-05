"""External AI-buyer standing mandate: authorise a ceiling once, then charge
within it with no checkout hand-off (Razorpay UPI AutoPay `as_presented`).

  * a fresh mandate is pending_authorization and carries an authorization_url;
  * the hosted approval callback activates it and stores the token;
  * a confirmed payment for a covered order then settles autonomously —
    status "paid", no checkout_url, order flipped to paid, PAYMENT_SUCCEEDED;
  * a charge above the mandate ceiling is not eligible -> hosted-checkout fallback;
  * an expired mandate is not eligible (and is lazily marked expired) -> fallback;
  * a cancelled mandate (token.cancelled) is not eligible -> fallback;
  * the token.confirmed webhook activates a pending mandate.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.schemas import BuyerIn, CreateMandateIn, LineItemIn
from app.agent_commerce.service import AgentCommerceService
from app.api.pay import CheckoutCallbackIn, activate_from_callback
from app.audit.models import AuditEvent
from app.domains.orders.models import Order
from app.domains.payments.models import Payment, PaymentMandate
from app.integrations.razorpay.fake_client import FakeRazorpayClient

pytestmark = pytest.mark.asyncio


def _buyer(tag: str) -> BuyerIn:
    return BuyerIn(
        name=f"Mandate Buyer {tag}",
        email=f"mandate.{tag}@example.com",
        phone=f"+91-90000{tag:0>5}",
        line1="1 Market Rd",
        city="Pune",
        state="MH",
        postal_code="411001",
        country="IN",
    )


async def _order_with_buyer(
    svc: AgentCommerceService, merchant, product, buyer: BuyerIn
) -> uuid.UUID:
    out = await svc.create_order(
        merchant.id, [LineItemIn(product_id=product.id, quantity=1)], buyer_ref=None, buyer=buyer
    )
    return out.order_id


async def _active_mandate(
    svc: AgentCommerceService,
    fake: FakeRazorpayClient,
    db: AsyncSession,
    merchant,
    buyer: BuyerIn,
    *,
    ceiling_paise: int,
    expires_at: datetime,
) -> PaymentMandate:
    created = await svc.create_mandate(
        merchant.id,
        CreateMandateIn(
            buyer=buyer,
            max_amount_paise=ceiling_paise,
            expires_at=expires_at,
            consent_reference=f"consent-{uuid.uuid4().hex[:8]}",
        ),
    )
    assert created.status == "pending_authorization"
    assert created.authorization_url and str(created.mandate_id) in created.authorization_url

    row = await db.get(PaymentMandate, created.mandate_id)
    # the human runs the hosted approval page; the fake signs the auth result
    sig = fake.sign_payment(row.provider_order_id, "pay_auth_x")
    result = await activate_from_callback(
        db,
        created.mandate_id,
        CheckoutCallbackIn(
            razorpay_payment_id="pay_auth_x",
            razorpay_order_id=row.provider_order_id,
            razorpay_signature=sig,
        ),
        razorpay_client=fake,
    )
    assert result["status"] == "active"
    await db.refresh(row)
    assert row.provider_token_id
    return row


async def test_active_mandate_charges_autonomously(
    db: AsyncSession, merchant, cheap_product
) -> None:
    fake = FakeRazorpayClient()
    svc = AgentCommerceService(db, actor_id="agent_key:test", razorpay_client=fake)
    buyer = _buyer("1")
    oid = await _order_with_buyer(svc, merchant, cheap_product, buyer)
    order = await db.get(Order, oid)

    await _active_mandate(
        svc, fake, db, merchant, buyer,
        ceiling_paise=order.total_paise + 100_000,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    out = await svc.request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True
    )
    assert out.status == "paid"
    assert out.checkout_url is None
    assert out.payment_id is not None

    await db.refresh(order)
    assert order.status == "paid"
    payment = await db.scalar(select(Payment).where(Payment.order_id == oid))
    assert payment.status == "paid" and payment.provider_payment_id
    assert await db.scalar(
        select(AuditEvent).where(
            AuditEvent.order_id == oid, AuditEvent.action == "PAYMENT_SUCCEEDED"
        )
    )


async def test_replay_of_mandate_charge_is_idempotent(
    db: AsyncSession, merchant, cheap_product
) -> None:
    fake = FakeRazorpayClient()
    svc = AgentCommerceService(db, actor_id="agent_key:test", razorpay_client=fake)
    buyer = _buyer("2")
    oid = await _order_with_buyer(svc, merchant, cheap_product, buyer)
    order = await db.get(Order, oid)
    await _active_mandate(
        svc, fake, db, merchant, buyer,
        ceiling_paise=order.total_paise + 100_000,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    key = f"k-{uuid.uuid4()}"
    first = await svc.request_payment(merchant.id, oid, idempotency_key=key, confirmed=True)
    second = await svc.request_payment(merchant.id, oid, idempotency_key=key, confirmed=True)
    assert first.status == second.status == "paid"
    assert first.payment_id == second.payment_id
    assert len(fake.recurring_charges) == 1  # charged exactly once


async def test_over_ceiling_falls_back_to_hosted_checkout(
    db: AsyncSession, merchant, cheap_product
) -> None:
    fake = FakeRazorpayClient()
    svc = AgentCommerceService(db, actor_id="agent_key:test", razorpay_client=fake)
    buyer = _buyer("3")
    oid = await _order_with_buyer(svc, merchant, cheap_product, buyer)
    order = await db.get(Order, oid)
    await _active_mandate(
        svc, fake, db, merchant, buyer,
        ceiling_paise=max(1, order.total_paise - 1),  # below the order total
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    out = await svc.request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True
    )
    assert out.status == "payment_created"
    assert out.checkout_url and out.checkout_url.endswith(f"/pay/{out.payment_id}")
    assert not fake.recurring_charges


async def test_expired_mandate_falls_back_and_is_marked_expired(
    db: AsyncSession, merchant, cheap_product
) -> None:
    fake = FakeRazorpayClient()
    svc = AgentCommerceService(db, actor_id="agent_key:test", razorpay_client=fake)
    buyer = _buyer("4")
    oid = await _order_with_buyer(svc, merchant, cheap_product, buyer)
    order = await db.get(Order, oid)
    mandate = await _active_mandate(
        svc, fake, db, merchant, buyer,
        ceiling_paise=order.total_paise + 100_000,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    # lapse it after authorisation
    mandate.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.flush()

    out = await svc.request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True
    )
    assert out.status == "payment_created"  # hosted-checkout fallback
    await db.refresh(mandate)
    assert mandate.status == "expired"


async def test_cancelled_mandate_falls_back(db: AsyncSession, merchant, cheap_product) -> None:
    fake = FakeRazorpayClient()
    svc = AgentCommerceService(db, actor_id="agent_key:test", razorpay_client=fake)
    buyer = _buyer("5")
    oid = await _order_with_buyer(svc, merchant, cheap_product, buyer)
    order = await db.get(Order, oid)
    mandate = await _active_mandate(
        svc, fake, db, merchant, buyer,
        ceiling_paise=order.total_paise + 100_000,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    mandate.status = "cancelled"
    await db.flush()

    out = await svc.request_payment(
        merchant.id, oid, idempotency_key=f"k-{uuid.uuid4()}", confirmed=True
    )
    assert out.status == "payment_created"
    assert not fake.recurring_charges


async def test_token_confirmed_webhook_activates_pending_mandate(
    db: AsyncSession, merchant, cheap_product
) -> None:
    from app.domains.payments.mandate_service import MandateService

    fake = FakeRazorpayClient()
    svc = AgentCommerceService(db, actor_id="agent_key:test", razorpay_client=fake)
    buyer = _buyer("6")
    created = await svc.create_mandate(
        merchant.id,
        CreateMandateIn(
            buyer=buyer,
            max_amount_paise=500_000,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            consent_reference="consent-webhook",
        ),
    )
    row = await db.get(PaymentMandate, created.mandate_id)
    assert row.status == "pending_authorization"

    activated = await MandateService(db, razorpay_client=fake).activate_by_provider_customer(
        row.provider_customer_id, provider_token_id="token_from_webhook"
    )
    assert activated is not None and activated.status == "active"
    await db.refresh(row)
    assert row.provider_token_id == "token_from_webhook"
    assert row.authorized_at is not None
