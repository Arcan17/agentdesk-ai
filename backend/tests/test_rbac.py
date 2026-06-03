"""RBAC + multi-tenant isolation tests."""
from __future__ import annotations

import pytest


async def _register(client, org, email, pw="supersecret"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": pw},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(client, email, pw="supersecret"):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": pw}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_can_create_user_viewer_cannot(client):
    admin = await _register(client, "Acme", "admin@acme.com")
    admin_token = admin["access_token"]

    # admin creates a viewer
    created = await client.post(
        "/api/v1/users",
        headers=_auth(admin_token),
        json={"email": "viewer@acme.com", "password": "viewerpass", "role": "viewer"},
    )
    assert created.status_code == 201

    viewer_token = await _login(client, "viewer@acme.com", "viewerpass")
    # viewer attempts to create a user -> forbidden
    denied = await client.post(
        "/api/v1/users",
        headers=_auth(viewer_token),
        json={"email": "x@acme.com", "password": "anotherpass", "role": "operator"},
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_requires_authentication(client):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tenant_isolation_user_list(client):
    a = await _register(client, "Acme", "admin@acme.com")
    b = await _register(client, "Globex", "admin@globex.com")

    # Acme admin creates one extra user
    await client.post(
        "/api/v1/users",
        headers=_auth(a["access_token"]),
        json={"email": "op@acme.com", "password": "operatorpw", "role": "operator"},
    )

    acme_list = await client.get("/api/v1/users", headers=_auth(a["access_token"]))
    globex_list = await client.get("/api/v1/users", headers=_auth(b["access_token"]))

    acme_emails = {u["email"] for u in acme_list.json()}
    globex_emails = {u["email"] for u in globex_list.json()}

    assert "op@acme.com" in acme_emails
    assert acme_emails.isdisjoint(globex_emails)
    assert globex_emails == {"admin@globex.com"}
