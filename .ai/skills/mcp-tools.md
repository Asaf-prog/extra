---
name: mcp-tools
description: Working on tool definitions, MCP server connections, tool invocation, or the tool permission layer. Primary task is tasks/0007-mcp-tools-and-permissions.md.
---

# Skill: MCP & Tools

## When to use this skill

Use this when working on tool definitions, MCP server connections, tool
invocation, or the tool permission layer. Primary task:
`tasks/0007-mcp-tools-and-permissions.md`.

## Files to read first

- `AGENTS.md`
- `docs/MCP_AND_TOOLS.md`
- `docs/SIDECAR_CONTEXT_AUTH.md` (permissions + tool policy)
- `docs/RUNTIME_LIFECYCLE.md` (connection lifetime)

## Architecture rules

- Tools enforce permissions and injected parameters at call time.
- Injected/policy parameters cannot be overridden by model output.
- Tool inputs are validated against the declared schema.
- MCP connections are created once and shared; never per request.
- Prompt text is not a security boundary — this layer is.
- Secrets never live in YAML; they are redacted in traces.

## Implementation rules

- Implement tool registry, MCP integration, and enforcement in
  `src/agentplatform/tools`.
- At call time: check `requires_permissions` against `ExecutionContext`
  permissions and sidecar `tool_policy`; block + trace on failure.
- Force `injected_params` and `tool_policy.inject` into the final arguments.
- Validate arguments against `input_schema` before invoking.
- Hold MCP clients on the long-lived runtime; pass per-request data via context.

## Validation checklist

- [ ] Calls blocked without required permissions; blocks are traced.
- [ ] Injected/policy params cannot be overridden by the model.
- [ ] Inputs validated against the tool schema.
- [ ] MCP connections created once and reused.
- [ ] No secrets in YAML; secrets redacted in traces.
- [ ] Tests cover allow, deny, injection, and schema-violation cases.
- [ ] `make check` passes.

## Common mistakes to avoid

- Letting the model's arguments override injected/tenant values.
- Recreating MCP connections per request.
- Skipping input validation.
- Relying on the prompt to restrict tool usage.
