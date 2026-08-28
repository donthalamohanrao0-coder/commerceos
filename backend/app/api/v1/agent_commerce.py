"""Agent Commerce API (ADR-006) — lets an external AI buyer transact with a
merchant end to end without touching internal service endpoints.

Auth: ``Authorization: Bearer ack_live_...``. Every route declares an explicit
capability scope; anything sensitive (refunds, discount overrides) is simply not
a grantable scope. Order and payment creation are idempotent.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.keys import AgentPrincipal
from app.agent_commerce.schemas import CatalogSearchIn, CreateOrderIn, QuoteIn
from app.agent_commerce.service import AgentCommerceService
from app.api.deps import get_agent_tenant_session, require_scope
from app.api.envelope import ok
from app.core.idempotency import with_idempotency

router = APIRouter(prefix="/agent-commerce", tags=["agent-commerce"])

# Module-level so the scope check is a singleton dependency (and ruff B008 stays quiet).
_CATALOG_READ = Depends(require_scope("catalog:read"))
_CATALOG_SEARCH = Depends(require_scope("catalog:search"))
_QUOTE_CREATE = Depends(require_scope("quote:create"))
_ORDER_CREATE = Depends(require_scope("order:create"))
_PAYMENT_REQUEST = Depends(require_scope("payment:request"))
_TENANT_SESSION = Depends(get_agent_tenant_session)
_IDEMPOTENCY_KEY = Header(..., alias="Idempotency-Key")


def _svc(session: AsyncSession, principal: AgentPrincipal) -> AgentCommerceService:
    return AgentCommerceService(session, actor_id=f"agent_key:{principal.name}")


@router.get("/catalog")
async def list_catalog(
    cursor: str | None = None,
    limit: int = 20,
    principal: AgentPrincipal = _CATALOG_READ,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    limit = max(1, min(limit, 100))
    async with session.begin():
        page = await _svc(session, principal).list_catalog(
            principal.merchant_id, cursor=cursor, limit=limit
        )
    return ok(
        {
            "products": [p.model_dump(mode="json") for p in page.products],
            "next_cursor": page.next_cursor,
        }
    )


@router.get("/catalog/{product_id}")
async def get_product(
    product_id: uuid.UUID,
    principal: AgentPrincipal = _CATALOG_READ,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        product = await _svc(session, principal).get_product(principal.merchant_id, product_id)
    return ok(product.model_dump(mode="json"))


@router.post("/catalog/search")
async def search_catalog(
    body: CatalogSearchIn,
    principal: AgentPrincipal = _CATALOG_SEARCH,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        products = await _svc(session, principal).search_catalog(principal.merchant_id, body)
    return ok({"products": [p.model_dump(mode="json") for p in products]})


@router.post("/quote")
async def create_quote(
    body: QuoteIn,
    principal: AgentPrincipal = _QUOTE_CREATE,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        quote = await _svc(session, principal).quote(principal.merchant_id, body.items)
    return ok(quote.model_dump(mode="json"))


@router.post("/orders")
async def create_order(
    body: CreateOrderIn,
    idempotency_key: str = _IDEMPOTENCY_KEY,
    principal: AgentPrincipal = _ORDER_CREATE,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        svc = _svc(session, principal)

        async def _execute() -> dict[str, Any]:
            order = await svc.create_order(
                principal.merchant_id, body.items, buyer_ref=body.buyer_ref
            )
            return order.model_dump(mode="json")

        result = await with_idempotency(
            session,
            merchant_id=principal.merchant_id,
            operation="agent_commerce.create_order",
            idempotency_key=idempotency_key,
            request_payload=body.model_dump(mode="json"),
            execute=_execute,
        )
    return ok(result)


@router.get("/orders/{order_id}")
async def get_order(
    order_id: uuid.UUID,
    principal: AgentPrincipal = _ORDER_CREATE,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        order = await _svc(session, principal).get_order(principal.merchant_id, order_id)
    return ok(order.model_dump(mode="json"))


@router.post("/orders/{order_id}/payment")
async def request_payment(
    order_id: uuid.UUID,
    confirmed: bool = False,
    idempotency_key: str = _IDEMPOTENCY_KEY,
    principal: AgentPrincipal = _PAYMENT_REQUEST,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        svc = _svc(session, principal)

        async def _execute() -> dict[str, Any]:
            payment = await svc.request_payment(
                principal.merchant_id,
                order_id,
                idempotency_key=idempotency_key,
                confirmed=confirmed,
            )
            return payment.model_dump(mode="json")

        # only the confirmed, charging call is idempotency-protected; the
        # unconfirmed "approval_required" probe is safe to repeat
        if confirmed:
            result = await with_idempotency(
                session,
                merchant_id=principal.merchant_id,
                operation="agent_commerce.request_payment",
                idempotency_key=idempotency_key,
                request_payload={"order_id": str(order_id), "confirmed": True},
                execute=_execute,
            )
        else:
            result = await _execute()
    return ok(result)
