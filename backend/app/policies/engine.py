"""PolicyEngine — the single authority the agent consults before any financial action.

Pure function over the `policies` table. The LLM never sees or edits policy rows
directly (plan.md #16, security-policy.md, agent-guardrails.md #5: "The agent cannot
override a policy result.").
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.models import Policy


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    capped_value: int | None = None


class PolicyEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_value(self, merchant_id: uuid.UUID, key: str) -> Any:
        row = await self._session.scalar(
            select(Policy).where(Policy.merchant_id == merchant_id, Policy.key == key)
        )
        if row is None:
            # Fail closed: an unavailable policy denies the action rather than
            # defaulting to permissive (agent-guardrails.md #8, security-policy.md).
            return None
        return row.value

    async def check_discount(self, merchant_id: uuid.UUID, discount_paise: int) -> PolicyDecision:
        max_discount = await self._get_value(merchant_id, "max_auto_discount_paise")
        if max_discount is None:
            return PolicyDecision(allowed=False, reason="policy_unavailable")
        if discount_paise > max_discount:
            return PolicyDecision(
                allowed=False,
                reason="exceeds_max_auto_discount",
                capped_value=max_discount,
            )
        return PolicyDecision(allowed=True, reason="within_auto_discount_limit")

    async def check_refund(self, merchant_id: uuid.UUID, refund_paise: int) -> PolicyDecision:
        max_refund = await self._get_value(merchant_id, "max_auto_refund_paise")
        if max_refund is None:
            return PolicyDecision(allowed=False, reason="policy_unavailable")
        if refund_paise > max_refund:
            return PolicyDecision(
                allowed=False,
                reason="requires_merchant_approval",
                capped_value=max_refund,
            )
        return PolicyDecision(allowed=True, reason="within_auto_refund_limit")

    async def check_transaction_amount(
        self, merchant_id: uuid.UUID, amount_paise: int
    ) -> PolicyDecision:
        max_amount = await self._get_value(merchant_id, "max_transaction_amount_paise")
        if max_amount is None:
            return PolicyDecision(allowed=False, reason="policy_unavailable")
        if amount_paise > max_amount:
            return PolicyDecision(
                allowed=False,
                reason="exceeds_max_transaction_amount",
                capped_value=max_amount,
            )
        return PolicyDecision(allowed=True, reason="within_transaction_limit")

    async def requires_customer_confirmation(self, merchant_id: uuid.UUID) -> bool:
        value = await self._get_value(merchant_id, "payment_requires_customer_confirmation")
        # Fail closed: an unavailable policy means confirmation IS required.
        return True if value is None else bool(value)

    async def get_agent_limits(self, merchant_id: uuid.UUID) -> dict[str, int]:
        """Bounded-execution limits for the LangGraph runtime wrapper (agent-guardrails.md #3)."""
        keys = ("max_graph_steps", "max_tool_calls", "max_execution_seconds", "max_retries")
        limits: dict[str, int] = {}
        for key in keys:
            value = await self._get_value(merchant_id, key)
            # Conservative built-in fallback if a merchant hasn't configured a limit yet —
            # still bounded, never unbounded.
            limits[key] = int(value) if value is not None else _DEFAULT_LIMITS[key]
        return limits


_DEFAULT_LIMITS = {
    "max_graph_steps": 20,
    "max_tool_calls": 10,
    "max_execution_seconds": 30,
    "max_retries": 2,
}
