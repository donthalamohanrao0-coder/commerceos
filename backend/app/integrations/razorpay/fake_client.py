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
        # recurring / UPI AutoPay simulation
        self.customers: dict[str, dict[str, str]] = {}
        self.mandate_orders: dict[str, dict[str, object]] = {}  # order_id -> {customer, max_amount}
        self.tokens: dict[str, dict[str, object]] = {}  # token_id -> {customer, max_amount, active}
        self.recurring_charges: list[dict[str, object]] = []

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

    # ------------------------------------------------- recurring / UPI AutoPay

    def create_customer(self, *, name: str, email: str, contact: str) -> str:
        cid = f"cust_fake_{uuid.uuid4().hex[:14]}"
        self.customers[cid] = {"name": name, "email": email, "contact": contact}
        return cid

    def create_mandate_order(
        self,
        *,
        provider_customer_id: str,
        max_amount_paise: int,
        expire_at_unix: int,
        frequency: str,
        notes: dict[str, str],
    ) -> RazorpayOrder:
        oid = f"order_fake_{uuid.uuid4().hex[:14]}"
        self.mandate_orders[oid] = {
            "customer": provider_customer_id,
            "max_amount": max_amount_paise,
            "expire_at": expire_at_unix,
            "frequency": frequency,
        }
        order = RazorpayOrder(
            provider_order_id=oid, amount_paise=0, currency="INR", receipt="mandate"
        )
        self.created_orders[oid] = order
        return order

    def authorize_mandate(self, mandate_order_id: str) -> str:
        """Test helper: simulate the human approving the mandate in their UPI app.
        Mints a token bound to the order's customer + ceiling and returns its id."""
        spec = self.mandate_orders[mandate_order_id]
        token_id = f"token_fake_{uuid.uuid4().hex[:14]}"
        self.tokens[token_id] = {
            "customer": spec["customer"],
            "max_amount": spec["max_amount"],
            "active": True,
        }
        return token_id

    def confirm_mandate_authorization(
        self, *, mandate_order_id: str, provider_payment_id: str
    ) -> str:
        # Simulates the human having approved the mandate in their UPI app during
        # the hosted authorisation payment — mints the token now.
        return self.authorize_mandate(mandate_order_id)

    def cancel_token(self, token_id: str) -> None:
        """Test helper: simulate token.cancelled / a revoked mandate."""
        if token_id in self.tokens:
            self.tokens[token_id]["active"] = False

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
        token = self.tokens.get(token_id)
        if token is None or not token.get("active"):
            raise ValueError(f"token {token_id} is not active")
        ceiling = int(str(token["max_amount"]))
        if amount_paise > ceiling:  # the rail refuses an over-ceiling charge
            raise ValueError(f"amount {amount_paise} exceeds mandate max {ceiling}")
        pid = f"pay_fake_{uuid.uuid4().hex[:14]}"
        self.recurring_charges.append(
            {"payment_id": pid, "order_id": provider_order_id, "amount": amount_paise}
        )
        self.paid_orders.add(provider_order_id)
        return pid

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
