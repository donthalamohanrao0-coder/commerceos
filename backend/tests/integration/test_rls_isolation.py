"""RLS tenant isolation — a request-scoped session (app_request role + GUC) must
only ever see its own merchant's rows (migrations 0012-0014)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.asyncio

_BOGUS = "00000000-0000-0000-0000-0000000000ff"


async def _orders_visible(role_merchant: str) -> int:
    from app.core.db import async_session_factory

    session = async_session_factory()
    try:
        async with session.begin():
            await session.execute(text(f"SET LOCAL app.current_merchant_id = '{role_merchant}'"))
            await session.execute(text("SET LOCAL ROLE app_request"))
            return int((await session.execute(text("SELECT count(*) FROM orders"))).scalar_one())
    finally:
        await session.close()


async def test_scoped_session_sees_only_its_tenant(merchant) -> None:
    real = await _orders_visible(str(merchant.id))
    bogus = await _orders_visible(_BOGUS)
    assert real > 0
    assert bogus == 0


async def test_app_request_role_has_no_bypassrls() -> None:
    from app.core.db import async_session_factory

    session = async_session_factory()
    try:
        row = (
            await session.execute(
                text("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'app_request'")
            )
        ).scalar_one()
        assert row is False
    finally:
        await session.close()


async def _run_blocked(sql: str, existing_id: str) -> None:
    """Each mutation gets its own session — an aborted transaction cannot be
    reused for the next attempt."""
    from app.core.db import async_session_factory

    session = async_session_factory()
    try:
        async with session.begin():
            await session.execute(text(sql), {"i": existing_id})
    finally:
        await session.close()


async def test_audit_events_are_append_only() -> None:
    from app.core.db import async_session_factory

    probe = async_session_factory()
    try:
        existing_id = (
            await probe.execute(text("SELECT id::text FROM audit_events LIMIT 1"))
        ).scalar_one_or_none()
    finally:
        await probe.close()
    if existing_id is None:
        pytest.skip("no audit_events to test against")

    with pytest.raises(DBAPIError):  # BEFORE DELETE trigger raises restrict_violation
        await _run_blocked("DELETE FROM audit_events WHERE id = :i", existing_id)
    with pytest.raises(DBAPIError):  # UPDATE is blocked too
        await _run_blocked("UPDATE audit_events SET action = 'x' WHERE id = :i", existing_id)
