import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import UpdatedAtMixin, UUIDPKMixin


class Policy(Base, UUIDPKMixin, UpdatedAtMixin):
    """Merchant-configurable policy values (e.g. max_auto_discount_paise). The LLM
    never sees or edits this table directly — only PolicyEngine reads it (Phase 3)."""

    __tablename__ = "policies"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (UniqueConstraint("merchant_id", "key", name="uq_policies_merchant_key"),)
