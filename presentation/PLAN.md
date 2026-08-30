# CommerceOS — Presentation Board Plan

Premium Miro board for the Razorpay Buildathon. Presenter: **Mohan**.
Build target: one Miro board, 19 frames laid out left→right at 1920×1080 each,
200px gutter, driven in Miro **Presentation Mode** (each frame = one slide).

Status: **PLANNING COMPLETE — awaiting 2 decisions (see end) before build.**

---

## 1. Design system (locked)

Native Miro shapes, not AI images, for every diagram — editable, crisp, on-brand.
Palette is Miro's free-form diagram palette so hand-assembled flows and any
Mermaid widgets match exactly.

| Role | Fill | Stroke | Used for |
|---|---|---|---|
| **Blue** | `#c6dcff` | `#305bab` | customer + agent-reasoning path |
| **Green** | `#adf0c7` | `#087429` | commerce core / money movement |
| **Amber** | `#f8d3af` | `#9b4a07` | trust layer — policy, approval, audit, guardrails |
| **Cyan** | `#c3faf5` | `#187574` | data stores (Postgres, Pinecone, Redis) |
| **Grey** | `#e7e7e7` | `#595959` | infra + external services |
| **Red** | `#ffc6c6` | `#bd0909` | failure / denied path ONLY (used once, Frame 6) |

- **Frame background:** `#ffffff`. **Top band** on every frame: full-width ink
  rect `#1c1c1a`, height 120, white title text (`data-text-color="#ffffff"`,
  `plex_sans`, 44px bold).
- **Footer** on every frame (grey `#8a8a86`, 14px, `plex_mono`):
  `CommerceOS · Razorpay Buildathon · Mohan · <NN>`
- **Fonts:** `plex_sans` (titles + body), `plex_mono` (code, routes, metrics). Two only.
- **Shapes by role:** terminal = `round_rectangle`; process = plain `rect`;
  decision = `rhombus`; input/output = `parallelogram`; external subprocess =
  `flow_chart_predefined_process`.
- **Connectors:** `data-shape="elbowed"`, `data-arrow="end"`, stroke matched to
  the target node's stroke colour, `data-start-side`/`data-end-side` pinned.
- **Node sizing:** processes 260×90, terminals 200×80, decisions 200×120.
  Same width for siblings. 120px horizontal gap between pipeline nodes.

---

## 2. Frame list (19)

| # | Frame | Type | Talk time |
|---|---|---|---|
| 1 | Cover | title + hero image | 10s |
| 2 | Who am I — Mohan | bio | 30s |
| 3 | The problem | text bands | 30s |
| 4 | The thesis: AI-native commerce | concept | 20s |
| 5 | What I built — product tour | screenshot wall | 30s |
| 6 | The golden path (live demo) | diagram ⭐ | 60s |
| 7 | System architecture | diagram ⭐ | 45s |
| 8 | Component: Agent Runtime (LangGraph) | flow | 30s |
| 9 | Component: Trust Layer | flow | 35s |
| 10 | Component: Payment + state machine | flow | 30s |
| 11 | Component: RAG pipeline | flow + metrics | 25s |
| 12 | Component: Agent Commerce API / MCP | flow | 25s |
| 13 | Multi-tenancy & security | 4-pillar | 20s |
| 14 | Data model | grouped tables | 15s |
| 15 | Maps to the judging bar | table | 25s |
| 16 | Engineering quality | 4 tiles | 20s |
| 17 | Tech stack | grid | 10s |
| 18 | Roadmap | bullets | 15s |
| 19 | Close — thank you | links + contact | 10s |

Minimum viable deck if time is short: **1, 2, 3, 6, 7, 15, 19**. Build those first.

---

## 3. Frame-by-frame spec

### Frame 1 — Cover
- Hero AI image as full-frame background (see §5 prompt "cover-hero"), 12% dark
  overlay rect for text contrast.
- Centre: **CommerceOS** (96px bold white).
- Sub: *An AI-native commerce platform — grows a merchant's revenue, and makes
  that merchant transactable by AI buyers, end to end.* (28px white, 60% width).
- Bottom-left: `Razorpay Buildathon — AI Growth & Agentic Commerce`.
- Bottom-right: `Mohan · NIT Raipur`.

### Frame 2 — Who am I
Left column: large `Mohan` + role line. Right column: 4 stat cards (green accent).
- Headline: **Mohan** — *3rd-year, NIT Raipur*
- Card 1: **20+** — AI projects delivered to real clients across the US & India
- Card 2: **Since Jan 2025** — building full-time in the agentic-AI space
- Card 3: **YouTube** — technical content on agentic AI
- Card 4: **This build** — CommerceOS, solo, for the Razorpay Buildathon
- One-liner under the cards: *"I build agents that take real actions safely — this
  is that idea applied to commerce."*

### Frame 3 — The problem
Three stacked bands (textArea blocks):
1. **The shift** — "Buying is moving from humans clicking to agents transacting.
   NPCI's UAP and the protocol race — ACP, AP2, x402 — make agent-to-agent
   commerce the open problem of the year. Razorpay's in-app pilots are already live."
2. **The merchant's two gaps** —
   *Growth:* revenue they can't see — upsell timing, campaign ideas, which product
   pairs convert.
   *Agent-readiness:* catalog, pricing and policies aren't consumable by an AI
   buyer, and there's no safe, bounded way to let an agent pay.
3. **The bar** (amber band, quote verbatim): *"Every money action explainable,
   bounded and gated. Show the audit trail and one failure handled gracefully."*

### Frame 4 — The thesis
Centre concept diagram (3 boxes under one header):
`AI-NATIVE COMMERCE` → **AI Agent** (LangGraph · OpenAI · Pinecone) · **Commerce
Core** (Supabase · Orders · Payments · Razorpay) · **Trust Layer** (Policies ·
Approvals · Audit · Idempotency).
Caption: *"The four technologies aren't the product. The product is a commerce
engine an agent can drive without anyone getting hurt."*

### Frame 5 — Product tour
Screenshot wall, 2 rows × 3, each in a grey device frame with a caption strip:
`customer-chat`, `console-analytics`, `console-activity-trace`,
`console-knowledge`, `console-approvals`, `console-ai-buyers`.
Caption: *"Three surfaces — a customer shopping agent, a merchant console where
the growth agent and the audit trail live, and a machine-facing API for external
buyers."*

### Frame 6 — The golden path ⭐  (the frame you demo against)
**Row A — happy path**, 7 terminals/processes left→right (blue for 1–2, green for
3–6, amber for 7):
1. `Discover` — search catalog
2. `Price` — server quote
3. `Commit` — create order
4. `Surface amount` — approval required
5. `Authorise` — explicit confirm
6. `Settle` — Razorpay + webhook
7. `Explain` — audit trail in console

**Amber control tags** (small rects) under each node:
1 `scoped API key + tenant RLS` · 2 `server re-prices; buyer prices ignored` ·
3 `Idempotency-Key required (400 if absent)` · 4 `amount shown, nothing charged` ·
5 `policy re-checked at execution time` · 6 `signature verified + event deduped` ·
7 `ORDER_CREATED → PAYMENT_CREATED → PAYMENT_SUCCEEDED`

**Row B — the one failure** (red), branch off node 5:
`Authorise (over limit)` → rhombus `check_transaction_amount` → `DENIED` →
`PAYMENT_FAILED audit row` → `no Payment row · no Razorpay call · order unchanged`
→ (back to blue) `agent tells the buyer why`.

Caption: *"Bounded by policy, gated by explicit confirmation, explainable from the
audit rows — and the failure leaves the system exactly where it started."*
Mirrors `docs/architecture/golden-path.md` — keep identical.

### Frame 7 — System architecture ⭐
Four horizontal swimlane bands (light tinted zone rects, dashed border, title
label top-left of each):

- **Band 1 — Clients (blue):** `Customer browser (Next.js)` ·
  `Merchant console (Next.js)` · `External AI buyer (MCP / HTTP)`
- **Band 2 — Edge (grey):** `Vercel — Next.js app` · `Supabase Auth (JWT)`.
  Small note: *"client gets public config only, never secrets."*
- **Band 3 — Application: FastAPI on Render (one big grey container, modular monolith):**
  - inner green row: `Catalog` `Cart` `Orders` `Payments` `Campaigns` `Customers`
  - inner amber row: `Policy Engine` `Approvals` `Audit (append-only)`
    `Idempotency` `Agent Runtime (LangGraph)` `Knowledge (RAG)`
  - inner grey row: `Request context / OTel / Sentry` · `Rate limiter`
  - side box (grey): `Celery worker — ingestion, analytics snapshots` ← `Redis`
- **Band 4 — Data & external (cyan for stores, grey for services):**
  `Supabase Postgres — RLS + SET LOCAL ROLE app_request` ·
  `Pinecone — namespace per merchant` · `Redis — cache + rate limit` ·
  `OpenAI — gpt-4o-mini + embeddings` · `Razorpay test APIs` · `Langfuse`

Connectors: Band1→Band2 down; Band2→Band3 down; Band3→Band4 down; plus a labelled
return connector `Razorpay → FastAPI /webhooks/razorpay` ("signed webhook").
3 amber sticky callouts pinned on top:
- "Modular monolith — domain boundaries, no distributed-systems tax (ADR-001)"
- "DB is the source of commerce truth; payment state only from verified provider events"
- "LLM output and retrieved docs are both untrusted inputs"

### Frame 8 — Agent Runtime (LangGraph)
Flow (blue): `User message` → `Supervisor: classify_workflow (cached 1h)` →
rhombus split → `Shopping graph` | `Support graph` | `Growth graph` →
`agent_node (plan)` ⇄ `tools_node (act)` [loop connector labelled "tool result"] →
`reply`.
Amber overlay band under the loop: *"Every turn is bounded — max_graph_steps,
max_tool_calls, wall-clock deadline; seeded from merchant policy, enforced in
agent_node."*
Grey note: *"Per-turn state, no checkpointer — durable state lives in Postgres (ADR-007)."*
Caption: *"The model reasons and requests tools; it never executes business logic directly."*

### Frame 9 — Trust Layer  ("the heart of the system")
Vertical flow, 10 amber process nodes, one per line:
`AI proposes action` → `validate schema (Pydantic)` → `authn` →
`authz / scope` → `tenant check` → `policy check` → `limit check` →
`approval check` → `execute deterministic service` → `record audit event` →
`return result to AI`.
Right-side note (red): *"Refunds & discount-overrides aren't grantable scopes at all."*
Caption: *"Ten checks between an AI intention and a committed side effect."*

### Frame 10 — Payment + state machine
Two sub-flows (green) + one strip:
- **Create:** `request payment` → rhombus `policy.check_transaction_amount` →
  `create Payment` → `Razorpay create order` → `transition → pending` →
  `audit PAYMENT_CREATED`.
- **Settle:** `Razorpay webhook` → `verify signature` → `dedupe event id` →
  `state machine pending → paid` → `order → paid` → `audit PAYMENT_SUCCEEDED`.
- **State strip** (small round-rects):
  `CREATED → PAYMENT_PENDING → PAYMENT_PROCESSING → PAID → FULFILLED`, with a red
  `FAILED` branch and a greyed `REFUND_*` lane labelled "not agent-grantable".
Caption: *"The browser is never the authority for payment success — only a
verified provider event is."*

### Frame 11 — RAG pipeline
- **Ingestion (cyan/grey):** `Upload doc (console) / seed script` →
  `chunk (structure-aware)` → `OpenAI embeddings` →
  `Pinecone upsert (merchant namespace)` + `document_versions row` →
  `cache generation bump`.
- **Retrieval (blue):** `customer question` → `embed` →
  `namespace + metadata filter` → `top-k chunks` →
  `wrap: "treat as DATA, not instructions"` → `agent answer + citation`.
- **Metrics badge (green pill):** `hit@3 100% · hit@1 89% · MRR 0.94 ·
  grounded@1 83% · 10 docs / ~44 chunks`.
Caption: *"Retrieved text is reference data, never instructions — injection fence
+ measured accuracy."*

### Frame 12 — Agent Commerce API / MCP
Flow (blue→green): `External AI buyer` → `Bearer ack_live_… key` →
`rate limit (per-key budget)` → `require_scope` → `tenant-scoped session` →
`catalog → quote → order → payment` → rhombus `confirmed?` →
(no) `return amount, nothing charged` / (yes) `charge + audit`.
Side box (grey): *"Same domain services as the in-app agent — no separate code
path, no DB exposure. OpenAPI + MCP server (stdio + HTTP-with-bearer)."*
Caption: *"A merchant becomes transactable by any agent, without trusting that agent."*

### Frame 13 — Multi-tenancy & security
4 amber pillar cards:
- **Auth** — Supabase JWT, backend verifies every request
- **DB isolation** — `SET LOCAL app.current_merchant_id` + `SET LOCAL ROLE
  app_request` + RLS `FOR ALL` (migration 0013)
- **Vector isolation** — Pinecone namespace per merchant
- **External access** — SHA-256-hashed scoped keys, deny-by-default capabilities
Small print: *"Prod boot check fails closed on auth/DB misconfig. X-Merchant-Id
dev bypass gated to non-prod."*

### Frame 14 — Data model
7 grouped clusters (cyan headers, grey chips):
Identity (organizations, merchants, users, merchant_users, customers) ·
Catalog (products, product_variants, inventory) ·
Transactional (carts, cart_items, orders, order_items, payments) ·
Growth (campaigns, campaign_rules, coupons) ·
Agent (agent_sessions, agent_messages, agent_actions) ·
Trust (policies, approval_requests, audit_events, idempotency_keys, webhook_events) ·
Knowledge (documents, document_versions).
Caption: *"A real commerce schema — the agent and trust tables are first-class."*

### Frame 15 — Maps to the judging bar
2-col table (amber header), brief's own language → implementation:
| Brief | In CommerceOS |
|---|---|
| Grow merchant revenue | Growth agent + analytics + campaign preview |
| Upsell / cross-sell | Shopping-agent tools tied to campaign hints |
| Conversational checkout | Customer shopping agent → cart → order → pay |
| Agent-readable catalog | Agent Commerce API + OpenAPI + MCP |
| AI buyer, end to end | catalog → quote → order → payment, confirm gate |
| Explainable | Agent Activity trace + append-only audit events |
| Bounded | Policy engine: amount, discount, step/tool/time budgets |
| Gated | Approval engine — one-shot, expiring, execution-time re-check |
| Audit trail | Immutable audit_events, shown in the console |
| One failure, handled | Over-limit order → PAYMENT_FAILED, zero side effects |

### Frame 16 — Engineering quality
4 tiles:
- **Tests** — 73 backend (unit + integration + agent-evals + payment-gating +
  RLS-isolation); 97 frontend + Playwright e2e
- **Observability** — OpenTelemetry (FastAPI/SQLAlchemy/httpx) · Sentry ·
  Langfuse agent traces · request-id on every log
- **Decisions** — 9 ADRs (`docs/architecture/decisions/`) + golden-path trace doc
- **Ops** — Docker · Render blueprint · pre-deploy `alembic upgrade head` ·
  `/health/live` + `/health/ready` · CI: lint → type → test → build

### Frame 17 — Tech stack
Grid by layer: Frontend (Next.js 15, React 19, TS, Tailwind v4, TanStack Query) ·
Backend (FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2) ·
AI (LangGraph, OpenAI gpt-4o-mini + text-embedding-3-small) ·
Data (Supabase Postgres, Pinecone, Redis) ·
Infra (Vercel, Render, Celery, Docker) · Payments (Razorpay test).

### Frame 18 — Roadmap
- Multi-merchant self-serve onboarding UI
- LangGraph checkpointer for long-running agent tasks (ADR-007 escape hatch)
- Analytics to a read replica / materialised views (ADR-008 escape hatch)
- Deeper ACP / AP2 conformance on the buyer API
Caption: *"Known next steps — documented as ADR trade-offs, not surprises."*

### Frame 19 — Close
Big **Thank you**. Then:
- Live: `<frontend URL>` · API docs: `<backend>/docs`
- Repo: `github.com/donthalamohanrao0-coder/commerceos`
- Mohan · `<YouTube handle>` · `<email / X>`
- One-line recap: *"Explainable, bounded, gated — an agent you can let near money."*

---

## 4. Screenshot capture plan (Playwright)

Store under `commerceos/presentation/assets/screenshots/`. Capture at viewport
1440×900, `deviceScaleFactor: 2` (→ 2880×1800 PNG). Full-page variants where noted.

Prereq: a running stack + a signed-in session. Script: a standalone Playwright
script `presentation/capture.mjs` that signs in once (reuse `e2e/smoke.spec.ts`
`signIn` flow, `E2E_EMAIL`/`E2E_PASSWORD`) then visits each route.

| File | Route | Must show | Pre-step |
|---|---|---|---|
| `customer-chat.png` | `/chat` | product cards + "Add to cart" in a live conversation | send 2 scripted prompts |
| `customer-checkout.png` | `/chat` | approval card / "confirm payment" + Razorpay Checkout modal | drive to checkout |
| `console-overview.png` | `/console` | KPI hero row + "View analytics →" | — |
| `console-analytics.png` | `/console/analytics` | KPI row + 6 charts + 30/45/90d chips | full-page |
| `console-activity.png` | `/console/activity` | grouped session list + workflow chips | — |
| `console-activity-trace.png` | `/console/activity` | node/tool trace drawer, policy decisions | click first session |
| `console-knowledge.png` | `/console/knowledge` | doc table + "Add a document" + scored retrieval chunks | run a retrieval preview |
| `console-approvals.png` | `/console/approvals` | pending approval w/ amount + approve/decline | — |
| `console-ai-buyers.png` | `/console/ai-buyers` | scoped keys / external buyer sessions | — |
| `console-campaigns.png` | `/console/campaigns` | campaign list / cross-sell opportunity | — |
| `console-orders.png` | `/console/orders` | orders table w/ status badges | — |
| `login.png` | `/login` | the login screen (polish shot) | logged out |

---

## 5. AI image prompts (only where a photo/texture beats a diagram)

**cover-hero.png** (Frame 1 background):
> Minimal abstract technical illustration, isometric, a network of clean geometric
> nodes connected by thin precise lines representing an AI-driven commerce system,
> palette limited to deep ink black, soft slate blue and one warm amber accent,
> generous negative space, faint underlying grid, premium enterprise-SaaS brand
> art in the spirit of Stripe and Linear, soft studio lighting, 16:9.
> Negative: no text, no logos, no words, no rainbow gradients, no glassmorphism
> blobs, no clutter, no photorealistic faces.

**section-texture.png** (optional, behind text-only frames 3/4/15/18 at ~6% opacity):
> Very subtle light-grey topographic contour lines on an off-white background,
> faint, evenly spaced, corporate report texture, 16:9, no text.

**close-bg.png** (Frame 19, optional):
> Same node-network style as the cover but sparser and calmer, fading toward the
> right into clean off-white space for text, ink + slate-blue only, 16:9, no text.

Architecture / component flows are **native Miro** — do not AI-generate them.

---

## 6. Build order (once decisions are in)

1. `board_create` → "CommerceOS — Architecture & Pitch".
2. Generate the 1–3 AI images; upload via `image_get_upload_url` → get hosted URLs.
3. Run `presentation/capture.mjs` → screenshots on disk → upload each →
   hosted URLs.
4. `canvas_create_from_svg` frame by frame in this order: 1, 2, 3, 6, 7 (core),
   then 4, 5, 8–14, 15, 16, then 17, 18, 19.
5. After each call, read `result_svg`, fix any flagged dimension/overlap changes
   with `canvas_update_from_svg` before moving on.
6. Final pass: consistent footer numbers, deep-links on Frame 5 / any index,
   run through Presentation Mode order.

---

## 7. Decisions (LOCKED 2026-08-29)

**D1 — Screenshot source: LIVE DEPLOYMENT** (Vercel + Render). Render free tier
cold-starts (~1 min on first hit) — warm it before the capture run. `capture.mjs`
points `E2E_BASE_URL` at the live frontend URL; sign in with the real Supabase
user (`donthalamohanrao0@gmail.com`). Live chat + Razorpay Checkout shots are in
scope.

**D2 — Imagery: AI HERO + SUBTLE TEXTURES.** Generate `cover-hero.png` (Frame 1
background) and `section-texture.png` (~6% opacity behind Frames 3, 4, 15, 18).
Optionally `close-bg.png` for Frame 19. All other frames 100% native Miro.
Prompts in §5.
