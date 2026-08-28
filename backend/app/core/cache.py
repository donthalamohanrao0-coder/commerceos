"""Small JSON cache over Redis, with a bounded in-process fallback.

Same degradation story as ``rate_limit``: use Redis when it's reachable, and on
any Redis failure switch to a per-process dict for the rest of the run so a
missing/slow Redis never breaks a request — it just stops sharing the cache
across instances.

Used for read-mostly, non-authoritative data where a stale hit is harmless:
knowledge retrieval results and the LLM workflow-classification label. Never for
prices, policy decisions, cart or payment state.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings

_redis: redis.Redis | None = None
_redis_ok = True
_local: OrderedDict[str, tuple[float, str]] = OrderedDict()  # key -> (expires_at, json)
_LOCAL_MAX = 512


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


def cache_key(*parts: str) -> str:
    """A stable, length-bounded key from arbitrary string parts."""
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"co:{parts[0]}:{digest}"


def _local_get(key: str) -> Any | None:
    hit = _local.get(key)
    if hit is None:
        return None
    expires_at, blob = hit
    if expires_at < time.time():
        _local.pop(key, None)
        return None
    _local.move_to_end(key)
    return json.loads(blob)


def _local_set(key: str, value: Any, ttl_seconds: int) -> None:
    _local[key] = (time.time() + ttl_seconds, json.dumps(value, default=str))
    _local.move_to_end(key)
    while len(_local) > _LOCAL_MAX:
        _local.popitem(last=False)


async def cache_get(key: str) -> Any | None:
    global _redis_ok
    if _redis_ok:
        try:
            blob = await _client().get(key)
            return json.loads(blob) if blob is not None else None
        except (RedisError, OSError):
            _redis_ok = False
    return _local_get(key)


async def cache_set(key: str, value: Any, *, ttl_seconds: int) -> None:
    global _redis_ok
    if _redis_ok:
        try:
            await _client().set(key, json.dumps(value, default=str), ex=ttl_seconds)
            return
        except (RedisError, OSError):
            _redis_ok = False
    _local_set(key, value, ttl_seconds)


async def cache_generation(scope: str) -> int:
    """A monotonically-increasing token for `scope`. Fold it into a cache key and
    `cache_bump(scope)` invalidates every entry built with the old value —
    without enumerating keys."""
    val = await cache_get(f"co:gen:{scope}")
    return int(val) if isinstance(val, int) else 0


async def cache_bump(scope: str) -> None:
    global _redis_ok
    if _redis_ok:
        try:
            await _client().incr(f"co:gen:{scope}")
            return
        except (RedisError, OSError):
            _redis_ok = False
    current = _local_get(f"co:gen:{scope}") or 0
    _local_set(f"co:gen:{scope}", int(current) + 1, 86400)
