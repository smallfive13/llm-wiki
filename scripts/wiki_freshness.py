#!/usr/bin/env python3
"""Check DataWorks-backed wiki anchors for upstream drift."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dataworks_client import DataWorksClient, DataWorksClientError, parse_ref
from wiki_common import LOCAL_TZ, load_markdown, now_iso


VERSION = "0.1.0"


def find_repo_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "scripts").is_dir():
        raise ConfigError("must run from repo root containing scripts/")
    return root


def resolve_instance_root(repo_root: Path, raw_root: Optional[str]) -> Path:
    root = Path(raw_root) if raw_root else repo_root / "knowledge"
    if not root.is_absolute():
        root = repo_root / root
    root = root.resolve()
    if not root.is_dir():
        raise ConfigError(f"instance root not found: {root}")
    return root


class ConfigError(Exception):
    pass


def scan_wiki_docs(root: Path):
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return []
    return [load_markdown(path, root) for path in sorted(wiki_root.glob("**/*.md"))]


def parse_last_synced(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=LOCAL_TZ)
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.combine(datetime.strptime(text, "%Y-%m-%d").date(), time.max, tzinfo=LOCAL_TZ)
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=LOCAL_TZ)


def update_frontmatter_status(path: Path, status: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    fm = text[4:end]
    lines = fm.splitlines()
    changed = False
    for idx, line in enumerate(lines):
        if re.match(r"^status\s*:", line):
            if line.strip() == f"status: {status}":
                return False
            lines[idx] = f"status: {status}"
            changed = True
            break
    if not changed:
        return False
    body = text[end:]
    tmp = Path(f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text("---\n" + "\n".join(lines) + body, encoding="utf-8")
    os.replace(tmp, path)
    return True


def warning(code: str, file: Optional[str], message: str) -> Dict[str, Any]:
    return {"code": code, "file": file, "message": message}


def drift_suggestion(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "stale_claim",
        "status": "pending",
        "priority": "high",
        "page_id": item.get("page_id"),
        "path": item.get("file"),
        "reason": item.get("reason"),
    }


def evaluate_instance(
    root: Path,
    *,
    client_factory: Optional[Callable[[], Any]] = None,
    apply_stale: bool = False,
) -> Dict[str, Any]:
    docs = scan_wiki_docs(root)
    anchors = [doc for doc in docs if isinstance(doc.fm.get("dataworks_ref"), str) and doc.fm.get("dataworks_ref").strip()]
    report: Dict[str, Any] = {
        "wiki_freshness_version": VERSION,
        "ran_at": now_iso(),
        "root": str(root),
        "scanned": {"wiki_pages": len(docs), "anchors": len(anchors)},
        "drift_count": 0,
        "warnings": [],
        "items": [],
        "review_queue_suggestions": [],
        "applied": {"apply_stale": apply_stale, "status_updates": []},
    }
    if not anchors:
        return report

    try:
        client = client_factory() if client_factory else DataWorksClient.from_env()
    except DataWorksClientError as exc:
        report["warnings"].append(warning(exc.code, None, exc.message))
        return report

    for doc in anchors:
        page_id = doc.fm.get("id")
        raw_ref = str(doc.fm.get("dataworks_ref")).strip()
        item: Dict[str, Any] = {
            "page_id": page_id,
            "file": doc.rel,
            "dataworks_ref": raw_ref,
            "kind": None,
            "status": "ok",
            "reason": "",
        }
        try:
            ref = parse_ref(raw_ref)
            item["kind"] = ref.kind
            if ref.kind == "file":
                code = client.get_file_code(raw_ref)
                item["current_fingerprint"] = code.fingerprint
                item["expected_fingerprint"] = doc.fm.get("code_fingerprint")
                item["fingerprint_version"] = "dw-code-v1"
                if not isinstance(doc.fm.get("code_fingerprint"), str) or not str(doc.fm.get("code_fingerprint")).startswith("sha256:"):
                    item["status"] = "warning"
                    item["reason"] = "missing or invalid code_fingerprint"
                    report["warnings"].append(warning("FINGERPRINT_MISSING", doc.rel, "file anchor missing sha256 code_fingerprint"))
                elif code.fingerprint != doc.fm.get("code_fingerprint"):
                    item["status"] = "drift"
                    item["reason"] = "code_fingerprint changed"
            else:
                table = client.get_table_info(raw_ref)
                item["last_ddl_time"] = table.last_ddl_time_iso
                item["column_count"] = len(table.columns)
                synced = parse_last_synced(doc.fm.get("last_synced"))
                if synced is None:
                    item["status"] = "warning"
                    item["reason"] = "missing or invalid last_synced"
                    report["warnings"].append(warning("LAST_SYNCED_MISSING", doc.rel, "table anchor missing comparable last_synced"))
                elif table.last_ddl_time_ms is not None:
                    ddl_dt = datetime.fromtimestamp(table.last_ddl_time_ms / 1000, tz=LOCAL_TZ)
                    if ddl_dt > synced:
                        item["status"] = "drift"
                        item["reason"] = "LastDdlTime newer than last_synced"
        except DataWorksClientError as exc:
            item["status"] = "warning"
            item["reason"] = exc.message
            report["warnings"].append(warning(exc.code, doc.rel, exc.message))

        if item["status"] == "drift":
            report["drift_count"] += 1
            report["review_queue_suggestions"].append(drift_suggestion(item))
            if apply_stale and update_frontmatter_status(doc.path, "stale"):
                report["applied"]["status_updates"].append(doc.rel)
        report["items"].append(item)
    return report


def render_human(report: Dict[str, Any]) -> str:
    lines = [
        "wiki-freshness",
        "==============",
        f"root: {report['root']}",
        f"wiki_pages: {report['scanned']['wiki_pages']} · anchors: {report['scanned']['anchors']} · drift: {report['drift_count']}",
        "",
        "Items",
        "-----",
    ]
    if not report["items"]:
        lines.append("- (none)")
    for item in report["items"]:
        lines.append(f"- {item.get('status')}: {item.get('file')} · {item.get('dataworks_ref')} · {item.get('reason') or 'ok'}")
    lines.extend(["", "Warnings", "--------"])
    if not report["warnings"]:
        lines.append("- (none)")
    for item in report["warnings"]:
        lines.append(f"- {item.get('code')}: {item.get('file') or '(global)'} · {item.get('message')}")
    if report["applied"]["status_updates"]:
        lines.extend(["", "Applied", "-------"])
        for rel in report["applied"]["status_updates"]:
            lines.append(f"- status: stale · {rel}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check DataWorks-backed wiki anchors for upstream drift")
    parser.add_argument("--root", help="wiki instance root; default: knowledge")
    parser.add_argument("--json", action="store_true", help="output JSON report")
    parser.add_argument("--check", action="store_true", help="exit 1 when drift is detected")
    parser.add_argument("--apply-stale", action="store_true", help="write status: stale to drift pages")
    return parser


def main(argv: Optional[List[str]] = None, *, client_factory: Optional[Callable[[], Any]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = find_repo_root()
        root = resolve_instance_root(repo_root, args.root)
    except ConfigError as exc:
        print(f"wiki-freshness config error: {exc}", file=sys.stderr)
        return 2

    report = evaluate_instance(root, client_factory=client_factory, apply_stale=args.apply_stale)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_human(report), end="")
    if args.check and report["drift_count"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
