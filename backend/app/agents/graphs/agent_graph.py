"""The agent LangGraph, shared by every flow: an ``agent`` node (LLM proposes) and
a ``tools`` node (backend decides), looping until the model answers with no tool
call, the step budget is hit, or a tool parks the turn on approval (ADR-004).

Only the tool registry and the system prompt change between shopping / support /
growth.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.agents.context import ToolContext
from app.agents.state.schema import AgentGraphState
from app.agents.tools.base import ToolRegistry
from app.integrations.langfuse.client import Span, get_tracer
from app.integrations.openai.chat import ChatClient, ChatMessage

_FALLBACK = (
    "I've done what I can for this turn. Could you tell me a bit more about what "
    "you'd like to do next?"
)
_BUDGET_HIT = (
    "This turn ran longer than I'm allowed to. I've stopped here without taking "
    "any further action — please try again or narrow the request."
)


async def _record_action(
    ctx: ToolContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    output: dict[str, Any] | None,
    status: str,
    duration_ms: int,
) -> None:
    from app.agents.models import AgentAction

    ctx.session.add(
        AgentAction(
            id=uuid.uuid4(),
            session_id=ctx.agent_session_id,
            merchant_id=ctx.merchant_id,
            node_name="tools",
            tool_name=tool_name,
            input=tool_input,
            output=output,
            status=status,
            duration_ms=duration_ms,
        )
    )
    await ctx.session.flush()


def build_agent_graph(
    *,
    chat_client: ChatClient,
    registry: ToolRegistry,
    ctx: ToolContext,
    system_prompt: str,
    trace: Span | None = None,
) -> Any:
    specs = registry.specs()
    span: Span = trace or get_tracer().trace(name="agent_turn", metadata={})

    async def agent_node(state: AgentGraphState) -> dict[str, Any]:
        step = state.get("step", 0) + 1

        # Bounded execution (agent-guardrails.md #3): stop on any of the merchant's
        # configured budgets — graph steps, cumulative tool calls, wall-clock.
        deadline = state.get("deadline", 0.0)
        over_budget = (
            step > state.get("max_steps", 8)
            or state.get("tool_calls_made", 0) >= state.get("max_tool_calls", 10)
            or (deadline and time.monotonic() > deadline)
        )
        if over_budget:
            stopped_early = step <= state.get("max_steps", 8) and not (
                state.get("tool_calls_made", 0) >= state.get("max_tool_calls", 10)
            )
            text = _BUDGET_HIT if stopped_early else _FALLBACK
            return {
                "step": step,
                "final_text": text,
                "messages": [ChatMessage(role="assistant", content=text)],
            }

        messages = [ChatMessage(role="system", content=system_prompt), *state["messages"]]
        gen = span.child(
            name="llm.plan", kind="generation", input={"model": chat_client.model, "step": step}
        )
        result = chat_client.complete(messages=messages, tools=specs)
        gen.end(
            output={
                "tool_calls": [tc.name for tc in result.tool_calls],
                "has_text": bool(result.content),
            }
        )

        if result.tool_calls:
            return {
                "step": step,
                "messages": [
                    ChatMessage(
                        role="assistant", content=result.content or "", tool_calls=result.tool_calls
                    )
                ],
            }
        text = result.content or _FALLBACK
        return {
            "step": step,
            "final_text": text,
            "messages": [ChatMessage(role="assistant", content=text)],
        }

    async def tools_node(state: AgentGraphState) -> dict[str, Any]:
        last = state["messages"][-1]
        tool_msgs: list[ChatMessage] = []
        trace_rows: list[dict[str, Any]] = []

        for tc in last.tool_calls:
            started = time.monotonic()
            tool_span = span.child(name=f"tool.{tc.name}", input={"args": sorted(tc.arguments)})
            status = "succeeded"
            try:
                tool = registry.get(tc.name)
                args = tool.Args(**tc.arguments)
                output = await tool.run(ctx, args)
                if isinstance(output, dict) and output.get("error"):
                    status = "failed"
            except KeyError:
                output, status = {"error": f"unknown_tool:{tc.name}"}, "failed"
            except ValidationError as exc:
                output, status = {"error": "invalid_arguments", "detail": exc.errors()}, "failed"
            except Exception as exc:  # domain error -> hand back to the model, don't crash the turn
                output, status = {"error": "tool_error", "detail": str(exc)}, "failed"

            duration_ms = int((time.monotonic() - started) * 1000)
            tool_span.end(output={"status": status}, level="ERROR" if status == "failed" else None)
            await _record_action(
                ctx,
                tool_name=tc.name,
                tool_input=tc.arguments,
                output=output if isinstance(output, dict) else {"value": output},
                status=status,
                duration_ms=duration_ms,
            )
            tool_msgs.append(
                ChatMessage(
                    role="tool",
                    name=tc.name,
                    tool_call_id=tc.id,
                    content=json.dumps(output, default=str),
                )
            )
            trace_rows.append({"tool": tc.name, "status": status, "output": output})

        update: dict[str, Any] = {
            "messages": tool_msgs,
            "tool_trace": trace_rows,
            "tool_calls_made": len(last.tool_calls),
        }
        if ctx.pending_approval is not None:
            update["pending_approval"] = ctx.pending_approval
        return update

    def route_after_agent(state: AgentGraphState) -> str:
        return "tools" if state["messages"][-1].tool_calls else END

    def route_after_tools(state: AgentGraphState) -> str:
        return END if state.get("pending_approval") else "agent"

    graph = StateGraph(AgentGraphState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
    graph.add_conditional_edges("tools", route_after_tools, {"agent": "agent", END: END})
    return graph.compile()
