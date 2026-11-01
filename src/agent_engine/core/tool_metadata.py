"""Offline check that every tool parameter tells the LLM what it means.

A tool's parameters reach the model as its input schema. Parameter types come
from the signature; descriptions come from ``Annotated`` metadata, which the
engine's ``StructuredTool.from_function`` already copies into that schema:

    def get_customer(customer_code: Annotated[str, "The unique customer code."]) -> str:

A parameter without one leaves the model to guess what value to pass. This
module reports such parameters so ``agentctl validate`` can surface them.

This is the first step of issue #114. Missing descriptions are reported as
warnings, not errors: existing tools (including every shipped example) have
none yet, and failing validation would break them all at once.

Detection is purely static, like ``plugin_stubs``: tool files are parsed
(``ast``), never executed. Anything the scan cannot positively identify — a
missing or unparseable file, a function it cannot find — is skipped and left
to the existing plugin checks and runtime loaders to report.

Parameters LangChain fills in at runtime are left out of the schema sent to the
model, so they are not checked. Being static, the scan recognizes them by the
names they are written with (see ``_is_runtime_injected``).
"""

from __future__ import annotations

import ast
from pathlib import Path

from agent_engine.core.plugin_stubs import find_function
from agent_engine.core.spec import AgentSpec, GraphNode, SystemSpec


def scan_tool_param_descriptions(spec: SystemSpec, base_dir: Path) -> list[str]:
    """Return one warning per tool parameter with a missing or blank description."""
    warnings: list[str] = []
    seen: set[str] = set()
    for node in _walk(spec.graph):
        if not isinstance(node.node, AgentSpec):
            continue
        for tool in node.node.tools:
            if tool.id in seen:
                continue
            seen.add(tool.id)
            path = base_dir / "plugins" / "tools" / f"{tool.id}.py"
            warnings.extend(_check_tool(path, tool.id))
    return warnings


def _walk(node: GraphNode) -> list[GraphNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_walk(child))
    return nodes


def _check_tool(path: Path, tool_id: str) -> list[str]:
    if not path.is_file():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    fn = find_function(tree, tool_id, None)
    if fn is None:
        return []
    warnings: list[str] = []
    for arg in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs):
        if _is_runtime_injected(arg):
            continue
        description = _annotated_description(arg.annotation)
        if description is None:
            warnings.append(f'tool "{tool_id}": parameter "{arg.arg}" is missing a description')
        elif not description.strip():
            warnings.append(f'tool "{tool_id}": parameter "{arg.arg}" has an empty description')
    return warnings


# LangChain drops these parameter names from every tool schema (``FILTERED_ARGS``).
_RUNTIME_ARG_NAMES = frozenset({"callbacks", "run_manager"})


def _is_runtime_injected(arg: ast.arg) -> bool:
    """True for a parameter LangChain fills in itself and never shows the model.

    Mirrors ``langchain_core`` tool-schema filtering:

    - ``callbacks`` / ``run_manager``, by name;
    - ``config: RunnableConfig`` — only the bare type; ``RunnableConfig | None``
      is still shown to the model;
    - ``ToolRuntime`` or ``ToolRuntime[...]``;
    - ``Annotated[T, Injected...]``: ``InjectedToolArg`` and its subclasses
      (``InjectedToolCallId``, LangGraph's ``InjectedState`` / ``InjectedStore``),
      bare or called.
    """
    if arg.arg in _RUNTIME_ARG_NAMES:
        return True
    annotation = arg.annotation
    if annotation is None:
        return False
    if _type_name(annotation) in {"RunnableConfig", "ToolRuntime"}:
        return True
    if isinstance(annotation, ast.Subscript):
        if _type_name(annotation.value) == "ToolRuntime":
            return True
        if _is_annotated(annotation.value) and isinstance(annotation.slice, ast.Tuple):
            return any(_is_injected_marker(item) for item in annotation.slice.elts[1:])
    return False


def _is_injected_marker(node: ast.expr) -> bool:
    """``InjectedState``, ``InjectedState("messages")``, ``tools.InjectedToolArg()``…"""
    target = node.func if isinstance(node, ast.Call) else node
    name = _type_name(target)
    return name is not None and name.startswith("Injected")


def _type_name(node: ast.expr) -> str | None:
    """The bare name of ``X`` or ``module.X``; None for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _annotated_description(annotation: ast.expr | None) -> str | None:
    """The first string in ``Annotated[T, ...]`` metadata, or None if there is none."""
    if not isinstance(annotation, ast.Subscript) or not _is_annotated(annotation.value):
        return None
    if not isinstance(annotation.slice, ast.Tuple):
        return None
    for item in annotation.slice.elts[1:]:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            return item.value
    return None


def _is_annotated(node: ast.expr) -> bool:
    """``Annotated`` or ``<module>.Annotated`` (e.g. ``typing.Annotated``)."""
    if isinstance(node, ast.Name):
        return node.id == "Annotated"
    return isinstance(node, ast.Attribute) and node.attr == "Annotated"
