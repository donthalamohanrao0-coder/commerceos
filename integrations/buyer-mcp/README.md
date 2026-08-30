# CommerceOS AI-buyer MCP server

Turns any MCP client (Claude Desktop, Claude Code, …) into an **external AI buyer**
for the CommerceOS merchant. The assistant gets seven tools that map 1:1 onto the
merchant's [Agent Commerce API](../../backend/app/api/v1/agent_commerce.py):

| Tool | Scope it uses | What it does |
|------|---------------|--------------|
| `list_catalog` | `catalog:read` | paginated product list |
| `get_product` | `catalog:read` | one product's full detail |
| `search_catalog` | `catalog:search` | query / category / max-price search |
| `get_quote` | `quote:create` | **authoritative** pricing for line items |
| `place_order` | `order:create` | create an order (auto idempotency key) |
| `get_order` | `order:create` | order status + totals |
| `request_payment` | `payment:request` | consent gate → payment against Razorpay test mode |

The assistant never sees the merchant id and never prices anything itself. Every
call lands in the merchant's audit trail as actor `external_agent`.

## Prerequisites

1. Backend running (`./scripts/dev.sh` → `http://localhost:8000`).
2. A scoped key: **Merchant console → AI buyers → Issue a key** (leave every scope
   checked). Copy the `ack_live_…` value — it's shown once.
3. [`uv`](https://docs.astral.sh/uv/) installed.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "commerceos-buyer": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/commerceos/integrations/buyer-mcp",
        "server.py"
      ],
      "env": {
        "AGENT_COMMERCE_BASE_URL": "http://localhost:8000/api/v1/agent-commerce",
        "AGENT_COMMERCE_KEY": "ack_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

Restart Claude Desktop. The tools appear under the 🔌 icon.

## Claude Code

From the repo root:

```bash
claude mcp add commerceos-buyer \
  --env AGENT_COMMERCE_BASE_URL=http://localhost:8000/api/v1/agent-commerce \
  --env AGENT_COMMERCE_KEY=ack_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  -- uv run --directory "$(pwd)/integrations/buyer-mcp" server.py
```

(or `cp .mcp.json.example .mcp.json` at the repo root and fill in the key — that
scopes it to this project. `.mcp.json` is git-ignored.)

## Try it

> **You:** Buy me a wireless mouse from NovaTech, budget ₹2,000.
>
> **Assistant:** *[search_catalog "mouse"]* → NovaGlide Wireless Mouse, ₹1,499.
> *[get_quote]* → subtotal ₹1,499 + ₹99 shipping = **₹1,598**. Shall I order it?
>
> **You:** Yes.
>
> **Assistant:** *[place_order]* → ORD-4019A9. *[request_payment confirmed=false]* →
> "approval_required — ₹1,598". Confirm the charge?
>
> **You:** Confirm.
>
> **Assistant:** *[request_payment confirmed=true]* → payment created, Razorpay
> `order_TVBoDLtR…`, and a **`checkout_url`**. Open it, pay with test card
> `4111 1111 1111 1111` — the order settles to **paid** automatically.

Then check **Merchant console → Agent activity** (actor `external_agent`) and
**→ Payments**.

## How the payment actually settles

A headless agent can't run Razorpay Checkout, so `request_payment(confirmed=true)`
returns a **`checkout_url`** — `https://commerceos.onrender.com/pay/{payment_id}`,
a one-page CommerceOS checkout for that exact order. A human opens it, Razorpay
Checkout runs there against the order the backend already created, and the browser
posts the signed result to `/pay/{payment_id}/callback`, which verifies the
signature server-side and flips the order to `paid` (writing `PAYMENT_SUCCEEDED`
to the audit trail — the same code path a webhook takes). This is the "agent
proposes the exact amount, consent completes it" model (AP2 / ACP / UAP). No
third-party link quota; identical in production.

The response may *also* carry a `payment_link_url` (a Razorpay Payment Link) when
one could be minted — but **test mode caps an account at 30 links**, so once that
is exhausted `link_error` explains the absence and you use `checkout_url`.

**Optional backend setup** (only needed for the Payment Link path / failure
events) — Razorpay Dashboard → Settings → Webhooks → Add:

| Field | Value |
|---|---|
| URL | `https://commerceos.onrender.com/api/v1/webhooks/razorpay` |
| Secret | the value of `RAZORPAY_WEBHOOK_SECRET` on the backend (must match exactly) |
| Active events | `payment.captured`, `payment.failed`, `payment_link.paid`, `order.paid` |

### Delegated mandate (optional)

Pass `mandate_reference`, `mandate_max_amount_paise` and `mandate_expires_at`
(ISO 8601) to `request_payment` and the backend refuses to charge outside the
mandate (`mandate_exceeded` / `mandate_expired`, nothing written) and records it
verbatim in the `PAYMENT_CREATED` audit row.

### Customer + shipping address

Pass a `buyer` object to `place_order` — `{name, email, phone, line1, city,
postal_code, country}` (plus optional `line2`, `state`). It is stored as the
merchant's `Customer` and as the order's structured `shipping_address`, returned
on `place_order` / `get_order`.

### If the order stays "unpaid" after you paid

The `/pay` callback or a settlement webhook was missed. Unstick it:
`POST /api/v1/console/payments/{payment_id}/reconcile` (merchant-authed) asks
Razorpay directly and settles the order if the provider says it cleared.

## Local smoke test (no MCP client)

```bash
cd integrations/buyer-mcp
cp .env.example .env        # fill in AGENT_COMMERCE_KEY
uv run python -c "import server; print(server.search_catalog(query='mouse', limit=3))"
```

---

## Remote (HTTP) transport

The same `server.py` speaks **streamable-http** when `MCP_TRANSPORT=http`. Endpoint
is `https://<host>/mcp` (or `/<MCP_URL_SECRET>`); `GET /healthz` returns `ok`.

### Authentication

Set **`MCP_AUTH_TOKEN`** and the server requires `Authorization: Bearer <that>` on
the MCP endpoint — every other request gets `401`. `/healthz` stays open (for the
platform health check). Generate one: `openssl rand -hex 32`.

| Client | Sends the bearer? | How |
|--------|-------------------|-----|
| **Claude Code** | ✅ | `claude mcp add --transport http commerceos-buyer https://<host>/mcp --header "Authorization: Bearer <token>"` |
| **Claude Desktop** | ✅ | server entry with `"headers": {"Authorization": "Bearer <token>"}` |
| **Claude API** (`mcp_servers`) | ✅ | `"authorization_token": "<token>"` |
| **claude.ai web connector** | ❌ | UI has only OAuth fields — no header. Use `MCP_URL_SECRET` (obscure path) instead, or front the server with an OAuth provider (WorkOS AuthKit / Stytch / Descope). |

`MCP_URL_SECRET` (serve at `/<string>` not `/mcp`) is independent — use it *with*
the token for defence in depth, or *instead of* it for claude.ai web.

### Run it locally over HTTP

```bash
MCP_TRANSPORT=http PORT=8080 MCP_AUTH_TOKEN=$(openssl rand -hex 32) \
AGENT_COMMERCE_BASE_URL=https://commerceos.onrender.com/api/v1/agent-commerce \
AGENT_COMMERCE_KEY=ack_live_xxxxxxxxxxxxxxxxxxxx \
uv run server.py

curl -s http://localhost:8080/healthz            # -> ok
npx @modelcontextprotocol/inspector             # Streamable HTTP -> http://localhost:8080/mcp, add the Authorization header
```

### Deploy on Render

`render.yaml` defines a **`commerceos-buyer-mcp`** web service (Docker,
`integrations/buyer-mcp/Dockerfile`). Sync the blueprint, then on that service set:

| Env | Value |
|-----|-------|
| `MCP_TRANSPORT` | `http` (preset) |
| `AGENT_COMMERCE_BASE_URL` | `https://commerceos.onrender.com/api/v1/agent-commerce` (preset) |
| `AGENT_COMMERCE_KEY` | an `ack_live_…` key (secret) |
| `MCP_AUTH_TOKEN` | `openssl rand -hex 32` (secret) — the bearer clients must send |
| `MCP_URL_SECRET` | *optional* obscure path |

Verify: `curl https://commerceos-buyer-mcp.onrender.com/healthz` → `ok`, and
`curl -X POST .../mcp` (no auth) → `401`.

### Connect

- **Claude Code / Desktop / API** — use the URL + the `Authorization: Bearer
  <MCP_AUTH_TOKEN>` header (table above). Real auth.
- **claude.ai web** (paid plan) — Settings → Connectors → Add custom connector,
  URL = `https://commerceos-buyer-mcp.onrender.com/<MCP_URL_SECRET>` (leave
  `MCP_AUTH_TOKEN` **unset** for this, since the web UI can't send the header),
  OAuth fields blank → Add. Enable it in a chat.

### Why the `ack_live_` key stays server-side

The buyer key never leaves Render's env. Even if someone reaches the MCP endpoint,
the backend still enforces per-key scopes, the merchant transaction limit, and the
human-approval gate — and it's a Razorpay **test** key. `MCP_AUTH_TOKEN` +
`MCP_URL_SECRET` are the front-door locks; rotate the `ack_live_` key and watch the
audit trail if you suspect leakage.
