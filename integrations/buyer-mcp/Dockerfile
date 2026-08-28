# CommerceOS buyer MCP server — HTTP (streamable-http) transport for remote hosting.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY server.py ./

ENV MCP_TRANSPORT=http PORT=8080
EXPOSE 8080

CMD ["uv", "run", "--no-sync", "server.py"]
