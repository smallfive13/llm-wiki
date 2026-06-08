import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path, profile: dict | None = None) -> None:
    for directory in [
        "wiki/topics",
        "wiki/sources",
        "wiki/entities",
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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-08T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-08T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        (
            '{"version":1,"auto_capture":false,"default_visibility":"private",'
            '"hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},'
            '"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-06-08T00:00:00+08:00"}\n'
        ),
    )
    if profile is not None:
        write(root / ".wiki-profile.json", json.dumps(profile, ensure_ascii=False, indent=2) + "\n")


def profile(version_marker: object = 1) -> dict:
    data = {
        "profile": "case-profile",
        "description": "",
        "extra_page_types": [],
        "extra_field_enums": {},
        "extra_optional_fields": {},
    }
    if version_marker != "__missing__":
        data["schema_version"] = version_marker
    return data


def lint_json(root: Path) -> tuple[int, dict, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), "--check-only", "--json"],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        data = json.loads(result.stdout)
    else:
        data = {}
    return result.returncode, data, result.stderr


class Task021aProfileVersionTest(unittest.TestCase):
    def assert_profile_issue(self, version_marker: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, profile(version_marker))
            code, data, stderr = lint_json(root)
            self.assertEqual(1, code, stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertIn("errors", data)
            self.assertEqual(["PROFILE_SCHEMA_VERSION"], [item["code"] for item in data["errors"]])

    def test_profile_v1_is_compatible_with_base_v2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, profile(1))
            code, data, stderr = lint_json(root)
            self.assertEqual(0, code, stderr)
            self.assertEqual([], data["errors"])

    def test_profile_v2_is_compatible_with_base_v2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, profile(2))
            code, data, stderr = lint_json(root)
            self.assertEqual(0, code, stderr)
            self.assertEqual([], data["errors"])

    def test_profile_version_below_min_is_error(self) -> None:
        self.assert_profile_issue(0)

    def test_profile_version_above_base_is_error(self) -> None:
        self.assert_profile_issue(3)

    def test_profile_version_missing_is_error_without_traceback(self) -> None:
        self.assert_profile_issue("__missing__")

    def test_profile_version_non_int_is_error_without_traceback(self) -> None:
        for value in ["2", None, 2.0, True]:
            with self.subTest(value=value):
                self.assert_profile_issue(value)

    def test_base_instance_without_profile_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            code, data, stderr = lint_json(root)
            self.assertEqual(0, code, stderr)
            self.assertEqual([], data["errors"])


if __name__ == "__main__":
    unittest.main()
