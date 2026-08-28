# CommerceOS — Data Architecture

## 1. Source of Truth

Supabase PostgreSQL is the source of truth for commerce state.

## 2. PostgreSQL Data

Core domains:
- merchants
- users
- customers
- products
- product_variants
- inventory
- carts
- cart_items
- orders
- order_items
- payments
- payment_attempts
- campaigns
- campaign_rules
- policies
- approvals
- agent_sessions
- agent_messages
- agent_actions
- audit_events
- webhook_events
- idempotency_keys
- documents
- document_versions

## 3. Pinecone Data

Pinecone contains embeddings for unstructured merchant knowledge:
- policies
- FAQs
- product documentation
- shipping information
- warranty documents
- brand information

Transactional facts such as stock, order status, price, and payment status must never rely on RAG.

## 4. Redis Data

Redis is non-authoritative.

Use for:
- cache
- rate limits
- short-lived locks
- task queues
- temporary agent state

Never use Redis as the only source of permanent commerce state.

## 5. Data Classification

Public:
- public product information

Internal:
- merchant analytics
- campaign performance

Sensitive:
- customer and order data

Highly sensitive:
- credentials
- secrets
- authentication tokens

## 6. Retention

Define retention periods by data class before production launch.

Payment/provider records must follow applicable legal, contractual, and provider requirements.

## 7. Database Constraints

Use:
- foreign keys
- unique constraints
- check constraints
- not-null constraints
- indexes
- transactional boundaries

Do not rely exclusively on application validation.

## 8. Indexing

Index common access paths:
- merchant_id
- customer_id
- order_id
- payment_id
- status
- created_at

Use composite indexes where query patterns justify them.

## 9. RLS

All exposed merchant-owned tables should have explicit RLS policies.

Service-role credentials are server-only and must never be exposed to the browser.
