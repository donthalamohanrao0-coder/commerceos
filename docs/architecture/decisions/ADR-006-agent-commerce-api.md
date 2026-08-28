# ADR-006 — Agent Commerce API

## Context

Razorpay's challenge includes making merchants transactable by AI buyers.

## Decision

Expose a versioned, capability-scoped Agent Commerce API.

Core capabilities:
- catalog read
- search
- cart operations
- order creation
- payment request

Sensitive capabilities are denied by default.

## Consequences

CommerceOS can support external AI buyers without exposing internal database or service interfaces.
