"""The compiled-graph models hold data and are immutable."""

from __future__ import annotations

import dataclasses

import pytest

from agentplatform.graph import AgentDeclaration, CompiledAgentGraph, GraphInstance


def _leaf_declaration() -> AgentDeclaration:
    return AgentDeclaration(
        node_id="super_agent",
        description="Handle supermarket orders.",
    )


def test_models_carry_their_data() -> None:
    declaration = _leaf_declaration()
    instance = GraphInstance(
        instance_id="main_router/super_agent",
        node_id="super_agent",
        parent_instance_id="main_router",
        path="main_router/super_agent",
        declaration=declaration,
        children=(),
    )
    graph = CompiledAgentGraph(
        system_name="Rami Levy AI System",
        root=instance,
        instances_by_id={instance.instance_id: instance},
        declarations_by_id={declaration.node_id: declaration},
    )

    assert graph.root.declaration is declaration
    assert graph.instances_by_id["main_router/super_agent"].node_id == "super_agent"


def test_instances_are_immutable() -> None:
    instance = GraphInstance(
        instance_id="i1",
        node_id="super_agent",
        parent_instance_id=None,
        path="super_agent",
        declaration=_leaf_declaration(),
        children=(),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        instance.node_id = "changed"  # type: ignore[misc]
