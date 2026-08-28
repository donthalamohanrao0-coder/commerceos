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

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        """Validate the signature Razorpay Checkout returns to the browser after a
        successful payment (hmac_sha256(order_id|payment_id, key_secret))."""
        ...
