"""The Fake AI clients are the deterministic backbone of the agent-eval tests —
pin their behaviour."""

import json
import math

from app.integrations.openai.chat import ChatMessage, FakeChatClient, ToolSpec
from app.integrations.openai.embeddings import FakeEmbeddingClient


def test_fake_embeddings_are_deterministic_unit_vectors() -> None:
    client = FakeEmbeddingClient(dimension=64)
    a1, a2 = client.embed(["hello"]), client.embed(["hello"])
    assert a1 == a2  # same text -> same vector
    assert client.embed(["hello"]) != client.embed(["world"])
    (vec,) = client.embed(["anything"])
    assert len(vec) == 64
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-9)


def _tools(*names: str) -> list[ToolSpec]:
    return [ToolSpec(name=n, description=n, parameters={"type": "object"}) for n in names]


def test_fake_chat_planner_runs_a_policy_question() -> None:
    client = FakeChatClient()
    result = client.complete(
        messages=[ChatMessage(role="user", content="what is your return policy?")],
        tools=_tools("knowledge_search", "catalog_search"),
    )
    assert result.tool_calls and result.tool_calls[0].name == "knowledge_search"


def test_fake_chat_planner_drives_the_buy_flow_in_order() -> None:
    client = FakeChatClient()
    tools = _tools(
        "catalog_search", "cart_add_item", "campaign_preview", "order_create", "payment_request"
    )
    transcript: list[ChatMessage] = [
        ChatMessage(role="user", content="buy me a laptop under 80000")
    ]

    def push_tool(name: str, payload: dict) -> None:
        transcript.append(
            ChatMessage(role="tool", name=name, tool_call_id="x", content=json.dumps(payload))
        )

    seen: list[str] = []
    for _ in range(8):
        res = client.complete(messages=transcript, tools=tools)
        if not res.tool_calls:
            break
        call = res.tool_calls[0]
        seen.append(call.name)
        transcript.append(ChatMessage(role="assistant", content="", tool_calls=res.tool_calls))
        if call.name == "catalog_search":
            push_tool(
                call.name, {"products": [{"product_id": "11111111-1111-1111-1111-111111111111"}]}
            )
        elif call.name == "order_create":
            push_tool(call.name, {"order_id": "22222222-2222-2222-2222-222222222222"})
        else:
            push_tool(call.name, {"ok": True})

    assert seen == [
        "catalog_search",
        "cart_add_item",
        "campaign_preview",
        "order_create",
        "payment_request",
    ]
