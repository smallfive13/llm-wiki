#!/usr/bin/env python3
"""Build a managed DataWorks code index for a wiki instance."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from dataworks_client import DataWorksClient, DataWorksClientError, DataWorksNode
from wiki_common import write_json_atomic


INDEX_VERSION = 2
DEFAULT_INDEX_REL = ".wiki/dataworks_index.json"
LAYER_ORDER = {"ODS": 0, "DWD": 1, "DWB": 2, "DWS": 3, "ADS": 4, "unknown": 9}
DETAIL_LAYERS = {"DWD", "DWB"}
CAVEAT = "基于 DataWorks 调度血缘，可能漏掉动态 SQL、脚本内临时表或未登记依赖。"


class ConfigError(Exception):
    pass


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


def infer_layer(name: Optional[str], tables: Iterable[str]) -> Tuple[str, str]:
    for source, text in [("name_prefix", name)] if name else []:
        lowered = text.lower()
        for layer in ("ods", "dwd", "dwb", "dws", "ads"):
            if lowered == layer or lowered.startswith((f"{layer}_", f"{layer}.", f"{layer}-")):
                return layer.upper(), source
    for table in tables:
        lowered = table.split(".")[-1].lower()
        for layer in ("ods", "dwd", "dwb", "dws", "ads"):
            if lowered == layer or lowered.startswith((f"{layer}_", f"{layer}.", f"{layer}-")):
                return layer.upper(), "output_table"
    return "unknown", "unknown"


def is_synthetic_output(table: str) -> bool:
    name = table.split(".")[-1].lower()
    return bool(name.endswith("_out") and name[:-4].isdigit())


def primary_table(tables: List[str]) -> Optional[str]:
    for table in tables:
        if not is_synthetic_output(table):
            return table
    return tables[0] if tables else None


def node_to_item(node: DataWorksNode) -> Dict[str, Any]:
    layer, layer_source = infer_layer(node.node_name, node.tables)
    return {
        "code_fingerprint": node.fingerprint,
        "dataworks_ref": f"file:{node.project_id}/{node.file_id}" if node.file_id is not None else None,
        "file_id": node.file_id,
        "file_path": node.file_path,
        "fingerprint_version": "dw-code-v1",
        "inputs": sorted(node.inputs),
        "last_synced": node.last_synced,
        "layer": layer,
        "layer_source": layer_source,
        "node_id": node.node_id,
        "node_name": node.node_name,
        "outputs": sorted(node.tables),
        "program_type": node.program_type,
        "table": primary_table(sorted(node.tables)),
    }


def stable_index(
    nodes: List[DataWorksNode],
    *,
    project_id: int,
    project_identifier: Optional[str],
    snapshot_date: Optional[str] = None,
    source_window: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    items = [node_to_item(node) for node in nodes]
    items.sort(key=lambda item: (str(item.get("node_name") or ""), int(item.get("node_id") or 0)))
    return {
        "index_version": INDEX_VERSION,
        "project_id": project_id,
        "project_identifier": project_identifier,
        "snapshot_date": snapshot_date or date.today().isoformat(),
        "source_window": source_window or {"mode": "full_prod_nodes"},
        "items": items,
    }


def build_index(
    client: Any,
    *,
    project_id: int,
    project_identifier: Optional[str],
    max_pages: Optional[int] = None,
    snapshot_date: Optional[str] = None,
) -> Dict[str, Any]:
    nodes = client.list_prod_nodes(project_id, max_pages=max_pages)
    return stable_index(nodes, project_id=project_id, project_identifier=project_identifier, snapshot_date=snapshot_date)


def load_index(root: Path, rel_path: str = DEFAULT_INDEX_REL) -> Dict[str, Any]:
    path = root / rel_path
    if not path.is_file():
        raise ConfigError(f"index not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ConfigError(f"invalid index: {path}")
    return data


def contains_code_payload(index: Dict[str, Any]) -> bool:
    text = json.dumps(index, ensure_ascii=False).lower()
    suspicious = ["select ", "insert ", "create table", "drop table", "overwrite table"]
    return any(token in text for token in suspicious)


def render_human(index: Dict[str, Any], *, path: Path, write: bool) -> str:
    items = index.get("items", [])
    by_layer: Dict[str, int] = {}
    for item in items:
        layer = str(item.get("layer") or "unknown")
        by_layer[layer] = by_layer.get(layer, 0) + 1
    layer_text = " · ".join(f"{key}:{by_layer[key]}" for key in sorted(by_layer)) or "(none)"
    action = "write" if write else "dry-run"
    return "\n".join(
        [
            "wiki-index",
            "==========",
            f"action: {action}",
            f"target: {path}",
            f"items: {len(items)}",
            f"layers: {layer_text}",
            f"contains_code_payload: {contains_code_payload(index)}",
        ]
    ) + "\n"


def normalize_table(text: str) -> str:
    return str(text or "").strip().lower()


def layer_note(layer: str) -> str:
    return {
        "ODS": "贴源层，通常用于溯源线上源表，不优先作为业务口径答案。",
        "DWD": "明细定义层，通常优先作为业务口径候选。",
        "DWB": "明细宽表/业务明细层，通常优先作为业务口径候选。",
        "DWS": "汇总层，适合说明聚合粒度和下游使用。",
        "ADS": "应用层，适合说明应用过滤、展示或报表口径。",
        "unknown": "未识别层级，需要人工判断。",
    }.get(layer, "未识别层级，需要人工判断。")


def knowledge_page_map(root: Path) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return result
    for path in sorted(wiki_root.glob("**/*.md")):
        text = path.read_text(encoding="utf-8")
        for match in set(re.findall(r"\b(?:[A-Za-z0-9_]+\.)?(?:ods|dwd|dwb|dws|ads)_[A-Za-z0-9_.-]+\b", text, flags=re.IGNORECASE)):
            result.setdefault(normalize_table(match), []).append(path.relative_to(root).as_posix())
    return result


def item_tables(item: Dict[str, Any]) -> List[str]:
    values = []
    for key in ("table",):
        if item.get(key):
            values.append(str(item[key]))
    for key in ("inputs", "outputs"):
        for value in item.get(key) or []:
            values.append(str(value))
    seen = set()
    out = []
    for value in values:
        key = normalize_table(value)
        if key and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def item_matches_table(item: Dict[str, Any], table: str) -> bool:
    wanted = normalize_table(table)
    use_short = "." not in wanted
    for value in item_tables(item):
        current = normalize_table(value)
        if current == wanted or (use_short and current.split(".")[-1] == wanted):
            return True
    return False


def normalized_aliases(value: str, *, include_short: bool = False) -> Set[str]:
    text = normalize_table(value)
    if not text:
        return set()
    values = {text}
    if include_short:
        values.add(text.split(".")[-1])
    return values


def query_aliases(value: str) -> Set[str]:
    text = normalize_table(value)
    if not text:
        return set()
    if "." in text:
        return {text}
    return {text}


def item_value_keys(item: Dict[str, Any], keys: Iterable[str], *, include_short: bool = False) -> Set[str]:
    values: Set[str] = set()
    for key in keys:
        raw = item.get(key)
        if isinstance(raw, str):
            values.update(normalized_aliases(raw, include_short=include_short))
        elif isinstance(raw, list):
            for value in raw:
                values.update(normalized_aliases(str(value), include_short=include_short))
    return values


def item_matches_any(item: Dict[str, Any], values: Set[str], keys: Iterable[str]) -> bool:
    return bool(item_value_keys(item, keys, include_short=True) & values)


def candidate(item: Dict[str, Any], pages_by_table: Dict[str, List[str]]) -> Dict[str, Any]:
    table = item.get("table") or ""
    pages = []
    for value in item_tables(item):
        pages.extend(pages_by_table.get(normalize_table(value), []))
        pages.extend(pages_by_table.get(normalize_table(value).split(".")[-1], []))
    pages = sorted(set(pages))
    layer = str(item.get("layer") or "unknown")
    return {
        "node_id": item.get("node_id"),
        "node_name": item.get("node_name"),
        "table": table,
        "layer": layer,
        "layer_note": layer_note(layer),
        "review": "has_knowledge_page" if pages else "missing_knowledge_page",
        "knowledge_pages": pages,
        "dataworks_ref": item.get("dataworks_ref"),
        "inputs": item.get("inputs") or [],
        "outputs": item.get("outputs") or [],
    }


def build_reverse_report(index: Dict[str, Any], table: str, *, root: Optional[Path] = None) -> Dict[str, Any]:
    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    pages_by_table = knowledge_page_map(root) if root else {}
    wanted = query_aliases(table)
    direct_matches = [item for item in items if item_matches_table(item, table)]
    upstream_items = [
        item
        for item in direct_matches
        if str(item.get("layer")) == "ODS"
        or item_matches_any(item, wanted, ("inputs",))
    ]
    upstream_ids = {str(item.get("node_id")) for item in upstream_items}

    downstream_items: List[Dict[str, Any]] = []
    seen_downstream: Set[str] = set()

    def add_downstream(item: Dict[str, Any]) -> None:
        key = str(item.get("node_id"))
        if key in upstream_ids or key in seen_downstream:
            return
        if str(item.get("layer")) == "ODS":
            return
        seen_downstream.add(key)
        downstream_items.append(item)

    for item in direct_matches:
        add_downstream(item)

    frontier: Set[str] = set()
    for item in upstream_items:
        frontier.update(item_value_keys(item, ("table", "outputs"), include_short=False))
    if not frontier:
        frontier = set(wanted)

    # Follow scheduling lineage from ODS outputs into downstream inputs. Keep a
    # small deterministic bound so reverse lookup cannot balloon on dirty graphs.
    for _depth in range(5):
        next_frontier: Set[str] = set()
        for item in items:
            key = str(item.get("node_id"))
            if key in upstream_ids or key in seen_downstream or str(item.get("layer")) == "ODS":
                continue
            if item_matches_any(item, frontier, ("inputs", "table", "outputs")):
                add_downstream(item)
                next_frontier.update(item_value_keys(item, ("table", "outputs")))
        if not next_frontier or next_frontier <= frontier:
            break
        frontier = next_frontier

    upstream = [candidate(item, pages_by_table) for item in upstream_items]
    downstream = [candidate(item, pages_by_table) for item in downstream_items]
    if upstream and not downstream:
        warnings = ["未找到下游明细/汇总/应用层候选；先返回 ODS 溯源结果，需人工继续查下游。"]
    elif not upstream and not downstream:
        warnings = ["索引中未命中该表；可能是非生产调度节点、动态 SQL、未拉全索引或表名不一致。"]
    else:
        warnings = []
    all_candidates = upstream + downstream
    recommended = [
        item for item in downstream if item.get("layer") in DETAIL_LAYERS
    ] or downstream or upstream
    sort_key = lambda item: (LAYER_ORDER.get(str(item.get("layer") or "unknown"), 9), str(item.get("node_name") or ""))
    return {
        "table": table,
        "caveat": CAVEAT,
        "upstream_ods": sorted(upstream, key=sort_key),
        "downstream_candidates": sorted(downstream, key=sort_key),
        "recommended": sorted(recommended, key=sort_key),
        "all_candidates": sorted(all_candidates, key=sort_key),
        "warnings": warnings,
    }


def render_reverse(report: Dict[str, Any]) -> str:
    lines = [
        "wiki-index reverse",
        "==================",
        f"table: {report['table']}",
        f"caveat: {report['caveat']}",
        "",
        "Recommended",
        "-----------",
    ]
    for item in report["recommended"]:
        lines.append(f"- {item['layer']} {item['node_name']} · {item['table'] or '(no table)'} · {item['review']} · {item['layer_note']}")
    if not report["recommended"]:
        lines.append("- (none)")
    lines.extend(["", "ODS upstream", "------------"])
    for item in report["upstream_ods"]:
        lines.append(f"- {item['node_name']} · inputs={item['inputs']} · outputs={item['outputs']} · {item['review']}")
    if not report["upstream_ods"]:
        lines.append("- (none)")
    lines.extend(["", "Downstream candidates", "---------------------"])
    for item in report["downstream_candidates"]:
        lines.append(f"- {item['layer']} {item['node_name']} · {item['table'] or '(no table)'} · {item['review']} · {item['layer_note']}")
    if not report["downstream_candidates"]:
        lines.append("- (none)")
    if report["warnings"]:
        lines.extend(["", "Warnings", "--------"])
        lines.extend(f"- {item}" for item in report["warnings"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build DataWorks managed code index")
    subparsers = parser.add_subparsers(dest="command")
    reverse = subparsers.add_parser("reverse", help="reverse lookup a source or warehouse table from local index")
    reverse.add_argument("--root", help="wiki instance root; default: knowledge")
    reverse.add_argument("--index", default=DEFAULT_INDEX_REL, help="index path relative to instance root")
    reverse.add_argument("--table", required=True, help="table name to lookup")
    reverse.add_argument("--json", action="store_true", help="output JSON")

    parser.add_argument("--root", help="wiki instance root; default: knowledge")
    parser.add_argument("--project-id", type=int, help="DataWorks project id")
    parser.add_argument("--project-identifier", help="DataWorks project identifier / MaxCompute project name")
    parser.add_argument("--output", default=DEFAULT_INDEX_REL, help="index path relative to instance root")
    parser.add_argument("--write", action="store_true", help="write the managed index; default is dry-run")
    parser.add_argument("--json", action="store_true", help="output JSON index")
    parser.add_argument("--max-pages", type=int, help="limit ListNodes pages for smoke tests")
    return parser


def main(argv: Optional[List[str]] = None, *, client_factory: Optional[Any] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = find_repo_root()
        root = resolve_instance_root(repo_root, args.root)
    except ConfigError as exc:
        print(f"wiki-index config error: {exc}", file=sys.stderr)
        return 2
    if args.command == "reverse":
        try:
            index = load_index(root, args.index)
            report = build_reverse_report(index, args.table, root=root)
        except ConfigError as exc:
            print(f"wiki-index config error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_reverse(report), end="")
        return 0
    if args.project_id is None:
        print("wiki-index config error: --project-id is required for build mode", file=sys.stderr)
        return 2
    try:
        client = client_factory() if client_factory else DataWorksClient.from_env()
        index = build_index(
            client,
            project_id=args.project_id,
            project_identifier=args.project_identifier,
            max_pages=args.max_pages,
        )
    except DataWorksClientError as exc:
        report = {"warnings": [{"code": exc.code, "message": exc.message}], "items": []}
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"wiki-index warning: {exc.code}: {exc.message}")
        return 0

    target = root / args.output
    if args.write:
        write_json_atomic(target, index)
    if args.json:
        print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_human(index, path=target, write=args.write), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
