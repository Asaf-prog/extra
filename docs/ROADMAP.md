# Roadmap

A phased, honest plan. Each phase below maps to one or more task files in
`tasks/`. Status reflects reality, not aspiration.

| Phase | Theme                         | Tasks      | Status        |
| ----- | ----------------------------- | ---------- | ------------- |
| 0     | Repository foundation         | docs/.ai/tasks | ✅ done      |
| 1     | Package skeleton & tooling    | 0001       | ✅ done        |
| 2     | YAML schema & validation      | 0002       | ✅ done        |
| 3     | Compiled agent graph          | 0003       | ✅ done        |
| 4     | Runtime engine                | 0004       | ✅ done        |
| 5     | Prompt rendering              | 0005       | 🔶 partial     |
| 6     | Plugin context/access         | 0006       | 🔶 partial     |
| 7     | MCP & plugin tools            | 0007       | 🔶 partial     |
| 8     | CLI                           | 0008       | 🔶 partial     |
| 9     | API server                    | 0009       | ⏳ planned     |
| 10    | Docker / deployment           | 0010       | ⏳ planned     |
| 11    | Observability & tracing       | 0011       | ⏳ planned     |
| 12    | Tests & quality gates         | 0012       | ⏳ planned     |

## Open-source developer-experience milestones

The platform is **self-hosted open source**. The bundled `examples/agents.yml`
demonstrates the product end-to-end. The CLI (**`agentctl`**) unlocks these
milestones in order:

| Milestone | Command (on `examples/agents.yml`) | Enabled by | Status |
| --------- | ---------------------------------- | ---------- | ------ |
| Validate  | `agentctl validate examples/agents.yml` | 0002 | ✅ done |
| Generate  | `agentctl generate examples/agents.yml --mode all` | 0006 | ✅ done |
| Run local | `agentctl run examples/agents.yml --message "hello"` | 0004–0006 | ✅ done |
| Inspect   | `agentctl graph examples/agents.yml` | 0003 | ⏳ planned |
| Serve     | `agentctl serve examples/agents.yml` | 0009 | ⏳ planned |

Validate, generate, and run work today. Graph inspection (visual/text dump of
the compiled graph) and the HTTP server are planned.

## Phase detail: what "partial" means

**Phase 3 — Compiled agent graph (✅ done).** `compiler/compile.py` compiles a
validated spec into an immutable `CompiledAgentGraph`. Node declarations
(orchestrators and agents) are built with resolved model, resolver, tool, and
MCP bindings. The `graph` tree is expanded into `AgentNode` objects with stable
node paths. Tests cover compilation and node path generation.

**Phase 4 — Runtime engine (✅ done).** `RuntimeEngine` (via `Engine`) is
created once from a `LoadedSpec`. `ExecutionContext` is created per request.
LangGraph-based routing recurses through orchestrators to leaf agents. Agents
call LLMs with tools bound. Tests cover routing with mock LLM factories.

**Phase 5 — Prompt rendering (🔶 partial).** Prompt file loading and simple
`{{ variable }}` substitution work inside `langgraph_builder.py`. Resolver
values are injected per request. **Remaining:** a dedicated `prompts/` module
with a parsed-template cache, strict missing-variable errors, and a formal
renderer interface.

**Phase 6 — Plugin context/access (🔶 partial).** Resolver plugins are fully
implemented: TOML-configured per-agent resolver classes, dynamic loading,
`BaseResolver` + per-agent subclasses, shared/agent-scoped resolvers, generation
modes (`--mode all/children/child`), overwrite protection, stale detection.
Access plugin contract (`plugins/access.py`) is defined but **not yet wired
into routing** — protected-node filtering is not enforced at runtime.

**Phase 7 — MCP & plugin tools (🔶 partial).** Python plugin tools load from
`plugins/tools/` and are bound to agents at graph-build time. Tool-call loops
work. **Remaining:** MCP client integration (connecting to declared MCP server
URLs and discovering their tools).

**Phase 8 — CLI (🔶 partial).** `agentctl validate`, `agentctl generate`
(with `--mode`, `--agent`, `--force`), `agentctl run`, and `agentctl version`
are implemented. **Remaining:** `agentctl graph` (inspect/dump compiled graph).

## Principles guiding the order

- **Validate before compile, compile before run.** The schema/validation work
  (0002) precedes the compiler (0003), which precedes the runtime (0004).
- **Capabilities before surfaces.** Core capabilities (prompts, plugins, tools)
  land before the surfaces that expose them (CLI, API).
- **Deployment and deep observability last**, once there is something to deploy
  and observe.
- **Tests accompany every task**; task 0012 hardens the overall quality gate
  rather than introducing testing for the first time.

## What "done" means per phase

A phase is done when its task's acceptance criteria are met, `make check`
passes, and the relevant documentation is consistent with the implementation.

## Explicitly out of scope (for now)

- Production-grade deployment topologies beyond a basic container.
- A hosted control plane / UI.
- Client-specific auth or business logic (this is the customer's plugin's job).
- Turning YAML into a general-purpose programming language.
