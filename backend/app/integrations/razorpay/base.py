"""Capability seam for the payment provider (harness-engineering-patterns.md #3):
one interface, swappable providers, zero consumer forks between fake and real."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RazorpayOrder:
    provider_order_id: str
    amount_paise: int
    currency: str
    receipt: str


class RazorpayClient(Protocol):
    def create_order(
        self, *, amount_paise: int, receipt: str, notes: dict[str, str]
    ) -> RazorpayOrder: ...

    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool: ...
