import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UpdatedAtMixin, UUIDPKMixin

PAYMENT_STATUSES = (
    "created",
    "pending",
    "processing",
    "paid",
    "failed",
    "refund_requested",
    "refund_processing",
    "refunded",
)

# Valid transitions, enforced in state_machine.py (Phase 3) — the DB CHECK above only
# constrains the domain of the column, not legal transitions between values.
PAYMENT_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "created": ("pending",),
    "pending": ("processing", "failed"),
    "processing": ("paid", "failed"),
    "paid": ("refund_requested",),
    "failed": (),
    "refund_requested": ("refund_processing",),
    "refund_processing": ("refunded",),
    "refunded": (),
}


class Payment(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "payments"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="created")
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    provider: Mapped[str] = mapped_column(String, nullable=False, default="razorpay")
    provider_order_id: Mapped[str | None] = mapped_column(String)
    provider_payment_id: Mapped[str | None] = mapped_column(String)
    razorpay_signature_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    failure_reason: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        CheckConstraint(f"status IN {PAYMENT_STATUSES}", name="ck_payments_status"),
        CheckConstraint("amount_paise > 0", name="ck_payments_amount_positive"),
        Index(
            "uq_payments_provider_order",
            "provider_order_id",
            unique=True,
            postgresql_where=text("provider_order_id IS NOT NULL"),
        ),
    )


class PaymentAttempt(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "payment_attempts"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String)
    provider_error_code: Mapped[str | None] = mapped_column(String)
    provider_error_description: Mapped[str | None] = mapped_column(String)
    idempotency_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("idempotency_keys.id")
    )

    __table_args__ = (
        UniqueConstraint("payment_id", "attempt_number", name="uq_payment_attempts_payment_number"),
        CheckConstraint(
            "status IN ('initiated','pending','succeeded','failed','timed_out')",
            name="ck_payment_attempts_status",
        ),
    )
