# ADR-004 — LangGraph for Agent Orchestration

## Context

CommerceOS requires bounded, stateful, multi-step agent workflows with explicit tool calls and approval gates.

## Decision

Use LangGraph for orchestration.

The graph controls:
- state
- routing
- tool execution flow
- termination
- approval waits
- failure recovery

The graph does not replace deterministic commerce services.
