# CommerceOS — Agent Guardrails

## 1. Agent Authority Model

The agent can:
- reason
- retrieve
- recommend
- request tools
- request approval

The agent cannot independently:
- change authoritative prices
- bypass policies
- execute unrestricted refunds
- access another merchant
- reveal secrets
- directly write payment state

## 2. Tool Allowlist

Each graph has an explicit tool registry.

Shopping:
- search_products
- get_product
- check_inventory
- add_to_cart
- remove_from_cart
- calculate_campaign
- create_order
- request_payment

Support:
- get_order
- search_policy
- get_shipping_status

Growth:
- get_analytics
- analyze_products
- analyze_customers
- recommend_campaign

## 3. Execution Limits

Configure:
- maximum graph steps
- maximum tool calls
- maximum execution time
- maximum retries
- maximum tokens where appropriate

## 4. Structured Outputs

All machine-relevant model outputs must be validated against explicit schemas.

## 5. Policy Enforcement

The agent cannot override a policy result.

## 6. Approval

Payment, large discounts, and sensitive refunds require explicit approval according to merchant policy.

## 7. Explainability

Expose safe summaries:
- what was selected
- relevant evidence
- policy result
- action outcome

Do not expose hidden chain-of-thought.

## 8. Fail Closed

If:
- policy is unavailable
- identity is ambiguous
- order ownership is uncertain
- payment state is unknown

do not execute the sensitive action.

## 9. Anti-loop

Every graph has deterministic termination conditions.

## 10. Tool Result Validation

Tool responses must be typed and validated before entering the next graph step.
