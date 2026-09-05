"""Real Razorpay adapter — used once RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET are set
(Phase 7 credential gate). Secret never leaves the backend (payment-security.md,
secrets-and-data-protection.md #2)."""

import razorpay
from razorpay.utility.utility import Utility

from app.integrations.razorpay.base import (
    RazorpayOrder,
    RazorpayPaymentLink,
    RazorpayProviderState,
)

_PAID_STATES = {"captured", "authorized", "paid"}


class RealRazorpayClient:
    def __init__(self, key_id: str, key_secret: str, webhook_secret: str) -> None:
        self._client = razorpay.Client(auth=(key_id, key_secret))
        self._webhook_secret = webhook_secret

    def create_order(
        self, *, amount_paise: int, receipt: str, notes: dict[str, str]
    ) -> RazorpayOrder:
        result = self._client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "notes": notes,
            }
        )
        return RazorpayOrder(
            provider_order_id=result["id"],
            amount_paise=result["amount"],
            currency=result["currency"],
            receipt=result["receipt"],
        )

    # ------------------------------------------------- recurring / UPI AutoPay
    # Requires the "Recurring Payments" feature enabled on the Razorpay account
    # (test mode included). See docs/architecture/decisions/ADR-010.

    def create_customer(self, *, name: str, email: str, contact: str) -> str:
        result = self._client.customer.create(
            {"name": name, "email": email, "contact": contact, "fail_existing": "0"}
        )
        return str(result["id"])

    def create_mandate_order(
        self,
        *,
        provider_customer_id: str,
        max_amount_paise: int,
        expire_at_unix: int,
        frequency: str,
        notes: dict[str, str],
    ) -> RazorpayOrder:
        result = self._client.order.create(
            {
                "amount": 0,
                "currency": "INR",
                "method": "upi",
                "customer_id": provider_customer_id,
                "token": {
                    "max_amount": max_amount_paise,
                    "expire_at": expire_at_unix,
                    "frequency": frequency,
                },
                "receipt": notes.get("co_mandate_id", "mandate"),
                "notes": notes,
            }
        )
        return RazorpayOrder(
            provider_order_id=result["id"],
            amount_paise=result["amount"],
            currency=result["currency"],
            receipt=result.get("receipt", ""),
        )

    def confirm_mandate_authorization(
        self, *, mandate_order_id: str, provider_payment_id: str
    ) -> str:
        payment = self._client.payment.fetch(provider_payment_id)
        token = payment.get("token_id") or payment.get("token")
        if not token:
            raise ValueError("authorisation payment produced no mandate token")
        return str(token)

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
        result = self._client.payment.createRecurring(
            {
                "email": email,
                "contact": contact,
                "amount": amount_paise,
                "currency": "INR",
                "order_id": provider_order_id,
                "customer_id": provider_customer_id,
                "token": token_id,
                "recurring": True,
                "description": notes.get("description", "CommerceOS recurring charge"),
                "notes": notes,
            }
        )
        return str(result["razorpay_payment_id"])

    def create_payment_link(
        self, *, amount_paise: int, reference_id: str, description: str, notes: dict[str, str]
    ) -> RazorpayPaymentLink:
        result = self._client.payment_link.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "accept_partial": False,
                "reference_id": reference_id,
                "description": description,
                "notes": notes,
                "reminder_enable": False,
                "notify": {"sms": False, "email": False},
            }
        )
        return RazorpayPaymentLink(
            link_id=result["id"],
            short_url=result["short_url"],
            status=result.get("status", "created"),
            amount_paise=result["amount"],
        )

    def reconcile(
        self, *, provider_order_id: str | None, payment_link_id: str | None
    ) -> RazorpayProviderState:
        if payment_link_id:
            link = self._client.payment_link.fetch(payment_link_id)
            pid = None
            for p in link.get("payments") or []:
                if p.get("status") in _PAID_STATES:
                    pid = p.get("payment_id") or p.get("id")
                    break
            return RazorpayProviderState(
                paid=link.get("status") == "paid" or pid is not None,
                status=str(link.get("status", "unknown")),
                provider_payment_id=pid,
            )
        if provider_order_id:
            payments = self._client.order.payments(provider_order_id)
            for p in payments.get("items", []):
                if p.get("status") in _PAID_STATES:
                    return RazorpayProviderState(
                        paid=True, status=str(p["status"]), provider_payment_id=p.get("id")
                    )
            return RazorpayProviderState(paid=False, status="no_captured_payment")
        return RazorpayProviderState(paid=False, status="nothing_to_reconcile")

    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool:
        try:
            Utility().verify_webhook_signature(
                body.decode("utf-8"), signature, self._webhook_secret
            )
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        try:
            self._client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                }
            )
            return True
        except razorpay.errors.SignatureVerificationError:
            return False
