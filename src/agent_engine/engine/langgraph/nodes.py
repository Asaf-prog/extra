"""LangGraph node callables.

``AgentNode``       — runs a single agent: resolve context → build prompt → tool loop.
``OrchestratorRouter`` — selects the next child node for a routing node.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from agent_engine.core.spec import AgentSpec, GraphNode, OrchestratorSpec
from agent_engine.engine.langgraph.filters import RouteFilter
from agent_engine.engine.langgraph.helpers import (
    _RouteDecision,
    as_text,
    emit_route,
    invoke_model,
    load_file,
    node_id,
    render_prompt,
)
from agent_engine.loaders.resolver_loader import ResolverLoader
from agent_engine.runtime.state import GraphState
from agent_engine.runtime.tool_models import ToolProviderName, ToolUsageRecord

logger = logging.getLogger(__name__)


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
        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.get("message", "")),
        ]

        route = (*state.get("visited", []), self._node_path)
        emit_route(state, route)

        used_tools: list[ToolUsageRecord] = list(state.get("used_tools", []))
        response = cast(Any, await invoke_model(self._bound_model, messages, state))

        while getattr(response, "tool_calls", None):
            messages.append(response)
            for tc in response.tool_calls:
                content = await self._invoke_tool(tc, used_tools)
                messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))
            response = cast(Any, await invoke_model(self._bound_model, messages, state))

        return {
            "visited": list(route),
            "answer": as_text(response.content),
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


class OrchestratorRouter:
    """Callable that selects the next child node for a routing (orchestrator) node.

    The selection pipeline:
        1. ``_filter_candidates`` — apply each ``RouteFilter`` in order (access
           control, feature flags, etc.).
        2. ``_decide`` — call the routing LLM (if configured) to pick from the
           remaining candidates; fall back to the first candidate on any error.
    """

    def __init__(
        self,
        spec: OrchestratorSpec,
        node_path: str,
        children: list[GraphNode],
        routing_chain: Any | None,
        filters: list[RouteFilter],
        base_dir: Path,
    ) -> None:
        self._spec = spec
        self._node_path = node_path
        self._children = children
        self._routing_chain = routing_chain
        self._filters = filters
        self._base_dir = base_dir
        # Computed once; used when all candidates are filtered out
        self._fallback = node_id(children[0], node_path)

    # ------------------------------------------------------------------
    # LangGraph callable
    # ------------------------------------------------------------------

    async def __call__(self, state: GraphState) -> str:
        candidates = self._filter_candidates(state)
        if not candidates:
            logger.warning(
                "Orchestrator=%s: all candidates filtered out; routing to fallback",
                self._node_path,
            )
            return self._fallback
        return await self._decide(candidates, state)

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _filter_candidates(self, state: GraphState) -> list[GraphNode]:
        """Apply every RouteFilter in sequence to narrow down eligible children."""
        ctx: dict[str, Any] = cast(dict[str, Any], state.get("run_context", {}))
        candidates: list[GraphNode] = list(self._children)
        for f in self._filters:
            candidates = f.filter(ctx, candidates)
        return candidates

    async def _decide(self, candidates: list[GraphNode], state: GraphState) -> str:
        """Ask the routing LLM which candidate to pick.

        Falls back to the first remaining candidate when:
        - no routing model is configured, or
        - the model returns an unrecognised agent id, or
        - the model call raises an exception.
        """
        if self._routing_chain is None:
            return node_id(candidates[0], self._node_path)

        orchestrator_prompt = load_file(self._base_dir, self._spec.prompts.orchestrator)
        descriptions = "\n".join(
            f"- {c.node.id}: {c.node.description}" for c in candidates
        )
        system = f"{orchestrator_prompt}\n\nAvailable agents:\n{descriptions}"

        try:
            decision = await self._routing_chain.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=state.get("message", "")),
                ]
            )
            if isinstance(decision, _RouteDecision):
                for c in candidates:
                    if c.node.id == decision.next:
                        return node_id(c, self._node_path)
                logger.warning(
                    "Orchestrator=%s: LLM returned unknown agent '%s'; using first candidate",
                    self._node_path,
                    decision.next,
                )
        except Exception:
            logger.warning(
                "Orchestrator=%s: routing chain raised an error; using first candidate",
                self._node_path,
                exc_info=True,
            )

        return node_id(candidates[0], self._node_path)
