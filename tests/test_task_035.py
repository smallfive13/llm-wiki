import importlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dataworks_client  # noqa: E402
import wiki_freshness  # noqa: E402
import wiki_index  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path) -> None:
    (root / ".wiki").mkdir(parents=True)
    (root / "wiki/asset-mappings").mkdir(parents=True)


def page(root: Path, rel: str, *, dataworks_ref: str | None = None, physical_table: str = "pk_data.dwd_asset_repay_record") -> Path:
    extra = [
        f"physical_table: {physical_table}",
        "business_concept: 还款记录",
    ]
    if dataworks_ref:
        extra.append(f"dataworks_ref: {dataworks_ref}")
    text = "\n".join(
        [
            "---",
            "id: asm_20260625_repay",
            "type: asset-mapping",
            "status: active",
            "confidence: low",
            "created: 2026-06-25",
            "updated: 2026-06-25",
            "last_verified: 2026-06-25",
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
            "# 还款记录",
            "",
            "映射到 pk_data.dwd_asset_repay_record。",
        ]
    )
    path = root / rel
    write(path, text)
    return path


def write_index(root: Path) -> None:
    index = {
        "index_version": 2,
        "project_id": 96107,
        "project_identifier": "pk_data",
        "snapshot_date": "2026-06-25",
        "source_window": {"mode": "full_prod_nodes"},
        "items": [
            {
                "code_fingerprint": "sha256:old",
                "dataworks_ref": "file:96107/100",
                "file_id": 100,
                "file_path": "业务流程/dwd_asset_repay_record",
                "fingerprint_version": "dw-code-v1",
                "inputs": ["pk_data.ods_pak_listing_autosync_3_tb_repay_record"],
                "last_synced": "2026-06-20T00:00:00+08:00",
                "layer": "DWD",
                "layer_source": "name_prefix",
                "node_id": 10,
                "node_name": "dwd_asset_repay_record",
                "outputs": ["pk_data.dwd_asset_repay_record"],
                "program_type": "ODPS_SQL",
                "table": "pk_data.dwd_asset_repay_record",
            },
            {
                "code_fingerprint": "sha256:other",
                "dataworks_ref": "file:96107/200",
                "file_id": 200,
                "file_path": "业务流程/dwd_asset_other",
                "fingerprint_version": "dw-code-v1",
                "inputs": [],
                "last_synced": "2026-06-20T00:00:00+08:00",
                "layer": "DWD",
                "layer_source": "name_prefix",
                "node_id": 20,
                "node_name": "dwd_asset_other",
                "outputs": ["pk_data.dwd_asset_other"],
                "program_type": "ODPS_SQL",
                "table": "pk_data.dwd_asset_other",
            },
        ],
    }
    write(root / ".wiki/dataworks_index.json", json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


class FakeIncrementalClient:
    def __init__(self, *, fingerprint: str = "sha256:new", changes=None) -> None:
        self.fingerprint = fingerprint
        self.changes = changes
        self.file_calls = []

    def list_successful_prod_deployment_items(self, project_id, *, end_execute_time_ms=None, max_pages=None):
        if self.changes is not None:
            return self.changes
        return [
            dataworks_client.DataWorksDeploymentItem(
                deployment_id=1,
                file_id=100,
                file_version=7,
                execute_time_ms=1780000000000,
                execute_time_iso="2026-05-27T09:46:40+08:00",
                to_environment=2,
            )
        ]

    def get_file_code(self, raw_ref):
        self.file_calls.append(raw_ref)
        return type("FileCode", (), {"fingerprint": self.fingerprint})()


class Task035IncrementalTest(unittest.TestCase):
    def test_incremental_dry_run_only_fingerprints_changed_file_and_finds_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write_index(root)
            page(root, "wiki/asset-mappings/repay.md", dataworks_ref="file:96107/100")
            client = FakeIncrementalClient()

            report = wiki_freshness.evaluate_deployment_incremental(root, project_id=96107, client_factory=lambda: client)

            self.assertEqual(["file:96107/100"], client.file_calls)
            self.assertFalse(report["applied"]["index_written"])
            self.assertEqual(1, len(report["changed_files"]))
            self.assertTrue(report["changed_files"][0]["fingerprint_changed"])
            self.assertEqual(["wiki/asset-mappings/repay.md"], [item["file"] for item in report["affected_pages"]])
            self.assertIn("dataworks_ref:file", report["affected_pages"][0]["reasons"])
            self.assertIn("normalized_lineage", report["affected_pages"][0]["reasons"])
            self.assertIn("sha256:old", (root / ".wiki/dataworks_index.json").read_text(encoding="utf-8"))

    def test_incremental_deduplicates_to_latest_change_per_file(self) -> None:
        changes = [
            dataworks_client.DataWorksDeploymentItem(
                deployment_id=1,
                file_id=100,
                file_version=7,
                execute_time_ms=1780000000000,
                execute_time_iso="2026-05-27T09:46:40+08:00",
                to_environment=2,
            ),
            dataworks_client.DataWorksDeploymentItem(
                deployment_id=2,
                file_id=100,
                file_version=8,
                execute_time_ms=1780000100000,
                execute_time_iso="2026-05-27T09:48:20+08:00",
                to_environment=2,
            ),
            dataworks_client.DataWorksDeploymentItem(
                deployment_id=3,
                file_id=200,
                file_version=1,
                execute_time_ms=1780000200000,
                execute_time_iso="2026-05-27T09:50:00+08:00",
                to_environment=2,
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write_index(root)
            page(root, "wiki/asset-mappings/repay.md", dataworks_ref="file:96107/100")
            client = FakeIncrementalClient(changes=changes)

            report = wiki_freshness.evaluate_deployment_incremental(root, project_id=96107, client_factory=lambda: client)

            self.assertEqual(["file:96107/200", "file:96107/100"], client.file_calls)
            self.assertEqual([200, 100], [item["file_id"] for item in report["changed_files"]])
            self.assertEqual(2, report["changed_files"][1]["deployment_id"])
            self.assertEqual([200, 100], [item["file_id"] for item in report["index_updates"]])

    def test_apply_writes_index_but_not_page_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write_index(root)
            p = page(root, "wiki/asset-mappings/repay.md", dataworks_ref="file:96107/100")

            report = wiki_freshness.evaluate_deployment_incremental(root, project_id=96107, client_factory=lambda: FakeIncrementalClient(), apply=True)

            self.assertTrue(report["applied"]["index_written"])
            self.assertIn("sha256:new", (root / ".wiki/dataworks_index.json").read_text(encoding="utf-8"))
            self.assertIn("status: active", p.read_text(encoding="utf-8"))

    def test_cli_exit_codes_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write_index(root)
            page(root, "wiki/asset-mappings/repay.md")
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                rc = wiki_freshness.main(
                    ["--root", str(root), "--incremental-deployments", "--project-id", "96107", "--json"],
                    client_factory=lambda: FakeIncrementalClient(),
                )
            self.assertEqual(0, rc)
            self.assertEqual("incremental_deployments", json.loads(out.getvalue())["mode"])
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = wiki_freshness.main(
                    ["--root", str(root), "--incremental-deployments", "--project-id", "96107", "--check"],
                    client_factory=lambda: FakeIncrementalClient(),
                )
            self.assertEqual(1, rc)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(2, wiki_freshness.main(["--root", str(root), "--incremental-deployments"]))

    def test_missing_credentials_warning_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_instance(root)
            write_index(root)

            def missing():
                raise dataworks_client.DataWorksClientError("AUTH_MISSING", "missing env")

            report = wiki_freshness.evaluate_deployment_incremental(root, project_id=96107, client_factory=missing)
            self.assertEqual(["AUTH_MISSING"], [item["code"] for item in report["warnings"]])

    def test_successful_prod_deployment_filter_shape(self) -> None:
        class Models:
            class ListDeploymentsRequest:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

            class GetDeploymentRequest:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

        class Resp:
            def __init__(self, body):
                self.body = body

        class Sdk:
            def list_deployments(self, req):
                return Resp({"Data": {"Deployments": [{"Id": 1}], "TotalCount": 1}})

            def get_deployment(self, req):
                return Resp(
                    {
                        "Data": {
                            "Deployment": {"Status": 1, "ToEnvironment": 2, "ExecuteTime": 1780000000000},
                            "DeployedItems": [{"FileId": 100, "FileVersion": 7}, {"FileId": 100, "FileVersion": 7}],
                        }
                    }
                )

        client = dataworks_client.DataWorksClient(Sdk(), Models())
        items = client.list_successful_prod_deployment_items(96107)
        self.assertEqual(1, len(items))
        self.assertEqual(100, items[0].file_id)
        self.assertEqual(7, items[0].file_version)
        self.assertEqual(2, items[0].to_environment)

    def test_offline_tools_do_not_import_online_modules(self) -> None:
        for name in list(sys.modules):
            if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud", "sqlglot")):
                sys.modules.pop(name, None)
        sys.path.insert(0, str(SCRIPTS))
        importlib.import_module("wiki_lint")
        importlib.import_module("wiki_graph")
        importlib.import_module("wiki_eval")
        leaked = [
            name
            for name in sys.modules
            if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud", "sqlglot"))
        ]
        self.assertEqual([], leaked)


if __name__ == "__main__":
    unittest.main()
