"""Request/response schemas for the Agent Commerce API (ADR-006). Every external
payload is validated here — never an arbitrary dict (api-standards.md)."""

from __future__ import annotations

import uuid
from datetime import datetime

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


class BuyerIn(BaseModel):
    """The end customer the AI buyer is purchasing for. Stored as a Customer and,
    as a structured shipping address, on the order."""

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    phone: str = Field(min_length=4, max_length=20)
    line1: str = Field(min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(default="IN", max_length=60)


class CreateOrderIn(BaseModel):
    items: list[LineItemIn] = Field(min_length=1, max_length=50)
    buyer_ref: str | None = Field(default=None, max_length=200)
    buyer: BuyerIn | None = None


class PaymentMandateIn(BaseModel):
    """The buyer agent's delegated spending authorisation (the AP2/ACP/UAP model).
    Optional; when present the backend refuses to charge outside it and records it
    verbatim in the PAYMENT_CREATED audit row."""

    consent_reference: str = Field(min_length=1, max_length=200)
    max_amount_paise: int = Field(ge=1)
    expires_at: datetime


class PaymentRequestIn(BaseModel):
    mandate: PaymentMandateIn | None = None


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
    shipping_address: dict | None = None


class PaymentOut(BaseModel):
    payment_id: uuid.UUID | None = None
    order_id: uuid.UUID
    status: str
    amount_paise: int
    currency: str = "INR"
    provider_order_id: str | None = None
    approval_id: uuid.UUID | None = None
    message: str | None = None
    # Hosted Razorpay page to complete the charge (external AI buyer has no browser
    # to run Checkout). Paying it fires the webhook that settles the order.
    payment_link_url: str | None = None
    payment_link_id: str | None = None
