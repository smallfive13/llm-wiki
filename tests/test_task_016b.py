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


def capture_policy_v2(*, hard=None, soft=None) -> dict:
    return {
        "version": 1,
        "auto_capture": False,
        "default_visibility": "private",
        "hard_redact": {"patterns": list(hard or [])},
        "soft_redact": {"patterns": list(soft or [])},
        "exclude_paths": [],
        "max_inbox_files": 100,
        "updated_at": "2026-06-04T00:00:00+08:00",
    }


def init_instance(root: Path, *, hard=None, source_manifest=None) -> None:
    for directory in [
        "wiki/topics",
        "wiki/sources",
        "wiki/entities",
        "inbox/archive/promoted",
        "inbox/archive/dropped",
        "raw/sources/assets",
        ".wiki",
        "maps",
    ]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for name in ["purpose.md", "index.md", "overview.md", "log.md"]:
        write(root / name, f"# {name}\n")
    source_manifest = source_manifest or {"version": 1, "sources": [], "updated_at": "2026-06-04T00:00:00+08:00"}
    write(root / "raw/source_manifest.json", json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n")
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-04T00:00:00+08:00"}\n')
    write(root / ".wiki/capture_policy.json", json.dumps(capture_policy_v2(hard=hard), ensure_ascii=False, indent=2) + "\n")


def page(root: Path, body: str, *, pid: str = "top_20260604_images", source_ids=None) -> None:
    source_ids = source_ids or []
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
    ]
    if source_ids:
        lines.extend(["source_ids:", *[f"  - {item}" for item in source_ids]])
    else:
        lines.append("source_ids: []")
    lines.extend(
        [
            "related_ids: []",
            "sources: []",
            "related: []",
            "supersedes: []",
            "superseded_by: []",
            "evidence_count: 0",
            "---",
            "",
            "# Images",
            "",
            body,
        ]
    )
    write(root / "wiki/topics/images.md", "\n".join(lines))


def lint_json(root: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "wiki_lint.py"), "--root", str(root), "--check-only", "--json"],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stderr + result.stdout)
    return json.loads(result.stdout)


def codes(data: dict, level: str) -> list[str]:
    return [item["code"] for item in data[level]]


class Task016bImageLintTest(unittest.TestCase):
    def test_local_image_exists_and_missing_image_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write(root / "raw/sources/assets/exists.png", b"fake".decode("ascii"))
            page(
                root,
                "\n".join(
                    [
                        "Existing diagram: ![exists](../../raw/sources/assets/exists.png)",
                        "Missing diagram: ![missing](../../raw/sources/assets/missing.png)",
                    ]
                ),
            )

            data = lint_json(root)
            self.assertIn("IMAGE_DANGLING", codes(data, "errors"))
            self.assertEqual(1, codes(data, "errors").count("IMAGE_DANGLING"))

    def test_nonlocal_schemes_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(
                root,
                "\n".join(
                    [
                        "Remote http: ![a](http://example.test/a.png)",
                        "Remote https: ![b](https://example.test/b.png)",
                        "Inline data: ![c](data:image/png;base64,abc)",
                        "Mail link: ![d](mailto:user@example.test)",
                    ]
                ),
            )

            data = lint_json(root)
            self.assertNotIn("IMAGE_DANGLING", codes(data, "errors"))

    def test_code_blocks_are_ignored_for_image_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "```md\n![fake](../../raw/sources/assets/missing.png)\n![[also-missing.png]]\n```")

            data = lint_json(root)
            self.assertNotIn("IMAGE_DANGLING", codes(data, "errors"))

    def test_path_escape_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, "Escaping diagram: ![x](../../../outside.png)")

            data = lint_json(root)
            self.assertIn("IMAGE_PATH_ESCAPE", codes(data, "errors"))

    def test_hard_redact_scans_filename_path_description_and_manifest_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "version": 1,
                "updated_at": "2026-06-04T00:00:00+08:00",
                "sources": [
                    {
                        "source_id": "src_20260604_images",
                        "title": "Images",
                        "source_type": "manual",
                        "hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "original_path": "raw/sources/images.md",
                        "source_url": None,
                        "imported_at": "2026-06-04T00:00:00+08:00",
                        "last_ingested_at": "2026-06-04T00:00:00+08:00",
                        "status": "ingested",
                        "summary_page_id": None,
                        "summary_page_path": None,
                        "adapter": "manual",
                        "captions": ["caption SECRET-CAPTION"],
                    }
                ],
            }
            init_instance(root, hard=["SECRET-[A-Z]+"], source_manifest=manifest)
            for name in ["SECRET-FILE.png", "ok.png", "manifest.png"]:
                write(root / f"raw/sources/assets/{name}", "fake\n")
            page(
                root,
                "\n".join(
                    [
                        "File name hit: ![file](../../raw/sources/assets/SECRET-FILE.png)",
                        "Description hit: ![ok](../../raw/sources/assets/ok.png)",
                        "SECRET-DESC",
                        "Manifest hit: ![manifest](../../raw/sources/assets/manifest.png)",
                    ]
                ),
                source_ids=["src_20260604_images"],
            )

            data = lint_json(root)
            self.assertGreaterEqual(codes(data, "errors").count("IMAGE_HARD_REDACT"), 3)

    def test_missing_adjacent_description_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write(root / "raw/sources/assets/ok.png", "fake\n")
            page(root, "![ok](../../raw/sources/assets/ok.png)")

            data = lint_json(root)
            self.assertEqual([], data["errors"])
            self.assertIn("IMAGE_NO_DESCRIPTION", codes(data, "warnings"))


if __name__ == "__main__":
    unittest.main()
