# YAML Specification

This document describes the **intended** structure of the declarative input
file (`agent.yml`). It is a design specification — no code parses this yet.
Validation and schema work happens in task `0002`; the compiler in `0003`.

The spec has two conceptual halves:

- **`definitions`** declare *what exists* (providers, MCP servers, tools,
  agents, prompts, context/security requirements).
- **`hierarchy`** declares the *visual nested structure* and routing between
  agents.

Keeping "what exists" separate from "how it is arranged" lets the same agent be
referenced in multiple places and keeps the hierarchy readable.

---

## Conceptual shape

```yaml
version: "1.0"

app:
  name: example-agent-system

runtime:
  entrypoint: root_orchestrator
  mode: monolith_runtime

definitions:
  llm_providers: {}
  mcp_servers: {}
  tools: {}
  agents: {}

hierarchy:
  agent: root_orchestrator
  children:
    - agent: business_orchestrator
      children:
        - agent: invoice_agent

security:
  sidecar:
    enabled: true

observability: {}

deployment: {}
```

---

## Top-level keys

| Key             | Required | Purpose                                                        |
| --------------- | -------- | -------------------------------------------------------------- |
| `version`       | yes      | Spec format version (string, e.g. `"1.0"`).                    |
| `app`           | yes      | Application metadata (`name`, and later description/owner).    |
| `runtime`       | yes      | Runtime settings: `entrypoint` (root agent id), `mode`.        |
| `definitions`   | yes      | All declared entities (see below).                             |
| `hierarchy`     | yes      | The nested agent tree and routing metadata.                    |
| `security`      | no       | Security/sidecar configuration.                                |
| `observability` | no       | Tracing/export configuration.                                  |
| `deployment`    | no       | Deployment-related hints (used by later phases).               |

---

## `definitions`

`definitions` is a set of named maps. Each entry is keyed by a stable **id** that
the hierarchy and other definitions reference.

### `llm_providers`
Declares LLM providers the system can use. A provider entry describes how to
reach a model (provider type, model name, parameters). **Secrets/API keys are
never stored here** — they are referenced indirectly (e.g. an environment
variable name) and resolved at runtime.

```yaml
definitions:
  llm_providers:
    default:
      type: openai          # provider kind
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY   # name of an env var, NOT the secret itself
```

### `mcp_servers`
Declares MCP servers the system can connect to (transport, address, allowed
tools). → See [MCP_AND_TOOLS.md](MCP_AND_TOOLS.md).

```yaml
definitions:
  mcp_servers:
    billing_mcp:
      transport: stdio
      command: ["billing-mcp"]
```

### `tools`
Declares tools available to agents, including which MCP server (if any) provides
them, declared input schema, **required permissions**, and any **injected
parameters** the runtime enforces. → See [MCP_AND_TOOLS.md](MCP_AND_TOOLS.md).

```yaml
definitions:
  tools:
    get_invoice:
      mcp_server: billing_mcp
      requires_permissions: ["invoice:read"]
      injected_params:
        tenant_id: "${context.tenant_id}"   # resolved by the runtime, not the model
```

### `agents`
Declares agents. An agent entry references a provider and prompt(s), lists the
tools it may use, and **declares what it needs**: required context values and
required permissions. The runtime resolves and enforces these.

```yaml
definitions:
  agents:
    invoice_agent:
      provider: default
      prompt: prompts/invoice_agent.md
      tools: ["get_invoice"]
      requires_context: ["tenant_id", "customer_code"]
      requires_permissions: ["invoice:read"]
```

### `prompts`
Prompts may be declared inline or referenced as template files. Either way they
are **templates** with placeholders, rendered per request. → See
[PROMPT_RENDERING.md](PROMPT_RENDERING.md).

### `context requirements` & `security requirements`
Agents and tools declare context (`requires_context`) and permissions
(`requires_permissions`). These declarations are what the runtime hands to the
sidecar and what the permission layer enforces. → See
[SIDECAR_CONTEXT_AUTH.md](SIDECAR_CONTEXT_AUTH.md).

---

## `hierarchy`

The hierarchy is a tree rooted at the `runtime.entrypoint` agent. Each node
references an agent by id and may contain `children` and routing metadata.

```yaml
hierarchy:
  agent: root_orchestrator
  children:
    - agent: business_orchestrator
      routing:
        when: "intent == 'billing'"   # routing metadata (declarative)
      children:
        - agent: invoice_agent
```

Rules the validator will enforce (task 0002):

- Exactly one root, and it must match `runtime.entrypoint`.
- Every `agent:` id must exist in `definitions.agents`.
- No cycles.
- Routing metadata is **declarative** — it describes *when* to route, it is not
  executable code.

---

## `security`

```yaml
security:
  sidecar:
    enabled: true
    endpoint_env: SIDECAR_URL     # env var name, not a hardcoded URL with secrets
    phases: ["pre_routing", "pre_agent"]
```

When the sidecar is enabled, the runtime calls it per the configured phases. →
See [SIDECAR_CONTEXT_AUTH.md](SIDECAR_CONTEXT_AUTH.md).

---

## Design rules for the spec

- **Declarative only.** YAML describes *what* and *which*, never *how* in code.
  No expressions that are really program logic; routing `when` clauses are
  declarative conditions, not arbitrary code.
- **References by id.** Cross-links use stable ids resolved at compile time.
- **No secrets.** Only references to secrets (env var names), never values.
- **Validated before use.** The compiler trusts only validated specs.

→ See [ADR 0002](adr/0002-yaml-is-compiled-not-executed-directly.md).
