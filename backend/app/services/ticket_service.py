"""Ticket business logic: creation, tenant-scoped reads, validated transitions, history."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent
from app.models.ticket import Ticket, TicketPriority, TicketStatus, can_transition
from app.models.ticket_event import TicketEvent
from app.services import audit_service


class NotFoundError(Exception):
    """Raised when a ticket does not exist within the caller's organization."""


class InvalidTransitionError(Exception):
    """Raised when a status change violates the ticket state machine."""


async def create_ticket(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    title: str,
    description: str,
    priority: TicketPriority,
) -> Ticket:
    ticket = Ticket(
        organization_id=organization_id,
        title=title,
        description=description,
        priority=priority,
        status=TicketStatus.new,
        created_by=actor_user_id,
    )
    db.add(ticket)
    await db.flush()

    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            organization_id=organization_id,
            event_type="created",
            to_status=TicketStatus.new,
            actor_user_id=actor_user_id,
        )
    )
    await audit_service.record(
        db,
        event=AuditEvent.ticket_created,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="ticket",
        target_id=ticket.id,
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def list_tickets(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    status: TicketStatus | None = None,
) -> list[Ticket]:
    stmt = select(Ticket).where(Ticket.organization_id == organization_id)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    stmt = stmt.order_by(Ticket.created_at.desc())
    return list(await db.scalars(stmt))


async def get_ticket(
    db: AsyncSession, *, organization_id: uuid.UUID, ticket_id: uuid.UUID
) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None or ticket.organization_id != organization_id:
        raise NotFoundError("Ticket not found")
    return ticket


async def list_events(
    db: AsyncSession, *, organization_id: uuid.UUID, ticket_id: uuid.UUID
) -> list[TicketEvent]:
    # Ensure the ticket belongs to the org (raises NotFound otherwise).
    await get_ticket(db, organization_id=organization_id, ticket_id=ticket_id)
    stmt = (
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at.asc())
    )
    return list(await db.scalars(stmt))


async def transition(
    db: AsyncSession,
    *,
    ticket: Ticket,
    to_status: TicketStatus,
    actor_user_id: uuid.UUID | None,
    event_type: str,
    message: str | None = None,
    flush: bool = True,
) -> Ticket:
    """Validate and apply a status change, appending a history event.

    Does not commit; the caller owns the transaction so several changes can be atomic.
    """
    if not can_transition(ticket.status, to_status):
        raise InvalidTransitionError(
            f"Cannot move ticket from {ticket.status} to {to_status}"
        )
    from_status = ticket.status
    ticket.status = to_status
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            organization_id=ticket.organization_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            message=message,
        )
    )
    if flush:
        await db.flush()
    return ticket
