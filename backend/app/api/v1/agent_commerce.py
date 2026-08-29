"""Agent Commerce API (ADR-006) — lets an external AI buyer transact with a
merchant end to end without touching internal service endpoints.

Auth: ``Authorization: Bearer ack_live_...``. Every route declares an explicit
capability scope; anything sensitive (refunds, discount overrides) is simply not
a grantable scope. Order and payment creation are idempotent.
"""

import copy
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
# Mutating routes (create order, charge payment) REQUIRE a stable key so a
# retried request can never create a second order / second charge. Read and
# unconfirmed-probe routes don't take one.
_IDEMPOTENCY_KEY = Header(default=None, alias="Idempotency-Key")


def _require_idempotency_key(idempotency_key: str | None) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required for this operation",
        )
    return idempotency_key.strip()


def _svc(session: AsyncSession, principal: AgentPrincipal) -> AgentCommerceService:
    return AgentCommerceService(session, actor_id=f"agent_key:{principal.name}")


_PREFIX = "/api/v1/agent-commerce"


@router.get("/openapi.json", include_in_schema=False)
async def buyer_openapi(request: Request) -> dict[str, Any]:
    """A trimmed OpenAPI doc for just this API, ready to paste into a ChatGPT
    Custom GPT ("Import from URL"). Only the agent-commerce paths, a bearer
    security scheme, and an absolute `servers` URL derived from this request."""
    full = request.app.openapi()
    paths: dict[str, Any] = {}
    for path, item in full.get("paths", {}).items():
        if not path.startswith(_PREFIX):
            continue
        item = copy.deepcopy(item)
        for op in item.values():
            if isinstance(op, dict):
                op["parameters"] = [
                    p
                    for p in op.get("parameters", [])
                    if str(p.get("name", "")).lower() != "authorization"
                ]
                op.pop("security", None)
        paths[path[len(_PREFIX) :] or "/"] = item

    used: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref" and isinstance(value, str) and "/schemas/" in value:
                    used.add(value.rsplit("/", 1)[-1])
                else:
                    _walk(value)
        elif isinstance(node, list):
            for entry in node:
                _walk(entry)

    all_schemas = full.get("components", {}).get("schemas", {})
    _walk(paths)
    seen: set[str] = set()
    while used - seen:
        for name in list(used - seen):
            seen.add(name)
            _walk(all_schemas.get(name, {}))

    base = str(request.base_url).rstrip("/")
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "CommerceOS Agent Commerce API",
            "version": "1.0.0",
            "description": (
                "Act as an external AI buyer for the NovaTech merchant. Always call "
                "createQuote before createOrder. Call requestPayment with confirmed=false "
                "first to surface the amount for approval, then confirmed=true to authorise."
            ),
        },
        "servers": [{"url": f"{base}{_PREFIX}"}],
        "paths": paths,
        "components": {
            "schemas": {n: all_schemas[n] for n in sorted(used) if n in all_schemas},
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        },
        "security": [{"bearerAuth": []}],
    }


@router.get("/catalog", operation_id="listCatalog")
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


@router.get("/catalog/{product_id}", operation_id="getProduct")
async def get_product(
    product_id: uuid.UUID,
    principal: AgentPrincipal = _CATALOG_READ,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        product = await _svc(session, principal).get_product(principal.merchant_id, product_id)
    return ok(product.model_dump(mode="json"))


@router.post("/catalog/search", operation_id="searchCatalog")
async def search_catalog(
    body: CatalogSearchIn,
    principal: AgentPrincipal = _CATALOG_SEARCH,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        products = await _svc(session, principal).search_catalog(principal.merchant_id, body)
    return ok({"products": [p.model_dump(mode="json") for p in products]})


@router.post("/quote", operation_id="createQuote")
async def create_quote(
    body: QuoteIn,
    principal: AgentPrincipal = _QUOTE_CREATE,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        quote = await _svc(session, principal).quote(principal.merchant_id, body.items)
    return ok(quote.model_dump(mode="json"))


@router.post("/orders", operation_id="createOrder")
async def create_order(
    body: CreateOrderIn,
    idempotency_key: str | None = _IDEMPOTENCY_KEY,
    principal: AgentPrincipal = _ORDER_CREATE,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    idem = _require_idempotency_key(idempotency_key)
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
            idempotency_key=idem,
            request_payload=body.model_dump(mode="json"),
            execute=_execute,
        )
    return ok(result)


@router.get("/orders/{order_id}", operation_id="getOrder")
async def get_order(
    order_id: uuid.UUID,
    principal: AgentPrincipal = _ORDER_CREATE,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    async with session.begin():
        order = await _svc(session, principal).get_order(principal.merchant_id, order_id)
    return ok(order.model_dump(mode="json"))


@router.post("/orders/{order_id}/payment", operation_id="requestPayment")
async def request_payment(
    order_id: uuid.UUID,
    confirmed: bool = False,
    idempotency_key: str | None = _IDEMPOTENCY_KEY,
    principal: AgentPrincipal = _PAYMENT_REQUEST,
    session: AsyncSession = _TENANT_SESSION,
) -> dict:
    # The charging call must be idempotent; the unconfirmed probe is read-only.
    idem = _require_idempotency_key(idempotency_key) if confirmed else f"probe-{order_id}"
    async with session.begin():
        svc = _svc(session, principal)

        async def _execute() -> dict[str, Any]:
            payment = await svc.request_payment(
                principal.merchant_id,
                order_id,
                idempotency_key=idem,
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
                idempotency_key=idem,
                request_payload={"order_id": str(order_id), "confirmed": True},
                execute=_execute,
            )
        else:
            result = await _execute()
    return ok(result)
