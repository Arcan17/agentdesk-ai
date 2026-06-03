"""Agent run schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.agent_run import AgentRunOutcome, AgentRunStatus


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    status: AgentRunStatus
    outcome: AgentRunOutcome | None
    confidence: float | None
    retrieval_hit: bool
    draft: str | None
    latency_ms: int | None
    estimated_cost_usd: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    created_at: datetime
    finished_at: datetime | None
