"""Audit logging: ticket_created plus login_success / login_failed."""
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


async def _events(db_session) -> list[AuditEvent]:
    rows = await db_session.scalars(select(AuditLog))
    return [r.event for r in rows]


@pytest.mark.asyncio
async def test_ticket_created_is_audited(client, db_session):
    token = await _register(client)
    await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": "t", "description": "d"},
    )
    assert AuditEvent.ticket_created in await _events(db_session)


@pytest.mark.asyncio
async def test_login_success_audited(client, db_session):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "admin@acme.com", "password": "supersecret"}
    )
    assert resp.status_code == 200
    assert AuditEvent.login_success in await _events(db_session)


@pytest.mark.asyncio
async def test_login_failed_audited(client, db_session):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "admin@acme.com", "password": "wrongpass1"}
    )
    assert resp.status_code == 401
    assert AuditEvent.login_failed in await _events(db_session)
