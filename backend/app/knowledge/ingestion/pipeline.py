"""Knowledge ingestion: markdown -> semantic chunks -> embeddings -> Pinecone,
with a versioned audit row in Postgres.

Postgres stays authoritative for *what* is indexed (documents / document_versions);
Pinecone only holds vectors. Re-ingesting a document creates a new version, points
`documents.current_version_id` at it, deactivates the prior version and deletes its
vectors, so a namespace never accumulates stale chunks.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_bump
from app.core.config import get_settings
from app.integrations.openai.embeddings import EmbeddingClient, get_embedding_client
from app.integrations.pinecone.client import VectorIndex, VectorRecord, get_vector_index
from app.knowledge.chunking import chunk_markdown
from app.knowledge.models import Document, DocumentVersion


@dataclass(frozen=True)
class IngestionResult:
    document_id: uuid.UUID
    document_key: str
    version_number: int
    chunk_count: int
    namespace: str


class KnowledgeIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embedding_client: EmbeddingClient | None = None,
        vector_index: VectorIndex | None = None,
    ) -> None:
        self._session = session
        self._embed = embedding_client or get_embedding_client()
        self._index = vector_index or get_vector_index()

    async def ingest_markdown(
        self,
        *,
        merchant_id: uuid.UUID,
        merchant_code: str,
        namespace: str,
        document_key: str,
        title: str,
        document_type: str,
        source_path: str,
        raw_text: str,
    ) -> IngestionResult:
        settings = get_settings()
        chunks = chunk_markdown(
            raw_text,
            target_tokens=settings.rag_chunk_target_tokens,
            max_tokens=settings.rag_chunk_max_tokens,
            overlap_tokens=settings.rag_chunk_overlap_tokens,
        )
        if not chunks:
            raise ValueError(f"{document_key}: chunker produced no chunks")

        # --- Postgres: upsert Document, compute next version -----------------
        document = await self._session.scalar(
            select(Document).where(
                Document.merchant_id == merchant_id,
                Document.storage_path == source_path,
            )
        )
        if document is None:
            document = Document(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                title=title,
                document_type=document_type,
                storage_path=source_path,
                status="processing",
            )
            self._session.add(document)
            await self._session.flush()

        prior_versions = list(
            await self._session.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document.id)
                .order_by(DocumentVersion.version_number.desc())
            )
        )
        next_version = (prior_versions[0].version_number + 1) if prior_versions else 1

        # --- embed + upsert vectors ----------------------------------------
        vectors = self._embed.embed([c.text for c in chunks])
        now = datetime.now(UTC)
        records = [
            VectorRecord(
                id=f"{merchant_code}:{document_key}:v{next_version}:{c.index}",
                values=vectors[c.index],
                metadata={
                    "merchant_id": str(merchant_id),
                    "merchant_code": merchant_code,
                    "document_uuid": str(document.id),
                    "document_id": document_key,
                    "document_type": document_type,
                    "version": next_version,
                    "chunk_index": c.index,
                    "heading": c.heading,
                    "source_path": source_path,
                    "content_hash": hashlib.sha256(c.text.encode()).hexdigest(),
                    "created_at": now.isoformat(),
                    "text": c.text,
                },
            )
            for c in chunks
        ]
        self._index.upsert(namespace=namespace, records=records)

        # --- Postgres: version bookkeeping --------------------------------
        await self._session.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .values(is_active=False)
        )
        version_row = DocumentVersion(
            id=uuid.uuid4(),
            document_id=document.id,
            version_number=next_version,
            chunk_count=len(chunks),
            pinecone_namespace=namespace,
            indexed_at=now,
            is_active=True,
        )
        self._session.add(version_row)
        await self._session.flush()

        document.current_version_id = version_row.id
        document.status = "indexed"
        document.title = title
        document.document_type = document_type

        # drop the previous version's vectors so the namespace has no stale chunks
        for old in prior_versions:
            if old.chunk_count:
                self._index.delete_ids(
                    namespace=namespace,
                    ids=[
                        f"{merchant_code}:{document_key}:v{old.version_number}:{i}"
                        for i in range(old.chunk_count)
                    ],
                )

        # invalidate this merchant's cached retrieval results
        await cache_bump(f"kb:{namespace}")

        return IngestionResult(
            document_id=document.id,
            document_key=document_key,
            version_number=next_version,
            chunk_count=len(chunks),
            namespace=namespace,
        )
