#!/usr/bin/env bash
# Start the whole CommerceOS stack for local development / demo:
#   - FastAPI backend on :8000
#   - Next.js frontend on :3000
# Ctrl-C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "backend/.env is missing — copy backend/.env.example and fill it in." >&2
  exit 1
fi
if [[ ! -f "$ROOT/apps/web/.env.local" ]]; then
  echo "apps/web/.env.local is missing — copy apps/web/.env.local.example and fill it in." >&2
  exit 1
fi

pids=()
cleanup() {
  echo
  echo "stopping…"
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "→ backend  http://localhost:8000  (docs: /docs)"
( cd "$ROOT/backend" && uv run uvicorn app.main:app --port 8000 --reload ) &
pids+=($!)

echo "→ frontend http://localhost:3000/chat"
( cd "$ROOT/apps/web" && npm run dev ) &
pids+=($!)

wait
