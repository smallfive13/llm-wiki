import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import wiki_graph  # noqa: E402
from wiki_common import BASE_SCHEMA, merge_schema  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path, profile: bool = False) -> None:
    for directory in [
        "wiki/topics",
        "wiki/entities",
        "wiki/sources",
        "wiki/decisions",
        "wiki/synthesis",
        "wiki/comparisons",
        "wiki/open-questions",
        "wiki/queries",
        "inbox/archive/promoted",
        "inbox/archive/dropped",
        "raw",
        ".wiki",
        "maps",
    ]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for name in ["purpose.md", "index.md", "overview.md", "log.md"]:
        write(root / name, f"# {name}\n")
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-01-01T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-01-01T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        '{"version":1,"auto_capture":false,"exclude_patterns":[],"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-01-01T00:00:00+08:00"}\n',
    )
    if profile:
        write(
            root / ".wiki-profile.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "profile": "case-profile",
                    "extra_page_types": [
                        {"type": "case", "id_prefix": "case", "dir": "wiki/cases", "required_fields": [], "optional_fields": []}
                    ],
                    "extra_field_enums": {},
                    "extra_optional_fields": {},
                },
                ensure_ascii=False,
            )
            + "\n",
        )
        (root / "wiki/cases").mkdir(parents=True, exist_ok=True)


def page(
    root: Path,
    rel: str,
    *,
    pid: str,
    page_type: str = "topic",
    status: str = "active",
    confidence: str = "medium",
    review: bool = True,
    last_verified: str = "2026-01-01",
    related_ids=None,
    source_ids=None,
    extra: str = "",
) -> None:
    related_ids = related_ids or []
    source_ids = source_ids or []
    fm = [
        "---",
        f"id: {pid}",
        f"type: {page_type}",
        f"status: {status}",
        f"confidence: {confidence}",
        "created: 2026-01-01",
        "updated: 2026-01-01",
        f"last_verified: {last_verified}",
        f"review: {'true' if review else 'false'}",
    ]
    if source_ids:
        fm.extend(["source_ids:", *[f"  - {item}" for item in source_ids]])
    else:
        fm.append("source_ids: []")
    if related_ids:
        fm.extend(["related_ids:", *[f"  - {item}" for item in related_ids]])
    else:
        fm.append("related_ids: []")
    fm.extend(["sources: []", "related: []", "supersedes: []", "superseded_by: []", "evidence_count: 0"])
    if page_type == "entity":
        fm.extend(["aliases: []", "canonical_id: null"])
    if page_type == "source":
        fm.extend(
            [
                f"source_id: {pid}",
                "hash_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "original_path: raw/sources/example.md",
                "source_url: null",
                "imported_at: 2026-01-01T00:00:00+08:00",
            ]
        )
    if extra:
        fm.extend(extra.splitlines())
    fm.extend(["---", "", f"# {pid}", ""])
    write(root / rel, "\n".join(fm))


def lint_json(root: Path, now: str = "2026-05-02") -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "wiki_lint.py"),
            "--root",
            str(root),
            "--check-only",
            "--json",
            "--now",
            now,
        ],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stderr + result.stdout)
    return json.loads(result.stdout)


class Task012LintTest(unittest.TestCase):
    def test_stale_and_unverified_trigger_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, profile=True)
            page(root, "wiki/decisions/stale.md", pid="dec_20260101_stale", page_type="decision", last_verified="2026-01-01")
            page(root, "wiki/decisions/boundary.md", pid="dec_20260102_boundary", page_type="decision", last_verified="2026-01-02")
            for status in ["stale", "archived", "draft"]:
                page(root, f"wiki/topics/{status}.md", pid=f"top_20260101_{status}", status=status, last_verified="2025-01-01")
            page(root, "wiki/entities/canon.md", pid="ent_20260101_canon", page_type="entity", status="active", last_verified="2025-01-01")
            page(
                root,
                "wiki/entities/redirect.md",
                pid="ent_20260101_redirect",
                page_type="entity",
                status="redirect",
                last_verified="2025-01-01",
                extra="canonical_id: ent_20260101_canon",
            )
            page(root, "wiki/sources/source.md", pid="src_20260101_source", page_type="source", last_verified="2025-01-01")
            page(root, "wiki/queries/query.md", pid="que_20260101_query", page_type="query", last_verified="2025-01-01")
            page(root, "wiki/cases/case.md", pid="case_20260101_case", page_type="case", last_verified="2025-01-01")
            page(root, "wiki/topics/unverified.md", pid="top_20260101_unverified", confidence="high", review=False)
            page(root, "wiki/topics/reviewed.md", pid="top_20260101_reviewed", confidence="high", review=True)
            page(root, "wiki/topics/medium.md", pid="top_20260101_medium", confidence="medium", review=False)
            for status in ["stale", "archived", "draft"]:
                page(root, f"wiki/topics/unverified-{status}.md", pid=f"top_20260101_unverified-{status}", status=status, confidence="high", review=False)

            data = lint_json(root)
            self.assertEqual([], data["errors"])
            stale_files = {item["file"] for item in data["warnings"] if item["code"] == "STALE_PAGE"}
            unverified_files = {item["file"] for item in data["warnings"] if item["code"] == "UNVERIFIED_HIGH"}
            self.assertEqual({"wiki/decisions/stale.md", "wiki/entities/canon.md"}, stale_files)
            self.assertEqual({"wiki/topics/unverified.md"}, unverified_files)


class Task012GraphTest(unittest.TestCase):
    def test_related_edges_are_directed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260101_a", related_ids=["top_20260101_b"])
            page(root, "wiki/topics/b.md", pid="top_20260101_b")
            graph, _meta = wiki_graph.build_graph(root, BASE_SCHEMA)
            nodes = {node["id"]: node for node in graph["nodes"]}
            self.assertEqual(1, nodes["top_20260101_a"]["out_degree"])
            self.assertEqual(0, nodes["top_20260101_a"]["in_degree"])
            self.assertEqual(0, nodes["top_20260101_b"]["out_degree"])
            self.assertEqual(1, nodes["top_20260101_b"]["in_degree"])

            page(root, "wiki/topics/b.md", pid="top_20260101_b", related_ids=["top_20260101_a"])
            graph, _meta = wiki_graph.build_graph(root, BASE_SCHEMA)
            nodes = {node["id"]: node for node in graph["nodes"]}
            self.assertEqual(1, nodes["top_20260101_a"]["out_degree"])
            self.assertEqual(1, nodes["top_20260101_a"]["in_degree"])
            self.assertEqual(1, nodes["top_20260101_b"]["out_degree"])
            self.assertEqual(1, nodes["top_20260101_b"]["in_degree"])

    def test_co_source_keeps_degree_but_skips_in_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/sources/source.md", pid="src_20260101_source", page_type="source")
            page(root, "wiki/topics/a.md", pid="top_20260101_a", source_ids=["src_20260101_source"])
            page(root, "wiki/topics/b.md", pid="top_20260101_b", source_ids=["src_20260101_source"])
            graph, _meta = wiki_graph.build_graph(root, BASE_SCHEMA)
            nodes = {node["id"]: node for node in graph["nodes"]}
            self.assertEqual(2, nodes["top_20260101_a"]["degree"])
            self.assertEqual(1, nodes["top_20260101_a"]["out_degree"])
            self.assertEqual(0, nodes["top_20260101_a"]["in_degree"])
            self.assertEqual(2, nodes["src_20260101_source"]["in_degree"])


if __name__ == "__main__":
    unittest.main()
