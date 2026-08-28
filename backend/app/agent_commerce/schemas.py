"""Request/response schemas for the Agent Commerce API (ADR-006). Every external
payload is validated here — never an arbitrary dict (api-standards.md)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LineItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=50)


class CatalogSearchIn(BaseModel):
    query: str | None = None
    category: str | None = None
    max_price_paise: int | None = Field(default=None, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class QuoteIn(BaseModel):
    items: list[LineItemIn] = Field(min_length=1, max_length=50)


class CreateOrderIn(BaseModel):
    items: list[LineItemIn] = Field(min_length=1, max_length=50)
    buyer_ref: str | None = Field(default=None, max_length=200)


class ProductOut(BaseModel):
    product_id: uuid.UUID
    external_code: str
    name: str
    brand: str | None
    category: str
    description: str | None
    price_paise: int
    currency: str = "INR"
    rating: float | None
    in_stock: bool
    tags: list[str]


class QuoteLineOut(BaseModel):
    product_id: uuid.UUID
    name: str
    quantity: int
    unit_price_paise: int
    line_total_paise: int
    in_stock: bool


class QuoteOut(BaseModel):
    lines: list[QuoteLineOut]
    subtotal_paise: int
    discount_paise: int
    shipping_paise: int
    tax_paise: int
    total_paise: int
    currency: str = "INR"
    campaign: str | None
    discount_reason: str


class OrderOut(BaseModel):
    order_id: uuid.UUID
    order_number: str
    status: str
    subtotal_paise: int
    discount_paise: int
    shipping_paise: int
    tax_paise: int
    total_paise: int
    currency: str = "INR"


class PaymentOut(BaseModel):
    payment_id: uuid.UUID | None = None
    order_id: uuid.UUID
    status: str
    amount_paise: int
    currency: str = "INR"
    provider_order_id: str | None = None
    approval_id: uuid.UUID | None = None
    message: str | None = None
