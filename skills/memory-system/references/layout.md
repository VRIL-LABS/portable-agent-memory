# Layout

Project-local store. Discovered from the repo the agent is working in, not from a hidden global sandbox.

```
<project_root>/
  .memsys-db            # hidden SQLite+FTS5 ledger (journal_mode=DELETE; regenerable via `reindex`)
  memories/
    .memory-root          # schema marker; required
    .gitignore            # ignores user/ and ../.memsys-db by default
    README.md
    user/                 # personal; default scope; typically not committed
      MEMORY.md           # always-loaded index; ≤200 lines
      <topic>.md          # on-demand
      skills/             # auto-discovered if SKILL.md exists
    team/                 # shared; only when the human asks
      MEMORY.md
      <topic>.md
      skills/
```

## Root discovery

`memory_tool` walks up from `--cwd`:

1. A directory that already contains `memories/.memory-root` (or `memories/`)
2. Else a directory containing `.git`, `go.mod`, `pyproject.toml`, `package.json`, `Cargo.toml`, `Makefile`, `composer.json`, `Gemfile`, `mix.exs`, or `deno.json`
3. Else fail. Never silently init at `/`.

The store is always `<project_root>/memories/`. Portable: clone the repo, the team store comes with it; user store stays local via `.gitignore`.

## Index contract

`MEMORY.md` is an index, not a diary.

- Must start with a heading
- Topics and Skills sections use `- [slug](file) — one-line summary`
- `## Last updated` is stamped by the tool, never by the model clock
- Fail if line count > 200

## Enumeration

The reliable listing is:

```bash
scripts/memory --cwd . glob "**/*.md"
scripts/memory --cwd . glob "user/skills/**/SKILL.md"
```

Never `ls`, `find`, or `tree` as proof. Re-`read` after every write and compare `sha256`.
