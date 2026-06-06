# Workflow: Implement a Feature Task

Use this to implement one numbered task from [`../../tasks/`](../../tasks/).

> Foundation-phase reminder: do not implement product features ahead of the
> task sequence. Follow the tasks in order.

## Roles & skills

- Primary role: [`../roles/architect.md`](../roles/architect.md) (for design),
  then implement directly.
- Always-on skill: [`../skills/project-architecture.md`](../skills/project-architecture.md).
- Engineering skill: [`../skills/senior-python-engineering.md`](../skills/senior-python-engineering.md).
- Area skill: pick the one for the layer you touch (yaml-schema, runtime-engine,
  prompt-rendering, sidecar-auth-context, mcp-tools).
- Tests skill: [`../skills/testing.md`](../skills/testing.md).

## Steps

1. **Read context.** `AGENTS.md`, `.ai/README.md`, the task file in `tasks/`,
   and the docs/ADRs the task references.
2. **Load skills.** Read `project-architecture` + the area skill + any practice
   skill the task names in its "Read first" line.
3. **Confirm scope.** Implement only what the task defines. Discovered work →
   propose a new task, don't expand scope.
4. **Design.** Sketch the public interface and where code lives
   (`src/agentplatform/<layer>`). If it touches a contract, check whether an ADR
   is required (`.ai/skills/architecture-review.md`).
5. **Implement** per `senior-python-engineering` — small, typed, testable
   modules; side effects at the edges.
6. **Test** per `testing` — behavior-focused, external systems mocked, negatives
   and security covered.
7. **Validate.** Run `make check` (format, lint, typecheck, test). Fix failures.
8. **Self-review** with [`code-review.md`](code-review.md) before declaring done.
9. **Report.** Summarize the modules added/changed, the layer each belongs to,
   tests added, and the `make check` result.

## Done when

- The task's acceptance criteria are met and in scope.
- New behavior is tested; `make check` passes.
- Docs/ADRs updated in the same change if a contract or behavior changed
  (see [`documentation-update.md`](documentation-update.md)).
