"""Document ingestion: validate, chunk, embed, and persist."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentSource
from app.models.document_chunk import DocumentChunk
from app.providers.factory import get_embedding_provider

_WORDS = re.compile(r"\S+")

CHUNK_SIZE_WORDS = 120
CHUNK_OVERLAP_WORDS = 20


def chunk_text(
    text: str, size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS
) -> list[str]:
    words = _WORDS.findall(text)
    if not words:
        return []
    step = max(1, size - overlap)
    chunks: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + size]
        if window:
            chunks.append(" ".join(window))
        if start + size >= len(words):
            break
    return chunks


async def create_document(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    title: str,
    content: str,
    source_type: DocumentSource,
) -> tuple[Document, int]:
    document = Document(
        organization_id=organization_id,
        title=title,
        content=content,
        source_type=source_type,
        created_by=actor_user_id,
    )
    db.add(document)
    await db.flush()

    chunks = chunk_text(content)
    embeddings = await get_embedding_provider().embed(chunks) if chunks else []
    for idx, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=True)):
        db.add(
            DocumentChunk(
                organization_id=organization_id,
                document_id=document.id,
                chunk_index=idx,
                content=chunk,
                embedding=vector,
            )
        )
    await db.commit()
    await db.refresh(document)
    return document, len(chunks)


async def list_documents(
    db: AsyncSession, *, organization_id: uuid.UUID
) -> list[tuple[Document, int]]:
    stmt = (
        select(Document, func.count(DocumentChunk.id))
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .where(Document.organization_id == organization_id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    rows = await db.execute(stmt)
    return [(doc, count) for doc, count in rows.all()]
