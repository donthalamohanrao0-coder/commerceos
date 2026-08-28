"""Supervisor — picks the workflow for a new session (agent-architecture.md #2).

Deterministic keyword routing by default (fast, testable, works without a key);
an LLM can refine it when a client is supplied and the keyword signal is weak.
"""

from __future__ import annotations

import re
from typing import Literal, cast

from app.core.cache import cache_get, cache_key, cache_set
from app.integrations.openai.chat import ChatClient, ChatMessage

Workflow = Literal["shopping", "support", "growth"]

_GROWTH = re.compile(
    r"\b(revenue|grow(th)?|campaign|promo(tion)?|cross[- ]?sell|upsell|attach rate|"
    r"aov|analytics|margin|conversion)\b",
    re.IGNORECASE,
)
_SUPPORT = re.compile(
    r"\b(track|tracking|where('| i)s my|order status|returns?|refund|warranty|"
    r"cancel|delivered|arriv(ed|al)|damaged|complaint|my order|order #?\s*ord)\b",
    re.IGNORECASE,
)


async def classify_workflow(text: str, *, chat_client: ChatClient | None = None) -> Workflow:
    if _GROWTH.search(text):
        return "growth"
    if _SUPPORT.search(text):
        return "support"
    if chat_client is not None and text.strip():
        key = cache_key("workflow", text.strip().lower())
        cached = await cache_get(key)
        if cached in ("shopping", "support", "growth"):
            return cast(Workflow, cached)
        try:
            result = await chat_client.complete(
                messages=[
                    ChatMessage(
                        role="system",
                        content=(
                            "Classify the user's message as exactly one word: "
                            "shopping, support, or growth. Reply with only that word."
                        ),
                    ),
                    ChatMessage(role="user", content=text),
                ],
                tools=[],
            )
            label = (result.content or "").strip().lower()
            if label in ("shopping", "support", "growth"):
                await cache_set(key, label, ttl_seconds=3600)
                return cast(Workflow, label)
        except Exception:  # never let routing fail the request
            pass
    return "shopping"
