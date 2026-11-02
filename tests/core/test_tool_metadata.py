"""Tests for the offline check that tool parameters carry descriptions (#114).

The scan is static (AST) — tool files are parsed, never executed — so these
tests write real tool files into tmp_path and assert on the warnings returned.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from agent_engine.core.spec import (
    AgentSpec,
    BasePromptSet,
    GraphNode,
    ModelConfig,
    OrchestratorPromptSet,
    OrchestratorSpec,
    SystemMeta,
    SystemSpec,
    ToolSpec,
)
from agent_engine.core.tool_metadata import scan_tool_param_descriptions

_MODEL = ModelConfig(provider="fake", name="fake", temperature=None)


def agent(node_id: str, *tool_ids: str) -> GraphNode:
    spec = AgentSpec(
        id=node_id,
        name=node_id,
        description=f"{node_id} agent",
        model=_MODEL,
        prompts=BasePromptSet(),
        tools=tuple(ToolSpec(t, t) for t in tool_ids),
    )
    return GraphNode(node=spec)


def orchestrator(node_id: str, children: list[GraphNode]) -> GraphNode:
    spec = OrchestratorSpec(
        id=node_id,
        name=node_id,
        description=f"{node_id} orchestrator",
        model=_MODEL,
        prompts=OrchestratorPromptSet(),
    )
    return GraphNode(node=spec, children=tuple(children))


def system(graph: GraphNode) -> SystemSpec:
    return SystemSpec(meta=SystemMeta(name="test-system"), defaults=None, graph=graph)


def write_tool(base: Path, tool_id: str, source: str) -> None:
    path = base / "plugins" / "tools" / f"{tool_id}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(source), encoding="utf-8")


def scan_one(tmp_path: Path, source: str) -> list[str]:
    write_tool(tmp_path, "get_customer", source)
    return scan_tool_param_descriptions(system(agent("a", "get_customer")), tmp_path)


def test_fully_described_tool_has_no_warnings(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        from typing import Annotated

        def get_customer(
            customer_code: Annotated[str, "The unique customer code."],
            include_inactive: Annotated[bool, "Whether to include inactive customers."] = False,
        ) -> str:
            return customer_code
        """,
    )

    assert warnings == []


def test_plain_parameter_is_reported_missing(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        "def get_customer(customer_code: str) -> str:\n    return customer_code\n",
    )

    assert warnings == ['tool "get_customer": parameter "customer_code" is missing a description']


def test_unannotated_parameter_is_reported_missing(tmp_path: Path) -> None:
    warnings = scan_one(tmp_path, "def get_customer(customer_code):\n    return customer_code\n")

    assert warnings == ['tool "get_customer": parameter "customer_code" is missing a description']


def test_blank_and_whitespace_descriptions_are_reported_empty(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        from typing import Annotated

        def get_customer(code: Annotated[str, ""], region: Annotated[str, "   "]) -> str:
            return code
        """,
    )

    assert warnings == [
        'tool "get_customer": parameter "code" has an empty description',
        'tool "get_customer": parameter "region" has an empty description',
    ]


def test_typing_annotated_attribute_form_is_accepted(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        import typing

        def get_customer(customer_code: typing.Annotated[str, "The customer code."]) -> str:
            return customer_code
        """,
    )

    assert warnings == []


def test_annotated_without_string_metadata_is_reported_missing(tmp_path: Path) -> None:
    """Only string metadata counts as a description for now; ``Field(...)`` does not."""
    warnings = scan_one(
        tmp_path,
        """\
        from typing import Annotated
        from pydantic import Field

        def get_customer(customer_code: Annotated[str, Field(min_length=1)]) -> str:
            return customer_code
        """,
    )

    assert warnings == ['tool "get_customer": parameter "customer_code" is missing a description']


def test_every_bad_parameter_is_reported_including_keyword_only(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        from typing import Annotated

        def get_customer(
            code: str, /, region: Annotated[str, "Sales region."], limit: int, *, verbose: bool
        ) -> str:
            return code
        """,
    )

    assert warnings == [
        'tool "get_customer": parameter "code" is missing a description',
        'tool "get_customer": parameter "limit" is missing a description',
        'tool "get_customer": parameter "verbose" is missing a description',
    ]


def test_star_args_and_kwargs_are_ignored(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        "def get_customer(*args, **kwargs) -> str:\n    return ''\n",
    )

    assert warnings == []


# -- runtime-injected parameters: LangChain fills these in; the model never sees them --


def test_runnable_config_parameter_is_not_reported(tmp_path: Path) -> None:
    """The case from the #156 review: the model's schema only exposes ``query``."""
    warnings = scan_one(
        tmp_path,
        """\
        from typing import Annotated
        from langchain_core.runnables import RunnableConfig

        def get_customer(query: Annotated[str, "What to look up."], config: RunnableConfig) -> str:
            return query
        """,
    )

    assert warnings == []


def test_optional_runnable_config_is_still_reported(tmp_path: Path) -> None:
    """LangChain only hides a bare ``RunnableConfig``; an optional one reaches the model."""
    warnings = scan_one(
        tmp_path,
        """\
        from langchain_core.runnables import RunnableConfig

        def get_customer(config: RunnableConfig | None = None) -> str:
            return ""
        """,
    )

    assert warnings == ['tool "get_customer": parameter "config" is missing a description']


def test_callback_parameters_are_not_reported(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        "def get_customer(callbacks=None, run_manager=None) -> str:\n    return ''\n",
    )

    assert warnings == []


def test_tool_runtime_is_not_reported(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        from langchain.tools import ToolRuntime

        def get_customer(runtime: ToolRuntime, other: ToolRuntime[dict, dict]) -> str:
            return ""
        """,
    )

    assert warnings == []


def test_injected_annotations_are_not_reported(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        from typing import Annotated
        from langchain_core import tools
        from langchain_core.tools import InjectedToolArg, InjectedToolCallId
        from langgraph.prebuilt import InjectedState, InjectedStore

        def get_customer(
            call_id: Annotated[str, InjectedToolCallId],
            arg: Annotated[str, InjectedToolArg()],
            qualified: Annotated[str, tools.InjectedToolArg],
            state: Annotated[dict, InjectedState],
            messages: Annotated[list, InjectedState("messages")],
            store: Annotated[object, InjectedStore()],
        ) -> str:
            return ""
        """,
    )

    assert warnings == []


def test_injected_parameters_do_not_hide_undescribed_model_parameters(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        """\
        from langchain_core.runnables import RunnableConfig

        def get_customer(query: str, config: RunnableConfig) -> str:
            return query
        """,
    )

    assert warnings == ['tool "get_customer": parameter "query" is missing a description']


def test_async_tool_is_scanned(tmp_path: Path) -> None:
    warnings = scan_one(
        tmp_path,
        "async def get_customer(customer_code: str) -> str:\n    return customer_code\n",
    )

    assert warnings == ['tool "get_customer": parameter "customer_code" is missing a description']


def test_tool_shared_by_two_agents_is_reported_once(tmp_path: Path) -> None:
    write_tool(tmp_path, "lookup", "def lookup(query: str) -> str:\n    return query\n")
    spec = system(orchestrator("root", [agent("a", "lookup"), agent("b", "lookup")]))

    warnings = scan_tool_param_descriptions(spec, tmp_path)

    assert warnings == ['tool "lookup": parameter "query" is missing a description']


def test_unscannable_tools_are_skipped_without_crashing(tmp_path: Path) -> None:
    """Missing files, syntax errors and missing functions are reported elsewhere."""
    write_tool(tmp_path, "broken", "def broken(:\n")
    write_tool(tmp_path, "renamed", "def something_else(query: str) -> str:\n    return query\n")
    spec = system(orchestrator("root", [agent("a", "absent", "broken", "renamed")]))

    assert scan_tool_param_descriptions(spec, tmp_path) == []
