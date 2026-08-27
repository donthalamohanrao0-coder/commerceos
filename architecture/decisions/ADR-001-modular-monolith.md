# ADR-001 — Modular Monolith

## Context

CommerceOS has many domains but is initially operated by a small engineering team and has moderate scale.

## Decision

Use a modular monolith for the core FastAPI application with clear domain boundaries and background workers.

## Alternatives

### Microservices
Rejected initially because they add deployment, networking, observability, and consistency complexity without enough benefit.

### Single unstructured application
Rejected because domain boundaries would become unclear.

## Consequences

Positive:
- simpler deployment
- easier local development
- easier transactions
- easier testing
- clear future extraction boundaries

Negative:
- requires discipline around module boundaries
- a single application can become large if architecture is not enforced
