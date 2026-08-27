# CommerceOS — Testing Strategy

## Test Pyramid

```text
          E2E
       Integration
     Unit / Domain
```

Most business rules should be covered at unit/service level.

## Unit Tests

Test:
- policy rules
- pricing
- discounts
- state transitions
- authorization decisions
- domain services

## Integration Tests

Test:
- Supabase/Postgres
- Redis
- Pinecone adapter
- Razorpay adapter
- webhook handling

## Agent Tests

Evaluate:
- intent classification
- tool selection
- tool arguments
- policy compliance
- termination
- refusal of unauthorized actions
- RAG grounding

## Payment Tests

Must include:
- success
- failure
- timeout
- duplicate request
- duplicate webhook
- invalid webhook signature
- already-paid order
- refund boundary
- over-limit transaction

## Security Tests

Include:
- cross-tenant access attempts
- privilege escalation
- malformed tokens
- prompt injection
- malicious tool arguments
- rate-limit enforcement

## E2E

Critical flows:
1. Customer product discovery
2. Add to cart
3. Checkout
4. Payment approval
5. Successful payment
6. Payment failure recovery
7. Merchant campaign creation
8. Knowledge upload
9. Agent trace inspection
10. External AI buyer flow

## Regression

Every production bug should gain a regression test.

## CI

No merge if required tests fail.
