# Task 0007 — MCP Tools & Permissions

## Goal

Implement the tool registry, MCP server integration, and the **tool permission
layer** that enforces permissions, injected parameters, and input validation at
call time. Wire into the runtime's tool seam.

## Context

Tools enforce permissions and injected parameters; prompt text is not a security
boundary. Connections are created once and shared. This task fills the tool seam
from 0004 and uses context/tool policy from 0006.

**Read first:** `AGENTS.md`, `.ai/skills/mcp-tools.md`, `docs/MCP_AND_TOOLS.md`,
`docs/SIDECAR_CONTEXT_AUTH.md` (permissions + tool policy).

## Scope

- Implement a tool registry built at startup from the compiled graph.
- Integrate MCP servers (connections created once, shared by the runtime).
- Implement enforcement at call time: permission check, injected/policy params,
  input-schema validation, and tracing.

## Files allowed to change

- `src/agentplatform/tools/**`
- `src/agentplatform/runtime/**` (only to connect the tool seam)
- `tests/tools/**`

## Requirements

- A tool call is **blocked + traced** unless the caller holds every
  `requires_permissions` and is not denied by sidecar `tool_policy`.
- `injected_params` and `tool_policy.inject` are **forced** into final arguments
  and **cannot** be overridden by model-proposed arguments.
- Arguments are validated against the tool's `input_schema` before invocation.
- MCP connections/clients are created once and reused; per-request data flows via
  `ExecutionContext`.
- No secrets in YAML; secrets redacted in traces.

## Out of scope

- API/CLI surfaces (0008, 0009).
- Deployment (0010), deep observability beyond basic tool-call tracing (0011).

## Acceptance criteria

- [ ] Calls without required permissions are blocked and traced.
- [ ] Injected/policy params cannot be overridden by the model.
- [ ] Inputs validated against the declared schema.
- [ ] MCP connections created once and shared.
- [ ] No secrets in YAML; secrets redacted in traces.
- [ ] Tests cover allow, deny, injection-override attempt, and schema violation.
- [ ] `make check` passes.

## Commands to run before finishing

```bash
make check
```

## Expected final report

Use the AGENTS.md §9 format. Confirm enforcement happens at the tool layer (not
the prompt) and injected values are non-overridable. Recommend task 0008 next.
