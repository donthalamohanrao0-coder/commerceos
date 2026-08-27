"""Redis-backed sliding-window rate limiter (security-architecture.md #10).

Wired in from Phase 4 and applied to /api/v1/agent/* now; extended to payments,
refunds, and the Agent Commerce API in later phases.
"""

import time

import redis.asyncio as redis

from app.core.config import get_settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds}s")


async def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    """Fixed-window counter keyed by e.g. f'agent:{merchant_id}:{customer_id}'.

    Simple and sufficient for the demo; can be upgraded to a sliding log later
    without changing call sites.
    """
    r = get_redis()
    now_bucket = int(time.time() // window_seconds)
    redis_key = f"ratelimit:{key}:{now_bucket}"

    count = await r.incr(redis_key)
    if count == 1:
        await r.expire(redis_key, window_seconds)

    if count > limit:
        ttl = await r.ttl(redis_key)
        raise RateLimitExceeded(retry_after_seconds=max(ttl, 1))
