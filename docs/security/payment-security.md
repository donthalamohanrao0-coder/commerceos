# CommerceOS — Payment Security

## 1. Payment Authority

The backend calculates the authoritative payable amount.

Never accept a final payment amount from the browser or LLM as authoritative.

## 2. Payment Lifecycle

```text
ORDER_CREATED
 -> PAYMENT_PENDING
 -> PAYMENT_PROCESSING
 -> PAID
```

Failure:
```text
PAYMENT_PROCESSING
 -> FAILED
```

Refund:
```text
PAID
 -> REFUND_REQUESTED
 -> REFUND_PROCESSING
 -> REFUNDED
```

Transitions must be validated.

## 3. Customer Confirmation

Payment requires explicit confirmation unless a separately defined, approved policy explicitly allows otherwise.

The initial product should require confirmation.

## 4. Idempotency

Every payment mutation requires an idempotency key.

## 5. Webhooks

Webhook flow:

```text
Receive
 -> verify signature
 -> validate event
 -> deduplicate
 -> validate state transition
 -> update DB
 -> audit
```

## 6. Duplicate Protection

Prevent:
- duplicate payment attempts for the same operation
- duplicate webhook processing
- duplicate refunds
- payment on already-paid orders

Use database constraints plus idempotency.

## 7. Payment Failure

Never blindly retry an uncertain payment.

First resolve provider state.

## 8. Refunds

Refund authorization is policy-controlled.

Example:
- automatic refund <= configured threshold
- merchant approval above threshold

## 9. Logging

Never log payment secrets or sensitive credentials.

Provider reference IDs may be logged when appropriate.

## 10. Testing

All payment edge cases must be covered before production release.
