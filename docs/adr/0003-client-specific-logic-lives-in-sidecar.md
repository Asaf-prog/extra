# ADR 0003: Client-specific logic lives in the sidecar

- **Status:** Accepted
- **Date:** Foundation phase
- **Related:** [SIDECAR_CONTEXT_AUTH.md](../SIDECAR_CONTEXT_AUTH.md),
  [ARCHITECTURE.md](../ARCHITECTURE.md)

## Context

Every client authenticates differently, models tenants/customers differently,
and stores business data differently. The platform must serve all of them
without embedding any single client's auth or business rules into the generated
runtime.

## Decision

Client-specific authentication, authorization, identity/tenant/customer
resolution, third-party calls, database lookups, business context, and tool
input policies are handled by a **client-owned sidecar** that implements a
standard contract (`POST /resolve-context`).

The runtime is responsible only for: calling the sidecar at defined phases,
mapping the response into the `ExecutionContext`, using resolved context for
prompt rendering, enforcing permissions and tool input policies, and tracing the
decision. It contains **no** client-specific logic.

## Consequences

**Positive**

- The runtime stays generic and reusable across clients.
- Clients customize auth and business logic without forking or editing generated
  runtime code.
- A clear, testable contract boundary; the runtime can be tested against a fake
  sidecar.

**Negative / constraints**

- A network hop and its failure modes; the runtime **fails closed** if the
  sidecar is enabled but unavailable.
- The contract must be versioned and stable; changes require an ADR.

## Alternatives considered

- **Built-in auth/business modules in the runtime:** forces one company's model
  on everyone and bloats the runtime. Rejected.
- **Plugin code loaded into the runtime process:** couples client code to the
  runtime's language/lifecycle and weakens isolation. The sidecar (separate
  service, standard contract) is preferred; an in-process plugin variant may be
  revisited later but is not the default.

## Enforcement

- No client-specific auth/business code in any runtime module.
- The runtime depends only on the sidecar contract types.
- `allowed: false` blocks execution and is traced; sidecar failures fail closed.
