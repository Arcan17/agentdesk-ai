"""LangGraph node implementations: classifier, retriever, draft, critic, decision.

Nodes are built via a factory that closes over the DB session and config so the graph
itself stays a pure orchestration of state transitions. All logic is deterministic when
the mock provider is used, keeping tests reproducible.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState, RetrievedRef
from app.core.config import settings
from app.providers.factory import get_llm_provider
from app.services import retrieval_service

NodeFn = Callable[[AgentState], Awaitable[AgentState]]

_WORD_RE = re.compile(r"[a-z0-9]+")

# Lightweight keyword taxonomy for deterministic classification.
_TYPE_KEYWORDS: dict[str, set[str]] = {
    "billing": {"billing", "invoice", "payment", "refund", "charge", "subscription", "price"},
    "technical": {"error", "bug", "crash", "broken", "fail", "login", "password", "reset"},
    "account": {"account", "profile", "settings", "email", "username", "permission"},
}
_URGENT_WORDS = {"urgent", "asap", "immediately", "critical", "outage", "down"}


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def classifier_node(_db: AsyncSession) -> NodeFn:
    async def run(state: AgentState) -> AgentState:
        text = f"{state.get('ticket_title', '')} {state.get('ticket_description', '')}"
        toks = _tokens(text)
        scores = {t: len(toks & kws) for t, kws in _TYPE_KEYWORDS.items()}
        best_type = max(scores, key=lambda k: scores[k]) if any(scores.values()) else "general"
        priority = "urgent" if toks & _URGENT_WORDS else "medium"
        return {
            **state,
            "classification": {"type": best_type, "signals": scores},
            "suggested_type": best_type,
            "suggested_priority": priority,
        }

    return run


def retriever_node(db: AsyncSession) -> NodeFn:
    async def run(state: AgentState) -> AgentState:
        query = f"{state.get('ticket_title', '')} {state.get('ticket_description', '')}"
        hits = await retrieval_service.search(
            db,
            organization_id=uuid.UUID(state["organization_id"]),
            query=query,
        )
        retrieved: list[RetrievedRef] = [
            RetrievedRef(
                chunk_id=str(h.chunk.id),
                document_id=str(h.chunk.document_id),
                content=h.chunk.content,
                score=round(h.score, 6),
            )
            for h in hits
        ]
        return {**state, "retrieved": retrieved, "retrieval_hit": bool(retrieved)}

    return run


def draft_node(_db: AsyncSession) -> NodeFn:
    async def run(state: AgentState) -> AgentState:
        retrieved = state.get("retrieved", [])
        context = "\n\n".join(r["content"] for r in retrieved)
        prompt = (
            f"Ticket: {state.get('ticket_title', '')}\n"
            f"Details: {state.get('ticket_description', '')}\n"
            "Write a helpful support reply grounded in the provided context."
        )
        result = await get_llm_provider().complete(
            prompt,
            system="You are a careful support agent. Only use the provided context.",
            context=context,
        )
        return {
            **state,
            "draft": result.text,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
        }

    return run


def critic_node(_db: AsyncSession) -> NodeFn:
    """Score how well the draft is grounded in the retrieved context (0..1)."""

    async def run(state: AgentState) -> AgentState:
        retrieved = state.get("retrieved", [])
        if not retrieved:
            return {**state, "confidence": 0.0}
        top_score = max(r["score"] for r in retrieved)
        context_tokens = _tokens(" ".join(r["content"] for r in retrieved))
        draft_tokens = _tokens(state.get("draft", ""))
        overlap = (
            len(context_tokens & draft_tokens) / len(context_tokens)
            if context_tokens
            else 0.0
        )
        confidence = round(0.5 * float(top_score) + 0.5 * overlap, 6)
        return {**state, "confidence": min(1.0, confidence)}

    return run


def decision_node(_db: AsyncSession) -> NodeFn:
    async def run(state: AgentState) -> AgentState:
        confidence = state.get("confidence", 0.0)
        outcome = (
            "waiting_approval"
            if confidence >= settings.confidence_threshold
            else "escalated"
        )
        return {**state, "outcome": outcome}

    return run
