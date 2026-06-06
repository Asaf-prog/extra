---
name: yaml-schema
description: Loading agent.yml, defining schema models, and validating the specification (definitions, hierarchy, security). Primary task is tasks/0002-yaml-schema-and-validation.md.
---

# Skill: YAML Schema & Validation

## When to use this skill

Use this when working on loading `agent.yml`, defining schema models, or
validating the specification (definitions, hierarchy, security, etc.). Primary
task: `tasks/0002-yaml-schema-and-validation.md`.

## Files to read first

- `AGENTS.md`
- `docs/YAML_SPEC.md`
- `docs/adr/0002-yaml-is-compiled-not-executed-directly.md`
- `docs/ARCHITECTURE.md` (spec + validation layers)

## Architecture rules

- YAML is declarative; it is data, never code. Never `eval`/execute spec values.
- The spec has two halves: `definitions` (what exists) and `hierarchy` (how it
  is arranged). Keep them distinct.
- Validation must happen **before** compilation. Downstream layers trust only
  validated specs.
- Secrets are never values in YAML — only references (e.g. env var names).

## Implementation rules

- Define typed schema models (e.g. pydantic/dataclasses) in `src/agentplatform/spec`.
- Validation belongs in `src/agentplatform/validation` and should report
  **all** errors with clear, located messages (not just the first).
- Enforce: required top-level keys; ids referenced in `hierarchy` exist in
  `definitions.agents`; single root matching `runtime.entrypoint`; no cycles;
  referenced providers/tools/MCP servers exist; routing metadata is declarative.
- Keep schema and validation separate from the compiler (that is task 0003).
- Do not implement runtime behavior here.

## Validation checklist

- [ ] Schema models cover the keys in `docs/YAML_SPEC.md`.
- [ ] Validator catches missing keys, dangling references, multiple/missing
      roots, and cycles.
- [ ] Errors are structured and human-readable.
- [ ] No secrets accepted as literal values (only references).
- [ ] Tests cover valid and invalid specs.
- [ ] `make check` passes.

## Common mistakes to avoid

- Mixing validation with compilation or runtime logic.
- Failing fast on the first error instead of collecting all errors.
- Allowing executable expressions in routing/condition fields.
- Accepting hardcoded secrets in the spec.
- Letting unknown/typo'd keys pass silently.
