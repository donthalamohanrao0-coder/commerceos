"""Merchant console — read models for the operator UI.

Every route is tenant-scoped through a resolved Supabase identity. These are
read-only projections; the console mutates state only through the existing agent
approval endpoint (``POST /agent/sessions/{id}/approvals/{approval_id}``), so the
"AI proposes, backend decides, a human gates" path stays the single code path.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import AgentAction, AgentMessage, AgentSession
from app.analytics.service import AnalyticsService
from app.api.deps import get_identity_tenant_session, get_merchant_identity
from app.api.envelope import ok
from app.approvals.models import ApprovalRequest
from app.audit.models import AuditEvent
from app.domains.campaigns.models import Campaign
from app.domains.catalog.models import Inventory, Product, ProductVariant
from app.domains.customers.models import Customer
from app.domains.merchants.models import Merchant
from app.domains.orders.models import Order, OrderItem
from app.domains.payments.models import Payment
from app.identity.service import MerchantIdentity
from app.knowledge.ingestion.pipeline import KnowledgeIngestionService
from app.knowledge.models import Document, DocumentVersion
from app.knowledge.retrieval.retriever import KnowledgeRetriever
from app.policies.models import Policy

router = APIRouter(prefix="/console", tags=["console"])
_log = logging.getLogger(__name__)

_IDENTITY = Depends(get_merchant_identity)
_SESSION = Depends(get_identity_tenant_session)


@router.get("/metrics")
async def metrics(
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    snap = await AnalyticsService(session).merchant_snapshot(identity.merchant_id, top_n=5)
    return ok(
        {
            "revenue_paise": snap.revenue_paise,
            "order_count": snap.order_count,
            "paid_order_count": snap.paid_order_count,
            "aov_paise": snap.aov_paise,
            "top_products": [
                {
                    "product_id": str(p.product_id),
                    "name": p.name,
                    "category": p.category,
                    "units_sold": p.units_sold,
                    "revenue_paise": p.revenue_paise,
                }
                for p in snap.top_products
            ],
            "cross_sell_pairs": [
                {
                    "a_name": c.a_name,
                    "b_name": c.b_name,
                    "co_occurrence": c.co_occurrence,
                    "attach_rate": round(c.attach_rate, 3),
                }
                for c in snap.cross_sell_pairs
            ],
            "category_revenue": [
                {"category": name, "revenue_paise": value} for name, value in snap.category_revenue
            ],
        }
    )


@router.get("/activity")
async def activity(
    limit: int = Query(default=25, ge=1, le=100),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    sessions = list(
        await session.scalars(
            select(AgentSession)
            .where(AgentSession.merchant_id == identity.merchant_id)
            .order_by(AgentSession.started_at.desc())
            .limit(limit)
        )
    )
    ids = [s.id for s in sessions]
    action_counts: dict[uuid.UUID, int] = {}
    msg_counts: dict[uuid.UUID, int] = {}
    if ids:
        for sid, count in await session.execute(
            select(AgentAction.session_id, func.count())
            .where(AgentAction.session_id.in_(ids))
            .group_by(AgentAction.session_id)
        ):
            action_counts[sid] = count
        for sid, count in await session.execute(
            select(AgentMessage.session_id, func.count())
            .where(AgentMessage.session_id.in_(ids))
            .group_by(AgentMessage.session_id)
        ):
            msg_counts[sid] = count

    return ok(
        {
            "sessions": [
                {
                    "session_id": str(s.id),
                    "workflow": s.workflow,
                    "status": s.status,
                    "channel": s.channel,
                    "started_at": s.started_at.isoformat(),
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "message_count": msg_counts.get(s.id, 0),
                    "action_count": action_counts.get(s.id, 0),
                }
                for s in sessions
            ]
        }
    )


@router.get("/activity/{session_id}")
async def activity_detail(
    session_id: uuid.UUID,
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    agent_session = await session.get(AgentSession, session_id)
    if agent_session is None or agent_session.merchant_id != identity.merchant_id:
        return ok({"session": None, "messages": [], "actions": []})

    messages = list(
        await session.scalars(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.asc())
        )
    )
    actions = list(
        await session.scalars(
            select(AgentAction)
            .where(AgentAction.session_id == session_id)
            .order_by(AgentAction.created_at.asc())
        )
    )
    return ok(
        {
            "session": {
                "session_id": str(agent_session.id),
                "workflow": agent_session.workflow,
                "status": agent_session.status,
                "channel": agent_session.channel,
                "started_at": agent_session.started_at.isoformat(),
            },
            "messages": [
                {
                    "role": m.role,
                    "content_type": m.content_type,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ],
            "actions": [
                {
                    "node_name": a.node_name,
                    "tool_name": a.tool_name,
                    "status": a.status,
                    "input": a.input,
                    "output": a.output,
                    "policy_decision": a.policy_decision,
                    "duration_ms": a.duration_ms,
                    "created_at": a.created_at.isoformat(),
                }
                for a in actions
            ],
        }
    )


@router.get("/approvals")
async def approvals(
    status: str = Query(default="pending"),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    rows = list(
        await session.scalars(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.merchant_id == identity.merchant_id,
                ApprovalRequest.status == status,
            )
            .order_by(ApprovalRequest.created_at.desc())
            .limit(50)
        )
    )
    workflows: dict[uuid.UUID, str] = {}
    orders: dict[uuid.UUID, Order] = {}
    session_ids = [r.session_id for r in rows if r.session_id]
    order_ids = [r.order_id for r in rows if r.order_id]
    if session_ids:
        for s in await session.scalars(
            select(AgentSession).where(AgentSession.id.in_(session_ids))
        ):
            workflows[s.id] = s.workflow
    if order_ids:
        for o in await session.scalars(select(Order).where(Order.id.in_(order_ids))):
            orders[o.id] = o

    def _order_view(order_id: uuid.UUID | None) -> dict | None:
        o = orders.get(order_id) if order_id else None
        if o is None:
            return None
        return {
            "order_id": str(o.id),
            "order_number": o.order_number,
            "total_paise": o.total_paise,
            "discount_paise": o.discount_paise,
            "status": o.status,
        }

    return ok(
        {
            "approvals": [
                {
                    "approval_id": str(r.id),
                    "session_id": str(r.session_id) if r.session_id else None,
                    "workflow": workflows.get(r.session_id) if r.session_id else None,
                    "requested_action": r.requested_action,
                    "requested_by": r.requested_by,
                    "status": r.status,
                    "payload": r.payload,
                    "created_at": r.created_at.isoformat(),
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                    "order": _order_view(r.order_id),
                }
                for r in rows
            ]
        }
    )


@router.get("/audit")
async def audit(
    limit: int = Query(default=50, ge=1, le=200),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    rows = list(
        await session.scalars(
            select(AuditEvent)
            .where(AuditEvent.merchant_id == identity.merchant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
    )
    return ok(
        {
            "events": [
                {
                    "id": str(e.id),
                    "actor_type": e.actor_type,
                    "actor_id": e.actor_id,
                    "action": e.action,
                    "session_id": str(e.session_id) if e.session_id else None,
                    "order_id": str(e.order_id) if e.order_id else None,
                    "policy_decision": e.policy_decision,
                    "created_at": e.created_at.isoformat(),
                }
                for e in rows
            ]
        }
    )


# --------------------------------------------------------------- catalog / customers


@router.get("/products")
async def products(
    limit: int = Query(default=200, ge=1, le=500),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    rows = list(
        await session.scalars(
            select(Product)
            .where(Product.merchant_id == identity.merchant_id)
            .order_by(Product.name.asc())
            .limit(limit)
        )
    )
    return ok(
        {
            "products": [
                {
                    "id": str(p.id),
                    "sku": p.sku,
                    "name": p.name,
                    "category": p.category,
                    "brand": p.brand,
                    "description": p.description,
                    "price_paise": p.price_paise,
                    "compare_at_price_paise": p.compare_at_price_paise,
                    "rating": float(p.rating) if p.rating is not None else None,
                    "review_count": p.review_count,
                    "image_key": p.image_key,
                    "tags": list(p.tags or []),
                    "status": p.status,
                }
                for p in rows
            ]
        }
    )


@router.get("/customers")
async def customers(
    limit: int = Query(default=200, ge=1, le=500),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    rows = list(
        await session.scalars(
            select(Customer)
            .where(Customer.merchant_id == identity.merchant_id)
            .order_by(Customer.lifetime_value_paise.desc())
            .limit(limit)
        )
    )
    return ok(
        {
            "customers": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "email": c.email,
                    "city": c.city,
                    "segment": c.segment,
                    "lifetime_value_paise": c.lifetime_value_paise,
                    "orders_count": c.orders_count,
                    "preferred_categories": list(c.preferred_categories or []),
                }
                for c in rows
            ]
        }
    )


# --------------------------------------------------------------- orders / payments


@router.get("/orders")
async def orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    stmt = select(Order).where(Order.merchant_id == identity.merchant_id)
    if status:
        stmt = stmt.where(Order.status == status)
    rows = list(await session.scalars(stmt.order_by(Order.created_at.desc()).limit(limit)))

    counts: dict[uuid.UUID, int] = {}
    if rows:
        for oid, n in await session.execute(
            select(OrderItem.order_id, func.count())
            .where(OrderItem.order_id.in_([o.id for o in rows]))
            .group_by(OrderItem.order_id)
        ):
            counts[oid] = n

    return ok(
        {
            "orders": [
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "status": o.status,
                    "source": o.source,
                    "subtotal_paise": o.subtotal_paise,
                    "discount_paise": o.discount_paise,
                    "shipping_paise": o.shipping_paise,
                    "tax_paise": o.tax_paise,
                    "total_paise": o.total_paise,
                    "item_count": counts.get(o.id, 0),
                    "created_at": o.created_at.isoformat(),
                }
                for o in rows
            ]
        }
    )


@router.get("/payments")
async def payments(
    limit: int = Query(default=100, ge=1, le=500),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    rows = list(
        await session.scalars(
            select(Payment)
            .where(Payment.merchant_id == identity.merchant_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
    )
    order_numbers: dict[uuid.UUID, str] = {}
    if rows:
        for oid, num in await session.execute(
            select(Order.id, Order.order_number).where(Order.id.in_([p.order_id for p in rows]))
        ):
            order_numbers[oid] = num

    return ok(
        {
            "payments": [
                {
                    "id": str(p.id),
                    "order_number": order_numbers.get(p.order_id),
                    "status": p.status,
                    "amount_paise": p.amount_paise,
                    "currency": p.currency,
                    "provider": p.provider,
                    "provider_order_id": p.provider_order_id,
                    "provider_payment_id": p.provider_payment_id,
                    "signature_verified": p.razorpay_signature_verified,
                    "failure_reason": p.failure_reason,
                    "created_at": p.created_at.isoformat(),
                }
                for p in rows
            ]
        }
    )


# --------------------------------------------------------------- campaigns / settings


@router.get("/campaigns")
async def campaigns(
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    rows = list(
        await session.scalars(
            select(Campaign)
            .where(Campaign.merchant_id == identity.merchant_id)
            .order_by(Campaign.created_at.desc())
            .limit(200)
        )
    )
    return ok(
        {
            "campaigns": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "external_campaign_code": c.external_campaign_code,
                    "status": c.status,
                    "discount_type": c.discount_type,
                    "discount_percent": float(c.discount_percent)
                    if c.discount_percent is not None
                    else None,
                    "discount_fixed_paise": c.discount_fixed_paise,
                    "max_discount_paise": c.max_discount_paise,
                    "requires_merchant_approval": c.requires_merchant_approval,
                    "created_at": c.created_at.isoformat(),
                }
                for c in rows
            ]
        }
    )


@router.get("/settings")
async def settings(
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    merchant = await session.get(Merchant, identity.merchant_id)
    policy_rows = list(
        await session.scalars(select(Policy).where(Policy.merchant_id == identity.merchant_id))
    )
    return ok(
        {
            "merchant": {
                "id": str(merchant.id),
                "merchant_code": merchant.merchant_code,
                "business_name": merchant.business_name,
                "legal_name": merchant.legal_name,
                "currency": merchant.currency,
                "country": merchant.country,
                "timezone": merchant.timezone,
                "gst_percent": float(merchant.gst_percent),
                "prices_tax_inclusive": merchant.prices_tax_inclusive,
                "status": merchant.status,
            }
            if merchant
            else None,
            "policies": [{"key": p.key, "value": p.value} for p in policy_rows],
        }
    )


# --------------------------------------------------------------- catalog writes


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    brand: str | None = None
    description: str | None = None
    price_paise: int = Field(gt=0)
    compare_at_price_paise: int | None = Field(default=None, gt=0)
    tags: list[str] = Field(default_factory=list)
    stock: int = Field(default=25, ge=0)


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    brand: str | None = None
    description: str | None = None
    price_paise: int | None = Field(default=None, gt=0)
    compare_at_price_paise: int | None = Field(default=None, gt=0)
    tags: list[str] | None = None
    status: Literal["active", "archived"] | None = None


def _product_view(p: Product) -> dict:
    return {
        "id": str(p.id),
        "sku": p.sku,
        "name": p.name,
        "category": p.category,
        "brand": p.brand,
        "description": p.description,
        "price_paise": p.price_paise,
        "compare_at_price_paise": p.compare_at_price_paise,
        "rating": float(p.rating) if p.rating is not None else None,
        "review_count": p.review_count,
        "image_key": p.image_key,
        "tags": list(p.tags or []),
        "status": p.status,
    }


async def _owned_product(
    session: AsyncSession, merchant_id: uuid.UUID, product_id: uuid.UUID
) -> Product:
    product = await session.get(Product, product_id)
    if product is None or product.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.post("/products", status_code=201)
async def create_product(
    body: ProductCreate,
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    async with session.begin():
        code = f"NT-MAN-{uuid.uuid4().hex[:6].upper()}"
        product = Product(
            id=uuid.uuid4(),
            merchant_id=identity.merchant_id,
            external_product_code=code,
            sku=code,
            name=body.name,
            category=body.category,
            brand=body.brand,
            description=body.description,
            price_paise=body.price_paise,
            compare_at_price_paise=body.compare_at_price_paise,
            rating=None,
            review_count=0,
            tags=body.tags,
            image_key=None,
            status="active",
        )
        session.add(product)
        await session.flush()

        variant = ProductVariant(
            id=uuid.uuid4(),
            product_id=product.id,
            merchant_id=identity.merchant_id,
            sku=code,
            price_paise=body.price_paise,
        )
        session.add(variant)
        await session.flush()

        session.add(
            Inventory(
                id=uuid.uuid4(),
                merchant_id=identity.merchant_id,
                product_variant_id=variant.id,
                quantity_available=body.stock,
                quantity_reserved=0,
            )
        )
    return ok(_product_view(product))


@router.patch("/products/{product_id}")
async def update_product(
    product_id: uuid.UUID,
    body: ProductPatch,
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    async with session.begin():
        product = await _owned_product(session, identity.merchant_id, product_id)
        fields = body.model_dump(exclude_unset=True)
        for key, value in fields.items():
            setattr(product, key, value)
        if "price_paise" in fields:
            for variant in await session.scalars(
                select(ProductVariant).where(ProductVariant.product_id == product.id)
            ):
                variant.price_paise = fields["price_paise"]
        await session.flush()
    return ok(_product_view(product))


@router.delete("/products/{product_id}")
async def archive_product(
    product_id: uuid.UUID,
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    """Soft delete — orders and carts reference this product's history, so the row
    stays; it is just hidden from the storefront."""
    async with session.begin():
        product = await _owned_product(session, identity.merchant_id, product_id)
        product.status = "archived"
        await session.flush()
    return ok({"id": str(product.id), "status": product.status})


# --------------------------------------------------------------- campaign writes


class CampaignPatch(BaseModel):
    status: Literal["active", "paused", "archived"]


@router.patch("/campaigns/{campaign_id}")
async def update_campaign_status(
    campaign_id: uuid.UUID,
    body: CampaignPatch,
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    async with session.begin():
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None or campaign.merchant_id != identity.merchant_id:
            raise HTTPException(status_code=404, detail="campaign not found")
        campaign.status = body.status
        await session.flush()
    return ok({"id": str(campaign.id), "status": campaign.status})


# --------------------------------------------------------------- analytics


_REVENUE_STATUSES = ("paid", "fulfilled")


@router.get("/analytics")
async def analytics(
    days: int = Query(default=45, ge=7, le=120),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    """Time-series + breakdowns for the Overview analytics charts."""
    mid = identity.merchant_id
    since = datetime.now(UTC) - timedelta(days=days)
    day = func.date(Order.created_at)
    revenue_sum = func.coalesce(
        func.sum(case((Order.status.in_(_REVENUE_STATUSES), Order.total_paise), else_=0)), 0
    )

    # revenue + order count per calendar day
    series_rows = (
        await session.execute(
            select(day.label("d"), func.count(Order.id), revenue_sum)
            .where(Order.merchant_id == mid, Order.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()

    by_day = {str(d): (int(c), int(r)) for d, c, r in series_rows}
    timeseries = []
    cursor = (datetime.now(UTC) - timedelta(days=days - 1)).date()
    end = datetime.now(UTC).date()
    while cursor <= end:
        key = cursor.isoformat()
        orders, revenue = by_day.get(key, (0, 0))
        timeseries.append({"date": key, "orders": orders, "revenue_paise": revenue})
        cursor += timedelta(days=1)

    # order source breakdown (window)
    source_rows = (
        await session.execute(
            select(Order.source, func.count(Order.id), revenue_sum)
            .where(Order.merchant_id == mid, Order.created_at >= since)
            .group_by(Order.source)
        )
    ).all()
    sources = [{"source": s, "orders": int(c), "revenue_paise": int(r)} for s, c, r in source_rows]

    # order status breakdown (window)
    status_rows = (
        await session.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.merchant_id == mid, Order.created_at >= since)
            .group_by(Order.status)
        )
    ).all()
    statuses = [{"status": s, "count": int(c)} for s, c in status_rows]

    # category revenue + top products (window, revenue statuses only)
    cat_rows = (
        await session.execute(
            select(Product.category, func.coalesce(func.sum(OrderItem.line_total_paise), 0))
            .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.merchant_id == mid,
                Order.created_at >= since,
                Order.status.in_(_REVENUE_STATUSES),
            )
            .group_by(Product.category)
            .order_by(func.sum(OrderItem.line_total_paise).desc())
        )
    ).all()
    category_revenue = [{"category": c, "revenue_paise": int(r)} for c, r in cat_rows]

    prod_rows = (
        await session.execute(
            select(
                Product.name,
                func.coalesce(func.sum(OrderItem.quantity), 0),
                func.coalesce(func.sum(OrderItem.line_total_paise), 0),
            )
            .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.merchant_id == mid,
                Order.created_at >= since,
                Order.status.in_(_REVENUE_STATUSES),
            )
            .group_by(Product.name)
            .order_by(func.sum(OrderItem.line_total_paise).desc())
            .limit(8)
        )
    ).all()
    top_products = [{"name": n, "units": int(u), "revenue_paise": int(r)} for n, u, r in prod_rows]

    window_orders = sum(c for c, _ in by_day.values())
    window_revenue = sum(r for _, r in by_day.values())
    paid_orders = sum(c for s, c in status_rows if s in _REVENUE_STATUSES)

    return ok(
        {
            "window_days": days,
            "summary": {
                "revenue_paise": window_revenue,
                "order_count": window_orders,
                "paid_order_count": paid_orders,
                "aov_paise": window_revenue // paid_orders if paid_orders else 0,
            },
            "timeseries": timeseries,
            "sources": sources,
            "statuses": statuses,
            "category_revenue": category_revenue,
            "top_products": top_products,
        }
    )


# --------------------------------------------------------------- knowledge base


@router.get("/knowledge")
async def knowledge_documents(
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    """The merchant's grounding corpus: what the agent can cite, and how it was indexed."""
    rows = (
        await session.execute(
            select(Document, DocumentVersion)
            .outerjoin(DocumentVersion, DocumentVersion.id == Document.current_version_id)
            .where(Document.merchant_id == identity.merchant_id)
            .order_by(Document.document_type.asc(), Document.title.asc())
        )
    ).all()

    retrievals: int = (
        await session.scalar(
            select(func.count(AgentAction.id))
            .join(AgentSession, AgentSession.id == AgentAction.session_id)
            .where(
                AgentSession.merchant_id == identity.merchant_id,
                AgentAction.tool_name == "knowledge_search",
            )
        )
        or 0
    )

    documents = []
    total_chunks = 0
    for doc, ver in rows:
        chunk_count = ver.chunk_count if ver and ver.chunk_count is not None else 0
        total_chunks += chunk_count
        documents.append(
            {
                "id": str(doc.id),
                "title": doc.title,
                "document_type": doc.document_type,
                "status": doc.status,
                "source_path": doc.storage_path,
                "version_number": ver.version_number if ver else None,
                "chunk_count": chunk_count,
                "namespace": ver.pinecone_namespace if ver else None,
                "indexed_at": ver.indexed_at.isoformat() if ver and ver.indexed_at else None,
            }
        )

    return ok(
        {
            "documents": documents,
            "summary": {
                "document_count": len(documents),
                "indexed_count": sum(1 for d in documents if d["status"] == "indexed"),
                "chunk_count": total_chunks,
                "retrieval_calls": retrievals,
            },
        }
    )


_KB_MAX_BYTES = 300_000
_KB_TYPES = ("merchant_policy", "faq_or_guide")


def _doc_key(name: str) -> str:
    stem = re.sub(r"\.(md|markdown|txt)$", "", name.strip(), flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    return slug or "document"


@router.post("/knowledge", status_code=201)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=2, max_length=200),
    document_type: str = Form(...),
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    """Ingest a markdown/text file into this merchant's vector namespace — the same
    pipeline as the CLI seeder (semantic chunks → embeddings → Pinecone + a
    versioned Postgres audit row). Re-uploading the same filename creates a new
    version and drops the old vectors."""
    if document_type not in _KB_TYPES:
        raise HTTPException(status_code=422, detail=f"document_type must be one of {_KB_TYPES}")

    raw_bytes = await file.read()
    if len(raw_bytes) > _KB_MAX_BYTES:
        raise HTTPException(status_code=413, detail="file is larger than 300 KB")
    text = raw_bytes.decode("utf-8", errors="replace").strip()
    if len(text) < 20:
        raise HTTPException(status_code=422, detail="file has no usable text")

    key = _doc_key(file.filename or title)
    try:
        async with session.begin():
            merchant = await session.get(Merchant, identity.merchant_id)
            if merchant is None or not merchant.pinecone_namespace:
                raise HTTPException(status_code=409, detail="merchant has no knowledge namespace")
            result = await KnowledgeIngestionService(session).ingest_markdown(
                merchant_id=identity.merchant_id,
                merchant_code=merchant.merchant_code,
                namespace=merchant.pinecone_namespace,
                document_key=key,
                title=title.strip(),
                document_type=document_type,
                source_path=f"upload/{key}.md",
                raw_text=text,
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — embedding / vector store outage
        _log.exception("knowledge upload failed for merchant %s", identity.merchant_id)
        raise HTTPException(
            status_code=503,
            detail="Indexing failed — check the embedding / vector store connection.",
        ) from exc

    return ok(
        {
            "document_id": str(result.document_id),
            "document_key": result.document_key,
            "version_number": result.version_number,
            "chunk_count": result.chunk_count,
            "namespace": result.namespace,
        }
    )


class KnowledgePreviewRequest(BaseModel):
    query: str = Field(min_length=2, max_length=400)
    document_type: Literal["merchant_policy", "faq_or_guide"] | None = None


@router.post("/knowledge/preview")
async def knowledge_preview(
    body: KnowledgePreviewRequest,
    identity: MerchantIdentity = _IDENTITY,
    session: AsyncSession = _SESSION,
) -> dict:
    """Run the exact retrieval the shopping agent runs, so the operator can see
    what a customer question would surface from the corpus before it ships."""
    merchant = await session.get(Merchant, identity.merchant_id)
    namespace = merchant.pinecone_namespace if merchant else None
    if not namespace:
        raise HTTPException(status_code=409, detail="merchant has no knowledge namespace")

    try:
        chunks = await asyncio.to_thread(
            KnowledgeRetriever().retrieve,
            namespace=namespace,
            query=body.query,
            document_type=body.document_type,
        )
    except Exception as exc:  # noqa: BLE001 — surface any vector/embedding outage as one status
        raise HTTPException(
            status_code=503,
            detail=(
                "Knowledge retrieval is unavailable right now. "
                "Check the vector store connection."
            ),
        ) from exc

    return ok(
        {
            "query": body.query,
            "results": [
                {
                    "document_id": c.document_id,
                    "document_type": c.document_type,
                    "heading": c.heading,
                    "text": c.text,
                    "score": round(c.score, 4),
                    "source_path": c.source_path,
                }
                for c in chunks
            ],
        }
    )
