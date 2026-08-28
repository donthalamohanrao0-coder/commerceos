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


class _LangfuseSpan:
    def __init__(self, handle: Any) -> None:
        self._h = handle

    def child(self, *, name: str, kind: str = "span", input: Any = None) -> _LangfuseSpan:
        factory = self._h.generation if kind == "generation" else self._h.span
        return _LangfuseSpan(factory(name=name, input=input))

    def end(self, *, output: Any = None, level: str | None = None) -> None:
        try:
            self._h.end(output=output, level=level)
        except TypeError:  # older SDK: end() takes no kwargs
            self._h.update(output=output)
            self._h.end()

    def score(self, *, name: str, value: float, comment: str | None = None) -> None:
        self._h.score(name=name, value=value, comment=comment)


class _LangfuseTracer:
    def __init__(self, client: Any) -> None:
        self._client = client

    def trace(self, *, name: str, metadata: dict[str, Any]) -> _LangfuseSpan:
        return _LangfuseSpan(self._client.trace(name=name, metadata=metadata))

    def flush(self) -> None:
        self._client.flush()


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
