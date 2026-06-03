"""Ticket schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: TicketPriority = TicketPriority.medium


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    suggested_type: str | None
    suggested_priority: TicketPriority | None
    draft_response: str | None
    final_response: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TicketEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    event_type: str
    from_status: TicketStatus | None
    to_status: TicketStatus | None
    actor_user_id: uuid.UUID | None
    message: str | None
    created_at: datetime
