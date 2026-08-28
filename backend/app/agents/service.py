"""ShoppingAgentService — customer-facing shopping flow. Adds a payment execution
on approval to the shared BaseAgentService lifecycle.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from app.agents.base_service import (
    AgentSessionNotFound,
    AgentTurnResult,
    ApprovalMismatch,
    BaseAgentService,
)
from app.agents.models import AgentSession
from app.agents.prompts.shopping import SHOPPING_SYSTEM_PROMPT
from app.agents.tools.base import ToolRegistry
from app.agents.tools.shopping import build_shopping_registry
from app.approvals.models import ApprovalRequest
from app.domains.payments.exceptions import PaymentPolicyDenied
from app.domains.payments.service import PaymentService

__all__ = [
    "AgentSessionNotFound",
    "AgentTurnResult",
    "ApprovalMismatch",
    "ShoppingAgentService",
]


class ShoppingAgentService(BaseAgentService):
    workflow: ClassVar[str] = "shopping"

    def _registry(self) -> ToolRegistry:
        return build_shopping_registry()

    def _system_prompt(self) -> str:
        return SHOPPING_SYSTEM_PROMPT

    def _rejection_text(self) -> str:
        return "Understood — I won't charge the card. Tell me if you'd like to change anything."

    def _format_approval_prompt(self, tool_trace: list[dict[str, Any]]) -> str:
        order: dict[str, Any] = next(
            (
                s["output"]
                for s in tool_trace
                if s.get("tool") == "order_create" and isinstance(s.get("output"), dict)
            ),
            {},
        )
        total = order.get("total_paise")
        suffix = f" (total ₹{total / 100:.2f})" if isinstance(total, int) else ""
        return (
            f"I've prepared your order{suffix}. I need your confirmation to charge the card — "
            "the agent can't complete payment on its own. Approve or decline to continue."
        )

    async def _run_approved_action(
        self, agent_session: AgentSession, approval: ApprovalRequest
    ) -> tuple[str, list[dict[str, Any]]]:
        order_id = uuid.UUID(str(approval.payload["order_id"]))
        try:
            result = await PaymentService(self._session).create_payment_intent(
                agent_session.merchant_id,
                order_id,
                idempotency_key=f"agent-{agent_session.id}-{order_id}",
                agent_session_id=agent_session.id,
                actor_type="customer",
                actor_id=None,
            )
        except PaymentPolicyDenied as exc:
            return (
                f"I couldn't start the payment: {exc.reason}.",
                [{"tool": "payment_request", "status": "failed", "output": {"reason": exc.reason}}],
            )
        amount_paise = int(str(result.get("amount_paise", 0)))
        return (
            f"Your payment for ₹{amount_paise / 100:.2f} is ready. Complete it in the secure "
            "Razorpay window — I'll confirm your order as soon as it goes through.",
            [
                {
                    "tool": "payment_request",
                    "status": "succeeded",
                    "output": {**result, "stage": "checkout_pending"},
                }
            ],
        )
