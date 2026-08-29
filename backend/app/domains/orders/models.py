import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UpdatedAtMixin, UUIDPKMixin

ORDER_STATUSES = (
    "created",
    "payment_pending",
    "payment_processing",
    "paid",
    "fulfilled",
    "failed",
    "cancelled",
    "refund_requested",
    "refund_processing",
    "refunded",
)


class Order(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "orders"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id")
    )
    cart_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("carts.id"))
    order_number: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="created")
    subtotal_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    shipping_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id")
    )
    source: Mapped[str] = mapped_column(String, nullable=False, default="customer")
    agent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_sessions.id")
    )
    # {name, phone, email, line1, line2, city, state, postal_code, country}
    shipping_address: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("merchant_id", "order_number", name="uq_orders_merchant_number"),
        CheckConstraint(f"status IN {ORDER_STATUSES}", name="ck_orders_status"),
        CheckConstraint(
            "source IN ('customer','ai_assisted','external_ai_buyer')", name="ck_orders_source"
        ),
    )


class OrderItem(Base, UUIDPKMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=False
    )
    product_name_snapshot: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),)
