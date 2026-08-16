#!/usr/bin/env python3
"""CLI source of truth. Never override, recalculate, or reformat its JSON."""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from .constants import (
    DB_NAME,
    DEFAULT_SCOPE,
    EXIT_AMBIGUOUS,
    EXIT_FAIL,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_SECRET,
    EXIT_USAGE,
    INDEX_NAME,
    SCHEMA,
    SCOPES,
    SKILL_NAME,
    STORE_DIRNAME,
)
from . import core
from . import ledger


def _emit(payload: dict[str, Any], exit_code: int) -> int:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return exit_code


def _base(op: str, started: float, **kw: Any) -> dict[str, Any]:
    out = {
        "skill": SKILL_NAME,
        "schema": SCHEMA,
        "op": op,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "warnings": [],
    }
    out.update(kw)
    return out


def _root_from_args(args: argparse.Namespace) -> Path:
    if getattr(args, "root", None):
        return Path(args.root).resolve()
    start = Path(args.cwd).resolve() if getattr(args, "cwd", None) else Path.cwd()
    return core.discover_project_root(start)


def cmd_root(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.memory_root(project)
    exists = (store / core.MARKER_NAME).is_file()
    return _emit(
        _base(
            "root",
            started,
            ok=True,
            project_root=str(project),
            memory_root=str(store),
            initialized=exists,
        ),
        EXIT_OK,
    )


def cmd_init(args: argparse.Namespace, started: float) -> int:
    if getattr(args, "root", None):
        project = Path(args.root).resolve()
    elif getattr(args, "cwd", None):
        project = Path(args.cwd).resolve()
    else:
        try:
            project = core.discover_project_root(Path.cwd())
        except core.MemoryError:
            project = Path.cwd().resolve()
    result = core.init_store(project, project_name=args.project_name)
    result["db"] = ledger.init_db(project)
    return _emit(
        _base("init", started, ok=True, project_root=str(project), **result),
        EXIT_OK,
    )


def cmd_glob(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    files = core.glob_store(store, args.pattern)
    recs = []
    for f in files:
        rec = core.file_record(f, store)
        rec.pop("abs", None)
        recs.append(rec)
    return _emit(
        _base(
            "glob",
            started,
            ok=True,
            project_root=str(project),
            memory_root=str(store),
            pattern=args.pattern,
            count=len(recs),
            files=recs,
        ),
        EXIT_OK,
    )


def cmd_read(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    path = core.resolve_in_store(store, args.path)
    if not path.is_file():
        return _emit(
            _base(
                "read",
                started,
                ok=False,
                error={"code": "not_found", "path": args.path},
            ),
            EXIT_NOT_FOUND,
        )
    text = core.read_text(path)
    rec = core.file_record(path, store, text)
    return _emit(
        _base("read", started, ok=True, file=rec, content=text),
        EXIT_OK,
    )


def cmd_write(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    rel = args.path
    if args.scope:
        if args.scope not in SCOPES:
            return _emit(
                _base("write", started, ok=False, error={"code": "bad_scope"}),
                EXIT_USAGE,
            )
        if not rel.startswith(args.scope + "/"):
            rel = f"{args.scope}/{rel}"
    path = core.resolve_in_store(store, rel)
    content = args.content
    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
    if content is None:
        return _emit(
            _base("write", started, ok=False, error={"code": "missing_content"}),
            EXIT_USAGE,
        )
    hits = core.scan_secrets(content)
    if hits:
        ledger.record_secret_hits(project, rel, hits)
        return _emit(
            _base(
                "write",
                started,
                ok=False,
                error={"code": "secret_detected", "hits": hits},
            ),
            EXIT_SECRET,
        )
    existed = path.is_file()
    if existed and not args.overwrite:
        return _emit(
            _base(
                "write",
                started,
                ok=False,
                error={"code": "exists", "path": rel, "hint": "Read first, then pass --overwrite"},
            ),
            EXIT_FAIL,
        )
    core.write_text_atomic(path, content)
    verify = core.read_text(path)
    rec = core.file_record(path, store, verify)
    if rec["sha256"] != core.sha256_text(content):
        return _emit(
            _base("write", started, ok=False, error={"code": "verify_mismatch"}),
            EXIT_FAIL,
        )
    ledger.upsert_entry_from_path(project, rel, verify)
    warnings = []
    if path.name == INDEX_NAME and rec["lines"] > core.INDEX_MAX_LINES:
        warnings.append(
            {
                "code": "index_too_long",
                "lines": rec["lines"],
                "max": core.INDEX_MAX_LINES,
            }
        )
    return _emit(
        _base(
            "write",
            started,
            ok=True,
            overwritten=existed,
            file=rec,
            warnings=warnings,
        ),
        EXIT_OK,
    )


def cmd_edit(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    path = core.resolve_in_store(store, args.path)
    if not path.is_file():
        return _emit(
            _base("edit", started, ok=False, error={"code": "not_found", "path": args.path}),
            EXIT_NOT_FOUND,
        )
    original = core.read_text(path)
    try:
        updated = core.apply_edit(original, args.old, args.new, replace_all=args.all)
    except core.MemoryError as exc:
        code = EXIT_AMBIGUOUS if exc.code == "edit_ambiguous" else EXIT_FAIL
        return _emit(
            _base("edit", started, ok=False, error={"code": exc.code, "message": exc.message, **exc.extra}),
            code,
        )
    hits = core.scan_secrets(updated)
    if hits:
        ledger.record_secret_hits(project, args.path, hits)
        return _emit(
            _base("edit", started, ok=False, error={"code": "secret_detected", "hits": hits}),
            EXIT_SECRET,
        )
    core.write_text_atomic(path, updated)
    verify = core.read_text(path)
    rec = core.file_record(path, store, verify)
    if rec["sha256"] != core.sha256_text(updated):
        return _emit(
            _base("edit", started, ok=False, error={"code": "verify_mismatch"}),
            EXIT_FAIL,
        )
    ledger.upsert_entry_from_path(project, rec["path"], verify)
    return _emit(_base("edit", started, ok=True, file=rec, replacements=original.count(args.old) if args.all else 1), EXIT_OK)


def cmd_validate(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    result = core.validate_store(store)
    result["violations"].extend(ledger.sidecar_violations(project))
    result["ok"] = len(result["violations"]) == 0
    return _emit(
        _base("validate", started, project_root=str(project), memory_root=str(store), **result),
        EXIT_OK if result["ok"] else EXIT_FAIL,
    )


def cmd_status(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    inv = core.inventory(store)
    val = core.validate_store(store)
    return _emit(
        _base(
            "status",
            started,
            ok=val["ok"],
            project_root=str(project),
            memory_root=str(store),
            inventory=inv,
            violations=val["violations"],
        ),
        EXIT_OK if val["ok"] else EXIT_FAIL,
    )


def cmd_classify(args: argparse.Namespace, started: float) -> int:
    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    if text is None:
        return _emit(_base("classify", started, ok=False, error={"code": "missing_text"}), EXIT_USAGE)
    result = core.classify(text, hint=args.hint)
    slug = None
    if result["ok"] and args.title:
        slug = core.slugify(args.title)
    return _emit(_base("classify", started, slug=slug, **result), EXIT_OK if result["ok"] else EXIT_SECRET)


def cmd_slug(args: argparse.Namespace, started: float) -> int:
    try:
        slug = core.slugify(args.text)
    except core.MemoryError as exc:
        return _emit(
            _base("slug", started, ok=False, error={"code": exc.code, "message": exc.message}),
            EXIT_FAIL,
        )
    return _emit(_base("slug", started, ok=True, slug=slug, input=args.text), EXIT_OK)


def cmd_scan(args: argparse.Namespace, started: float) -> int:
    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    if text is None:
        return _emit(_base("scan-secrets", started, ok=False, error={"code": "missing_text"}), EXIT_USAGE)
    hits = core.scan_secrets(text)
    return _emit(
        _base("scan-secrets", started, ok=len(hits) == 0, hits=hits),
        EXIT_OK if not hits else EXIT_SECRET,
    )


def cmd_index_link(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    if args.scope not in SCOPES:
        return _emit(_base("index-link", started, ok=False, error={"code": "bad_scope"}), EXIT_USAGE)
    path = store / args.scope / INDEX_NAME
    if not path.is_file():
        return _emit(_base("index-link", started, ok=False, error={"code": "not_found"}), EXIT_NOT_FOUND)
    original = core.read_text(path)
    slug = core.slugify(args.slug)
    updated = core.upsert_index_link(original, slug, args.filename, args.summary, args.section)
    hits = core.scan_secrets(updated)
    if hits:
        return _emit(_base("index-link", started, ok=False, error={"code": "secret_detected", "hits": hits}), EXIT_SECRET)
    if len(updated.splitlines()) > core.INDEX_MAX_LINES:
        return _emit(
            _base(
                "index-link",
                started,
                ok=False,
                error={"code": "index_too_long", "lines": len(updated.splitlines()), "max": core.INDEX_MAX_LINES},
            ),
            EXIT_FAIL,
        )
    core.write_text_atomic(path, updated)
    rec = core.file_record(path, store, updated)
    return _emit(_base("index-link", started, ok=True, file=rec, slug=slug), EXIT_OK)


def cmd_search(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    core.require_store(project)
    try:
        result = ledger.search(project, args.query, limit=args.limit)
    except core.MemoryError as exc:
        if exc.code == "bad_query":
            code = EXIT_USAGE
        elif exc.code == "db_missing":
            code = EXIT_NOT_FOUND
        else:
            code = EXIT_FAIL
        return _emit(
            _base("search", started, ok=False, error={"code": exc.code, "message": exc.message, **exc.extra}),
            code,
        )
    return _emit(_base("search", started, ok=True, **result), EXIT_OK)


def cmd_reindex(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    result = ledger.reindex(project, store)
    return _emit(
        _base("reindex", started, ok=True, project_root=str(project), memory_root=str(store), **result),
        EXIT_OK,
    )


def cmd_forget(args: argparse.Namespace, started: float) -> int:
    project = _root_from_args(args)
    store = core.require_store(project)
    try:
        path_norm = core.sanitize_rel(args.path).as_posix()
        confirm_norm = core.sanitize_rel(args.confirm).as_posix()
    except core.MemoryError as exc:
        return _emit(
            _base("forget", started, ok=False, error={"code": exc.code, "message": exc.message, **exc.extra}),
            EXIT_USAGE,
        )
    if confirm_norm != path_norm:
        # confirm_mismatch is a deliberate safety check, not a malformed
        # invocation, but protocol.md documents this case as exiting 2
        # (EXIT_USAGE) — keep the value stable for callers relying on it.
        return _emit(
            _base(
                "forget",
                started,
                ok=False,
                error={
                    "code": "confirm_mismatch",
                    "path": args.path,
                    "hint": "Pass --confirm with the exact same path. Forget is irreversible.",
                },
            ),
            EXIT_USAGE,
        )
    try:
        removed = core.remove_from_store(store, args.path)
    except core.MemoryError as exc:
        code = EXIT_NOT_FOUND if exc.code == "not_found" else EXIT_FAIL
        return _emit(
            _base("forget", started, ok=False, error={"code": exc.code, "message": exc.message, **exc.extra}),
            code,
        )
    if ledger.db_path(project).is_file():
        ledger.remove_entry(project, removed["path"])
    return _emit(_base("forget", started, ok=True, removed=removed), EXIT_OK)


def cmd_selftest(args: argparse.Namespace, started: float) -> int:
    from .selftest import run_selftest
    result = run_selftest()
    return _emit(_base("selftest", started, **result), EXIT_OK if result["ok"] else EXIT_FAIL)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="memory_tool",
        description="Portable project-local memory store. JSON to stdout. Never use bash ls.",
    )
    p.add_argument("--cwd", default=None, help="Starting directory for root discovery")
    p.add_argument("--root", default=None, help="Explicit project root (skips discovery)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("root", help="Resolve project and memory roots")
    init_p = sub.add_parser("init", help="Create memories/ layout in the project")
    init_p.add_argument("--project-name", default=None)

    g = sub.add_parser("glob", help="Enumerate store files (the reliable listing)")
    g.add_argument("pattern", nargs="?", default="**/*")

    r = sub.add_parser("read", help="Read a store file and return content + checksum")
    r.add_argument("path")

    w = sub.add_parser("write", help="Create or overwrite a store file after secret scan")
    w.add_argument("path")
    w.add_argument("--content", default=None)
    w.add_argument("--content-file", default=None)
    w.add_argument("--scope", choices=SCOPES, default=None)
    w.add_argument("--overwrite", action="store_true")

    e = sub.add_parser("edit", help="Exact-string replace inside a store file")
    e.add_argument("path")
    e.add_argument("--old", required=True)
    e.add_argument("--new", required=True)
    e.add_argument("--all", action="store_true")

    sub.add_parser("validate", help="Binary store validation")
    sub.add_parser("status", help="Inventory + validation")

    c = sub.add_parser("classify", help="Deterministic skill vs index vs topic")
    c.add_argument("--text", default=None)
    c.add_argument("--text-file", default=None)
    c.add_argument("--hint", default=None)
    c.add_argument("--title", default=None)

    s = sub.add_parser("slug", help="Deterministic slug")
    s.add_argument("text")

    sc = sub.add_parser("scan-secrets", help="Scan text for secret patterns")
    sc.add_argument("--text", default=None)
    sc.add_argument("--text-file", default=None)

    il = sub.add_parser("index-link", help="Upsert a MEMORY.md bullet")
    il.add_argument("--scope", default=DEFAULT_SCOPE, choices=SCOPES)
    il.add_argument("--slug", required=True)
    il.add_argument("--filename", required=True)
    il.add_argument("--summary", required=True)
    il.add_argument("--section", default="Topics", choices=("Topics", "Skills"))

    se = sub.add_parser("search", help="FTS5 search over the .memsys-db ledger")
    se.add_argument("query")
    se.add_argument("--limit", type=int, default=20)

    sub.add_parser("reindex", help="Rebuild .memsys-db from markdown on disk")

    fg = sub.add_parser("forget", help="Irreversibly delete a store file + ledger rows")
    fg.add_argument("path")
    fg.add_argument("--confirm", required=True)

    sub.add_parser("selftest", help="Run the bundled sandbox assertion")
    return p


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_USAGE
        if code == 0:
            return 0
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "skill": SKILL_NAME,
                    "op": "parse",
                    "error": {"code": "usage", "message": "invalid arguments"},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return EXIT_USAGE
    dispatch = {
        "root": cmd_root,
        "init": cmd_init,
        "glob": cmd_glob,
        "read": cmd_read,
        "write": cmd_write,
        "edit": cmd_edit,
        "validate": cmd_validate,
        "status": cmd_status,
        "classify": cmd_classify,
        "slug": cmd_slug,
        "scan-secrets": cmd_scan,
        "index-link": cmd_index_link,
        "search": cmd_search,
        "reindex": cmd_reindex,
        "forget": cmd_forget,
        "selftest": cmd_selftest,
    }
    try:
        return dispatch[args.cmd](args, started)
    except core.MemoryError as exc:
        return _emit(
            _base(args.cmd, started, ok=False, error={"code": exc.code, "message": exc.message, **exc.extra}),
            EXIT_NOT_FOUND if exc.code in {"store_missing", "no_project_root"} else EXIT_FAIL,
        )
    except Exception as exc:  # noqa: BLE001 — surface raw error, do not interpret as success
        return _emit(
            _base(
                getattr(args, "cmd", "unknown"),
                started,
                ok=False,
                error={"code": "internal", "type": type(exc).__name__, "message": str(exc), "trace": traceback.format_exc()},
            ),
            EXIT_FAIL,
        )


if __name__ == "__main__":
    raise SystemExit(main())
