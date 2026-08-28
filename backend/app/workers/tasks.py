"""Celery tasks. Each opens its own DB session (workers have no request scope) and
bridges the async domain services with ``asyncio.run``.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.db import async_session_factory
from app.domains.merchants.models import Merchant
from app.workers.celery_app import celery_app

_DATA_ROOT = Path(__file__).resolve().parents[3] / "demo-data"


async def _ingest(
    merchant_code: str, document_key: str, path: str, title: str, doc_type: str
) -> dict[str, Any]:
    from app.knowledge.ingestion.pipeline import KnowledgeIngestionService

    async with async_session_factory() as session, session.begin():
        merchant = await session.scalar(
            select(Merchant).where(Merchant.merchant_code == merchant_code)
        )
        if merchant is None:
            raise RuntimeError(f"unknown merchant {merchant_code}")
        raw = (_DATA_ROOT / path).read_text(encoding="utf-8")
        result = await KnowledgeIngestionService(session).ingest_markdown(
            merchant_id=merchant.id,
            merchant_code=merchant_code,
            namespace=merchant.pinecone_namespace,
            document_key=document_key,
            title=title,
            document_type=doc_type,
            source_path=path,
            raw_text=raw,
        )
        return {
            "document_id": str(result.document_id),
            "version": result.version_number,
            "chunk_count": result.chunk_count,
        }


@celery_app.task(name="knowledge.ingest_document", bind=True, max_retries=3)
def ingest_knowledge_document(
    self: Any,
    *,
    merchant_code: str,
    document_key: str,
    path: str,
    title: str,
    document_type: str,
) -> dict[str, Any]:
    try:
        return asyncio.run(_ingest(merchant_code, document_key, path, title, document_type))
    except Exception as exc:  # transient (network/embedding) -> retry with backoff
        raise self.retry(exc=exc, countdown=min(2**self.request.retries * 5, 60)) from exc


async def _snapshot(merchant_id: uuid.UUID) -> dict[str, Any]:
    from app.analytics.service import AnalyticsService

    async with async_session_factory() as session:
        snap = await AnalyticsService(session).merchant_snapshot(merchant_id)
        return {
            "merchant_id": str(merchant_id),
            "revenue_paise": snap.revenue_paise,
            "aov_paise": snap.aov_paise,
            "cross_sell_pairs": len(snap.cross_sell_pairs),
        }


@celery_app.task(name="growth.refresh_snapshot")
def refresh_growth_snapshot(*, merchant_id: str) -> dict[str, Any]:
    """Precompute a merchant's analytics snapshot (e.g. nightly) so the growth
    agent's first turn is fast."""
    return asyncio.run(_snapshot(uuid.UUID(merchant_id)))
