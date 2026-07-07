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

from dataworks_client import (
    DataWorksClient,
    DataWorksClientError,
    DataWorksDatasourceResolution,
    DataWorksNode,
    assert_no_datasource_secrets,
    datasource_resolution_to_map,
    parse_di_source_binding,
    source_binding_to_index_fields,
)
from wiki_common import WikiCliConfigError, resolve_instance_root_arg, write_json_atomic


INDEX_VERSION = 2
DEFAULT_INDEX_REL = ".wiki/dataworks_index.json"
DEFAULT_DATASOURCE_MAP_REL = ".wiki/datasource_map.json"
LAYER_ROLE = {
    "ODS": "trace-only",
    "TMP": "trace-only",
    "DWD": "detail-candidate",
    "DWB": "detail-candidate",
    "DIM": "detail-candidate",
    "S-DWD": "detail-candidate",
    "S-DWB": "detail-candidate",
    "S-DIM": "detail-candidate",
    "DWS": "downstream-derived",
    "ADS": "downstream-derived",
    "DDM": "downstream-derived",
    "EDW": "downstream-derived",
    "unknown": "unknown",
}
LAYER_ORDER = {
    "ODS": 0,
    "TMP": 0,
    "DWD": 1,
    "DWB": 2,
    "DIM": 2,
    "S-DWD": 2,
    "S-DWB": 2,
    "S-DIM": 2,
    "DWS": 3,
    "ADS": 4,
    "DDM": 4,
    "EDW": 4,
    "unknown": 9,
}
DETAIL_LAYERS = {layer for layer, role in LAYER_ROLE.items() if role == "detail-candidate" and layer in {"DWD", "DWB"}}
SUMMARY_LAYERS = {layer for layer, role in LAYER_ROLE.items() if role == "downstream-derived" and layer in {"DWS", "ADS"}}
assert DETAIL_LAYERS == {"DWD", "DWB"}
assert SUMMARY_LAYERS == {"DWS", "ADS"}
ODS_STAGE_SUFFIXES = {"extract", "pre", "assign", "fix"}
CAVEAT = "基于 DataWorks 调度血缘，可能漏掉动态 SQL、脚本内临时表或未登记依赖。"


class ConfigError(Exception):
    pass


def find_repo_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "scripts").is_dir():
        raise ConfigError("must run from repo root containing scripts/")
    return root


def resolve_instance_root(repo_root: Path, raw_root: Optional[str]) -> Path:
    try:
        return resolve_instance_root_arg(repo_root, raw_root)
    except WikiCliConfigError as exc:
        raise ConfigError(str(exc)) from exc


def infer_layer(name: Optional[str], tables: Iterable[str]) -> Tuple[str, str]:
    for source, text in [("name_prefix", name)] if name else []:
        lowered = text.lower()
        for layer in ("s_dwd", "s_dwb", "s_dim"):
            if lowered == layer or lowered.startswith((f"{layer}_", f"{layer}.", f"{layer}-")):
                return layer.replace("_", "-").upper(), source
        for layer in ("ods", "tmp", "dwd", "dwb", "dim", "dws", "ads", "ddm", "edw"):
            if lowered == layer or lowered.startswith((f"{layer}_", f"{layer}.", f"{layer}-")):
                return layer.upper(), source
    for table in tables:
        lowered = table.split(".")[-1].lower()
        for layer in ("s_dwd", "s_dwb", "s_dim"):
            if lowered == layer or lowered.startswith((f"{layer}_", f"{layer}.", f"{layer}-")):
                return layer.replace("_", "-").upper(), "output_table"
        for layer in ("ods", "tmp", "dwd", "dwb", "dim", "dws", "ads", "ddm", "edw"):
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
    item = {
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
    if node.program_type and node.program_type != "DI":
        item["source_binding"] = "inferred"
    return item


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


def attach_source_bindings(index: Dict[str, Any], client: Any, *, project_id: int) -> Dict[str, Any]:
    for item in index.get("items", []):
        if not isinstance(item, dict):
            continue
        for key in ("source_binding", "source_datasource", "source_tables", "binding_warnings"):
            item.pop(key, None)
        program_type = item.get("program_type")
        if program_type != "DI":
            item.setdefault("source_binding", "inferred")
            continue
        file_id = item.get("file_id")
        if not isinstance(file_id, int):
            item.update(source_binding_to_index_fields(parse_di_source_binding("", program_type="DI")))
            continue
        try:
            code = client.get_file_code(f"file:{project_id}/{file_id}")
            binding = parse_di_source_binding(code.content, program_type="DI")
        except DataWorksClientError as exc:
            binding = parse_di_source_binding("", program_type="DI")
            binding = type(binding)("unparsed", None, [], [f"GetFile failed: {exc.code}"])
        item.update(source_binding_to_index_fields(binding))
    return index


def stable_datasource_map(resolutions: List[DataWorksDatasourceResolution], *, project_id: int) -> Dict[str, Any]:
    items = [datasource_resolution_to_map(item) for item in resolutions]
    items.sort(key=lambda item: str(item.get("datasource_name") or ""))
    data = {
        "map_version": 1,
        "project_id": project_id,
        "source": {"kind": "ListDataSources", "env_type": 1},
        "items": items,
    }
    assert_no_datasource_secrets(data)
    return data


def build_datasource_map(client: Any, *, project_id: int) -> Dict[str, Any]:
    return stable_datasource_map(client.list_datasource_resolutions(project_id), project_id=project_id)


def load_datasource_map(root: Path, rel_path: str = DEFAULT_DATASOURCE_MAP_REL) -> Dict[str, Any]:
    path = root / rel_path
    if not path.is_file():
        raise ConfigError(f"datasource map not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ConfigError(f"invalid datasource map: {path}")
    assert_no_datasource_secrets(data)
    return data


def attach_datasource_resolutions(index: Dict[str, Any], datasource_map: Dict[str, Any]) -> Dict[str, Any]:
    by_name = {
        str(item.get("datasource_name")): item
        for item in datasource_map.get("items", [])
        if isinstance(item, dict) and item.get("datasource_name")
    }
    for item in index.get("items", []):
        if not isinstance(item, dict):
            continue
        for key in ("source_database", "source_db_type"):
            item.pop(key, None)
        if item.get("source_binding") != "parsed":
            continue
        source_datasource = item.get("source_datasource")
        if not isinstance(source_datasource, str):
            continue
        resolution = by_name.get(source_datasource)
        if not resolution or resolution.get("resolution") != "parsed":
            continue
        database = resolution.get("database_name")
        db_type = resolution.get("db_type")
        if isinstance(database, str) and database.strip():
            item["source_database"] = database.strip()
        if isinstance(db_type, str) and db_type.strip():
            item["source_db_type"] = db_type.strip()
    return index


def build_index(
    client: Any,
    *,
    project_id: int,
    project_identifier: Optional[str],
    max_pages: Optional[int] = None,
    snapshot_date: Optional[str] = None,
) -> Dict[str, Any]:
    nodes = client.list_prod_nodes(project_id, max_pages=max_pages)
    index = stable_index(nodes, project_id=project_id, project_identifier=project_identifier, snapshot_date=snapshot_date)
    return attach_source_bindings(index, client, project_id=project_id)


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


def normalize_layer(layer: Any) -> str:
    text = str(layer or "unknown").strip()
    if not text:
        return "unknown"
    lowered = text.lower().replace("_", "-")
    aliases = {
        "ods": "ODS",
        "tmp": "TMP",
        "dwd": "DWD",
        "dwb": "DWB",
        "dim": "DIM",
        "s-dwd": "S-DWD",
        "s-dwb": "S-DWB",
        "s-dim": "S-DIM",
        "dws": "DWS",
        "ads": "ADS",
        "ddm": "DDM",
        "edw": "EDW",
        "unknown": "unknown",
    }
    return aliases.get(lowered, text.upper())


def layer_role(layer: Any) -> str:
    return LAYER_ROLE.get(normalize_layer(layer), "unknown")


def normalize_table_key(text: str) -> str:
    raw = normalize_table(text)
    if not raw:
        return ""
    parts = [part for part in raw.split(".") if part]
    if parts and parts[-1] in ODS_STAGE_SUFFIXES:
        parts = parts[:-1]
    if not parts:
        return ""
    project = parts[0]
    rest = "_".join(parts[1:]) if len(parts) > 1 else project
    if len(parts) == 1:
        return project
    for layer in ("ods", "dwd", "dwb", "dws", "ads"):
        if rest == layer:
            rest = layer
            break
        if rest.startswith(f"{layer}_") or rest.startswith(f"{layer}-"):
            rest = f"{layer}_{rest[len(layer) + 1:]}"
            break
    return f"{project}.{rest}"


def table_basename_key(text: str) -> str:
    key = normalize_table_key(text)
    return key.split(".")[-1] if key else ""


def table_domain(text: str) -> str:
    key = normalize_table_key(text)
    base = key.split(".")[-1]
    match = re.match(r"^(?:ods|dwd|dwb|dws|ads)_([a-z0-9]+)", base)
    return match.group(1) if match else "unknown"


def layer_note(layer: str) -> str:
    layer = normalize_layer(layer)
    return {
        "ODS": "贴源层，通常用于溯源线上源表，不优先作为业务口径答案。",
        "TMP": "临时中间层，仅用于血缘溯源，不建议作为业务口径取数定义点。",
        "DWD": "明细定义层，通常优先作为业务口径候选。",
        "DWB": "明细宽表/业务明细层，通常优先作为业务口径候选。",
        "DIM": "维表/映射定义层，可作为枚举或映射口径候选。",
        "S-DWD": "服务化明细层，可作为业务口径候选，需确认服务化边界。",
        "S-DWB": "服务化宽表层，可作为业务口径候选，需确认服务化边界。",
        "S-DIM": "服务化维表层，可作为枚举或映射口径候选。",
        "DWS": "汇总层，适合说明聚合粒度和下游使用。",
        "ADS": "应用层，适合说明应用过滤、展示或报表口径。",
        "DDM": "集市/下游派生层，默认不作为口径定义点，需 --include-summary 展开。",
        "EDW": "报表/下游派生层，默认不作为口径定义点，需 --include-summary 展开。",
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


def is_dexin_projection(item: Dict[str, Any]) -> bool:
    values: List[str] = []
    for key in ("table", "node_name"):
        if item.get(key):
            values.append(str(item[key]))
    for value in item.get("outputs") or []:
        values.append(str(value))
    for value in values:
        normalized = normalize_table(value)
        if normalized.startswith("pk_dexin.") or normalized.startswith("pk_data.pk_dexin."):
            return True
    return False


def item_role(item: Dict[str, Any]) -> str:
    if is_dexin_projection(item):
        return "trace-only"
    return layer_role(item.get("layer"))


def item_keys(item: Dict[str, Any], keys: Iterable[str] = ("table", "inputs", "outputs")) -> Set[str]:
    values: Set[str] = set()
    for value in item_tables({key: item.get(key) for key in keys}):
        normalized = normalize_table_key(value)
        if normalized:
            values.add(normalized)
    return values


def item_basename_keys(item: Dict[str, Any], keys: Iterable[str] = ("table", "inputs", "outputs")) -> Set[str]:
    values: Set[str] = set()
    for value in item_tables({key: item.get(key) for key in keys}):
        basename = table_basename_key(value)
        if basename:
            values.add(basename)
    return values


def item_binding_keys(item: Dict[str, Any]) -> Set[str]:
    """Online-source lookup keys from RFC-030/031 binding fields (parsed only).

    Lets reverse/origin resolve queries phrased as online names —
    ``<source_database>.<table>`` / ``<source_datasource>.<table>`` — against
    the ODS sync item. Read-only: consumes fields already backfilled into the
    index; absent fields mean no extra keys (legacy behavior unchanged).
    """
    if item.get("source_binding") != "parsed":
        return set()
    values: Set[str] = set()
    prefixes = [item.get("source_database"), item.get("source_datasource")]
    for raw in item.get("source_tables") or []:
        table = str(raw or "").strip()
        if not table:
            continue
        for prefix in prefixes:
            if isinstance(prefix, str) and prefix.strip():
                normalized = normalize_table_key(f"{prefix.strip()}.{table}")
                if normalized:
                    values.add(normalized)
    return values


def item_binding_basename_keys(item: Dict[str, Any]) -> Set[str]:
    if item.get("source_binding") != "parsed":
        return set()
    values: Set[str] = set()
    for raw in item.get("source_tables") or []:
        basename = table_basename_key(str(raw or ""))
        if basename:
            values.add(basename)
    return values


def item_lookup_keys(item: Dict[str, Any]) -> Set[str]:
    values = item_keys(item, ("table", "inputs", "outputs"))
    node_name = item.get("node_name")
    if isinstance(node_name, str):
        normalized = normalize_table_key(node_name)
        if normalized:
            values.add(normalized)
    values |= item_binding_keys(item)
    return values


def item_lookup_basename_keys(item: Dict[str, Any]) -> Set[str]:
    values = item_basename_keys(item, ("table", "inputs", "outputs"))
    node_name = item.get("node_name")
    if isinstance(node_name, str):
        basename = table_basename_key(node_name)
        if basename:
            values.add(basename)
    values |= item_binding_basename_keys(item)
    return values


def item_matches_table(item: Dict[str, Any], table: str) -> bool:
    wanted = normalize_table_key(table)
    return bool(wanted and wanted in item_keys(item))


def candidate(item: Dict[str, Any], pages_by_table: Dict[str, List[str]]) -> Dict[str, Any]:
    table = item.get("table") or ""
    pages = []
    for value in item_tables(item):
        pages.extend(pages_by_table.get(normalize_table(value), []))
        pages.extend(pages_by_table.get(normalize_table(value).split(".")[-1], []))
    pages = sorted(set(pages))
    layer = normalize_layer(item.get("layer") or "unknown")
    domain = table_domain(table or (item.get("node_name") or ""))
    return {
        "node_id": item.get("node_id"),
        "node_name": item.get("node_name"),
        "table": table,
        "layer": layer,
        "role": item_role(item),
        "layer_note": layer_note(layer),
        "domain": domain,
        "review": "has_knowledge_page" if pages else "missing_knowledge_page",
        "knowledge_pages": pages,
        "dataworks_ref": item.get("dataworks_ref"),
        "inputs": item.get("inputs") or [],
        "outputs": item.get("outputs") or [],
    }


def group_by_domain(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item.get("domain") or "unknown"), []).append(item)
    return {key: groups[key] for key in sorted(groups)}


def build_reverse_report(
    index: Dict[str, Any],
    table: str,
    *,
    root: Optional[Path] = None,
    depth: int = 1,
    include_summary: bool = False,
) -> Dict[str, Any]:
    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    pages_by_table = knowledge_page_map(root) if root else {}
    wanted = normalize_table_key(table)
    wanted_basename = table_basename_key(table)
    query_has_project = "." in normalize_table(table)
    ambiguous_matches: List[Dict[str, Any]] = []
    matched_trace_only: List[Dict[str, Any]] = []
    if wanted:
        if not query_has_project:
            basename = [item for item in items if wanted_basename and wanted_basename in item_lookup_basename_keys(item)]
            if len(basename) == 1:
                candidates = sorted(key for key in item_lookup_keys(basename[0]) if key.split(".")[-1] == wanted_basename)
                qualified = [key for key in candidates if "." in key]
                wanted = (qualified or candidates or sorted(item_lookup_keys(basename[0])))[0]
            elif len(basename) > 1:
                ambiguous_matches = basename
        direct = [item for item in items if wanted in item_lookup_keys(item)]
    upstream_items: List[Dict[str, Any]] = []
    first_layer_items: List[Dict[str, Any]] = []
    summary_items: List[Dict[str, Any]] = []
    seen_summary: Set[str] = set()

    for item in items:
        layer = normalize_layer(item.get("layer") or "unknown")
        role = item_role(item)
        if not wanted or wanted not in item_lookup_keys(item):
            continue
        if role == "trace-only" and layer != "ODS":
            matched_trace_only.append(item)
        if layer == "ODS":
            upstream_items.append(item)
        elif role == "detail-candidate":
            first_layer_items.append(item)
        elif role == "downstream-derived":
            key = str(item.get("node_id"))
            if key not in seen_summary:
                seen_summary.add(key)
                summary_items.append(item)

    upstream_ids = {str(item.get("node_id")) for item in upstream_items}
    seen_details = {str(item.get("node_id")) for item in first_layer_items}
    frontier: Set[str] = {wanted} if wanted else set()
    for item in upstream_items:
        frontier.update(item_keys(item, ("table", "outputs")))

    max_depth = max(1, int(depth or 1))
    for _ in range(max_depth):
        if not frontier:
            break
        next_frontier = set()
        found_detail = False
        for item in items:
            key = str(item.get("node_id"))
            layer = normalize_layer(item.get("layer") or "unknown")
            role = item_role(item)
            if key in upstream_ids or key in seen_details:
                continue
            if not (item_keys(item, ("inputs",)) & frontier):
                continue
            if layer == "ODS":
                upstream_items.append(item)
                upstream_ids.add(key)
                next_frontier.update(item_keys(item, ("table", "outputs")))
                continue
            if role == "detail-candidate":
                first_layer_items.append(item)
                seen_details.add(key)
                found_detail = True
                continue
            if include_summary and role == "downstream-derived":
                if key not in seen_summary:
                    seen_summary.add(key)
                    summary_items.append(item)
        if found_detail:
            break
        if not next_frontier or next_frontier <= frontier:
            break
        frontier = next_frontier

    upstream = [candidate(item, pages_by_table) for item in upstream_items]
    downstream = [candidate(item, pages_by_table) for item in first_layer_items]
    summary = [candidate(item, pages_by_table) for item in summary_items] if include_summary else []
    trace_only = [candidate(item, pages_by_table) for item in matched_trace_only if item_role(item) == "trace-only"]
    has_any_match = bool(upstream or downstream or summary or trace_only)
    if ambiguous_matches:
        warnings = ["ambiguous_table_key: 表名无 project 前缀且命中多个候选，请带 project 前缀重查。"]
    elif upstream and not downstream:
        warnings = ["未找到下游明细/汇总/应用层候选；先返回 ODS 溯源结果，需人工继续查下游。"]
    elif not has_any_match:
        warnings = [
            "索引中未命中该表；可能是非生产调度节点、动态 SQL、未拉全索引或表名不一致。"
            "若查询的是线上库表（datasource.table），已支持直接输入线上表名反查；仍未命中可能是该同步任务 binding 未解析。"
        ]
    else:
        warnings = []
    all_candidates = upstream + downstream + summary
    recommended = [] if (ambiguous_matches or trace_only) else ([item for item in downstream if item.get("role") == "detail-candidate"] or downstream or summary or upstream)
    sort_key = lambda item: (LAYER_ORDER.get(str(item.get("layer") or "unknown"), 9), str(item.get("node_name") or ""))
    upstream = sorted(upstream, key=sort_key)
    downstream = sorted(downstream, key=sort_key)
    summary = sorted(summary, key=sort_key)
    trace_only = sorted(trace_only, key=sort_key)
    recommended = sorted(recommended, key=sort_key)
    all_candidates = sorted(all_candidates, key=sort_key)
    return {
        "table": table,
        "normalized_key": wanted,
        "caveat": CAVEAT,
        "ambiguous_matches": [candidate(item, pages_by_table) for item in ambiguous_matches],
        "matched_trace_only": trace_only,
        "upstream_ods": upstream,
        "downstream_candidates": downstream,
        "summary_candidates": summary,
        "recommended": recommended,
        "all_candidates": all_candidates,
        "domain_groups": group_by_domain(downstream),
        "warnings": warnings,
    }


def render_reverse(report: Dict[str, Any]) -> str:
    lines = [
        "wiki-index reverse",
        "==================",
        f"table: {report['table']}",
        f"normalized_key: {report['normalized_key']}",
        f"caveat: {report['caveat']}",
        "",
        "Recommended",
        "-----------",
    ]
    for item in report["recommended"]:
        lines.append(f"- [{item['domain']}] {item['layer']} {item['node_name']} · {item['table'] or '(no table)'} · {item['review']} · {item['layer_note']}")
    if not report["recommended"]:
        lines.append("- (none)")
    if report.get("matched_trace_only"):
        lines.extend(["", "Matched trace-only", "------------------"])
        for item in report["matched_trace_only"]:
            lines.append(f"- {item['layer']} {item['node_name']} · {item['table'] or '(no table)'} · 仅溯源，不建议作为取数定义点")
    lines.extend(["", "ODS upstream", "------------"])
    for item in report["upstream_ods"]:
        lines.append(f"- {item['node_name']} · inputs={item['inputs']} · outputs={item['outputs']} · {item['review']}")
    if not report["upstream_ods"]:
        lines.append("- (none)")
    lines.extend(["", "Downstream candidates", "---------------------"])
    for domain, items in report.get("domain_groups", {}).items():
        lines.append(f"[{domain}]")
        for item in items:
            lines.append(f"- {item['layer']} {item['node_name']} · {item['table'] or '(no table)'} · {item['review']} · {item['layer_note']}")
    if not report["downstream_candidates"]:
        lines.append("- (none)")
    if report.get("summary_candidates"):
        lines.extend(["", "Summary candidates", "------------------"])
        for item in report["summary_candidates"]:
            lines.append(f"- [{item['domain']}] {item['layer']} {item['node_name']} · {item['table'] or '(no table)'} · {item['review']} · {item['layer_note']}")
    if report["warnings"]:
        lines.extend(["", "Warnings", "--------"])
        lines.extend(f"- {item}" for item in report["warnings"])
    return "\n".join(lines) + "\n"


def build_origin_report(index: Dict[str, Any], table: str, *, max_hops: int = 10) -> Dict[str, Any]:
    """Trace a warehouse table upstream to its online source bindings.

    Walks ``inputs`` upward until reaching ODS sync items carrying RFC-030
    source bindings; lists every online ``datasource.table`` found and notes
    upstream items whose binding is not ``parsed``. Offline: reads only the
    local managed index.
    """
    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    wanted = normalize_table_key(table)
    wanted_basename = table_basename_key(table)
    query_has_project = "." in normalize_table(table)
    warnings: List[str] = []
    ambiguous: List[Dict[str, Any]] = []
    if wanted and not query_has_project:
        basename_hits = [item for item in items if wanted_basename and wanted_basename in item_lookup_basename_keys(item)]
        if len(basename_hits) == 1:
            candidates = sorted(key for key in item_lookup_keys(basename_hits[0]) if key.split(".")[-1] == wanted_basename)
            qualified = [key for key in candidates if "." in key]
            wanted = (qualified or candidates or sorted(item_lookup_keys(basename_hits[0])))[0]
        elif len(basename_hits) > 1:
            ambiguous = basename_hits
    start_items = [] if ambiguous else [item for item in items if wanted and wanted in item_lookup_keys(item)]

    origins: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    seen_nodes: Set[str] = set()
    seen_origins: Set[Tuple[str, str, str]] = set()

    def collect_binding(item: Dict[str, Any]) -> None:
        binding = item.get("source_binding")
        if not binding:
            return
        if binding == "parsed":
            for raw in item.get("source_tables") or []:
                key = (
                    str(item.get("source_datasource") or ""),
                    str(item.get("source_database") or ""),
                    str(raw),
                )
                if key in seen_origins:
                    continue
                seen_origins.add(key)
                origins.append(
                    {
                        "source_db_type": item.get("source_db_type"),
                        "source_database": item.get("source_database"),
                        "source_datasource": item.get("source_datasource"),
                        "source_table": str(raw),
                        "ods_table": item.get("table"),
                        "node_name": item.get("node_name"),
                    }
                )
        else:
            unresolved.append(
                {
                    "ods_table": item.get("table"),
                    "node_name": item.get("node_name"),
                    "source_binding": binding,
                }
            )

    frontier: Set[str] = set()
    for item in start_items:
        seen_nodes.add(str(item.get("node_id")))
        collect_binding(item)
        frontier |= item_keys(item, ("inputs",))
    hops = 0
    while frontier and hops < max(1, int(max_hops)):
        hops += 1
        next_frontier: Set[str] = set()
        progressed = False
        for item in items:
            key = str(item.get("node_id"))
            if key in seen_nodes:
                continue
            if not (item_keys(item, ("table", "outputs")) & frontier):
                continue
            seen_nodes.add(key)
            progressed = True
            collect_binding(item)
            next_frontier |= item_keys(item, ("inputs",))
        if not progressed:
            break
        frontier = next_frontier

    # 同一 ODS 处理链（normalize 后同键）已由 extract 项给出 parsed 来源时，
    # 该链的 pre/终表等 inferred 阶段不再列为 unresolved（去噪）。
    parsed_chain_keys = {normalize_table_key(str(entry.get("ods_table") or "")) for entry in origins}
    unresolved = [
        entry
        for entry in unresolved
        if normalize_table_key(str(entry.get("ods_table") or "")) not in parsed_chain_keys
    ]
    if ambiguous:
        warnings.append("ambiguous_table_key: 表名无 project 前缀且命中多个候选，请带 project 前缀重查。")
    elif not start_items:
        warnings.append(
            "索引中未命中该表；可能是非生产调度节点、动态 SQL、未拉全索引或表名不一致。"
            "若查询的是线上库表（datasource.table），已支持直接输入线上表名反查；仍未命中可能是该同步任务 binding 未解析。"
        )
    elif not origins and not unresolved:
        warnings.append("未追溯到线上来源：上游链路中无 source binding（可能是仓内加工链或 binding 未回填）。")
    origins.sort(key=lambda entry: (str(entry.get("source_database") or ""), str(entry.get("source_table") or "")))
    unresolved.sort(key=lambda entry: str(entry.get("ods_table") or ""))
    return {
        "table": table,
        "normalized_key": wanted,
        "caveat": CAVEAT,
        "hops_used": hops,
        "origins": origins,
        "unresolved_bindings": unresolved,
        "ambiguous_matches": [candidate(item, {}) for item in ambiguous],
        "warnings": warnings,
    }


def render_origin(report: Dict[str, Any]) -> str:
    lines = [
        "wiki-index origin",
        "=================",
        f"table: {report['table']}",
        f"normalized_key: {report['normalized_key']}",
        f"caveat: {report['caveat']}",
        "",
        "Online origins",
        "--------------",
    ]
    for entry in report["origins"]:
        database = entry.get("source_database") or entry.get("source_datasource") or "?"
        db_type = entry.get("source_db_type") or "unknown"
        via = entry.get("source_datasource") or "?"
        ods = entry.get("ods_table") or entry.get("node_name") or "?"
        lines.append(f"- {db_type}:{database}.{entry['source_table']} · via datasource {via} · ODS {ods}")
    if not report["origins"]:
        lines.append("- (none)")
    if report["unresolved_bindings"]:
        lines.extend(["", "Unresolved bindings", "-------------------"])
        for entry in report["unresolved_bindings"]:
            ods = entry.get("ods_table") or entry.get("node_name") or "?"
            lines.append(f"- {ods} · source_binding={entry.get('source_binding')} · 线上来源未解析")
    if report["warnings"]:
        lines.extend(["", "Warnings", "--------"])
        lines.extend(f"- {item}" for item in report["warnings"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build DataWorks managed code index")
    subparsers = parser.add_subparsers(dest="command")
    datasource_map = subparsers.add_parser("datasource-map", help="build sanitized DataWorks datasource map")
    datasource_map.add_argument("--root", help="wiki instance root; default: knowledge")
    datasource_map.add_argument("--project-id", type=int, required=True, help="DataWorks project id")
    datasource_map.add_argument("--output", default=DEFAULT_DATASOURCE_MAP_REL, help="map path relative to instance root")
    datasource_map.add_argument("--write", action="store_true", help="write the datasource map; default is dry-run")
    datasource_map.add_argument("--json", action="store_true", help="output JSON datasource map")

    reverse = subparsers.add_parser("reverse", help="reverse lookup a source or warehouse table from local index")
    reverse.add_argument("--root", help="wiki instance root; default: knowledge")
    reverse.add_argument("--index", default=DEFAULT_INDEX_REL, help="index path relative to instance root")
    reverse.add_argument("--table", required=True, help="table name to lookup")
    reverse.add_argument("--depth", type=int, default=1, help="ODS traversal depth before detail layer; default: 1")
    reverse.add_argument("--include-summary", action="store_true", help="also include DWS/ADS summary candidates")
    reverse.add_argument("--json", action="store_true", help="output JSON")

    origin = subparsers.add_parser("origin", help="trace a warehouse table upstream to online datasource.table bindings")
    origin.add_argument("--root", help="wiki instance root; default: knowledge")
    origin.add_argument("--index", default=DEFAULT_INDEX_REL, help="index path relative to instance root")
    origin.add_argument("--table", required=True, help="warehouse table to trace upstream")
    origin.add_argument("--max-hops", type=int, default=10, help="max upstream hops; default: 10")
    origin.add_argument("--json", action="store_true", help="output JSON")

    parser.add_argument("--root", help="wiki instance root; default: knowledge")
    parser.add_argument("--project-id", type=int, help="DataWorks project id")
    parser.add_argument("--project-identifier", help="DataWorks project identifier / MaxCompute project name")
    parser.add_argument("--output", default=DEFAULT_INDEX_REL, help="index path relative to instance root")
    parser.add_argument("--datasource-map", default=DEFAULT_DATASOURCE_MAP_REL, help="datasource map path relative to instance root")
    parser.add_argument("--write", action="store_true", help="write the managed index; default is dry-run")
    parser.add_argument("--json", action="store_true", help="output JSON index")
    parser.add_argument("--max-pages", type=int, help="limit ListNodes pages for smoke tests")
    parser.add_argument("--attach-datasource-map", action="store_true", help="attach source_database/source_db_type from datasource map")
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
            report = build_reverse_report(index, args.table, root=root, depth=args.depth, include_summary=args.include_summary)
        except ConfigError as exc:
            print(f"wiki-index config error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_reverse(report), end="")
        return 0
    if args.command == "origin":
        try:
            index = load_index(root, args.index)
            report = build_origin_report(index, args.table, max_hops=args.max_hops)
        except ConfigError as exc:
            print(f"wiki-index config error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_origin(report), end="")
        return 0
    if args.command == "datasource-map":
        try:
            client = client_factory() if client_factory else DataWorksClient.from_env()
            data = build_datasource_map(client, project_id=args.project_id)
        except DataWorksClientError as exc:
            report = {"warnings": [{"code": exc.code, "message": exc.message}], "items": []}
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(f"wiki-index warning: {exc.code}: {exc.message}")
            return 0
        target = root / args.output
        if args.write:
            write_json_atomic(target, data)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            parsed = sum(1 for item in data["items"] if item.get("resolution") == "parsed")
            print("wiki-index datasource-map")
            print("=========================")
            print(f"action: {'write' if args.write else 'dry-run'}")
            print(f"target: {target}")
            print(f"items: {len(data['items'])}")
            print(f"parsed: {parsed}")
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
        if args.attach_datasource_map:
            datasource_map = load_datasource_map(root, args.datasource_map)
            index = attach_datasource_resolutions(index, datasource_map)
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
