"""Auth flow tests: register, login, refresh, bad credentials."""
from __future__ import annotations

import pytest


async def _register(client, org="Acme", email="admin@acme.com", pw="supersecret"):
    return await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": pw},
    )


@pytest.mark.asyncio
async def test_register_returns_token_pair(client):
    resp = await _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_org_conflicts(client):
    await _register(client)
    resp = await _register(client, email="other@acme.com")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success_and_bad_password(client):
    await _register(client)
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "supersecret"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@acme.com", "password": "whatever12"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client):
    reg = await _register(client)
    refresh_token = reg.json()["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client):
    reg = await _register(client)
    access = reg.json()["access_token"]
    # an access token must not be accepted by the refresh endpoint
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401
