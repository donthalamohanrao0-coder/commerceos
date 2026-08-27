# CommerceOS — Security Policy

## Core Principle

Treat every external input as untrusted.

This includes:
- users
- AI agents
- LLM outputs
- RAG documents
- browser data
- webhooks
- external APIs

## Security Priorities

1. Prevent unauthorized money movement.
2. Prevent cross-tenant data access.
3. Protect credentials and secrets.
4. Prevent AI tool abuse.
5. Maintain an auditable action history.

## Default Deny

New:
- roles
- scopes
- tools
- endpoints
- policy capabilities

must default to denied until explicitly enabled.

## Vulnerability Handling

Security issues should be classified by severity and fixed according to risk.

## Production Rule

Never enable real-money payment capability until the test-mode flow has passed the complete security and payment test suite.
