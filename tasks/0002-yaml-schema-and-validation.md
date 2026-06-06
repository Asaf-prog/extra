# Task 0002 — YAML Schema & Validation

## Goal

Load `agent.yml` into typed schema models and validate it thoroughly, producing
either a validated spec object or a structured set of errors. **No compilation
or runtime behavior.**

## Context

Per the architecture, YAML is validated before it is compiled or run. This task
implements only the **spec** and **validation** layers. The compiler (0003) will
consume the validated spec.

**Read first:** `AGENTS.md`, `.ai/skills/yaml-schema.md`, `docs/YAML_SPEC.md`,
`docs/adr/0002-yaml-is-compiled-not-executed-directly.md`.

## Scope

- Define typed schema models for the spec described in `docs/YAML_SPEC.md`
  (`version`, `app`, `runtime`, `definitions`, `hierarchy`, `security`,
  `observability`, `deployment`).
- Implement a loader (file/string → schema models).
- Implement semantic validation beyond schema shape.

## Files allowed to change

- `src/agentplatform/spec/**`
- `src/agentplatform/validation/**`
- `tests/spec/**`, `tests/validation/**`
- Test fixtures under `tests/fixtures/**` (sample valid/invalid YAML)

## Requirements

- Schema models are typed (e.g. pydantic) and reject unknown top-level keys.
- Loader parses YAML safely (no arbitrary object construction / no `eval`).
- Validation collects **all** errors (not just the first) with clear, located
  messages and enforces at least:
  - required top-level keys present;
  - every `hierarchy` agent id exists in `definitions.agents`;
  - exactly one root, matching `runtime.entrypoint`;
  - repeated references to the same agent definition each declare a unique `as`
    instance name; ambiguous repeated references are rejected (see
    [ADR 0006](../docs/adr/0006-reusable-agent-definitions-and-hierarchy-instances.md));
  - no cycles in the hierarchy;
  - referenced `provider`/`tools`/`mcp_server` ids exist in `definitions`;
  - routing metadata is declarative (no executable expressions);
  - no literal secrets (only references such as env var names).
- Provide a single public entry point, e.g. `validate_spec(data) -> Result`.

## Out of scope

- Compilation into the agent graph (task 0003).
- Runtime, prompts, sidecar, tools.
- Inventing YAML features not in `docs/YAML_SPEC.md` (extend the spec doc via the
  documentation skill if truly needed).

## Acceptance criteria

- [ ] Valid sample specs load and validate with no errors.
- [ ] Invalid samples produce structured, located error messages.
- [ ] Dangling references, multiple/missing roots, and cycles are caught.
- [ ] Unknown keys and literal secrets are rejected.
- [ ] Loader uses safe parsing; no code execution from YAML.
- [ ] Tests cover valid and each invalid case.
- [ ] `make check` passes.

## Commands to run before finishing

```bash
make check
```

## Expected final report

Use the AGENTS.md §9 format. Confirm validation runs before compilation, YAML is
treated as data, and no secrets are accepted. Recommend task 0003 next.
