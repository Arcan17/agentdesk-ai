"""AgentRun — a record of one execution of the AI workflow on a ticket."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.audit_log import JSONType


class AgentRunStatus(enum.StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentRunOutcome(enum.StrEnum):
    waiting_approval = "waiting_approval"
    escalated = "escalated"


class AgentRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(AgentRunStatus, name="agent_run_status"),
        nullable=False,
        default=AgentRunStatus.running,
    )
    classification: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    retrieved_chunk_ids: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    retrieval_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[AgentRunOutcome | None] = mapped_column(
        SAEnum(AgentRunOutcome, name="agent_run_outcome"), nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
