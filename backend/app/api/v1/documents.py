"""Knowledge-base document endpoints: create, list, semantic search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.document import DocumentCreate, DocumentOut, SearchHit, SearchRequest
from app.services import document_service, retrieval_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator)),
) -> DocumentOut:
    document, chunk_count = await document_service.create_document(
        db,
        organization_id=current.organization_id,
        actor_user_id=current.id,
        title=body.title,
        content=body.content,
        source_type=body.source_type,
    )
    out = DocumentOut.model_validate(document)
    out.chunk_count = chunk_count
    return out


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator, Role.viewer)),
) -> list[DocumentOut]:
    results = await document_service.list_documents(
        db, organization_id=current.organization_id
    )
    out: list[DocumentOut] = []
    for doc, count in results:
        item = DocumentOut.model_validate(doc)
        item.chunk_count = count
        out.append(item)
    return out


@router.post("/search", response_model=list[SearchHit])
async def search_documents(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator, Role.viewer)),
) -> list[SearchHit]:
    hits = await retrieval_service.search(
        db,
        organization_id=current.organization_id,
        query=body.query,
        threshold=body.threshold,
        top_k=body.top_k,
    )
    return [
        SearchHit(
            chunk_id=h.chunk.id,
            document_id=h.chunk.document_id,
            content=h.chunk.content,
            score=round(h.score, 6),
        )
        for h in hits
    ]
