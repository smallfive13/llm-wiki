#!/usr/bin/env python3
"""Build the llm-wiki canonical graph projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from wiki_common import (
    BASE_SCHEMA,
    MarkdownDoc,
    first_h1,
    load_markdown,
    load_profile,
    merge_schema,
    normalize_alias,
    now_iso,
    profile_name,
    validate_profile,
    write_json_atomic,
)


VERSION = 1
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

Node = Dict[str, Any]
Edge = Dict[str, Any]
WikilinkLookups = Dict[str, Any]


def find_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "scripts").is_dir():
        print("wiki-graph config error: must run from repo root containing scripts/", file=sys.stderr)
        sys.exit(2)
    return root


def instance_root(repo_root: Path, raw_root: Optional[str]) -> Path:
    path = Path(raw_root) if raw_root else repo_root / "knowledge"
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()
    if not path.is_dir():
        print(f"wiki-graph config error: instance root not found: {path}", file=sys.stderr)
        sys.exit(2)
    return path


def load_effective_schema(root: Path) -> Tuple[Dict[str, Any], str]:
    profile = load_profile(root)
    issues = validate_profile(profile, BASE_SCHEMA)
    if issues:
        for item in issues:
            print(f"wiki-graph config error: {item.code} {item.field}: {item.message}", file=sys.stderr)
        sys.exit(2)
    return merge_schema(BASE_SCHEMA, profile), profile_name(profile)


def rel_to_repo(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def scan_wiki_docs(root: Path) -> List[MarkdownDoc]:
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return []
    return [load_markdown(path, root) for path in sorted(wiki_root.glob("**/*.md"))]


def page_id(doc: MarkdownDoc) -> Optional[str]:
    value = doc.fm.get("id")
    return value if isinstance(value, str) and value else None


def list_field(doc: MarkdownDoc, field: str) -> List[str]:
    value = doc.fm.get(field, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]


def is_redirect(doc: MarkdownDoc) -> bool:
    return doc.fm.get("status") == "redirect"


def node_label(doc: MarkdownDoc) -> str:
    label = first_h1(doc).strip()
    return label or Path(doc.rel).stem


def build_redirect_map(docs: Iterable[MarkdownDoc]) -> Dict[str, str]:
    redirects: Dict[str, str] = {}
    for doc in docs:
        pid = page_id(doc)
        canonical_id = doc.fm.get("canonical_id")
        if pid and is_redirect(doc) and isinstance(canonical_id, str) and canonical_id:
            redirects[pid] = canonical_id
    return redirects


def fold_target(target: str, redirects: Dict[str, str]) -> str:
    return redirects.get(target, target)


def build_nodes(docs: Iterable[MarkdownDoc], schema: Dict[str, Any]) -> Tuple[Dict[str, Node], List[Dict[str, str]]]:
    nodes: Dict[str, Node] = {}
    unknown_types: List[Dict[str, str]] = []
    known_types = set(schema.get("page_types", {}).keys())
    for doc in docs:
        pid = page_id(doc)
        if not pid or is_redirect(doc):
            continue
        page_type = str(doc.fm.get("type"))
        if page_type not in known_types:
            unknown_types.append({"id": pid, "type": page_type, "file": doc.rel})
            continue
        nodes[pid] = {
            "id": pid,
            "label": node_label(doc),
            "type": page_type,
            "status": doc.fm.get("status"),
            "degree": 0,
            "community": None,
        }
    return dict(sorted(nodes.items())), unknown_types


def read_alias_index(root: Path, redirects: Dict[str, str]) -> Dict[str, str]:
    path = root / ".wiki/normalized_alias_index.json"
    data = read_json(path)
    entries = data.get("entries", {})
    lookup: Dict[str, str] = {}
    if not isinstance(entries, dict):
        return lookup
    for key, item in entries.items():
        if not isinstance(key, str) or not isinstance(item, dict):
            continue
        canonical_id = item.get("canonical_id")
        if isinstance(canonical_id, str) and canonical_id:
            normalized = normalize_alias(key)
            if normalized:
                lookup[normalized] = fold_target(canonical_id, redirects)
    return lookup


def normalize_wikilink_target(value: str) -> str:
    text = value.strip()
    if text.endswith(".md"):
        text = text[:-3]
    return normalize_alias(text)


def build_wikilink_lookup(root: Path, docs: List[MarkdownDoc], redirects: Dict[str, str]) -> WikilinkLookups:
    alias_lookup = read_alias_index(root, redirects)
    path_lookup: Dict[str, str] = {}
    slug_targets: Dict[str, Set[str]] = defaultdict(set)
    for doc in docs:
        pid = page_id(doc)
        if not pid:
            continue
        target = fold_target(pid, redirects)
        path_key = normalize_wikilink_target(doc.rel)
        if path_key:
            path_lookup[path_key] = target
        slug_key = normalize_wikilink_target(Path(doc.rel).stem)
        if slug_key:
            slug_targets[slug_key].add(target)

    slug_lookup: Dict[str, str] = {}
    ambiguous_slugs: Set[str] = set()
    for key, targets in slug_targets.items():
        if len(targets) == 1:
            slug_lookup[key] = next(iter(targets))
        else:
            ambiguous_slugs.add(key)
    return {
        "alias": alias_lookup,
        "path": path_lookup,
        "slug": slug_lookup,
        "ambiguous_slugs": ambiguous_slugs,
    }


def parse_wikilink(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0]
    return target.strip()


def resolve_wikilink_target(raw_target: str, lookups: WikilinkLookups) -> Tuple[Optional[str], str]:
    key = normalize_wikilink_target(raw_target)
    if not key:
        return None, "dangling"
    alias_lookup = lookups["alias"]
    if key in alias_lookup:
        return alias_lookup[key], "resolved"
    if "/" in raw_target:
        path_lookup = lookups["path"]
        return (path_lookup[key], "resolved") if key in path_lookup else (None, "dangling")
    slug_lookup = lookups["slug"]
    if key in slug_lookup:
        return slug_lookup[key], "resolved"
    if key in lookups["ambiguous_slugs"]:
        return None, "ambiguous"
    return None, "dangling"


def add_edge(
    edges: Dict[Tuple[str, str, str, str], Edge],
    nodes: Dict[str, Node],
    redirects: Dict[str, str],
    source: str,
    target: str,
    relation: str,
    source_kind: str,
    weight: int,
    undirected: bool = False,
) -> None:
    if source in redirects:
        return
    target = fold_target(target, redirects)
    if source not in nodes or target not in nodes or source == target:
        return
    if undirected and target < source:
        source, target = target, source
    key = (source, target, relation, source_kind)
    edges.setdefault(
        key,
        {
            "source": source,
            "target": target,
            "relation": relation,
            "source_kind": source_kind,
            "weight": weight,
        },
    )


def build_edges(
    docs: List[MarkdownDoc],
    nodes: Dict[str, Node],
    redirects: Dict[str, str],
    wikilink_lookup: WikilinkLookups,
) -> Tuple[List[Edge], List[Dict[str, str]], List[Dict[str, str]]]:
    edges: Dict[Tuple[str, str, str, str], Edge] = {}
    dangling: Dict[Tuple[str, str], Dict[str, str]] = {}
    ambiguous: Dict[Tuple[str, str], Dict[str, str]] = {}
    docs_by_source: Dict[str, List[str]] = defaultdict(list)

    for doc in docs:
        pid = page_id(doc)
        if not pid or pid not in nodes:
            continue
        for target in list_field(doc, "source_ids"):
            add_edge(edges, nodes, redirects, pid, target, "source_ref", "canonical", 2)
            docs_by_source[target].append(pid)
        for target in list_field(doc, "related_ids"):
            add_edge(edges, nodes, redirects, pid, target, "related", "canonical", 2)
        for target in list_field(doc, "supersedes"):
            add_edge(edges, nodes, redirects, pid, target, "supersedes", "canonical", 2)
        for match in WIKILINK_RE.finditer(doc.body):
            raw_target = parse_wikilink(match.group(1))
            if not raw_target:
                continue
            target, resolution = resolve_wikilink_target(raw_target, wikilink_lookup)
            if target:
                add_edge(edges, nodes, redirects, pid, target, "wikilink", "wikilink", 1)
            elif resolution == "ambiguous":
                ambiguous.setdefault(
                    (pid, raw_target),
                    {"source": pid, "target": raw_target, "file": doc.rel},
                )
            else:
                dangling.setdefault(
                    (pid, raw_target),
                    {"source": pid, "target": raw_target, "file": doc.rel},
                )

    for source_id, page_ids in sorted(docs_by_source.items()):
        unique_pages = sorted(set(page_ids))
        if source_id not in nodes:
            continue
        for left, right in combinations(unique_pages, 2):
            add_edge(edges, nodes, redirects, left, right, "co_source", "computed", 1, undirected=True)

    sorted_edges = [edges[key] for key in sorted(edges)]
    return (
        sorted_edges,
        [dangling[key] for key in sorted(dangling)],
        [ambiguous[key] for key in sorted(ambiguous)],
    )


def build_adjacency(nodes: Dict[str, Node], edges: List[Edge]) -> Dict[str, Set[str]]:
    adjacency: Dict[str, Set[str]] = {pid: set() for pid in nodes}
    for edge in edges:
        source, target = edge["source"], edge["target"]
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)
    return adjacency


def assign_degree(nodes: Dict[str, Node], edges: List[Edge]) -> Dict[str, int]:
    degree = {pid: 0 for pid in nodes}
    for edge in edges:
        degree[edge["source"]] = degree.get(edge["source"], 0) + 1
        degree[edge["target"]] = degree.get(edge["target"], 0) + 1
    for pid, value in degree.items():
        nodes[pid]["degree"] = value
    return degree


def detect_communities(nodes: Dict[str, Node], edges: List[Edge]) -> List[Dict[str, Any]]:
    if not nodes:
        return []
    adjacency = build_adjacency(nodes, edges)
    labels = {pid: pid for pid in nodes}
    for _ in range(20):
        changed = False
        previous = dict(labels)
        for pid in sorted(nodes):
            neighbor_labels = [previous[n] for n in sorted(adjacency.get(pid, set()))]
            if not neighbor_labels:
                new_label = previous[pid]
            else:
                counts = Counter(neighbor_labels)
                best_count = max(counts.values())
                new_label = min(label for label, count in counts.items() if count == best_count)
            labels[pid] = new_label
            changed = changed or new_label != previous[pid]
        if not changed:
            break

    groups: Dict[str, List[str]] = defaultdict(list)
    for pid, label in labels.items():
        groups[label].append(pid)
    ordered_groups = sorted((sorted(ids) for ids in groups.values()), key=lambda ids: ids[0])
    degree = {pid: int(nodes[pid].get("degree", 0)) for pid in nodes}
    communities: List[Dict[str, Any]] = []
    for cid, ids in enumerate(ordered_groups):
        for pid in ids:
            nodes[pid]["community"] = cid
        top_nodes = sorted(ids, key=lambda pid: (-degree.get(pid, 0), pid))[:5]
        communities.append({"id": cid, "size": len(ids), "top_nodes": top_nodes})
    return communities


def build_graph(root: Path, schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    docs = scan_wiki_docs(root)
    redirects = build_redirect_map(docs)
    nodes, unknown_types = build_nodes(docs, schema)
    wikilink_lookup = build_wikilink_lookup(root, docs, redirects)
    edges, dangling, ambiguous = build_edges(docs, nodes, redirects, wikilink_lookup)
    assign_degree(nodes, edges)
    communities = detect_communities(nodes, edges)

    sorted_nodes = [nodes[pid] for pid in sorted(nodes)]
    sorted_edges = sorted(edges, key=lambda item: (item["source"], item["target"], item["relation"], item["source_kind"]))
    sorted_communities = sorted(communities, key=lambda item: item["id"])
    canonical = {"nodes": sorted_nodes, "edges": sorted_edges, "communities": sorted_communities}
    canonical_json = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    graph = {
        "version": VERSION,
        "generated_at": now_iso(),
        "content_hash": content_hash,
        "stats": {
            "nodes": len(sorted_nodes),
            "edges": len(sorted_edges),
            "communities": len(sorted_communities),
        },
        "nodes": sorted_nodes,
        "edges": sorted_edges,
        "communities": sorted_communities,
    }
    meta = {
        "dangling_wikilinks": dangling,
        "ambiguous_wikilinks": ambiguous,
        "type_counts": Counter(str(node.get("type")) for node in sorted_nodes),
        "unknown_type_pages": unknown_types,
    }
    return graph, meta


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def table_or_none(rows: List[str]) -> List[str]:
    return rows if rows else ["- (none)"]


def render_graph_overview(graph: Dict[str, Any], meta: Dict[str, Any]) -> str:
    lines = [
        "# Knowledge Graph",
        "",
        f"generated_at: {graph['generated_at']}",
        f"content_hash: {graph['content_hash']}",
        "",
        "## Stats",
        "",
        f"- Nodes: {graph['stats']['nodes']}",
        f"- Edges: {graph['stats']['edges']}",
        f"- Communities: {graph['stats']['communities']}",
        "",
        "## Type Distribution",
        "",
        "| type | count |",
        "| --- | ---: |",
    ]
    for page_type, count in sorted(meta["type_counts"].items()):
        lines.append(f"| {page_type} | {count} |")
    if not meta["type_counts"]:
        lines.append("| (none) | 0 |")
    lines.extend(["", "## Communities", ""])
    for community in graph["communities"]:
        top = ", ".join(community["top_nodes"]) or "(none)"
        lines.append(f"- {community['id']}: size {community['size']} · top {top}")
    if not graph["communities"]:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def render_insights(graph: Dict[str, Any], meta: Dict[str, Any]) -> str:
    nodes = graph["nodes"]
    edges = graph["edges"]
    node_by_id = {node["id"]: node for node in nodes}
    isolated = [node["id"] for node in nodes if node.get("degree") == 0]
    hubs = sorted(nodes, key=lambda item: (-int(item.get("degree", 0)), item["id"]))[:10]
    largest = sorted(graph["communities"], key=lambda item: (-item["size"], item["id"]))[:5]
    cross_type = []
    for edge in edges:
        source_type = node_by_id.get(edge["source"], {}).get("type")
        target_type = node_by_id.get(edge["target"], {}).get("type")
        if source_type != target_type:
            cross_type.append(f"- {edge['source']} -> {edge['target']} ({source_type} -> {target_type}, {edge['relation']})")
    dangling = [
        f"- {item['target']} (from {item['source']}, {item['file']})"
        for item in meta["dangling_wikilinks"]
    ]
    ambiguous = [
        f"- {item['target']} (from {item['source']}, {item['file']})"
        for item in meta.get("ambiguous_wikilinks", [])
    ]
    unknown = [
        f"- unknown type {item['type']} (id {item['id']}, {item['file']})"
        for item in meta.get("unknown_type_pages", [])
    ]

    lines = [
        "# Graph Insights",
        "",
        f"generated_at: {graph['generated_at']}",
        "",
        "## Isolated Nodes",
        "",
        *table_or_none([f"- {pid}" for pid in isolated]),
        "",
        "## High Centrality Hubs",
        "",
        *table_or_none([f"- {node['id']} · degree {node['degree']}" for node in hubs if node.get("degree", 0) > 0]),
        "",
        "## Largest Communities",
        "",
        *table_or_none([f"- {item['id']} · size {item['size']} · top {', '.join(item['top_nodes'])}" for item in largest]),
        "",
        "## Cross-Type Connections",
        "",
        *table_or_none(cross_type[:20]),
        "",
        "## Dangling Wikilinks",
        "",
        *table_or_none(dangling),
        "",
        "## Ambiguous Wikilinks",
        "",
        *table_or_none(ambiguous),
        "",
        "## Unknown Types",
        "",
        *table_or_none(unknown),
    ]
    return "\n".join(lines) + "\n"


def write_maps(root: Path, graph: Dict[str, Any], meta: Dict[str, Any]) -> None:
    maps_root = root / "maps"
    write_json_atomic(maps_root / "graph-data.json", graph)
    write_text_atomic(maps_root / "knowledge-graph.md", render_graph_overview(graph, meta))
    write_text_atomic(maps_root / "graph-insights.md", render_insights(graph, meta))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build llm-wiki graph projection")
    parser.add_argument("--root", help="实例根目录；缺省为 ./knowledge")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    root = instance_root(find_root(), args.root)
    schema, active_profile = load_effective_schema(root)
    print(f"wiki-graph instance root: {root} · profile: {active_profile}", file=sys.stderr)
    graph, meta = build_graph(root, schema)
    if args.json_output:
        print(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        write_maps(root, graph, meta)
        print(
            "wiki-graph: "
            f"{graph['stats']['nodes']} nodes, {graph['stats']['edges']} edges, "
            f"{graph['stats']['communities']} communities"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
