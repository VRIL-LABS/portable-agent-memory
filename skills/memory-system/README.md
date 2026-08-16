# memory-system

Agent skill for a **portable, project-local** memory store. Compatible with the [Agent Skills](https://agentskills.io/specification) open standard.

The store lives in the repo the agent is working on:

```
<project>/memories/{user,team}/MEMORY.md
```

This skill's persistence is file-based: this directory convention plus `references/memory_tool`. It doesn't assume the host has no other memory mechanism — if one exists, treat this as an additional, project-local layer alongside it.

## Install

Copy the `memory-system/` folder to one of:

| Runtime | Project path | User path |
| --- | --- | --- |
| Claude Code | `.claude/skills/memory-system/` | `~/.claude/skills/memory-system/` |
| GitHub Copilot | `.github/skills/memory-system/` | `~/.copilot/skills/memory-system/` |
| Windsurf Cascade | `.windsurf/skills/memory-system/` | `~/.codeium/windsurf/skills/memory-system/` |
| Cross-agent | `.agents/skills/memory-system/` | `~/.agents/skills/memory-system/` |
| Cursor / VS Code / Goose / Amp / Gemini CLI | `.agents/skills/memory-system/` | implementation default |

Requires Python 3.9+ (stdlib only).

## Verify

```bash
scripts/memory selftest
```

Must print `"ok": true` and exit 0.

## Use

The agent loads this skill when you say remember, forget, persist a preference, recall a decision, or mention `memories/` / `MEMORY.md`. You can also invoke it by name (`/memory-system`, `@memory-system`) depending on the host.

## Layout of this skill

```
memory-system/
  SKILL.md
  scripts/memory
  references/memory_tool/    # portable glob storage system
  references/*.md
  assets/templates/
  assets/schemas/
  examples/
```
