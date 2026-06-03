"""Typed state passed between LangGraph nodes."""
from __future__ import annotations

from typing import TypedDict


class RetrievedRef(TypedDict):
    chunk_id: str
    document_id: str
    content: str
    score: float


class AgentState(TypedDict, total=False):
    # inputs
    organization_id: str
    ticket_title: str
    ticket_description: str

    # classifier
    classification: dict
    suggested_type: str
    suggested_priority: str

    # retriever
    retrieved: list[RetrievedRef]
    retrieval_hit: bool

    # draft
    draft: str
    model: str
    prompt_tokens: int
    completion_tokens: int

    # critic / decision
    confidence: float
    outcome: str  # "waiting_approval" | "escalated"
