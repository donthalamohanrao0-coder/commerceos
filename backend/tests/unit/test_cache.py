"""The JSON cache round-trips, honours TTL, and a generation bump invalidates
keys built with the prior generation. Runs against whatever backend is live
(Redis or the in-process fallback) — both must satisfy these.
"""

import asyncio

import pytest

from app.core import cache

pytestmark = pytest.mark.asyncio


async def test_round_trip_and_miss() -> None:
    key = cache.cache_key("test", "round-trip", str(id(object())))
    assert await cache.cache_get(key) is None
    await cache.cache_set(key, {"a": 1, "b": ["x"]}, ttl_seconds=30)
    assert await cache.cache_get(key) == {"a": 1, "b": ["x"]}


async def test_ttl_expiry() -> None:
    key = cache.cache_key("test", "ttl", str(id(object())))
    await cache.cache_set(key, 42, ttl_seconds=1)
    assert await cache.cache_get(key) == 42
    await asyncio.sleep(1.2)
    assert await cache.cache_get(key) is None


async def test_generation_bump_invalidates() -> None:
    scope = f"test:{id(object())}"
    g0 = await cache.cache_generation(scope)
    k0 = cache.cache_key("test", scope, str(g0))
    await cache.cache_set(k0, "old", ttl_seconds=60)

    await cache.cache_bump(scope)
    g1 = await cache.cache_generation(scope)
    assert g1 == g0 + 1

    k1 = cache.cache_key("test", scope, str(g1))
    assert await cache.cache_get(k1) is None  # the new-generation key is empty
