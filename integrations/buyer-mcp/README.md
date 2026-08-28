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
> `order_TVBoDLtR…`. Done.

Then check **Merchant console → Overview → Audit trail** and **→ Payments**.

## Local smoke test (no MCP client)

```bash
cd integrations/buyer-mcp
cp .env.example .env        # fill in AGENT_COMMERCE_KEY
uv run python -c "import server; print(server.search_catalog(query='mouse', limit=3))"
```
