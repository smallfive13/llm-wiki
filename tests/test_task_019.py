import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

sys.path.insert(0, str(SCRIPTS))
from wiki_common import BASE_SCHEMA, ingest_progress  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def source(index: int, status: str) -> dict:
    return {
        "source_id": f"src_20260605_batch-{index}",
        "title": f"Batch Source {index}",
        "source_type": "manual",
        "hash_sha256": HASH,
        "original_path": f"raw/sources/batch-{index}.md",
        "source_url": None,
        "imported_at": "2026-06-05T00:00:00+08:00",
        "last_ingested_at": "2026-06-05T00:00:00+08:00",
        "status": status,
        "summary_page_id": None,
        "summary_page_path": None,
        "adapter": "manual",
    }


def init_instance(root: Path, statuses: list[str]) -> None:
    for directory in [
        "wiki/sources",
        "wiki/topics",
        "wiki/entities",
        "inbox/archive/promoted",
        "inbox/archive/dropped",
        "raw",
        ".wiki",
        "maps",
    ]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for name in ["purpose.md", "index.md", "overview.md", "log.md"]:
        write(root / name, f"# {name}\n")
    sources = [source(index, status) for index, status in enumerate(statuses, start=1)]
    write(
        root / "raw/source_manifest.json",
        json.dumps({"version": 1, "sources": sources, "updated_at": "2026-06-05T00:00:00+08:00"}, ensure_ascii=False) + "\n",
    )
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-05T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        '{"version":1,"auto_capture":false,"default_visibility":"private","hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-06-05T00:00:00+08:00"}\n',
    )


def run_lint(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


def snapshot_files(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for base in [root / ".wiki", root / "maps"]:
        if not base.exists():
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            result[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return result


class Task019IngestProgressTest(unittest.TestCase):
    def test_progress_empty_manifest(self) -> None:
        statuses = list(BASE_SCHEMA["json_contracts"]["source_manifest"]["statuses"])
        progress = ingest_progress({"sources": []}, statuses)
        self.assertEqual({status: 0 for status in statuses}, progress["counts"])
        self.assertEqual(0, progress["pending_apply_count"])
        self.assertEqual([], progress["pending_apply"])

    def test_progress_all_ingested_has_no_pending(self) -> None:
        statuses = list(BASE_SCHEMA["json_contracts"]["source_manifest"]["statuses"])
        manifest = {"sources": [source(1, "ingested"), source(2, "ingested")]}
        progress = ingest_progress(manifest, statuses)
        self.assertEqual(2, progress["counts"]["ingested"])
        self.assertEqual([], progress["pending_apply"])

    def test_progress_mixed_statuses_only_pending_triaged(self) -> None:
        statuses = list(BASE_SCHEMA["json_contracts"]["source_manifest"]["statuses"])
        manifest = {"sources": [source(1, "new"), source(2, "triaged"), source(3, "failed"), source(4, "triaged"), source(5, "ingested")]}
        progress = ingest_progress(manifest, statuses)
        self.assertEqual(1, progress["counts"]["new"])
        self.assertEqual(2, progress["counts"]["triaged"])
        self.assertEqual(1, progress["counts"]["failed"])
        self.assertEqual(1, progress["counts"]["ingested"])
        self.assertEqual(["src_20260605_batch-2", "src_20260605_batch-4"], [item["source_id"] for item in progress["pending_apply"]])

    def test_ingest_status_json_reports_invalid_status_and_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, ["bogus", "triaged"])

            result = run_lint(root, "--ingest-status", "--json")
            self.assertEqual(1, result.returncode, result.stderr + result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(1, data["ingest_progress"]["other_count"])
            self.assertEqual(1, data["ingest_progress"]["pending_apply_count"])
            self.assertEqual("src_20260605_batch-2", data["ingest_progress"]["pending_apply"][0]["source_id"])
            status_errors = [item for item in data["errors"] if item["code"] == "ENUM_INVALID" and item["field"] == "status"]
            self.assertEqual(1, len(status_errors))

    def test_ingest_status_does_not_write_derived_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, ["triaged", "ingested"])
            before = snapshot_files(root)

            result = run_lint(root, "--ingest-status")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertIn("ingest 进度", result.stdout)
            self.assertIn("triaged 待 apply: 1", result.stdout)
            self.assertEqual(before, snapshot_files(root))

    def test_ingest_status_ignores_unrelated_wiki_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, ["triaged"])
            write(root / "wiki/topics/bad.md", "# Bad page without frontmatter\n")

            status_result = run_lint(root, "--ingest-status", "--json")
            self.assertEqual(0, status_result.returncode, status_result.stderr + status_result.stdout)
            status_data = json.loads(status_result.stdout)
            self.assertEqual([], status_data["errors"])

            normal_result = run_lint(root, "--check-only", "--json")
            self.assertEqual(1, normal_result.returncode, normal_result.stderr + normal_result.stdout)


if __name__ == "__main__":
    unittest.main()
