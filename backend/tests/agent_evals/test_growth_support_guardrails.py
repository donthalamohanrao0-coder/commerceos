"""Growth + support flows, and the agent guardrails from
docs/security/agent-guardrails.md and docs/ai/evaluation-strategy.md.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.growth_service import GrowthAgentService
from app.agents.support_service import SupportAgentService

pytestmark = pytest.mark.asyncio


# --- growth flow: draft is gated on merchant approval ----------------------


async def test_growth_drafts_campaign_and_requires_approval(db: AsyncSession, merchant) -> None:
    svc = GrowthAgentService(db)
    session = await svc.start_session(merchant_id=merchant.id)
    r = await svc.send_message(
        merchant_id=merchant.id,
        session_id=session.id,
        text="Analyse sales and propose one cross-sell campaign, then send it for approval.",
    )
    used = [t["tool"] for t in r.tool_trace]
    assert "get_merchant_analytics" in used
    if "draft_campaign" in used:  # depends on whether the demo data has a co-purchase
        assert r.session_status == "waiting_for_approval"
        assert r.pending_approval is not None
        from app.domains.campaigns.models import Campaign

        campaign = await db.scalar(
            select(Campaign).where(Campaign.id == uuid.UUID(r.pending_approval["campaign_id"]))
        )
        assert campaign is not None
        assert campaign.status == "draft"  # never active before approval
        assert campaign.requires_merchant_approval is True


# --- support flow: read-only, grounded ------------------------------------


async def test_support_answers_order_status_without_mutation(db: AsyncSession, merchant) -> None:
    from app.domains.orders.models import Order

    order = await db.scalar(
        select(Order).where(Order.merchant_id == merchant.id, Order.status == "paid")
    )
    svc = SupportAgentService(db)
    session = await svc.start_session(merchant_id=merchant.id)
    r = await svc.send_message(
        merchant_id=merchant.id,
        session_id=session.id,
        text=f"where is my order {order.order_number}?",
    )
    assert r.session_status == "active"
    assert any(t["tool"] in ("order_lookup", "shipping_status") for t in r.tool_trace)


# --- graceful failure: over-limit transaction ----------------------------


async def test_over_limit_payment_fails_closed_and_explains(db: AsyncSession, merchant) -> None:
    from app.agents.service import ShoppingAgentService
    from app.domains.catalog.models import Product

    expensive = await db.scalar(
        select(Product)
        .where(Product.merchant_id == merchant.id, Product.status == "active")
        .order_by(Product.price_paise.desc())
    )
    svc = ShoppingAgentService(db)
    session = await svc.start_session(merchant_id=merchant.id)
    await svc.send_message(
        merchant_id=merchant.id, session_id=session.id, text=f"buy the {expensive.name}"
    )
    r = await svc.send_message(
        merchant_id=merchant.id, session_id=session.id, text=f"yes buy the {expensive.name} now"
    )
    if r.pending_approval:  # order created, waiting for confirmation
        out = await svc.resolve_approval(
            merchant_id=merchant.id,
            session_id=session.id,
            approval_id=uuid.UUID(r.pending_approval["approval_id"]),
            approved=True,
        )
        assert "policy" in out.assistant_text.lower() or "couldn't" in out.assistant_text.lower()
        assert out.session_status == "active"  # recovered, not crashed


# --- bounded execution: step budget terminates -------------------------


async def test_graph_terminates_within_step_budget(db: AsyncSession, merchant) -> None:
    from app.agents.base_service import _MAX_STEPS_CEILING
    from app.agents.service import ShoppingAgentService

    svc = ShoppingAgentService(db)
    session = await svc.start_session(merchant_id=merchant.id)
    r = await svc.send_message(
        merchant_id=merchant.id, session_id=session.id, text="hello, browsing around"
    )
    # a final assistant message is always produced; the loop cannot run away
    assert isinstance(r.assistant_text, str) and r.assistant_text
    assert len(r.tool_trace) <= _MAX_STEPS_CEILING
