# Workflow: Add or Run Tests

Use this when adding tests for a change, fixing a bug, or working on the test
suite/quality gate (task `0012`).

## Roles & skills

- Role: [`../roles/test-engineer.md`](../roles/test-engineer.md).
- Primary skill: [`../skills/testing.md`](../skills/testing.md).
- Area skill for the code under test (runtime, prompts, sidecar, tools, yaml).

## Steps

1. **Read context.** `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`,
   `pyproject.toml` (`[tool.pytest.ini_options]`), and the area skill.
2. **Pick the category** — unit / integration / contract / golden / negative /
   security — for what you are testing.
3. **For a bug fix,** write a regression test that fails before the fix.
4. **Arrange with fixtures**; parametrize input variations. Mock external
   boundaries (LLM/MCP/DB/HTTP/sidecar) at the adapter seam.
5. **Assert behavior** through public interfaces, not private internals.
6. **Cover negatives and security:** validation errors, missing prompt
   variables, denied permissions, sidecar `allowed: false`, non-overridable
   injected params.
7. **Run** `make test`, then `make check`. Fix failures.

## Done when

- New/changed behavior has tests; bugs have a regression test.
- No real external systems are called; tests are deterministic.
- `make test` and `make check` pass (or you state why they can't run).
