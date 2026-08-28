# ADR-003 — Pinecone for Merchant Knowledge Retrieval

## Context

CommerceOS needs tenant-isolated semantic retrieval over merchant documents.

## Decision

Use Pinecone for vector retrieval, with merchant-specific namespaces and metadata.

## Consequences

Positive:
- clean tenant isolation
- scalable semantic retrieval
- separate vector infrastructure from transactional database

Constraint:
- PostgreSQL remains authoritative for structured commerce data
