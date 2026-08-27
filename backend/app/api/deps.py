"""Request-scoped dependencies.

TEMPORARY: merchant identity is read from an X-Merchant-Id header until Supabase Auth
is wired (Phase 6+/Supabase cutover). Production auth must derive merchant_id from the
authenticated identity server-side — never trust a client-supplied value as
authorization (security-architecture.md #4). This header-based stand-in exists only
to let Phase 3-5 be smoke-tested over HTTP before real auth lands.
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_merchant_id(x_merchant_id: str = Header(...)) -> uuid.UUID:
    try:
        return uuid.UUID(x_merchant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-Merchant-Id must be a valid UUID") from exc
