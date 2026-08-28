"""Request-scoped dependencies.

Internal API identity: the frontend authenticates the user with Supabase Auth and
sends ``Authorization: Bearer <jwt>``. The backend resolves that token to a user
and maps the user to a merchant server-side (``IdentityService``) — never trusting
a client-supplied merchant id. An ``X-Merchant-Id`` header is still honoured as a
fallback for local scripts and tests. The Agent Commerce API derives the merchant
from the API key instead.
"""

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.keys import AgentApiKeyService, AgentPrincipal, InvalidAgentKey
from app.core.db import async_session_factory
from app.core.rate_limit import enforce_rate_limit
from app.identity.service import IdentityService, MerchantIdentity, NoMerchantForUser
from app.integrations.supabase.auth import InvalidAuthToken, get_token_verifier


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Unscoped session — connects as the privileged login role (RLS bypassed).

    Use only for tenant-agnostic work (health checks, webhook intake, API-key
    authentication before the merchant is known). Tenant paths use a scoped session.
    """
    async with async_session_factory() as session:
        yield session


def _tenant_scoped_session(merchant_id: uuid.UUID) -> AsyncSession:
    """A session whose every transaction sets the `app.current_merchant_id` GUC and
    drops to the non-privileged `app_request` role, so the tenant_isolation_* RLS
    policies (migrations 0012-0014) bind — the login role has BYPASSRLS. Both
    statements are transaction-local and reset on commit/rollback."""
    session = async_session_factory()

    def _scope(_sess: object, _trans: object, conn: object) -> None:
        # merchant_id is a validated uuid.UUID -> canonical form, no injection
        # surface. SET LOCAL does not accept bind parameters.
        conn.exec_driver_sql(f"SET LOCAL app.current_merchant_id = '{merchant_id}'")  # type: ignore[attr-defined]
        conn.exec_driver_sql("SET LOCAL ROLE app_request")  # type: ignore[attr-defined]

    event.listen(session.sync_session, "after_begin", _scope)
    session.info["_scope_listener"] = _scope
    return session


async def _yield_scoped(merchant_id: uuid.UUID) -> AsyncGenerator[AsyncSession, None]:
    session = _tenant_scoped_session(merchant_id)
    try:
        yield session
    finally:
        listener = session.info.pop("_scope_listener", None)
        if listener is not None:
            event.remove(session.sync_session, "after_begin", listener)
        await session.close()


def _bearer(authorization: str) -> str:
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


async def get_merchant_identity(
    authorization: str = Header(default=""),
) -> MerchantIdentity:
    """Resolve ``Authorization: Bearer <supabase-jwt>`` to the user's merchant.

    Runs on an unscoped session — the merchant is unknown until the token is
    resolved, and first-time users are auto-provisioned (IdentityService).
    """
    token = _bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        principal = get_token_verifier().verify(token)
    except InvalidAuthToken as exc:
        raise HTTPException(status_code=401, detail="invalid or expired session") from exc

    async with async_session_factory() as session, session.begin():
        try:
            return await IdentityService(session).resolve(principal)
        except NoMerchantForUser as exc:
            raise HTTPException(status_code=403, detail="no merchant for this user") from exc


async def get_current_merchant_id(
    x_merchant_id: str | None = Header(default=None),
    authorization: str = Header(default=""),
) -> uuid.UUID:
    """Merchant id for a tenant request.

    Preferred: derived from the authenticated Supabase identity. Fallback: an
    explicit ``X-Merchant-Id`` header (local scripts / tests).
    """
    if _bearer(authorization):
        return (await get_merchant_identity(authorization)).merchant_id
    if x_merchant_id:
        try:
            return uuid.UUID(x_merchant_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="X-Merchant-Id must be a valid UUID"
            ) from exc
    raise HTTPException(status_code=401, detail="authentication required")


async def get_tenant_session(
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _yield_scoped(merchant_id):
        yield session


async def get_identity_tenant_session(
    identity: MerchantIdentity = Depends(get_merchant_identity),
) -> AsyncGenerator[AsyncSession, None]:
    """Tenant-scoped session that also *requires* a resolved Supabase identity
    (used by the merchant console, which is never anonymous)."""
    async for session in _yield_scoped(identity.merchant_id):
        yield session


# --------------------------------------------------------------- Agent Commerce API


async def get_agent_principal(authorization: str = Header(default="")) -> AgentPrincipal:
    """Authenticate an external AI buyer from `Authorization: Bearer ack_...`.

    Uses an unscoped session (merchant is unknown until the key resolves); the key
    lookup itself is by unique hash, so there is no cross-tenant read.
    """
    token = authorization.removeprefix("Bearer ").strip()
    async with async_session_factory() as session, session.begin():
        try:
            principal = await AgentApiKeyService(session).authenticate(token)
        except InvalidAgentKey as exc:
            raise HTTPException(status_code=401, detail="invalid or missing agent API key") from exc

    # Per-key rate limit (the key's own configured budget). RateLimitExceeded ->
    # 429 via the exception map.
    await enforce_rate_limit(
        f"agentkey:{principal.key_id}",
        limit=principal.rate_limit_per_minute,
        window_seconds=60,
    )
    return principal


async def get_agent_tenant_session(
    principal: AgentPrincipal = Depends(get_agent_principal),
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _yield_scoped(principal.merchant_id):
        yield session


def require_scope(scope: str) -> Callable[..., Awaitable[AgentPrincipal]]:
    """FastAPI dependency factory: 403 unless the principal holds `scope`."""

    async def _check(principal: AgentPrincipal = Depends(get_agent_principal)) -> AgentPrincipal:
        if scope not in principal.scopes:
            raise HTTPException(status_code=403, detail=f"api key missing required scope: {scope}")
        return principal

    return _check
