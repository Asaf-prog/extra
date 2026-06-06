# Declarative Agent Platform

> A declarative platform for building AI agent systems. Describe your agents in
> YAML; the platform validates, compiles, and runs them through a long-lived
> runtime with dynamic prompts, tools/MCP, client-owned context resolution, and
> execution tracing.

**Status: 🚧 Repository foundation phase.** This repository currently contains
documentation, architecture decisions, agent skills, and ordered implementation
tasks. **The runtime, YAML parser, compiler, sidecar client, MCP client, and
API are not implemented yet.** Nothing below describing the runtime is working
software — it describes the intended design that future work will build.

---

## 1. What this is

A platform that turns a declarative YAML description of an agent system into a
running, traceable, multi-agent application. You declare *what* exists (LLM
providers, MCP servers, tools, agents, prompts) and *how* it is structured (a
nested agent hierarchy), and the platform handles validation, compilation, and
execution.

## 2. Why it exists

Building multi-agent systems by hand means re-implementing the same plumbing
every time: prompt rendering, routing between agents, tool wiring, permission
enforcement, auth/context resolution, and tracing. This project moves that
plumbing into a reusable runtime and lets developers focus on the **declarative
specification** of their system rather than its mechanics.

## 3. Vision

- A single `agent.yml` fully describes an agent system.
- The specification is **validated** and **compiled** into a typed agent graph.
- A **long-lived runtime** executes requests against that graph.
- **Prompts are templates** rendered per request from dynamic context.
- **Client-specific auth and business context** live in a client-owned
  **sidecar**, not in generated runtime code.
- Every request produces a **trace** for observability and debugging.

## 4. Current status

Repository foundation phase. See the [Roadmap](docs/ROADMAP.md) and the
[`tasks/`](tasks/) directory for the planned, ordered implementation work.

| Area                      | Status         |
| ------------------------- | -------------- |
| Documentation & ADRs      | ✅ In place     |
| Agent skills              | ✅ In place     |
| Implementation tasks      | ✅ Defined      |
| YAML schema & validation  | ⏳ Planned (0002) |
| Compiled agent graph      | ⏳ Planned (0003) |
| Runtime engine            | ⏳ Planned (0004) |
| Prompt rendering          | ⏳ Planned (0005) |
| Sidecar context/auth      | ⏳ Planned (0006) |
| Tools & MCP               | ⏳ Planned (0007) |
| CLI / API / Docker        | ⏳ Planned (0008–0010) |
| Observability             | ⏳ Planned (0011) |

## 5. Planned architecture

```
agent.yml → validate → compile → CompiledAgentGraph → RuntimeEngine
          → ExecutionContext (per request) → recursive execution → response + trace
```

Layers: spec → validation → compiler → agent graph → runtime → prompt rendering
→ context resolver → sidecar → MCP/tools → tool permissions → observability →
API → CLI → deployment. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

**Key rule:** `RuntimeEngine` is created **once** at startup; `ExecutionContext`
is created **per request**. See
[ADR 0001](docs/adr/0001-runtime-engine-created-once.md).

## 6. Example future YAML shape

This is the **intended** shape (not yet parsed by any code). See
[docs/YAML_SPEC.md](docs/YAML_SPEC.md) for the full specification.

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

`definitions` declares *what exists*; `hierarchy` declares the *visual nested
structure* and routing relationships.

## 7. How the sidecar model works (high level)

The generated runtime contains **no** client-specific authentication,
authorization, or business-data lookup code. Instead, a client implements a
standard **Context/Auth Sidecar** contract. Before routing and/or before agent
execution, the runtime calls the sidecar (`POST /resolve-context`) to resolve
identity, tenant, customer code, roles, permissions, dynamic context values, and
tool input policies. The runtime maps the response into the `ExecutionContext`,
enforces permissions, and traces the decision. See
[docs/SIDECAR_CONTEXT_AUTH.md](docs/SIDECAR_CONTEXT_AUTH.md).

## 8. How prompts are rendered dynamically

Prompt files are **templates**. Parsed templates may be cached, but values are
resolved **per request** from request data, identity, sidecar context, system
time, memory, tools, databases, APIs, or plugins. Fully-rendered prompts are
**never** cached globally, and missing required variables fail loudly. Prompt
text is **not** a security boundary — enforcement happens at the tool/data
layer. See [docs/PROMPT_RENDERING.md](docs/PROMPT_RENDERING.md).

## 9. How future agents should work here

This repository is **agent-first**. If you are an AI coding agent:

1. Read [AGENTS.md](AGENTS.md) in full.
2. Read the relevant guide in [`skills/`](skills/).
3. Pick the next task in [`tasks/`](tasks/) and work strictly within its scope.
4. Run `make check` before finishing and report using the format in AGENTS.md.

## 10. Development setup

> Requires Python 3.11+. Tooling: `ruff`, `mypy`, `pytest` (configured in
> `pyproject.toml`). Early in the foundation phase some commands are no-ops or
> placeholders; this is expected and documented in the task files.

```bash
make install   # create/refresh the dev environment
make format     # auto-format
make lint       # ruff + mypy
make test       # pytest
make check      # format-check + lint + test (must pass before finishing a task)
```

## 11. Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the phased plan. In short:
foundation → spec & validation → compiler → runtime → prompts → sidecar →
tools/MCP → CLI/API → deployment → observability → quality gates.

## License

To be determined. This is a new open-source project; a license will be added
before any public release.
