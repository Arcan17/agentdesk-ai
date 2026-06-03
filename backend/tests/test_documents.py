"""Document ingestion, validation, and tenant isolation."""
from __future__ import annotations

import pytest


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
async def test_create_document_chunks_and_embeds(client):
    token = await _register(client, "Acme", "admin@acme.com")
    resp = await client.post(
        "/api/v1/documents",
        headers=_auth(token),
        json={
            "title": "Password reset guide",
            "content": "To reset your password open settings and click forgot password.",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["chunk_count"] >= 1
    assert body["title"] == "Password reset guide"


@pytest.mark.asyncio
async def test_empty_content_rejected(client):
    token = await _register(client, "Acme", "admin@acme.com")
    resp = await client.post(
        "/api/v1/documents",
        headers=_auth(token),
        json={"title": "Blank", "content": "   "},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_viewer_cannot_create_document(client):
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
        "/api/v1/documents",
        headers=_auth(viewer),
        json={"title": "x", "content": "some content here"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_document_tenant_isolation(client):
    a = await _register(client, "Acme", "admin@acme.com")
    b = await _register(client, "Globex", "admin@globex.com")
    await client.post(
        "/api/v1/documents",
        headers=_auth(a),
        json={"title": "Acme KB", "content": "acme internal billing policy details"},
    )
    # Globex sees no documents and search returns nothing from Acme
    listed = await client.get("/api/v1/documents", headers=_auth(b))
    assert listed.json() == []
    search = await client.post(
        "/api/v1/documents/search",
        headers=_auth(b),
        json={"query": "billing policy", "threshold": 0.0},
    )
    assert search.json() == []
