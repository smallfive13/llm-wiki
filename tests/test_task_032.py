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


class Request:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Models:
    ListNodesRequest = Request


class Response:
    def __init__(self, body):
        self.body = body


class PagedSdk:
    def __init__(self):
        self.calls = []

    def list_nodes(self, request):
        self.calls.append(request.page_number)
        pages = {
            1: [{"NodeId": 1, "NodeName": "ods_a"}],
            2: [{"NodeId": 2, "NodeName": "dwd_b"}],
            3: [{"NodeId": 3, "NodeName": "dws_c"}],
        }
        return Response({"Data": {"Nodes": pages.get(request.page_number, []), "TotalCount": 3}})


def node(node_id, name, inputs, outputs):
    return dataworks_client.DataWorksNode(
        node_id=node_id,
        node_name=name,
        project_id=96107,
        file_id=1000 + node_id,
        file_name=f"{name}.sql",
        file_path=f"业务流程/{name}.sql",
        file_version=None,
        program_type="ODPS_SQL",
        scheduler_type="NORMAL",
        repeatability=True,
        inputs=inputs,
        outputs=outputs,
        tables=outputs,
        fingerprint=f"sha256:{node_id:064x}",
        last_synced="2026-06-24T00:00:00+08:00",
    )


class Task032IndexTest(unittest.TestCase):
    def test_list_nodes_prod_raw_paginates_full_and_supports_limit(self):
        full = dataworks_client.DataWorksClient(PagedSdk(), Models())
        self.assertEqual([1, 2, 3], [item["NodeId"] for item in full.list_nodes_prod_raw(96107)])
        limited_sdk = PagedSdk()
        limited = dataworks_client.DataWorksClient(limited_sdk, Models())
        self.assertEqual([1, 2], [item["NodeId"] for item in limited.list_nodes_prod_raw(96107, max_pages=2)])
        self.assertEqual([1, 2], limited_sdk.calls)

    def test_index_version_inputs_layers_and_stable_payload(self):
        index = wiki_index.stable_index(
            [
                node(1, "dwb_coupon_detail", ["pk_data.dwd_coupon"], ["pk_data.dwb_coupon_detail"]),
                node(2, "dws_holo.dws_coupon_sum", ["pk_data.dwb_coupon_detail"], ["pk_data.dws_coupon_sum"]),
                node(3, "ads_coupon_board", ["pk_data.dws_coupon_sum"], ["pk_data.ads_coupon_board"]),
                node(4, "misc_job", [], ["pk_data.fact_unknown"]),
            ],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-24",
        )
        self.assertEqual(2, index["index_version"])
        layers = {item["node_name"]: item["layer"] for item in index["items"]}
        self.assertEqual("DWB", layers["dwb_coupon_detail"])
        self.assertEqual("DWS", layers["dws_holo.dws_coupon_sum"])
        self.assertEqual("ADS", layers["ads_coupon_board"])
        self.assertEqual("unknown", layers["misc_job"])
        self.assertFalse(wiki_index.contains_code_payload(index))
        self.assertNotIn("generated_at", index)

    def test_reverse_online_source_to_ods_and_downstream_with_knowledge_page(self):
        index = wiki_index.stable_index(
            [
                node(1, "ods_order", ["mysql_trade.orders"], ["pk_data.ods_order"]),
                node(2, "dwd_order_detail", ["pk_data.ods_order"], ["pk_data.dwd_order_detail"]),
                node(3, "dws_order_sum", ["pk_data.dwd_order_detail"], ["pk_data.dws_order_sum"]),
            ],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-24",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki/asset-mappings").mkdir(parents=True)
            (root / "wiki/asset-mappings/order.md").write_text("physical_table: pk_data.dwd_order_detail\n", encoding="utf-8")
            report = wiki_index.build_reverse_report(index, "mysql_trade.orders", root=root)
        self.assertEqual(["ods_order"], [item["node_name"] for item in report["upstream_ods"]])
        self.assertEqual(["dwd_order_detail", "dws_order_sum"], [item["node_name"] for item in report["downstream_candidates"]])
        self.assertEqual("DWD", report["recommended"][0]["layer"])
        self.assertEqual("has_knowledge_page", report["recommended"][0]["review"])
        self.assertIn("动态 SQL", report["caveat"])

    def test_reverse_ods_without_downstream_warns(self):
        index = wiki_index.stable_index(
            [node(1, "ods_order", ["mysql_trade.orders"], ["pk_data.ods_order"])],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-24",
        )
        report = wiki_index.build_reverse_report(index, "mysql_trade.orders")
        self.assertEqual(["ods_order"], [item["node_name"] for item in report["upstream_ods"]])
        self.assertEqual([], report["downstream_candidates"])
        self.assertTrue(report["warnings"])

    def test_reverse_fully_qualified_table_does_not_match_only_suffix(self):
        index = wiki_index.stable_index(
            [
                node(1, "ods_target", ["pk_data.ods.target.pre"], ["pk_data.ods.target.extract"]),
                node(2, "ods_other", ["pk_data.ods.other.pre"], ["pk_data.ods.other.extract"]),
            ],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-24",
        )
        report = wiki_index.build_reverse_report(index, "pk_data.ods.target.pre")
        self.assertEqual(["ods_target"], [item["node_name"] for item in report["upstream_ods"]])

    def test_reverse_cli_does_not_require_project_id(self):
        index = wiki_index.stable_index(
            [node(1, "ods_order", ["mysql_trade.orders"], ["pk_data.ods_order"])],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-24",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki").mkdir(parents=True)
            (root / ".wiki/dataworks_index.json").write_text(json.dumps(index), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                rc = wiki_index.main(["reverse", "--root", str(root), "--table", "mysql_trade.orders"])
        self.assertEqual(0, rc)
        self.assertIn("wiki-index reverse", out.getvalue())

    def test_missing_project_id_for_build_is_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                rc = wiki_index.main(["--root", tmp])
        self.assertEqual(2, rc)
        self.assertIn("--project-id is required", err.getvalue())

    def test_credentials_missing_warning_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            def missing():
                raise dataworks_client.DataWorksClientError("AUTH_MISSING", "missing env")

            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                rc = wiki_index.main(["--root", tmp, "--project-id", "96107", "--json"], client_factory=missing)
        self.assertEqual(0, rc)
        self.assertEqual("AUTH_MISSING", json.loads(out.getvalue())["warnings"][0]["code"])

    def test_offline_tools_do_not_import_online_modules(self):
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
