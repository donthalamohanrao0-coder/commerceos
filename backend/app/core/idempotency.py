"""with_idempotency — required for payment creation, refunds, and order creation
where retries can duplicate state (api-standards.md, payment-security.md #4).

First call executes and caches the response. A duplicate call with the same key and
a matching request hash replays the cached response without re-executing. The same
key with a different request hash is a conflict (409) — the caller changed the
request under an already-used idempotency key.
"""

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotency_models import IdempotencyKey


class IdempotencyConflict(Exception):
    """Same idempotency key reused with a different request payload."""


def hash_request(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def with_idempotency(
    session: AsyncSession,
    *,
    merchant_id: uuid.UUID,
    operation: str,
    idempotency_key: str,
    request_payload: dict[str, Any],
    execute: Callable[[], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    request_hash = hash_request(request_payload)

    existing = await session.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.merchant_id == merchant_id,
            IdempotencyKey.operation == operation,
            IdempotencyKey.idempotency_key == idempotency_key,
        )
    )

    if existing is not None:
        if existing.request_hash != request_hash:
            raise IdempotencyConflict(
                f"idempotency key {idempotency_key!r} was already used for a different request"
            )
        if existing.status == "completed" and existing.response is not None:
            return existing.response
        # status == 'in_progress' or 'failed': fall through and re-attempt below,
        # reusing the same row rather than creating a duplicate.

    record = existing or IdempotencyKey(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        operation=operation,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status="in_progress",
    )
    if existing is None:
        session.add(record)
        await session.flush()

    try:
        response = await execute()
    except Exception:
        record.status = "failed"
        await session.flush()
        raise

    record.response = response
    record.status = "completed"
    await session.flush()
    return response
