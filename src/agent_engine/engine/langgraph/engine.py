from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from agent_engine.core.spec import AgentSpec, GraphNode, OrchestratorSpec, SystemSpec
from agent_engine.engine.engine import Engine
from agent_engine.engine.langgraph.filters import AccessFilter, RouteFilter
from agent_engine.engine.langgraph.helpers import (
    _RouteDecision,
    as_text,
    collect_mcp_servers,
    emit_route,
    has_protected_nodes,
    invoke_model,
    load_file,
    make_orchestrator_node,
    node_id,
    render_prompt,
)
from agent_engine.engine.types import RunResult, ToolUsageRecord
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
        loop = asyncio.get_event_loop()

        def put(item: RunStreamEvent) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, item)

        state: dict[str, Any] = {
            "message": message,
            "used_tools": [],
            "answer_stream": lambda c: put(RunStreamEvent(type="answer_delta", content=c)),
            "route_stream": lambda r: put(RunStreamEvent(type="route", route=r)),
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
            builder.add_node(path, self._make_agent_node(node.node, path))

        if node.children:
            routes = {node_id(c, path): node_id(c, path) for c in node.children}
            builder.add_conditional_edges(path, self._make_router(node, path), routes)
            for child in node.children:
                self._wire_node(builder, child, parent_path=path)
        else:
            builder.add_edge(path, END)

    def _make_router(self, node: GraphNode, node_path: str) -> Callable[[GraphState], str]:
        assert isinstance(node.node, OrchestratorSpec)
        spec = node.node
        children = list(node.children)
        first_child = node_id(children[0], node_path)

        routing_chain = None
        if spec.model.provider and spec.model.name:
            routing_chain = self._model_factory(
                spec.model.provider, spec.model.name, spec.model.temperature
            ).with_structured_output(_RouteDecision)

        def route(state: GraphState) -> str:
            ctx = state.get("run_context", {})
            candidates = list(children)
            for f in self._filters:
                candidates = f.filter(ctx, candidates)
            if not candidates:
                return first_child
            if routing_chain is not None:
                prompt = load_file(self._base_dir, spec.prompts.orchestrator)
                descriptions = "\n".join(f"- {c.node.id}: {c.node.description}" for c in candidates)
                system = f"{prompt}\n\nAvailable agents:\n{descriptions}"
                try:
                    decision = routing_chain.invoke(
                        [SystemMessage(content=system), HumanMessage(content=state.get("message", ""))]
                    )
                    if isinstance(decision, _RouteDecision):
                        for c in candidates:
                            if c.node.id == decision.next:
                                return node_id(c, node_path)
                except Exception:
                    logger.warning("Orchestrator=%s routing failed; using first candidate", node_path)
            return node_id(candidates[0], node_path)

        return route

    def _make_agent_node(
        self,
        spec: AgentSpec,
        node_path: str,
    ) -> Callable[[GraphState], dict[str, object]]:
        assert self._tool_loader is not None
        assert self._resolver_loader is not None

        tools = self._build_agent_tools(spec)
        model = self._model_factory(spec.model.provider, spec.model.name, spec.model.temperature)
        bound_model = model.bind_tools(tools) if tools else model
        tool_map = {t.name: t for t in tools}
        resolver_loader = self._resolver_loader

        def node(state: GraphState) -> dict[str, object]:
            ctx: dict[str, Any] = {}
            for r in spec.resolvers:
                ctx[r.id] = str(resolver_loader.load(spec.id, r.id)(ctx))

            system_prompt = render_prompt(
                load_file(self._base_dir, spec.prompts.system) or spec.description,
                ctx,
            )
            messages: list[Any] = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state.get("message", "")),
            ]

            route = (*state.get("visited", []), node_path)
            emit_route(state, route)

            used_tools: list[ToolUsageRecord] = list(state.get("used_tools", []))
            response = cast(Any, invoke_model(bound_model, messages, state))

            while getattr(response, "tool_calls", None):
                messages.append(response)
                for tc in response.tool_calls:
                    tool = tool_map[tc["name"]]
                    try:
                        result = tool.invoke(tc["args"])
                        used_tools.append(ToolUsageRecord(
                            name=tc["name"], provider="local",
                            status="succeeded", agent_id=spec.id,
                        ))
                        content = str(result)
                    except Exception as exc:
                        used_tools.append(ToolUsageRecord(
                            name=tc["name"], provider="local",
                            status="failed", agent_id=spec.id, error=str(exc)[:200],
                        ))
                        content = f"Tool error: {exc}"
                    messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))
                response = cast(Any, invoke_model(bound_model, messages, state))

            return {
                "visited": list(route),
                "answer": as_text(response.content),
                "used_tools": used_tools,
            }

        return node

    def _build_agent_tools(self, spec: AgentSpec) -> list[BaseTool]:
        assert self._tool_loader is not None
        tools: list[BaseTool] = []
        for t in spec.tools:
            fn = self._tool_loader.load(t.id)
            tools.append(StructuredTool.from_function(fn, description=t.description))
        for mcp in spec.mcps:
            tools.extend(self._mcp_tools.get(mcp.id, []))
        return tools
