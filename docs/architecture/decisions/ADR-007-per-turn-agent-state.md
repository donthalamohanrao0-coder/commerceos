# ADR-007 — Per-turn Agent State (no graph checkpointer)

## Context

LangGraph supports a checkpointer that persists graph state between steps so a
run can be paused and resumed. CommerceOS agent turns are short (one user
message → a bounded plan/act loop → one reply) and every durable fact the turn
produces — the cart, the order, the approval request, the audit events — is
already written to Postgres by the domain services, not held in graph memory.

## Decision

Build the graph state fresh at the start of each turn from persisted data
(`agent_sessions`, `agent_messages`, the cart) and discard it when the turn
returns. No checkpointer, no thread store to manage.

Bounded execution is enforced inside the turn instead: `max_graph_steps`,
`max_tool_calls`, and a wall-clock `deadline` are seeded into state by
`BaseAgentService._initial_state` from the merchant's policy and enforced in
`agent_node` (see ADR-005, `docs/security/audit.md`).

## Alternatives

### Postgres/Redis checkpointer
Rejected for now: adds a stateful component and migration surface for a
resumption capability the demo does not need. The commerce state that matters is
already durable in the relational model.

## Consequences

Positive:
- no partial-run state to reconcile after a deploy or crash
- a restarted API process simply replays the last turn from persisted history
- simpler local development and testing

Negative:
- an in-flight turn interrupted mid-tool-call is not auto-resumed; the client
  re-sends the message and the turn re-runs (tool calls that already committed
  are idempotent or re-derived from state)
- if turns ever become long-running (e.g. multi-minute research), revisit and
  add a checkpointer
