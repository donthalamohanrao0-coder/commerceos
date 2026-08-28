# CommerceOS API + Celery worker.
# One image, two commands: the web service runs uvicorn, the worker runs celery.
# Build context is the repo root (the backend needs ../db for migrations and
# ../demo-data for the knowledge-ingestion task).

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# --- dependency layer (cached until the lockfile changes) ---------------------
COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project

# --- application source -----------------------------------------------------
COPY backend /app/backend
COPY db /app/db
COPY demo-data /app/demo-data
RUN cd backend && uv sync --frozen --no-dev

WORKDIR /app/backend

# Platforms (Render/Railway/Fly) inject $PORT; default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

# Web service. The worker service overrides this with:
#   celery -A app.workers.celery_app.celery_app worker --loglevel=info
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
