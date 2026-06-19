"""after_tool_call fires for local and MCP tool calls with correct attribution.

No real MCP server: a fake MCP tool is injected into the engine's tool set the
same way ``_connect_mcps`` would, and the agent's MCP server map is wired so the
hook receives provider="mcp" and the server_id.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, cast

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.tools import StructuredTool

from agent_engine.core.spec import (
    AgentSpec,
    BasePromptSet,
    GraphNode,
    HooksConfig,
    HookSpec,
    MCPSpec,
    ModelConfig,
    SystemMeta,
    SystemSpec,
    ToolSpec,
)
from agent_engine.engine.langgraph.engine import LangGraphEngine
from tests.runtime.hooks import fixtures

_FIX = "tests.runtime.hooks.fixtures"
_MODEL = ModelConfig(provider="fake", name="fake", temperature=None)


class FakeChatModel:
    def __init__(self, answer: str = "ok", tool_names: list[str] | None = None) -> None:
        self._answer = answer
        self._tool_names = tool_names or []

    def bind_tools(self, tools: list[Any]) -> FakeChatModel:
        return FakeChatModel(self._answer, [t.name for t in tools])

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        return self._respond(messages)

    async def astream(self, messages: list[Any]) -> AsyncIterator[AIMessage]:
        yield self._respond(messages)

    def _respond(self, messages: list[Any]) -> AIMessage:
        already = any(isinstance(m, ToolMessage) for m in messages)
        if self._tool_names and not already:
            return AIMessage(
                content="",
                tool_calls=[ToolCall(name=self._tool_names[0], args={"message": "x"}, id="c1")],
            )
        return AIMessage(content=self._answer)


@pytest.fixture
def model_factory() -> Callable[[str, str, float | None], BaseChatModel]:
    def factory(provider: str, name: str, temperature: float | None) -> BaseChatModel:
        return cast(BaseChatModel, FakeChatModel())

    return factory


@pytest.fixture(autouse=True)
def _clear_calls() -> None:
    fixtures.CALLS.clear()


def _write_tool(base_dir: Path, tool_id: str, *, fail: bool = False) -> None:
    body = (
        f"def {tool_id}(message: str) -> str:\n    raise RuntimeError('nope')\n"
        if fail
        else f"def {tool_id}(message: str) -> str:\n    return 'did: ' + message\n"
    )
    tools_dir = base_dir / "plugins" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / f"{tool_id}.py").write_text(body, encoding="utf-8")


def _agent(node_id: str, **kw: Any) -> GraphNode:
    return GraphNode(
        node=AgentSpec(
            id=node_id,
            name=node_id,
            description=f"{node_id} agent",
            model=_MODEL,
            prompts=BasePromptSet(),
            **kw,
        )
    )


def _system(graph: GraphNode, *hooks: HookSpec) -> SystemSpec:
    return SystemSpec(
        meta=SystemMeta(name="tool-hooks"),
        defaults=None,
        graph=graph,
        hooks=HooksConfig(hooks=hooks),
    )


async def test_after_tool_call_runs_for_local_tool(tmp_path: Path, model_factory: Any) -> None:
    _write_tool(tmp_path, "book_flight")
    spec = _system(
        _agent("flights", tools=(ToolSpec("book_flight", "book"),)),
        HookSpec("after_tool_call", f"{_FIX}:record_after_tool_call"),
    )
    async with LangGraphEngine(tmp_path, model_factory=model_factory) as engine:
        await engine.build(spec)
        await engine.run("book please")

    calls = [c[1] for c in fixtures.CALLS if c[0] == "after_tool_call"]
    assert len(calls) == 1
    assert calls[0].tool_name == "book_flight"
    assert calls[0].provider == "local"
    assert calls[0].server_id is None
    assert calls[0].status == "succeeded"
    assert calls[0].latency_ms is not None


async def test_after_tool_call_receives_failure_status(tmp_path: Path, model_factory: Any) -> None:
    _write_tool(tmp_path, "book_flight", fail=True)
    spec = _system(
        _agent("flights", tools=(ToolSpec("book_flight", "book"),)),
        HookSpec("after_tool_call", f"{_FIX}:record_after_tool_call"),
    )
    async with LangGraphEngine(tmp_path, model_factory=model_factory) as engine:
        await engine.build(spec)
        await engine.run("book please")

    call = next(c[1] for c in fixtures.CALLS if c[0] == "after_tool_call")
    assert call.status == "failed"
    assert call.error is not None


async def test_after_tool_call_receives_provider_and_server_id(
    tmp_path: Path, model_factory: Any
) -> None:
    spec = _system(
        _agent("research", mcps=(MCPSpec(id="wiki", url="https://wiki.test/mcp"),)),
        HookSpec("after_tool_call", f"{_FIX}:record_after_tool_call"),
    )

    def fake_mcp_tool(message: str) -> str:
        return "wiki says hi"

    mcp_tool = StructuredTool.from_function(fake_mcp_tool, name="wiki_search", description="search")

    async with LangGraphEngine(tmp_path, model_factory=model_factory) as engine:
        await engine.build(spec)
        # Inject a fake MCP tool for server "wiki" (as _connect_mcps would).
        engine._mcp_tools["wiki"] = [mcp_tool]
        # Recompile so the agent node picks up the injected MCP tool.
        engine._app = engine._compile_graph(spec)
        await engine.run("search please")

    call = next(c[1] for c in fixtures.CALLS if c[0] == "after_tool_call")
    assert call.tool_name == "wiki_search"
    assert call.provider == "mcp"
    assert call.server_id == "wiki"
