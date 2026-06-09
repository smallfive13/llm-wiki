import hashlib
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/wiki_init.py"
SOURCE_SCHEMA = REPO / "knowledge/.wiki-schema.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_init(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


def parse_report(stdout: str) -> dict:
    report = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            report[key] = value
    return report


def file_snapshot(root: Path) -> dict:
    snapshot = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root).as_posix()
        snapshot[rel] = (sha256(path), path.stat().st_mtime_ns)
    return snapshot


class Task015SyncSchemaTest(unittest.TestCase):
    def test_sync_schema_refuses_existing_file_without_sync_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".wiki-schema.md"
            target.write_text("old schema\n", encoding="utf-8")
            old_sha = sha256(target)

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(1, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("refused", report["action"])
            self.assertEqual(old_sha, report["old_sha256"])
            self.assertEqual(sha256(SOURCE_SCHEMA), report["new_sha256"])
            self.assertEqual("old schema\n", target.read_text(encoding="utf-8"))

    def test_sync_schema_creates_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("created", report["action"])
            self.assertEqual("null", report["old_sha256"])
            self.assertEqual(sha256(SOURCE_SCHEMA), report["new_sha256"])
            self.assertEqual(SOURCE_SCHEMA.read_text(encoding="utf-8"), (root / ".wiki-schema.md").read_text(encoding="utf-8"))

    def test_sync_schema_unchanged_does_not_touch_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".wiki-schema.md"
            target.write_text(SOURCE_SCHEMA.read_text(encoding="utf-8"), encoding="utf-8")
            before_mtime = target.stat().st_mtime_ns
            time.sleep(0.01)

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("metadata_repaired", report["action"])
            self.assertEqual(before_mtime, target.stat().st_mtime_ns)
            self.assertTrue((root / ".wiki/schema_sync.json").is_file())

    def test_sync_schema_rejects_conflicting_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [
                ("--profile", "x"),
                ("--git",),
                ("--git-root", str(root)),
            ]
            for case in cases:
                with self.subTest(case=case):
                    result = run_init("--sync-schema", "--root", str(root), *case)
                    self.assertEqual(2, result.returncode)
                    self.assertIn("--sync-schema cannot be combined", result.stderr)

    def test_sync_schema_rejects_invalid_roots_and_directory_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            missing = base / "missing"
            result = run_init("--sync-schema", "--root", str(missing))
            self.assertEqual(2, result.returncode)
            self.assertIn("root must exist", result.stderr)

            file_root = base / "file-root"
            file_root.write_text("not dir\n", encoding="utf-8")
            result = run_init("--sync-schema", "--root", str(file_root))
            self.assertEqual(2, result.returncode)
            self.assertIn("root must exist", result.stderr)

            root = base / "root"
            (root / ".wiki-schema.md").mkdir(parents=True)
            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(2, result.returncode)
            self.assertIn("target .wiki-schema.md must be a file", result.stderr)

    def test_sync_schema_only_changes_schema_and_metadata_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki").mkdir()
            (root / ".obsidian").mkdir()
            (root / ".gitignore").write_text("keep\n", encoding="utf-8")
            (root / ".obsidian/app.json").write_text('{"userIgnoreFilters":[]}\n', encoding="utf-8")
            (root / ".wiki/capture_policy.json").write_text("{}\n", encoding="utf-8")
            (root / ".wiki-schema.md").write_text("old\n", encoding="utf-8")
            before = file_snapshot(root)

            result = run_init("--sync-schema", "--force", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            after = file_snapshot(root)

            changed = [rel for rel in sorted(before) if before.get(rel) != after.get(rel)]
            self.assertEqual([".wiki-schema.md"], changed)
            self.assertEqual({".wiki/schema_sync.json"}, set(after) - set(before))

    def test_new_instance_schema_has_no_parent_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "instance"
            result = run_init("--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            schema = (root / ".wiki-schema.md").read_text(encoding="utf-8")
            self.assertNotIn("](../", schema)


if __name__ == "__main__":
    unittest.main()
