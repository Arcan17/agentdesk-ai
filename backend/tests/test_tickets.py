"""Ticket CRUD, history, tenant isolation, and state-machine validation."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.ticket import Ticket, TicketStatus
from app.services import ticket_service


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org, email, pw="supersecret"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": pw},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_list_detail_and_history(client):
    token = await _register(client, "Acme", "admin@acme.com")
    created = await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": "Cannot login", "description": "User locked out", "priority": "high"},
    )
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["status"] == "new"
    assert ticket["priority"] == "high"

    listed = await client.get("/api/v1/tickets", headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/tickets/{ticket['id']}", headers=_auth(token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Cannot login"

    events = await client.get(f"/api/v1/tickets/{ticket['id']}/events", headers=_auth(token))
    assert events.status_code == 200
    types = [e["event_type"] for e in events.json()]
    assert "created" in types


@pytest.mark.asyncio
async def test_viewer_cannot_create_ticket(client):
    admin = await _register(client, "Acme", "admin@acme.com")
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
        "/api/v1/tickets",
        headers=_auth(viewer),
        json={"title": "x", "description": "y"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_tenant_isolation_tickets(client):
    a = await _register(client, "Acme", "admin@acme.com")
    b = await _register(client, "Globex", "admin@globex.com")
    created = await client.post(
        "/api/v1/tickets",
        headers=_auth(a),
        json={"title": "Acme issue", "description": "secret"},
    )
    tid = created.json()["id"]

    # Globex cannot see Acme's ticket
    detail = await client.get(f"/api/v1/tickets/{tid}", headers=_auth(b))
    assert detail.status_code == 404
    listed = await client.get("/api/v1/tickets", headers=_auth(b))
    assert listed.json() == []


@pytest.mark.asyncio
async def test_invalid_transition_raises(client, db_session):
    # Create org+user via API so FKs resolve, then test the service directly.
    await _register(client, "Acme", "admin@acme.com")
    ticket = (await db_session.scalars(select(Ticket))).first()
    # force terminal state, then attempt an illegal move
    await client.post(
        "/api/v1/tickets",
        headers=_auth(await _login(client)),
        json={"title": "t", "description": "d"},
    )
    ticket = (await db_session.scalars(select(Ticket))).first()
    ticket.status = TicketStatus.closed
    await db_session.flush()
    with pytest.raises(ticket_service.InvalidTransitionError):
        await ticket_service.transition(
            db_session,
            ticket=ticket,
            to_status=TicketStatus.approved,
            actor_user_id=None,
            event_type="test",
        )


async def _login(client, email="admin@acme.com", pw="supersecret"):
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    return resp.json()["access_token"]
