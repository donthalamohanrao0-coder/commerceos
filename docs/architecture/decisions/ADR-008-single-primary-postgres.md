# ADR-008 — Single Primary Postgres

## Context

One Supabase Postgres instance currently serves transactional commerce data
(catalog, carts, orders, payments), the append-only audit log, agent session /
message / action history, the knowledge-document metadata, and the aggregate
queries behind the merchant analytics page.

## Decision

Keep a single primary database. Serve analytics from the same instance, using
indexed aggregate queries over a rolling window (30–90 days). Isolate
concerns with schema discipline and row-level security, not separate stores.

## Alternatives

### Separate analytics store / read replica / warehouse
Rejected at current scale: the analytics workload is a handful of `GROUP BY`
queries over one merchant's recent orders, run interactively. A replica or
warehouse adds sync lag, cost, and a second consistency model for no benefit
yet.

### Materialised views for analytics
Deferred: a straightforward next step if aggregate latency grows. The query
shapes are already centralised in `app/analytics/`, so swapping in a matview or
a nightly snapshot table is a local change.

## Consequences

Positive:
- one backup, one migration path, one connection story
- analytics is always live — no "data is 15 minutes stale" caveat
- transactions can span commerce writes and their audit rows

Negative:
- a heavy analytics query competes with OLTP for the same instance; mitigated by
  narrow time windows and indexes, and bounded by the demo's data volume
- escape hatch (matview → read replica → warehouse) is deliberately left open and
  documented here rather than built now
