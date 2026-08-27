# CommerceOS — Agent Architecture

## 1. Orchestration

LangGraph manages:
- state
- routing
- bounded execution
- approvals
- retries
- termination
- failure recovery

## 2. Supervisor

A supervisor determines the appropriate high-level workflow.

Possible flows:
- shopping
- support
- growth

## 3. Nodes

Nodes should have narrow responsibilities.

Examples:
- classify_intent
- retrieve_products
- generate_recommendation
- evaluate_upsell
- calculate_campaign
- validate_cart
- create_order
- request_payment
- await_approval
- handle_failure

## 4. Tools

Tools are the only supported interface between the agent and business operations.

Tools call domain services rather than databases directly.

## 5. State

Agent state should include only information necessary for execution.

Avoid putting unnecessary PII or secrets in graph state.

## 6. Termination

Every graph has explicit terminal states:
- completed
- waiting_for_user
- waiting_for_approval
- failed
- cancelled

## 7. Human/Customer Gates

The graph pauses at approval boundaries rather than trying to infer consent.

## 8. Deterministic Commerce

The following are deterministic:
- pricing
- inventory
- order totals
- policy decisions
- payment state
- refund state

AI can recommend but cannot redefine them.
