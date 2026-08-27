import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UUIDPKMixin


class Campaign(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "campaigns"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    external_campaign_code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    discount_type: Mapped[str] = mapped_column(String, nullable=False)
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    discount_fixed_paise: Mapped[int | None] = mapped_column(BigInteger)
    max_discount_paise: Mapped[int | None] = mapped_column(BigInteger)
    requires_merchant_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "external_campaign_code", name="uq_campaigns_merchant_code"
        ),
        CheckConstraint(
            "status IN ('draft','active','paused','archived')", name="ck_campaigns_status"
        ),
        CheckConstraint(
            "discount_type IN ('percentage','fixed')", name="ck_campaigns_discount_type"
        ),
    )


class CampaignRule(Base, UUIDPKMixin):
    __tablename__ = "campaign_rules"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String, nullable=False)
    rule_value: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "rule_type IN ("
            "'eligible_category','eligible_segment','min_order_value','min_category_purchase'"
            ")",
            name="ck_campaign_rules_type",
        ),
    )


class Coupon(Base, UUIDPKMixin):
    __tablename__ = "coupons"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id")
    )
    code: Mapped[str] = mapped_column(String, nullable=False)
    max_redemptions: Mapped[int | None] = mapped_column(Integer)
    redemptions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("merchant_id", "code", name="uq_coupons_merchant_code"),)
