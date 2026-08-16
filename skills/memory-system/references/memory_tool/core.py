"""Deterministic memory-store operations. Source of truth. Do not reinterpret."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .constants import (
    CLASS_INDEX_HINTS,
    CLASS_SKILL_HINTS,
    DB_NAME,
    DEFAULT_SCOPE,
    INDEX_MAX_LINES,
    INDEX_NAME,
    MARKER_NAME,
    PROJECT_MARKERS,
    SCHEMA,
    SCOPES,
    SECRET_RULES,
    SKILL_FILENAME,
    SKILLS_DIRNAME,
    SLUG_MAX,
    STORE_DIRNAME,
)

_SECRET_COMPILED = tuple((name, re.compile(pat)) for name, pat in SECRET_RULES)
_SLUG_SAFE = re.compile(r"[^a-z0-9]+")
_INJECTION = re.compile(r"[\x00-\x1f]|[<>]|`|\$\(")


class MemoryError(Exception):
    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def discover_project_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    if cur.is_file():
        cur = cur.parent
    found_marker = None
    found_project = None
    for candidate in [cur, *cur.parents]:
        store = candidate / STORE_DIRNAME
        if (store / MARKER_NAME).is_file() or store.is_dir():
            found_marker = candidate
            break
        if any((candidate / m).exists() for m in PROJECT_MARKERS):
            found_project = candidate
            break
    if found_marker:
        return found_marker
    if found_project:
        return found_project
    raise MemoryError(
        "no_project_root",
        "No project root found. Run init from the project directory or pass --root.",
        start=str(cur),
    )


def memory_root(project_root: Path) -> Path:
    return project_root.resolve() / STORE_DIRNAME


def require_store(project_root: Path) -> Path:
    root = memory_root(project_root)
    marker = root / MARKER_NAME
    if not root.is_dir() or not marker.is_file():
        raise MemoryError(
            "store_missing",
            f"Memory store not initialized at {root}. Run: memory_tool init",
            memory_root=str(root),
        )
    return root


def sanitize_rel(rel: str) -> Path:
    if not rel or rel.strip() != rel:
        raise MemoryError("bad_path", "Path must be non-empty and unpadded.", path=rel)
    if _INJECTION.search(rel):
        raise MemoryError("bad_path", "Path contains control or injection characters.", path=rel)
    raw = Path(rel.replace("\\", "/"))
    if raw.is_absolute() or any(part in ("..", "") for part in raw.parts):
        raise MemoryError("bad_path", "Path must be store-relative with no traversal.", path=rel)
    if raw.parts and raw.parts[0] == STORE_DIRNAME:
        raw = Path(*raw.parts[1:])
    return raw


def resolve_in_store(store: Path, rel: str) -> Path:
    target = (store / sanitize_rel(rel)).resolve()
    store_r = store.resolve()
    if target != store_r and store_r not in target.parents:
        raise MemoryError("path_escape", "Resolved path escaped the memory store.", path=rel)
    return target


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_SAFE.sub("-", norm.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    if not slug:
        raise MemoryError("bad_slug", "Could not derive a slug from input.", input=text)
    if len(slug) > SLUG_MAX:
        slug = slug[:SLUG_MAX].rstrip("-")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise MemoryError("bad_slug", "Slug failed charset contract.", slug=slug)
    return slug


def scan_secrets(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for name, cre in _SECRET_COMPILED:
        for m in cre.finditer(text):
            hits.append({"rule": name, "start": m.start(), "end": m.end()})
    return hits


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def file_record(path: Path, store: Path, content: str | None = None) -> dict[str, Any]:
    text = content if content is not None else read_text(path)
    rel = path.resolve().relative_to(store.resolve()).as_posix()
    lines = text.splitlines()
    return {
        "path": rel,
        "abs": str(path.resolve()),
        "bytes": len(text.encode("utf-8")),
        "lines": len(lines),
        "sha256": sha256_text(text),
        "exists": True,
    }


def glob_store(store: Path, pattern: str = "**/*") -> list[Path]:
    pat = pattern.replace("\\", "/")
    if pat.startswith(STORE_DIRNAME + "/"):
        pat = pat[len(STORE_DIRNAME) + 1 :]
    if pat.startswith("/"):
        raise MemoryError("bad_path", "Glob pattern must be store-relative.", path=pattern)
    matches: list[Path] = []
    store_r = store.resolve()
    for p in store_r.rglob("*"):
        if not p.is_file():
            continue
        if p.name.endswith(".tmp"):
            continue
        rel = p.relative_to(store_r).as_posix()
        if Path(rel).match(pat) or _glob_match(rel, pat):
            matches.append(p)
    matches.sort(key=lambda x: x.as_posix())
    return matches


def _glob_match(rel: str, pattern: str) -> bool:
    from fnmatch import fnmatch
    if fnmatch(rel, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch(rel, pattern[3:]) or fnmatch(rel.split("/")[-1], pattern[3:])
    return fnmatch(rel.split("/")[-1], pattern)


def init_store(project_root: Path, project_name: str | None = None) -> dict[str, Any]:
    store = memory_root(project_root)
    created: list[str] = []
    store.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema": SCHEMA,
        "created_at": utc_now(),
        "project_name": project_name or project_root.name,
        "scopes": list(SCOPES),
        "default_scope": DEFAULT_SCOPE,
        "index_max_lines": INDEX_MAX_LINES,
    }
    marker_path = store / MARKER_NAME
    if not marker_path.exists():
        write_text_atomic(marker_path, json.dumps(marker, indent=2) + "\n")
        created.append(MARKER_NAME)
    gitignore = store / ".gitignore"
    if not gitignore.exists():
        write_text_atomic(
            gitignore,
            "# Personal memories stay local. Team memories are shareable.\n"
            "user/\n"
            "../" + DB_NAME + "\n"
            ".DS_Store\n"
            "*.tmp\n"
            "*.secret\n",
        )
        created.append(".gitignore")
    readme = store / "README.md"
    if not readme.exists():
        write_text_atomic(readme, _STORE_README)
        created.append("README.md")
    for scope in SCOPES:
        scope_dir = store / scope
        scope_dir.mkdir(exist_ok=True)
        skills = scope_dir / SKILLS_DIRNAME
        skills.mkdir(exist_ok=True)
        keep = skills / ".gitkeep"
        if not keep.exists() and scope == "team":
            write_text_atomic(keep, "")
            created.append(f"{scope}/{SKILLS_DIRNAME}/.gitkeep")
        index = scope_dir / INDEX_NAME
        if not index.exists():
            write_text_atomic(index, index_template(scope))
            created.append(f"{scope}/{INDEX_NAME}")
    return {"memory_root": str(store), "created": created, "marker": marker}


def remove_from_store(store: Path, rel: str) -> dict[str, Any]:
    target = resolve_in_store(store, rel)
    if not target.is_file():
        raise MemoryError("not_found", "Path not found in store.", path=rel)
    record = file_record(target, store)
    record.pop("abs", None)
    target.unlink()
    return record


def index_template(scope: str) -> str:
    return (
        f"# Memory Index — {scope}\n\n"
        f"> Index only. Keep under {INDEX_MAX_LINES} lines. Link out; never embed detail.\n\n"
        "## Topics\n\n"
        "- _(none yet)_\n\n"
        "## Skills\n\n"
        "- _(none yet)_\n\n"
        f"## Last updated\n\n"
        f"{utc_now()}\n"
    )


_STORE_README = """# memories/

Project-local persistent memory for agents working in this repository.

- `user/` personal to the operator; gitignored by default
- `team/` shared with anyone who clones the repo
- `*/MEMORY.md` always-loaded index (keep short)
- `*/<topic>.md` on-demand topic notes
- `*/skills/` auto-discovered skills (`SKILL.md` required)

Enumerate with the memory_tool glob command. Never trust `ls`/`find` as proof of store state.
"""


def validate_index(path: Path) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if not path.is_file():
        return [{"code": "index_missing", "path": path.name}]
    text = read_text(path)
    lines = text.splitlines()
    if len(lines) > INDEX_MAX_LINES:
        violations.append(
            {
                "code": "index_too_long",
                "path": path.name,
                "lines": len(lines),
                "max": INDEX_MAX_LINES,
            }
        )
    if scan_secrets(text):
        violations.append({"code": "index_secret", "path": path.name})
    if not text.lstrip().startswith("#"):
        violations.append({"code": "index_no_heading", "path": path.name})
    return violations


def validate_store(store: Path) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    marker = store / MARKER_NAME
    if not marker.is_file():
        violations.append({"code": "marker_missing", "path": MARKER_NAME})
    else:
        try:
            data = json.loads(read_text(marker))
            if data.get("schema") != SCHEMA:
                violations.append({"code": "schema_mismatch", "got": data.get("schema")})
        except json.JSONDecodeError:
            violations.append({"code": "marker_invalid_json", "path": MARKER_NAME})
    for scope in SCOPES:
        scope_dir = store / scope
        if not scope_dir.is_dir():
            violations.append({"code": "scope_missing", "scope": scope})
            continue
        idx = scope_dir / INDEX_NAME
        for v in validate_index(idx):
            v["scope"] = scope
            violations.append(v)
        for f in glob_store(store, f"{scope}/**/*.md"):
            hits = scan_secrets(read_text(f))
            if hits:
                violations.append(
                    {
                        "code": "secret_detected",
                        "path": f.relative_to(store).as_posix(),
                        "hits": hits,
                    }
                )
    ok = len(violations) == 0
    return {"ok": ok, "violations": violations}


def classify(text: str, hint: str | None = None) -> dict[str, Any]:
    blob = f"{hint or ''} {text}".lower()
    if scan_secrets(text):
        return {"class": "reject", "reason": "secret_pattern", "ok": False}
    if any(k in blob for k in CLASS_SKILL_HINTS):
        return {"class": "skill", "reason": "workflow_keywords", "ok": True}
    if len(text.splitlines()) <= 2 and any(k in blob for k in CLASS_INDEX_HINTS):
        return {"class": "index", "reason": "short_preference", "ok": True}
    return {"class": "topic", "reason": "default_topic_note", "ok": True}


def apply_edit(original: str, old: str, new: str, replace_all: bool = False) -> str:
    count = original.count(old)
    if old == "":
        raise MemoryError("bad_edit", "old_string must be non-empty")
    if count == 0:
        raise MemoryError("edit_no_match", "old_string not found; exact match required")
    if count > 1 and not replace_all:
        raise MemoryError(
            "edit_ambiguous",
            "old_string matched multiple times; refuse without --all",
            matches=count,
        )
    return original.replace(old, new) if replace_all else original.replace(old, new, 1)


def upsert_index_link(index_text: str, slug: str, filename: str, summary: str, section: str) -> str:
    bullet = f"- [{slug}]({filename}) — {summary.strip() or slug}"
    lines = index_text.splitlines()
    header = f"## {section}"
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == header)
    except StopIteration:
        lines.extend(["", header, "", bullet])
        return _stamp_index("\n".join(lines) + "\n")
    i = start + 1
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].startswith(f"- [{slug}]("):
            lines[i] = bullet
            return _stamp_index("\n".join(lines) + "\n")
        i += 1
    insert_at = start + 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    if insert_at < len(lines) and lines[insert_at].strip() == "- _(none yet)_":
        lines[insert_at] = bullet
    else:
        lines.insert(insert_at, bullet)
    return _stamp_index("\n".join(lines) + "\n")


def _stamp_index(text: str) -> str:
    stamp = utc_now()
    if "## Last updated" in text:
        parts = text.split("## Last updated", 1)
        rest = parts[1]
        nl = rest.find("\n")
        tail = rest[nl + 1 :] if nl >= 0 else ""
        tail_lines = tail.splitlines()
        while tail_lines and tail_lines[0].strip() == "":
            tail_lines.pop(0)
        if tail_lines:
            tail_lines[0] = stamp
        else:
            tail_lines = [stamp]
        return parts[0] + "## Last updated\n\n" + "\n".join(tail_lines) + (
            "\n" if text.endswith("\n") else ""
        )
    return text.rstrip() + f"\n\n## Last updated\n\n{stamp}\n"


def inventory(store: Path) -> dict[str, Any]:
    files = []
    for f in glob_store(store, "**/*"):
        rec = file_record(f, store)
        rec.pop("abs", None)
        files.append(rec)
    scopes = {}
    for scope in SCOPES:
        idx = store / scope / INDEX_NAME
        topics = [
            t.relative_to(store).as_posix()
            for t in glob_store(store, f"{scope}/*.md")
            if t.name != INDEX_NAME
        ]
        skills = [
            s.relative_to(store).as_posix()
            for s in glob_store(store, f"{scope}/{SKILLS_DIRNAME}/**/{SKILL_FILENAME}")
        ]
        scopes[scope] = {
            "index_lines": len(read_text(idx).splitlines()) if idx.is_file() else 0,
            "topics": topics,
            "skills": skills,
        }
    return {"files": files, "scopes": scopes, "count": len(files)}
