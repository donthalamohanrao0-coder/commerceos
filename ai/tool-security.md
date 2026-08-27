# CommerceOS — Tool Security

## 1. Tool Contract

Each tool has:
- name
- purpose
- input schema
- output schema
- authorization requirements
- policy requirements
- rate limit
- audit requirement

## 2. Example

```text
request_payment
Input:
- order_id
- confirmation_id

Preconditions:
- authenticated customer
- order ownership
- order unpaid
- server-calculated total
- confirmation valid
- policy passes
- idempotency key
```

## 3. No Direct Database Tools

Do not give the LLM tools such as:
- execute_sql
- update_order_row
- update_payment_row

Expose domain operations instead.

## 4. Tool Allowlists

Tools are registered per agent.

## 5. Argument Validation

Use Pydantic schemas.

Reject unknown fields where appropriate.

## 6. Authorization

Tool execution repeats critical authorization checks even if the graph already checked them.

Defense in depth.

## 7. Rate Limiting

Sensitive tools have stricter rate limits.

## 8. Audit

Financial and administrative tools create audit events.

## 9. Timeouts

External tool calls have explicit timeouts.

## 10. Result Validation

Validate tool results before passing them back into the agent.
