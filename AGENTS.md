# AGENTS.md - Development Guidance for `memory-system` v2.2.0

## Summary

Nominally enhance and genuinely achieve total technological superiority with breakthrough programmatically excellent domination by integrating a portable database(s) that are portably copied from the `memory-system` skill bundle into the agent’s current project and instantiated for reference as a hidden file (i.e. `.memsys-db`).

Utilize GitHub to deep-search for the most bleeding-edge solutions to hyperfuse into the `memory-system` skill further to our goal.

## Development Plan Summary

Use a **SQLite** file as `.memsys-db`. The winning stack is SQLite + FTS5 now, with optional `sqlite-vec` later — not DuckDB, LanceDB, or a web admin panel.[1][2][3]

## Verdict

| Option | Role | Fits `.memsys-db`? | Ship in the skill? |
| --- | --- | --- | --- |
| SQLite (`sqlite3` stdlib) | Single-file ACID store | Yes | Default. Zero extra deps |
| FTS5 | Built-in lexical search | Yes, inside the same file | Default. No model, no network |
| [sqlite-vec](https://github.com/asg017/sqlite-vec) | In-process KNN (`vec0`) | Yes, same file | Optional loadable extension |
| [Turso](https://github.com/tursodatabase/turso) / [libSQL](https://github.com/tursodatabase/libsql) | SQLite-compatible rewrite, MCP, encryption | Same file shape, still BETA | Adapter later, not the core |
| DuckDB | Embedded OLAP | File, but write-hostile | No. Wrong workload |
| [LanceDB](https://github.com/lancedb/lancedb) | Embedded multimodal vectors | Directory of files, not one hidden file | No as the ledger |
| [Adminer](https://github.com/vrana/adminer) | One-file PHP browser | Needs PHP + HTTP | Never in the agent path |

Adminer cannot be the database. It is a deployable inspector for MySQL/Postgres/SQLite and would force a PHP runtime plus an HTTP surface into every project. That is the opposite of a portable hidden file.[2][4]

DuckDB is an in-process analytics engine, not a transactional memory ledger. LanceDB is a retrieval library that wants a directory, not one inode. Redis/Milvus/Qdrant/pgvector need daemons. They lose the “copy the skill into the project and go” contract.

## Why this stack wins

The current skill already forbids inventing a sidecar API and already uses Python stdlib. `sqlite3` is in that stdlib. The file can be created by `scripts/memory init` at `<project>/.memsys-db` and enumerated the same way as `memories/` — never via `ls`.

Lexical-first is not a compromise. [deja-vu](https://github.com/vshulcz/deja-vu) indexes agent transcripts with no embeddings and reports 84.9% hit@1 on LongMemEval-S, ~12 ms over 3.3 GB.  [vstash](https://arxiv.org/abs/2604.15484) puts hybrid retrieval in one SQLite file: `sqlite-vec` + FTS5 + reciprocal rank fusion.  [memento](https://github.com/iAchilles/memento) is the same triad as an MCP memory server.  [Uteke](https://github.com/codecoradev/uteke) is the 2026 local-first engine: SQLite + FTS5 + vectors, single Rust binary, ~45 ms recall, no API keys.[3][5][6][7][8]

Keep markdown as the human source of truth. The DB is the index, ledger, and search plane — regenerable from files, never the only copy of prose.[9]

## How `.memsys-db` should exist

Do not enable WAL if you want a single hidden file. WAL creates `.memsys-db-wal` and `.memsys-db-shm`, which breaks the “one inode” story. Use DELETE journal mode so only `.memsys-db` appears.[10]

Copy semantics from the skill bundle:

- Ship `references/memory_tool/schema.sql` + empty migrations, not a pre-filled binary
- `init` creates `<project>/.memsys-db` in the discovered project root
- Never copy user rows out of the skill
- Add `.memsys-db` to `memories/.gitignore` for `user` data; `team` rows can be a second attached DB or a scope column
- After every write, checksum both the markdown file and the DB row. JSON from the tool remains source of truth

Suggested schema (deterministic Zone B):

- `files(path, scope, sha256, lines, kind)`
- `entries(id, scope, slug, class, path, body, sha256, updated_at)`
- `entries_fts` — FTS5 over slug + body
- `events` — append-only audit (op, path, sha256)
- `secrets_hits` — fail-closed scan results, never the secret text
- `vec_entries` — optional `vec0` table when `sqlite-vec` is present[1][11]

Search path: FTS5 always. If `sqlite-vec` loads, RRF hybrid. If it does not, lexical still works. That is how deja-vu and SuperLocalMemory stay useful offline.[5][12]

## What to fuse from GitHub

Do not vendor Uteke or deja-vu into the skill. Steal their contracts:

- **deja-vu**: redact at index time; tombstones so rebuild cannot resurrect forgotten rows; `blame <path>`; JSON doctor; no LLM required.[5]
- **sqlite-vec + sqlite-lembed**: keep vectors inside SQLite; generate embeddings locally from GGUF only when the human opts in.[1]
- **Turso MCP**: nine typed tools (`list_tables`, `execute_query`, `schema_change`). Mirror that as `memory_tool` subcommands, not a second daemon. Turso itself is still BETA — file-compatible later, not the default engine.[13]
- **Uteke / memento / Sibyl-Memory**: hybrid recall, file+SQLite dual write, no cloud.[6][7]
- **Litestream**: optional team backup of `.memsys-db` to object storage. Not required for v1.
- **Graphify**: deterministic graph over the repo. Complementary skill, not a replacement store.

Do not add Adminer, Beekeeper, or DB Browser to the agent runtime. If a human needs a GUI, they open `.memsys-db` with those tools themselves.[4]

The next implementation slice is small: `memory_tool init` creates `.memsys-db` from `schema.sql`, every `write`/`edit` upserts FTS5, `glob`/`status` can query the ledger, and `search` is a new Zone B command. Markdown stays authoritative. Say the word and that becomes `memory-system` 1.1.0.

## What 2.2.0 should add

Markdown under `memories/` stays the source of truth. `init` now also instantiates a hidden `<project>/.memsys-db` from the bundled `schema.sql` — SQLite + FTS5, `journal_mode=DELETE`, one file, no `-wal`/`-shm`.

| Command | Contract |
| --- | --- |
| `search QUERY` | Tokenized FTS5. Raw `MATCH` never reaches SQLite |
| `reindex` | Rebuilds the ledger from markdown |
| `forget PATH --confirm PATH` | Deletes file + drops ledger rows only when paths match |
| `write` / `edit` | Dual-write file then upsert FTS. Secrets never enter the DB |

Optional `sqlite-vec` can attach later; lexical search works alone.

## Use

```bash
scripts/memory --cwd . init
scripts/memory --cwd . write user/edge-tls.md --content "# Edge TLS\n\nTerminate TLS at Envoy.\n"
scripts/memory --cwd . search "Envoy TLS"
scripts/memory selftest
```

## Security and quality audit

| Check | Resolution |
| --- | --- |
| Description routes correctly | Load on remember/search/`.memsys-db`; silent on ordinary I/O |
| Reproducible ops in Zone B | Slug, FTS query, checksums, journal mode, classify are scripted |
| Hard stops | 16 Never-rules, including no WAL, no Adminer, ledger never outranks markdown |
| Injection | Paths sanitized; FTS tokens quoted; secret writes logged by rule name only |
| Single hidden file | Selftest asserts no `-wal`/`-shm`; `validate` fails if sidecars appear |
| Forget is irreversible | `--confirm` must equal `path` |
| Machine-readable | JSON envelope, schema `memory-system/v1.1` |
| Progressive disclosure | SKILL.md is 146 lines; DB contract lives in `references/memsys-db.md` |

- The natural next step is `init` in a real repo and one `search` after a write to confirm the ledger. 

- Once this phase is completed cleanly, Attach `sqlite-vec` to finalize, perform quality assurance testing again, then mark as complete.

Sources
[1] GitHub - asg017/sqlite-vec: A vector search SQLite extension that runs anywhere! https://github.com/asg017/sqlite-vec
[2] GitHub - vrana/adminer: Database management in a single PHP file https://github.com/vrana/adminer
[3] vstash: Local-First Hybrid Retrieval with Adaptive Fusion for LLM Agents https://arxiv.org/abs/2604.15484
[4] 33 Best SQLite GUI Clients — Free & Paid (2026) https://1bench.dev/best/sqlite-gui-clients
[5] vshulcz/deja-vu: Your agents already solved ... https://github.com/vshulcz/deja-vu
[6] iAchilles/memento: MCP memory server using SQLite + ... https://github.com/iAchilles/memento
[7] Uteke - The Brain for Your AI https://github.com/codecoradev/uteke
[8] Uteke — Offline Semantic Memory Engine for AI Agents https://codecora.dev/uteke
[9] Where does your agent memory live? : r/AI_Agents https://www.reddit.com/r/AI_Agents/comments/1tp3tvs/where_does_your_agent_memory_live/
[10] Write-Ahead Logging https://www.sqlite.org/wal.html
[11] Memory That Outlives the Context Window https://thelastguardian.me/posts/2026-04-12-memory-that-outlives-the-context-window/
[12] SuperLocalMemory: Privacy-Preserving Multi-Agent Memory with Bayesian Trust Defense Against Memory Poisoning https://arxiv.org/abs/2603.02240
[13] GitHub - tursodatabase/turso: Turso is an in-process SQL database, compatible with SQLite. https://github.com/tursodatabase/turso
[14] Web Cloud Databases - Connecting to a database https://docs.ovhcloud.com/en/guides/web-cloud/databases/db-connecting-database-server
[15] 16.2 A 28nm 53.8TOPS/W 8b Sparse Transformer Accelerator with In-Memory Butterfly Zero Skipper for Unstructured-Pruned NN and CIM-Based Local-Attention-Reusable Engine https://ieeexplore.ieee.org/document/10067360/
[16] Developer-Centric Bug Prediction: A Local Desktop Vulnerability Analysis System with Dual-Engine Detection, SQLite Persistence, and Longitudinal Security Dashboards https://ijdim.com/journal/index.php/ijdim/article/view/487
[17] Energy-Efficient and High-Throughput CNN Inference Engine Based on Memory-Sharing and Data-Reusing for Edge Applications https://ieeexplore.ieee.org/document/10521770/
[18] SynaptiQ: Building a Local-First Conversational Analytics Platform with NL-to-SQL, Forecasting, and Offline Voice Support https://www.ijraset.com/best-journal/synaptiq-conversational-analytics-and-decision-intelligence-platform
[19] Storing Data in a PHP Project - Spoken Like a Geek https://www.spokenlikeageek.com/2025/10/15/storing-data-in-a-php-project/
[20] An Efficient LSM-Tree-Based SQLite-Like Database Engine for Mobile Devices https://ieeexplore.ieee.org/document/8411471/
[21] Baru di dunia open-source LLM! Kenalan sama Ornith-1.0 ... https://www.instagram.com/p/DaDDMSaEwN_/
[22] DB-LIO: Database-Driven LiDAR–Inertial Odometry for Memory-Bounded Persistent Mapping https://www.mdpi.com/1424-8220/26/10/3061
[23] Aero-engine remaining useful life prediction using state-involving graph networks with multi-scale perception enhancement https://iopscience.iop.org/article/10.1088/2631-8695/ae8409
[24] Configurable Dataflow and Adaptive Mapping Optimization for Hybrid ReRAM and SRAM Compute-in-Memory Accelerator https://ieeexplore.ieee.org/document/11119681/
