import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UUIDPKMixin


class IdempotencyKey(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "idempotency_keys"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    request_hash: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, nullable=False, default="in_progress")

    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_keys_merchant_op_key",
        ),
        CheckConstraint(
            "status IN ('in_progress','completed','failed')", name="ck_idempotency_keys_status"
        ),
    )
