# `.claude/` — Claude Code adapter

The canonical, tool-agnostic project instructions live under [`.ai/`](../.ai/).
Claude-specific instruction files in this folder are generated adapters. They
contain full canonical content for Claude compatibility, but they are not
editable source files.

Start with:

- [`../AGENTS.md`](../AGENTS.md) — repo-wide rules for all agents.
- [`../.ai/README.md`](../.ai/README.md) — the instruction-system index.
- [`../.ai/skills/`](../.ai/skills/) — reusable operational playbooks.
- [`../.ai/roles/`](../.ai/roles/) — reusable agent personas.
- [`../.ai/workflows/`](../.ai/workflows/) — task workflows.

This folder contains Claude-specific **tool configuration** and generated
adapters:

- `settings.json` — shared, conservative permissions for Claude Code.
- `skills/<name>/SKILL.md` — generated from `.ai/skills/<name>.md`.
- `agents/<name>.md` — generated from `.ai/roles/<name>.md`.
- `workflows/<name>.md` — generated from `.ai/workflows/<name>.md`.

Local/private config (`CLAUDE.local.md`, `.claude/settings.local.json`) is
git-ignored.

Regenerate adapters with `make sync-ai` after editing `.ai/**`.
`make sync-skills` remains a backward-compatible alias. Do not edit generated
adapter files directly.
