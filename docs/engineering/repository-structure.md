# CommerceOS — Repository Structure

```text
commerceos/
├── apps/
│   └── web/                     # Next.js 15 (App Router) — customer chat + merchant console
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI routers + request-scoped deps
│   │   ├── core/                # config, db, logging, rate-limit, otel
│   │   ├── domains/             # catalog, cart, orders, payments, campaigns, customers, merchants
│   │   ├── agents/              # LangGraph multi-agent (shopping / growth / support + supervisor)
│   │   ├── agent_commerce/      # external AI-buyer API (scoped keys, ADR-006)
│   │   ├── knowledge/           # RAG: chunking, ingestion, retrieval
│   │   ├── identity/            # Supabase-auth → user → merchant resolution
│   │   ├── policies/ approvals/ audit/ analytics/
│   │   ├── workers/             # Celery tasks (knowledge ingestion, analytics refresh)
│   │   └── integrations/        # razorpay, openai, pinecone, langfuse, supabase (seam pattern)
│   └── tests/                   # unit/ integration/ agent_evals/
├── apps/web/e2e/                # Playwright smoke tests
├── db/
│   ├── migrations/              # Alembic (script_location = ../db/migrations)
│   └── seeds/                   # demo seed + history generator + knowledge ingestion
├── demo-data/                   # NovaTech merchant fixture: catalog, customers, knowledge md, campaigns
├── integrations/
│   └── buyer-mcp/               # MCP server: drive the Agent Commerce API from Claude
├── docs/
│   ├── ai/ architecture/ engineering/ security/ frontend-design-spec/
│   ├── plan.md problemstatement.md
├── infra/
│   └── docker-compose.yml       # local Postgres + Redis
├── scripts/                     # dev.sh, agent_buyer_demo.sh
├── .github/workflows/           # CI (offline lane)
├── Dockerfile                   # backend API + Celery worker (one image)
├── render.yaml                  # Render blueprint (web + worker + redis)
├── apps/web/vercel.json         # Vercel (frontend)
├── DEMO.md  DEPLOY.md  README.md
```

## Backend domain structure

```text
domains/<name>/
├── models.py        # SQLAlchemy
├── schemas.py       # pydantic (where the domain has its own DTOs)
├── service.py       # deterministic business logic — owns pricing/policy/state
├── exceptions.py
└── (state_machine.py, inventory_service.py, ... as needed)
```

## Integration seam

Each external dependency is a `Protocol` + a real client + a fake client + a
factory (`get_razorpay_client`, `get_chat_client`, `get_token_verifier`, …). Code
depends on the Protocol; tests and local dev use the fake until a credential is set.

```text
integrations/<name>/
├── base.py          # Protocol + shared types
├── real_client.py
├── fake_client.py
└── factory.py
```

## Rule

Dependencies flow inward toward domain logic. Domain logic never imports HTTP
route modules. The agent proposes; deterministic services decide and persist;
every money action is gated and audited.
