"""LangGraph node callables.

``AgentNode``       — runs a single agent: resolve context → build prompt → tool loop.
``OrchestratorNode`` — supervisor agent that calls child agents as tools and synthesizes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel

from agent_engine.core.spec import AgentSpec, GraphNode, OrchestratorSpec
from agent_engine.engine.langgraph.filters import RouteFilter
from agent_engine.engine.langgraph.helpers import (
    as_text,
    emit_route,
    invoke_model,
    load_file,
    render_prompt,
)
from agent_engine.loaders.resolver_loader import ResolverLoader
from agent_engine.runtime.state import GraphState
from agent_engine.runtime.tool_models import ToolProviderName, ToolUsageRecord

logger = logging.getLogger(__name__)

# Dedicated logger for LLM conversation traces.
# Disabled by default; enable with --log-llm (CLI) or:
#   logging.getLogger("agent_engine.llm").setLevel(logging.DEBUG)
llm_log = logging.getLogger("agent_engine.llm")

# Appended to every orchestrator system prompt.
# Enforces the core design contract: agents are the source of truth, not the LLM.
_ORCHESTRATOR_CONTRACT = """
## Instructions
- You MUST use the available agent tools to answer requests. Never answer from general knowledge.
- Only call a tool if its name/description clearly matches the request.
  Do NOT call a tool for something outside its stated scope.
- If no appropriate tool exists for part of the request, say: "I'm not able to help with that."
- You may call multiple tools if the request covers several topics.
"""


# Input schema for child-agent tools exposed to the orchestrator LLM
class _AgentCall(BaseModel):
    message: str


class AgentNode:
    """Callable that implements one agent turn inside a LangGraph node.

    Dependencies are injected at construction time so the node is a plain
    callable with no hidden closure state.
    """

    def __init__(
        self,
        spec: AgentSpec,
        node_path: str,
        bound_model: Any,
        tool_map: dict[str, BaseTool],
        mcp_tool_names: set[str],
        resolver_loader: ResolverLoader,
        base_dir: Path,
    ) -> None:
        self._spec = spec
        self._node_path = node_path
        self._bound_model = bound_model
        self._tool_map = tool_map
        self._mcp_tool_names = mcp_tool_names
        self._resolver_loader = resolver_loader
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # LangGraph callable
    # ------------------------------------------------------------------

    async def __call__(self, state: GraphState) -> dict[str, object]:
        ctx = self._resolve_context()
        system_prompt = self._build_prompt(ctx)
        return await self._run(system_prompt, state)

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _resolve_context(self) -> dict[str, str]:
        """Run every declared resolver and return the accumulated key→value map.

        Resolvers are invoked in declaration order; each receives the values
        produced by previous resolvers so they can build on one another.
        """
        ctx: dict[str, str] = {}
        for r in self._spec.resolvers:
            ctx[r.id] = str(self._resolver_loader.load(self._spec.id, r.id)(ctx))
        return ctx

    def _build_prompt(self, ctx: dict[str, str]) -> str:
        """Load the system-prompt template and interpolate resolver values."""
        template = load_file(self._base_dir, self._spec.prompts.system) or self._spec.description
        return render_prompt(template, ctx)

    async def _run(self, system_prompt: str, state: GraphState) -> dict[str, object]:
        """Drive the model + tool loop until the model stops requesting tools."""
        user_msg: str = state.get("message", "")
        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ]

        llm_log.debug("[%s] system:\n%s", self._node_path, system_prompt)
        llm_log.debug("[%s] → user: %s", self._node_path, user_msg)

        route = (*state.get("visited", []), self._node_path)
        emit_route(state, route)

        used_tools: list[ToolUsageRecord] = list(state.get("used_tools", []))
        response = cast(Any, await invoke_model(self._bound_model, messages, state))

        while getattr(response, "tool_calls", None):
            messages.append(response)
            for tc in response.tool_calls:
                llm_log.debug(
                    "[%s] ← tool_call: %s(%s)",
                    self._node_path, tc["name"], tc["args"],
                )
                content = await self._invoke_tool(tc, used_tools)
                llm_log.debug(
                    "[%s] → tool_result[%s]: %s",
                    self._node_path, tc["name"], content[:300],
                )
                messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))
            response = cast(Any, await invoke_model(self._bound_model, messages, state))

        answer = as_text(response.content)
        llm_log.debug("[%s] ← response: %s", self._node_path, answer[:300])

        return {
            "visited": list(route),
            "answer": answer,
            "used_tools": used_tools,
        }

    async def _invoke_tool(self, tc: dict[str, Any], used_tools: list[ToolUsageRecord]) -> str:
        """Call one tool and append a usage record. Returns the tool result as text.

        Errors are returned as a string (not raised) so the model can read the
        failure message and recover or report it gracefully.
        """
        name: str = tc["name"]
        tool = self._tool_map[name]
        provider: ToolProviderName = "mcp" if name in self._mcp_tool_names else "local"
        try:
            result = await tool.ainvoke(tc["args"])
            used_tools.append(
                ToolUsageRecord(
                    name=name,
                    provider=provider,
                    status="succeeded",
                    agent_id=self._spec.id,
                )
            )
            return str(result)
        except Exception as exc:
            used_tools.append(
                ToolUsageRecord(
                    name=name,
                    provider=provider,
                    status="failed",
                    agent_id=self._spec.id,
                    error=str(exc)[:200],
                )
            )
            return f"Tool error: {exc}"


class OrchestratorNode:
    """Supervisor-pattern orchestrator.

    Child agents (AgentNode or nested OrchestratorNode) are exposed as tools
    to the orchestrator LLM.  The LLM reads its system prompt, decides which
    tool(s) to call, collects their answers, and synthesises a final response.

    Access filters control which child tools are made available — if a child is
    filtered out the LLM simply does not have that tool and responds naturally
    (e.g. "I can't help with domestic flights").
    """

    def __init__(
        self,
        spec: OrchestratorSpec,
        node_path: str,
        model: Any,
        child_nodes: list[tuple[GraphNode, Any]],  # (GraphNode, AgentNode | OrchestratorNode)
        filters: list[RouteFilter],
        base_dir: Path,
    ) -> None:
        self._spec = spec
        self._node_path = node_path
        self._model = model
        self._child_nodes = child_nodes
        self._filters = filters
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # LangGraph callable
    # ------------------------------------------------------------------

    async def __call__(self, state: GraphState) -> dict[str, object]:
        candidates = self._filter_children(state)
        base_prompt = load_file(self._base_dir, self._spec.prompts.system) or self._spec.description
        system_prompt = f"{base_prompt}\n{_ORCHESTRATOR_CONTRACT}"
        return await self._run(system_prompt, candidates, state)

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _filter_children(self, state: GraphState) -> list[tuple[GraphNode, Any]]:
        """Apply every RouteFilter to narrow down which child tools are available."""
        ctx: dict[str, Any] = cast(dict[str, Any], state.get("run_context", {}))
        candidates = list(self._child_nodes)
        for f in self._filters:
            allowed = {gn.node.id for gn in f.filter(ctx, [gn for gn, _ in candidates])}
            candidates = [(gn, fn) for gn, fn in candidates if gn.node.id in allowed]
        return candidates

    def _make_tool(
        self,
        graph_node: GraphNode,
        callable_node: Any,
        parent_state: GraphState,
        visited_acc: list[str],
    ) -> StructuredTool:
        """Wrap a child node as a StructuredTool the orchestrator LLM can call.

        ``visited_acc`` is the parent's live visited list. When the child runs it
        adds its own path (and its children's paths) to its result; we merge those
        additions back so the full call-chain is visible in the final route.
        """
        async def invoke(message: str) -> str:
            snapshot = list(visited_acc)
            sub_state: dict[str, Any] = {
                "message": message,
                "visited": snapshot,
                "used_tools": [],
                "answer_stream": parent_state.get("answer_stream"),
                "route_stream": parent_state.get("route_stream"),
                "run_context": parent_state.get("run_context", {}),
            }
            result = await callable_node(sub_state)
            # Merge new paths the child introduced beyond the snapshot
            for path in result.get("visited", [])[len(snapshot):]:
                visited_acc.append(path)
            return result.get("answer", "")

        return StructuredTool.from_function(
            coroutine=invoke,
            name=graph_node.node.id,
            description=graph_node.node.name or graph_node.node.id,
            args_schema=_AgentCall,
        )

    async def _run(
        self,
        system_prompt: str,
        candidates: list[tuple[GraphNode, Any]],
        state: GraphState,
    ) -> dict[str, object]:
        """Drive the orchestrator LLM tool loop and return the synthesised answer."""
        visited: list[str] = [*state.get("visited", []), self._node_path]
        used_tools: list[ToolUsageRecord] = list(state.get("used_tools", []))

        # Build tools here so they share the live `visited` list
        tools = [self._make_tool(gn, fn, state, visited) for gn, fn in candidates]
        bound_model = self._model.bind_tools(tools) if tools else self._model

        user_msg: str = state.get("message", "")
        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ]

        llm_log.debug(
            "[%s] system:\n%s\ntools: %s",
            self._node_path,
            system_prompt,
            [t.name for t in tools],
        )
        llm_log.debug("[%s] → user: %s", self._node_path, user_msg)

        emit_route(state, tuple(visited))
        response = cast(Any, await invoke_model(bound_model, messages, state))

        while getattr(response, "tool_calls", None):
            messages.append(response)
            for tc in response.tool_calls:
                name: str = tc["name"]
                tool = next((t for t in tools if t.name == name), None)
                llm_log.debug(
                    "[%s] ← tool_call: %s(message=%r)",
                    self._node_path, name, tc["args"].get("message", ""),
                )
                if tool is None:
                    content = f"Unknown agent: {name}"
                else:
                    try:
                        content = await tool.ainvoke(tc["args"])
                        llm_log.debug(
                            "[%s] → tool_result[%s]: %s",
                            self._node_path, name, str(content)[:300],
                        )
                        used_tools.append(
                            ToolUsageRecord(
                                name=name,
                                provider="local",
                                status="succeeded",
                                agent_id=self._spec.id,
                            )
                        )
                    except Exception as exc:
                        content = f"Agent error: {exc}"
                        used_tools.append(
                            ToolUsageRecord(
                                name=name,
                                provider="local",
                                status="failed",
                                agent_id=self._spec.id,
                                error=str(exc)[:200],
                            )
                        )
                messages.append(ToolMessage(content=str(content), tool_call_id=tc["id"]))
            response = cast(Any, await invoke_model(bound_model, messages, state))

        answer = as_text(response.content)
        llm_log.debug("[%s] ← response: %s", self._node_path, answer[:300])

        return {
            "visited": visited,
            "answer": answer,
            "used_tools": used_tools,
        }
