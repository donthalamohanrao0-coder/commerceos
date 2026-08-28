"""Shared test fixtures.

- `_force_fake_ai` (autouse): blanks the OpenAI / Pinecone / Langfuse credentials
  for the test process so the agent runs on the deterministic Fake clients.
- `db`: a session on the live Supabase DB wrapped in a transaction that is always
  rolled back — real Postgres behaviour, zero pollution (testing-strategy.md).
- `merchant` / `product` / `customer`: handles to the seeded NovaTech demo data.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MERCHANT_CODE = "mrc_novatech_001"


@pytest.fixture(scope="session", autouse=True)
def _force_fake_ai() -> None:
    # env vars outrank the .env file in pydantic-settings, so a blank value here
    # forces every credential-gated factory onto its Fake implementation.
    for key in (
        "OPENAI_API_KEY",
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ):
        os.environ[key] = ""

    from app.core.config import get_settings
    from app.integrations.langfuse.client import get_tracer
    from app.integrations.openai.chat import get_chat_client
    from app.integrations.openai.embeddings import get_embedding_client
    from app.integrations.pinecone.client import get_vector_index

    get_settings.cache_clear()
    get_chat_client.cache_clear()
    get_embedding_client.cache_clear()
    get_vector_index.cache_clear()
    get_tracer.cache_clear()

    settings = get_settings()
    assert not settings.openai_api_key, "tests must run on the Fake chat client"


@pytest.fixture(autouse=True)
def _null_pool_engine():  # noqa: ANN202
    """Rebuild the shared engine on a NullPool for each test so asyncpg
    connections never outlive their event loop (pytest gives each test a fresh
    loop; a pooled connection bound to a dead loop raises on teardown)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core import db as db_module

    original_engine, original_factory = db_module.engine, db_module.async_session_factory
    db_module.engine = create_async_engine(
        db_module.settings.database_url, poolclass=NullPool, pool_pre_ping=True
    )
    db_module.async_session_factory = async_sessionmaker(db_module.engine, expire_on_commit=False)
    try:
        yield
    finally:
        db_module.engine, db_module.async_session_factory = original_engine, original_factory


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    from app.core.db import async_session_factory

    session = async_session_factory()
    txn = await session.begin()
    try:
        yield session
    finally:
        await txn.rollback()
        await session.close()


@pytest_asyncio.fixture
async def merchant(db: AsyncSession):  # noqa: ANN201 - ORM row
    from app.domains.merchants.models import Merchant

    row = await db.scalar(select(Merchant).where(Merchant.merchant_code == MERCHANT_CODE))
    assert row is not None, "seed the NovaTech demo data before running tests"
    return row


@pytest_asyncio.fixture
async def cheap_product(db: AsyncSession, merchant):  # noqa: ANN201
    from app.domains.catalog.models import Product

    row = await db.scalar(
        select(Product)
        .where(Product.merchant_id == merchant.id, Product.status == "active")
        .order_by(Product.price_paise.asc())
    )
    assert row is not None
    return row


@pytest_asyncio.fixture
async def customer(db: AsyncSession, merchant):  # noqa: ANN201
    from app.domains.customers.models import Customer

    row = await db.scalar(select(Customer).where(Customer.merchant_id == merchant.id))
    assert row is not None
    return row
