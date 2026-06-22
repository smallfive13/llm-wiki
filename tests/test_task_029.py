import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dataworks_client  # noqa: E402
import wiki_freshness  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path) -> None:
    for directory in [
        "wiki/asset-mappings",
        "wiki/topics",
        "wiki/decisions",
        "wiki/sources",
        "wiki/entities",
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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-22T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-22T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        (
            '{"version":1,"auto_capture":false,"default_visibility":"private",'
            '"hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},'
            '"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-06-22T00:00:00+08:00"}\n'
        ),
    )
    write(
        root / ".wiki-profile.json",
        json.dumps(
            {
                "schema_version": 2,
                "profile": "case-profile",
                "extra_page_types": [
                    {
                        "type": "asset-mapping",
                        "id_prefix": "asm",
                        "dir": "wiki/asset-mappings",
                        "required_fields": ["business_concept", "physical_table"],
                        "optional_fields": [
                            "physical_field",
                            "business_aliases",
                            "dataworks_ref",
                            "code_fingerprint",
                            "last_synced",
                        ],
                    }
                ],
                "extra_field_enums": {},
                "extra_optional_fields": {
                    "topic": ["dataworks_ref", "code_fingerprint", "last_synced"],
                    "decision": ["dataworks_ref", "code_fingerprint", "last_synced"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )


def page(
    root: Path,
    *,
    rel: str = "wiki/asset-mappings/payment-channel.md",
    status: str = "active",
    dataworks_ref: str | None = None,
    code_fingerprint: str | None = None,
    last_synced: str | None = None,
) -> Path:
    extra = [
        "business_concept: 收款渠道",
        "physical_table: pk_data.example_payment_order",
    ]
    if dataworks_ref is not None:
        extra.append(f"dataworks_ref: {dataworks_ref}")
    if code_fingerprint is not None:
        extra.append(f"code_fingerprint: {code_fingerprint}")
    if last_synced is not None:
        extra.append(f"last_synced: {last_synced}")
    text = "\n".join(
        [
            "---",
            "id: asm_20260622_payment-channel",
            "type: asset-mapping",
            f"status: {status}",
            "confidence: low",
            "created: 2026-06-22",
            "updated: 2026-06-22",
            "last_verified: 2026-06-22",
            "review: false",
            "source_ids: []",
            "related_ids: []",
            "sources: []",
            "related: []",
            "supersedes: []",
            "superseded_by: []",
            "evidence_count: 0",
            *extra,
            "---",
            "",
            "# 收款渠道",
            "",
            "示例。",
        ]
    )
    path = root / rel
    write(path, text)
    return path


class FakeClient:
    def __init__(self, *, file_fingerprint: str = "sha256:good", last_ddl_ms: int = 1780000000000) -> None:
        self.file_fingerprint = file_fingerprint
        self.last_ddl_ms = last_ddl_ms

    def get_file_code(self, raw_ref: str):
        return type(
            "FileCode",
            (),
            {"fingerprint": self.file_fingerprint, "content_path": "Data.File.Content"},
        )()

    def get_table_info(self, raw_ref: str):
        return type(
            "TableInfo",
            (),
            {"last_ddl_time_ms": self.last_ddl_ms, "last_ddl_time_iso": "2026-05-27T09:46:40+08:00", "columns": [{"ColumnName": "id"}]},
        )()


class Task029FreshnessTest(unittest.TestCase):
    def test_code_sha256_is_stable_lf_strip_and_sorted(self) -> None:
        left = dataworks_client.code_sha256([("b.sql", "select 1;  \r\n"), ("a.sql", "select 2;\n\n")])
        right = dataworks_client.code_sha256([("a.sql", "select 2;"), ("b.sql", "select 1;\n")])
        self.assertEqual(left, right)
        self.assertTrue(left.startswith("sha256:"))
        self.assertEqual(71, len(left))

    def test_file_anchor_drift_and_default_readonly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            p = page(root, dataworks_ref="file:96107/123", code_fingerprint="sha256:old")

            report = wiki_freshness.evaluate_instance(root, client_factory=lambda: FakeClient(file_fingerprint="sha256:new"))
            self.assertEqual(1, report["drift_count"])
            self.assertEqual("drift", report["items"][0]["status"])
            self.assertIn("status: active", p.read_text(encoding="utf-8"))
            self.assertEqual([], report["applied"]["status_updates"])
            self.assertEqual("stale_claim", report["review_queue_suggestions"][0]["type"])

    def test_apply_stale_updates_only_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            p = page(root, dataworks_ref="file:96107/123", code_fingerprint="sha256:old")

            report = wiki_freshness.evaluate_instance(root, client_factory=lambda: FakeClient(file_fingerprint="sha256:new"), apply_stale=True)
            self.assertEqual(1, report["drift_count"])
            self.assertEqual(["wiki/asset-mappings/payment-channel.md"], report["applied"]["status_updates"])
            text = p.read_text(encoding="utf-8")
            self.assertIn("status: stale", text)
            self.assertIn("code_fingerprint: sha256:old", text)

    def test_table_anchor_uses_last_ddl_time_against_last_synced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, dataworks_ref="table:pk_data.dwb_risk_user_limit_dtl", last_synced="2026-01-01")

            report = wiki_freshness.evaluate_instance(root, client_factory=lambda: FakeClient(last_ddl_ms=1780000000000))
            self.assertEqual(1, report["drift_count"])
            self.assertEqual("LastDdlTime newer than last_synced", report["items"][0]["reason"])

    def test_credentials_missing_warning_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, dataworks_ref="file:96107/123", code_fingerprint="sha256:old")

            def raise_missing():
                raise dataworks_client.DataWorksClientError("AUTH_MISSING", "missing env")

            report = wiki_freshness.evaluate_instance(root, client_factory=raise_missing)
            self.assertEqual(0, report["drift_count"])
            self.assertEqual(["AUTH_MISSING"], [item["code"] for item in report["warnings"]])

    def test_exit_codes_check_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root, dataworks_ref="file:96107/123", code_fingerprint="sha256:old")
            with mock.patch("wiki_freshness.DataWorksClient.from_env", return_value=FakeClient(file_fingerprint="sha256:new")):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(0, wiki_freshness.main(["--root", str(root)], client_factory=None))
                    self.assertEqual(1, wiki_freshness.main(["--root", str(root), "--check"], client_factory=None))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(2, wiki_freshness.main(["--root", str(root / "missing")], client_factory=lambda: FakeClient()))

    def test_json_output_and_no_anchor_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            page(root)
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "wiki_freshness.py"), "--root", str(root), "--json", "--check"],
                cwd=REPO,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(0, data["scanned"]["anchors"])
            self.assertEqual(0, data["drift_count"])

    def test_offline_tools_do_not_import_dataworks_sdk_or_client(self) -> None:
        for module_name in ["wiki_lint", "wiki_graph", "wiki_eval"]:
            sys.modules.pop(module_name, None)
        before = set(sys.modules)
        importlib.import_module("wiki_lint")
        importlib.import_module("wiki_graph")
        importlib.import_module("wiki_eval")
        loaded = set(sys.modules) - before
        self.assertNotIn("dataworks_client", loaded)
        self.assertFalse(any(name.startswith("alibabacloud_dataworks_public") for name in loaded))

    @unittest.skipUnless(os.environ.get("TASK029_REAL_SMOKE_FILE_REF"), "set TASK029_REAL_SMOKE_FILE_REF to run real smoke")
    def test_real_smoke_file_shape(self) -> None:
        client = dataworks_client.DataWorksClient.from_env()
        file_code = client.get_file_code(os.environ["TASK029_REAL_SMOKE_FILE_REF"])
        self.assertEqual("Data.File.Content", file_code.content_path)


if __name__ == "__main__":
    unittest.main()
