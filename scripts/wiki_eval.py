#!/usr/bin/env python3
"""Evaluate llm-wiki instance health from lint and graph signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import wiki_graph
import wiki_lint
from wiki_common import BASE_SCHEMA, WikiCliConfigError, clamp_0_100, now_iso, resolve_instance_root_arg, round_half_up


DIM_ORDER = ["integrity", "freshness", "endorsement", "connectivity"]


def instance_root(repo_root: Path, raw_root: Optional[str]) -> Path:
    return resolve_instance_root_arg(repo_root, raw_root)


def _active_nodes(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [node for node in graph.get("nodes", []) if node.get("status") == "active"]


def _integrity_score(page_count: int, lint_data: Dict[str, Any], graph_meta: Dict[str, Any]) -> float:
    error_rate = min(1.0, len(lint_data.get("errors", [])) / page_count)
    dangling_rate = min(1.0, len(graph_meta.get("dangling_wikilinks", [])) / page_count)
    ambiguous_rate = min(1.0, len(graph_meta.get("ambiguous_wikilinks", [])) / page_count)
    return clamp_0_100(100 - (100 * error_rate + 50 * dangling_rate + 50 * ambiguous_rate))


def _freshness_score(graph: Dict[str, Any], lint_data: Dict[str, Any]) -> float:
    active_nodes = _active_nodes(graph)
    if not active_nodes:
        return 100.0
    stale_count = sum(1 for item in lint_data.get("warnings", []) if item.get("code") == "STALE_PAGE")
    stale_count = min(stale_count, len(active_nodes))
    return clamp_0_100(((len(active_nodes) - stale_count) / len(active_nodes)) * 100)


def _eligible_review_nodes(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        node
        for node in _active_nodes(graph)
        if node.get("type") not in {"source", "query"}
    ]


def _unreviewed_sort_key(node: Dict[str, Any]) -> tuple[int, int, str]:
    return (
        -int(node.get("in_degree", 0) or 0),
        -int(node.get("out_degree", 0) or 0),
        str(node.get("id", "")),
    )


def review_coverage(graph: Dict[str, Any]) -> Dict[str, Any]:
    eligible = _eligible_review_nodes(graph)
    reviewed = [node for node in eligible if node.get("review") is True]
    percent = 100 if not eligible else round_half_up((len(reviewed) / len(eligible)) * 100)
    unreviewed = [
        {
            "id": str(node.get("id", "")),
            "type": str(node.get("type", "")),
            "in_degree": int(node.get("in_degree", 0) or 0),
            "out_degree": int(node.get("out_degree", 0) or 0),
        }
        for node in sorted((node for node in eligible if node.get("review") is not True), key=_unreviewed_sort_key)
    ]
    return {
        "eligible": len(eligible),
        "reviewed": len(reviewed),
        "percent": int(clamp_0_100(percent)),
        "unreviewed": unreviewed,
    }


def _endorsement_score(graph: Dict[str, Any]) -> float:
    return float(review_coverage(graph)["percent"])


def _connectivity_score(graph: Dict[str, Any]) -> float:
    nodes = graph.get("nodes", [])
    if not nodes:
        return 100.0
    connected = [
        node
        for node in nodes
        if int(node.get("in_degree", 0) or 0) + int(node.get("out_degree", 0) or 0) > 0
    ]
    return clamp_0_100((len(connected) / len(nodes)) * 100)


def weakest_dim(dims: Dict[str, int]) -> Optional[str]:
    if not dims:
        return None
    return min(DIM_ORDER, key=lambda name: dims.get(name, 100))


def calculate_health(lint_result: Dict[str, Any], graph_result: Dict[str, Any], schema: Dict[str, Any] = BASE_SCHEMA) -> Dict[str, Any]:
    lint_data = lint_result["data"]
    graph = graph_result.get("graph") or {"nodes": [], "edges": [], "communities": [], "stats": {"nodes": 0, "edges": 0, "communities": 0}}
    meta = graph_result.get("meta") or {"dangling_wikilinks": [], "ambiguous_wikilinks": []}
    page_count = int(lint_data.get("scanned", {}).get("wiki_pages", 0) or 0)
    lint_errors = len(lint_data.get("errors", []))
    graph_errors = len(graph_result.get("config_errors", []))
    lint_exit_code = int(lint_result.get("exit_code", 0) or 0)
    graph_exit_code = int(graph_result.get("exit_code", 0) or 0)
    coverage = review_coverage(graph)
    if page_count == 0 and lint_errors == 0 and graph_errors == 0 and lint_exit_code == 0 and graph_exit_code == 0:
        return {
            "score": None,
            "status": "empty",
            "dims": None,
            "pages": 0,
            "weakest_dim": None,
            "threshold": int(schema.get("health_threshold", 70)),
            "lint_errors": 0,
            "graph_errors": 0,
            "lint_exit_code": lint_exit_code,
            "graph_exit_code": graph_exit_code,
            "review_coverage": coverage,
        }
    if page_count == 0:
        return {
            "score": 0,
            "status": "error",
            "dims": {"integrity": 0, "freshness": 0, "endorsement": 0, "connectivity": 0},
            "pages": 0,
            "weakest_dim": "integrity",
            "threshold": int(schema.get("health_threshold", 70)),
            "lint_errors": lint_errors,
            "graph_errors": graph_errors,
            "lint_exit_code": lint_exit_code,
            "graph_exit_code": graph_exit_code,
            "review_coverage": coverage,
        }

    dims_float = {
        "integrity": _integrity_score(page_count, lint_data, meta),
        "freshness": _freshness_score(graph, lint_data),
        "endorsement": float(coverage["percent"]),
        "connectivity": _connectivity_score(graph),
    }
    dims = {name: round_half_up(value) for name, value in dims_float.items()}
    weights = schema.get("health_weights", BASE_SCHEMA["health_weights"])
    score = round_half_up(sum(dims_float[name] * float(weights[name]) for name in DIM_ORDER))
    score = int(clamp_0_100(score))
    status = "error" if lint_exit_code == 2 or graph_exit_code == 2 or graph_errors else "ok"
    return {
        "score": score,
        "status": status,
        "dims": dims,
        "pages": page_count,
        "weakest_dim": weakest_dim(dims),
        "threshold": int(schema.get("health_threshold", 70)),
        "lint_errors": lint_errors,
        "graph_errors": graph_errors,
        "lint_exit_code": lint_exit_code,
        "graph_exit_code": graph_exit_code,
        "review_coverage": coverage,
    }


def evaluate(root: Path, *, now=None, scan_wiki_pii: bool = False) -> Dict[str, Any]:
    lint_result = wiki_lint.evaluate_instance(root, now=now, scan_wiki_pii=scan_wiki_pii)
    graph_result = wiki_graph.evaluate_instance(root)
    result = calculate_health(lint_result, graph_result, BASE_SCHEMA)
    result["root"] = str(Path(root).resolve())
    result["ts"] = now_iso()
    result["lint"] = {
        "exit_code": result["lint_exit_code"],
        "errors": lint_result["data"].get("errors", []),
        "warnings": lint_result["data"].get("warnings", []),
    }
    result["graph"] = {
        "exit_code": result["graph_exit_code"],
        "config_errors": graph_result.get("config_errors", []),
        "stats": (graph_result.get("graph") or {}).get("stats", {"nodes": 0, "edges": 0, "communities": 0}),
        "dangling_wikilinks": (graph_result.get("meta") or {}).get("dangling_wikilinks", []),
        "ambiguous_wikilinks": (graph_result.get("meta") or {}).get("ambiguous_wikilinks", []),
    }
    return result


def public_json(result: Dict[str, Any]) -> Dict[str, Any]:
    data = {
        "score": result["score"],
        "status": result["status"],
        "dims": result["dims"],
        "pages": result["pages"],
        "weakest_dim": result["weakest_dim"],
        "ts": result["ts"],
    }
    if "review_coverage" in result:
        data["review_coverage"] = result["review_coverage"]
    return data


def read_last_snapshot(root: Path) -> Optional[Dict[str, Any]]:
    path = root / ".wiki/eval_history.jsonl"
    if not path.exists():
        return None
    last = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last


def append_snapshot(root: Path, result: Dict[str, Any]) -> bool:
    if result["status"] != "ok":
        return False
    path = root / ".wiki/eval_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": result["ts"],
        "score": result["score"],
        "dims": result["dims"],
        "pages": result["pages"],
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def render_bar(value: int) -> str:
    filled = max(0, min(10, value // 10))
    return "#" * filled + "." * (10 - filled)


def render_human(result: Dict[str, Any], previous: Optional[Dict[str, Any]], snapshot_written: bool) -> str:
    lines = [
        "wiki-eval",
        "=========",
        f"实例: {result['root']}",
        f"状态: {result['status']}",
    ]
    if result["status"] == "empty":
        coverage = result.get("review_coverage", {})
        lines.extend(
            [
                "score: null",
                "空库：无可评估页面",
                f"reviewed-eligible: {coverage.get('reviewed', 0)}/{coverage.get('eligible', 0)}",
            ]
        )
        return "\n".join(lines)

    delta = ""
    if previous and isinstance(previous.get("score"), int):
        diff = result["score"] - int(previous["score"])
        if diff > 0:
            delta = f" (delta +{diff})"
        elif diff < 0:
            delta = f" (delta {diff})"
        else:
            delta = " (delta 0)"
    lines.extend(
        [
            f"score: {result['score']}/100{delta}",
            f"threshold: {result['threshold']}",
            f"pages: {result['pages']}",
            f"weakest_dim: {result['weakest_dim']}",
            f"reviewed-eligible: {result.get('review_coverage', {}).get('reviewed', 0)}/{result.get('review_coverage', {}).get('eligible', 0)}",
            "",
            "维度:",
        ]
    )
    for name in DIM_ORDER:
        value = int(result["dims"][name])
        lines.append(f"- {name:12s} {value:3d} [{render_bar(value)}]")
    lines.append("")
    lines.append(f"lint_errors: {result['lint_errors']}")
    lines.append(f"graph_config_errors: {result['graph_errors']}")
    lines.append(f"snapshot: {'written' if snapshot_written else 'not written'}")
    return "\n".join(lines)


def check_exit_code(result: Dict[str, Any]) -> int:
    if result["status"] == "empty":
        return 0
    if (
        result["lint_exit_code"] == 0
        and result["graph_exit_code"] == 0
        and result["lint_errors"] == 0
        and result["graph_errors"] == 0
        and result["score"] >= result["threshold"]
    ):
        return 0
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate llm-wiki knowledge health")
    parser.add_argument("--root", help="实例根目录；缺省为 ./knowledge")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        root = instance_root(repo_root, args.root)
    except WikiCliConfigError as exc:
        print(f"wiki-eval config error: {exc}", file=sys.stderr)
        return 2
    result = evaluate(root)
    previous = read_last_snapshot(root)
    snapshot_written = append_snapshot(root, result) if args.snapshot else False

    if args.json_output:
        print(json.dumps(public_json(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_human(result, previous, snapshot_written))
    if args.check:
        return check_exit_code(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
