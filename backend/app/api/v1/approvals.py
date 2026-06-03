"""Human-in-the-loop endpoints: approve, reject, edit the draft."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.ticket import TicketOut
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["approvals"])


class ApproveRequest(BaseModel):
    edited_response: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class EditDraftRequest(BaseModel):
    content: str = Field(min_length=1)


async def _load(db: AsyncSession, org_id: uuid.UUID, ticket_id: uuid.UUID):
    try:
        return await ticket_service.get_ticket(
            db, organization_id=org_id, ticket_id=ticket_id
        )
    except ticket_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        ) from exc


@router.post("/{ticket_id}/approve", response_model=TicketOut)
async def approve(
    ticket_id: uuid.UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator)),
) -> TicketOut:
    ticket = await _load(db, current.organization_id, ticket_id)
    try:
        ticket = await ticket_service.approve(
            db, ticket=ticket, actor_user_id=current.id, edited_response=body.edited_response
        )
    except ticket_service.EmptyResponseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ticket_service.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TicketOut.model_validate(ticket)


@router.post("/{ticket_id}/reject", response_model=TicketOut)
async def reject(
    ticket_id: uuid.UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator)),
) -> TicketOut:
    ticket = await _load(db, current.organization_id, ticket_id)
    try:
        ticket = await ticket_service.reject(
            db, ticket=ticket, actor_user_id=current.id, reason=body.reason
        )
    except ticket_service.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TicketOut.model_validate(ticket)


@router.patch("/{ticket_id}/edit-draft", response_model=TicketOut)
async def edit_draft(
    ticket_id: uuid.UUID,
    body: EditDraftRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator)),
) -> TicketOut:
    ticket = await _load(db, current.organization_id, ticket_id)
    try:
        ticket = await ticket_service.edit_draft(
            db, ticket=ticket, actor_user_id=current.id, content=body.content
        )
    except ticket_service.EmptyResponseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TicketOut.model_validate(ticket)
