import uuid

from sqlalchemy import ARRAY, BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UpdatedAtMixin, UUIDPKMixin


class Customer(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "customers"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    external_customer_code: Mapped[str | None] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    segment: Mapped[str | None] = mapped_column(String)
    lifetime_value_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preferred_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "external_customer_code", name="uq_customers_merchant_external_code"
        ),
    )
