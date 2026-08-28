# CommerceOS — Demo Script

~6 minutes. Shows the four things the problem statement grades on: **every money
action explainable, bounded and gated**, the **audit trail**, and **one failure
handled gracefully**.

## Setup

```bash
uv run --project backend python db/seeds/generate_demo_history.py   # once: 95 orders / 60 days for the charts
./scripts/dev.sh          # backend :8000 + frontend :3000
```

Open `http://localhost:3000` → sign up / sign in (any email; first sign-in is
auto-linked to the demo merchant **NovaTech**).

Demo user already provisioned: `e2e@commerceos.test` / `E2e-pass-12345`.

---

## 1. Conversational checkout — the AI proposes, the backend decides, a human gates (2 min)

On **/chat**:

1. Type: **"Show me a laptop for coding under ₹80,000"**
   → watch the activity stream: *Searching the catalogue…* → a product card.
2. Click **Add to cart** on the NovaBook Pro 14.
   → *Updating your cart…* → cart preview + an **upsell card**: *"Frequently
   bought together"* (sleeve, dock — from real purchase history via
   `cross_sell_product_codes`). Items whose category would unlock an as-yet
   ineligible campaign show a green **"Unlocks Laptop Setup Bonus (₹500 off)"**
   tag (computed server-side by `CampaignService.near_miss_category_unlocks`, not
   invented by the model). Add one or click **Not now**. The top-right **Cart**
   button opens the cart drawer.
3. Click **Checkout** (or type "check out and pay").
   → the agent prepares the order and **stops** at the **payment approval card**:
   *"Review your purchase — ₹74,999 — Requires your confirmation."*

   **Say this:** the agent has done everything except move money. It cannot.
   The card lists what the backend verified (availability, price, campaign,
   payment policy).

4. Click **Confirm & Pay** → the real **Razorpay Checkout** window opens (test
   mode). Pay with test card **4111 1111 1111 1111**, any future expiry, any CVV.
   → the browser hands the result to the backend, which **verifies the signature
   server-side** and captures → *"Payment received — your order is confirmed."*
   (Order and Payment both flip to `paid`; the webhook path reaches the same
   `confirm_captured`.)

   If you close the Razorpay window, the order stays reserved and a **Pay ₹74,999**
   button remains — nothing is charged until Razorpay confirms.

---

## 2. The audit trail (1 min)

Top nav → **Merchant console** → **Overview**.

- Revenue / AOV / orders are the **authoritative** figures (computed from orders,
  not anything the agent said).
- Scroll to **Audit trail** — the turn you just did, append-only:
  `APPROVAL_REQUESTED → ORDER_CREATED → PAYMENT_CREATED → APPROVAL_GRANTED →
  PAYMENT_SUCCEEDED`. The order shows on **Console → Payments** as `captured`.

Below the audit trail: the **Analytics** section — revenue trend, orders/day,
revenue by category, where orders come from (in-app agent vs. customer vs. AI
buyer), status mix, top products.

**Console → Agent activity** → sessions grouped **Today / Yesterday / Earlier
this week / …**, filter by workflow. Click one → the full trace drawer: every
tool call, its duration, input/output summary, and the **policy decision**.

**Console → Knowledge base** → the grounding corpus (6 indexed docs, chunk counts,
index version). The **Retrieval preview** box runs the exact semantic search the
shopping agent runs — type *"what is the return window"* → ranked passages with
similarity scores. This is what "grounded, not hallucinated" means: the agent can
only cite what shows up here.

---

## 3. Sellable to an AI buyer, end to end (2 min)

**Console → AI buyers** → *Issue a key* (leave all scopes checked) → copy the
`ack_live_…` key.

Three ways to drive it as an external buyer, pick one:

- **A real AI assistant** — `integrations/buyer-mcp/` is an MCP server exposing
  the Agent Commerce API as tools. Point Claude Desktop / Claude Code at it
  (README in that folder), then: *"buy me a wireless mouse from NovaTech"* — the
  assistant searches, quotes, orders, and stops for your confirmation before pay.
- **One command** — `scripts/agent_buyer_demo.sh <ack_live_key>` runs the whole
  happy path and prints where to look on the merchant side.
- **Raw curl** (below) — to also show the failure cases.

```bash
KEY=ack_live_xxxxxxxxxxxxxxxx
B=http://localhost:8000/api/v1/agent-commerce
H="Authorization: Bearer $KEY"

# 1. agent-readable catalog
curl -s "$B/catalog?limit=3" -H "$H"

# 2. authoritative quote (the buyer never computes the price itself)
curl -s -X POST "$B/quote" -H "$H" -H 'Content-Type: application/json' \
  -d '{"items":[{"product_id":"<paste a product_id>","quantity":2}]}'

# 3. place the order (idempotent)
curl -s -X POST "$B/orders" -H "$H" -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-po-1' \
  -d '{"items":[{"product_id":"<same id>","quantity":2}],"buyer_ref":"DEMO-PO-1"}'

# 4. request payment — WITHOUT confirming -> the consent gate
curl -s -X POST "$B/orders/<order_id>/payment" -H "$H" -H 'Idempotency-Key: demo-pay-1'
#   -> {"status":"approval_required", ...}   (nothing charged)

# 5. confirm -> payment intent created against Razorpay test mode
curl -s -X POST "$B/orders/<order_id>/payment?confirmed=true" -H "$H" -H 'Idempotency-Key: demo-pay-1'
#   -> {"status":"payment_created","provider_order_id":"order_...", ...}
```

**Say this:** the buyer proves *intent and consent* (`?confirmed=true`); the
merchant's backend creates and captures the payment. Refunds / discount overrides
aren't even grantable scopes.

Back in **Console → AI buyers** the key shows *last used*, and **Overview →
Audit trail** has the buyer's calls.

---

## 4. One failure, handled gracefully (30 s)

Two options:

**A — over the merchant's transaction limit:** ask the chat to buy a very large
quantity, approve it → the agent comes back with *"Payment couldn't be completed…
No charge was created."* and the conversation continues. No retry loop.

**B — rate limit:** issue a key with `rate_limit_per_minute: 3`, fire 4 catalog
calls → the 4th returns **429**, no partial state.

---

## Deploying it

See [DEPLOY.md](DEPLOY.md): frontend → Vercel, API + Celery worker → Render
(`Dockerfile` + `render.yaml` at the repo root), Postgres stays on Supabase.

---

## The one-liner

> The AI can *propose* any money action. Deterministic services, policies and
> state machines decide whether it's allowed and execute it — and every step is
> in the audit trail.
