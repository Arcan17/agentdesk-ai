"""Celery tasks. Each opens its own async DB session and bridges to async code."""
from __future__ import annotations

import asyncio
import uuid

from app.db.engine import SessionLocal
from app.services import agent_run_service
from app.workers.celery_app import celery_app


async def _run_agent(run_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        await agent_run_service.execute_run(db, run_id=run_id)


@celery_app.task(name="run_agent")
def run_agent(run_id: str) -> str:
    asyncio.run(_run_agent(uuid.UUID(run_id)))
    return run_id
