"""Fixed-window rate limiter (security-architecture.md #10).

Redis-backed when a broker is reachable; falls back to an in-process counter so
the limiter still enforces in a single-node demo with no Redis. Applied to
``/api/v1/agent/*`` and the Agent Commerce API.
"""

from __future__ import annotations

import time

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings

_redis: redis.Redis | None = None
_redis_ok = True
_local_counters: dict[str, tuple[int, int]] = {}  # key -> (bucket, count)


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds}s")


def _enforce_local(key: str, *, limit: int, window_seconds: int) -> None:
    bucket = int(time.time() // window_seconds)
    prev_bucket, count = _local_counters.get(key, (bucket, 0))
    count = count + 1 if prev_bucket == bucket else 1
    _local_counters[key] = (bucket, count)
    if count > limit:
        elapsed = int(time.time()) % window_seconds
        raise RateLimitExceeded(retry_after_seconds=max(window_seconds - elapsed, 1))


async def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    """Fixed-window counter keyed by e.g. ``f'agentkey:{key_id}'``.

    Uses Redis when available; on any Redis failure it switches to a per-process
    counter for the rest of the process's life (logged once by the caller path).
    """
    global _redis_ok
    if _redis_ok:
        try:
            r = get_redis()
            now_bucket = int(time.time() // window_seconds)
            redis_key = f"ratelimit:{key}:{now_bucket}"
            count = await r.incr(redis_key)
            if count == 1:
                await r.expire(redis_key, window_seconds)
            if count > limit:
                ttl = await r.ttl(redis_key)
                raise RateLimitExceeded(retry_after_seconds=max(ttl, 1))
            return
        except (RedisError, OSError):
            _redis_ok = False  # Redis is down — degrade to in-process for this run

    _enforce_local(key, limit=limit, window_seconds=window_seconds)
