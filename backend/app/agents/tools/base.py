"""Tool abstraction for the shopping graph.

A tool is the *proposal* half of "AI proposes, backend decides": a class exposing
``name`` / ``description`` / a Pydantic ``Args`` schema (validated before anything
runs) and an ``async run(ctx, args)`` that delegates to a deterministic domain
service, which owns auth / policy / limits / persistence.

Tools are duck-typed (each defines its own ``Args`` subclass and a ``run`` that
takes it), so the registry deliberately holds them as ``Any`` rather than forcing
a Protocol that a narrowed ``run`` signature can never satisfy under strict mypy.
"""

from __future__ import annotations

from typing import Any

from app.integrations.openai.chat import ToolSpec


def tool_spec(tool: Any) -> ToolSpec:
    schema = tool.Args.model_json_schema()
    schema.pop("title", None)
    return ToolSpec(name=tool.name, description=tool.description, parameters=schema)


class ToolRegistry:
    def __init__(self, tools: list[Any]) -> None:
        self._tools: dict[str, Any] = {t.name: t for t in tools}

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def specs(self) -> list[ToolSpec]:
        return [tool_spec(t) for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)
