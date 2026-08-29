"""Real Razorpay adapter — used once RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET are set
(Phase 7 credential gate). Secret never leaves the backend (payment-security.md,
secrets-and-data-protection.md #2)."""

import razorpay
from razorpay.utility.utility import Utility

from app.integrations.razorpay.base import RazorpayOrder, RazorpayPaymentLink


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
