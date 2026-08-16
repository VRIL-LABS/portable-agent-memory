"""Executable sandbox assertion. Binary pass/fail. Do not interpret."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import cli, core


def _run(argv: list[str]) -> tuple[int, dict]:
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(argv)
    text = buf.getvalue()
    data = json.loads(text)
    return code, data


def run_selftest() -> dict:
    checks: list[dict] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(cond), "detail": detail})

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "proj"
        root.mkdir()
        (root / ".git").mkdir()

        code, data = _run(["--root", str(root), "init"])
        check("init_ok", code == 0 and data.get("ok") is True)
        store = Path(data["memory_root"])
        check("marker_exists", (store / core.MARKER_NAME).is_file())
        check("user_index", (store / "user" / "MEMORY.md").is_file())
        check("team_index", (store / "team" / "MEMORY.md").is_file())

        db = root / ".memsys-db"
        check("db_created", db.is_file())
        check("db_no_wal", not (root / ".memsys-db-wal").exists())
        check("db_no_shm", not (root / ".memsys-db-shm").exists())
        check("init_reports_fts5", data.get("db", {}).get("fts5") is True)
        check("init_journal_delete", data.get("db", {}).get("journal_mode") == "delete")

        code, data = _run(["--root", str(root), "glob", "**/*.md"])
        check("glob_lists_indexes", code == 0 and data.get("count", 0) >= 2, str(data.get("count")))

        # bash-style emptiness is irrelevant; glob is source of truth
        check("glob_not_empty", data["count"] > 0)

        code, data = _run(
            [
                "--root",
                str(root),
                "write",
                "user/architecture.md",
                "--content",
                "# Architecture\n\nUse Envoy as the edge proxy.\n",
            ]
        )
        check("write_topic", code == 0 and data.get("ok") is True, data.get("error", {}).get("code", ""))
        sha = data["file"]["sha256"]

        code, data = _run(["--root", str(root), "search", "Envoy proxy"])
        check("search_finds_write", code == 0 and data.get("count", 0) >= 1, str(data.get("count")))
        check(
            "search_hit_path",
            any(r.get("path") == "user/architecture.md" for r in data.get("results", [])),
        )
        code, data = _run(["--root", str(root), "search", '"; DROP TABLE entries; --'])
        check(
            "search_injection_safe",
            code == 0 and data.get("count") == 0 and "DROP" in data.get("match", ""),
            str(data.get("match")),
        )
        code, data = _run(["--root", str(root), "search", '"; --'])
        check("search_bad_query", data.get("ok") is False and data.get("error", {}).get("code") == "bad_query")
        code, data = _run(["--root", str(root), "search", "zzz_nonexistent_token_qqq"])
        check("search_miss_ok", code == 0 and data.get("count") == 0)

        code, data = _run(["--root", str(root), "read", "user/architecture.md"])
        check("read_verifies", code == 0 and data["file"]["sha256"] == sha)

        code, data = _run(
            [
                "--root",
                str(root),
                "edit",
                "user/architecture.md",
                "--old",
                "Envoy as the edge proxy",
                "--new",
                "Envoy + a local sidecar",
            ]
        )
        check("edit_exact", code == 0 and data.get("ok") is True)

        code, data = _run(
            [
                "--root",
                str(root),
                "write",
                "user/secrets.md",
                "--content",
                'password: "hunter2hunter2"\n',
            ]
        )
        check("reject_secret", code == 3 and data.get("ok") is False)

        import sqlite3
        conn = sqlite3.connect(str(db))
        n = conn.execute("SELECT COUNT(*) FROM secrets_hits").fetchone()[0]
        conn.close()
        check("secret_logged_by_rule_only", n >= 1)

        code, data = _run(["--root", str(root), "reindex"])
        check("reindex_ok", code == 0 and data.get("ok") is True and data.get("rebuilt", 0) >= 3, str(data.get("rebuilt")))

        code, data = _run(["slug", "Prefer Tabs Over Spaces!!"])
        check("slug_deterministic", code == 0 and data.get("slug") == "prefer-tabs-over-spaces")

        code, data = _run(["classify", "--text", "I prefer tabs over spaces", "--hint", "preference"])
        check("classify_index", code == 0 and data.get("class") == "index", str(data.get("class")))

        code, data = _run(
            [
                "classify",
                "--text",
                "Multi-step workflow checklist for deploying the edge proxy",
            ]
        )
        check("classify_skill", code == 0 and data.get("class") == "skill", str(data.get("class")))

        code, data = _run(
            [
                "--root",
                str(root),
                "index-link",
                "--scope",
                "user",
                "--slug",
                "architecture",
                "--filename",
                "architecture.md",
                "--summary",
                "Edge proxy decision",
            ]
        )
        check("index_link", code == 0 and data.get("ok") is True)

        code, data = _run(["--root", str(root), "validate"])
        check("validate_clean", code == 0 and data.get("ok") is True, str(data.get("violations")))

        # adversarial: path traversal
        code, data = _run(["--root", str(root), "read", "../etc/passwd"])
        check("reject_traversal", data.get("ok") is False)

        # overwrite without flag fails
        code, data = _run(
            ["--root", str(root), "write", "user/architecture.md", "--content", "x\n"]
        )
        check("refuse_blind_overwrite", code == 1 and data.get("error", {}).get("code") == "exists")

        # missing store on a different root
        other = Path(td) / "empty"
        other.mkdir()
        code, data = _run(["--root", str(other), "glob"])
        check("missing_store_fails", data.get("ok") is False and data.get("error", {}).get("code") == "store_missing")

        # forget: confirm must match path, then file + ledger rows are purged
        code, data = _run(["--root", str(root), "forget", "user/architecture.md", "--confirm", "user/other.md"])
        check("forget_confirm_mismatch", code == 2 and data.get("error", {}).get("code") == "confirm_mismatch")
        check("forget_mismatch_keeps_file", (store / "user" / "architecture.md").is_file())

        code, data = _run(["--root", str(root), "forget", "user/architecture.md", "--confirm", "user/architecture.md"])
        check("forget_ok", code == 0 and data.get("ok") is True)
        check("forget_removes_file", not (store / "user" / "architecture.md").exists())
        code, data = _run(["--root", str(root), "search", "Envoy"])
        check("forget_purges_ledger", code == 0 and data.get("count") == 0, str(data.get("count")))
        code, data = _run(["--root", str(root), "forget", "user/architecture.md", "--confirm", "user/architecture.md"])
        check("forget_missing_404", code == 4 and data.get("error", {}).get("code") == "not_found")
        check("db_still_single_file", not (root / ".memsys-db-wal").exists() and not (root / ".memsys-db-shm").exists())

    failed = [c for c in checks if not c["ok"]]
    return {
        "ok": len(failed) == 0,
        "passed": sum(1 for c in checks if c["ok"]),
        "failed": len(failed),
        "checks": checks,
    }
