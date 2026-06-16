#!/usr/bin/env python3
"""Initialize an llm-wiki instance skeleton safely."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional

from wiki_common import BASE_SCHEMA

LOCAL_TZ = timezone(timedelta(hours=8))
EXIT_CONFIG = 2
PROFILE_RE = re.compile(r"^[a-z][a-z0-9-]*$")

DIRS_WITH_GITKEEP = [
    "raw/sources",
    "wiki/sources",
    "wiki/entities",
    "wiki/topics",
    "wiki/comparisons",
    "wiki/synthesis",
    "wiki/decisions",
    "wiki/queries",
    "wiki/open-questions",
    "inbox",
    "inbox/archive/promoted",
    "inbox/archive/dropped",
    "maps",
    ".wiki",
]

GITIGNORE_LINES = [
    "# wiki 派生层（可重建，不进 Git）",
    "**/.wiki/id_index.json",
    "**/.wiki/inbox_index.json",
    "**/.wiki/normalized_alias_index.json",
    "**/.wiki/cache.json",
    "**/.wiki/search_index/",
    "**/.wiki/lightrag/",
    "!**/.wiki/schema_sync.json",
    "**/maps/graph-data.json",
    "**/maps/knowledge-graph.md",
    "**/maps/graph-insights.md",
    "# Obsidian 每机器配置",
    "**/.obsidian/workspace.json",
    "**/.obsidian/workspace-mobile.json",
]

IGNORE_LINES = [
    "# 检索优化（rg / fd 原生读 .ignore，对 agent 答疑透明；不影响 wiki_lint/graph 的 Python 扫描）。",
    "# 答疑只需 wiki/ + 上下文层（purpose/index/overview/log）；原始材料、图片、派生层、图谱不参与全文检索。",
    "# ingest 若需检索已归档原文，用 `rg --no-ignore` 或显式路径；raw/dropbox/（待处理投料）刻意保留可搜。",
    "raw/sources/",
    "raw/source_manifest.json",
    "maps/",
    ".wiki/",
]


@dataclass
class Counters:
    created: int = 0
    skipped: int = 0
    conflicts: List[str] = field(default_factory=list)
    git_root: str = "none"
    selfcheck: str = "fail"
    obsidian: str = "unchanged"
    notes: List[str] = field(default_factory=list)

    def conflict(self, path: Path, detail: str) -> None:
        self.conflicts.append(f"{path}: {detail}")


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat()


def default_capture_policy() -> dict[str, Any]:
    contract = BASE_SCHEMA["json_contracts"]["capture_policy"]
    return {
        "version": 1,
        "auto_capture": False,
        "default_visibility": contract["default_visibility"],
        "hard_redact": contract["hard_redact"],
        "soft_redact": contract["soft_redact"],
        "exclude_paths": [],
        "max_inbox_files": 100,
        "updated_at": now_iso(),
    }


def today() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


def engine_repo() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_from_engine(raw: str, engine: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = engine / path
    return path.resolve()


def write_report(counters: Counters) -> None:
    for note in counters.notes:
        print(note)
    for item in counters.conflicts:
        print(f"conflict: {item}", file=sys.stderr)
    print(f"created: {counters.created}")
    print(f"skipped: {counters.skipped}")
    print(f"conflicts: {len(counters.conflicts)}")
    print(f"git_root: {counters.git_root}")
    print(f"selfcheck: {counters.selfcheck}")
    print(f"obsidian: {counters.obsidian}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sync_report(action: str, old_sha256: Optional[str], new_sha256: str) -> None:
    print(f"old_sha256: {old_sha256 if old_sha256 is not None else 'null'}")
    print(f"new_sha256: {new_sha256}")
    print(f"action: {action}")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def read_schema_sync(sync_path: Path) -> dict[str, Any]:
    if not sync_path.exists():
        return {}
    if not sync_path.is_file():
        return {}
    try:
        data = json.loads(sync_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def schema_sync_bytes(engine_sha: str) -> bytes:
    data = {
        "version": 1,
        "last_synced_engine_sha256": engine_sha,
        "updated_at": now_iso(),
    }
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def write_schema_and_metadata(target: Path, sync_path: Path, schema_bytes: bytes, engine_sha: str) -> None:
    atomic_write_bytes(target, schema_bytes)
    atomic_write_bytes(sync_path, schema_sync_bytes(engine_sha))


def write_schema_diff(source: Path, target: Path) -> None:
    try:
        source_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        source_lines = source.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    try:
        target_lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        target_lines = target.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    diff = difflib.unified_diff(
        target_lines,
        source_lines,
        fromfile=str(target),
        tofile=str(source),
    )
    for line in diff:
        print(line, end="", file=sys.stderr)


def sync_schema(root: Path, engine: Path, *, force: bool = False) -> int:
    if not root.exists() or not root.is_dir():
        print(f"config error: --sync-schema root must exist and be a directory: {root}", file=sys.stderr)
        return EXIT_CONFIG

    source = engine / "knowledge/.wiki-schema.md"
    target = root / ".wiki-schema.md"
    sync_path = root / ".wiki/schema_sync.json"
    if not source.is_file():
        print(f"config error: engine schema template missing: {source}", file=sys.stderr)
        return EXIT_CONFIG
    if target.exists() and not target.is_file():
        print(f"config error: target .wiki-schema.md must be a file, found directory: {target}", file=sys.stderr)
        return EXIT_CONFIG
    if sync_path.exists() and not sync_path.is_file():
        print(f"config error: target schema_sync.json must be a file, found directory: {sync_path}", file=sys.stderr)
        return EXIT_CONFIG

    schema_bytes = source.read_bytes()
    new_sha = sha256_file(source)
    old_sha = sha256_file(target) if target.exists() else None

    if force:
        write_schema_and_metadata(target, sync_path, schema_bytes, new_sha)
        write_sync_report("created" if old_sha is None else "forced", old_sha, new_sha)
        return 0

    if old_sha is None:
        write_schema_and_metadata(target, sync_path, schema_bytes, new_sha)
        write_sync_report("created", old_sha, new_sha)
        return 0

    sync_data = read_schema_sync(sync_path)
    last_synced = sync_data.get("last_synced_engine_sha256")

    if old_sha == new_sha:
        if last_synced != new_sha:
            atomic_write_bytes(sync_path, schema_sync_bytes(new_sha))
            write_sync_report("metadata_repaired", old_sha, new_sha)
            return 0
        write_sync_report("unchanged", old_sha, new_sha)
        return 0

    if isinstance(last_synced, str) and old_sha == last_synced:
        write_schema_and_metadata(target, sync_path, schema_bytes, new_sha)
        write_sync_report("replaced", old_sha, new_sha)
        return 0

    write_sync_report("refused", old_sha, new_sha)
    print(
        "sync refused: .wiki-schema.md differs from the engine template and has no matching last-synced record; rerun with --force after moving instance-specific notes to purpose.md/AGENTS.md/capture_policy/profile.",
        file=sys.stderr,
    )
    write_schema_diff(source, target)
    return 1


def create_root(root: Path, counters: Counters) -> bool:
    if root.exists():
        if root.is_dir():
            counters.skipped += 1
            return True
        counters.conflict(root, "root path exists but is not a directory")
        return False
    try:
        root.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        counters.conflict(root, f"cannot create root directory: {exc}")
        return False
    counters.created += 1
    return True


def required_file_paths(root: Path, profile: Optional[str]) -> List[Path]:
    paths = [
        root / "purpose.md",
        root / "index.md",
        root / "overview.md",
        root / "log.md",
        root / ".ignore",
        root / ".wiki-schema.md",
        root / "raw/source_manifest.json",
        root / ".wiki/review_queue.json",
        root / ".wiki/capture_policy.json",
    ]
    if profile:
        paths.append(root / ".wiki-profile.json")
    paths.extend(root / rel / ".gitkeep" for rel in DIRS_WITH_GITKEEP)
    return paths


def collect_type_conflicts(root: Path, dirs: Iterable[str], files: Iterable[Path], counters: Counters) -> bool:
    root = root.resolve()
    planned_dirs = [root / rel for rel in dirs]
    all_targets = planned_dirs + list(files)
    for target in all_targets:
        try:
            rel_parts = target.relative_to(root).parts
        except ValueError:
            counters.conflict(target, "planned path escapes instance root")
            continue
        current = root
        for part in rel_parts[:-1]:
            current = current / part
            if current.exists() and not current.is_dir():
                counters.conflict(current, "parent path must be a directory")
                break
    for directory in planned_dirs:
        if directory.exists() and not directory.is_dir():
            counters.conflict(directory, "expected directory but found file")
    for path in files:
        if path.exists() and not path.is_file():
            counters.conflict(path, "expected file but found directory")
    return not counters.conflicts


def ensure_dir(path: Path, counters: Counters) -> None:
    if path.exists():
        counters.skipped += 1
        return
    path.mkdir(parents=True, exist_ok=False)
    counters.created += 1


def ensure_text_file(path: Path, text: str, counters: Counters) -> bool:
    if path.exists():
        counters.skipped += 1
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    counters.created += 1
    return True


def ensure_json_file(path: Path, data: Any, counters: Counters) -> bool:
    if path.exists():
        counters.skipped += 1
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    counters.created += 1
    return True


def ensure_lines_file(path: Path, lines: List[str], counters: Counters, label: str) -> bool:
    existing_text = ""
    if path.exists():
        if not path.is_file():
            counters.conflict(path, f"expected {label} file but found directory")
            return False
        existing_text = path.read_text(encoding="utf-8")
        counters.skipped += 1
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        counters.created += 1

    existing_lines = set(existing_text.splitlines())
    missing = [line for line in lines if line not in existing_lines]
    if missing:
        prefix = "" if not existing_text or existing_text.endswith("\n") else "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(prefix)
            f.write("\n".join(missing))
            f.write("\n")
        counters.created += len(missing)
    else:
        counters.skipped += len(lines)
    return True


def copy_schema(root: Path, engine: Path, counters: Counters) -> bool:
    target = root / ".wiki-schema.md"
    if target.exists():
        counters.skipped += 1
        return True
    source = engine / "knowledge/.wiki-schema.md"
    if not source.is_file():
        counters.conflict(source, "engine schema template missing")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    counters.created += 1
    return True


def create_skeleton(root: Path, engine: Path, profile: Optional[str], counters: Counters) -> bool:
    for rel in DIRS_WITH_GITKEEP:
        ensure_dir(root / rel, counters)
        ensure_text_file(root / rel / ".gitkeep", "", counters)

    instance_name = root.name or "knowledge"
    date = today()
    profile_name = profile or "base"
    ensure_text_file(root / "purpose.md", f"# Purpose\n\n> {instance_name} 知识库目的(占位,待填)。\n", counters)
    ensure_text_file(
        root / "index.md",
        "# Index\n\n"
        "知识库入口。\n\n"
        "## 主题\n\n"
        "（随知识增长，在此用 `[[slug|标题]]` 链接各页）\n\n"
        "## 导航\n\n"
        "- [Purpose](purpose.md) — 知识库目的\n"
        "- [Overview](overview.md) — 主题总览\n"
        "- [Log](log.md) — 变更日志\n",
        counters,
    )
    ensure_text_file(
        root / "overview.md",
        "# Overview\n\n"
        "> 这个知识库目前包含什么、围绕什么主题展开。\n\n"
        "## 主题\n\n"
        "（待填）\n\n"
        "## 健康度\n\n"
        "| 指标 | 当前值 |\n"
        "| --- | --- |\n"
        "| wiki 页面 | 0 |\n",
        counters,
    )
    ensure_text_file(
        root / "log.md",
        f"# Log\n\n## {date} · Initialized\n\nInitialized by wiki_init (engine: llm-wiki, profile: {profile_name})。\n",
        counters,
    )
    if not copy_schema(root, engine, counters):
        return False

    if not ensure_lines_file(root / ".ignore", IGNORE_LINES, counters, ".ignore"):
        return False
    ensure_json_file(root / "raw/source_manifest.json", {"version": 1, "sources": []}, counters)
    ensure_json_file(root / ".wiki/review_queue.json", {"version": 1, "items": []}, counters)
    ensure_json_file(root / ".wiki/capture_policy.json", default_capture_policy(), counters)
    if profile:
        ensure_json_file(
            root / ".wiki-profile.json",
            {
                "schema_version": 1,
                "profile": profile,
                "description": "",
                "extra_page_types": [],
                "extra_field_enums": {},
                "extra_optional_fields": {},
            },
            counters,
        )
    return True


def ensure_obsidian_app(root: Path, counters: Counters) -> bool:
    obsidian_dir = root / ".obsidian"
    app_path = obsidian_dir / "app.json"
    required = ["maps/", ".wiki/"]
    if not obsidian_dir.exists():
        obsidian_dir.mkdir(parents=True, exist_ok=True)
        counters.created += 1
    elif not obsidian_dir.is_dir():
        counters.conflict(obsidian_dir, "expected .obsidian directory but found file")
        return False

    if not app_path.exists():
        ensure_json_file(app_path, {"userIgnoreFilters": required}, counters)
        counters.obsidian = "created"
        return True
    if not app_path.is_file():
        counters.conflict(app_path, "expected app.json file but found directory")
        return False

    try:
        with app_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        counters.conflict(app_path, f"invalid JSON: {exc}")
        return False

    if not isinstance(data, dict):
        counters.conflict(app_path, "app.json top-level value must be an object")
        return False

    current = data.get("userIgnoreFilters")
    if current is None:
        data["userIgnoreFilters"] = list(required)
        changed = True
    elif isinstance(current, list):
        changed = False
        for item in required:
            if item not in current:
                current.append(item)
                changed = True
    else:
        counters.conflict(app_path, "userIgnoreFilters must be a list")
        return False

    if changed:
        with app_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        counters.obsidian = "merged"
    else:
        counters.skipped += 1
        counters.obsidian = "unchanged"
    return True


def is_inside(path: Path, parent: Path) -> bool:
    return path == parent or path.is_relative_to(parent)


def run_git(args: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)


def ensure_git(root: Path, raw_git_root: Optional[str], engine: Path, counters: Counters) -> bool:
    git_root = resolve_from_engine(raw_git_root, engine) if raw_git_root else root
    counters.git_root = str(git_root)
    if not is_inside(root, git_root):
        counters.notes.append(f"git error: root is not inside git_root: root={root} git_root={git_root}")
        return False
    if git_root.exists() and not git_root.is_dir():
        counters.conflict(git_root, "git_root exists but is not a directory")
        return False
    git_root.mkdir(parents=True, exist_ok=True)

    probe = run_git(["rev-parse", "--show-toplevel"], git_root)
    if probe.returncode != 0:
        init = run_git(["init"], git_root)
        if init.returncode != 0:
            counters.notes.append("git error: git init failed; skeleton changes are not rolled back")
            if init.stderr.strip():
                counters.notes.append(init.stderr.strip())
            return False
        probe = run_git(["rev-parse", "--show-toplevel"], git_root)
    if probe.returncode != 0:
        counters.notes.append("git error: git rev-parse --show-toplevel failed; skeleton changes are not rolled back")
        if probe.stderr.strip():
            counters.notes.append(probe.stderr.strip())
        return False

    actual = probe.stdout.strip()
    if actual:
        counters.git_root = actual
        counters.notes.append(f"git repo: {actual}")
    return ensure_gitignore(git_root, counters)


def ensure_gitignore(git_root: Path, counters: Counters) -> bool:
    return ensure_lines_file(git_root / ".gitignore", GITIGNORE_LINES, counters, ".gitignore")


def run_selfcheck(root: Path, engine: Path, counters: Counters) -> bool:
    lint = engine / "scripts/wiki_lint.py"
    result = subprocess.run(
        [sys.executable, str(lint), "--root", str(root), "--check-only"],
        cwd=engine,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        counters.selfcheck = "ok"
        return True
    counters.selfcheck = "fail"
    counters.notes.append("selfcheck failed: wiki_lint returned non-zero")
    if result.stdout.strip():
        counters.notes.append(result.stdout.strip())
    if result.stderr.strip():
        counters.notes.append(result.stderr.strip())
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize an llm-wiki instance skeleton safely.")
    parser.add_argument("--root", required=True, help="实例根目录；相对路径按引擎仓库根解析")
    parser.add_argument("--profile", help="创建最小 .wiki-profile.json 模板")
    parser.add_argument("--git", action="store_true", help="确保实例进入 git，并写入派生层 .gitignore")
    parser.add_argument("--git-root", help="git repo 根目录；相对路径按引擎仓库根解析")
    parser.add_argument("--sync-schema", action="store_true", help="仅同步 .wiki-schema.md 镜像文档并退出")
    parser.add_argument("--force", action="store_true", help="仅用于 --sync-schema：跳过本地修改保护并覆盖 .wiki-schema.md")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    engine = engine_repo()
    root = resolve_from_engine(args.root, engine)
    counters = Counters()

    if args.sync_schema:
        if args.profile or args.git or args.git_root:
            print("config error: --sync-schema cannot be combined with --profile/--git/--git-root", file=sys.stderr)
            return EXIT_CONFIG
        return sync_schema(root, engine, force=args.force)

    if args.force:
        print("config error: --force requires --sync-schema", file=sys.stderr)
        return EXIT_CONFIG

    if args.profile and not PROFILE_RE.match(args.profile):
        counters.notes.append("config error: --profile must match ^[a-z][a-z0-9-]*$")
        write_report(counters)
        return EXIT_CONFIG

    schema_preexisted = (root / ".wiki-schema.md").is_file()
    if not create_root(root, counters):
        write_report(counters)
        return EXIT_CONFIG

    files = required_file_paths(root, args.profile)
    if not collect_type_conflicts(root, DIRS_WITH_GITKEEP, files, counters):
        write_report(counters)
        return EXIT_CONFIG

    if not create_skeleton(root, engine, args.profile, counters):
        write_report(counters)
        return EXIT_CONFIG
    if args.profile and schema_preexisted:
        counters.notes.append("profile summary skipped: .wiki-schema.md exists")

    if not ensure_obsidian_app(root, counters):
        write_report(counters)
        return EXIT_CONFIG

    if args.git and not ensure_git(root, args.git_root, engine, counters):
        write_report(counters)
        return EXIT_CONFIG

    if not run_selfcheck(root, engine, counters):
        write_report(counters)
        return EXIT_CONFIG

    write_report(counters)
    return 0


if __name__ == "__main__":
    sys.exit(main())
