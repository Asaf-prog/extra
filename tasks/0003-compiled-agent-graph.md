# Task 0003 — Compiled Agent Graph

## Goal

Compile a validated spec into an immutable, typed `CompiledAgentGraph`: resolve
references, expand the hierarchy, and link agents to prompts/tools/providers and
their declared context/permission requirements. **No runtime execution.**

## Context

The runtime (0004) operates only on compiled, typed models — never raw YAML.
This task builds the bridge from validated spec to that model.

**Read first:** `AGENTS.md`, `.ai/skills/runtime-engine.md`,
`docs/ARCHITECTURE.md` (compiler + agent graph layers),
`docs/adr/0002-yaml-is-compiled-not-executed-directly.md`.

## Scope

- Define the `CompiledAgentGraph` and related typed models. **Distinguish
  `AgentDefinition` (reusable, from `definitions.agents`) from
  `CompiledAgentInstance` (a hierarchy occurrence)**, plus edges/routing
  relationships, prompt bindings, tool bindings, provider bindings, and declared
  context/permission requirements.
- Implement the compiler: validated spec → `CompiledAgentGraph`, expanding each
  `hierarchy` reference into a distinct `CompiledAgentInstance`.

## Files allowed to change

- `src/agentplatform/graph/**`
- `src/agentplatform/compiler/**`
- `tests/graph/**`, `tests/compiler/**`

## Requirements

- The compiler accepts only a **validated** spec (task 0002 output); it does not
  re-implement validation but may assert invariants.
- Resolve all id references into direct typed links.
- Expand `hierarchy` into a traversable tree/graph of `CompiledAgentInstance`
  nodes rooted at the entrypoint; **the same `AgentDefinition` may back multiple
  instances** (reusable agents). Each instance has `instance_id`, `agent_id`,
  `parent_instance_id`, and a fully-qualified `path`.
- Enforce instance rules (per [ADR 0006](../docs/adr/0006-reusable-agent-definitions-and-hierarchy-instances.md)):
  unique `as` for repeated references; default instance id to the agent id only
  when it appears once; reject ambiguous repeated references; no cycles.
- The resulting graph is **immutable** (frozen models / read-only).
- Carry agent-declared `requires_context` and `requires_permissions` onto the
  definition (and available via each instance) for later enforcement.
- Provide a single public entry point, e.g.
  `compile_spec(validated_spec) -> CompiledAgentGraph`.

## Out of scope

- `RuntimeEngine` / `ExecutionContext` / execution (task 0004).
- Prompt rendering, sidecar calls, tool invocation.
- Reading raw YAML (only the validated spec is the input).

## Acceptance criteria

- [ ] `CompiledAgentGraph` is typed and immutable.
- [ ] `AgentDefinition` and `CompiledAgentInstance` are distinct; instances carry
      `instance_id`, `agent_id`, `parent_instance_id`, and `path`.
- [ ] A reused definition produces multiple distinct instances; ambiguous
      repeated references (missing/duplicate `as`) are rejected.
- [ ] All id references are resolved into direct links.
- [ ] The hierarchy is expanded into traversable instances from the entrypoint.
- [ ] Declared context/permission requirements are reachable from each instance.
- [ ] The compiler input is the validated spec, not raw YAML.
- [ ] Tests cover compilation of a representative spec, a **reused agent**, and
      graph traversal.
- [ ] `make check` passes.

## Commands to run before finishing

```bash
make check
```

## Expected final report

Use the AGENTS.md §9 format. Confirm the graph is immutable, references are
resolved, and the runtime will consume only compiled models. Recommend task 0004
next.
