# Constitution

Imperative prohibitions. Violation is a failed run, not a style issue.

1. Never expose secrets, credentials, or PII in any output layer.
2. Never store secrets, API keys, passwords, tokens, private keys, or JWTs.
3. Never proceed with irreversible operations (wipe store, delete topic, publish to `team/`) without explicit human confirmation in the same session turn naming the exact target.
4. Never modify Zone B artifacts or their output post-execution.
5. Never enumerate memory with `bash ls`, `find`, `tree`, or sandbox directory listings.
6. Never treat compressed or summarized tool results as proof of on-disk state.
7. Never default scope to `team`. Never silently promote user memory to team.
8. Never build a second, competing storage mechanism for this skill's own memories. The store is files, via the bundled tool. (This does not preclude other memory systems the host environment may already provide — this skill is an additional, file-based layer, not a claim of exclusivity.)
9. Never dump detail into `MEMORY.md`. Never exceed 200 lines. Never skip truncation-by-split.
10. Never write outside `<project_root>/memories/`. Never follow path traversal.
11. Never skip `classify` and secret scan before a write.
12. Never soften, curve, or reinterpret a binary tool failure as success.
13. Never invent a recalled memory that `glob`/`read` did not return.
14. Never forward raw user input to a path argument without sanitization.
15. Never override slugs, checksums, line counts, or classify results from the tool.
16. Never enable WAL or otherwise let `.memsys-db` grow `-wal`/`-shm` sidecars; never let the ledger outrank markdown; never pass raw FTS `MATCH` syntax to SQLite (tokenize and quote); never store secret text in `secrets_hits` (rule name only); never add Adminer/GUI/daemon databases to the agent path; never ship user rows in the skill bundle.
