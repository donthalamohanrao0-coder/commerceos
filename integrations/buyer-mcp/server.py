"""CommerceOS AI-buyer MCP server.

Exposes the merchant's **Agent Commerce API** (`/api/v1/agent-commerce`) as MCP
tools so an AI assistant (Claude Desktop, Claude Code, any MCP client) can act as
an external AI buyer: discover products, get an authoritative quote, place an
order, and — only after the human confirms — authorise payment.

The assistant never sees the merchant id or prices anything itself; the merchant
backend owns pricing, policy, limits and the audit trail. This server just
carries a scoped `ack_live_...` key.

Env:
  AGENT_COMMERCE_BASE_URL   default http://localhost:8000/api/v1/agent-commerce
  AGENT_COMMERCE_KEY        required — an ack_live_... key issued from
                            Merchant console -> AI buyers
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

try:  # optional: pick up a local .env when run directly (not needed via MCP config)
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

# stdio transport: keep our own chatter off the wire, only warnings on stderr.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

BASE_URL = os.environ.get(
    "AGENT_COMMERCE_BASE_URL", "http://localhost:8000/api/v1/agent-commerce"
).rstrip("/")
API_KEY = os.environ.get("AGENT_COMMERCE_KEY", "")

mcp = FastMCP("commerceos-buyer")


def _call(method: str, path: str, **kw: Any) -> Any:
    """One request. Returns the unwrapped `data` on success, or a readable
    ``{"error": ...}`` dict the model can reason about (scope denied, rate
    limited, policy denied, over the transaction limit, ...)."""
    if not API_KEY:
        return {
            "error": "not_configured",
            "detail": (
                "AGENT_COMMERCE_KEY is not set. Issue a key from the Merchant "
                "console (AI buyers -> Issue a key) and put it in this server's env."
            ),
        }
    url = f"{BASE_URL}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {API_KEY}", **kw.pop("headers", {})}
    try:
        resp = httpx.request(
            method,
            url,
            headers=headers,
            timeout=httpx.Timeout(60.0, connect=10.0),
            **kw,
        )
    except httpx.HTTPError as exc:
        return {"error": "network_error", "detail": f"{type(exc).__name__}: {exc}", "url": url}

    try:
        body = resp.json()
    except ValueError:
        body = {}

    if resp.is_success:
        return body.get("data", body)

    detail = body.get("detail") or body.get("error") or resp.text
    hint = {
        401: "the API key is missing or revoked",
        403: "the API key does not hold the scope this call needs",
        404: "not found for this merchant",
        409: "conflicting state",
        422: "invalid arguments",
        429: "per-key rate limit exceeded — slow down and retry",
    }.get(resp.status_code)
    return {
        "error": f"http_{resp.status_code}",
        "detail": detail,
        **({"hint": hint} if hint else {}),
    }


def _line_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for it in items:
        out.append({"product_id": str(it["product_id"]), "quantity": int(it.get("quantity", 1))})
    return out


@mcp.tool()
def list_catalog(limit: int = 20, cursor: str | None = None) -> Any:
    """List the merchant's products (paginated). Returns product_id, name,
    price_paise, in_stock, category and a next_cursor for the following page."""
    params: dict[str, Any] = {"limit": max(1, min(limit, 100))}
    if cursor:
        params["cursor"] = cursor
    return _call("GET", "/catalog", params=params)


@mcp.tool()
def search_catalog(
    query: str | None = None,
    category: str | None = None,
    max_price_paise: int | None = None,
    limit: int = 20,
) -> Any:
    """Search the merchant's catalog by free-text query / category / max price.
    Prices are in paise (₹1 = 100 paise)."""
    payload: dict[str, Any] = {"limit": max(1, min(limit, 100))}
    if query:
        payload["query"] = query
    if category:
        payload["category"] = category
    if max_price_paise is not None:
        payload["max_price_paise"] = int(max_price_paise)
    return _call("POST", "/catalog/search", json=payload)


@mcp.tool()
def get_product(product_id: str) -> Any:
    """Full detail for one product by its product_id (UUID)."""
    return _call("GET", f"/catalog/{product_id}")


@mcp.tool()
def get_quote(items: list[dict[str, Any]]) -> Any:
    """Get an AUTHORITATIVE quote for a set of line items before ordering.
    `items` is a list of {"product_id": "<uuid>", "quantity": <int>}.
    The merchant computes subtotal, discount, shipping, tax and total — never
    guess these yourself."""
    return _call("POST", "/quote", json={"items": _line_items(items)})


@mcp.tool()
def place_order(items: list[dict[str, Any]], buyer_ref: str | None = None) -> Any:
    """Place an order for the given line items. Idempotent — a fresh
    Idempotency-Key is generated per call. `buyer_ref` is your own PO reference.
    Returns order_id, order_number, status and the priced totals. This does NOT
    charge anything."""
    headers = {"Idempotency-Key": f"mcp-{uuid.uuid4()}"}
    payload: dict[str, Any] = {"items": _line_items(items)}
    if buyer_ref:
        payload["buyer_ref"] = buyer_ref
    return _call("POST", "/orders", json=payload, headers=headers)


@mcp.tool()
def get_order(order_id: str) -> Any:
    """Fetch an order by id (status and totals)."""
    return _call("GET", f"/orders/{order_id}")


@mcp.tool()
def request_payment(order_id: str, confirmed: bool = False) -> Any:
    """Authorise payment for an order.

    ALWAYS call this first with confirmed=false. If the merchant policy requires
    it, that returns status "approval_required" and charges nothing — relay the
    amount to the human and get an explicit yes. Only then call again with
    confirmed=true, which is the buyer's consent signal and creates the payment
    against Razorpay test mode. The confirmed call is idempotent."""
    headers = {"Idempotency-Key": f"mcp-pay-{order_id}"}
    return _call(
        "POST",
        f"/orders/{order_id}/payment",
        params={"confirmed": str(bool(confirmed)).lower()},
        headers=headers,
    )


@mcp.custom_route("/healthz", ["GET"])
async def _healthz(_request):  # noqa: ANN001, ANN202
    from starlette.responses import PlainTextResponse

    return PlainTextResponse("ok")


def _run() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        from mcp.server.transport_security import TransportSecuritySettings

        # Hosted behind HTTPS on a fixed domain; the localhost-only DNS-rebinding
        # guard would otherwise 421 every request from claude.ai.
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
        mcp.settings.host = "0.0.0.0"  # noqa: S104 — bind for the platform's proxy
        mcp.settings.port = int(os.environ.get("PORT", "8080"))
        # Optional: serve the endpoint at a hard-to-guess path instead of /mcp.
        # The connector has no auth field, so a secret path is the cheapest guard.
        secret = os.environ.get("MCP_URL_SECRET", "").strip("/")
        if secret:
            mcp.settings.streamable_http_path = f"/{secret}"
        mcp.run(transport="streamable-http")  # endpoint: https://<host>/mcp
    else:
        mcp.run()  # stdio: Claude Desktop / Claude Code


if __name__ == "__main__":
    _run()
