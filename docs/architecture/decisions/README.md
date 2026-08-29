# Architecture Decision Records

Short records of the decisions that shape CommerceOS — the context, the choice,
what was rejected, and the trade-off accepted. Read these to understand *why* the
code is structured the way it is.

| ADR | Decision |
| --- | --- |
| [001](ADR-001-modular-monolith.md) | Modular monolith for the core app + background workers |
| [002](ADR-002-supabase.md) | Supabase for Postgres + Auth + Storage |
| [003](ADR-003-pinecone.md) | Pinecone for the RAG vector store, one namespace per merchant |
| [004](ADR-004-langgraph.md) | LangGraph for agent orchestration (supervisor → flow → tools) |
| [005](ADR-005-payment-gating.md) | No payment from inferred intent — server order + policy + explicit confirm |
| [006](ADR-006-agent-commerce-api.md) | Versioned, capability-scoped Agent Commerce API for external AI buyers |
| [007](ADR-007-per-turn-agent-state.md) | Per-turn agent state, no graph checkpointer; durable state lives in Postgres |
| [008](ADR-008-single-primary-postgres.md) | One primary Postgres serves OLTP, audit, and analytics |
| [009](ADR-009-idempotency-and-rate-limiting.md) | Required idempotency keys on external mutations; Redis rate limits with in-process fallback |

See also [`../golden-path.md`](../golden-path.md) — one AI-buyer purchase traced
end to end, showing where every control sits.
