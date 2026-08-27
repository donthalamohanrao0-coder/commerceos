from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    async with async_session_factory() as session:
        yield session


@asynccontextmanager
async def db_session_with_tenant(merchant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Session scoped to a single transaction with `app.current_merchant_id` set for RLS.

    Merchant id must already be derived server-side from the authenticated identity —
    never accept it as a raw client-supplied value (security-architecture.md #4).
    """
    async with async_session_factory() as session, session.begin():
        # set_config(..., true) scopes the setting to the current transaction only,
        # and (unlike bare SET LOCAL) accepts a bound parameter rather than a literal.
        await session.execute(
            text("SELECT set_config('app.current_merchant_id', :merchant_id, true)"),
            {"merchant_id": merchant_id},
        )
        yield session
