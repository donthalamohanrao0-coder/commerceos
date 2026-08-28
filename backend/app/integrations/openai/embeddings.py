"""Capability seam for text embeddings (harness-engineering-patterns.md #3).

One interface; the real client calls OpenAI ``text-embedding-3-small``, the fake
returns deterministic unit vectors so ingestion/retrieval can be exercised (and
tested) with no API key and no network.
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings


class EmbeddingClient(Protocol):
    model: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddingClient:
    """Deterministic hash-seeded pseudo-embeddings on the unit sphere.

    Same text -> same vector, so upserts are stable and similarity ordering is
    reproducible; unrelated texts are near-orthogonal in expectation.
    """

    model = "fake-embedding"

    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            seed = hashlib.sha256(text.encode("utf-8")).digest()
            raw = [
                (seed[i % len(seed)] ^ (i * 131 % 256)) / 255.0 - 0.5 for i in range(self.dimension)
            ]
            norm = math.sqrt(sum(v * v for v in raw)) or 1.0
            out.append([v / norm for v in raw])
        return out


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str, model: str, dimension: int, batch_size: int = 128) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.dimension = dimension
        self._batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            resp = self._client.embeddings.create(model=self.model, input=batch)
            vectors.extend(item.embedding for item in resp.data)
        return vectors


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIEmbeddingClient(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.rag_embedding_dimension,
        )
    return FakeEmbeddingClient(dimension=settings.rag_embedding_dimension)
