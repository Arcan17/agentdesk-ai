"""Webhook signing, enqueue-on-approve, and delivery (success + bounded retry)."""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.audit_log import AuditEvent, AuditLog
from app.models.webhook_delivery import DeliveryStatus, WebhookDelivery
from app.services import webhook_service

SECRET = "a-very-long-webhook-secret-key"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org="Acme", email="admin@acme.com", pw="supersecret"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": pw},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _configure_webhook(client, token, url="https://example.com/hook"):
    resp = await client.put(
        "/api/v1/webhooks",
        headers=_auth(token),
        json={"url": url, "secret": SECRET, "is_active": True},
    )
    assert resp.status_code == 200, resp.text


async def _ticket_waiting(client, token) -> str:
    await client.post(
        "/api/v1/documents",
        headers=_auth(token),
        json={"title": "Reset", "content": "to reset your password open settings forgot password"},
    )
    created = await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": "Forgot password", "description": "reset my password settings"},
    )
    tid = created.json()["id"]
    await client.post(f"/api/v1/tickets/{tid}/run", headers=_auth(token))
    return tid


def test_signature_roundtrip():
    body = webhook_service.serialize_payload({"b": 2, "a": 1})
    sig = webhook_service.sign(SECRET, body)
    assert sig.startswith("sha256=")
    assert webhook_service.verify(SECRET, body, sig)
    assert not webhook_service.verify("wrong-secret", body, sig)


@pytest.mark.asyncio
async def test_approve_records_pending_delivery_with_valid_signature(client, db_session):
    token = await _register(client)
    await _configure_webhook(client, token)
    tid = await _ticket_waiting(client, token)
    await client.post(f"/api/v1/tickets/{tid}/approve", headers=_auth(token), json={})

    delivery = (await db_session.scalars(select(WebhookDelivery))).first()
    assert delivery is not None
    assert delivery.event == "ticket.approved"
    assert delivery.status == DeliveryStatus.pending

    body = webhook_service.serialize_payload(delivery.payload)
    sig = webhook_service.sign(SECRET, body)
    assert webhook_service.verify(SECRET, body, sig)


@pytest.mark.asyncio
async def test_escalation_records_delivery(client, db_session):
    token = await _register(client)
    await _configure_webhook(client, token)
    # ticket with no matching KB -> escalated -> webhook enqueued
    created = await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": "Quantum", "description": "spooky action at a distance"},
    )
    tid = created.json()["id"]
    await client.post(f"/api/v1/tickets/{tid}/run", headers=_auth(token))
    delivery = (await db_session.scalars(select(WebhookDelivery))).first()
    assert delivery is not None and delivery.event == "ticket.escalated"


@pytest.mark.asyncio
async def test_deliver_once_success(client, db_session):
    token = await _register(client)
    await _configure_webhook(client, token)
    tid = await _ticket_waiting(client, token)
    await client.post(f"/api/v1/tickets/{tid}/approve", headers=_auth(token), json={})
    delivery = (await db_session.scalars(select(WebhookDelivery))).first()

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["sig"] = request.headers.get(webhook_service.SIGNATURE_HEADER)
        seen["body"] = request.content
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as hc:
        ok = await webhook_service.deliver_once(db_session, delivery_id=delivery.id, client=hc)

    assert ok is True
    await db_session.refresh(delivery)
    assert delivery.status == DeliveryStatus.success
    assert delivery.attempts == 1
    # signature on the wire verifies against our secret
    assert webhook_service.verify(SECRET, seen["body"], seen["sig"])

    events = {e.event for e in await db_session.scalars(select(AuditLog))}
    assert AuditEvent.webhook_sent in events


@pytest.mark.asyncio
async def test_deliver_once_retries_then_failed(client, db_session):
    token = await _register(client)
    await _configure_webhook(client, token)
    tid = await _ticket_waiting(client, token)
    await client.post(f"/api/v1/tickets/{tid}/approve", headers=_auth(token), json={})
    delivery = (await db_session.scalars(select(WebhookDelivery))).first()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as hc:
        results = []
        for _ in range(settings.webhook_max_retries):
            results.append(
                await webhook_service.deliver_once(db_session, delivery_id=delivery.id, client=hc)
            )

    assert all(r is False for r in results)
    await db_session.refresh(delivery)
    assert delivery.attempts == settings.webhook_max_retries
    assert delivery.status == DeliveryStatus.failed
    assert delivery.last_status_code == 500
