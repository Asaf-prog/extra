# Roadmap

A phased, honest plan. The repository is in the **foundation phase**. Each phase
below maps to one or more task files in `tasks/`. Status reflects reality, not
aspiration.

| Phase | Theme                         | Tasks      | Status        |
| ----- | ----------------------------- | ---------- | ------------- |
| 0     | Repository foundation         | docs/skills/tasks | ✅ done   |
| 1     | Package skeleton & tooling    | 0001       | ⏳ planned     |
| 2     | YAML schema & validation      | 0002       | ⏳ planned     |
| 3     | Compiled agent graph          | 0003       | ⏳ planned     |
| 4     | Runtime engine                | 0004       | ⏳ planned     |
| 5     | Prompt rendering              | 0005       | ⏳ planned     |
| 6     | Sidecar context/auth          | 0006       | ⏳ planned     |
| 7     | MCP & tools + permissions     | 0007       | ⏳ planned     |
| 8     | CLI                           | 0008       | ⏳ planned     |
| 9     | API server                    | 0009       | ⏳ planned     |
| 10    | Docker / deployment           | 0010       | ⏳ planned     |
| 11    | Observability & tracing       | 0011       | ⏳ planned     |
| 12    | Tests & quality gates         | 0012       | ⏳ planned     |

## Principles guiding the order

- **Validate before compile, compile before run.** The schema/validation work
  (0002) precedes the compiler (0003), which precedes the runtime (0004).
- **Capabilities before surfaces.** Core capabilities (prompts, sidecar, tools)
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
- Client-specific auth or business logic (this is the sidecar's job, forever).
- Turning YAML into a general-purpose programming language.
