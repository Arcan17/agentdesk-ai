"""Ticket model with status/priority enums and a validated state machine."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class TicketStatus(enum.StrEnum):
    new = "new"
    triaged = "triaged"
    draft_ready = "draft_ready"
    waiting_approval = "waiting_approval"
    approved = "approved"
    rejected = "rejected"
    escalated = "escalated"
    closed = "closed"


class TicketPriority(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


# Allowed status transitions. The agent workflow may move an open ticket directly to
# waiting_approval or escalated; humans approve/reject; anything open can be closed.
ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.new: {
        TicketStatus.triaged,
        TicketStatus.waiting_approval,
        TicketStatus.escalated,
        TicketStatus.closed,
    },
    TicketStatus.triaged: {
        TicketStatus.draft_ready,
        TicketStatus.waiting_approval,
        TicketStatus.escalated,
        TicketStatus.closed,
    },
    TicketStatus.draft_ready: {
        TicketStatus.waiting_approval,
        TicketStatus.escalated,
        TicketStatus.closed,
    },
    TicketStatus.waiting_approval: {
        TicketStatus.approved,
        TicketStatus.rejected,
        TicketStatus.escalated,
        TicketStatus.closed,
    },
    TicketStatus.approved: {TicketStatus.closed},
    TicketStatus.rejected: {
        TicketStatus.draft_ready,
        TicketStatus.waiting_approval,
        TicketStatus.escalated,
        TicketStatus.closed,
    },
    TicketStatus.escalated: {
        TicketStatus.waiting_approval,
        TicketStatus.closed,
    },
    TicketStatus.closed: set(),
}


def can_transition(current: TicketStatus, target: TicketStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


class Ticket(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tickets"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority"),
        nullable=False,
        default=TicketPriority.medium,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status"),
        nullable=False,
        default=TicketStatus.new,
        index=True,
    )
    suggested_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suggested_priority: Mapped[TicketPriority | None] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority", create_type=False), nullable=True
    )
    draft_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
