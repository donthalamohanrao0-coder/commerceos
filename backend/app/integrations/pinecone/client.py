"""Capability seam for the vector store (harness-engineering-patterns.md #3).

Real client -> Pinecone serverless; fake client -> in-memory cosine index. Every
call is namespace-scoped: the namespace is the merchant's tenant boundary
(plan.md #5, ADR-003), never a cross-merchant global space.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class VectorRecord:
    id: str
    values: list[float]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ScoredChunk:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorIndex(Protocol):
    def ensure_ready(self) -> None: ...

    def list_namespaces(self) -> list[str]: ...

    def upsert(self, *, namespace: str, records: list[VectorRecord]) -> int: ...

    def delete_ids(self, *, namespace: str, ids: list[str]) -> None: ...

    def delete_namespace(self, *, namespace: str) -> None: ...

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _matches_filter(metadata: dict[str, Any], flt: dict[str, Any] | None) -> bool:
    if not flt:
        return True
    for key, cond in flt.items():
        value = metadata.get(key)
        if isinstance(cond, dict):
            if "$eq" in cond and value != cond["$eq"]:
                return False
            if "$ne" in cond and value == cond["$ne"]:
                return False
            if "$in" in cond and value not in cond["$in"]:
                return False
        elif value != cond:
            return False
    return True


@dataclass
class FakeVectorIndex:
    dimension: int = 1536
    _store: dict[str, dict[str, VectorRecord]] = field(default_factory=dict)

    def ensure_ready(self) -> None:  # noqa: D401 - no-op for the fake
        return

    def list_namespaces(self) -> list[str]:
        return [ns for ns, recs in self._store.items() if recs]

    def upsert(self, *, namespace: str, records: list[VectorRecord]) -> int:
        ns = self._store.setdefault(namespace, {})
        for rec in records:
            ns[rec.id] = rec
        return len(records)

    def delete_ids(self, *, namespace: str, ids: list[str]) -> None:
        ns = self._store.get(namespace, {})
        for vid in ids:
            ns.pop(vid, None)

    def delete_namespace(self, *, namespace: str) -> None:
        self._store.pop(namespace, None)

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        recs = self._store.get(namespace, {}).values()
        scored = [
            ScoredChunk(id=r.id, score=_cosine(vector, r.values), metadata=r.metadata)
            for r in recs
            if _matches_filter(r.metadata, metadata_filter)
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]


class PineconeVectorIndex:
    def __init__(
        self, *, api_key: str, index_name: str, cloud: str, region: str, dimension: int
    ) -> None:
        from pinecone import Pinecone

        self._pc = Pinecone(api_key=api_key)
        self._index_name = index_name
        self._cloud = cloud
        self._region = region
        self._dimension = dimension
        self._index: Any = None

    def _idx(self) -> Any:
        if self._index is None:
            self._index = self._pc.Index(self._index_name)
        return self._index

    def ensure_ready(self) -> None:
        existing = {i["name"] for i in self._pc.list_indexes()}
        if self._index_name not in existing:
            from pinecone import ServerlessSpec

            self._pc.create_index(
                name=self._index_name,
                dimension=self._dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=self._cloud, region=self._region),
            )

    def list_namespaces(self) -> list[str]:
        stats = self._idx().describe_index_stats()
        return list((stats.get("namespaces") or {}).keys())

    def upsert(self, *, namespace: str, records: list[VectorRecord]) -> int:
        payload = [{"id": r.id, "values": r.values, "metadata": r.metadata} for r in records]
        for start in range(0, len(payload), 100):
            self._idx().upsert(vectors=payload[start : start + 100], namespace=namespace)
        return len(payload)

    def delete_ids(self, *, namespace: str, ids: list[str]) -> None:
        if not ids:
            return
        for start in range(0, len(ids), 1000):
            self._idx().delete(ids=ids[start : start + 1000], namespace=namespace)

    def delete_namespace(self, *, namespace: str) -> None:
        try:
            self._idx().delete(delete_all=True, namespace=namespace)
        except Exception as exc:  # namespace already absent -> nothing to do
            if "not found" not in str(exc).lower():
                raise

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        res = self._idx().query(
            namespace=namespace,
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter or None,
        )
        return [
            ScoredChunk(id=m["id"], score=float(m["score"]), metadata=dict(m.get("metadata") or {}))
            for m in res.get("matches", [])
        ]


@lru_cache
def get_vector_index() -> VectorIndex:
    settings = get_settings()
    if settings.pinecone_api_key and settings.pinecone_index_name:
        return PineconeVectorIndex(
            api_key=settings.pinecone_api_key,
            index_name=settings.pinecone_index_name,
            cloud=settings.pinecone_cloud,
            region=settings.pinecone_region,
            dimension=settings.rag_embedding_dimension,
        )
    return FakeVectorIndex(dimension=settings.rag_embedding_dimension)
