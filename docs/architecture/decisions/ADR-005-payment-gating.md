# ADR-005 — Explicit Payment Gating

## Context

AI agents can reason about purchases, but payment is a high-impact financial action.

## Decision

No payment is executed solely from inferred natural-language intent.

A payment requires:
1. authoritative server-side order
2. validated total
3. policy approval
4. explicit customer confirmation
5. idempotency protection
6. provider request
7. verified provider state

## Consequence

The system is safer and directly satisfies the explainable, bounded, and gated requirement.
