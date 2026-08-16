# `.memsys-db` — the ledger contract

Markdown under `memories/` is the source of truth. `.memsys-db` is a **regenerable
index, ledger, and search plane** — never the only copy of prose, never outranking
the files.

## What it is

- One hidden SQLite file at `<project_root>/.memsys-db`.
- `journal_mode = DELETE`. **Never WAL** — `-wal`/`-shm` sidecars break the
  single-hidden-file contract. `validate` fails if either appears.
- SQLite **FTS5** always. `sqlite-vec` (`vec0`) attaches later, optionally —
  lexical search works alone.
- Created by `scripts/memory init` from the bundled `references/memory_tool/schema.sql`.
  The skill ships an empty schema, never user rows.
- `memories/.gitignore` ignores `../.memsys-db` (the ledger is derived state; `user/`
  data stays local either way).

## Schema (deterministic Zone B)

| Table | Role |
| --- | --- |
| `files(path, scope, sha256, lines, kind)` | per-file checksum ledger |
| `entries(id, scope, slug, class, path, body, sha256, updated_at)` | one row per markdown file |
| `entries_fts` | FTS5 over `slug + body`, content-synced by triggers |
| `events` | append-only audit (`write`, `reindex`, `secret_reject`, `forget`) |
| `secrets_hits` | fail-closed scan results — rule name + path only, **never** the secret text |
| `vec_entries` | placeholder for optional `sqlite-vec` KNN |

When `sqlite-vec` is importable, `init` also loads the extension and creates a
`vec0` virtual table `vec_index` inside the same file. If it is not installed,
everything above still works — lexical FTS5 alone. Embeddings are generated
locally (e.g. via `sqlite-lembed`/GGUF) only when the human opts in; never by
default.

## Commands

```bash
scripts/memory --cwd . init                                   # creates memories/ AND .memsys-db
scripts/memory --cwd . write user/edge-tls.md --content "..." # dual-write: file, then FTS upsert
scripts/memory --cwd . search "Envoy TLS"                     # tokenized FTS5; raw MATCH never reaches SQLite
scripts/memory --cwd . reindex                                # rebuild the ledger from markdown
scripts/memory --cwd . forget user/edge-tls.md --confirm user/edge-tls.md
```

## Hard rules

- `search` tokenizes the query into quoted FTS tokens joined by `OR`. Injection
  strings (e.g. `"; DROP TABLE entries; --`) are neutralized to harmless tokens.
- Secrets never enter the DB: writes fail closed before any upsert; the rejection
  is logged to `secrets_hits` by **rule name only**.
- `forget` is irreversible: `--confirm` must equal `path` exactly. It deletes the
  file and drops the ledger rows in the same run.
- The ledger is a cache. If `.memsys-db` is lost or corrupted, `reindex` rebuilds
  it from markdown. Never hand-edit the DB to change memory content — edit the
  markdown and re-run `write`/`edit`/`reindex`.
- After every write, both the markdown file and the DB row are checksum-verified.
