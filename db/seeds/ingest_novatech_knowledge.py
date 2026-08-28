"""Ingest the NovaTech merchant knowledge base into Pinecone + Postgres.

    uv run --project backend python -m db.seeds.ingest_novatech_knowledge [--purge] [--purge-only]

--purge       wipe every namespace in the index before ingesting (clears any
              vectors left over from prior/other use of the shared index)
--purge-only  wipe and stop (no ingestion)

Source of truth for the doc set is demo-data/knowledge/knowledge_index.json.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(_BACKEND))


def _load_backend_env() -> None:
    """Populate os.environ from backend/.env so the OpenAI/Pinecone keys resolve
    no matter which directory this script is launched from (pydantic-settings
    only reads a .env in the CWD)."""
    env_path = _BACKEND / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_backend_env()

from sqlalchemy import select  # noqa: E402

from app.core.db import async_session_factory  # noqa: E402
from app.domains.merchants.models import Merchant  # noqa: E402
from app.integrations.openai.embeddings import get_embedding_client  # noqa: E402
from app.integrations.pinecone.client import get_vector_index  # noqa: E402
from app.knowledge.ingestion.pipeline import KnowledgeIngestionService  # noqa: E402

DATA_ROOT = Path(__file__).resolve().parents[2] / "demo-data"
KNOWLEDGE_INDEX = DATA_ROOT / "knowledge" / "knowledge_index.json"


def _title_from(raw: str, fallback: str) -> str:
    for line in raw.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("_", " ").title()


async def main() -> None:
    purge = "--purge" in sys.argv or "--purge-only" in sys.argv
    purge_only = "--purge-only" in sys.argv

    index = get_vector_index()
    index.ensure_ready()

    if purge:
        namespaces = index.list_namespaces()
        for ns in namespaces:
            index.delete_namespace(namespace=ns)
        print(f"purged {len(namespaces)} namespace(s): {namespaces or '(none)'}")
    if purge_only:
        return

    entries = json.loads(KNOWLEDGE_INDEX.read_text(encoding="utf-8"))
    embed = get_embedding_client()
    print(f"embedding client: {embed.model}  (dim {embed.dimension})")

    async with async_session_factory() as session, session.begin():
        merchant_cache: dict[str, Merchant] = {}
        for entry in entries:
            code = entry["merchant_id"]
            if code not in merchant_cache:
                merchant = await session.scalar(
                    select(Merchant).where(Merchant.merchant_code == code)
                )
                if merchant is None:
                    raise RuntimeError(f"merchant {code} not seeded — run seed_novatech_demo first")
                merchant_cache[code] = merchant
            merchant = merchant_cache[code]

            raw = (DATA_ROOT / entry["path"]).read_text(encoding="utf-8")
            svc = KnowledgeIngestionService(session, embedding_client=embed, vector_index=index)
            result = await svc.ingest_markdown(
                merchant_id=merchant.id,
                merchant_code=code,
                namespace=merchant.pinecone_namespace,
                document_key=entry["document_id"],
                title=_title_from(raw, entry["document_id"]),
                document_type=entry["document_type"],
                source_path=entry["path"],
                raw_text=raw,
            )
            print(
                f"  {result.document_key:32} v{result.version_number}  "
                f"{result.chunk_count:2} chunks -> {result.namespace}"
            )

    print("knowledge ingestion complete.")


if __name__ == "__main__":
    asyncio.run(main())
