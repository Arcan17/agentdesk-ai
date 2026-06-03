"""Metrics schema."""
from __future__ import annotations

from pydantic import BaseModel


class Metrics(BaseModel):
    total_tickets: int
    tickets_by_status: dict[str, int]
    avg_agent_latency_ms: float
    avg_estimated_cost_usd: float
    approval_rate: float
    escalation_rate: float
    retrieval_hit_rate: float
    failed_jobs: int
