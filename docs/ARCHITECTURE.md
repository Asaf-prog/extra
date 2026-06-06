# Architecture

This document describes the high-level design of the Declarative Agent Platform.
It is the conceptual blueprint; implementation is built task-by-task (see
`tasks/`). Nothing here is working software yet.

---

## Design goals

- A YAML specification fully describes an agent system.
- The specification is **validated** and **compiled** before it ever runs.
- A **single long-lived runtime** executes many requests against an immutable
  compiled graph.
- **Client-specific concerns** (auth, business context) are pushed to a sidecar.
- Every request is **traceable**.

---

## Layers

The system is organized as a one-directional pipeline of layers. Each layer has
a single responsibility and a typed boundary with its neighbors.

### 1. Spec layer
Loads `agent.yml` from disk into in-memory data, then into raw schema models.
It does **not** execute anything. Output: parsed spec models.
→ See [YAML_SPEC.md](YAML_SPEC.md).

### 2. Validation layer
Validates the spec: schema correctness, required fields, referential integrity
(every referenced agent/tool/provider exists), hierarchy well-formedness (no
cycles, single root), and security/context declarations. Validation **must**
happen before compilation. Output: a validated spec or a structured error set.

### 3. Compiler layer
Transforms the validated spec into typed, immutable internal models. This is
where declarative YAML becomes a real object graph. The compiler resolves
references, expands the hierarchy, and links prompts/tools/providers to agents.
Output: a `CompiledAgentGraph`. The runtime never sees raw YAML.
→ See [ADR 0002](adr/0002-yaml-is-compiled-not-executed-directly.md).

### 4. Agent graph layer
The `CompiledAgentGraph` is an immutable, validated object graph: agents,
their parent/child routing relationships, attached prompts, tool bindings,
provider bindings, and declared context/permission requirements. Built once;
shared read-only by all requests.

### 5. Runtime layer
The `RuntimeEngine` is constructed **once at application startup** from the
compiled graph. It is long-lived and stateless with respect to individual
requests. For each request it creates a fresh `ExecutionContext`, routes through
the hierarchy, and executes the selected agent(s) recursively.
→ See [RUNTIME_LIFECYCLE.md](RUNTIME_LIFECYCLE.md) and
[ADR 0001](adr/0001-runtime-engine-created-once.md).

### 6. Prompt rendering layer
Loads prompt **templates** (cacheable) and renders them **per request** using
values from the `ExecutionContext`. Missing required variables fail loudly.
Rendered prompts are never cached globally.
→ See [PROMPT_RENDERING.md](PROMPT_RENDERING.md) and
[ADR 0004](adr/0004-prompts-are-templates-rendered-per-request.md).

### 7. Context resolver layer
Assembles the values used for prompt rendering and tool calls. Context can come
from the request, identity, the sidecar, system time, memory, tools, databases,
APIs, or plugins. Agents **declare** required context; the resolver gathers it.

### 8. Sidecar auth/context layer
Calls the client-owned sidecar over a standard contract to resolve identity,
tenant, permissions, dynamic context, and tool input policies. The runtime maps
the response into the `ExecutionContext`. No client-specific logic lives in the
runtime itself.
→ See [SIDECAR_CONTEXT_AUTH.md](SIDECAR_CONTEXT_AUTH.md) and
[ADR 0003](adr/0003-client-specific-logic-lives-in-sidecar.md).

### 9. MCP/tool layer
Connects agents to MCP servers and tools declared in the spec. Manages tool
discovery, parameter binding, and invocation.
→ See [MCP_AND_TOOLS.md](MCP_AND_TOOLS.md).

### 10. Tool permission layer
Enforces, at call time, that the resolved identity/permissions allow a tool
call, that injected parameters are applied, and that tool input policies from
the sidecar are honored. **Prompt text is not a security boundary** — this layer
is. Denied calls are blocked and traced.

### 11. Observability layer
Produces a structured trace for every request: routing decisions, sidecar
calls, resolved context (redacted), prompt rendering, tool calls, and the final
response. Used for debugging and auditing.

### 12. API layer
Exposes the runtime over HTTP. Constructs the `RuntimeEngine` once at startup
and creates an `ExecutionContext` per request. Never builds a runtime per
request.

### 13. CLI layer
Command-line entry points for validating, compiling, inspecting, and locally
running an `agent.yml`.

### 14. Deployment layer
Packaging and deployment concerns (e.g. Docker). Out of scope until late tasks.

---

## Request flow

```
Incoming request
  → Security/Context Gate          (reject obviously invalid/unauthenticated calls)
  → optional pre-routing sidecar call   (resolve identity/context needed for routing)
  → RuntimeEngine
  → route through hierarchy        (choose the agent path from the root entrypoint)
  → optional pre-agent sidecar call     (resolve context/permissions for the chosen agent)
  → resolve context                (assemble values from all declared sources)
  → render prompts                 (templates → text, per request)
  → execute selected agent         (recursively, including children as needed)
  → enforce tool permissions       (block disallowed tool calls; apply policies)
  → return response and trace
```

### Why two sidecar phases?

Some context is needed **before** the runtime can route (e.g. tenant/role-based
routing). Other context is only needed **once an agent is chosen** (e.g.
agent-specific permissions or data lookups). Both phases use the same contract;
either may be skipped if not required. See `phase` in
[SIDECAR_CONTEXT_AUTH.md](SIDECAR_CONTEXT_AUTH.md).

---

## Component lifetimes (summary)

| Component            | Created            | Lifetime        | Holds request state? |
| -------------------- | ------------------ | --------------- | -------------------- |
| Spec / validation    | build/load time    | transient       | no                   |
| `CompiledAgentGraph` | startup (once)     | application     | **no (immutable)**   |
| `RuntimeEngine`      | startup (once)     | application     | **no**               |
| Prompt templates     | first use / startup| cached          | no                   |
| `ExecutionContext`   | per request        | request         | **yes**              |
| Trace                | per request        | request         | yes                  |

This table is binding. Violating it (e.g. putting request state on the engine,
or rebuilding the graph per request) is an architecture rule violation.
