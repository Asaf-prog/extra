# ADR 0004: Prompts are templates rendered per request

- **Status:** Accepted
- **Date:** Foundation phase
- **Related:** [PROMPT_RENDERING.md](../PROMPT_RENDERING.md),
  [RUNTIME_LIFECYCLE.md](../RUNTIME_LIFECYCLE.md)

## Context

Agents need prompts that incorporate request-specific data (identity, tenant,
time, retrieved values). We must decide whether prompts are static strings,
fully precomputed, or templates rendered at request time — and what may be
cached.

## Decision

Prompt files are **templates** containing placeholders. The system:

- **Caches the parsed template** (deterministic, reusable).
- **Renders per request** using values resolved from the `ExecutionContext`.
- **Never caches the rendered prompt globally**, because it contains
  request-/tenant-specific data.
- **Fails loudly** when a required variable is missing (no silent blanks).
- Treats templates as **data, not code** — no arbitrary execution inside a
  template.

## Consequences

**Positive**

- Prompts adapt to each request without rebuilding anything expensive.
- Parsed-template caching keeps rendering cheap.
- Strict missing-variable errors catch misconfiguration early.

**Negative / constraints**

- Rendering happens on the request path; it must stay lightweight.
- Contributors must not introduce a global cache of rendered prompts (data-leak
  risk).
- Security must not rely on prompt wording.

## Alternatives considered

- **Static prompts:** cannot carry per-request data. Rejected.
- **Globally cache rendered prompts:** leaks one request's/tenant's data into
  another. Rejected.
- **Executable logic inside templates:** turns prompts into code and a security
  risk. Rejected.

## Enforcement

- Template parse cache keyed by file path + version; no rendered-prompt cache.
- Strict rendering mode: undeclared/missing variables raise named errors.
- Security enforcement lives in the tool/data layer, not prompt text
  (see [ADR 0003](0003-client-specific-logic-lives-in-sidecar.md)).
