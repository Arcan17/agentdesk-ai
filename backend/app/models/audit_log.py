"""AuditLog — append-only record of significant security/business events."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDMixin

# Portable JSON: JSONB on Postgres, JSON elsewhere (e.g. SQLite in tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class AuditEvent(enum.StrEnum):
    ticket_created = "ticket_created"
    agent_run_started = "agent_run_started"
    retrieval_completed = "retrieval_completed"
    draft_generated = "draft_generated"
    response_approved = "response_approved"
    response_rejected = "response_rejected"
    ticket_escalated = "ticket_escalated"
    webhook_sent = "webhook_sent"
    login_success = "login_success"
    login_failed = "login_failed"


class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event: Mapped[AuditEvent] = mapped_column(
        SAEnum(AuditEvent, name="audit_event"), nullable=False, index=True
    )
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
