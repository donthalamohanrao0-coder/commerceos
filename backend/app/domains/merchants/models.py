import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UpdatedAtMixin, UUIDPKMixin


class Organization(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String, nullable=False)


class Merchant(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "merchants"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    merchant_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    business_name: Mapped[str] = mapped_column(String, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    country: Mapped[str] = mapped_column(String, nullable=False, default="IN")
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="Asia/Kolkata")
    gst_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=18.00)
    prices_tax_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pinecone_namespace: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")

    __table_args__ = (
        CheckConstraint("status IN ('active','suspended')", name="ck_merchants_status"),
    )


class User(Base, UUIDPKMixin, TimestampMixin):
    """Mirrors Supabase auth.users.id (as auth_provider_id) once Supabase is wired."""

    __tablename__ = "users"

    auth_provider_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ("
            "'CUSTOMER','MERCHANT_OPERATOR','MERCHANT_ADMIN','PLATFORM_ADMIN','EXTERNAL_AGENT'"
            ")",
            name="ck_users_role",
        ),
    )


class MerchantUser(Base, UUIDPKMixin):
    __tablename__ = "merchant_users"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("merchant_id", "user_id", name="uq_merchant_users_merchant_user"),
        CheckConstraint(
            "role IN ('MERCHANT_OPERATOR','MERCHANT_ADMIN')", name="ck_merchant_users_role"
        ),
    )
