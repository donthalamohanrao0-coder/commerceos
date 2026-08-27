# CommerceOS — System Architecture

## 1. Architecture Style

CommerceOS uses a modular monolith for the core application with dedicated background workers and external integrations.

We deliberately avoid premature microservices.

```text
Next.js / Vercel
       |
       v
FastAPI / Render
       |
       +-- Auth
       +-- Catalog
       +-- Cart
       +-- Orders
       +-- Payments
       +-- Campaigns
       +-- Customers
       +-- Policies
       +-- Approvals
       +-- Audit
       +-- Agent Runtime
       |
       +-- Supabase PostgreSQL/Auth/Storage
       +-- Redis
       +-- Pinecone
       +-- OpenAI
       +-- Razorpay
       +-- Langfuse
       +-- Sentry/OpenTelemetry
```

## 2. Trust Boundaries

1. Browser is untrusted.
2. LLM output is untrusted.
3. Retrieved RAG content is untrusted.
4. External AI agents are untrusted.
5. Webhooks are untrusted until verified.
6. Database is the source of commerce truth.
7. Policy engine is authoritative for agent permissions.
8. Payment provider state is authoritative for payment status after verification.

## 3. Request Flow

```text
Request
 -> Authentication
 -> Authorization
 -> Tenant resolution
 -> Input validation
 -> Domain service
 -> Policy validation where required
 -> Repository/integration
 -> Audit event where required
 -> Response
```

## 4. Agent Flow

```text
User
 -> Agent Gateway
 -> LangGraph
 -> OpenAI
 -> Structured tool request
 -> Tool validation
 -> Policy engine
 -> Domain service
 -> Result
 -> Audit/trace
 -> Agent
 -> User
```

## 5. Financial Flow

```text
Customer
 -> Cart
 -> Server-calculated order
 -> Customer confirmation
 -> Payment policy
 -> Idempotency
 -> Razorpay
 -> Webhook
 -> Signature verification
 -> Payment state machine
 -> Order state update
 -> Audit event
```

## 6. Background Work

Use workers for:
- document parsing
- embedding generation
- Pinecone indexing
- analytics aggregation
- notifications
- long-running non-interactive jobs

Interactive payment and order state transitions must not depend on an eventually consistent background job to become correct.

## 7. Availability

Health endpoints:
- `/health/live`
- `/health/ready`

Readiness should verify only dependencies required for the service to accept traffic.

## 8. Failure Principle

Fail closed for:
- payments
- refunds
- high-value discounts
- authorization
- tenant access

Fail gracefully for:
- recommendations
- optional analytics
- non-critical AI enrichment
