import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.agent_commerce import _require_idempotency_key
from app.core.idempotency import IdempotencyConflict, with_idempotency

pytestmark = pytest.mark.asyncio


def test_agent_commerce_requires_idempotency_key() -> None:
    assert _require_idempotency_key("  order-42 ") == "order-42"
    for missing in (None, "", "   "):
        with pytest.raises(HTTPException) as exc:
            _require_idempotency_key(missing)
        assert exc.value.status_code == 400


async def test_replay_returns_cached_response_without_re_executing(
    db: AsyncSession, merchant
) -> None:
    calls = {"n": 0}

    async def execute() -> dict:
        calls["n"] += 1
        return {"value": calls["n"]}

    kwargs = dict(
        merchant_id=merchant.id,
        operation="test.op",
        idempotency_key="key-1",
        request_payload={"a": 1},
        execute=execute,
    )
    first = await with_idempotency(db, **kwargs)
    second = await with_idempotency(db, **kwargs)
    assert first == second == {"value": 1}
    assert calls["n"] == 1  # executed exactly once


async def test_same_key_different_payload_conflicts(db: AsyncSession, merchant) -> None:
    async def execute() -> dict:
        return {"ok": True}

    await with_idempotency(
        db,
        merchant_id=merchant.id,
        operation="test.op",
        idempotency_key="key-2",
        request_payload={"a": 1},
        execute=execute,
    )
    with pytest.raises(IdempotencyConflict):
        await with_idempotency(
            db,
            merchant_id=merchant.id,
            operation="test.op",
            idempotency_key="key-2",
            request_payload={"a": 2},
            execute=execute,
        )
