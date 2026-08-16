# Protocol

Zero-trust. Typed arguments only. JSON is truth.

## INGEST

- Extract: intent (save/recall/list/update/forget/init), scope, topic hint, payload
- Reject: `..`, absolute paths outside the store, control characters, `$(...)`, raw HTML/tool tags in filenames
- Default scope `user`
- If the payload looks like a secret, run `scan-secrets` immediately and stop on hits

## RETRIEVE

```bash
scripts/memory --cwd . root
scripts/memory --cwd . glob "user/**/*.md"
scripts/memory --cwd . read user/MEMORY.md
scripts/memory --cwd . search "edge proxy"     # FTS5 over .memsys-db; tokenized, never raw MATCH
```

Load a topic file only when the query names it or the index link matches. Do not preload `team/` unless scope is team. `search` ranks candidates; `read` the file for the authoritative content.

## REASON

```bash
scripts/memory classify --text "$PAYLOAD" --hint "$INTENT" --title "$TITLE"
scripts/memory slug "$TITLE"
```

Speak the class and slug before writing.

## REFLECT

Stop if:

- team scope was not explicitly requested
- classifier is `reject`
- index would exceed 200 lines
- path would escape `memories/`
- human asked to forget but the target is ambiguous

## EXECUTE

Init if `root.initialized` is false and the human wants persistence:

```bash
scripts/memory --cwd . init
```

Write new topic:

```bash
scripts/memory --cwd . write user/<slug>.md --content-file "$TMP"
scripts/memory --cwd . index-link --scope user --slug <slug> --filename <slug>.md --summary "$ONE_LINE"
scripts/memory --cwd . read user/<slug>.md
```

Edit existing:

```bash
scripts/memory --cwd . read user/<slug>.md
scripts/memory --cwd . edit user/<slug>.md --old "$EXACT" --new "$REPLACEMENT"
scripts/memory --cwd . read user/<slug>.md
```

Overwrite existing only after a same-turn `read` and `--overwrite`.

Forget (delete) is irreversible: require same-turn human confirmation naming the exact path. Then:

```bash
scripts/memory --cwd . forget user/<slug>.md --confirm user/<slug>.md
scripts/memory --cwd . search "<slug>"        # confirm ledger purged
```

`forget` deletes the markdown file and drops the `.memsys-db` rows; `--confirm` must equal the path exactly or it exits 2 without touching anything.

If the ledger drifts (missing rows, stale checksums), rebuild it from markdown — the files are always the source of truth:

```bash
scripts/memory --cwd . reindex
```

## PACKAGE

Emit:

```json
{
  "ok": true,
  "skill": "memory-system",
  "schema": "memory-system/v1.1",
  "op": "write",
  "scope": "user",
  "path": "user/architecture.md",
  "sha256": "<from tool>",
  "warnings": [],
  "confidence": 1.0,
  "next": ["recall", "update", "promote-to-skill", "copy-to-team"]
}
```

Then one short human paragraph. Do not reformat the tool JSON.
