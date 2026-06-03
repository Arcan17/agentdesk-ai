"""Human-in-the-loop approval flow tests."""
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


async def _ticket_waiting_approval(client, token) -> str:
    await client.post(
        "/api/v1/documents",
        headers=_auth(token),
        json={
            "title": "Password reset",
            "content": "To reset your password open settings then click forgot password link.",
        },
    )
    created = await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": "Forgot password", "description": "reset my password in settings"},
    )
    tid = created.json()["id"]
    run = await client.post(f"/api/v1/tickets/{tid}/run", headers=_auth(token))
    assert run.json()["outcome"] == "waiting_approval"
    return tid


@pytest.mark.asyncio
async def test_approve_sets_final_response(client, db_session):
    token = await _register(client)
    tid = await _ticket_waiting_approval(client, token)
    resp = await client.post(
        f"/api/v1/tickets/{tid}/approve", headers=_auth(token), json={}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["final_response"]

    events = {e.event for e in await db_session.scalars(select(AuditLog))}
    assert AuditEvent.response_approved in events


@pytest.mark.asyncio
async def test_edit_then_approve_uses_edited_text(client):
    token = await _register(client)
    tid = await _ticket_waiting_approval(client, token)
    edit = await client.patch(
        f"/api/v1/tickets/{tid}/edit-draft",
        headers=_auth(token),
        json={"content": "Custom operator answer."},
    )
    assert edit.status_code == 200
    approve = await client.post(
        f"/api/v1/tickets/{tid}/approve", headers=_auth(token), json={}
    )
    assert approve.json()["final_response"] == "Custom operator answer."


@pytest.mark.asyncio
async def test_edit_empty_rejected(client):
    token = await _register(client)
    tid = await _ticket_waiting_approval(client, token)
    resp = await client.patch(
        f"/api/v1/tickets/{tid}/edit-draft", headers=_auth(token), json={"content": "   "}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reject_sets_rejected(client, db_session):
    token = await _register(client)
    tid = await _ticket_waiting_approval(client, token)
    resp = await client.post(
        f"/api/v1/tickets/{tid}/reject", headers=_auth(token), json={"reason": "not good"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    events = {e.event for e in await db_session.scalars(select(AuditLog))}
    assert AuditEvent.response_rejected in events


@pytest.mark.asyncio
async def test_approve_wrong_state_conflicts(client):
    token = await _register(client)
    # fresh ticket in 'new' cannot be approved
    created = await client.post(
        "/api/v1/tickets", headers=_auth(token), json={"title": "t", "description": "d"}
    )
    tid = created.json()["id"]
    resp = await client.post(
        f"/api/v1/tickets/{tid}/approve", headers=_auth(token), json={"edited_response": "x"}
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_viewer_cannot_approve(client):
    admin = await _register(client)
    tid = await _ticket_waiting_approval(client, admin)
    await client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "viewer@acme.com", "password": "viewerpass", "role": "viewer"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "viewer@acme.com", "password": "viewerpass"}
    )
    viewer = login.json()["access_token"]
    resp = await client.post(
        f"/api/v1/tickets/{tid}/approve", headers=_auth(viewer), json={}
    )
    assert resp.status_code == 403
