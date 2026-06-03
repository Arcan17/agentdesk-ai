"""Assemble the support workflow as a LangGraph state graph.

Flow: START → classifier → retriever → draft → critic → decision → END
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import nodes
from app.agent.state import AgentState


def build_graph(db: AsyncSession):
    graph = StateGraph(AgentState)
    # langgraph's add_node overloads don't recognize plain async closures; runtime is fine.
    graph.add_node("classifier", nodes.classifier_node(db))  # type: ignore[call-overload]
    graph.add_node("retriever", nodes.retriever_node(db))  # type: ignore[call-overload]
    graph.add_node("draft", nodes.draft_node(db))  # type: ignore[call-overload]
    graph.add_node("critic", nodes.critic_node(db))  # type: ignore[call-overload]
    graph.add_node("decision", nodes.decision_node(db))  # type: ignore[call-overload]

    graph.add_edge(START, "classifier")
    graph.add_edge("classifier", "retriever")
    graph.add_edge("retriever", "draft")
    graph.add_edge("draft", "critic")
    graph.add_edge("critic", "decision")
    graph.add_edge("decision", END)

    return graph.compile()


async def run_workflow(db: AsyncSession, initial: AgentState) -> AgentState:
    compiled = build_graph(db)
    result = await compiled.ainvoke(initial)
    return result  # type: ignore[return-value]
