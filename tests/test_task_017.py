import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    sources = []
    for index, status in enumerate(statuses, start=1):
        sources.append(
            {
                "source_id": f"src_20260604_status-{index}",
                "title": f"Status {index}",
                "source_type": "manual",
                "hash_sha256": HASH,
                "original_path": f"raw/sources/status-{index}.md",
                "source_url": None,
                "imported_at": "2026-06-04T00:00:00+08:00",
                "last_ingested_at": "2026-06-04T00:00:00+08:00",
                "status": status,
                "summary_page_id": None,
                "summary_page_path": None,
                "adapter": "manual",
            }
        )
    write(root / "raw/source_manifest.json", json.dumps({"version": 1, "sources": sources, "updated_at": "2026-06-04T00:00:00+08:00"}, ensure_ascii=False) + "\n")
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-04T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        '{"version":1,"auto_capture":false,"default_visibility":"private","hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-06-04T00:00:00+08:00"}\n',
    )


def lint_json(root: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), "--check-only", "--json"],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stderr + result.stdout)
    return result.returncode, json.loads(result.stdout)


class Task017SourceManifestStatusTest(unittest.TestCase):
    def test_superseded_and_archived_manifest_statuses_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, ["superseded", "archived"])

            code, data = lint_json(root)
            self.assertEqual(0, code)
            self.assertEqual([], data["errors"])

    def test_existing_manifest_statuses_remain_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, ["new", "triaged", "ingested", "skipped", "failed", "deleted"])

            code, data = lint_json(root)
            self.assertEqual(0, code)
            self.assertEqual([], data["errors"])

    def test_invalid_manifest_status_still_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, ["bogus"])

            code, data = lint_json(root)
            self.assertEqual(1, code)
            status_errors = [item for item in data["errors"] if item["code"] == "ENUM_INVALID" and item["field"] == "status"]
            self.assertEqual(1, len(status_errors))


if __name__ == "__main__":
    unittest.main()
