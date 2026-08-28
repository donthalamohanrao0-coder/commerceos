# ADR-002 — Supabase as the Primary Data Platform

## Context

CommerceOS needs PostgreSQL, authentication, storage, row-level security, and operational tooling.

## Decision

Use Supabase for PostgreSQL, Auth, Storage, and database management.

## Consequences

Positive:
- PostgreSQL remains the relational source of truth
- integrated authentication
- integrated object storage
- RLS
- fast development

Constraints:
- service-role credentials must remain server-side
- database schema remains portable PostgreSQL
