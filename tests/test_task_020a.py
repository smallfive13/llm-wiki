import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"

sys.path.insert(0, str(SCRIPTS))
from wiki_common import (  # noqa: E402
    BASE_SCHEMA,
    DOC_CONSISTENCY_TARGETS,
    begin_doc_block,
    end_doc_block,
    generate_doc_block,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path, schema_text: str | None = None) -> None:
    for directory in [
        "wiki/topics",
        "wiki/sources",
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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-08T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-08T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        '{"version":1,"auto_capture":false,"default_visibility":"private","hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-06-08T00:00:00+08:00"}\n',
    )
    if schema_text is None:
        schema_text = (REPO / "knowledge/.wiki-schema.md").read_text(encoding="utf-8")
    write(root / ".wiki-schema.md", schema_text)


def run_lint(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


def replace_block_content(text: str, name: str, replacement: str) -> str:
    begin = begin_doc_block(name)
    end = end_doc_block(name)
    pattern = re.compile(f"{re.escape(begin)}\\n.*?\\n{re.escape(end)}", re.S)
    updated, count = pattern.subn(f"{begin}\n{replacement}\n{end}", text, count=1)
    if count != 1:
        raise AssertionError(f"block {name} not found")
    return updated


def block_outside_text(text: str, name: str) -> str:
    begin = begin_doc_block(name)
    end = end_doc_block(name)
    pattern = re.compile(f"({re.escape(begin)}\\n).*?(\\n{re.escape(end)})", re.S)
    updated, count = pattern.subn(r"\1<BLOCK>\2", text, count=1)
    if count != 1:
        raise AssertionError(f"block {name} not found")
    return updated


class Task020aDocConsistencyTest(unittest.TestCase):
    def test_generate_doc_block_is_deterministic_and_ordered(self) -> None:
        first = generate_doc_block("page-types")
        second = generate_doc_block("page-types")
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))
        source_pos = first.index("`source`")
        entity_pos = first.index("`entity`")
        topic_pos = first.index("`topic`")
        self.assertLess(source_pos, entity_pos)
        self.assertLess(entity_pos, topic_pos)

    def test_check_docs_aligned_instance_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            result = run_lint(root, "--check-docs")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertIn("错误: 0", result.stdout)

    def test_check_docs_reports_drift(self) -> None:
        schema = (REPO / "knowledge/.wiki-schema.md").read_text(encoding="utf-8")
        schema = replace_block_content(schema, "status-enum", "- `draft`\n- `active`")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, schema)
            result = run_lint(root, "--check-docs")
            self.assertEqual(1, result.returncode, result.stderr + result.stdout)
            self.assertIn("DOC_BLOCK_DRIFT", result.stdout)
            self.assertIn("status-enum", result.stdout)

    def test_check_docs_fix_only_changes_block_content(self) -> None:
        original = (REPO / "knowledge/.wiki-schema.md").read_text(encoding="utf-8")
        broken = replace_block_content(original, "confidence-enum", "- `low`")
        before_outside = block_outside_text(broken, "confidence-enum")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, broken)
            result = run_lint(root, "--check-docs", "--fix")
            self.assertEqual(1, result.returncode, result.stderr + result.stdout)
            fixed = (root / ".wiki-schema.md").read_text(encoding="utf-8")
            self.assertEqual(before_outside, block_outside_text(fixed, "confidence-enum"))
            clean = run_lint(root, "--check-docs")
            self.assertEqual(0, clean.returncode, clean.stderr + clean.stdout)

    def test_missing_and_duplicate_blocks_error(self) -> None:
        original = (REPO / "knowledge/.wiki-schema.md").read_text(encoding="utf-8")
        missing = original.replace(begin_doc_block("visibility-enum"), "", 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, missing)
            result = run_lint(root, "--check-docs")
            self.assertEqual(1, result.returncode, result.stderr + result.stdout)
            self.assertIn("DOC_BLOCK_MISSING", result.stdout)

        duplicate = original + "\n" + begin_doc_block("status-enum") + "\n- `draft`\n" + end_doc_block("status-enum") + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, duplicate)
            result = run_lint(root, "--check-docs")
            self.assertEqual(1, result.returncode, result.stderr + result.stdout)
            self.assertIn("DOC_BLOCK_DUPLICATE", result.stdout)

    def test_regular_lint_does_not_run_docs_checker(self) -> None:
        original = (REPO / "knowledge/.wiki-schema.md").read_text(encoding="utf-8")
        broken = replace_block_content(original, "source-manifest-status", "- `new`")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, broken)
            result = run_lint(root, "--check-only", "--json")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual([], [item for item in data["errors"] if item["code"].startswith("DOC_BLOCK_")])

    def test_check_docs_json_is_not_supported_yet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            result = run_lint(root, "--check-docs", "--json")
            self.assertEqual(2, result.returncode, result.stderr + result.stdout)
            self.assertIn("--json is not supported with --check-docs", result.stderr)

    def test_email_soft_redact_pattern_matches_common_address(self) -> None:
        patterns = BASE_SCHEMA["json_contracts"]["capture_policy"]["soft_redact"]["patterns"]
        self.assertIn("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", patterns)
        regex = re.compile(patterns[1], re.IGNORECASE)
        self.assertIsNotNone(regex.search("contact a.b+x@sub.example.cn now"))

    def test_targets_include_six_blocks(self) -> None:
        self.assertEqual(
            ["page-types", "status-enum", "confidence-enum", "visibility-enum", "source-manifest-status", "capture-policy-fields"],
            DOC_CONSISTENCY_TARGETS[0]["blocks"],
        )


if __name__ == "__main__":
    unittest.main()
