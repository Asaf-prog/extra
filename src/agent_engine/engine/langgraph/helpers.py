from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from agent_engine.core.spec import AgentSpec, GraphNode
from agent_engine.runtime.state import GraphState


def node_id(node: GraphNode, parent_path: str | None) -> str:
    return f"{parent_path}/{node.node.id}" if parent_path else node.node.id


def render_prompt(template: str, ctx: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        return ctx.get(match.group(1).strip(), match.group(0))
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, template)


def load_file(base_dir: Path, rel_path: str | None) -> str:
    if not rel_path:
        return ""
    path = base_dir / rel_path
    return path.read_text(encoding="utf-8") if path.is_file() else ""


async def invoke_model(model: Any, messages: list, state: GraphState) -> Any:
    answer_stream = state.get("answer_stream")
    if not callable(answer_stream):
        return await model.ainvoke(messages)
    streamed = None
    async for chunk in model.astream(messages):
        streamed = chunk if streamed is None else streamed + chunk
        text = as_text(getattr(chunk, "content", ""))
        if text:
            answer_stream(text)
    return streamed or AIMessage(content="")


def emit_route(state: GraphState, route: tuple[str, ...]) -> None:
    fn = state.get("route_stream")
    if callable(fn):
        fn(route)


def as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b["text"] for b in content if isinstance(b, dict) and isinstance(b.get("text"), str)
        )
    return str(content)


def has_protected_nodes(node: GraphNode) -> bool:
    if node.node.protected:
        return True
    return any(has_protected_nodes(c) for c in node.children)


def collect_mcp_servers(node: GraphNode) -> dict[str, str]:
    """Return {server_id: url} for every unique MCP server in the graph."""
    result: dict[str, str] = {}
    if isinstance(node.node, AgentSpec):
        for mcp in node.node.mcps:
            result.setdefault(mcp.id, mcp.url)
    for child in node.children:
        result.update(collect_mcp_servers(child))
    return result
