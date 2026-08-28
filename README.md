# CommerceOS

An AI-native commerce platform for the Razorpay buildathon. It covers **both**
problem-statement directions:

- **Conversational, agentic checkout** — a customer shops in plain language; a
  LangGraph agent proposes actions (search, cart, quote, order, pay) and the
  merchant backend prices, checks policy, and gates every payment behind explicit
  human confirmation.
- **Sellable to an AI buyer end to end** — an external AI agent transacts through
  a scoped-key REST API (`/api/v1/agent-commerce`): catalog → authoritative quote
  → idempotent order → consent-gated payment.

> **Core principle:** the AI may *propose* a money action. Deterministic backend
> services, policies, and state machines decide whether it's allowed and execute
> it — and every step is in an append-only audit trail.

---

## What's in the box

| | |
|---|---|
| **Customer chat** (`/chat`) | streaming agent, product carousels, cart drawer, upsell/cross-sell with campaign-unlock hints, real Razorpay Checkout |
| **Merchant console** (`/console`) | authoritative metrics, analytics charts, agent-activity trace (grouped by session + time), approvals, audit trail, knowledge-base retrieval preview, product CRUD, AI-buyer key management |
| **Agent Commerce API** | external AI buyers, scoped `ack_live_…` keys (SHA-256 at rest), per-key rate limits, idempotency, consent gate |
| **RAG** | structure-aware chunking, per-merchant Pinecone namespaces, retrieved text treated as data not instructions |
| **MCP buyer** (`integrations/buyer-mcp/`) | drive the Agent Commerce API from Claude Desktop / Claude Code |

## Stack

- **Backend** — FastAPI (async), SQLAlchemy 2.0 + asyncpg, Alembic, Postgres
  (Supabase), LangGraph, OpenAI, Pinecone, Razorpay test mode, Celery + Redis.
  `uv`, ruff, mypy strict, pytest.
- **Frontend** — Next.js 15 (App Router), React 19, TypeScript strict, Tailwind
  v4, TanStack Query, `@supabase/supabase-js`, Recharts. Vitest + Playwright.

## Repository layout

```
apps/web/          Next.js frontend (customer chat + merchant console)
backend/           FastAPI service + LangGraph agents + Celery workers
db/                Alembic migrations + seed / demo-history scripts
demo-data/         NovaTech merchant fixture (catalog, customers, knowledge, campaigns)
integrations/      buyer-mcp — MCP server for the Agent Commerce API
docs/              architecture, engineering standards, security, AI, design spec
infra/             docker-compose (local Postgres + Redis)
scripts/           dev.sh, agent_buyer_demo.sh
Dockerfile         backend API + Celery worker (one image)
render.yaml        Render blueprint       apps/web/vercel.json  Vercel config
```

Full map: [`docs/engineering/repository-structure.md`](docs/engineering/repository-structure.md).

## Quickstart (local)

```bash
cp backend/.env.example backend/.env            # fill in the credentials
cp apps/web/.env.local.example apps/web/.env.local
./scripts/dev.sh                                # backend :8000 + frontend :3000
```

Open http://localhost:3000 → sign up (any email; first sign-in auto-links to the
demo merchant **NovaTech**).

Optional — a populated demo:

```bash
uv run --project backend python db/seeds/seed_novatech_demo.py
uv run --project backend python db/seeds/generate_demo_history.py
uv run --project backend python -m db.seeds.ingest_novatech_knowledge
```

- **Demo walkthrough:** [DEMO.md](DEMO.md)
- **Deploy (Vercel + Render):** [DEPLOY.md](DEPLOY.md)

## Documentation

| | |
|---|---|
| Architecture + ADRs | [`docs/architecture/`](docs/architecture/) |
| Engineering standards | [`docs/engineering/`](docs/engineering/) |
| Security & guardrails | [`docs/security/`](docs/security/) |
| AI / agent design | [`docs/ai/`](docs/ai/) |
| Frontend design spec | [`docs/frontend-design-spec/`](docs/frontend-design-spec/) |
| Original plan / problem statement | [`docs/plan.md`](docs/plan.md) · [`docs/problemstatement.md`](docs/problemstatement.md) |

## Non-negotiable principles

1. Never trust the LLM with authoritative money values.
2. Never let the frontend decide payment state.
3. Every sensitive action is authenticated and authorized.
4. Every tenant-scoped resource is isolated.
5. Every financial mutation is idempotent.
6. Every payment webhook is verified and deduplicated.
7. Every agent has bounded execution.
8. Every sensitive tool has a strict schema and allowlist.
9. Retrieved documents are untrusted data, never instructions.
10. Secrets and unnecessary sensitive data never enter prompts, logs, or traces.
11. Routes remain thin; domain services own business logic.
12. Production changes pass automated checks before deployment.
