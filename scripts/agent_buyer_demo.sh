#!/usr/bin/env bash
# Simulate an external AI buyer transacting with the NovaTech merchant end to end
# through the Agent Commerce API (ADR-006). No browser, no internal endpoints —
# just a scoped `ack_live_...` key.
#
#   1. Issue a key:  Merchant console -> AI buyers -> Issue a key  (leave scopes checked)
#   2. Run:          scripts/agent_buyer_demo.sh ack_live_xxxxxxxxxxxx
#
# Env overrides:  API_BASE (default http://localhost:8000/api/v1)

set -euo pipefail

KEY="${1:?usage: agent_buyer_demo.sh <ack_live_key>}"
API_BASE="${API_BASE:-http://localhost:8000/api/v1}"
B="$API_BASE/agent-commerce"
H="Authorization: Bearer $KEY"
RUN="demo-$(date +%s)"

jq_or_cat() { if command -v jq >/dev/null; then jq "$@"; else cat; fi; }
step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "1. Agent-readable catalog (buyer discovers products)"
curl -sS "$B/catalog?limit=3" -H "$H" | jq_or_cat '.data.products[] | {product_id, name, price_paise, in_stock}'

step "2. Search the catalog"
PID=$(curl -sS -X POST "$B/catalog/search" -H "$H" -H 'Content-Type: application/json' \
  -d '{"query":"mouse","limit":1}' | jq_or_cat -r '.data.products[0].product_id')
echo "picked product_id=$PID"

step "3. Authoritative quote (the buyer never prices anything itself)"
curl -sS -X POST "$B/quote" -H "$H" -H 'Content-Type: application/json' \
  -d "{\"items\":[{\"product_id\":\"$PID\",\"quantity\":1}]}" | jq_or_cat '.data'

step "4. Place the order (idempotent — Idempotency-Key: ord-$RUN)"
OID=$(curl -sS -X POST "$B/orders" -H "$H" -H 'Content-Type: application/json' \
  -H "Idempotency-Key: ord-$RUN" \
  -d "{\"items\":[{\"product_id\":\"$PID\",\"quantity\":1}],\"buyer_ref\":\"PO-$RUN\"}" \
  | tee >(jq_or_cat '.data' >&2) | jq_or_cat -r '.data.order_id')

step "5. Request payment WITHOUT confirming -> the consent gate"
curl -sS -X POST "$B/orders/$OID/payment" -H "$H" -H "Idempotency-Key: pay-$RUN" | jq_or_cat '.data'

step "6. Confirm (?confirmed=true) -> payment intent against Razorpay test mode"
curl -sS -X POST "$B/orders/$OID/payment?confirmed=true" -H "$H" -H "Idempotency-Key: pay-$RUN" | jq_or_cat '.data'

step "7. Replay step 6 (same Idempotency-Key) -> identical result, no double charge"
curl -sS -X POST "$B/orders/$OID/payment?confirmed=true" -H "$H" -H "Idempotency-Key: pay-$RUN" | jq_or_cat '.data.status'

cat <<EOF

Done. Now check the merchant side:
  Console -> Payments        the order shows a captured/created payment
  Console -> Overview        Audit trail has APPROVAL_REQUESTED -> ORDER_CREATED ->
                             PAYMENT_CREATED for actor "external_agent"
  Console -> AI buyers       the key's "last used" just moved
EOF
