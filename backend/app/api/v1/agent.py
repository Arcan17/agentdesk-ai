"""Agent workflow endpoint: trigger an AI run for a ticket."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.ticket import TicketStatus
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.agent import AgentRunOut
from app.services import agent_run_service, ticket_service

router = APIRouter(prefix="/tickets", tags=["agent"])


@router.post(
    "/{ticket_id}/run",
    response_model=AgentRunOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_workflow(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin, Role.operator)),
) -> AgentRunOut:
    try:
        ticket = await ticket_service.get_ticket(
            db, organization_id=current.organization_id, ticket_id=ticket_id
        )
    except ticket_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        ) from exc

    if ticket.status == TicketStatus.closed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot run the workflow on a closed ticket",
        )

    run = await agent_run_service.start_run(db, ticket=ticket, actor_user_id=current.id)

    if settings.agent_run_eager:
        run = await agent_run_service.execute_run(db, run_id=run.id)
    else:
        from app.workers.tasks import run_agent  # lazy: avoid importing celery in tests

        run_agent.delay(str(run.id))

    return AgentRunOut.model_validate(run)
