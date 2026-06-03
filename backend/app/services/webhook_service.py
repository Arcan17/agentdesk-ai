"""Webhook configuration, signing, and delivery.

Notifications are signed with HMAC-SHA256 over the exact serialized JSON body so that
recipients can verify authenticity and integrity (FR-022). Delivery attempts are recorded;
the Celery task applies bounded exponential-backoff retries (FR-023).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditEvent
from app.models.ticket import Ticket
from app.models.webhook import Webhook
from app.models.webhook_delivery import DeliveryStatus, WebhookDelivery
from app.services import audit_service

SIGNATURE_HEADER = "X-AgentDesk-Signature"
TIMESTAMP_HEADER = "X-AgentDesk-Timestamp"
EVENT_HEADER = "X-AgentDesk-Event"


def serialize_payload(payload: dict) -> bytes:
    """Deterministic JSON body used for both signing and sending."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify(secret: str, body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign(secret, body), signature)


async def get_config(db: AsyncSession, *, organization_id: uuid.UUID) -> Webhook | None:
    return await db.scalar(
        select(Webhook).where(Webhook.organization_id == organization_id)
    )


async def upsert_config(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    url: str,
    secret: str,
    is_active: bool,
) -> Webhook:
    webhook = await get_config(db, organization_id=organization_id)
    if webhook is None:
        webhook = Webhook(
            organization_id=organization_id, url=url, secret=secret, is_active=is_active
        )
        db.add(webhook)
    else:
        webhook.url = url
        webhook.secret = secret
        webhook.is_active = is_active
    await db.commit()
    await db.refresh(webhook)
    return webhook


def build_ticket_payload(ticket: Ticket, event: str, delivery_id: uuid.UUID) -> dict:
    return {
        "event": event,
        "delivery_id": str(delivery_id),
        "organization_id": str(ticket.organization_id),
        "ticket": {
            "id": str(ticket.id),
            "title": ticket.title,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "final_response": ticket.final_response,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        },
        "sent_at": datetime.now(UTC).isoformat(),
    }


async def enqueue_for_ticket(
    db: AsyncSession, *, ticket: Ticket, event: str
) -> WebhookDelivery | None:
    """Create a pending delivery (if an active webhook exists) and dispatch it.

    Returns the delivery, or None when the organization has no active webhook.
    """
    webhook = await get_config(db, organization_id=ticket.organization_id)
    if webhook is None or not webhook.is_active:
        return None

    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        organization_id=ticket.organization_id,
        event=event,
        payload={},
        status=DeliveryStatus.pending,
    )
    db.add(delivery)
    await db.flush()
    delivery.payload = build_ticket_payload(ticket, event, delivery.id)
    await db.commit()
    await db.refresh(delivery)

    if not settings.webhook_dispatch_enabled:
        return delivery  # recorded only (tests)
    if settings.webhook_delivery_eager:
        await deliver_once(db, delivery_id=delivery.id)
    else:
        from app.workers.tasks import deliver_webhook  # lazy: avoid celery import in tests

        deliver_webhook.delay(str(delivery.id))
    return delivery


async def deliver_once(
    db: AsyncSession,
    *,
    delivery_id: uuid.UUID,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Perform a single delivery attempt. Returns True on success (HTTP 2xx)."""
    delivery = await db.get(WebhookDelivery, delivery_id)
    if delivery is None:
        return False
    webhook = await db.get(Webhook, delivery.webhook_id)
    if webhook is None:
        return False

    body = serialize_payload(delivery.payload)
    headers = {
        "Content-Type": "application/json",
        EVENT_HEADER: delivery.event,
        TIMESTAMP_HEADER: str(int(time.time())),
        SIGNATURE_HEADER: sign(webhook.secret, body),
    }
    delivery.attempts += 1

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=settings.webhook_timeout_seconds)
    try:
        resp = await client.post(webhook.url, content=body, headers=headers)
        delivery.last_status_code = resp.status_code
        success = 200 <= resp.status_code < 300
    except Exception as exc:  # noqa: BLE001 - record and signal failure for retry
        delivery.last_error = str(exc)
        success = False
    finally:
        if owns_client:
            await client.aclose()

    if success:
        delivery.status = DeliveryStatus.success
        await audit_service.record(
            db,
            event=AuditEvent.webhook_sent,
            organization_id=delivery.organization_id,
            target_type="webhook_delivery",
            target_id=delivery.id,
            meta={"event": delivery.event, "status_code": delivery.last_status_code},
        )
    elif delivery.attempts >= settings.webhook_max_retries:
        delivery.status = DeliveryStatus.failed

    await db.commit()
    return success
