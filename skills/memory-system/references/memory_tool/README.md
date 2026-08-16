# memory_tool

Portable, project-local memory store. Stdlib only. JSON to stdout.

Never override, recalculate, or reformat output from this tool. It is the source of truth.

## Run

```bash
python3 -m memory_tool --help
# from this directory's parent:
PYTHONPATH=references python3 -m memory_tool init
# or via the wrapper:
scripts/memory init
```

Discovery walks up from `--cwd` (default: process cwd) looking for an existing `memories/.memory-root`, then for project markers (`.git`, `go.mod`, `pyproject.toml`, `package.json`, …). The store is always `<project_root>/memories/`.

## Commands

| Command | Purpose |
| --- | --- |
| `init` | Create `memories/{user,team}/` + indexes + marker |
| `root` | Print resolved project/memory roots |
| `glob [pattern]` | Enumerate store files. **The** listing method |
| `read PATH` | Read + sha256. A success summary is not proof — this is |
| `write PATH` | Create file after secret scan. `--overwrite` required to replace |
| `edit PATH --old X --new Y` | Exact-string replace. Fails on 0 or >1 matches |
| `validate` | Binary store contract check |
| `status` | Inventory + validation |
| `classify` | skill / index / topic / reject |
| `slug TEXT` | Deterministic hyphen slug |
| `scan-secrets` | Secret pattern scan |
| `index-link` | Upsert a MEMORY.md bullet |
| `selftest` | Sandbox assertion |

Exit codes: `0` ok, `1` fail, `2` usage, `3` secret, `4` not found, `5` ambiguous edit.

## Hard rules

- Never use `bash ls` / `find` as proof of store state
- Never write secrets
- Never escape `memories/`
- Never treat a compressed tool summary as on-disk proof
- Default scope is `user` unless the human asked for `team`
