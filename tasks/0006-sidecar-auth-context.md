# Task 0006 — Sidecar Auth & Context

## Goal

Implement the sidecar client and context resolver: call `POST /resolve-context`
at the configured phases, map the response into the `ExecutionContext`, and
enforce `allowed`/fail-closed behavior. Wire into the runtime's sidecar seam.

## Context

Client-specific auth/business logic lives in the sidecar, not the runtime. The
runtime only calls, maps, enforces, and traces. This task fills the sidecar seam
from 0004 and feeds resolved context to prompts (0005) and tools (0007).

**Read first:** `AGENTS.md`, `.ai/skills/sidecar-auth-context.md`,
`docs/SIDECAR_CONTEXT_AUTH.md`,
`docs/adr/0003-client-specific-logic-lives-in-sidecar.md`.

## Scope

- Define the contract request/response types from `docs/SIDECAR_CONTEXT_AUTH.md`.
- Implement an HTTP sidecar client and a context resolver that builds requests
  from agent-declared `required_context`/`required_permissions`.
- Map responses onto the `ExecutionContext`; enforce `allowed` and fail-closed.

## Files allowed to change

- `src/agentplatform/context/**`
- `src/agentplatform/runtime/**` (only to connect the sidecar seam)
- `tests/context/**`

## Requirements

- No client-specific auth/business logic in the runtime — only call/map/enforce/
  trace.
- Support `pre_routing` and `pre_agent` phases via the configured
  `security.sidecar.phases`.
- Build requests from declared requirements; map `identity`, `permissions`,
  `context`, `tool_policy` onto the `ExecutionContext`.
- `allowed: false` blocks execution and is traced with `reason`.
- Sidecar enabled but unreachable/erroring → **fail closed** (deny + trace).
- Redact secrets/tokens in traces.

## Out of scope

- Implementing a real client sidecar (use a fake in tests).
- Tool permission enforcement internals (task 0007) beyond mapping `tool_policy`
  into context.

## Acceptance criteria

- [ ] Contract types match `docs/SIDECAR_CONTEXT_AUTH.md`.
- [ ] Both phases supported and gated by config.
- [ ] Response correctly mapped onto `ExecutionContext`.
- [ ] `allowed: false` blocks + traces; failures fail closed.
- [ ] Secrets redacted in traces.
- [ ] No client-specific logic in the runtime.
- [ ] Tests use a fake sidecar covering allow/deny/error.
- [ ] `make check` passes.

## Commands to run before finishing

```bash
make check
```

## Expected final report

Use the AGENTS.md §9 format. Confirm ADR 0003 (no client logic in runtime,
fail-closed). Recommend task 0007 next.
