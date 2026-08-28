# CommerceOS — Web (`apps/web`)

Next.js 15 (App Router) frontend for CommerceOS. Two surfaces:

- **Customer chat** (`/chat`) — conversational commerce. Product cards, cart /
  order previews, campaign offers, RAG citations, and a button-gated payment
  approval card. Every rich block is reconstructed from the backend's real
  `tool_trace` — nothing is model-rendered HTML.
- **Merchant console** (`/console`) — revenue metrics, the append-only audit
  trail, the full agent tool/policy trace per session, an approval queue, and
  scoped Agent Commerce API key management for external AI buyers.

## Architecture

| Concern | Choice |
|---|---|
| Identity | Supabase Auth (email/password). The access token is sent as `Authorization: Bearer …`; the FastAPI backend verifies it and derives the merchant server-side. |
| Server state | TanStack Query |
| Styling | Tailwind v4 + semantic design tokens in `app/globals.css`. Hand-rolled UI primitives (`components/ui/`). |
| Money | Always formatted for display only (`lib/format.ts`). The backend computes every amount. |

```
app/                (customer)/chat, (merchant)/console/*, login
components/ui        Button, Badge, Card, Field, Spinner, Skeleton, Empty/ErrorState
components/navigation AuthGuard, TopBar, ConsoleSidebar
features/chat        deriveBlocks, useChat, blocks/, AgentActivity, QuickReplies, PaymentApprovalCard
features/console     hooks (queries/mutations), Shared, SessionTrace
lib                  api, auth, supabase, config, format, types
```

## Running locally

1. Backend up on `http://localhost:8000` (`cd ../../backend && uv run uvicorn app.main:app`).
2. `cp .env.local.example .env.local` and fill in (Supabase URL + anon key must
   match the backend's project).
3. `npm install`
4. `npm run dev` → http://localhost:3000

First sign-up is auto-linked to the demo merchant (`mrc_novatech_001`) as
`MERCHANT_ADMIN`.

## Scripts

- `npm run dev` / `npm run build` / `npm run start`
- `npm run typecheck` — `tsc --noEmit`
- `npm run lint` — `next lint`
- `npm test` — Vitest unit/component suite (mocked, offline)
- `npm run test:e2e` — Playwright against a real running stack (see `e2e/README.md`)
- `npm run verify` — typecheck + lint + unit tests + build

## Testing

- **Unit / component** (`npm test`): 70 tests. Pure logic (`deriveBlocks`,
  `lib/api`, `lib/format`), the `useChat` turn state machine, and every chat/console
  component with `fetch` + Supabase auth mocked.
- **E2E** (`npm run test:e2e`): drives the deployed app + FastAPI + live Supabase /
  OpenAI / Razorpay-test. Covers the full customer buy → approval → payment-authorised
  flow and the merchant console (metrics, session trace, AI-buyer key issuance).

## Not done yet

- Real product imagery — cards use deterministic category tiles (the demo image
  set is mostly stock-photo page links, not usable image URLs).
- SSE streaming — the agent endpoint is a single request/response today; the UI
  shows an honest indeterminate "thinking" state, then the real step summary.
