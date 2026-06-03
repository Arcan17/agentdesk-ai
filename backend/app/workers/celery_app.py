"""Celery application for asynchronous jobs (agent runs, webhook delivery)."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "agentdesk",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
)
