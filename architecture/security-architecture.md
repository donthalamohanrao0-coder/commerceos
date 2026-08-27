# CommerceOS — Security Architecture

## 1. Defense in Depth

Security is enforced at multiple layers:

```text
Authentication
 -> Authorization
 -> Tenant isolation
 -> Input validation
 -> Rate limiting
 -> Policy engine
 -> Domain validation
 -> Database constraints/RLS
 -> Audit
```

No single layer is considered sufficient.

## 2. Authentication

Supabase Auth provides identity.

FastAPI validates the authenticated identity and creates the application security context.

## 3. Authorization

Use RBAC plus resource-level authorization.

Roles:
- CUSTOMER
- MERCHANT_OPERATOR
- MERCHANT_ADMIN
- PLATFORM_ADMIN
- EXTERNAL_AGENT

Authorization is enforced server-side.

## 4. Tenant Isolation

Every merchant-owned resource includes `merchant_id`.

The backend derives merchant context from the authenticated identity or API credential.

Never trust a client-supplied `merchant_id` as authorization.

Defense layers:
- FastAPI authorization
- Supabase RLS
- Pinecone namespace isolation
- Service-level ownership checks

## 5. Browser Security

- HTTPS only in production
- Strict CORS
- Secure authentication/session handling
- CSRF protection where applicable
- Content Security Policy
- No secrets in client bundles
- No service-role credentials in browser code

## 6. API Security

Every endpoint must define:
- authentication requirement
- authorization requirement
- request schema
- response schema
- rate limit class
- audit requirement

## 7. External Agent Security

External AI agents receive scoped credentials/capabilities.

Example:
- `catalog:read`
- `cart:write`
- `order:create`
- `payment:request`

Sensitive capabilities such as refunds and campaign administration are not granted by default.

## 8. Sensitive Data

Never send secrets, credentials, payment secrets, or unnecessary PII to:
- OpenAI
- Langfuse
- logs
- browser storage
- analytics systems

## 9. Security Headers

Production frontend should use appropriate headers including:
- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy

Exact CSP values should be derived from actual deployed dependencies rather than copied blindly.

## 10. Rate Limiting

Use Redis-backed rate limits for:
- authentication-sensitive endpoints
- chat
- agent APIs
- payment creation
- refunds
- document upload
- webhook endpoints

## 11. Audit

Security-sensitive actions must generate immutable audit events.

## 12. Secure Defaults

New permissions and tools must default to denied until explicitly enabled.
