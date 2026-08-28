"""GrowthAgentService — merchant-facing revenue-growth flow. On approval it
activates the drafted campaign (the deterministic action the approval unblocks).
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from app.agents.base_service import BaseAgentService
from app.agents.models import AgentSession
from app.agents.prompts.growth import GROWTH_SYSTEM_PROMPT
from app.agents.tools.base import ToolRegistry
from app.agents.tools.growth import build_growth_registry
from app.approvals.models import ApprovalRequest
from app.domains.campaigns.exceptions import CampaignNotFound
from app.domains.campaigns.service import CampaignService


class GrowthAgentService(BaseAgentService):
    workflow: ClassVar[str] = "growth"

    def _registry(self) -> ToolRegistry:
        return build_growth_registry()

    def _system_prompt(self) -> str:
        return GROWTH_SYSTEM_PROMPT

    def _rejection_text(self) -> str:
        return (
            "Understood — I'll leave that campaign as a draft. Want me to look for another angle?"
        )

    def _format_approval_prompt(self, tool_trace: list[dict[str, Any]]) -> str:
        draft: dict[str, Any] = next(
            (
                s["output"]
                for s in tool_trace
                if s.get("tool") == "draft_campaign" and isinstance(s.get("output"), dict)
            ),
            {},
        )
        pct = draft.get("discount_percent")
        detail = f" ({pct:g}% off, policy-capped)" if isinstance(pct, int | float) else ""
        return (
            f"I've drafted a campaign{detail}. It stays a draft until you approve it — "
            "approve to activate, or decline to keep iterating."
        )

    async def _run_approved_action(
        self, agent_session: AgentSession, approval: ApprovalRequest
    ) -> tuple[str, list[dict[str, Any]]]:
        campaign_id = uuid.UUID(str(approval.payload["campaign_id"]))
        try:
            campaign = await CampaignService(self._session).activate(
                agent_session.merchant_id, campaign_id
            )
        except CampaignNotFound:
            return (
                "I couldn't find that campaign to activate.",
                [
                    {
                        "tool": "activate_campaign",
                        "status": "failed",
                        "output": {"error": "not_found"},
                    }
                ],
            )
        return (
            f"Campaign '{campaign.name}' is now active.",
            [
                {
                    "tool": "activate_campaign",
                    "status": "succeeded",
                    "output": {"campaign_id": str(campaign.id), "status": campaign.status},
                }
            ],
        )
