#!/usr/bin/env python3
"""Build a managed DataWorks code index for a wiki instance."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dataworks_client import DataWorksClient, DataWorksClientError, DataWorksNode
from wiki_common import write_json_atomic


INDEX_VERSION = 1
DEFAULT_INDEX_REL = ".wiki/dataworks_index.json"


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
        for layer in ("ods", "dwd", "dws", "ads"):
            if lowered == layer or lowered.startswith((f"{layer}_", f"{layer}.", f"{layer}-")):
                return layer.upper(), source
    for table in tables:
        lowered = table.split(".")[-1].lower()
        for layer in ("ods", "dwd", "dws", "ads"):
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build DataWorks managed code index")
    parser.add_argument("--root", help="wiki instance root; default: knowledge")
    parser.add_argument("--project-id", type=int, required=True, help="DataWorks project id")
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
