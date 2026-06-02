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
        '{"version":1,"auto_capture":false,"exclude_patterns":[],"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-01-01T00:00:00+08:00"}\n',
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
    last_verified: str = "2026-06-01",
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
        f"last_verified: {last_verified}",
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


def eval_root(root: Path) -> dict:
    return wiki_eval.evaluate(root, now=date(2026, 6, 2))


def run_eval(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_eval.py"), "--root", str(root), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


class Task014EvalTest(unittest.TestCase):
    def test_fixture_a_all_green_scores_100(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b")

            result = eval_root(root)
            self.assertEqual(100, result["score"])
            self.assertEqual({"integrity": 100, "freshness": 100, "endorsement": 100, "connectivity": 100}, result["dims"])
            self.assertEqual("ok", result["status"])
            self.assertEqual(0, result["lint_errors"])
            self.assertEqual(0, result["graph_errors"])

    def test_fixture_b_endorsement_low_is_weakest_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", review=False, related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b", review=True)

            result = eval_root(root)
            self.assertEqual(50, result["dims"]["endorsement"])
            self.assertEqual("endorsement", result["weakest_dim"])
            self.assertEqual(90, result["score"])

    def test_fixture_c_integrity_formula_counts_dangling_by_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", related_ids=["top_20260601_b"], body="[[missing-target]]")
            page(root, "wiki/topics/b.md", pid="top_20260601_b")

            result = eval_root(root)
            self.assertEqual(75, result["dims"]["integrity"])
            self.assertEqual(90, result["score"])
            self.assertEqual(1, len(result["graph"]["dangling_wikilinks"]))

    def test_empty_instance_has_null_score_check_zero_and_no_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)

            result = eval_root(root)
            self.assertEqual("empty", result["status"])
            self.assertIsNone(result["score"])
            self.assertIsNone(result["dims"])

            check = run_eval(root, "--check")
            self.assertEqual(0, check.returncode, check.stderr + check.stdout)

            snapshot = run_eval(root, "--snapshot")
            self.assertEqual(0, snapshot.returncode, snapshot.stderr + snapshot.stdout)
            self.assertFalse((root / ".wiki/eval_history.jsonl").exists())

    def test_snapshot_appends_for_non_empty_ok_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b")

            first = run_eval(root, "--snapshot")
            second = run_eval(root, "--snapshot")
            self.assertEqual(0, first.returncode, first.stderr + first.stdout)
            self.assertEqual(0, second.returncode, second.stderr + second.stdout)

            lines = (root / ".wiki/eval_history.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(2, len(lines))
            entries = [json.loads(line) for line in lines]
            self.assertEqual([100, 100], [item["score"] for item in entries])
            self.assertEqual([2, 2], [item["pages"] for item in entries])

    def test_check_requires_zero_lint_errors_even_when_score_is_high(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            for index in range(10):
                extra = "updated: not-a-date" if index == 0 else ""
                page(
                    root,
                    f"wiki/topics/page-{index}.md",
                    pid=f"top_20260601_page-{index}",
                    related_ids=[f"top_20260601_page-{(index + 1) % 10}"],
                    extra=extra,
                )

            result = eval_root(root)
            self.assertGreaterEqual(result["score"], 70)
            self.assertGreater(result["lint_errors"], 0)
            check = run_eval(root, "--check")
            self.assertEqual(1, check.returncode, check.stdout)

    def test_deterministic_except_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b")

            first = eval_root(root)
            second = eval_root(root)
            for item in (first, second):
                item.pop("ts", None)
                item["lint"].pop("warnings", None)
            self.assertEqual(first, second)

    def test_multi_root_calls_do_not_leak_lint_global_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root_a = Path(tmp) / "a"
            root_b = Path(tmp) / "b"
            init_instance(root_a)
            init_instance(root_b)
            page(root_a, "wiki/topics/a.md", pid="top_20260601_a", related_ids=["top_20260601_b"])
            page(root_a, "wiki/topics/b.md", pid="top_20260601_b")
            page(root_b, "wiki/topics/a.md", pid="top_20260601_a", review=False, related_ids=["top_20260601_b"])
            page(root_b, "wiki/topics/b.md", pid="top_20260601_b", review=True)

            first_a = eval_root(root_a)
            result_b = eval_root(root_b)
            second_a = eval_root(root_a)
            self.assertEqual(100, first_a["score"])
            self.assertEqual(90, result_b["score"])
            self.assertEqual(first_a["score"], second_a["score"])
            self.assertEqual(first_a["dims"], second_a["dims"])

    def test_json_smoke_and_eval_does_not_write_derived_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "wiki/topics/a.md", pid="top_20260601_a", related_ids=["top_20260601_b"])
            page(root, "wiki/topics/b.md", pid="top_20260601_b")
            before = sorted(path.relative_to(root).as_posix() for path in (root / ".wiki").glob("**/*") if path.is_file())
            before += sorted(path.relative_to(root).as_posix() for path in (root / "maps").glob("**/*") if path.is_file())

            result = run_eval(root, "--json")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(100, data["score"])
            self.assertIn("dims", data)

            after = sorted(path.relative_to(root).as_posix() for path in (root / ".wiki").glob("**/*") if path.is_file())
            after += sorted(path.relative_to(root).as_posix() for path in (root / "maps").glob("**/*") if path.is_file())
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
