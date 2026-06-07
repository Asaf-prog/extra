"""State carried through the example LangGraph workflow."""

from __future__ import annotations

from typing import Literal, TypedDict

Route = Literal["general", "tool"]


class AgentState(TypedDict, total=False):
    """Mutable graph state updated by each LangGraph node."""

    message: str
    route: Route
    tool_result: str
    answer: str
    final_response: str
    steps: list[str]
