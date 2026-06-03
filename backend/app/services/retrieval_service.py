"""Semantic retrieval over an organization's knowledge base.

Cosine similarity, scoped to the caller's organization, filtered by a similarity
threshold. Uses pgvector's ``<=>`` operator on PostgreSQL; falls back to in-Python
cosine on other dialects (e.g. SQLite in tests) for deterministic, offline behavior.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from app.providers.factory import get_embedding_provider


@dataclass(slots=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float  # cosine similarity in [-1, 1]


def _dialect_name(db: AsyncSession) -> str:
    try:
        return db.get_bind().dialect.name
    except Exception:  # pragma: no cover - defensive
        return "unknown"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def search(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    query: str,
    threshold: float | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    threshold = settings.similarity_threshold if threshold is None else threshold
    top_k = settings.retrieval_top_k if top_k is None else top_k

    query_vec = (await get_embedding_provider().embed([query]))[0]

    if _dialect_name(db) == "postgresql":
        # pgvector cosine distance operator; similarity = 1 - distance.
        distance = DocumentChunk.embedding.op("<=>")(query_vec)
        stmt = (
            select(DocumentChunk, distance.label("distance"))
            .where(DocumentChunk.organization_id == organization_id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = await db.execute(stmt)
        hits = [RetrievedChunk(chunk=c, score=1.0 - float(d)) for c, d in rows.all()]
    else:
        stmt = select(DocumentChunk).where(
            DocumentChunk.organization_id == organization_id
        )
        chunks = list(await db.scalars(stmt))
        scored = [RetrievedChunk(chunk=c, score=_cosine(query_vec, c.embedding)) for c in chunks]
        scored.sort(key=lambda r: r.score, reverse=True)
        hits = scored[:top_k]

    return [h for h in hits if h.score >= threshold]
