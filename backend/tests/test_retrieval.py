"""Deterministic semantic retrieval (mock embeddings)."""
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


async def _add_doc(client, token, title, content):
    resp = await client.post(
        "/api/v1/documents",
        headers=_auth(token),
        json={"title": title, "content": content},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_relevant_query_returns_matching_chunk(client):
    token = await _register(client)
    billing_id = await _add_doc(
        client, token, "Billing", "billing invoice payment refund charges subscription"
    )
    await _add_doc(
        client, token, "Auth", "password login account security two factor authentication"
    )

    resp = await client.post(
        "/api/v1/documents/search",
        headers=_auth(token),
        json={"query": "billing payment refund", "threshold": 0.1, "top_k": 5},
    )
    assert resp.status_code == 200
    hits = resp.json()
    assert hits, "expected at least one hit"
    # the billing document should rank first
    assert hits[0]["document_id"] == billing_id
    # scores are sorted descending
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_threshold_filters_unrelated(client):
    token = await _register(client)
    await _add_doc(client, token, "Billing", "billing invoice payment refund charges")

    # gibberish query shares no vocabulary -> cosine ~0 -> below default threshold
    resp = await client.post(
        "/api/v1/documents/search",
        headers=_auth(token),
        json={"query": "zzzz qqqq wxyz", "threshold": 0.5},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_identical_text_high_similarity(client):
    token = await _register(client)
    await _add_doc(client, token, "Note", "alpha bravo charlie delta echo")
    resp = await client.post(
        "/api/v1/documents/search",
        headers=_auth(token),
        json={"query": "alpha bravo charlie delta echo", "threshold": 0.9},
    )
    assert resp.status_code == 200
    hits = resp.json()
    assert hits and hits[0]["score"] >= 0.9
