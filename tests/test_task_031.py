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
import wiki_index  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class FakeClient:
    def __init__(self, nodes=None) -> None:
        self.nodes = nodes or [
            {
                "NodeId": 10,
                "NodeName": "dwd_payment_order_daily",
                "ProjectId": 96107,
                "Repeatability": True,
                "SchedulerType": "NORMAL",
                "ProgramType": "ODPS_SQL",
                "ModifyTime": 1780000000000,
            },
            {
                "NodeId": 11,
                "NodeName": "ads_paused_daily",
                "ProjectId": 96107,
                "Repeatability": True,
                "SchedulerType": "PAUSE",
                "ProgramType": "ODPS_SQL",
                "ModifyTime": 1780000000000,
            },
            {
                "NodeId": 12,
                "NodeName": "manual_temp",
                "ProjectId": 96107,
                "Repeatability": False,
                "SchedulerType": "NORMAL",
                "ProgramType": "ODPS_SQL",
                "ModifyTime": 1780000000000,
            },
        ]
        self.file_calls = []

    def list_nodes_prod_raw(self, project_id, *, page_size=100, max_pages=None):
        return self.nodes

    def get_node_prod(self, node_id):
        return next(item for item in self.nodes if item["NodeId"] == node_id)

    def find_design_file_for_node(self, project_id, node_id):
        return {
            "FileId": node_id + 1000,
            "FileName": f"file_{node_id}",
            "AbsoluteFolderPath": "业务流程/pk/folderMaxCompute",
        }

    def list_node_outputs(self, node_id):
        if node_id == 10:
            return ["pk_data.dwd_payment_order_daily", "pk_data.10_out"]
        return []

    def list_node_inputs(self, node_id):
        if node_id == 10:
            return ["pk_data.ods_payment_order_daily"]
        return []

    def get_design_file_code(self, project_id, file_id):
        self.file_calls.append((project_id, file_id))
        return type("FileCode", (), {"fingerprint": f"sha256:{file_id:064x}"})()

    def list_prod_nodes(self, project_id, *, page_size=100, max_pages=None):
        return dataworks_client.DataWorksClient.list_prod_nodes(self, project_id, page_size=page_size, max_pages=max_pages)


class Task031IndexTest(unittest.TestCase):
    def test_prod_filter_keeps_normal_repeatable_and_excludes_pause(self) -> None:
        client = FakeClient()
        nodes = client.list_prod_nodes(96107)
        self.assertEqual([10], [node.node_id for node in nodes])
        self.assertEqual([(96107, 1010)], client.file_calls)
        self.assertEqual(["pk_data.dwd_payment_order_daily", "pk_data.10_out"], nodes[0].tables)
        self.assertEqual(["pk_data.ods_payment_order_daily"], nodes[0].inputs)

    def test_layer_inference_and_unknown_are_best_effort(self) -> None:
        self.assertEqual(("DWD", "name_prefix"), wiki_index.infer_layer("dwd_order", []))
        self.assertEqual(("ODS", "name_prefix"), wiki_index.infer_layer("ods.sdk_backend.extract", []))
        self.assertEqual(("ADS", "output_table"), wiki_index.infer_layer("payment_order", ["pk_data.ads_payment_order"]))
        self.assertEqual(("unknown", "unknown"), wiki_index.infer_layer("payment_order", ["pk_data.payment_order"]))

    def test_stable_index_has_no_code_payload_or_generated_at(self) -> None:
        index = wiki_index.build_index(FakeClient(), project_id=96107, project_identifier="pk_data", snapshot_date="2026-06-23")
        self.assertEqual(2, index["index_version"])
        self.assertEqual("2026-06-23", index["snapshot_date"])
        self.assertNotIn("generated_at", index)
        self.assertFalse(wiki_index.contains_code_payload(index))
        item = index["items"][0]
        self.assertEqual("DWD", item["layer"])
        self.assertEqual("name_prefix", item["layer_source"])
        self.assertEqual("pk_data.dwd_payment_order_daily", item["table"])
        self.assertEqual(["pk_data.ods_payment_order_daily"], item["inputs"])
        self.assertIsNone(item.get("code"))

    def test_cli_dry_run_does_not_write_and_write_requires_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki").mkdir(parents=True)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = wiki_index.main(["--root", str(root), "--project-id", "96107", "--project-identifier", "pk_data"], client_factory=lambda: FakeClient())
            self.assertEqual(0, rc)
            self.assertFalse((root / ".wiki/dataworks_index.json").exists())
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = wiki_index.main(
                    ["--root", str(root), "--project-id", "96107", "--project-identifier", "pk_data", "--write"],
                    client_factory=lambda: FakeClient(),
                )
            self.assertEqual(0, rc)
            self.assertTrue((root / ".wiki/dataworks_index.json").is_file())

    def test_credentials_missing_warning_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def missing():
                raise dataworks_client.DataWorksClientError("AUTH_MISSING", "missing env")

            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                rc = wiki_index.main(["--root", str(root), "--project-id", "96107", "--json"], client_factory=missing)
            self.assertEqual(0, rc)
            data = json.loads(out.getvalue())
            self.assertEqual("AUTH_MISSING", data["warnings"][0]["code"])

    def test_offline_tools_do_not_import_dataworks_sdk_client_or_index(self) -> None:
        for name in list(sys.modules):
            if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud")):
                sys.modules.pop(name, None)
        sys.path.insert(0, str(SCRIPTS))
        importlib.import_module("wiki_lint")
        importlib.import_module("wiki_graph")
        importlib.import_module("wiki_eval")
        leaked = [name for name in sys.modules if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud"))]
        self.assertEqual([], leaked)


if __name__ == "__main__":
    unittest.main()
