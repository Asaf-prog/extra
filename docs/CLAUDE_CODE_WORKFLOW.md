# Claude Code Workflow

How this repository is prepared for **Claude Code**, and how to work in it
effectively. This complements `AGENTS.md` (the tool-agnostic manual) and
`CLAUDE.md` (the Claude entrypoint).

---

## 1. How this repository is prepared for Claude Code

All agent instructions — skills, roles, and workflows — live in one canonical,
tool-agnostic place: **`.ai/`**. Claude Code reads `CLAUDE.md` as its entrypoint,
which points to `.ai/`. `.claude/` holds only tool configuration and a thin
adapter README; it contains **no duplicated instructions**.

```
CLAUDE.md                      ← Claude entrypoint (mission, rules, skill/role map)
.claude/
├── settings.json              ← conservative, shared project settings (permissions)
└── README.md                  ← thin adapter; points to .ai/
docs/CLAUDE_CODE_WORKFLOW.md   ← this file
.ai/                           ← canonical, tool-agnostic instruction system
├── README.md                  ← index
├── skills/                    ← operational playbooks (how to work)
├── roles/                     ← agent personas (architect, reviewer, …)
└── workflows/                 ← end-to-end task workflows
```

## 2. What `CLAUDE.md` is for

`CLAUDE.md` is the project entrypoint Claude Code reads first. It states the
mission, the core pipeline, the non-negotiable architecture rules, what to read
before feature work, how to use the `.ai/` skills and roles, the validation
commands, and the required final-response format. If `CLAUDE.md` and `AGENTS.md`
ever disagree, `AGENTS.md` wins.

## 3. Single source of truth: `.ai/`

There is **one** instruction system, under `.ai/`:

- `.ai/skills/<name>.md` — operational playbooks (each with `name`/`description`
  frontmatter so any tool can select them).
- `.ai/roles/<name>.md` — focused personas (`architect`, `code-reviewer`,
  `test-engineer`, `documentation-writer`).
- `.ai/workflows/<name>.md` — recipes that combine roles + skills for a common
  task (`feature-task`, `code-review`, `testing`, `documentation-update`).

Claude Code, Codex, Cursor, and any future tool read the same files. **Do not
copy these into `.claude/` (or any tool folder).** If a tool needs a specific
format in the future, generate a *thin adapter* that references `.ai/` — never a
duplicate.

Available skills: `project-architecture`, `senior-python-engineering`,
`code-review`, `architecture-review`, `refactoring`, `testing`, `documentation`,
`git-workflow`, `skill-authoring`, `yaml-schema`, `runtime-engine`,
`prompt-rendering`, `sidecar-auth-context`, `mcp-tools`.

## 4. Roles (personas)

Adopt a role from `.ai/roles/` when the work matches it:

- **architect** — architecture planning/review (read-only; doesn't implement
  unless asked).
- **code-reviewer** — senior structured review.
- **test-engineer** — plans/writes pytest tests; never calls real services.
- **documentation-writer** — updates docs/ADRs honestly.

## 5. Recommended workflow

1. **Read the task** in `tasks/` (Goal, Scope, Files allowed to change, Out of
   scope).
2. **Read context** (`AGENTS.md`, `CLAUDE.md`, `.ai/README.md`, and the
   architecture/layer docs the task touches).
3. **Pick a workflow** in `.ai/workflows/` and the skill(s) it names. Always read
   `.ai/skills/project-architecture.md` first. If the task touches multiple
   areas, read all relevant skills first.
4. **Plan** the change in small, task-sized steps (adopt the `architect` role for
   design-heavy work).
5. **Implement a small change** within scope.
6. **Run validation:** `make check` (format-check + lint + test).
7. **Report clearly** using the final-response format in `CLAUDE.md`/`AGENTS.md`.

## 6. What not to do

- **Do not build everything in one task.** Work task-by-task.
- **Do not rewrite architecture casually.** Contract/architecture changes need an
  ADR (use `.ai/skills/architecture-review.md`).
- **Do not skip tests.** Behavior ships with tests; mock external systems.
- **Do not hardcode secrets** in code, YAML, prompts, or `.claude/` config.
- **Do not duplicate** instructions into `.claude/` or any tool folder — keep
  `.ai/` the single source of truth and reference it.
