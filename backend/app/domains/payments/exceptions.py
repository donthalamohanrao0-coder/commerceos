class PaymentNotFound(Exception):
    pass


class PaymentPolicyDenied(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class PaymentVerificationFailed(Exception):
    """The Razorpay Checkout signature / order did not validate — no capture."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)
