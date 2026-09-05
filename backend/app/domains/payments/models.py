import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
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

MANDATE_STATUSES = ("pending_authorization", "active", "cancelled", "expired")

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
    # Razorpay Payment Link — the settlement path for a headless AI buyer. The link
    # runs its own internal order, so we keep its id to reconcile with the provider
    # if the webhook is missed.
    payment_link_id: Mapped[str | None] = mapped_column(String)
    payment_link_url: Mapped[str | None] = mapped_column(String)
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


class PaymentMandate(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    """A buyer's standing, pre-authorised spending mandate (AP2/ACP/UAP on real
    rails). A human authorises the ceiling + expiry once; afterwards an external
    AI buyer's confirmed payment charges within it with no checkout hand-off."""

    __tablename__ = "payment_mandates"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False, default="razorpay")
    provider_customer_id: Mapped[str | None] = mapped_column(String)
    provider_token_id: Mapped[str | None] = mapped_column(String)
    provider_order_id: Mapped[str | None] = mapped_column(String)
    method: Mapped[str] = mapped_column(String, nullable=False, default="upi")
    max_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    consent_reference: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending_authorization"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(f"status IN {MANDATE_STATUSES}", name="ck_payment_mandates_status"),
        CheckConstraint("max_amount_paise > 0", name="ck_payment_mandates_amount_positive"),
        Index("idx_payment_mandates_merchant_customer", "merchant_id", "customer_id"),
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
