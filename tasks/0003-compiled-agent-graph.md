# Task 0003 — Compiled Agent Graph

## Goal

Compile a validated spec into an immutable, typed `CompiledAgentGraph`: resolve
references, expand the hierarchy, and link agents to prompts/tools/providers and
their declared context/permission requirements. **No runtime execution.**

## Context

The runtime (0004) operates only on compiled, typed models — never raw YAML.
This task builds the bridge from validated spec to that model.

**Read first:** `AGENTS.md`, `skills/runtime-engine-skill.md`,
`docs/ARCHITECTURE.md` (compiler + agent graph layers),
`docs/adr/0002-yaml-is-compiled-not-executed-directly.md`.

## Scope

- Define the `CompiledAgentGraph` and related typed models (agents, edges/routing
  relationships, prompt bindings, tool bindings, provider bindings, declared
  context/permission requirements).
- Implement the compiler: validated spec → `CompiledAgentGraph`.

## Files allowed to change

- `src/agentplatform/graph/**`
- `src/agentplatform/compiler/**`
- `tests/graph/**`, `tests/compiler/**`

## Requirements

- The compiler accepts only a **validated** spec (task 0002 output); it does not
  re-implement validation but may assert invariants.
- Resolve all id references into direct typed links.
- Expand `hierarchy` into a traversable tree/graph rooted at the entrypoint.
- The resulting graph is **immutable** (frozen models / read-only).
- Carry agent-declared `requires_context` and `requires_permissions` onto the
  compiled agent nodes for later enforcement.
- Provide a single public entry point, e.g.
  `compile_spec(validated_spec) -> CompiledAgentGraph`.

## Out of scope

- `RuntimeEngine` / `ExecutionContext` / execution (task 0004).
- Prompt rendering, sidecar calls, tool invocation.
- Reading raw YAML (only the validated spec is the input).

## Acceptance criteria

- [ ] `CompiledAgentGraph` is typed and immutable.
- [ ] All id references are resolved into direct links.
- [ ] The hierarchy is expanded and traversable from the entrypoint.
- [ ] Declared context/permission requirements are attached to agent nodes.
- [ ] The compiler input is the validated spec, not raw YAML.
- [ ] Tests cover compilation of a representative spec and graph traversal.
- [ ] `make check` passes.

## Commands to run before finishing

```bash
make check
```

## Expected final report

Use the AGENTS.md §9 format. Confirm the graph is immutable, references are
resolved, and the runtime will consume only compiled models. Recommend task 0004
next.
