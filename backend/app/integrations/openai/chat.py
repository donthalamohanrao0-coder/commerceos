"""Capability seam for the chat/reasoning LLM (harness-engineering-patterns.md #3).

Real client -> OpenAI chat completions with tool calling. Fake client -> a
deterministic, keyword-driven planner that can still drive a full shopping flow
(search -> recommend -> cart -> campaign -> order -> payment) so the graph, the
tool lifecycle and the API are all testable with no key and no network.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal, Protocol

from app.core.config import get_settings

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ChatResult:
    content: str | None
    tool_calls: tuple[ToolCall, ...] = ()


class ChatClient(Protocol):
    model: str

    async def complete(
        self, *, messages: list[ChatMessage], tools: list[ToolSpec], temperature: float = 0.2
    ) -> ChatResult: ...


# --------------------------------------------------------------------------- real


class OpenAIChatClient:
    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def complete(
        self, *, messages: list[ChatMessage], tools: list[ToolSpec], temperature: float = 0.2
    ) -> ChatResult:
        payload: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                payload.append(
                    {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
                )
            elif m.role == "assistant" and m.tool_calls:
                payload.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            else:
                payload.append({"role": m.role, "content": m.content})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": payload,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        completion = await self._client.chat.completions.create(**kwargs)
        choice = completion.choices[0].message
        calls = tuple(
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments or "{}"),
            )
            for tc in (choice.tool_calls or [])
        )
        return ChatResult(content=choice.content, tool_calls=calls)


# --------------------------------------------------------------------------- fake


@dataclass
class FakeChatClient:
    """Deterministic planner. Reads the running transcript and emits the next
    tool call (or a final answer) using simple rules, so integration tests get a
    stable multi-step shopping conversation."""

    model: str = "fake-chat"
    _counter: dict[str, int] = field(default_factory=dict)

    def _seq(self, call_id: str) -> str:
        self._counter[call_id] = self._counter.get(call_id, 0) + 1
        return f"call_{call_id}_{self._counter[call_id]}"

    async def complete(
        self, *, messages: list[ChatMessage], tools: list[ToolSpec], temperature: float = 0.2
    ) -> ChatResult:
        names = {t.name for t in tools}
        called = {m.name for m in messages if m.role == "tool"}  # across the whole transcript
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "").lower()
        last_tool_msg = next((m for m in reversed(messages) if m.role == "tool"), None)

        def call(tool_name: str, **args: Any) -> ChatResult:
            return ChatResult(
                content=None,
                tool_calls=(ToolCall(id=self._seq(tool_name), name=tool_name, arguments=args),),
            )

        is_policy_q = any(
            w in last_user
            for w in ("return", "refund", "warranty", "shipping", "policy", "deliver", "how long")
        )
        wants_buy = any(
            w in last_user
            for w in ("buy", "order", "checkout", "purchase", "pay", "add to cart", "take it")
        )
        cat = _category_for(last_user)
        wants_products = bool(cat) or any(
            w in last_user for w in ("recommend", "suggest", "compare", "cheaper", "product")
        )

        # --- support flow -------------------------------------------------
        order_ref = _extract_order_ref(last_user)
        if order_ref and "shipping_status" in names and "shipping_status" not in called:
            return call("shipping_status", order_ref=order_ref)

        if is_policy_q and "knowledge_search" in names and "knowledge_search" not in called:
            return call("knowledge_search", query=last_user)

        # --- growth flow -------------------------------------------------
        if "get_merchant_analytics" in names:
            if "get_merchant_analytics" not in called:
                return call("get_merchant_analytics")
            if "analyze_cross_sell" not in called:
                return call("analyze_cross_sell")
            pair = _first_cross_sell_pair(messages)
            if pair and "draft_campaign" not in called:
                return call(
                    "draft_campaign",
                    name=f"Bundle: {pair} accessory discount",
                    discount_percent=10,
                    max_discount_paise=50000,
                )
            campaign_id = _first_campaign_id(messages)
            if campaign_id and "request_campaign_approval" not in called:
                rationale = "Frequently bought together; a bundle discount should lift attach rate."
                return call(
                    "request_campaign_approval", campaign_id=campaign_id, rationale=rationale
                )

        if wants_products and "catalog_search" in names and "catalog_search" not in called:
            args: dict[str, Any] = {"limit": 5}
            if cat:
                args["category"] = cat
            else:
                args["query"] = _keywords(last_user) or "laptop"
            price_cap = _extract_price(last_user)
            if price_cap:
                args["max_price_paise"] = price_cap
            return call("catalog_search", **args)

        first_product = _first_product_id(messages)
        order_id = _first_order_id(messages)

        if wants_buy and first_product:
            if "cart_add_item" in names and "cart_add_item" not in called:
                return call("cart_add_item", product_id=first_product, quantity=1)
            if "campaign_preview" in names and "campaign_preview" not in called:
                return call("campaign_preview")
            if "save_shipping_details" in names and "save_shipping_details" not in called:
                return call(
                    "save_shipping_details",
                    name="Demo Buyer",
                    email="demo.buyer@example.com",
                    phone="+91-9000000000",
                    line1="1 Demo Street",
                    city="Bengaluru",
                    postal_code="560001",
                    country="IN",
                )
            if "order_create" in names and "order_create" not in called:
                return call("order_create")
            if "payment_request" in names and "payment_request" not in called and order_id:
                return call("payment_request", order_id=order_id)

        return ChatResult(content=_final_text(last_user, last_tool_msg, first_product is not None))


def _extract_price(text: str) -> int | None:
    m = re.search(r"(?:under|below|<|upto|up to|less than)\s*₹?\s*([\d,]+)", text)
    if not m:
        m = re.search(r"₹\s*([\d,]+)", text)
    if not m:
        return None
    return int(m.group(1).replace(",", "")) * 100


_CATEGORY_KEYWORDS = {
    "laptop": "Laptops",
    "notebook": "Laptops",
    "phone": "Smartphones",
    "smartphone": "Smartphones",
    "mouse": "Mice",
    "keyboard": "Keyboards",
    "headphone": "Audio",
    "earbud": "Audio",
    "buds": "Audio",
    "watch": "Wearables",
    "stand": "Accessories",
    "hub": "Accessories",
    "dock": "Accessories",
}


def _category_for(text: str) -> str | None:
    for kw, category in _CATEGORY_KEYWORDS.items():
        if kw in text:
            return category
    return None


def _keywords(text: str) -> str:
    stop = {
        "i",
        "need",
        "a",
        "an",
        "the",
        "for",
        "want",
        "to",
        "buy",
        "me",
        "please",
        "under",
        "below",
        "with",
        "and",
        "of",
        "suitable",
        "some",
        "can",
        "you",
        "recommend",
        "show",
        "find",
        "looking",
        "help",
    }
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in stop and not w.isdigit()]
    return " ".join(words[:4])


def _tool_result(messages: list[ChatMessage], tool_name: str) -> dict[str, Any] | None:
    for m in messages:
        if m.role == "tool" and m.name == tool_name:
            try:
                data = json.loads(m.content)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return data
    return None


def _first_product_id(messages: list[ChatMessage]) -> str | None:
    data = _tool_result(messages, "catalog_search")
    items = data.get("products") if data else None
    return str(items[0]["product_id"]) if items else None


def _first_order_id(messages: list[ChatMessage]) -> str | None:
    data = _tool_result(messages, "order_create")
    return str(data["order_id"]) if data and data.get("order_id") else None


def _extract_order_ref(text: str) -> str | None:
    m = re.search(r"\bord-[0-9a-z]{4,}\b", text, re.IGNORECASE)
    return m.group(0).upper() if m else None


def _first_cross_sell_pair(messages: list[ChatMessage]) -> str | None:
    data = _tool_result(messages, "analyze_cross_sell")
    pairs = data.get("pairs") if data else None
    return str(pairs[0]["a_name"]) if pairs else None


def _first_campaign_id(messages: list[ChatMessage]) -> str | None:
    data = _tool_result(messages, "draft_campaign")
    return str(data["campaign_id"]) if data and data.get("campaign_id") else None


def _final_text(user: str, last_tool: ChatMessage | None, had_product: bool) -> str:
    if last_tool is not None and last_tool.name == "payment_request":
        return (
            "I've prepared the payment. Please confirm to authorise the charge — "
            "the agent cannot complete payment without your approval."
        )
    if last_tool is not None and last_tool.name == "order_create":
        return "Your order is created. Shall I proceed to payment?"
    if last_tool is not None and last_tool.name == "knowledge_search":
        try:
            results = json.loads(last_tool.content).get("results", [])
        except (ValueError, TypeError):
            results = []
        if results:
            body = results[0]["text"].split("\n\n", 1)[-1].strip()
            return f"Here's what the store's policy says: {body}"
        return "I couldn't find anything on that in the store's documents."
    if had_product:
        return (
            "Here are the closest matches from the catalogue. "
            "Let me know which to add to your cart."
        )
    return "I couldn't find a matching product. Tell me a bit more about what you need."


@lru_cache
def get_chat_client() -> ChatClient:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIChatClient(
            api_key=settings.openai_api_key, model=settings.openai_reasoning_model
        )
    return FakeChatClient()
