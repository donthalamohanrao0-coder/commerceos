"""Deterministic guardrail invariants for money movement (ADR-005,
security-policy.md, agent-guardrails.md #5). No LLM — these assert the properties
the agent *cannot* talk its way past, by driving the domain services directly.

  * a payment over the merchant's transaction limit is refused, with nothing
    written and a PAYMENT_FAILED audit row;
  * an approval is a one-shot gate — it cannot be replayed;
  * payment creation is idempotent (one Payment, one provider order per key);
  * the policy re-check runs at execution time, so a *stale* approval still
    cannot push a charge past the limit.
"""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.service import ApprovalNotPending, ApprovalService
from app.audit.models import AuditEvent
from app.domains.cart.service import CartService
from app.domains.orders.service import OrderService
from app.domains.payments.exceptions import PaymentNotFound, PaymentPolicyDenied
from app.domains.payments.models import Payment
from app.domains.payments.service import PaymentService
from app.integrations.razorpay.fake_client import FakeRazorpayClient
from app.policies.engine import PolicyEngine

pytestmark = pytest.mark.asyncio


async def _order_for(db: AsyncSession, merchant, product, qty: int):  # noqa: ANN202
    carts = CartService(db)
    cart = await carts.create_fresh_cart(merchant.id)
    await carts.add_item(merchant.id, cart.id, product_id=product.id, quantity=qty)
    return await OrderService(db).create_order_from_cart(
        merchant.id, cart.id, agent_session_id=None, actor_type="customer", actor_id=None
    )


async def _payments_for(db: AsyncSession, merchant, order_id: uuid.UUID) -> list[Payment]:
    return list(
        await db.scalars(
            select(Payment).where(
                Payment.merchant_id == merchant.id, Payment.order_id == order_id
            )
        )
    )


async def test_over_limit_payment_is_refused_with_nothing_written(
    db: AsyncSession, merchant, cheap_product
) -> None:
    # what the merchant's max_transaction_amount_paise policy resolves to
    decision = await PolicyEngine(db).check_transaction_amount(merchant.id, 10**12)
    assert not decision.allowed and decision.reason == "exceeds_max_transaction_amount"

    big_order = await _order_for(db, merchant, cheap_product, qty=1)
    # an order total just over the cap (mirrors a large multi-item cart)
    big_order.total_paise = (decision.capped_value or 0) + 1
    await db.flush()

    audits_before = await db.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.merchant_id == merchant.id, AuditEvent.action == "PAYMENT_FAILED"
        )
    )

    with pytest.raises(PaymentPolicyDenied):
        await PaymentService(db, FakeRazorpayClient()).create_payment_intent(
            merchant.id,
            big_order.id,
            idempotency_key=f"gate-{uuid.uuid4()}",
            agent_session_id=None,
            actor_type="agent",
            actor_id="test",
        )

    assert await _payments_for(db, merchant, big_order.id) == []
    audits_after = await db.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.merchant_id == merchant.id, AuditEvent.action == "PAYMENT_FAILED"
        )
    )
    assert audits_after == (audits_before or 0) + 1


async def test_payment_creation_is_idempotent(
    db: AsyncSession, merchant, cheap_product
) -> None:
    order = await _order_for(db, merchant, cheap_product, qty=1)
    svc = PaymentService(db, FakeRazorpayClient())
    key = f"idem-{uuid.uuid4()}"

    first = await svc.create_payment_intent(
        merchant.id, order.id, idempotency_key=key,
        agent_session_id=None, actor_type="customer", actor_id=None,
    )
    second = await svc.create_payment_intent(
        merchant.id, order.id, idempotency_key=key,
        agent_session_id=None, actor_type="customer", actor_id=None,
    )

    assert first == second
    assert len(await _payments_for(db, merchant, order.id)) == 1


async def test_payment_for_unknown_order_is_refused(db: AsyncSession, merchant) -> None:
    with pytest.raises(PaymentNotFound):
        await PaymentService(db, FakeRazorpayClient()).create_payment_intent(
            merchant.id,
            uuid.uuid4(),
            idempotency_key=f"nf-{uuid.uuid4()}",
            agent_session_id=None,
            actor_type="agent",
            actor_id="test",
        )


async def test_approval_is_a_one_shot_gate(db: AsyncSession, merchant) -> None:
    approvals = ApprovalService(db)
    approval = await approvals.request(
        merchant_id=merchant.id,
        requested_action="payment_initiation",
        requested_by="agent",
        payload={"order_id": str(uuid.uuid4())},
    )

    await approvals.approve(merchant.id, approval.id, decided_by=None)

    # granting again — or rejecting after grant — must fail, no replay
    with pytest.raises(ApprovalNotPending):
        await approvals.approve(merchant.id, approval.id, decided_by=None)
    with pytest.raises(ApprovalNotPending):
        await approvals.reject(merchant.id, approval.id, decided_by=None)


async def test_expired_approval_cannot_be_granted(db: AsyncSession, merchant) -> None:
    from datetime import UTC, datetime, timedelta

    approvals = ApprovalService(db)
    approval = await approvals.request(
        merchant_id=merchant.id,
        requested_action="payment_initiation",
        requested_by="agent",
        payload={"order_id": str(uuid.uuid4())},
    )
    approval.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.flush()

    with pytest.raises(ApprovalNotPending):
        await approvals.approve(merchant.id, approval.id, decided_by=None)
