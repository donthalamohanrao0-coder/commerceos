# End-to-end tests

These run against a **real stack**: FastAPI (`:8000`) + this app (`:3000`) + the
live Supabase project + live OpenAI/Razorpay-test. They are not part of `npm test`
(which is fully mocked and offline).

## Prerequisites

1. Backend running: `cd ../../backend && uv run uvicorn app.main:app --port 8000`
2. App running: `npm run build && npm run start` (or `npm run dev`)
3. A confirmed Supabase user. One is provisioned for CI as
   `e2e@commerceos.test` / `E2e-pass-12345`; override with `E2E_EMAIL` /
   `E2E_PASSWORD`.
4. `npx playwright install chromium` once.

## Run

```bash
E2E_EMAIL=e2e@commerceos.test E2E_PASSWORD=E2e-pass-12345 npx playwright test
```

The chat flow drives a real LLM, so it is inherently slower and less
deterministic than the unit suite; assertions are intentionally structural
(a card/button appears) rather than exact copy.
