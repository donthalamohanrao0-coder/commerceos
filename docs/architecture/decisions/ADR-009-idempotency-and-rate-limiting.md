# ADR-009 — Idempotency & Rate-limiting Posture

## Context

Two classes of caller can trigger money movement or LLM spend: the in-app agent
(driven by an authenticated customer session) and an external AI buyer (driven
by a scoped API key). Both retry. Retries must not double-charge, double-order,
or be usable to exhaust budget.

## Decision

### Idempotency
- Every mutating operation on the internal path runs through
  `with_idempotency(operation, key, request_payload, execute)`, which stores the
  first result keyed by `(merchant_id, operation, key)` and replays it on repeat.
- On the **Agent Commerce API**, `Idempotency-Key` is **required** (HTTP 400 if
  absent) for `createOrder` and the confirmed `requestPayment`. The server never
  mints a key for a mutating external call — a client that cannot supply a stable
  key cannot safely be allowed to retry an order or a charge.
- The unconfirmed `requestPayment` probe (`confirmed=false`) is read-only and
  takes no key.
- Razorpay webhooks are deduplicated on the provider event id.

### Rate-limiting
- Fixed-window counters in Redis, with a per-process fallback for the rest of the
  run if Redis is unreachable (`app/core/rate_limit.py`) — same degradation story
  as the cache layer.
- Agent Commerce: per-key budget (`rate_limit_per_minute` on the key), enforced
  in `get_agent_principal`.
- In-app agent chat: per-conversation limit (`agentchat:{session_id}`,
  20 turns/min) on both the sync and streaming turn endpoints, because each turn
  fans out to several LLM calls.

## Consequences

Positive:
- a retried external order/charge is provably safe or provably rejected — no
  silent second write
- LLM spend per conversation is bounded even for an authenticated abuser
- no hard dependency on Redis for correctness

Negative:
- external buyer integrations must implement key generation (documented in the
  OpenAPI description and the buyer-mcp client)
- fixed-window limiter allows a brief burst at a window boundary; acceptable for
  the threat model (cost control, not DDoS defence)
