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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-18T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-18T00:00:00+08:00"}\n')
    policy = {
        "version": 1,
        "auto_capture": False,
        "default_visibility": default_visibility,
        "hard_redact": {"patterns": list(hard or [])},
        "soft_redact": {"patterns": list(soft or [])},
        "exclude_paths": [],
        "max_inbox_files": 100,
        "updated_at": "2026-06-18T00:00:00+08:00",
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


class Task027DropboxBinaryBlocklistTest(unittest.TestCase):
    def test_code_and_config_extensions_are_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=[r"AKIA[0-9A-Z]{16}", r"password\s*="])
            write(root / "raw/dropbox/code/query.sql", "select 'AKIA1234567890ABCDEF';\n")
            write(root / "raw/dropbox/code/app.env", "password=unsafe\n")
            write(root / "raw/dropbox/code/script.py", "print('AKIA1234567890ABCDEF')\n")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual(["HARD_REDACT_HIT"] * 3, [item["code"] for item in data["errors"]])
            self.assertEqual(
                ["raw/dropbox/code/app.env", "raw/dropbox/code/query.sql", "raw/dropbox/code/script.py"],
                sorted(item["file"] for item in data["errors"]),
            )
            self.assertEqual(3, data["scanned"]["dropbox_texts"])

    def test_binary_extensions_are_skipped_without_decode_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write_bytes(root / "raw/dropbox/bin/image.png", b"\xff\xfeSECRET")
            write_bytes(root / "raw/dropbox/bin/manual.pdf", b"\xff\xfeSECRET")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual([], data["errors"])
            self.assertEqual([], [item for item in data["warnings"] if item["code"] == "DROPBOX_DECODE_FAILED"])
            self.assertEqual(0, data["scanned"]["dropbox_texts"])

    def test_svg_and_no_suffix_are_treated_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write(root / "raw/dropbox/text/diagram.svg", "<svg><text>SECRET</text></svg>\n")
            write(root / "raw/dropbox/text/noext", "SECRET\n")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual(["HARD_REDACT_HIT", "HARD_REDACT_HIT"], [item["code"] for item in data["errors"]])
            self.assertEqual(["raw/dropbox/text/diagram.svg", "raw/dropbox/text/noext"], sorted(item["file"] for item in data["errors"]))
            self.assertEqual(2, data["scanned"]["dropbox_texts"])

    def test_non_utf8_non_binary_extension_warns_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write_bytes(root / "raw/dropbox/bad/broken.sql", b"\xff\xfe\x00SECRET")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual([], data["errors"])
            warnings = [item for item in data["warnings"] if item["code"] == "DROPBOX_DECODE_FAILED"]
            self.assertEqual(1, len(warnings))
            self.assertEqual("raw/dropbox/bad/broken.sql", warnings[0]["file"])
            self.assertEqual(0, data["scanned"]["dropbox_texts"])

    def test_python_soft_redact_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, soft=[r"team@example\.com"], default_visibility="internal")
            write(root / "raw/dropbox/code/tool.py", "owner = 'team@example.com'\n")

            data = lint_json(root, "--scan-wiki-pii")
            warnings = [item for item in data["warnings"] if item["code"] == "SOFT_REDACT_HIT"]
            self.assertEqual([], data["errors"])
            self.assertEqual(1, len(warnings))
            self.assertEqual("raw/dropbox/code/tool.py", warnings[0]["file"])
            self.assertEqual(1, data["scanned"]["dropbox_texts"])

    def test_plain_lint_still_ignores_dropbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, hard=["SECRET"])
            write(root / "raw/dropbox/code/query.sql", "SECRET\n")

            data = lint_json(root)
            self.assertEqual([], data["errors"])
            self.assertEqual(0, data["scanned"]["dropbox_texts"])


if __name__ == "__main__":
    unittest.main()
