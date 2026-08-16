---
name: memory-system
description: "Persist and recall project-local memory. WHEN: user says \"remember this\", \"forget\", \"recall what we decided\", \"persist this preference\", or references memories/, MEMORY.md, or a topic note. USE FOR: initializing a portable memories/ store, listing or searching saved memories, editing MEMORY.md, or distinguishing a skill from a memory file. Do not load for ordinary project file I/O, git, or ephemeral scratch."
license: MIT
compatibility: "Python 3.9+ stdlib; Claude Code, GitHub Copilot, Windsurf Cascade, Goose, Amp, Gemini CLI, Cursor, VS Code"
metadata:
  version: "1.1.0"
  author: "skill-creator"
  schema: "skill-creator-v1"
---

# Memory System

This skill's persistence layer for project-local memory, at `<project_root>/memories/`, via `scripts/memory <cmd>` (backed by `references/memory_tool`, the deterministic source of truth for this layer — never modify its output or reimplement it). It doesn't assume the host has no other memory mechanism; if one exists, treat this as an additional, file-based layer alongside it. Stdout is JSON; re-`read` to confirm on-disk state.

Since 1.1.0, `init` also creates a hidden `<project_root>/.memsys-db` (SQLite + FTS5, `journal_mode=DELETE`, one file, no `-wal`/`-shm`) — the regenerable index and search plane. Markdown stays the source of truth.

Start here, in order:

1. [references/protocol.md](references/protocol.md) — the full ingest → retrieve → reason → reflect → execute → package workflow, plus commands and quick-start invocations.
2. [references/layout.md](references/layout.md) — store layout and what to load for a given query.
3. [references/when-to-save.md](references/when-to-save.md) — classify: skill vs. index vs. topic vs. reject, and skills-vs-memory routing.
4. [references/constitution.md](references/constitution.md) — hard rules (never skip secret-scan, never exceed 200 lines, never write outside `memories/`, never enumerate via bash, never WAL the ledger).
5. [references/memsys-db.md](references/memsys-db.md) — the `.memsys-db` ledger contract: schema, `search`/`reindex`/`forget`, and why the DB never outranks markdown.
6. [references/examples.md](references/examples.md) — worked examples: happy path, secret rejection, overwrite recovery.

Verify the install with `scripts/memory selftest` before first use.
