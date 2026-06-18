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


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def init_instance(root: Path, *, hard=None, soft=None, default_visibility: str = "internal") -> None:
    for directory in [
        "wiki/topics",
        "wiki/sources",
        "wiki/entities",
        "inbox/archive/promoted",
        "inbox/archive/dropped",
        "raw/dropbox",
        "raw/sources",
        ".wiki",
        "maps",
    ]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for name in ["purpose.md", "index.md", "overview.md", "log.md"]:
        write(root / name, f"# {name}\n")
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-10T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-10T00:00:00+08:00"}\n')
    policy = {
        "version": 1,
        "auto_capture": False,
        "default_visibility": default_visibility,
        "hard_redact": {"patterns": list(hard or [])},
        "soft_redact": {"patterns": list(soft or [])},
        "exclude_paths": [],
        "max_inbox_files": 100,
        "updated_at": "2026-06-10T00:00:00+08:00",
    }
    write(root / ".wiki/capture_policy.json", json.dumps(policy, ensure_ascii=False, indent=2) + "\n")


def run_lint(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), "--check-only", *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


def lint_json(root: Path, *args: str) -> dict:
    result = run_lint(root, "--json", *args)
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stderr + result.stdout)
    return json.loads(result.stdout)


def snapshot_derived(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for base in [root / ".wiki", root / "maps"]:
        if not base.exists():
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            result[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8", errors="replace")
    return result


class Task024DropboxPiiTest(unittest.TestCase):
    def test_dropbox_hard_redact_blocks_scan_wiki_pii(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=[r"AKIA[0-9A-Z]{16}"])
            write(root / "raw/dropbox/20260610-secret/note.md", "credential AKIA1234567890ABCDEF\n")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual(["HARD_REDACT_HIT"], [item["code"] for item in data["errors"]])
            self.assertEqual("raw/dropbox/20260610-secret/note.md", data["errors"][0]["file"])
            self.assertEqual(1, data["scanned"]["dropbox_texts"])

    def test_dropbox_soft_redact_warns_and_inherits_default_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, soft=[r"team@example\.com"], default_visibility="internal")
            write(root / "raw/dropbox/20260610-contact/info.txt", "contact team@example.com\n")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual([], data["errors"])
            warnings = [item for item in data["warnings"] if item["code"] == "SOFT_REDACT_HIT"]
            self.assertEqual(1, len(warnings))
            self.assertEqual("raw/dropbox/20260610-contact/info.txt", warnings[0]["file"])
            self.assertIn("按库策略", warnings[0]["hint"])

    def test_clean_dropbox_has_no_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"], soft=["SOFT"])
            write(root / "raw/dropbox/20260610-clean/readme.md", "clean material\n")

            result = run_lint(root, "--scan-wiki-pii")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertIn("脱敏扫描（inbox/archive + wiki + dropbox）: 0 命中", result.stdout)

    def test_binary_extensions_are_skipped_and_code_like_files_are_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write(root / "raw/dropbox/20260610-binary/image.png", "SECRET in skipped png\n")
            write(root / "raw/dropbox/20260610-binary/doc.pdf", "SECRET in skipped pdf\n")
            write(root / "raw/dropbox/20260610-text/query.sql", "select 'SECRET';\n")
            write(root / "raw/dropbox/20260610-text/app.env", "PASSWORD=SECRET\n")
            write(root / "raw/dropbox/20260610-text/tool.py", "password = 'SECRET'\n")
            write(root / "raw/dropbox/20260610-text/noext", "SECRET in no suffix\n")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual(["HARD_REDACT_HIT"] * 4, [item["code"] for item in data["errors"]])
            self.assertEqual(
                [
                    "raw/dropbox/20260610-text/app.env",
                    "raw/dropbox/20260610-text/noext",
                    "raw/dropbox/20260610-text/query.sql",
                    "raw/dropbox/20260610-text/tool.py",
                ],
                sorted(item["file"] for item in data["errors"]),
            )
            self.assertEqual([], [item for item in data["warnings"] if item["code"] in {"SOFT_REDACT_HIT", "DROPBOX_DECODE_FAILED"}])
            self.assertEqual(4, data["scanned"]["dropbox_texts"])

    def test_non_utf8_text_file_warns_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write_bytes(root / "raw/dropbox/20260610-gbk/bad.txt", b"\xff\xfe\x00SECRET")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual([], data["errors"])
            warnings = [item for item in data["warnings"] if item["code"] == "DROPBOX_DECODE_FAILED"]
            self.assertEqual(1, len(warnings))
            self.assertEqual("raw/dropbox/20260610-gbk/bad.txt", warnings[0]["file"])
            self.assertIn("人工核查", warnings[0]["hint"])
            self.assertEqual(0, data["scanned"]["dropbox_texts"])

    def test_plain_lint_ignores_dropbox_even_when_it_contains_hard_redact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write(root / "raw/dropbox/20260610-secret/note.md", "SECRET\n")

            data = lint_json(root)
            self.assertEqual([], data["errors"])
            self.assertNotIn("HARD_REDACT_HIT", [item["code"] for item in data["warnings"]])
            self.assertEqual(0, data["scanned"]["dropbox_texts"])

    def test_check_only_does_not_write_derived_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write(root / "raw/dropbox/20260610-clean/readme.md", "clean material\n")
            before = snapshot_derived(root)

            result = run_lint(root, "--scan-wiki-pii")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertEqual(before, snapshot_derived(root))


if __name__ == "__main__":
    unittest.main()
