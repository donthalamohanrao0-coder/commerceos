"""Shared machinery for every agent flow (shopping / support / growth).

Each concrete service supplies a workflow name, a tool registry, a system prompt,
an approval-prompt formatter, and what to do when an approval is granted. Session
lifecycle, transcript persistence, the LangGraph invocation and the Langfuse trace
all live here.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import ToolContext
from app.agents.graphs.agent_graph import build_agent_graph
from app.agents.models import AgentMessage, AgentSession
from app.agents.tools.base import ToolRegistry
from app.approvals.models import ApprovalRequest
from app.approvals.service import ApprovalService
from app.core.logging import request_id_ctx
from app.domains.customers.models import Customer
from app.domains.merchants.models import Merchant
from app.integrations.langfuse.client import get_tracer
from app.integrations.openai.chat import ChatMessage, ToolCall, get_chat_client
from app.policies.engine import PolicyEngine

_HISTORY_LIMIT = 40
# Hard ceiling on graph steps regardless of merchant policy — defence in depth so
# a mis-set `max_graph_steps` can't make a turn pathologically slow/expensive.
_MAX_STEPS_CEILING = 12


class AgentSessionNotFound(Exception):
    pass


class ApprovalMismatch(Exception):
    pass


@dataclass
class AgentTurnResult:
    session_id: uuid.UUID
    session_status: str
    assistant_text: str
    pending_approval: dict[str, Any] | None = None
    tool_trace: list[dict[str, Any]] = field(default_factory=list)


def _dump_message(m: ChatMessage) -> dict[str, Any]:
    return {
        "text": m.content,
        "tool_calls": [
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in m.tool_calls
        ],
        "tool_call_id": m.tool_call_id,
        "name": m.name,
    }


def _load_message(role: str, content: dict[str, Any]) -> ChatMessage:
    return ChatMessage(
        role=role,  # type: ignore[arg-type]
        content=str(content.get("text", "")),
        tool_calls=tuple(
            ToolCall(id=tc["id"], name=tc["name"], arguments=tc.get("arguments", {}))
            for tc in content.get("tool_calls", [])
        ),
        tool_call_id=content.get("tool_call_id"),
        name=content.get("name"),
    )


class BaseAgentService(ABC):
    workflow: ClassVar[str]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---- to be provided by each flow -----------------------------------------

    @abstractmethod
    def _registry(self) -> ToolRegistry: ...

    @abstractmethod
    def _system_prompt(self) -> str: ...

    @abstractmethod
    def _format_approval_prompt(self, tool_trace: list[dict[str, Any]]) -> str: ...

    @abstractmethod
    async def _run_approved_action(
        self, agent_session: AgentSession, approval: ApprovalRequest
    ) -> tuple[str, list[dict[str, Any]]]:
        """Execute the deterministic action the approval unblocks; return
        (assistant_text, tool_trace)."""

    def _rejection_text(self) -> str:
        return "Understood — I won't proceed. Tell me if you'd like to change anything."

    # ---- shared lifecycle ---------------------------------------------------

    async def start_session(
        self,
        *,
        merchant_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
        channel: str = "web_chat",
    ) -> AgentSession:
        agent_session = AgentSession(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer_id,
            workflow=self.workflow,
            status="active",
            channel=channel,
            session_metadata={},
        )
        self._session.add(agent_session)
        await self._session.flush()
        return agent_session

    async def _load_session(self, merchant_id: uuid.UUID, session_id: uuid.UUID) -> AgentSession:
        s = await self._session.get(AgentSession, session_id)
        if s is None or s.merchant_id != merchant_id or s.workflow != self.workflow:
            raise AgentSessionNotFound(str(session_id))
        return s

    async def _history(self, session_id: uuid.UUID) -> list[ChatMessage]:
        rows = list(
            await self._session.scalars(
                select(AgentMessage)
                .where(AgentMessage.session_id == session_id)
                .order_by(AgentMessage.created_at.desc())
                .limit(_HISTORY_LIMIT)
            )
        )
        rows.reverse()
        return [_load_message(r.role, r.content) for r in rows]

    def _persist(self, session_id: uuid.UUID, messages: list[ChatMessage]) -> None:
        # strictly increasing created_at so the transcript reloads in order (several
        # messages in one turn would otherwise share now() and sort randomly)
        base = datetime.now(UTC)
        for i, m in enumerate(messages):
            self._session.add(
                AgentMessage(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    role=m.role,
                    content_type="tool_calls" if m.tool_calls else "text",
                    content=_dump_message(m),
                    created_at=base + timedelta(milliseconds=i),
                )
            )

    async def _persist_message(self, session_id: uuid.UUID, role: str, text: str) -> None:
        self._persist(session_id, [ChatMessage(role=role, content=text)])  # type: ignore[arg-type]
        await self._session.flush()

    async def _build_context(self, agent_session: AgentSession) -> ToolContext:
        merchant = await self._session.get(Merchant, agent_session.merchant_id)
        namespace = merchant.pinecone_namespace if merchant else ""

        segment: str | None = None
        if agent_session.customer_id is not None:
            customer = await self._session.get(Customer, agent_session.customer_id)
            segment = customer.segment if customer else None

        cart_raw = agent_session.session_metadata.get("cart_id")
        addr = agent_session.session_metadata.get("shipping_address")
        return ToolContext(
            session=self._session,
            merchant_id=agent_session.merchant_id,
            agent_session_id=agent_session.id,
            customer_id=agent_session.customer_id,
            customer_segment=segment,
            merchant_namespace=namespace,
            cart_id=uuid.UUID(cart_raw) if cart_raw else None,
            shipping_address=addr if isinstance(addr, dict) else None,
        )

    def _build_graph(self, ctx: ToolContext, merchant_id: uuid.UUID, session_id: uuid.UUID) -> Any:
        trace = get_tracer().trace(
            name=f"{self.workflow}_turn",
            metadata={
                "workflow": self.workflow,
                "merchant_id": str(merchant_id),
                "agent_session_id": str(session_id),
                "request_id": request_id_ctx.get(),
            },
        )
        return build_agent_graph(
            chat_client=get_chat_client(),
            registry=self._registry(),
            ctx=ctx,
            system_prompt=self._system_prompt(),
            trace=trace,
        )

    async def _finalize(
        self,
        agent_session: AgentSession,
        session_id: uuid.UUID,
        history_len: int,
        user_msg: ChatMessage,
        ctx: ToolContext,
        final_state: dict[str, Any],
    ) -> AgentTurnResult:
        """Persist the new transcript slice and settle session status. Shared by
        the buffered and streaming turn paths so their side effects stay identical."""
        get_tracer().flush()

        new_messages = [user_msg, *final_state["messages"][history_len + 1 :]]
        self._persist(session_id, new_messages)

        pending = final_state.get("pending_approval")
        tool_trace = final_state.get("tool_trace", [])
        if pending:
            assistant_text = self._format_approval_prompt(tool_trace)
            self._persist(session_id, [ChatMessage(role="assistant", content=assistant_text)])
        else:
            assistant_text = final_state.get("final_text") or next(
                (m.content for m in reversed(new_messages) if m.role == "assistant" and m.content),
                "",
            )

        if ctx.cart_id is not None:
            agent_session.session_metadata = {
                **agent_session.session_metadata,
                "cart_id": str(ctx.cart_id),
            }
        agent_session.status = "waiting_for_approval" if pending else "active"
        await self._session.flush()

        return AgentTurnResult(
            session_id=session_id,
            session_status=agent_session.status,
            assistant_text=assistant_text,
            pending_approval=pending,
            tool_trace=tool_trace,
        )

    async def _initial_state(
        self, merchant_id: uuid.UUID, history: list[ChatMessage], user_msg: ChatMessage
    ) -> dict[str, Any]:
        """Turn state seeded with this merchant's bounded-execution budgets
        (agent-guardrails.md #3) — never unbounded, and a merchant can only make
        them *tighter* than the built-in ceiling."""
        limits = await PolicyEngine(self._session).get_agent_limits(merchant_id)
        return {
            "messages": [*history, user_msg],
            "step": 0,
            "max_steps": min(limits["max_graph_steps"], _MAX_STEPS_CEILING),
            "max_tool_calls": limits["max_tool_calls"],
            "tool_calls_made": 0,
            "deadline": time.monotonic() + limits["max_execution_seconds"],
            "tool_trace": [],
        }

    async def send_message(
        self, *, merchant_id: uuid.UUID, session_id: uuid.UUID, text: str
    ) -> AgentTurnResult:
        agent_session = await self._load_session(merchant_id, session_id)
        history = await self._history(session_id)
        user_msg = ChatMessage(role="user", content=text)
        ctx = await self._build_context(agent_session)

        graph = self._build_graph(ctx, merchant_id, session_id)
        final_state = await graph.ainvoke(
            await self._initial_state(merchant_id, history, user_msg)
        )
        return await self._finalize(
            agent_session, session_id, len(history), user_msg, ctx, final_state
        )

    async def stream_message(
        self, *, merchant_id: uuid.UUID, session_id: uuid.UUID, text: str
    ) -> AsyncIterator[dict[str, Any]]:
        """Same turn as ``send_message`` but yields progress events as the graph
        runs (frontend-architecture.md §7). Terminal event ``done`` carries the
        exact payload ``send_message`` would have returned."""
        agent_session = await self._load_session(merchant_id, session_id)
        history = await self._history(session_id)
        user_msg = ChatMessage(role="user", content=text)
        ctx = await self._build_context(agent_session)
        graph = self._build_graph(ctx, merchant_id, session_id)

        yield {"type": "start"}

        final_state: dict[str, Any] = {"messages": [], "tool_trace": []}
        seen_trace = 0
        seen_tool_call_ids: set[str] = set()
        try:
            async for state in graph.astream(
                await self._initial_state(merchant_id, history, user_msg),
                stream_mode="values",
            ):
                final_state = state
                messages = state.get("messages", [])
                if messages and messages[-1].tool_calls:
                    fresh = [
                        tc for tc in messages[-1].tool_calls if tc.id not in seen_tool_call_ids
                    ]
                    if fresh:
                        seen_tool_call_ids.update(tc.id for tc in fresh)
                        yield {"type": "planning", "tools": [tc.name for tc in fresh]}

                trace = state.get("tool_trace", [])
                for row in trace[seen_trace:]:
                    yield {"type": "tool", "tool": row["tool"], "status": row["status"]}
                seen_trace = len(trace)
        except Exception:  # noqa: BLE001 - surface a clean error event, keep the stream well-formed
            yield {"type": "error", "message": "The assistant hit an error. No action was taken."}
            return

        result = await self._finalize(
            agent_session, session_id, len(history), user_msg, ctx, final_state
        )
        yield {
            "type": "done",
            "session_id": str(result.session_id),
            "session_status": result.session_status,
            "assistant": result.assistant_text,
            "pending_approval": result.pending_approval,
            "tool_trace": result.tool_trace,
        }

    async def resolve_approval(
        self,
        *,
        merchant_id: uuid.UUID,
        session_id: uuid.UUID,
        approval_id: uuid.UUID,
        approved: bool,
    ) -> AgentTurnResult:
        agent_session = await self._load_session(merchant_id, session_id)
        approval = await self._session.get(ApprovalRequest, approval_id)
        if approval is None or approval.session_id != session_id:
            raise ApprovalMismatch(str(approval_id))

        approvals = ApprovalService(self._session)
        if not approved:
            await approvals.reject(merchant_id, approval_id, decided_by=None)
            agent_session.status = "active"
            text = self._rejection_text()
            await self._persist_message(session_id, "assistant", text)
            await self._session.flush()
            return AgentTurnResult(session_id, "active", text)

        await approvals.approve(merchant_id, approval_id, decided_by=None)
        text, trace = await self._run_approved_action(agent_session, approval)
        agent_session.status = "active"
        await self._persist_message(session_id, "assistant", text)
        await self._session.flush()
        return AgentTurnResult(session_id, "active", text, tool_trace=trace)
