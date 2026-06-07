"""Small LangGraph node functions used by the example workflow."""

from __future__ import annotations

from .state import AgentState, Route
from .tools import count_words


def _steps(state: AgentState) -> list[str]:
    return list(state.get("steps", []))


def _with_step(state: AgentState, step: str) -> list[str]:
    steps = _steps(state)
    steps.append(step)
    return steps


def _choose_route(message: str) -> Route:
    normalized = message.lower()
    if "count" in normalized or "word" in normalized:
        return "tool"
    return "general"


def route_request(state: AgentState) -> AgentState:
    """Choose whether the request needs a tool."""
    message = state["message"]
    route = _choose_route(message)
    return {
        "route": route,
        "steps": _with_step(state, f"route_request:{route}"),
    }


def answer_general(state: AgentState) -> AgentState:
    """Return a deterministic general answer."""
    message = state["message"]
    return {
        "answer": f"I can answer directly: {message}",
        "steps": _with_step(state, "answer_general"),
    }


def answer_with_tool(state: AgentState) -> AgentState:
    """Use a local LangChain tool and store its result."""
    message = state["message"]
    tool_result = str(count_words.invoke({"text": message}))
    return {
        "tool_result": tool_result,
        "answer": f"I used the word-count tool. {tool_result}.",
        "steps": _with_step(state, "answer_with_tool"),
    }


def finalize_response(state: AgentState) -> AgentState:
    """Produce the final response string."""
    return {
        "final_response": state["answer"],
        "steps": _with_step(state, "finalize_response"),
    }
