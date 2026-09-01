"""Langfuse tracing seam (docs/ai/langfuse-observability.md).

Langfuse is the AI-observability layer (traces, generations, tool observations,
cost/latency). It stays a no-op until both keys are set, exactly like Sentry — so
the agent runs identically with or without it. Nothing sensitive is sent: only
tool names, argument keys, status, and coarse metadata.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol


class Span(Protocol):
    def child(self, *, name: str, kind: str = "span", input: Any = None) -> Span: ...

    def end(self, *, output: Any = None, level: str | None = None) -> None: ...

    def score(self, *, name: str, value: float, comment: str | None = None) -> None: ...


class Tracer(Protocol):
    def trace(self, *, name: str, metadata: dict[str, Any]) -> Span: ...

    def flush(self) -> None: ...


# ------------------------------------------------------------------------- no-op


class _NoopSpan:
    def child(self, *, name: str, kind: str = "span", input: Any = None) -> _NoopSpan:
        return self

    def end(self, *, output: Any = None, level: str | None = None) -> None:
        return

    def score(self, *, name: str, value: float, comment: str | None = None) -> None:
        return


class _NoopTracer:
    def trace(self, *, name: str, metadata: dict[str, Any]) -> _NoopSpan:
        return _NoopSpan()

    def flush(self) -> None:
        return


# ------------------------------------------------------------------------- real


_LEVELS = {"DEBUG", "DEFAULT", "WARNING", "ERROR"}


def _level(level: str | None) -> str | None:
    if not level:
        return None
    up = level.upper()
    return up if up in _LEVELS else "ERROR"


class _LangfuseSpan:
    """Wraps a langfuse v3/v4 observation handle. Every call is guarded — a
    tracing failure must never surface in an agent turn."""

    def __init__(self, handle: Any) -> None:
        self._h = handle
        self._ended = False

    def child(self, *, name: str, kind: str = "span", input: Any = None) -> _LangfuseSpan:
        try:
            as_type = "generation" if kind == "generation" else "span"
            return _LangfuseSpan(self._h.start_observation(name=name, as_type=as_type, input=input))
        except Exception:  # noqa: BLE001 - never break the turn on a tracing hiccup
            return _LangfuseSpan(None)

    def end(self, *, output: Any = None, level: str | None = None) -> None:
        if self._h is None or self._ended:
            return
        self._ended = True
        try:
            self._h.update(output=output, level=_level(level))
            self._h.end()
        except Exception:  # noqa: BLE001
            return

    def score(self, *, name: str, value: float, comment: str | None = None) -> None:
        if self._h is None:
            return
        try:
            self._h.score(name=name, value=value, comment=comment)
        except Exception:  # noqa: BLE001
            return


class _LangfuseTracer:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._open: list[_LangfuseSpan] = []

    def trace(self, *, name: str, metadata: dict[str, Any]) -> _LangfuseSpan:
        try:
            handle = self._client.start_observation(
                name=name, as_type="span", metadata=metadata
            )
            span = _LangfuseSpan(handle)
        except Exception:  # noqa: BLE001
            return _LangfuseSpan(None)
        self._open.append(span)
        return span

    def flush(self) -> None:
        # v4 spans only export once ended; close any root spans the graph left open.
        for span in self._open:
            span.end()
        self._open.clear()
        try:
            self._client.flush()
        except Exception:  # noqa: BLE001
            return


@lru_cache
def get_tracer() -> Tracer:
    from app.core.config import get_settings

    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return _NoopTracer()
    try:
        from langfuse import Langfuse

        return _LangfuseTracer(
            Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        )
    except Exception:  # SDK missing / misconfigured -> degrade to no-op, never fail a request
        return _NoopTracer()
