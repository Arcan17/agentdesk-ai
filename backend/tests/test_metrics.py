"""Metrics aggregation and RBAC."""
from __future__ import annotations

import pytest


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org="Acme", email="admin@acme.com", pw="supersecret"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": pw},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _run(client, token, title, description, *, with_kb=False):
    if with_kb:
        await client.post(
            "/api/v1/documents",
            headers=_auth(token),
            json={"title": "KB", "content": "to reset your password open settings forgot password"},
        )
    created = await client.post(
        "/api/v1/tickets",
        headers=_auth(token),
        json={"title": title, "description": description},
    )
    tid = created.json()["id"]
    return (await client.post(f"/api/v1/tickets/{tid}/run", headers=_auth(token))).json()


@pytest.mark.asyncio
async def test_metrics_reflect_runs(client):
    token = await _register(client)
    grounded = await _run(
        client, token, "Forgot password", "reset my password settings", with_kb=True
    )
    escalated = await _run(client, token, "Quantum", "spooky action at a distance")
    assert grounded["outcome"] == "waiting_approval"
    assert escalated["outcome"] == "escalated"

    resp = await client.get("/api/v1/admin/metrics", headers=_auth(token))
    assert resp.status_code == 200
    m = resp.json()
    assert m["total_tickets"] == 2
    assert m["tickets_by_status"].get("waiting_approval") == 1
    assert m["tickets_by_status"].get("escalated") == 1
    assert m["approval_rate"] == 0.5
    assert m["escalation_rate"] == 0.5
    assert m["retrieval_hit_rate"] == 0.5
    assert m["avg_agent_latency_ms"] >= 0
    assert m["avg_estimated_cost_usd"] > 0
    assert m["failed_jobs"] == 0


@pytest.mark.asyncio
async def test_metrics_requires_admin(client):
    admin = await _register(client)
    await client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "op@acme.com", "password": "operatorpw", "role": "operator"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "op@acme.com", "password": "operatorpw"}
    )
    op = login.json()["access_token"]
    resp = await client.get("/api/v1/admin/metrics", headers=_auth(op))
    assert resp.status_code == 403
