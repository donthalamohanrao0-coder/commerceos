"""PolicyEngine decision logic with a stub session — pure, no DB."""

import uuid
from typing import Any

import pytest

from app.policies.engine import PolicyEngine
from app.policies.models import Policy

MID = uuid.uuid4()


class _StubSession:
    def __init__(self, policies: dict[str, Any]) -> None:
        self._policies = policies

    async def scalar(self, _stmt: Any) -> Policy | None:
        # PolicyEngine builds `select(Policy).where(key == <k>)`; pull the literal out
        key = _stmt.whereclause.clauses[1].right.value  # type: ignore[union-attr]
        if key not in self._policies:
            return None
        return Policy(merchant_id=MID, key=key, value=self._policies[key])


def _engine(policies: dict[str, Any]) -> PolicyEngine:
    return PolicyEngine(_StubSession(policies))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_transaction_limit_allows_and_denies() -> None:
    eng = _engine({"max_transaction_amount_paise": 100_000})
    assert (await eng.check_transaction_amount(MID, 99_999)).allowed
    denied = await eng.check_transaction_amount(MID, 100_001)
    assert not denied.allowed
    assert denied.reason == "exceeds_max_transaction_amount"
    assert denied.capped_value == 100_000


@pytest.mark.asyncio
async def test_missing_policy_fails_closed() -> None:
    eng = _engine({})
    assert not (await eng.check_transaction_amount(MID, 1)).allowed
    assert not (await eng.check_discount(MID, 1)).allowed
    # confirmation requirement fails closed to "confirmation required"
    assert await eng.requires_customer_confirmation(MID) is True


@pytest.mark.asyncio
async def test_discount_cap_is_reported() -> None:
    eng = _engine({"max_auto_discount_paise": 1_000})
    decision = await eng.check_discount(MID, 5_000)
    assert not decision.allowed
    assert decision.capped_value == 1_000


@pytest.mark.asyncio
async def test_agent_limits_have_bounded_fallback() -> None:
    limits = await _engine({}).get_agent_limits(MID)
    assert limits["max_graph_steps"] > 0
    assert limits["max_tool_calls"] > 0
