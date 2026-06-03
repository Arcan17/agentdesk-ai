"""Ticket endpoints: create, list, detail, history."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.ticket import TicketStatus
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.ticket import TicketCreate, TicketEventOut, TicketOut
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    body: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator)),
) -> TicketOut:
    ticket = await ticket_service.create_ticket(
        db,
        organization_id=current.organization_id,
        actor_user_id=current.id,
        title=body.title,
        description=body.description,
        priority=body.priority,
    )
    return TicketOut.model_validate(ticket)


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator, Role.viewer)),
) -> list[TicketOut]:
    tickets = await ticket_service.list_tickets(
        db, organization_id=current.organization_id, status=status_filter
    )
    return [TicketOut.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator, Role.viewer)),
) -> TicketOut:
    try:
        ticket = await ticket_service.get_ticket(
            db, organization_id=current.organization_id, ticket_id=ticket_id
        )
    except ticket_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        ) from exc
    return TicketOut.model_validate(ticket)


@router.get("/{ticket_id}/events", response_model=list[TicketEventOut])
async def list_ticket_events(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator, Role.viewer)),
) -> list[TicketEventOut]:
    try:
        events = await ticket_service.list_events(
            db, organization_id=current.organization_id, ticket_id=ticket_id
        )
    except ticket_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        ) from exc
    return [TicketEventOut.model_validate(e) for e in events]
