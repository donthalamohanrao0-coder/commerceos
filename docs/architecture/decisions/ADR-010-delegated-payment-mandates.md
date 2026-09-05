# ADR-010 — Delegated payment mandates (UPI AutoPay)

## Context

The Agent Commerce API's confirmed payment call returns a hosted checkout URL that
a human opens for every purchase. That is a consent gate, but it is not autonomous
commerce — the buyer agent cannot actually settle a purchase on its own.

The AP2 / ACP / UAP model is: a human delegates a bounded spending authority once,
and the agent transacts within it afterwards. On Indian rails that is a Razorpay
UPI AutoPay `as_presented` (variable-amount) mandate, or a card / e-mandate token.

## Decision

Add a standing **payment mandate**: `{max_amount_paise, expires_at,
consent_reference}` registered against a buyer once, via a one-time hosted
authorization page.

- `POST /agent-commerce/mandates` (scope `mandate:create`) registers a Razorpay
  customer + a zero-amount authorization order and returns an `authorization_url`.
- A human opens it once; Razorpay Checkout runs with `recurring: 1`; the signed
  result (or a `token.confirmed` webhook) activates the mandate and stores the
  token.
- On `POST /orders/{id}/payment?confirmed=true`, if the buyer has an **active,
  unexpired** mandate whose ceiling covers the order, the backend charges it via
  `payments/create/recurring` and settles through the same `_settle()` path — no
  `checkout_url`. Otherwise the hosted-checkout flow is unchanged.

Bounds are enforced server-side on every charge: over the ceiling, past the
expiry, or a cancelled/rejected token (`token.cancelled` webhook) all fall back to
hosted checkout. `refund` and `discount-override` remain non-grantable.

The provider integration sits behind the existing `RazorpayClient` seam
(Protocol + Real + Fake). Live UPI AutoPay requires the **Recurring Payments**
feature enabled on the Razorpay account (test mode included); until then the Fake
client exercises the full lifecycle for local dev, tests and the demo.

## Consequences

- An external AI buyer can complete a purchase autonomously within a
  human-delegated ceiling — real agentic commerce, not a checkout hand-off.
- One more provider capability to gate and one more token lifecycle to reconcile
  (`payment_mandates`, migration 0016; `token.*` webhook events).
- The hosted-checkout path stays as the universal fallback, so a missing mandate,
  a lapsed one, or an account without Recurring Payments enabled still works.
