# `.codex/` — Codex adapter

The canonical, tool-agnostic project instructions live under [`.ai/`](../.ai/).
Codex-specific instruction files in this folder are generated adapters. They
contain full canonical content for Codex compatibility, but they are not editable
source files.

Start with:

- [`../AGENTS.md`](../AGENTS.md) — repo-wide rules for all agents.
- [`../.ai/README.md`](../.ai/README.md) — the instruction-system index.
- [`../.ai/skills/`](../.ai/skills/) — reusable operational playbooks.
- [`../.ai/roles/`](../.ai/roles/) — reusable agent personas (the source for any
  Codex agent definitions).
- [`../.ai/workflows/`](../.ai/workflows/) — task workflows.

Generated Codex adapters live at:

- `.codex/skills/<skill-name>.md`
- `.codex/agents/<role-name>.md`
- `.codex/workflows/<workflow-name>.md`

Regenerate adapters with `make sync-ai` after editing `.ai/**`.
`make sync-skills` remains a backward-compatible alias. Do not edit generated
adapter files directly.
