# CommerceOS — Engineering, Security & Guardrails Documentation

This directory defines the engineering rules for building CommerceOS as a production-grade AI-native commerce platform.

Core principle:

> The AI may propose an action. Deterministic backend services, policies, authorization, and state machines decide whether that action is permitted and execute it.

## Documents

### Architecture
- `architecture/system-architecture.md`
- `architecture/security-architecture.md`
- `architecture/data-architecture.md`
- `architecture/decisions/ADR-001-modular-monolith.md`
- `architecture/decisions/ADR-002-supabase.md`
- `architecture/decisions/ADR-003-pinecone.md`
- `architecture/decisions/ADR-004-langgraph.md`
- `architecture/decisions/ADR-005-payment-gating.md`
- `architecture/decisions/ADR-006-agent-commerce-api.md`

### Engineering
- `engineering/coding-standards.md`
- `engineering/repository-structure.md`
- `engineering/api-standards.md`
- `engineering/testing-strategy.md`
- `engineering/git-and-ci.md`

### Security
- `security/security-policy.md`
- `security/agent-guardrails.md`
- `security/payment-security.md`
- `security/prompt-injection-defense.md`
- `security/secrets-and-data-protection.md`

### AI
- `ai/agent-architecture.md`
- `ai/tool-security.md`
- `ai/rag-security.md`
- `ai/evaluation-strategy.md`
- `ai/langfuse-observability.md`

## Non-negotiable principles

1. Never trust the LLM with authoritative money values.
2. Never let the frontend decide payment state.
3. Every sensitive action is authenticated and authorized.
4. Every tenant-scoped resource is isolated.
5. Every financial mutation is idempotent.
6. Every payment webhook is verified and deduplicated.
7. Every agent has bounded execution.
8. Every sensitive tool has a strict schema and allowlist.
9. Retrieved documents are untrusted data, never instructions.
10. Secrets and unnecessary sensitive data never enter prompts, logs, or traces.
11. Routes remain thin; domain services own business logic.
12. Production changes pass automated checks before deployment.
