"""Aggregate operational and AI metrics, scoped to an organization."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun, AgentRunOutcome, AgentRunStatus
from app.models.ticket import Ticket
from app.models.webhook_delivery import DeliveryStatus, WebhookDelivery
from app.schemas.metrics import Metrics


async def compute(db: AsyncSession, *, organization_id: uuid.UUID) -> Metrics:
    total_tickets = (
        await db.scalar(
            select(func.count(Ticket.id)).where(Ticket.organization_id == organization_id)
        )
    ) or 0

    status_rows = await db.execute(
        select(Ticket.status, func.count(Ticket.id))
        .where(Ticket.organization_id == organization_id)
        .group_by(Ticket.status)
    )
    tickets_by_status = {status.value: count for status, count in status_rows.all()}

    completed = select(AgentRun).where(
        AgentRun.organization_id == organization_id,
        AgentRun.status == AgentRunStatus.completed,
    ).subquery()

    avg_latency = (
        await db.scalar(select(func.avg(completed.c.latency_ms)))
    ) or 0.0
    avg_cost = (
        await db.scalar(select(func.avg(completed.c.estimated_cost_usd)))
    ) or 0.0

    total_completed = (
        await db.scalar(select(func.count()).select_from(completed))
    ) or 0
    waiting = (
        await db.scalar(
            select(func.count())
            .select_from(completed)
            .where(completed.c.outcome == AgentRunOutcome.waiting_approval)
        )
    ) or 0
    escalated = (
        await db.scalar(
            select(func.count())
            .select_from(completed)
            .where(completed.c.outcome == AgentRunOutcome.escalated)
        )
    ) or 0
    hits = (
        await db.scalar(
            select(func.count()).select_from(completed).where(completed.c.retrieval_hit.is_(True))
        )
    ) or 0

    failed_runs = (
        await db.scalar(
            select(func.count(AgentRun.id)).where(
                AgentRun.organization_id == organization_id,
                AgentRun.status == AgentRunStatus.failed,
            )
        )
    ) or 0
    failed_deliveries = (
        await db.scalar(
            select(func.count(WebhookDelivery.id)).where(
                WebhookDelivery.organization_id == organization_id,
                WebhookDelivery.status == DeliveryStatus.failed,
            )
        )
    ) or 0

    def rate(numerator: int) -> float:
        return round(numerator / total_completed, 4) if total_completed else 0.0

    return Metrics(
        total_tickets=total_tickets,
        tickets_by_status=tickets_by_status,
        avg_agent_latency_ms=round(float(avg_latency), 2),
        avg_estimated_cost_usd=round(float(avg_cost), 8),
        approval_rate=rate(waiting),
        escalation_rate=rate(escalated),
        retrieval_hit_rate=rate(hits),
        failed_jobs=failed_runs + failed_deliveries,
    )
