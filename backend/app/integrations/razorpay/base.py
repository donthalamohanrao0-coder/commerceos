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


@dataclass(frozen=True)
class RazorpayPaymentLink:
    link_id: str
    short_url: str
    status: str
    amount_paise: int


@dataclass(frozen=True)
class RazorpayProviderState:
    """A snapshot of what the provider believes, used to reconcile when a webhook
    was missed. `paid` is true if any payment on the order/link is captured."""

    paid: bool
    status: str
    provider_payment_id: str | None = None


class RazorpayClient(Protocol):
    def create_order(
        self, *, amount_paise: int, receipt: str, notes: dict[str, str]
    ) -> RazorpayOrder: ...

    # ---------------------------------------------------- recurring / UPI AutoPay
    def create_customer(self, *, name: str, email: str, contact: str) -> str:
        """Register the buyer as a Razorpay customer; returns the `cust_...` id.
        Needed before a mandate order — the token is bound to a customer."""
        ...

    def create_mandate_order(
        self,
        *,
        provider_customer_id: str,
        max_amount_paise: int,
        expire_at_unix: int,
        frequency: str,
        notes: dict[str, str],
    ) -> RazorpayOrder:
        """The zero-amount authorisation order that carries the `token` block
        (max_amount, expire_at, frequency). A human runs Checkout against it once
        with `recurring: 1`; that registers the mandate and mints a token."""
        ...

    def confirm_mandate_authorization(
        self, *, mandate_order_id: str, provider_payment_id: str
    ) -> str:
        """After a human completes the authorisation payment, resolve the minted
        mandate token id (`token_...`). Raises if no token was created."""
        ...

    def charge_recurring(
        self,
        *,
        provider_order_id: str,
        provider_customer_id: str,
        token_id: str,
        amount_paise: int,
        email: str,
        contact: str,
        notes: dict[str, str],
    ) -> str:
        """Charge a fresh order against an existing mandate token, no browser.
        Returns the `pay_...` id. Rejected by the provider if amount_paise exceeds
        the mandate's max_amount."""
        ...

    def create_payment_link(
        self, *, amount_paise: int, reference_id: str, description: str, notes: dict[str, str]
    ) -> RazorpayPaymentLink:
        """A hosted Razorpay page for one order amount. When paid (test card
        4111 1111 1111 1111) Razorpay fires `payment_link.paid` + `payment.captured`
        webhooks carrying `notes`, which settle the CommerceOS payment. This is the
        settlement path for an external AI buyer that has no browser to run Checkout."""
        ...

    def reconcile(
        self, *, provider_order_id: str | None, payment_link_id: str | None
    ) -> RazorpayProviderState:
        """Ask Razorpay directly whether this order / payment link has been paid —
        the fallback when the settlement webhook never arrived."""
        ...

    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool: ...

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        """Validate the signature Razorpay Checkout returns to the browser after a
        successful payment (hmac_sha256(order_id|payment_id, key_secret))."""
        ...
