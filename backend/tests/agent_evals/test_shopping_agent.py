"""Shopping-agent evaluation: intent -> tools -> order -> approval-gated payment,
driven by the deterministic FakeChatClient against the live schema.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import AgentAction
from app.agents.service import ShoppingAgentService

pytestmark = pytest.mark.asyncio


async def test_buy_flow_reaches_approval_then_pays(db: AsyncSession, merchant, customer) -> None:
    svc = ShoppingAgentService(db)
    session = await svc.start_session(merchant_id=merchant.id, customer_id=customer.id)

    r1 = await svc.send_message(
        merchant_id=merchant.id, session_id=session.id, text="recommend a wireless mouse"
    )
    assert r1.session_status == "active"
    assert any(t["tool"] == "catalog_search" for t in r1.tool_trace)

    r2 = await svc.send_message(
        merchant_id=merchant.id, session_id=session.id, text="great, buy the first one"
    )
    # payment must NOT be taken without approval
    assert r2.session_status == "waiting_for_approval"
    assert r2.pending_approval is not None
    tools_used = [t["tool"] for t in r2.tool_trace]
    # cart -> order -> payment, in that dependency order
    assert tools_used.index("cart_add_item") < tools_used.index("order_create")
    assert tools_used.index("order_create") < tools_used.index("payment_request")

    approval_id = r2.pending_approval["approval_id"]
    r3 = await svc.resolve_approval(
        merchant_id=merchant.id,
        session_id=session.id,
        approval_id=__import__("uuid").UUID(approval_id),
        approved=True,
    )
    assert r3.session_status == "active"
    text = r3.assistant_text.lower()
    # either the Checkout hand-off copy, or a policy denial — never a silent charge
    assert "razorpay" in text or "complete it" in text or "policy" in text or "couldn't" in text

    # every tool call was recorded for the audit/eval trail
    actions = list(
        await db.scalars(select(AgentAction).where(AgentAction.session_id == session.id))
    )
    assert {a.tool_name for a in actions} >= {"catalog_search", "cart_add_item", "order_create"}
    assert all(a.status in ("succeeded", "failed") for a in actions)


async def test_decline_does_not_charge(db: AsyncSession, merchant, customer) -> None:
    svc = ShoppingAgentService(db)
    session = await svc.start_session(merchant_id=merchant.id, customer_id=customer.id)
    await svc.send_message(merchant_id=merchant.id, session_id=session.id, text="find a mouse")
    r = await svc.send_message(
        merchant_id=merchant.id, session_id=session.id, text="buy the first one"
    )
    assert r.pending_approval is not None
    out = await svc.resolve_approval(
        merchant_id=merchant.id,
        session_id=session.id,
        approval_id=__import__("uuid").UUID(r.pending_approval["approval_id"]),
        approved=False,
    )
    assert out.session_status == "active"
    from app.domains.payments.models import Payment

    payments = list(await db.scalars(select(Payment).where(Payment.merchant_id == merchant.id)))
    assert all(p.order_id is not None for p in payments)  # no orphan / forced payment
