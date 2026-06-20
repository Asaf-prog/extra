from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from agent_engine.core.spec import AgentSpec, GraphNode
from agent_engine.runtime.state import GraphState

logger = logging.getLogger(__name__)


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


async def invoke_model(model: Any, messages: list[Any], state: GraphState) -> Any:
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


async def run_tool_loop(
    model: Any,
    messages: list[Any],
    state: GraphState,
    node_path: str,
    invoke_tool: Callable[[dict[str, Any]], Awaitable[str]],
) -> Any:
    """Drive the model → tools → model loop until the model stops calling tools.

    ``invoke_tool`` executes one tool call and returns its result as text. Each
    caller supplies its own: an agent runs real/MCP tools, an orchestrator runs
    child agents exposed as tools. The final (tool-call-free) model response is
    returned.
    """
    response = await invoke_model(model, messages, state)
    while getattr(response, "tool_calls", None):
        messages.append(response)
        for tc in response.tool_calls:
            logger.debug("[%s] ← tool_call: %s(%s)", node_path, tc["name"], tc["args"])
            content = await invoke_tool(tc)
            logger.debug("[%s] → tool_result[%s]: %s", node_path, tc["name"], content[:300])
            messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))
        response = await invoke_model(model, messages, state)
    return response


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


def collect_mcp_specs(node: GraphNode) -> dict[str, Any]:
    """Return {server_id: MCPSpec} for every unique MCP server in the graph."""
    from agent_engine.core.spec import MCPSpec

    result: dict[str, MCPSpec] = {}
    if isinstance(node.node, AgentSpec):
        for mcp in node.node.mcps:
            result.setdefault(mcp.id, mcp)
    for child in node.children:
        result.update(collect_mcp_specs(child))
    return result
