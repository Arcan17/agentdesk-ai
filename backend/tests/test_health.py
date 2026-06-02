"""Phase 1 smoke tests: app boots and health endpoint reports DB connectivity."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"]
