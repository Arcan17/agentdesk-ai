"""Orchestrates an AI workflow run for a ticket.

`start_run` creates the AgentRun record (so the API can return immediately), and
`execute_run` runs the LangGraph workflow, persists results, writes audit events, and
transitions the ticket to waiting_approval or escalated.
"""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.cost import estimate_cost
from app.agent.graph import run_workflow
from app.agent.state import AgentState
from app.models.agent_run import AgentRun, AgentRunOutcome, AgentRunStatus
from app.models.audit_log import AuditEvent
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.services import audit_service, ticket_service


async def start_run(
    db: AsyncSession, *, ticket: Ticket, actor_user_id: uuid.UUID | None
) -> AgentRun:
    run = AgentRun(
        ticket_id=ticket.id,
        organization_id=ticket.organization_id,
        status=AgentRunStatus.running,
    )
    db.add(run)
    await db.flush()
    await audit_service.record(
        db,
        event=AuditEvent.agent_run_started,
        organization_id=ticket.organization_id,
        actor_user_id=actor_user_id,
        target_type="ticket",
        target_id=ticket.id,
        meta={"agent_run_id": str(run.id)},
    )
    await db.commit()
    await db.refresh(run)
    return run


async def execute_run(db: AsyncSession, *, run_id: uuid.UUID) -> AgentRun:
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise ValueError("AgentRun not found")
    ticket = await db.get(Ticket, run.ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")

    started = time.perf_counter()
    try:
        initial: AgentState = {
            "organization_id": str(ticket.organization_id),
            "ticket_title": ticket.title,
            "ticket_description": ticket.description,
        }
        state = await run_workflow(db, initial)
        latency_ms = int((time.perf_counter() - started) * 1000)

        run.classification = state.get("classification")
        run.retrieved_chunk_ids = [r["chunk_id"] for r in state.get("retrieved", [])]
        run.retrieval_hit = bool(state.get("retrieval_hit"))
        run.draft = state.get("draft")
        run.confidence = state.get("confidence")
        run.prompt_tokens = state.get("prompt_tokens", 0)
        run.completion_tokens = state.get("completion_tokens", 0)
        run.estimated_cost_usd = estimate_cost(
            state.get("model", "mock-1"),
            run.prompt_tokens or 0,
            run.completion_tokens or 0,
        )
        run.latency_ms = latency_ms

        # audit mid-graph milestones
        await audit_service.record(
            db,
            event=AuditEvent.retrieval_completed,
            organization_id=ticket.organization_id,
            target_type="ticket",
            target_id=ticket.id,
            meta={"hits": len(run.retrieved_chunk_ids or []), "hit": run.retrieval_hit},
        )
        await audit_service.record(
            db,
            event=AuditEvent.draft_generated,
            organization_id=ticket.organization_id,
            target_type="ticket",
            target_id=ticket.id,
            meta={"confidence": run.confidence},
        )

        # apply classifier suggestions + draft to the ticket
        ticket.suggested_type = state.get("suggested_type")
        sp = state.get("suggested_priority")
        ticket.suggested_priority = TicketPriority(sp) if sp else None
        ticket.draft_response = run.draft

        outcome = state.get("outcome", "escalated")
        if outcome == "waiting_approval":
            run.outcome = AgentRunOutcome.waiting_approval
            await ticket_service.transition(
                db,
                ticket=ticket,
                to_status=TicketStatus.waiting_approval,
                actor_user_id=None,
                event_type="agent_run",
                message="AI draft ready for approval",
            )
        else:
            run.outcome = AgentRunOutcome.escalated
            await ticket_service.transition(
                db,
                ticket=ticket,
                to_status=TicketStatus.escalated,
                actor_user_id=None,
                event_type="agent_run",
                message="Low confidence; escalated for human handling",
            )
            await audit_service.record(
                db,
                event=AuditEvent.ticket_escalated,
                organization_id=ticket.organization_id,
                target_type="ticket",
                target_id=ticket.id,
                meta={"confidence": run.confidence},
            )

        run.status = AgentRunStatus.completed
        run.finished_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001 - record failure, re-raise for caller/worker
        await db.rollback()
        run = await db.get(AgentRun, run_id)
        if run is not None:
            run.status = AgentRunStatus.failed
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
            await db.commit()
        raise
