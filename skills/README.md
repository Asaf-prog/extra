# Skills

This directory contains **operational playbooks** for AI coding agents working
in this repository. Each skill is a focused guide for one discipline or area:
its purpose, when to use it, what to read first, core principles, a process,
checklists, common mistakes, and the report to produce afterwards.

## How to use skills

1. **Always start** with `project-architecture-skill.md` — it applies to every
   change.
2. Read the **practice skill(s)** for the *kind* of work you're doing (review,
   testing, engineering, refactoring, docs, git, architecture review).
3. Read the **area skill** for the *part of the system* you're touching (YAML,
   runtime, prompts, plugin context/access, tools).
4. **If a task touches multiple areas, read all relevant skills before editing.**
5. Follow the process, finish the checklist, and produce the skill's expected
   report.

## Practice / discipline skills

How to work well, regardless of which part of the system you touch.

| Skill                                                                   | Use when…                                          |
| ----------------------------------------------------------------------- | -------------------------------------------------- |
| [project-architecture-skill](project-architecture-skill.md)             | Anything — overall rules and layout (always).      |
| [senior-python-engineering-skill](senior-python-engineering-skill.md)   | Writing/structuring Python code.                   |
| [code-review-skill](code-review-skill.md)                               | Reviewing a change (others' or your own).          |
| [architecture-review-skill](architecture-review-skill.md)               | A change affects layers, lifecycles, or contracts. |
| [refactoring-skill](refactoring-skill.md)                               | Restructuring code without changing behavior.      |
| [testing-skill](testing-skill.md)                                       | Writing or running tests.                          |
| [documentation-skill](documentation-skill.md)                           | Editing docs, README, AGENTS.md, or ADRs.          |
| [git-workflow-skill](git-workflow-skill.md)                             | Branching, staging, committing.                    |
| [skill-authoring-skill](skill-authoring-skill.md)                       | Creating or restructuring a skill.                 |

## Area skills

What the rules are for a specific part of the system.

| Skill                                                          | Use when working on…                          |
| -------------------------------------------------------------- | --------------------------------------------- |
| [yaml-schema-skill](yaml-schema-skill.md)                      | YAML schema, loading, validation.             |
| [runtime-engine-skill](runtime-engine-skill.md)                | RuntimeEngine, ExecutionContext, lifecycle.   |
| [prompt-rendering-skill](prompt-rendering-skill.md)            | Prompt templates and rendering.               |
| [sidecar-auth-context-skill](sidecar-auth-context-skill.md)    | Plugin context and protected-node access.     |
| [mcp-tools-skill](mcp-tools-skill.md)                          | Tool plugins and MCP servers.                 |

> Note: practice skills follow the standard 8-section format
> (Purpose → … → Expected Final Report). Area skills predate that format and use
> a slightly leaner structure; both are valid. New skills should use the
> standard format from `skill-authoring-skill.md`.

## Relationship to tasks

Skills explain **how** to work; [`../tasks/`](../tasks/) define **what** to
build, in order. A task file lists which skill(s) to read first. See the skill
mapping in [`../AGENTS.md`](../AGENTS.md) (§5, Skills System).
