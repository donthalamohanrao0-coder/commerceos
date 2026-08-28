# CommerceOS — Deploy

Three moving parts:

| Part | Host | Notes |
|------|------|-------|
| Postgres | **Supabase** | already live (`db.rnusvxrltrkrgkciogxp.supabase.co`) |
| FastAPI API `+` Celery worker | **Render** | `Dockerfile` + `render.yaml` at the repo root |
| Next.js frontend | **Vercel** | `apps/web`, `apps/web/vercel.json` |

Everything runs in test/sandbox mode (Razorpay test keys). No production PII.

---

## 0. Prerequisites

- The repo pushed to GitHub.
- Accounts: [Render](https://render.com), [Vercel](https://vercel.com).
- The secret values currently in `backend/.env` (DB password, OpenAI, Razorpay
  test keys, Pinecone, Supabase keys, Langfuse). **Never commit them** — you paste
  them into the Render/Vercel dashboards.

---

## 1. Backend + worker → Render

1. **New + → Blueprint**, pick this repo. Render reads `render.yaml` and proposes:
   `commerceos-api` (web), `commerceos-worker` (worker), `commerceos-redis`.
2. **Apply.** The first build will fail health checks until the env vars are set —
   that's expected.
3. Open **commerceos-api → Environment** and fill every `sync: false` var:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `postgresql+asyncpg://postgres:<DB_PASSWORD>@db.rnusvxrltrkrgkciogxp.supabase.co:5432/postgres` |
   | `CORS_ALLOW_ORIGINS` | `["https://<your-vercel-domain>"]` (JSON list — update after step 2) |
   | `SUPABASE_URL` | `https://rnusvxrltrkrgkciogxp.supabase.co` |
   | `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | from Supabase → Project Settings → API |
   | `OPENAI_API_KEY` | — |
   | `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` | Razorpay **test** keys |
   | `PINECONE_API_KEY` / `PINECONE_INDEX_NAME` | — |
   | `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | optional (observability) |

   Copy `DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`
   onto **commerceos-worker** too.

   > Supabase serverless tip: if direct `:5432` connections are throttled, use the
   > **session pooler** host instead —
   > `postgresql+asyncpg://postgres.rnusvxrltrkrgkciogxp:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres`.

4. **Manual Deploy → Clear build cache & deploy.** `preDeployCommand` runs
   `alembic upgrade head` against Supabase (schema is already migrated, so this is
   a no-op the first time). Health check hits `/docs`.

   *Free plan:* Render free web services have no `preDeployCommand`. Delete that
   line from `render.yaml` and set
   `dockerCommand: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"`.

5. Note the API URL: `https://commerceos-api.onrender.com`.

### One-time data seed (optional, for a populated demo)

From your laptop, pointed at the same Supabase DB:

```bash
uv run --project backend python db/seeds/generate_demo_history.py     # 95 orders / 60 days
uv run --project backend python -m db.seeds.ingest_novatech_knowledge  # knowledge → Pinecone
```

The Celery worker is **not** required for the app to run — rate-limiting falls
back to an in-process limiter and ingestion can be run from the CLI as above.
Enable the worker when you want async knowledge ingestion from the console.

---

## 2. Frontend → Vercel

1. **Add New → Project**, import the repo.
2. **Root Directory: `apps/web`** (Edit → set it). Framework auto-detects as Next.js.
3. **Environment Variables** (Production + Preview):

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://commerceos-api.onrender.com/api/v1` (no trailing slash) |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://rnusvxrltrkrgkciogxp.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the anon key (public-safe) |

4. **Deploy.** Grab the domain, e.g. `https://commerceos.vercel.app`.
5. Back in Render, set `CORS_ALLOW_ORIGINS` to `["https://commerceos.vercel.app"]`
   (add the `*.vercel.app` preview domain too if you test previews) and redeploy
   the API.

---

## 3. Wire the last two things

- **Supabase Auth → URL Configuration**: add `https://commerceos.vercel.app` to
  **Site URL** and **Redirect URLs** so email sign-in links resolve.
- **Razorpay Dashboard → Webhooks** (test mode): add
  `https://commerceos-api.onrender.com/api/v1/webhooks/razorpay` with the same
  `RAZORPAY_WEBHOOK_SECRET`. Not required for the Checkout-popup demo flow (the
  browser posts the signed result to `/payments/{id}/verify` directly), but it
  keeps captures reconciled if the tab closes.

---

## 4. Smoke test

```bash
curl https://commerceos-api.onrender.com/docs           # 200
open  https://commerceos.vercel.app/login               # sign up → /chat
```

Then run the demo in [DEMO.md](DEMO.md) against the live URLs.

---

## Local "prod-like" run

`infra/docker-compose.yml` brings up Postgres + Redis only. To run the
whole stack in containers, build the API image directly:

```bash
docker build -t commerceos-api .
docker run --rm -p 8000:8000 --env-file backend/.env commerceos-api
docker run --rm --env-file backend/.env commerceos-api \
  celery -A app.workers.celery_app.celery_app worker --loglevel=info
```
