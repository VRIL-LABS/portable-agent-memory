-- memory-system .memsys-db schema. Deterministic Zone B.
-- SQLite + FTS5. journal_mode MUST be DELETE (single hidden file; no -wal/-shm).
-- Markdown under memories/ is the source of truth; this DB is the regenerable
-- index, ledger, and search plane. User rows are never shipped in the skill bundle.
PRAGMA journal_mode = DELETE;

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    lines INTEGER NOT NULL,
    kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL,
    slug TEXT NOT NULL,
    class TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    slug,
    body,
    content = 'entries',
    content_rowid = 'id'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts (rowid, slug, body) VALUES (new.id, new.slug, new.body);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts (entries_fts, rowid, slug, body)
        VALUES ('delete', old.id, old.slug, old.body);
END;

CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts (entries_fts, rowid, slug, body)
        VALUES ('delete', old.id, old.slug, old.body);
    INSERT INTO entries_fts (rowid, slug, body) VALUES (new.id, new.slug, new.body);
END;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    op TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS secrets_hits (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    rule TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Optional KNN plane. Populated only when the sqlite-vec extension is present.
CREATE TABLE IF NOT EXISTS vec_entries (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL,
    dim INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
