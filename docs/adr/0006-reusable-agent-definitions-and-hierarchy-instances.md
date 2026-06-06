# ADR 0006: Reusable agent definitions and hierarchy instances

## Status

Accepted

## Context

The YAML carries two distinct concepts that have so far been conflated:

- An **agent definition** — a reusable declaration under `definitions.agents`
  describing *what an agent is* (type, prompts, tools, provider, declared
  context/permission requirements).
- An **agent instance** — a specific *occurrence* of a definition inside the
  `hierarchy`, describing *where* the agent sits (its parent and path).

The same agent definition may legitimately appear **multiple times** under
different parents — for example, a `security_review_agent` reused under both an
`invoice_orchestrator` and a `payment_orchestrator`. This means the hierarchy is
not a simple tree of unique agents; it is a tree/DAG of **references to reusable
definitions**.

Without a clear separation, repeated references are ambiguous: the runtime cannot
tell two occurrences apart for routing, path-specific context, or tracing.

## Decision

Agent **definitions are declared once** under `definitions.agents`. They may be
**reused multiple times** in the `hierarchy`, and **each occurrence compiles into
a distinct `CompiledAgentInstance`** that points back to the shared
`AgentDefinition`.

- A hierarchy node references a definition by `agent` id and may declare `as`, an
  **instance name** for that occurrence.
- The compiler produces, for each occurrence, a `CompiledAgentInstance` with:
  `instance_id`, `agent_id` (the definition), `parent_instance_id`, and a
  fully-qualified `path`.
- **The runtime executes `CompiledAgentInstance` nodes, not definitions.** The
  instance points to its definition for configuration.
- **Trace events use `instance_id`** as the primary identity and **also include
  the original `agent_id`** (and `path`).

### Validation rules

1. Every `hierarchy.agent` must reference an existing `definitions.agents` entry.
2. If a definition appears more than once in the hierarchy, each occurrence must
   declare a unique `as` value.
3. `as` (instance) ids must be unique within the compiled graph (or at minimum
   unique within a parent scope, if scoped instance ids are adopted).
4. If `as` is omitted, the instance id may default to the agent id **only** when
   the agent appears exactly once.
5. The compiler must detect ambiguous repeated references (a reused definition
   without distinct `as`) and fail with a clear error.
6. Cycles are not allowed in the MVP unless explicitly supported later.
7. Trace events use `instance_id` and also include `agent_id`.
8. Runtime execution operates on instances, not only definitions.

## Consequences

- Agents are **reusable** across the hierarchy without duplicating their
  configuration.
- Tracing is **unambiguous**: each occurrence is a distinct `instance_id`, while
  `agent_id` still reveals which definition ran.
- Routing and context can be **path-specific** because each instance has its own
  `instance_id` and `path`.
- The model leaves room for optional **instance-level overrides** in the future
  (e.g. an occurrence tweaking a prompt value) without changing the definition.
- The compiler is responsible for expanding references into instances and for
  enforcing the validation rules above; the runtime never resolves this from raw
  YAML.

## Alternatives Considered

1. **Treat the hierarchy as a tree of unique agents (no reuse).** Rejected:
   forces duplicated definitions for common agents and loses a key feature.
2. **Reuse definitions but share a single node identity across occurrences.**
   Rejected: makes routing, path-specific context, and tracing ambiguous.
3. **Always require `as`, even for single occurrences.** Rejected as unnecessary
   ceremony; a unique single occurrence can safely default its instance id to the
   agent id (rule 4).
4. **Allow cycles/recursion in the MVP.** Rejected for now to keep compilation
   and execution bounded and predictable; may be revisited via a later ADR.

## Related

- [ADR 0001 — RuntimeEngine created once](0001-runtime-engine-created-once.md)
- [ADR 0002 — YAML is compiled, not executed directly](0002-yaml-is-compiled-not-executed-directly.md)
- Docs: [ARCHITECTURE.md](../ARCHITECTURE.md#agent-definitions-vs-agent-instances),
  [YAML_SPEC.md](../YAML_SPEC.md)

> This ADR records a **decision**. The `AgentDefinition` / `CompiledAgentInstance`
> models and their validation are **not implemented yet**; they are built by the
> compiler task (`tasks/0003-compiled-agent-graph.md`) and used by the runtime
> task (`tasks/0004-runtime-engine.md`).
