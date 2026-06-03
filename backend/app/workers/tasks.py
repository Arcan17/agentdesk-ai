"""Celery tasks. Each opens its own async DB session and bridges to async code."""
from __future__ import annotations

import asyncio
import uuid

from app.core.config import settings
from app.db.engine import SessionLocal
from app.services import agent_run_service, webhook_service
from app.workers.celery_app import celery_app


async def _run_agent(run_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        await agent_run_service.execute_run(db, run_id=run_id)


@celery_app.task(name="run_agent")
def run_agent(run_id: str) -> str:
    asyncio.run(_run_agent(uuid.UUID(run_id)))
    return run_id


async def _deliver_webhook(delivery_id: uuid.UUID) -> bool:
    async with SessionLocal() as db:
        return await webhook_service.deliver_once(db, delivery_id=delivery_id)


@celery_app.task(name="deliver_webhook", bind=True, max_retries=settings.webhook_max_retries)
def deliver_webhook(self, delivery_id: str) -> str:
    success = asyncio.run(_deliver_webhook(uuid.UUID(delivery_id)))
    if not success and self.request.retries < settings.webhook_max_retries:
        # exponential backoff with jitter; deliver_once already recorded the attempt
        countdown = settings.webhook_backoff_base_seconds * (2**self.request.retries)
        raise self.retry(countdown=countdown)
    return delivery_id
