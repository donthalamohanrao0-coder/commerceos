"""FakeRazorpayClient — lets Phases 1-7 build/test the full checkout flow before
real Razorpay test keys arrive. Same interface as RealRazorpayClient (base.py seam)."""

import hashlib
import hmac
import json
import uuid

from app.integrations.razorpay.base import (
    RazorpayOrder,
    RazorpayPaymentLink,
    RazorpayProviderState,
)

FAKE_WEBHOOK_SECRET = "fake-local-webhook-secret"


class FakeRazorpayClient:
    def __init__(self) -> None:
        self.created_orders: dict[str, RazorpayOrder] = {}
        self.created_links: dict[str, RazorpayPaymentLink] = {}
        self.paid_links: set[str] = set()
        self.paid_orders: set[str] = set()

    def create_order(
        self, *, amount_paise: int, receipt: str, notes: dict[str, str]
    ) -> RazorpayOrder:
        order = RazorpayOrder(
            provider_order_id=f"order_fake_{uuid.uuid4().hex[:14]}",
            amount_paise=amount_paise,
            currency="INR",
            receipt=receipt,
        )
        self.created_orders[order.provider_order_id] = order
        return order

    def create_payment_link(
        self, *, amount_paise: int, reference_id: str, description: str, notes: dict[str, str]
    ) -> RazorpayPaymentLink:
        link_id = f"plink_fake_{uuid.uuid4().hex[:14]}"
        link = RazorpayPaymentLink(
            link_id=link_id,
            short_url=f"https://rzp.test/i/{link_id}",
            status="created",
            amount_paise=amount_paise,
        )
        self.created_links[link_id] = link
        return link

    def mark_link_paid(self, link_id: str) -> None:
        """Test helper: simulate the buyer completing the hosted payment link."""
        self.paid_links.add(link_id)

    def reconcile(
        self, *, provider_order_id: str | None, payment_link_id: str | None
    ) -> RazorpayProviderState:
        if payment_link_id and payment_link_id in self.paid_links:
            return RazorpayProviderState(
                paid=True, status="paid", provider_payment_id=f"pay_fake_{payment_link_id[-10:]}"
            )
        if provider_order_id and provider_order_id in self.paid_orders:
            return RazorpayProviderState(paid=True, status="captured")
        return RazorpayProviderState(paid=False, status="no_captured_payment")

    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool:
        expected = hmac.new(FAKE_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        expected = hmac.new(
            FAKE_WEBHOOK_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def sign_payment(order_id: str, payment_id: str) -> str:
        """Test helper: the signature Razorpay Checkout would hand back."""
        return hmac.new(
            FAKE_WEBHOOK_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def sign_payload(payload: dict[str, object]) -> tuple[bytes, str]:
        """Test helper: produce a (body, signature) pair a test can POST to the
        webhook endpoint, simulating a genuine Razorpay-signed webhook locally."""
        body = json.dumps(payload).encode()
        signature = hmac.new(FAKE_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return body, signature
