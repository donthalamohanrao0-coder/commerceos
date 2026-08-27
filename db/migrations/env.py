import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.agents import models as agent_models  # noqa: E402,F401
from app.approvals import models as approval_models  # noqa: E402,F401
from app.audit import models as audit_models  # noqa: E402,F401
from app.core import idempotency_models  # noqa: E402,F401
from app.core.config import get_settings  # noqa: E402
from app.core.db import Base  # noqa: E402
from app.domains.campaigns import models as campaigns_models  # noqa: E402,F401
from app.domains.cart import models as cart_models  # noqa: E402,F401
from app.domains.catalog import models as catalog_models  # noqa: E402,F401
from app.domains.customers import models as customers_models  # noqa: E402,F401

# Import all domain models so Base.metadata is fully populated for autogenerate.
from app.domains.merchants import models as merchants_models  # noqa: E402,F401
from app.domains.orders import models as orders_models  # noqa: E402,F401
from app.domains.payments import models as payments_models  # noqa: E402,F401
from app.knowledge import models as knowledge_models  # noqa: E402,F401
from app.policies import models as policy_models  # noqa: E402,F401
from app.webhooks import models as webhook_models  # noqa: E402,F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
db_url = os.environ.get("DATABASE_URL", settings.database_url)
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
