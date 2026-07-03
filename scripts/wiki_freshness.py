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

from dataworks_client import DataWorksClient, DataWorksClientError, assert_no_datasource_secrets, parse_di_source_binding, parse_ref, source_binding_from_index_item, source_binding_to_index_fields
from wiki_common import LOCAL_TZ, load_markdown, now_iso, write_json_atomic
from wiki_index import DEFAULT_DATASOURCE_MAP_REL, DEFAULT_INDEX_REL, build_datasource_map, load_datasource_map, load_index, normalize_table_key


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


def doc_table_keys(doc) -> set[str]:
    keys: set[str] = set()
    for field in ("physical_table", "physical_field"):
        value = doc.fm.get(field)
        if isinstance(value, str):
            key = normalize_table_key(value)
            if key:
                keys.add(key)
    raw_ref = doc.fm.get("dataworks_ref")
    if isinstance(raw_ref, str) and raw_ref.startswith("table:"):
        key = normalize_table_key(raw_ref.removeprefix("table:"))
        if key:
            keys.add(key)
    for value in re.findall(r"\b[A-Za-z0-9_]+\.(?:ods|dwd|dwb|dws|ads)[A-Za-z0-9_.-]*\b", doc.body, flags=re.IGNORECASE):
        key = normalize_table_key(value)
        if key:
            keys.add(key)
    return keys


def doc_file_refs(doc) -> set[int]:
    refs: set[int] = set()
    raw_ref = doc.fm.get("dataworks_ref")
    if isinstance(raw_ref, str) and raw_ref.startswith("file:"):
        try:
            ref = parse_ref(raw_ref)
        except DataWorksClientError:
            return refs
        if ref.file_id is not None:
            refs.add(ref.file_id)
    return refs


def index_item_table_keys(item: Dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("table",):
        value = item.get(field)
        if isinstance(value, str):
            key = normalize_table_key(value)
            if key:
                keys.add(key)
    for field in ("inputs", "outputs"):
        values = item.get(field) or []
        if isinstance(values, list):
            for value in values:
                key = normalize_table_key(str(value))
                if key:
                    keys.add(key)
    return keys


def affected_docs_for_item(item: Dict[str, Any], docs: List[Any]) -> List[Dict[str, Any]]:
    file_id = item.get("file_id")
    table_keys = index_item_table_keys(item)
    affected: List[Dict[str, Any]] = []
    for doc in docs:
        reasons = []
        if isinstance(file_id, int) and file_id in doc_file_refs(doc):
            reasons.append("dataworks_ref:file")
        if table_keys & doc_table_keys(doc):
            reasons.append("normalized_lineage")
        if reasons:
            affected.append(
                {
                    "page_id": doc.fm.get("id"),
                    "file": doc.rel,
                    "reasons": sorted(set(reasons)),
                    "status": doc.fm.get("status"),
                    "review": doc.fm.get("review"),
                }
            )
    affected.sort(key=lambda item: str(item.get("file") or ""))
    return affected


def latest_change_by_file(changes: List[Any]) -> List[Any]:
    latest: Dict[int, Any] = {}
    for change in changes:
        current = latest.get(change.file_id)
        current_key = (
            current.execute_time_ms or 0,
            current.deployment_id,
            current.file_version or 0,
        ) if current else None
        change_key = (
            change.execute_time_ms or 0,
            change.deployment_id,
            change.file_version or 0,
        )
        if current is None or change_key > current_key:
            latest[change.file_id] = change
    return sorted(
        latest.values(),
        key=lambda item: (item.execute_time_ms or 0, item.deployment_id, item.file_id, item.file_version or 0),
        reverse=True,
    )


def evaluate_deployment_incremental(
    root: Path,
    *,
    project_id: int,
    client_factory: Optional[Callable[[], Any]] = None,
    end_execute_time_ms: Optional[int] = None,
    max_pages: Optional[int] = None,
    apply: bool = False,
    index_rel: str = DEFAULT_INDEX_REL,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "wiki_freshness_version": VERSION,
        "mode": "incremental_deployments",
        "ran_at": now_iso(),
        "root": str(root),
        "project_id": project_id,
        "dry_run": not apply,
        "source": {
            "kind": "ListDeployments+GetDeployment",
            "status": "success",
            "to_environment": 2,
            "end_execute_time_ms": end_execute_time_ms,
            "max_pages": max_pages,
        },
        "warnings": [],
        "changed_files": [],
        "affected_pages": [],
        "index_updates": [],
        "applied": {"index_written": False},
    }
    try:
        index = load_index(root, index_rel)
    except Exception as exc:
        report["warnings"].append(warning("INDEX_UNAVAILABLE", None, str(exc)))
        return report

    try:
        client = client_factory() if client_factory else DataWorksClient.from_env()
    except DataWorksClientError as exc:
        report["warnings"].append(warning(exc.code, None, exc.message))
        return report

    try:
        changes = client.list_successful_prod_deployment_items(project_id, end_execute_time_ms=end_execute_time_ms, max_pages=max_pages)
    except DataWorksClientError as exc:
        report["warnings"].append(warning(exc.code, None, exc.message))
        return report

    by_file_id = {
        item.get("file_id"): item
        for item in index.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("file_id"), int)
    }
    docs = scan_wiki_docs(root)
    changed_index = False
    affected_by_file: Dict[str, Dict[str, Any]] = {}
    for change in latest_change_by_file(changes):
        changed: Dict[str, Any] = {
            "deployment_id": change.deployment_id,
            "file_id": change.file_id,
            "file_version": change.file_version,
            "execute_time": change.execute_time_iso,
            "indexed": change.file_id in by_file_id,
            "status": "ok",
            "reason": "",
        }
        item = by_file_id.get(change.file_id)
        try:
            code = client.get_file_code(f"file:{project_id}/{change.file_id}")
            changed["current_fingerprint"] = code.fingerprint
        except DataWorksClientError as exc:
            changed["status"] = "warning"
            changed["reason"] = exc.message
            report["warnings"].append(warning(exc.code, None, f"file:{project_id}/{change.file_id}: {exc.message}"))
            report["changed_files"].append(changed)
            continue
        if item:
            changed["previous_fingerprint"] = item.get("code_fingerprint")
            changed["fingerprint_changed"] = code.fingerprint != item.get("code_fingerprint")
            should_parse_binding = item.get("program_type") == "DI" or item.get("source_binding") == "parsed"
            if should_parse_binding:
                previous_binding = source_binding_from_index_item(item)
                binding = parse_di_source_binding(code.content, program_type=str(item.get("program_type") or "DI"))
                current_binding = source_binding_to_index_fields(binding)
                changed["binding_previous"] = previous_binding
                changed["binding_current"] = current_binding
                changed["binding_changed"] = previous_binding != current_binding
            affected = affected_docs_for_item(item, docs)
            changed["affected_pages"] = affected
            for page in affected:
                affected_by_file.setdefault(str(page.get("file")), page)
            if changed["fingerprint_changed"]:
                report["index_updates"].append(
                    {
                        "file_id": change.file_id,
                        "node_name": item.get("node_name"),
                        "from": item.get("code_fingerprint"),
                        "to": code.fingerprint,
                    }
                )
                if apply:
                    item["code_fingerprint"] = code.fingerprint
                    item["last_synced"] = change.execute_time_iso or now_iso()
                    if should_parse_binding:
                        for key in ("source_binding", "source_datasource", "source_tables", "binding_warnings"):
                            item.pop(key, None)
                        item.update(current_binding)
                    changed_index = True
            if changed.get("binding_changed"):
                report["warnings"].append(warning("BINDING_CHANGED", None, f"file:{project_id}/{change.file_id}: source binding changed"))
                report.setdefault("review_queue_suggestions", []).append(
                    {
                        "type": "source_binding_changed",
                        "status": "pending",
                        "priority": "high",
                        "file_id": change.file_id,
                        "node_name": item.get("node_name"),
                        "reason": "DataWorks DI reader source binding changed",
                    }
                )
        else:
            changed["fingerprint_changed"] = None
            changed["reason"] = "file_id not present in local index"
        report["changed_files"].append(changed)
    report["affected_pages"] = sorted(affected_by_file.values(), key=lambda item: str(item.get("file") or ""))
    if apply and changed_index:
        write_json_atomic(root / index_rel, index)
        report["applied"]["index_written"] = True
    return report


def _datasource_by_name(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in data.get("items", []):
        if isinstance(item, dict) and isinstance(item.get("datasource_name"), str):
            result[item["datasource_name"]] = item
    return result


def evaluate_datasource_map(
    root: Path,
    *,
    project_id: int,
    client_factory: Optional[Callable[[], Any]] = None,
    apply: bool = False,
    map_rel: str = DEFAULT_DATASOURCE_MAP_REL,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "wiki_freshness_version": VERSION,
        "mode": "datasource_map",
        "ran_at": now_iso(),
        "root": str(root),
        "project_id": project_id,
        "dry_run": not apply,
        "map_path": map_rel,
        "warnings": [],
        "changes": [],
        "review_queue_suggestions": [],
        "applied": {"map_written": False},
    }
    try:
        current = load_datasource_map(root, map_rel)
    except Exception:
        current = {"items": []}
    try:
        client = client_factory() if client_factory else DataWorksClient.from_env()
        fresh = build_datasource_map(client, project_id=project_id)
    except DataWorksClientError as exc:
        report["warnings"].append(warning(exc.code, None, exc.message))
        return report
    assert_no_datasource_secrets(fresh)
    old_by_name = _datasource_by_name(current)
    new_by_name = _datasource_by_name(fresh)
    for name in sorted(set(old_by_name) | set(new_by_name)):
        old = old_by_name.get(name)
        new = new_by_name.get(name)
        status = None
        if old is None:
            status = "added"
        elif new is None:
            status = "removed"
        else:
            old_pair = (old.get("db_type"), old.get("database_name"), old.get("resolution"))
            new_pair = (new.get("db_type"), new.get("database_name"), new.get("resolution"))
            if old_pair != new_pair:
                status = "changed"
        if status:
            change = {
                "datasource_name": name,
                "status": status,
                "previous": {
                    "db_type": old.get("db_type") if old else None,
                    "database_name": old.get("database_name") if old else None,
                    "resolution": old.get("resolution") if old else None,
                },
                "current": {
                    "db_type": new.get("db_type") if new else None,
                    "database_name": new.get("database_name") if new else None,
                    "resolution": new.get("resolution") if new else None,
                },
            }
            assert_no_datasource_secrets(change)
            report["changes"].append(change)
            if status == "changed":
                report["review_queue_suggestions"].append(
                    {
                        "type": "datasource_target_changed",
                        "status": "pending",
                        "priority": "high",
                        "datasource_name": name,
                        "reason": "DataWorks datasource database/db_type changed",
                    }
                )
    if apply:
        write_json_atomic(root / map_rel, fresh)
        report["applied"]["map_written"] = True
    assert_no_datasource_secrets(report)
    return report


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
    if report.get("mode") == "incremental_deployments":
        lines = [
            "wiki-freshness incremental-deployments",
            "======================================",
            f"root: {report['root']}",
            f"project_id: {report['project_id']}",
            f"dry_run: {report['dry_run']}",
            f"changed_files: {len(report['changed_files'])} · affected_pages: {len(report['affected_pages'])} · index_updates: {len(report['index_updates'])}",
            "",
            "Changed files",
            "-------------",
        ]
        if not report["changed_files"]:
            lines.append("- (none)")
        for item in report["changed_files"]:
            binding = ""
            if "binding_changed" in item:
                binding = f" · binding_changed={item.get('binding_changed')}"
            lines.append(
                f"- file:{report['project_id']}/{item.get('file_id')} · deployment={item.get('deployment_id')} · "
                f"version={item.get('file_version')} · indexed={item.get('indexed')} · changed={item.get('fingerprint_changed')}" + binding
            )
        lines.extend(["", "Affected pages", "--------------"])
        if not report["affected_pages"]:
            lines.append("- (none)")
        for item in report["affected_pages"]:
            lines.append(f"- {item.get('file')} · reasons={','.join(item.get('reasons') or [])} · status={item.get('status')} · review={item.get('review')}")
        lines.extend(["", "Warnings", "--------"])
        if not report["warnings"]:
            lines.append("- (none)")
        for item in report["warnings"]:
            lines.append(f"- {item.get('code')}: {item.get('file') or '(global)'} · {item.get('message')}")
        if report.get("applied", {}).get("index_written"):
            lines.extend(["", "Applied", "-------", "- index written"])
        return "\n".join(lines) + "\n"

    if report.get("mode") == "datasource_map":
        lines = [
            "wiki-freshness datasource-map",
            "=============================",
            f"root: {report['root']}",
            f"project_id: {report['project_id']}",
            f"dry_run: {report['dry_run']}",
            f"changes: {len(report['changes'])}",
            "",
            "Changes",
            "-------",
        ]
        if not report["changes"]:
            lines.append("- (none)")
        for item in report["changes"]:
            lines.append(f"- {item['status']}: {item['datasource_name']} · {item['previous']} -> {item['current']}")
        lines.extend(["", "Warnings", "--------"])
        if not report["warnings"]:
            lines.append("- (none)")
        for item in report["warnings"]:
            lines.append(f"- {item.get('code')}: {item.get('file') or '(global)'} · {item.get('message')}")
        if report.get("applied", {}).get("map_written"):
            lines.extend(["", "Applied", "-------", "- datasource map written"])
        text = "\n".join(lines) + "\n"
        assert_no_datasource_secrets(text)
        return text

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
    parser.add_argument("--incremental-deployments", action="store_true", help="check successful production deployments instead of page anchors")
    parser.add_argument("--datasource-map", action="store_true", help="check DataWorks datasource map drift instead of page anchors")
    parser.add_argument("--project-id", type=int, help="DataWorks project id for --incremental-deployments")
    parser.add_argument("--datasource-map-path", default=DEFAULT_DATASOURCE_MAP_REL, help="datasource map path relative to instance root")
    parser.add_argument("--end-execute-time-ms", type=int, help="deployment window end time in epoch milliseconds")
    parser.add_argument("--max-pages", type=int, help="limit deployment pages for smoke tests")
    parser.add_argument("--apply", action="store_true", help="write updated fingerprints to dataworks_index.json in incremental mode")
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

    if args.incremental_deployments and args.datasource_map:
        print("wiki-freshness config error: choose only one of --incremental-deployments or --datasource-map", file=sys.stderr)
        return 2

    if args.incremental_deployments:
        if args.project_id is None:
            print("wiki-freshness config error: --project-id is required for --incremental-deployments", file=sys.stderr)
            return 2
        report = evaluate_deployment_incremental(
            root,
            project_id=args.project_id,
            client_factory=client_factory,
            end_execute_time_ms=args.end_execute_time_ms,
            max_pages=args.max_pages,
            apply=args.apply,
        )
    elif args.datasource_map:
        if args.project_id is None:
            print("wiki-freshness config error: --project-id is required for --datasource-map", file=sys.stderr)
            return 2
        report = evaluate_datasource_map(
            root,
            project_id=args.project_id,
            client_factory=client_factory,
            apply=args.apply,
            map_rel=args.datasource_map_path,
        )
    else:
        report = evaluate_instance(root, client_factory=client_factory, apply_stale=args.apply_stale)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_human(report), end="")
    if args.check and (report.get("drift_count", 0) or report.get("index_updates") or report.get("changes")):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
