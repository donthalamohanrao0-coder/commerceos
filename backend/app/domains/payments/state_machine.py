"""Payment state machine (ADR-005, payment-security.md #2, plan.md #13).

Invalid transitions raise InvalidPaymentTransition and never touch the row —
fail closed (agent-guardrails.md #8, system-architecture.md #8).
"""

from app.domains.payments.models import PAYMENT_TRANSITIONS, Payment


class InvalidPaymentTransition(Exception):
    def __init__(self, *, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"cannot transition payment from {from_status!r} to {to_status!r}")


def assert_valid_transition(from_status: str, to_status: str) -> None:
    allowed = PAYMENT_TRANSITIONS.get(from_status, ())
    if to_status not in allowed:
        raise InvalidPaymentTransition(from_status=from_status, to_status=to_status)


def transition(payment: Payment, to_status: str) -> Payment:
    """Mutates `payment.status` only if the transition is legal; otherwise raises
    and leaves the row untouched (caller's transaction is free to continue/rollback)."""
    assert_valid_transition(payment.status, to_status)
    payment.status = to_status
    return payment
