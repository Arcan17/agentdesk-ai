"""LangGraph workflow tests (deterministic mock provider, eager execution)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditEvent, AuditLog


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org="Acme", email="admin@acme.com", pw="supersecret"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": pw},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _add_doc(client, token, title, content):
    resp = await client.post(
        "/api/v1/documents", headers=_auth(token), json={"title": title, "content": content}
    )
    assert resp.status_code == 201, resp.text


async def _create_ticket(client, token, title, description, priority="medium"):
    resp = await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": title, "description": description, "priority": priority},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_grounded_ticket_goes_to_waiting_approval(client):
    token = await _register(client)
    await _add_doc(
        client,
        token,
        "Password reset",
        "To reset your password open settings then click forgot password and follow the link.",
    )
    ticket_id = await _create_ticket(
        client, token, "Forgot password", "I need to reset my password from settings"
    )

    run = await client.post(f"/api/v1/tickets/{ticket_id}/run", headers=_auth(token))
    assert run.status_code == 202, run.text
    body = run.json()
    assert body["status"] == "completed"
    assert body["outcome"] == "waiting_approval"
    assert body["retrieval_hit"] is True
    assert body["draft"]
    assert body["confidence"] >= 0.7
    assert body["latency_ms"] is not None
    assert body["estimated_cost_usd"] is not None and body["estimated_cost_usd"] > 0

    detail = await client.get(f"/api/v1/tickets/{ticket_id}", headers=_auth(token))
    assert detail.json()["status"] == "waiting_approval"
    assert detail.json()["draft_response"]


@pytest.mark.asyncio
async def test_no_context_ticket_is_escalated(client, db_session):
    token = await _register(client)
    # knowledge base has unrelated content only
    await _add_doc(client, token, "Shipping", "orders are shipped within two business days")
    ticket_id = await _create_ticket(
        client, token, "Quantum entanglement", "explain spooky action at a distance"
    )

    run = await client.post(f"/api/v1/tickets/{ticket_id}/run", headers=_auth(token))
    assert run.status_code == 202, run.text
    body = run.json()
    assert body["outcome"] == "escalated"
    assert body["retrieval_hit"] is False

    detail = await client.get(f"/api/v1/tickets/{ticket_id}", headers=_auth(token))
    assert detail.json()["status"] == "escalated"

    events = [e for e in await db_session.scalars(select(AuditLog))]
    kinds = {e.event for e in events}
    assert AuditEvent.agent_run_started in kinds
    assert AuditEvent.retrieval_completed in kinds
    assert AuditEvent.draft_generated in kinds
    assert AuditEvent.ticket_escalated in kinds


@pytest.mark.asyncio
async def test_run_on_missing_ticket_404(client):
    token = await _register(client)
    resp = await client.post(
        "/api/v1/tickets/00000000-0000-0000-0000-000000000000/run", headers=_auth(token)
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_viewer_cannot_run_workflow(client):
    admin = await _register(client)
    await client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "viewer@acme.com", "password": "viewerpass", "role": "viewer"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "viewer@acme.com", "password": "viewerpass"}
    )
    viewer = login.json()["access_token"]
    ticket_id = await _create_ticket(client, admin, "t", "d")
    resp = await client.post(f"/api/v1/tickets/{ticket_id}/run", headers=_auth(viewer))
    assert resp.status_code == 403
