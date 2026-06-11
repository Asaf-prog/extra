"""Compile a validated spec into an immutable ``CompiledAgentGraph``.

Input is the *validated* ``AgentEngineSpec`` (from the spec layer), never raw
YAML (ADR 0002). The compiler does two jobs:

1. Build one resolved ``NodeDeclaration`` per orchestrator/agent — spec types
   are flattened into graph-native fields, references resolved, and the
   effective model computed from defaults + node override.
2. Expand the ``graph`` tree into ``GraphInstance`` occurrences, each with a
   stable ``instance_id`` and a pointer back to its shared declaration
   (ADR 0006).

Validation (task 0002) already guarantees the input is well-formed: exactly
one graph root, every graph id is declared, all references resolve, no cycles.
"""

from __future__ import annotations

from agentplatform.graph.models import (
    AgentDeclaration,
    CompiledAgentGraph,
    GraphInstance,
    NodeDeclaration,
    OrchestratorDeclaration,
    ResolvedMcp,
    ResolvedResolver,
    ResolvedTool,
)
from agentplatform.spec.models import AgentEngineSpec, AgentSpec, ModelSpec, OrchestratorSpec


def compile_spec(spec: AgentEngineSpec) -> CompiledAgentGraph:
    """Compile a validated spec into an immutable compiled graph."""
    default_model = spec.defaults.model if spec.defaults else None
    declarations = _build_declarations(spec, default_model)

    root_id, root_children = next(iter(spec.graph.items()))
    root = _expand_node(
        node_id=root_id,
        children=root_children,
        parent_instance_id=None,
        parent_path=None,
        declarations=declarations,
    )

    instances_by_id: dict[str, GraphInstance] = {}
    _index_instances(root, instances_by_id)

    return CompiledAgentGraph(
        system_name=spec.system.name,
        root=root,
        instances_by_id=instances_by_id,
        declarations_by_id=declarations,
    )


def _build_declarations(
    spec: AgentEngineSpec,
    default_model: ModelSpec | None,
) -> dict[str, NodeDeclaration]:
    declarations: dict[str, NodeDeclaration] = {}
    for node_id, o in spec.orchestrators.items():
        declarations[node_id] = _compile_orchestrator(node_id, o, default_model)
    for node_id, a in spec.agents.items():
        declarations[node_id] = _compile_agent(node_id, a, spec, default_model)
    return declarations


def _compile_orchestrator(
    node_id: str,
    spec: OrchestratorSpec,
    default_model: ModelSpec | None,
) -> OrchestratorDeclaration:
    provider, name, temperature = _resolve_model(spec.model, default_model)
    return OrchestratorDeclaration(
        node_id=node_id,
        description=spec.description,
        model_provider=provider,
        model_name=name,
        model_temperature=temperature,
        orchestrator_prompt=spec.prompts.orchestrator,
        system_prompt=spec.prompts.system,
        user_prompt=spec.prompts.user,
        resolvers=tuple(ResolvedResolver(id=r) for r in spec.resolvers),
        protected=spec.protected,
    )


def _compile_agent(
    node_id: str,
    spec: AgentSpec,
    engine_spec: AgentEngineSpec,
    default_model: ModelSpec | None,
) -> AgentDeclaration:
    provider, name, temperature = _resolve_model(spec.model, default_model)
    return AgentDeclaration(
        node_id=node_id,
        description=spec.description,
        model_provider=provider,
        model_name=name,
        model_temperature=temperature,
        system_prompt=spec.prompts.system if spec.prompts else None,
        user_prompt=spec.prompts.user if spec.prompts else None,
        resolvers=tuple(ResolvedResolver(id=r) for r in spec.resolvers),
        tools=tuple(
            ResolvedTool(id=ref, description=engine_spec.tools[ref].description)
            for ref in spec.tools
        ),
        mcps=tuple(
            ResolvedMcp(id=ref, url=engine_spec.mcps[ref].url)
            for ref in spec.mcps
        ),
        protected=spec.protected,
    )


def _resolve_model(
    node_model: ModelSpec | None,
    default_model: ModelSpec | None,
) -> tuple[str | None, str | None, float | None]:
    """Return (provider, name, temperature) from the effective model, or all None."""
    m = node_model or default_model
    if m is None:
        return None, None, None
    return m.provider, m.name, m.temperature


def _expand_node(
    *,
    node_id: str,
    children: object,
    parent_instance_id: str | None,
    parent_path: str | None,
    declarations: dict[str, NodeDeclaration],
) -> GraphInstance:
    """Recursively expand a spec graph node into a ``GraphInstance`` tree.

    Computes a stable ``instance_id`` path (e.g. ``main_router/super_agent``),
    looks up the pre-compiled declaration, and recurses into children.
    """
    path = f"{parent_path}/{node_id}" if parent_path else node_id
    child_map = children if isinstance(children, dict) else {}

    child_instances = tuple(
        _expand_node(
            node_id=child_id,
            children=grandchildren,
            parent_instance_id=path,
            parent_path=path,
            declarations=declarations,
        )
        for child_id, grandchildren in child_map.items()
    )

    return GraphInstance(
        instance_id=path,
        node_id=node_id,
        parent_instance_id=parent_instance_id,
        path=path,
        declaration=declarations[node_id],
        children=child_instances,
    )


def _index_instances(
    instance: GraphInstance,
    index: dict[str, GraphInstance],
) -> None:
    index[instance.instance_id] = instance
    for child in instance.children:
        _index_instances(child, index)
