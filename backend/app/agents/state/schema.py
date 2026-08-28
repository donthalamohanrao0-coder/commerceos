"""Shared LangGraph state for every agent flow (shopping / support / growth).

LangGraph owns in-turn control flow only (agent <-> tools loop, routing,
termination, approval interrupt) per ADR-004. Cross-turn persistence is Postgres
(agent_sessions / agent_messages / agent_actions), rebuilt into `messages` at the
start of each turn — so no checkpointer / thread state to manage.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.integrations.openai.chat import ChatMessage


class AgentGraphState(TypedDict, total=False):
    messages: Annotated[list[ChatMessage], operator.add]
    step: int
    max_steps: int
    # bounded-execution budgets (PolicyEngine.get_agent_limits, agent-guardrails.md #3)
    max_tool_calls: int
    tool_calls_made: Annotated[int, operator.add]
    deadline: float  # time.monotonic() past which the turn must stop
    final_text: str | None
    pending_approval: dict[str, Any] | None
    tool_trace: Annotated[list[dict[str, Any]], operator.add]
