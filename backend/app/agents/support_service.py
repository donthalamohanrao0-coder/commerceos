"""SupportAgentService — read-only customer support flow. No approval path (the
support agent cannot mutate commerce state), so the approval hooks are inert.
"""

from __future__ import annotations

from typing import Any, ClassVar

from app.agents.base_service import BaseAgentService
from app.agents.models import AgentSession
from app.agents.prompts.support import SUPPORT_SYSTEM_PROMPT
from app.agents.tools.base import ToolRegistry
from app.agents.tools.support import build_support_registry
from app.approvals.models import ApprovalRequest


class SupportAgentService(BaseAgentService):
    workflow: ClassVar[str] = "support"

    def _registry(self) -> ToolRegistry:
        return build_support_registry()

    def _system_prompt(self) -> str:
        return SUPPORT_SYSTEM_PROMPT

    def _format_approval_prompt(self, tool_trace: list[dict[str, Any]]) -> str:  # pragma: no cover
        return "This request needs a merchant operator."

    async def _run_approved_action(
        self, agent_session: AgentSession, approval: ApprovalRequest
    ) -> tuple[str, list[dict[str, Any]]]:  # pragma: no cover - support has no approvals
        return ("Nothing to action.", [])
