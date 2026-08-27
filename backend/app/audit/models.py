import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UUIDPKMixin


class AuditEvent(Base, UUIDPKMixin, TimestampMixin):
    """Append-only. UPDATE/DELETE grants are revoked at the DB role level in the
    RLS migration (Phase 5) — immutability is enforced at the database, not just app code."""

    __tablename__ = "audit_events"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id")
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    input: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    policy_decision: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('customer','agent','merchant_user','system','external_agent')",
            name="ck_audit_events_actor_type",
        ),
        Index("idx_audit_events_merchant_created", "merchant_id", "created_at"),
        Index("idx_audit_events_order", "order_id"),
    )
