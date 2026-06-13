from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_engine.core.spec import AgentSpec, GraphNode, OrchestratorSpec, SystemSpec
from agent_engine.engine.engine import Engine
from agent_engine.engine.langgraph.filters import AccessFilter, RouteFilter
from agent_engine.engine.langgraph.helpers import (
    _RouteDecision,
    collect_mcp_servers,
    has_protected_nodes,
    make_orchestrator_node,
    node_id,
)
from agent_engine.engine.langgraph.nodes import AgentNode, OrchestratorRouter
from agent_engine.engine.types import RunResult
from agent_engine.loaders.resolver_loader import ResolverLoader
from agent_engine.loaders.tool_loader import ToolLoader
from agent_engine.models.factory import build_chat_model
from agent_engine.runtime.state import GraphState
from agent_engine.runtime.streaming import RunStreamEvent

logger = logging.getLogger(__name__)

ModelFactory = Callable[[str, str, float | None], BaseChatModel]


class LangGraphEngine(Engine):
    def __init__(
        self,
        base_dir: Path,
        *,
        model_factory: ModelFactory = build_chat_model,
    ) -> None:
        self._base_dir = base_dir
        self._model_factory = model_factory

        # set during build()
        self._app: CompiledStateGraph | None = None
        self._system_name = ""
        self._filters: list[RouteFilter] = []
        self._mcp_clients: dict[str, Any] = {}
        self._mcp_tools: dict[str, list[BaseTool]] = {}
        self._tool_loader: ToolLoader | None = None
        self._resolver_loader: ResolverLoader | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def build(self, spec: SystemSpec, filters: list[RouteFilter] | None = None) -> None:
        self._system_name = spec.meta.name

        # 1. filters — access control, feature flags, etc.
        self._filters = self._setup_filters(spec, filters)

        # 2. MCP — connect to servers, collect tools per server
        self._mcp_tools = await self._connect_mcps(spec)

        # 3. loaders — tools and resolvers from plugins/
        self._tool_loader = ToolLoader(self._base_dir)
        self._resolver_loader = ResolverLoader(self._base_dir)

        # 4. compile — build StateGraph from spec tree
        self._app = self._compile_graph(spec)

    async def close(self) -> None:
        for client in self._mcp_clients.values():
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                logger.warning("Error closing MCP client", exc_info=True)
        self._mcp_clients.clear()
        self._mcp_tools.clear()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, message: str) -> RunResult:
        assert self._app is not None, "call build() before run()"
        state: dict[str, Any] = {"message": message, "used_tools": []}
        result = await self._app.ainvoke(cast(Any, state))
        return RunResult(
            system_name=self._system_name,
            visited=result.get("visited", []),
            answer=result.get("answer", ""),
            used_tools=tuple(result.get("used_tools", [])),
        )

    async def stream(self, message: str) -> AsyncIterator[RunStreamEvent]:
        assert self._app is not None, "call build() before stream()"

        queue: asyncio.Queue[RunStreamEvent | BaseException | None] = asyncio.Queue()

        state: dict[str, Any] = {
            "message": message,
            "used_tools": [],
            "answer_stream": lambda c: queue.put_nowait(RunStreamEvent(type="answer_delta", content=c)),
            "route_stream": lambda r: queue.put_nowait(RunStreamEvent(type="route", route=r)),
        }

        async def run_graph() -> None:
            try:
                result = await self._app.ainvoke(cast(Any, state))  # type: ignore[union-attr]
                queue.put_nowait(RunStreamEvent(
                    type="final",
                    content=result.get("answer", ""),
                    route=tuple(result.get("visited", [])),
                    system_name=self._system_name,
                    used_tools=tuple(result.get("used_tools", [])),
                ))
            except Exception as exc:
                queue.put_nowait(exc)
            finally:
                queue.put_nowait(None)

        task = asyncio.create_task(run_graph())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise RuntimeError(str(item)) from item
                yield item
        finally:
            await task

    # ------------------------------------------------------------------
    # Build steps
    # ------------------------------------------------------------------

    def _setup_filters(
        self,
        spec: SystemSpec,
        extra: list[RouteFilter] | None,
    ) -> list[RouteFilter]:
        filters = list(extra or [])
        if has_protected_nodes(spec.graph):
            access_plugin = self._base_dir / "plugins" / "access.py"
            if access_plugin.is_file():
                filters.insert(0, AccessFilter(self._base_dir))
        return filters

    async def _connect_mcps(self, spec: SystemSpec) -> dict[str, list[BaseTool]]:
        """Open one MultiServerMCPClient per server. Return tools grouped by server id."""
        from langchain_mcp_adapters.client import MultiServerMCPClient

        mcp_tools: dict[str, list[BaseTool]] = {}
        for server_id, url in collect_mcp_servers(spec.graph).items():
            client = MultiServerMCPClient({server_id: {"url": url, "transport": "streamable_http"}})
            await client.__aenter__()
            self._mcp_clients[server_id] = client
            mcp_tools[server_id] = await client.get_tools()
            logger.info("MCP server=%s connected, tools=%d", server_id, len(mcp_tools[server_id]))
        return mcp_tools

    def _compile_graph(self, spec: SystemSpec) -> CompiledStateGraph:
        """Walk the spec tree and wire nodes + edges into a StateGraph."""
        builder = StateGraph(GraphState)
        self._wire_node(builder, spec.graph, parent_path=None)
        builder.add_edge(START, node_id(spec.graph, parent_path=None))
        return builder.compile()

    # ------------------------------------------------------------------
    # Graph wiring
    # ------------------------------------------------------------------

    def _wire_node(
        self,
        builder: StateGraph,
        node: GraphNode,
        parent_path: str | None,
    ) -> None:
        path = node_id(node, parent_path)

        if isinstance(node.node, OrchestratorSpec):
            builder.add_node(path, make_orchestrator_node(path))
        else:
            assert isinstance(node.node, AgentSpec)
            builder.add_node(path, self._build_agent_node(node.node, path))

        if node.children:
            router = self._build_router(node, path)
            routes = {node_id(c, path): node_id(c, path) for c in node.children}
            builder.add_conditional_edges(path, router, routes)
            for child in node.children:
                self._wire_node(builder, child, parent_path=path)
        else:
            builder.add_edge(path, END)

    def _build_router(self, node: GraphNode, node_path: str) -> OrchestratorRouter:
        assert isinstance(node.node, OrchestratorSpec)
        spec = node.node
        routing_chain: Any = None
        if spec.model.provider and spec.model.name:
            routing_chain = self._model_factory(
                spec.model.provider, spec.model.name, spec.model.temperature
            ).with_structured_output(_RouteDecision)
        return OrchestratorRouter(
            spec=spec,
            node_path=node_path,
            children=list(node.children),
            routing_chain=routing_chain,
            filters=self._filters,
            base_dir=self._base_dir,
        )

    def _build_agent_node(self, spec: AgentSpec, node_path: str) -> AgentNode:
        assert self._tool_loader is not None
        assert self._resolver_loader is not None
        tools, mcp_names = self._build_agent_tools(spec)
        model = self._model_factory(spec.model.provider, spec.model.name, spec.model.temperature)
        bound_model = model.bind_tools(tools) if tools else model
        return AgentNode(
            spec=spec,
            node_path=node_path,
            bound_model=bound_model,
            tool_map={t.name: t for t in tools},
            mcp_tool_names=mcp_names,
            resolver_loader=self._resolver_loader,
            base_dir=self._base_dir,
        )

    def _build_agent_tools(self, spec: AgentSpec) -> tuple[list[BaseTool], set[str]]:
        """Return all tools for an agent and the set of MCP-sourced tool names."""
        assert self._tool_loader is not None
        tools: list[BaseTool] = []
        mcp_names: set[str] = set()
        for t in spec.tools:
            fn = self._tool_loader.load(t.id)
            tools.append(StructuredTool.from_function(fn, description=t.description))
        for mcp in spec.mcps:
            server_tools = self._mcp_tools.get(mcp.id, [])
            tools.extend(server_tools)
            mcp_names.update(t.name for t in server_tools)
        return tools, mcp_names
