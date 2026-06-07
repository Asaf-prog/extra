from __future__ import annotations

from langgraph_basic_agent.graph import build_graph


def test_graph_builds_successfully() -> None:
    graph = build_graph()

    assert graph is not None


def test_general_route_works() -> None:
    graph = build_graph()

    result = graph.invoke({"message": "hello there", "steps": []})

    assert result["route"] == "general"
    assert result["final_response"] == "I can answer directly: hello there"


def test_tool_route_works() -> None:
    graph = build_graph()

    result = graph.invoke({"message": "count words in this message", "steps": []})

    assert result["route"] == "tool"
    assert result["tool_result"] == "word_count=5"
    assert "word-count tool" in result["final_response"]


def test_final_response_is_produced() -> None:
    graph = build_graph()

    result = graph.invoke({"message": "general question", "steps": []})

    assert result["final_response"]


def test_steps_are_recorded() -> None:
    graph = build_graph()

    result = graph.invoke({"message": "count these words", "steps": []})

    assert result["steps"] == [
        "route_request:tool",
        "answer_with_tool",
        "finalize_response",
    ]
