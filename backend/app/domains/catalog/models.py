import uuid

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.model_mixins import TimestampMixin, UpdatedAtMixin, UUIDPKMixin


class Product(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "products"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    external_product_code: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    brand: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    compare_at_price_paise: Mapped[int | None] = mapped_column(BigInteger)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1))
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    cross_sell_product_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    image_key: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "external_product_code", name="uq_products_merchant_external_code"
        ),
        UniqueConstraint("merchant_id", "sku", name="uq_products_merchant_sku"),
        CheckConstraint("price_paise >= 0", name="ck_products_price_nonneg"),
        CheckConstraint("status IN ('active','archived')", name="ck_products_status"),
    )


class ProductVariant(Base, UUIDPKMixin):
    """MVP: every product gets exactly one default variant row, created at import time."""

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String, nullable=False)
    variant_attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")

    __table_args__ = (UniqueConstraint("merchant_id", "sku", name="uq_variants_merchant_sku"),)


class Inventory(Base, UUIDPKMixin, UpdatedAtMixin):
    __tablename__ = "inventory"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=False, unique=True
    )
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("quantity_available >= 0", name="ck_inventory_available_nonneg"),
        CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_nonneg"),
    )
