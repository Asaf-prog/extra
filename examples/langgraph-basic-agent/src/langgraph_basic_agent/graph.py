"""LangGraph construction for the reference example."""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from .nodes import (
    answer_general,
    answer_with_tool,
    finalize_response,
    route_request,
)
from .state import AgentState


def _route_edge(state: AgentState) -> Literal["general", "tool"]:
    return state.get("route", "general")


def build_graph():
    """Build and compile the example LangGraph workflow."""
    builder = StateGraph(AgentState)
    builder.add_node("route_request", route_request)
    builder.add_node("answer_general", answer_general)
    builder.add_node("answer_with_tool", answer_with_tool)
    builder.add_node("finalize_response", finalize_response)

    builder.add_edge(START, "route_request")
    builder.add_conditional_edges(
        "route_request",
        _route_edge,
        {
            "general": "answer_general",
            "tool": "answer_with_tool",
        },
    )
    builder.add_edge("answer_general", "finalize_response")
    builder.add_edge("answer_with_tool", "finalize_response")
    builder.add_edge("finalize_response", END)

    return builder.compile()
