import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/wiki_init.py"
SOURCE_SCHEMA = REPO / "knowledge/.wiki-schema.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_init(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


def parse_report(stdout: str) -> dict[str, str]:
    report = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            report[key] = value
    return report


def sync_data(root: Path) -> dict:
    return json.loads((root / ".wiki/schema_sync.json").read_text(encoding="utf-8"))


class Task021bSyncSchemaProtectionTest(unittest.TestCase):
    def assert_no_temp_files(self, root: Path) -> None:
        temps = [path.relative_to(root).as_posix() for path in root.rglob("*.tmp")]
        self.assertEqual([], temps)

    def test_missing_target_writes_schema_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("created", report["action"])
            self.assertEqual("null", report["old_sha256"])
            self.assertEqual(sha256(SOURCE_SCHEMA), report["new_sha256"])
            self.assertEqual(SOURCE_SCHEMA.read_bytes(), (root / ".wiki-schema.md").read_bytes())
            self.assertEqual(sha256(SOURCE_SCHEMA), sync_data(root)["last_synced_engine_sha256"])
            self.assert_no_temp_files(root)

    def test_equal_target_noops_when_metadata_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_init("--sync-schema", "--root", str(root))
            target = root / ".wiki-schema.md"
            sync_path = root / ".wiki/schema_sync.json"
            before_schema_mtime = target.stat().st_mtime_ns
            before_sync_mtime = sync_path.stat().st_mtime_ns

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("unchanged", report["action"])
            self.assertEqual(before_schema_mtime, target.stat().st_mtime_ns)
            self.assertEqual(before_sync_mtime, sync_path.stat().st_mtime_ns)

    def test_equal_target_repairs_missing_metadata_without_touching_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".wiki-schema.md"
            target.write_bytes(SOURCE_SCHEMA.read_bytes())
            before_mtime = target.stat().st_mtime_ns

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("metadata_repaired", report["action"])
            self.assertEqual(before_mtime, target.stat().st_mtime_ns)
            self.assertEqual(sha256(SOURCE_SCHEMA), sync_data(root)["last_synced_engine_sha256"])

    def test_last_synced_match_allows_safe_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki").mkdir()
            target = root / ".wiki-schema.md"
            old_bytes = b"old synced schema\n"
            target.write_bytes(old_bytes)
            old_sha = hashlib.sha256(old_bytes).hexdigest()
            (root / ".wiki/schema_sync.json").write_text(
                json.dumps({"version": 1, "last_synced_engine_sha256": old_sha, "updated_at": "2026-06-09T00:00:00+08:00"})
                + "\n",
                encoding="utf-8",
            )

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("replaced", report["action"])
            self.assertEqual(old_sha, report["old_sha256"])
            self.assertEqual(SOURCE_SCHEMA.read_bytes(), target.read_bytes())
            self.assertEqual(sha256(SOURCE_SCHEMA), sync_data(root)["last_synced_engine_sha256"])

    def test_local_change_without_record_refuses_and_prints_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".wiki-schema.md"
            target.write_text("local schema\n", encoding="utf-8")
            old_sha = sha256(target)

            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(1, result.returncode)
            report = parse_report(result.stdout)
            self.assertEqual("refused", report["action"])
            self.assertEqual(old_sha, report["old_sha256"])
            self.assertIn("sync refused", result.stderr)
            self.assertIn("---", result.stderr)
            self.assertIn("+++", result.stderr)
            self.assertEqual("local schema\n", target.read_text(encoding="utf-8"))

    def test_force_overwrites_local_change_and_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".wiki-schema.md"
            target.write_text("local schema\n", encoding="utf-8")

            result = run_init("--sync-schema", "--force", "--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = parse_report(result.stdout)
            self.assertEqual("forced", report["action"])
            self.assertEqual(SOURCE_SCHEMA.read_bytes(), target.read_bytes())
            self.assertEqual(sha256(SOURCE_SCHEMA), sync_data(root)["last_synced_engine_sha256"])
            self.assert_no_temp_files(root)

    def test_force_requires_sync_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_init("--force", "--root", str(root))
            self.assertEqual(2, result.returncode)
            self.assertIn("--force requires --sync-schema", result.stderr)

    def test_directory_sync_metadata_is_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki/schema_sync.json").mkdir(parents=True)
            result = run_init("--sync-schema", "--root", str(root))
            self.assertEqual(2, result.returncode)
            self.assertIn("schema_sync.json must be a file", result.stderr)


if __name__ == "__main__":
    unittest.main()
