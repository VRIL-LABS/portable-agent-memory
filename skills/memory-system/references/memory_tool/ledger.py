"""SQLite ledger for .memsys-db. Markdown stays authoritative; this is the index.

Rules: journal_mode=DELETE (single hidden file, never WAL), FTS5 always, raw
MATCH strings never reach SQLite (queries are tokenized and quoted), secrets
never enter the DB (fail-closed scan before upsert), sqlite-vec optional.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .constants import DB_NAME, SCOPES, SECRET_RULES
from . import core

_SCHEMA_SQL = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
_FTS_TOKEN = re.compile(r"[A-Za-z0-9_]+")
_KIND_INDEX = "index"
_KIND_SKILL = "skill"
_KIND_TOPIC = "topic"


def db_path(project_root: Path) -> Path:
    return project_root.resolve() / DB_NAME


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    mode = conn.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
    if str(mode).lower() != "delete":
        conn.close()
        raise core.MemoryError(
            "wal_forbidden",
            "journal_mode=%s would create sidecar files. DELETE required." % mode,
            db=str(path),
        )
    return conn


def init_db(project_root: Path) -> dict[str, Any]:
    path = db_path(project_root)
    existed = path.is_file()
    conn = _connect(path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        assert_single_file(path)
        vec = vec_available(conn)
        if vec:
            conn.commit()
        return {
            "db": str(path),
            "created": not existed,
            "fts5": True,
            "sqlite_vec": vec,
            "journal_mode": "delete",
        }
    finally:
        conn.close()


def require_db(project_root: Path) -> Path:
    path = db_path(project_root)
    if not path.is_file():
        raise core.MemoryError(
            "db_missing",
            f"{DB_NAME} not found. Run: memory_tool init",
            db=str(path),
        )
    return path


def assert_single_file(path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        if path.with_name(path.name + suffix).exists():
            raise core.MemoryError(
                "sidecar_detected",
                f"{path.name}{suffix} exists; WAL sidecars are forbidden.",
                db=str(path),
            )


def vec_available(conn: sqlite3.Connection | None = None) -> bool:
    try:
        import sqlite_vec  # type: ignore  # noqa: F401
    except Exception:
        return False
    if conn is not None:
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)  # type: ignore[union-attr]
            ensure_vec_table(conn)
            return True
        except Exception:
            return False
    return True


def ensure_vec_table(conn: sqlite3.Connection, dim: int = 384) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vec_index'"
    ).fetchone()
    if not exists:
        conn.execute(
            "CREATE VIRTUAL TABLE vec_index USING vec0(embedding float[%d])" % dim
        )


def _kind_for(rel: str, name: str) -> str:
    if name == core.INDEX_NAME:
        return _KIND_INDEX
    parts = Path(rel).parts
    if len(parts) >= 2 and parts[1] == "skills":
        return _KIND_SKILL
    return _KIND_TOPIC


def upsert_entry(conn: sqlite3.Connection, rel: str, text: str) -> None:
    parts = rel.split("/")
    scope = parts[0] if parts and parts[0] in SCOPES else "user"
    name = parts[-1] if parts else rel
    slug = name[:-3] if name.endswith(".md") else name
    sha = core.sha256_text(text)
    now = core.utc_now()
    conn.execute(
        "INSERT INTO files (path, scope, sha256, lines, kind) VALUES (?,?,?,?,?) "
        "ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256, lines=excluded.lines, "
        "kind=excluded.kind, scope=excluded.scope",
        (rel, scope, sha, len(text.splitlines()), _kind_for(rel, name)),
    )
    conn.execute(
        "INSERT INTO entries (scope, slug, class, path, body, sha256, updated_at) "
        "VALUES (?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET scope=excluded.scope, "
        "slug=excluded.slug, class=excluded.class, body=excluded.body, "
        "sha256=excluded.sha256, updated_at=excluded.updated_at",
        (scope, slug, _kind_for(rel, name), rel, text, sha, now),
    )
    conn.execute(
        "INSERT INTO events (op, path, sha256, created_at) VALUES (?,?,?,?)",
        ("write", rel, sha, now),
    )


def record_secret_hits(project_root: Path, rel: str, hits: list[dict[str, Any]]) -> None:
    path = db_path(project_root)
    if not path.is_file():
        return
    conn = _connect(path)
    try:
        now = core.utc_now()
        conn.executemany(
            "INSERT INTO secrets_hits (path, rule, created_at) VALUES (?,?,?)",
            [(rel, h.get("rule", "unknown"), now) for h in hits],
        )
        conn.execute(
            "INSERT INTO events (op, path, sha256, created_at) VALUES (?,?,?,?)",
            ("secret_reject", rel, "", now),
        )
        conn.commit()
    finally:
        conn.close()


def fts_query(raw: str) -> str:
    tokens = _FTS_TOKEN.findall(raw)
    if not tokens:
        raise core.MemoryError("bad_query", "Query has no searchable tokens.", query=raw)
    return " OR ".join('"' + t + '"' for t in tokens)


def search(project_root: Path, query: str, limit: int = 20) -> dict[str, Any]:
    path = require_db(project_root)
    conn = _connect(path)
    try:
        match = fts_query(query)
        rows = conn.execute(
            "SELECT e.scope, e.slug, e.class, e.path, e.sha256, e.updated_at, "
            "snippet(entries_fts, 1, '[', ']', '…', 12) AS snippet, "
            "bm25(entries_fts) AS score "
            "FROM entries_fts JOIN entries e ON e.id = entries_fts.rowid "
            "WHERE entries_fts MATCH ? ORDER BY score LIMIT ?",
            (match, limit),
        ).fetchall()
        return {
            "query": query,
            "match": match,
            "count": len(rows),
            "results": [
                {
                    "scope": r["scope"],
                    "slug": r["slug"],
                    "class": r["class"],
                    "path": r["path"],
                    "sha256": r["sha256"],
                    "updated_at": r["updated_at"],
                    "snippet": r["snippet"],
                    "score": r["score"],
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


def remove_entry(project_root: Path, rel: str) -> None:
    path = require_db(project_root)
    conn = _connect(path)
    try:
        conn.execute("DELETE FROM files WHERE path = ?", (rel,))
        conn.execute("DELETE FROM entries WHERE path = ?", (rel,))
        conn.execute(
            "INSERT INTO events (op, path, sha256, created_at) VALUES (?,?,?,?)",
            ("forget", rel, "", core.utc_now()),
        )
        conn.commit()
    finally:
        conn.close()


def reindex(project_root: Path, store: Path) -> dict[str, Any]:
    path = require_db(project_root)
    conn = _connect(path)
    rebuilt = 0
    skipped_secrets: list[str] = []
    try:
        conn.execute("DELETE FROM files")
        conn.execute("DELETE FROM entries")
        for f in core.glob_store(store, "**/*.md"):
            rel = f.relative_to(store.resolve()).as_posix()
            text = core.read_text(f)
            hits = core.scan_secrets(text)
            if hits:
                skipped_secrets.append(rel)
                now = core.utc_now()
                conn.executemany(
                    "INSERT INTO secrets_hits (path, rule, created_at) VALUES (?,?,?)",
                    [(rel, h["rule"], now) for h in hits],
                )
                continue
            upsert_entry(conn, rel, text)
            rebuilt += 1
        conn.execute(
            "INSERT INTO events (op, path, sha256, created_at) VALUES (?,?,?,?)",
            ("reindex", "", "", core.utc_now()),
        )
        conn.commit()
        return {
            "rebuilt": rebuilt,
            "skipped_secrets": skipped_secrets,
            "db": str(path),
            "sqlite_vec": vec_available(conn),
        }
    finally:
        conn.close()


def sidecar_violations(project_root: Path) -> list[dict[str, Any]]:
    path = db_path(project_root)
    out: list[dict[str, Any]] = []
    for suffix in ("-wal", "-shm"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists():
            out.append({"code": "sidecar_detected", "path": sidecar.name})
    return out
