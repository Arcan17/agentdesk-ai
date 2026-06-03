"""TicketEvent — chronological history of state changes and actions on a ticket."""
from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.ticket import TicketStatus


class TicketEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ticket_events"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[TicketStatus | None] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", create_type=False), nullable=True
    )
    to_status: Mapped[TicketStatus | None] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", create_type=False), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
