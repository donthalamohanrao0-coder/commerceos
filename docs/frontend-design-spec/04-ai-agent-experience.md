# CommerceOS — AI Agent Experience

## 1. Purpose

The UI must make agent behavior understandable.

Razorpay's requirement is:

> Every money action explainable, bounded and gated.

The frontend should visibly communicate these properties.

## 2. Agent States

The UI should distinguish:

```text
IDLE
THINKING
RETRIEVING
USING_TOOL
WAITING_FOR_USER
WAITING_FOR_APPROVAL
EXECUTING
SUCCESS
FAILED
RECOVERING
```

## 3. Compact Activity Indicator

Customer UI:

```text
✦ Working on your request

✓ Understanding your requirements
✓ Searching catalog
● Comparing products
○ Checking offers
```

Do not expose hidden chain-of-thought.

Only show safe, high-level action summaries.

## 4. Tool Activity

Safe labels:
- Searching products
- Checking availability
- Calculating eligible offers
- Preparing your order
- Verifying payment requirements

Do not expose:
- system prompts
- hidden reasoning
- private tool arguments
- secrets
- internal policy implementation details

## 5. Explainability

For decisions, show:
- User requirement
- Relevant facts
- Result
- Policy status

Example:

```text
Why was this recommended?

Budget
✓ Within ₹80,000

Use case
✓ Suitable for software development

Specifications
✓ 16GB RAM
✓ 512GB SSD

Availability
✓ In stock
```

## 6. Policy UI

Allowed:

```text
✓ Payment limit verified
✓ Customer confirmation received
```

Blocked:

```text
Action unavailable

The requested discount exceeds the
merchant's configured automatic discount limit.

[Choose another offer]
```

Do not reveal internal bypass information.

## 7. Approval UI

Approval card:

```text
Action requires confirmation

Create payment
₹75,498

Order
ORD-10428

[Cancel] [Confirm & Pay]
```

## 8. Merchant Agent Trace

Merchant users can see a deeper trace than customers.

Show:
- Session
- Node
- Tool
- Duration
- Status
- Input summary
- Output summary
- Policy decision
- Cost/usage where appropriate

## 9. Agent Errors

Use recovery states:

```text
The catalog service is temporarily unavailable.

I haven't created an order.

[Try again]
```

The UI should explicitly communicate when no money action occurred.

## 10. Agent Failure Recovery

For payment uncertainty:

```text
We couldn't confirm the payment state.

No additional payment attempt has been created.

[Check payment status]
```

This is preferable to automatically retrying.

## 11. Agent Commerce API Console

Merchant dashboard should include an optional developer-style screen showing:

```text
Agent Commerce API

Catalog
Search
Cart
Order
Payment

API status: Healthy
Requests today: 1,248
Success rate: 99.4%
```

Incoming requests can be visualized safely.

## 12. AI Buyer Transaction View

Show:

```text
External AI buyer

Request
"I need a coding laptop under ₹80k"

✓ Catalog access
✓ Product match
✓ Inventory verification
✓ Price verification
✓ Policy check
● Awaiting customer approval
```

## 13. No Fake AI

Never show fake activity that didn't happen.

Every displayed tool status should correspond to a real backend event or stream event.

## 14. Streaming Event Contract

Frontend can consume events such as:

```text
agent.started
agent.status
agent.tool.started
agent.tool.completed
agent.message.delta
agent.approval.required
agent.completed
agent.failed
```

Use SSE initially for the customer agent stream.

## 15. Trust Principle

The customer should always understand:
- What the AI selected
- Why it selected it
- What it is about to charge
- Whether approval is required
- Whether payment succeeded
- What happens after a failure
