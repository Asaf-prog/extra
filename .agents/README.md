# `.agents/` — generic agent adapter (no duplicated instructions)

Duplicate skills are intentionally **not** stored here. The canonical,
tool-agnostic project instructions live under [`.ai/`](../.ai/).

Start with:

- [`../AGENTS.md`](../AGENTS.md) — repo-wide rules for all agents.
- [`../.ai/README.md`](../.ai/README.md) — the instruction-system index.
- [`../.ai/skills/`](../.ai/skills/) — reusable operational playbooks.
- [`../.ai/roles/`](../.ai/roles/) — reusable agent personas.
- [`../.ai/workflows/`](../.ai/workflows/) — task workflows.

If a tool that auto-discovers skills from `.agents/skills/` is adopted, generate
**thin adapters that reference `.ai/`** — never copy the content.
