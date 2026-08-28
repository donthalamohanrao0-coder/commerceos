import pytest

from app.domains.payments.models import Payment
from app.domains.payments.state_machine import (
    InvalidPaymentTransition,
    assert_valid_transition,
    transition,
)


@pytest.mark.parametrize(
    ("frm", "to"),
    [
        ("created", "pending"),
        ("pending", "processing"),
        ("pending", "failed"),
        ("processing", "paid"),
        ("paid", "refund_requested"),
        ("refund_requested", "refund_processing"),
        ("refund_processing", "refunded"),
    ],
)
def test_legal_transitions(frm: str, to: str) -> None:
    assert_valid_transition(frm, to)  # does not raise


@pytest.mark.parametrize(
    ("frm", "to"),
    [
        ("created", "paid"),  # cannot skip pending/processing
        ("pending", "paid"),
        ("paid", "failed"),  # a captured payment cannot fail
        ("failed", "pending"),  # terminal
        ("refunded", "paid"),  # terminal
        ("processing", "refunded"),
    ],
)
def test_illegal_transitions_raise(frm: str, to: str) -> None:
    with pytest.raises(InvalidPaymentTransition):
        assert_valid_transition(frm, to)


def test_transition_mutates_only_on_success() -> None:
    payment = Payment(status="pending")
    transition(payment, "processing")
    assert payment.status == "processing"

    with pytest.raises(InvalidPaymentTransition):
        transition(payment, "refunded")
    assert payment.status == "processing"  # row untouched — fail closed
