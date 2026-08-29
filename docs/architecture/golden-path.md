# Golden Path — one AI-buyer purchase, end to end

This is the single request flow that satisfies the Razorpay bar: **every money
action explainable, bounded, gated, with an audit trail and one failure handled
gracefully.** Read it top to bottom to see exactly what happens and where the
controls sit.

Actors: an **external AI buyer** holding a scoped API key
(`Authorization: Bearer ack_live_…`), talking only to `/api/v1/agent-commerce/*`.
It never touches an internal service endpoint or the database.

---

## Happy path

### 1. Discover — `POST /agent-commerce/catalog/search`
- `get_agent_principal` hashes the bearer token, looks the key up by unique hash,
  loads its `scopes` and `rate_limit_per_minute`.
- `enforce_rate_limit("agentkey:{key_id}", limit=key budget, 60s)` — 429 if over.
- `require_scope("catalog:search")` — 403 if the key lacks it.
- The session is opened **tenant-scoped**: `SET LOCAL app.current_merchant_id` +
  `SET LOCAL ROLE app_request`, so RLS makes cross-merchant rows invisible even
  if a query is wrong.
- Returns products for that merchant only.

### 2. Price — `POST /agent-commerce/quote`
- Scope `quote:create`.
- Server computes line totals and the order total from **its own** catalog
  prices. The buyer's claimed prices are never trusted.
- No writes, no audit — a quote is not a commitment.

### 3. Commit — `POST /agent-commerce/orders`  *(idempotent, required key)*
- Scope `order:create`.
- **`Idempotency-Key` header is required (HTTP 400 if absent).** The server does
  not mint one for a mutating external call — see ADR-009.
- Optional **`buyer`** block (name, email, phone, line1/line2, city, state,
  postal_code, country): upserted as a `Customer` and written to the order as a
  structured `shipping_address`. (The in-app agent captures the same via a
  `save_shipping_details` tool before `order_create`.)
- `with_idempotency(operation="agent_commerce.create_order", key=…, payload=…)`:
  first call executes and stores the response; any repeat returns the stored
  response byte-for-byte — no second order.
- The order is re-priced server-side again on creation.
- Audit row: **`ORDER_CREATED`** — `actor_type=agent_key`, `actor_id`, the items,
  the server total.

### 4. Surface the amount — `POST /agent-commerce/orders/{id}/payment?confirmed=false`
- Scope `payment:request`.
- Read-only probe. Returns the amount and `approval_required=true`.
- This is the **gate**: the buyer must show this number to its principal and come
  back with an explicit confirmation. Nothing is charged.

### 5. Authorise — `POST /agent-commerce/orders/{id}/payment?confirmed=true`  *(idempotent, required key)*
- `Idempotency-Key` required.
- `PaymentService.request_payment` runs, and **before any write**:
  `PolicyEngine.check_transaction_amount(merchant_id, order.total_paise)`.
  The limit is re-checked here, at execution time — a stale or replayed approval
  cannot exceed current policy.
- On allow: create `Payment`, call Razorpay to create a provider order,
  `transition(payment, "pending")`, audit **`PAYMENT_CREATED`** with
  `policy_decision={allowed: true, reason}`.
- Optional **delegated mandate** on the confirm body (`consent_reference`,
  `max_amount_paise`, `expires_at`): the charge is refused outside it
  (`mandate_exceeded` / `mandate_expired`, nothing written) and it is recorded
  verbatim in the `PAYMENT_CREATED` audit `input`. This is the AP2/ACP/UAP model.
- The response carries a **Razorpay Payment Link** (`payment_link_url`) — the
  external buyer has no browser to run Checkout, so it hands this hosted page to
  its principal.
- The whole thing is wrapped in `with_idempotency` — a retried confirm returns
  the same payment, never a second charge.

### 6. Settle — Razorpay webhook → `POST /api/v1/webhooks/razorpay`
- The payment link is paid (test card `4111 1111 1111 1111`); Razorpay fires
  `payment_link.paid` / `payment.captured`. (The in-app browser flow settles via
  `POST /payments/{id}/verify` instead — same `_settle` code path.)
- Signature verified with `RAZORPAY_WEBHOOK_SECRET`. Bad signature → rejected,
  no state change.
- Provider event id deduplicated — a redelivered webhook is a no-op.
- Matched to the `Payment` by `provider_order_id`, or by our payment id carried
  in the link's `notes` (a payment link runs its own internal Razorpay order).
- Payment state machine advances `pending → processing → paid` (validated
  transitions). Order moves to `paid`.
- Audit row: **`PAYMENT_SUCCEEDED`**.

### 7. Explain
`GET /api/v1/console/activity` (merchant view) shows the session and every
audit row in order: `ORDER_CREATED → PAYMENT_CREATED → PAYMENT_SUCCEEDED`, each
with actor, input, result, and the policy decision. That is the explainability
requirement, satisfied from data, not narration.

---

## The failure, handled gracefully

Buyer tries to authorise an order whose total is above the merchant's
`max_transaction_amount`.

- Step 5 runs `check_transaction_amount` **first**.
- `policy_decision.allowed == false`:
  - Audit row **`PAYMENT_FAILED`** with `input={reason: "policy_denied"}` and
    `policy_decision={allowed: false, reason}`.
  - `PaymentPolicyDenied(reason)` raised → HTTP 4xx with the reason.
  - **No `Payment` row, no Razorpay call, no order state change.** The `_execute`
    closure never runs.
- The buyer gets a clear, machine-readable reason and can lower the amount or ask
  its principal. The merchant sees the blocked attempt in the activity feed.

Bounded (policy), gated (explicit confirm + approval), explainable (audit rows),
and the one failure leaves the system exactly where it started.

---

## Where each control lives

| Control | Code |
| --- | --- |
| Key auth + rate limit | `app/api/deps.py::get_agent_principal` |
| Capability scope | `app/api/deps.py::require_scope` |
| Tenant isolation | `_yield_scoped` → `SET LOCAL … app_request` + RLS (migration 0013) |
| Server-authoritative pricing | `app/agent_commerce/service.py`, `app/domains/orders/service.py` |
| Idempotency | `app/core/idempotency.py::with_idempotency` |
| Payment policy (execution-time re-check) | `app/domains/payments/service.py::request_payment` |
| Payment state machine | `app/domains/payments/` `transition()` |
| Webhook verify + dedup | `app/webhooks/` |
| Audit trail | `app/audit/` — append-only |
| Explainability UI | `apps/web/app/(merchant)/console/activity` |
