"""Machine-readable discovery for the Agent Commerce API (ADR-006).

An external AI buyer that has never seen this merchant can GET
``/.well-known/agent-commerce`` — unauthenticated — and learn the whole
transaction surface: the auth scheme and how to get a key, the scopes, the
absolute endpoint URLs, the ordered ``catalog -> quote -> order -> consent-gated
payment`` flow, the delegated-mandate schema, idempotency rules, and the
server-side guarantees. Transacting still requires a scoped ``ack_live_`` key;
only this manifest is public.

The same capability surface is also exposed over MCP (self-describing tool
schemas) for buyers that speak MCP — this endpoint is the transport-agnostic
HTTP equivalent.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.models import AGENT_API_SCOPES
from app.api.deps import get_session
from app.core.config import get_settings
from app.domains.merchants.models import Merchant
from app.policies.models import Policy

_log = logging.getLogger(__name__)
router = APIRouter(tags=["discovery"])

_SESSION = Depends(get_session)

_SCOPE_DESCRIPTIONS = {
    "catalog:read": "List products and fetch a single product.",
    "catalog:search": "Search the catalogue by query, category, or max price.",
    "quote:create": "Get an authoritative quote (campaign price, discount, shipping, tax, total).",
    "order:create": "Create an order. Requires an Idempotency-Key header.",
    "payment:request": "Request payment for an order (two-phase: probe, then confirm).",
}

_ADVISORY_POLICY_KEYS = (
    "max_transaction_amount_paise",
    "payment_requires_customer_confirmation",
    "max_auto_discount_paise",
)

_FLOW_STEPS = [
    ("GET /catalog | POST /catalog/search", "discover products"),
    ("POST /quote", "authoritative price: campaign, discount, shipping, tax"),
    ("POST /orders", "create order (Idempotency-Key required)"),
    ("POST /orders/{id}/payment?confirmed=false", "probe: returns amount, no charge"),
    ("POST /orders/{id}/payment?confirmed=true", "consent; optional mandate; -> checkout_url"),
    ("human opens checkout_url", "Checkout runs; signed result settles server-side"),
    ("GET /orders/{id}", "poll until status = paid (or webhook / reconcile)"),
]
_FLOW = [
    {"step": i, "call": call, "does": does}
    for i, (call, does) in enumerate(_FLOW_STEPS, start=1)
]

_MANDATE_SCHEMA = {
    "consent_reference": "string — your delegation id, recorded verbatim in the audit trail",
    "max_amount_paise": "integer — hard ceiling; the backend refuses to charge above it",
    "expires_at": "RFC 3339 timestamp — the backend refuses to charge after it",
}

_GUARANTEES = [
    "Every money action passes schema validation, auth, scope check, tenant isolation "
    "(Postgres RLS), a deterministic policy check, an amount bound and a bounded-execution "
    "check before it runs.",
    "The unconfirmed payment call never charges.",
    "Payment status comes only from a server-verified Razorpay signature, never the client.",
    "A missed callback or webhook is recoverable: the merchant reconciles against "
    "Razorpay directly.",
    "Every request made with a key is written to an append-only audit trail the "
    "merchant can review.",
]


async def _advisory_limits(session: AsyncSession) -> dict[str, object]:
    """Best-effort: the demo merchant's actual configured limits, so a buyer knows
    them up front. Never raises — discovery must not depend on merchant state."""
    try:
        code = get_settings().demo_merchant_code
        merchant = await session.scalar(select(Merchant).where(Merchant.merchant_code == code))
        if merchant is None:
            return {}
        rows = await session.scalars(
            select(Policy).where(
                Policy.merchant_id == merchant.id,
                Policy.key.in_(_ADVISORY_POLICY_KEYS),
            )
        )
        return {row.key: row.value for row in rows}
    except Exception:  # noqa: BLE001 — discovery is public and must always answer
        _log.warning("well-known: advisory limits lookup failed", exc_info=True)
        return {}


async def _merchant_block(session: AsyncSession, code: str) -> dict:
    try:
        merchant = await session.scalar(select(Merchant).where(Merchant.merchant_code == code))
        if merchant is not None:
            return {
                "code": merchant.merchant_code,
                "name": merchant.business_name,
                "currency": merchant.currency,
                "country": merchant.country,
            }
    except Exception:  # noqa: BLE001
        _log.warning("well-known: merchant block lookup failed", exc_info=True)
    return {"code": code, "currency": "INR", "country": "IN"}


@router.get("/.well-known/agent-commerce", include_in_schema=False)
async def agent_commerce_manifest(session: AsyncSession = _SESSION) -> dict:
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    api = f"{base}{settings.api_prefix}/agent-commerce"

    limits: dict[str, object] = {
        "rate_limit_per_minute_default": 60,
        "note": "Advisory only. Every limit is enforced server-side regardless of the request.",
    }
    limits.update(await _advisory_limits(session))

    return {
        "protocol": "agent-commerce",
        "spec_version": "0.1",
        "aligned_with": ["AP2", "ACP", "UAP"],
        "description": (
            "Discover and transact with this merchant as an autonomous AI buyer: "
            "catalog -> authoritative quote -> idempotent order -> consent-gated payment "
            "on Razorpay rails. Every money action is bounded, gated and audited."
        ),
        "merchant": await _merchant_block(session, settings.demo_merchant_code),
        "authentication": {
            "type": "http-bearer",
            "header": "Authorization: Bearer <token>",
            "token_format": "ack_live_<hex>",
            "how_to_obtain": (
                "The merchant issues a scoped, rate-limited key per buyer in "
                "Console -> Agent keys. Only its SHA-256 hash is stored."
            ),
        },
        "scopes": {s: _SCOPE_DESCRIPTIONS[s] for s in AGENT_API_SCOPES},
        "non_grantable": ["refund", "discount-override"],
        "mcp": {
            "available": True,
            "transports": ["stdio", "http"],
            "note": "Same capability surface as self-describing MCP tools, for MCP buyers.",
        },
        "endpoints": {
            "openapi": f"{api}/openapi.json",
            "catalog_list": f"{api}/catalog",
            "catalog_get": f"{api}/catalog/{{product_id}}",
            "catalog_search": f"{api}/catalog/search",
            "quote": f"{api}/quote",
            "order_create": f"{api}/orders",
            "order_get": f"{api}/orders/{{order_id}}",
            "payment_request": f"{api}/orders/{{order_id}}/payment",
        },
        "flow": _FLOW,
        "mandate_schema": _MANDATE_SCHEMA,
        "idempotency": {
            "header": "Idempotency-Key",
            "required_on": [
                "POST /orders",
                "POST /orders/{order_id}/payment?confirmed=true",
            ],
            "replay": "same key + same payload replays the original response; "
            "same key + different payload is a 409",
        },
        "limits": limits,
        "guarantees": _GUARANTEES,
    }
