# `.codex/` — Codex adapter (no duplicated instructions)

Codex-specific duplicate skills and agent definitions are intentionally **not**
stored here. The canonical, tool-agnostic project instructions live under
[`.ai/`](../.ai/).

Start with:

- [`../AGENTS.md`](../AGENTS.md) — repo-wide rules for all agents.
- [`../.ai/README.md`](../.ai/README.md) — the instruction-system index.
- [`../.ai/skills/`](../.ai/skills/) — reusable operational playbooks.
- [`../.ai/roles/`](../.ai/roles/) — reusable agent personas (the source for any
  Codex agent definitions).
- [`../.ai/workflows/`](../.ai/workflows/) — task workflows.

If Codex needs `.codex/agents/*.toml` definitions in the future, generate them
as **thin adapters** whose `developer_instructions` point to the matching role
in `.ai/roles/` — never copy the content.
