"""The in-process fallback limiter (used when Redis is unreachable) must still
enforce the per-key budget — the Agent Commerce API depends on it (ADR-006)."""

import pytest

from app.core.rate_limit import RateLimitExceeded, _enforce_local, _local_counters


def _key(name: str) -> str:
    _local_counters.pop(name, None)
    return name


def test_allows_up_to_the_limit_then_blocks() -> None:
    key = _key("k1")
    for _ in range(3):
        _enforce_local(key, limit=3, window_seconds=60)
    with pytest.raises(RateLimitExceeded) as exc:
        _enforce_local(key, limit=3, window_seconds=60)
    assert exc.value.retry_after_seconds >= 1


def test_counters_are_independent_per_key() -> None:
    a, b = _key("a"), _key("b")
    for _ in range(5):
        _enforce_local(a, limit=5, window_seconds=60)
    _enforce_local(b, limit=1, window_seconds=60)  # b is on its own budget
    with pytest.raises(RateLimitExceeded):
        _enforce_local(a, limit=5, window_seconds=60)


def test_window_rollover_resets_the_count(monkeypatch: pytest.MonkeyPatch) -> None:
    key = _key("roll")
    now = [1_000_000.0]
    monkeypatch.setattr("app.core.rate_limit.time.time", lambda: now[0])

    _enforce_local(key, limit=1, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        _enforce_local(key, limit=1, window_seconds=60)

    now[0] += 61  # next window
    _enforce_local(key, limit=1, window_seconds=60)  # allowed again
