import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import wiki_eval  # noqa: E402
import wiki_graph  # noqa: E402
from wiki_common import BASE_SCHEMA  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path) -> None:
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
        '{"version":1,"auto_capture":false,"exclude_paths":[],"max_inbox_files":100,"default_visibility":"private","hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},"updated_at":"2026-01-01T00:00:00+08:00"}\n',
    )


def page(
    root: Path,
    rel: str,
    *,
    pid: str,
    page_type: str = "topic",
    status: str = "active",
    confidence: str = "high",
    review: bool = True,
    related_ids=None,
    body: str = "",
    extra: str = "",
) -> None:
    related_ids = related_ids or []
    lines = [
        "---",
        f"id: {pid}",
        f"type: {page_type}",
        f"status: {status}",
        f"confidence: {confidence}",
        "created: 2026-01-01",
        "updated: 2026-06-01",
        "last_verified: 2026-06-01",
        f"review: {'true' if review else 'false'}",
        "source_ids: []",
    ]
    if related_ids:
        lines.extend(["related_ids:", *[f"  - {item}" for item in related_ids]])
    else:
        lines.append("related_ids: []")
    lines.extend(["sources: []", "related: []", "supersedes: []", "superseded_by: []", "evidence_count: 0"])
    if page_type == "entity":
        lines.extend(["aliases: []", "canonical_id: null"])
    if page_type == "source":
        lines.extend(
            [
                f"source_id: {pid}",
                "hash_sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "original_path: raw/sources/example.md",
                "source_url: null",
                "imported_at: 2026-01-01T00:00:00+08:00",
            ]
        )
    if extra:
        lines.extend(extra.splitlines())
    lines.extend(["---", "", f"# {pid}", "", body])
    write(root / rel, "\n".join(lines))


def evaluate(root: Path) -> dict:
    return wiki_eval.evaluate(root, now=date(2026, 6, 2))


def run_eval(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_eval.py"), "--root", str(root), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


class Task026ReviewCoverageTest(unittest.TestCase):
    def test_all_unreviewed_eligible_scores_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", review=False, related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b", review=False)

            result = evaluate(root)
            self.assertEqual(0, result["dims"]["endorsement"])
            self.assertEqual({"eligible": 2, "reviewed": 0, "percent": 0}, {key: result["review_coverage"][key] for key in ["eligible", "reviewed", "percent"]})
            self.assertEqual(80, result["score"])

    def test_half_reviewed_remains_fifty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", review=True, related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b", review=False)

            result = evaluate(root)
            self.assertEqual(50, result["dims"]["endorsement"])
            self.assertEqual(1, result["review_coverage"]["reviewed"])
            self.assertEqual(2, result["review_coverage"]["eligible"])

    def test_no_eligible_source_query_only_scores_hundred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/sources/a.md", pid="src_20260601_a", page_type="source", review=False, related_ids=["que_20260601_q"])
            page(root, "wiki/queries/q.md", pid="que_20260601_q", page_type="query", review=False)

            result = evaluate(root)
            self.assertEqual(100, result["dims"]["endorsement"])
            self.assertEqual(0, result["review_coverage"]["eligible"])
            self.assertEqual([], result["review_coverage"]["unreviewed"])

    def test_empty_instance_does_not_crash_and_has_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)

            result = evaluate(root)
            self.assertEqual("empty", result["status"])
            self.assertIsNone(result["score"])
            self.assertEqual({"eligible": 0, "reviewed": 0, "percent": 100, "unreviewed": []}, result["review_coverage"])

    def test_high_pages_are_counted_as_eligible_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/high.md", pid="top_20260601_high", confidence="high", review=True, related_ids=["top_20260601_medium"])
            page(root, "wiki/topics/medium.md", pid="top_20260601_medium", confidence="medium", review=False)

            result = evaluate(root)
            self.assertEqual(50, result["dims"]["endorsement"])
            self.assertEqual(2, result["review_coverage"]["eligible"])
            self.assertEqual(1, result["review_coverage"]["reviewed"])
            self.assertEqual(["top_20260601_medium"], [item["id"] for item in result["review_coverage"]["unreviewed"]])

    def test_json_review_coverage_and_unreviewed_sorting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/hub.md", pid="top_20260601_hub", review=False)
            page(root, "wiki/topics/low.md", pid="top_20260601_low", review=False)
            page(root, "wiki/topics/support-1.md", pid="top_20260601_support-1", review=True, related_ids=["top_20260601_hub"])
            page(root, "wiki/topics/support-2.md", pid="top_20260601_support-2", review=True, related_ids=["top_20260601_hub"])
            page(root, "wiki/topics/support-3.md", pid="top_20260601_support-3", review=True, related_ids=["top_20260601_low"])

            completed = run_eval(root, "--json")
            self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
            data = json.loads(completed.stdout)
            coverage = data["review_coverage"]
            self.assertEqual(5, coverage["eligible"])
            self.assertEqual(3, coverage["reviewed"])
            self.assertEqual(60, coverage["percent"])
            self.assertEqual(
                [
                    {"id": "top_20260601_hub", "type": "topic", "in_degree": 2, "out_degree": 0},
                    {"id": "top_20260601_low", "type": "topic", "in_degree": 1, "out_degree": 0},
                ],
                coverage["unreviewed"],
            )

    def test_graph_insights_has_unreviewed_list_and_keeps_high_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/high.md", pid="top_20260601_high", confidence="high", review=False)
            page(root, "wiki/topics/medium.md", pid="top_20260601_medium", confidence="medium", review=False)
            page(root, "wiki/topics/support-1.md", pid="top_20260601_support-1", review=True, related_ids=["top_20260601_high"])
            page(root, "wiki/topics/support-2.md", pid="top_20260601_support-2", review=True, related_ids=["top_20260601_medium"])
            page(root, "wiki/topics/support-3.md", pid="top_20260601_support-3", review=True, related_ids=["top_20260601_high"])

            graph, meta = wiki_graph.build_graph(root, BASE_SCHEMA)
            text = wiki_graph.render_insights(graph, meta, BASE_SCHEMA, date(2026, 6, 2))
            self.assertIn("reviewed-eligible 3/5", text)
            self.assertIn("### 未背书应背书页", text)
            self.assertIn("### High (Unverified)", text)
            unreviewed_section = text.split("### 未背书应背书页", 1)[1].split("### High (Unverified)", 1)[0]
            high_section = text.split("### High (Unverified)", 1)[1]
            high_section = high_section.split("## Isolated Nodes", 1)[0]
            self.assertLess(unreviewed_section.index("top_20260601_high"), unreviewed_section.index("top_20260601_medium"))
            self.assertIn("top_20260601_high", high_section)
            self.assertNotIn("top_20260601_medium", high_section)


if __name__ == "__main__":
    unittest.main()
