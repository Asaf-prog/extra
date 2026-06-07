"""Run the deterministic LangGraph example."""

from __future__ import annotations

import sys

from .graph import build_graph
from .state import AgentState

DEFAULT_MESSAGE = "count the words in this simple local example"


def run(message: str = DEFAULT_MESSAGE) -> AgentState:
    graph = build_graph()
    return graph.invoke({"message": message, "steps": []})


def main() -> None:
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_MESSAGE
    result = run(message)

    print(f"Input: {message}")
    print(f"Route: {result.get('route')}")
    print(f"Final answer: {result.get('final_response')}")
    print("Steps:")
    for step in result.get("steps", []):
        print(f"  - {step}")


if __name__ == "__main__":
    main()
