"""Bounded execution (agent-guardrails.md #3): a turn is seeded with the
merchant's configured budgets — graph steps, cumulative tool calls, wall-clock —
and a merchant can only make them *tighter* than the built-in ceiling, never
unbounded.
"""

import time

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_service import _MAX_STEPS_CEILING
from app.agents.service import ShoppingAgentService
from app.integrations.openai.chat import ChatMessage
from app.policies.models import Policy

pytestmark = pytest.mark.asyncio


async def _state(db: AsyncSession, merchant):  # noqa: ANN202
    svc = ShoppingAgentService(db)
    return await svc._initial_state(
        merchant.id, [], ChatMessage(role="user", content="hi")
    )


async def test_turn_state_carries_every_budget(db: AsyncSession, merchant) -> None:
    state = await _state(db, merchant)
    assert 1 <= state["max_steps"] <= _MAX_STEPS_CEILING
    assert state["max_tool_calls"] >= 1
    assert state["tool_calls_made"] == 0
    assert state["deadline"] > time.monotonic()  # a real wall-clock cutoff


async def test_merchant_policy_can_only_tighten_the_step_budget(
    db: AsyncSession, merchant
) -> None:
    row = await db.scalar(
        select(Policy).where(
            Policy.merchant_id == merchant.id, Policy.key == "max_graph_steps"
        )
    )
    assert row is not None
    original = row.value

    row.value = 3  # tighter than the ceiling
    await db.flush()
    assert (await _state(db, merchant))["max_steps"] == 3

    row.value = 999  # looser than the ceiling -> ceiling wins
    await db.flush()
    assert (await _state(db, merchant))["max_steps"] == _MAX_STEPS_CEILING

    row.value = original  # rolled back anyway, but keep the fixture tidy
    await db.flush()
