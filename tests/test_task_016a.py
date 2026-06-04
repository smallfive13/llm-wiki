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


def capture_policy_v1(patterns=None) -> dict:
    return {
        "version": 1,
        "auto_capture": False,
        "exclude_patterns": list(patterns or []),
        "exclude_paths": [],
        "max_inbox_files": 100,
        "updated_at": "2026-06-04T00:00:00+08:00",
    }


def capture_policy_v2(*, default_visibility="private", hard=None, soft=None) -> dict:
    return {
        "version": 1,
        "auto_capture": False,
        "default_visibility": default_visibility,
        "hard_redact": {"patterns": list(hard or [])},
        "soft_redact": {"patterns": list(soft or [])},
        "exclude_paths": [],
        "max_inbox_files": 100,
        "updated_at": "2026-06-04T00:00:00+08:00",
    }


def init_instance(root: Path, policy: dict) -> None:
    for directory in [
        "wiki/topics",
        "wiki/sources",
        "wiki/entities",
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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-04T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-04T00:00:00+08:00"}\n')
    write(root / ".wiki/capture_policy.json", json.dumps(policy, ensure_ascii=False, indent=2) + "\n")


def page(root: Path, rel: str, *, pid: str, visibility=None, body="") -> None:
    lines = [
        "---",
        f"id: {pid}",
        "type: topic",
        "status: active",
        "confidence: medium",
        "created: 2026-06-04",
        "updated: 2026-06-04",
        "last_verified: 2026-06-04",
        "review: true",
        "source_ids: []",
        "related_ids: []",
        "sources: []",
        "related: []",
        "supersedes: []",
        "superseded_by: []",
        "evidence_count: 0",
    ]
    if visibility is not None:
        lines.append(f"visibility: {visibility}")
    lines.extend(["---", "", f"# {pid}", "", body])
    write(root / rel, "\n".join(lines))


def inbox(root: Path, body: str) -> None:
    write(
        root / "inbox/20260604-120000-test.md",
        "\n".join(
            [
                "---",
                "id: inb_20260604_120000_test",
                "type: inbox",
                "status: draft",
                "confidence: medium",
                "review: false",
                "suggested_target_type: topic",
                "suggested_target_title: Test",
                "created: 2026-06-04",
                "---",
                "",
                body,
            ]
        ),
    )


def add_source_manifest(root: Path, *, visibility=None) -> None:
    source = {
        "source_id": "src_20260604_example",
        "title": "Example",
        "source_type": "manual",
        "hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "original_path": "raw/sources/example.md",
        "source_url": None,
        "imported_at": "2026-06-04T00:00:00+08:00",
        "last_ingested_at": "2026-06-04T00:00:00+08:00",
        "status": "ingested",
        "summary_page_id": None,
        "summary_page_path": None,
        "adapter": "manual",
    }
    if visibility is not None:
        source["visibility"] = visibility
    write(root / "raw/source_manifest.json", json.dumps({"version": 1, "sources": [source]}, ensure_ascii=False) + "\n")


def lint_json(root: Path, *extra: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), "--check-only", "--json", *extra],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stderr + result.stdout)
    return json.loads(result.stdout)


class Task016aLintTest(unittest.TestCase):
    def test_v1_capture_policy_is_legacy_warning_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, capture_policy_v1(["SOFT-LEGACY"]))
            inbox(root, "SOFT-LEGACY should warn only")

            data = lint_json(root)
            self.assertEqual([], data["errors"])
            codes = [item["code"] for item in data["warnings"]]
            self.assertIn("CAPTURE_POLICY_LEGACY", codes)
            self.assertIn("SOFT_REDACT_HIT", codes)

    def test_v2_capture_policy_has_no_legacy_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, capture_policy_v2(soft=["SOFT-V2"]))
            inbox(root, "SOFT-V2 should warn only")

            data = lint_json(root)
            self.assertEqual([], data["errors"])
            codes = [item["code"] for item in data["warnings"]]
            self.assertNotIn("CAPTURE_POLICY_LEGACY", codes)
            self.assertIn("SOFT_REDACT_HIT", codes)

    def test_hard_redact_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, capture_policy_v2(hard=["HARD-SECRET"]))
            inbox(root, "HARD-SECRET must block")

            data = lint_json(root)
            self.assertEqual(["HARD_REDACT_HIT"], [item["code"] for item in data["errors"]])

    def test_visibility_optional_and_invalid_values_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, capture_policy_v2(default_visibility="internal"))
            page(root, "wiki/topics/missing.md", pid="top_20260604_missing")
            page(root, "wiki/topics/public.md", pid="top_20260604_public", visibility="public")
            page(root, "wiki/topics/bad.md", pid="top_20260604_bad", visibility="team")
            add_source_manifest(root, visibility="team")

            data = lint_json(root)
            fields = [(item["file"], item["field"]) for item in data["errors"] if item["code"] == "ENUM_INVALID"]
            self.assertIn(("wiki/topics/bad.md", "visibility"), fields)
            self.assertIn(("raw/source_manifest.json", "visibility"), fields)
            self.assertNotIn(("wiki/topics/missing.md", "visibility"), fields)

    def test_public_wiki_page_soft_redact_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root, capture_policy_v2(default_visibility="private", soft=["INTERNAL-TERM"]))
            page(root, "wiki/topics/public.md", pid="top_20260604_public", visibility="public", body="INTERNAL-TERM")

            data = lint_json(root, "--scan-wiki-pii")
            self.assertEqual([], data["errors"])
            warnings = [item for item in data["warnings"] if item["code"] == "SOFT_REDACT_HIT"]
            self.assertEqual(1, len(warnings))
            self.assertIn("公开内容", warnings[0]["hint"])


if __name__ == "__main__":
    unittest.main()
