# Skill: Sidecar Auth & Context

## When to use this skill

Use this when working on the sidecar client, the `/resolve-context` contract,
mapping sidecar responses into `ExecutionContext`, or permission/tool-policy
enforcement driven by the sidecar. Primary task:
`tasks/0006-sidecar-auth-context.md`.

## Files to read first

- `AGENTS.md`
- `docs/SIDECAR_CONTEXT_AUTH.md`
- `docs/adr/0003-client-specific-logic-lives-in-sidecar.md`
- `docs/ARCHITECTURE.md` (sidecar + context resolver layers)

## Architecture rules

- The runtime contains **no** client-specific auth/business logic.
- The runtime only: calls the sidecar, maps the response into
  `ExecutionContext`, enforces permissions/tool policies, and traces decisions.
- Two phases share one contract: `pre_routing` and `pre_agent`.
- `allowed: false` blocks execution; sidecar failures **fail closed**.
- Secrets are redacted in traces.

## Implementation rules

- Implement the client in `src/agentplatform/context` against the contract types
  in `docs/SIDECAR_CONTEXT_AUTH.md`.
- Build the request from agent-declared `required_context` /
  `required_permissions`; do not invent client semantics.
- Map `identity`, `permissions`, `context`, `tool_policy` onto the
  `ExecutionContext`.
- Enforce `tool_policy.inject` so model output cannot override injected values.
- Make the sidecar client a shared collaborator on the long-lived engine; pass
  per-request data via `ExecutionContext`.

## Validation checklist

- [ ] No client-specific logic in the runtime.
- [ ] Request/response match the documented contract (or an ADR updates it).
- [ ] `allowed: false` blocks and traces with `reason`.
- [ ] Sidecar errors fail closed.
- [ ] Injected/policy values cannot be overridden.
- [ ] Secrets redacted in traces.
- [ ] Tests use a fake sidecar covering allow/deny/error.
- [ ] `make check` passes.

## Common mistakes to avoid

- Implementing auth/tenant/business rules inside the runtime.
- Failing open when the sidecar is unavailable.
- Trusting model-proposed values over injected policy values.
- Logging raw tokens/secrets in the trace.
