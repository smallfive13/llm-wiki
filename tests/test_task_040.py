import importlib
import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import wiki_index  # noqa: E402


def item(node_id, node_name, layer, inputs=None, outputs=None, table=None):
    outputs = outputs or ([table] if table else [])
    return {
        "node_id": node_id,
        "node_name": node_name,
        "layer": layer,
        "inputs": inputs or [],
        "outputs": outputs,
        "table": table or (outputs[0] if outputs else None),
        "dataworks_ref": f"file:96107/{node_id}",
    }


def index(items):
    return {
        "index_version": 2,
        "project_id": 96107,
        "project_identifier": "pk_data",
        "snapshot_date": "2026-07-02",
        "source_window": {"mode": "fixture"},
        "items": items,
    }


class Task040PhysicalLayerRolesTest(unittest.TestCase):
    def test_compat_wrappers_stay_legacy(self):
        self.assertEqual({"DWD", "DWB"}, wiki_index.DETAIL_LAYERS)
        self.assertEqual({"DWS", "ADS"}, wiki_index.SUMMARY_LAYERS)

    def test_three_role_classification(self):
        idx = index(
            [
                item(1, "dim_merchant_info", "DIM", [], ["pk_data.dim_merchant_info"]),
                item(2, "s_dwd_asset_apply", "S-DWD", ["pk_data.ods_apply"], ["pk_data.s_dwd_asset_apply"]),
                item(3, "ddm_asset_board", "DDM", ["pk_data.s_dwd_asset_apply"], ["pk_data.ddm_asset_board"]),
                item(4, "edw_asset_report", "EDW", ["pk_data.ddm_asset_board"], ["pk_data.edw_asset_report"]),
                item(5, "tmp_asset_mid", "TMP", ["pk_data.ods_apply"], ["pk_data.tmp_asset_mid"]),
            ]
        )
        detail = wiki_index.build_reverse_report(idx, "dim_merchant_info")
        self.assertEqual(["dim_merchant_info"], [x["node_name"] for x in detail["recommended"]])
        self.assertEqual("detail-candidate", detail["recommended"][0]["role"])

        hidden = wiki_index.build_reverse_report(idx, "pk_data.s_dwd_asset_apply")
        shown = wiki_index.build_reverse_report(idx, "pk_data.s_dwd_asset_apply", include_summary=True)
        self.assertEqual([], hidden["summary_candidates"])
        self.assertEqual(["ddm_asset_board"], [x["node_name"] for x in shown["summary_candidates"]])
        self.assertEqual("downstream-derived", shown["summary_candidates"][0]["role"])

        trace = wiki_index.build_reverse_report(idx, "pk_data.tmp_asset_mid")
        self.assertEqual([], trace["recommended"])
        self.assertEqual(["tmp_asset_mid"], [x["node_name"] for x in trace["matched_trace_only"]])

    def test_exact_trace_only_match_suppresses_downstream_recommendation(self):
        idx = index(
            [
                item(1, "tmp_asset_repay_dtl", "TMP", ["pk_data.ods_repay"], ["pk_data.tmp_asset_repay_dtl"]),
                item(2, "dwb_asset_repay_dtl", "DWB", ["pk_data.tmp_asset_repay_dtl"], ["pk_data.dwb_asset_repay_dtl"]),
            ]
        )
        report = wiki_index.build_reverse_report(idx, "pk_data.tmp_asset_repay_dtl")
        self.assertEqual([], report["recommended"])
        self.assertEqual(["tmp_asset_repay_dtl"], [x["node_name"] for x in report["matched_trace_only"]])

    def test_unqualified_table_resolves_only_when_unique(self):
        idx = index([item(1, "dim_merchant_info", "DIM", [], ["pk_data.dim_merchant_info"])])
        report = wiki_index.build_reverse_report(idx, "dim_merchant_info")
        self.assertEqual("pk_data.dim_merchant_info", report["normalized_key"])
        self.assertEqual(["dim_merchant_info"], [x["node_name"] for x in report["recommended"]])

    def test_unqualified_table_can_resolve_by_node_name_when_output_is_synthetic(self):
        idx = index([item(1, "dim_merchant_info", "DIM", [], ["pk_data.500573807_out"])])
        report = wiki_index.build_reverse_report(idx, "dim_merchant_info")
        self.assertEqual("dim_merchant_info", report["normalized_key"])
        self.assertEqual(["dim_merchant_info"], [x["node_name"] for x in report["recommended"]])

    def test_unqualified_table_ambiguity_warns_and_does_not_recommend(self):
        idx = index(
            [
                item(1, "dim_merchant_info", "DIM", [], ["pk_data.dim_merchant_info"]),
                item(2, "dim_merchant_info_dexin", "DIM", [], ["pk_dexin.dim_merchant_info"]),
            ]
        )
        report = wiki_index.build_reverse_report(idx, "dim_merchant_info")
        self.assertEqual([], report["recommended"])
        self.assertIn("ambiguous_table_key", report["warnings"][0])
        self.assertEqual(2, len(report["ambiguous_matches"]))

    def test_dexin_projection_is_trace_only_by_table_node_or_outputs(self):
        idx = index(
            [
                item(1, "dwd_asset_loan_list", "DWD", [], ["pk_data.dwd_asset_loan_list"]),
                item(2, "pk_dexin.dwd_asset_loan_list", "DWD", [], ["pk_data.pk_dexin.dwd_asset_loan_list"]),
                item(3, "dexin_output", "DWD", [], ["pk_dexin.dwd_asset_loan_debt"]),
            ]
        )
        report = wiki_index.build_reverse_report(idx, "pk_data.pk_dexin.dwd_asset_loan_list")
        rendered = wiki_index.render_reverse(report)
        self.assertEqual([], report["recommended"])
        self.assertEqual(["pk_dexin.dwd_asset_loan_list"], [x["node_name"] for x in report["matched_trace_only"]])
        self.assertIn("仅溯源，不建议作为取数定义点", rendered)
        self.assertEqual("trace-only", wiki_index.item_role(idx["items"][2]))

    def test_legacy_six_layer_rendering_is_byte_compatible(self):
        idx = index(
            [
                item(1, "ods_order", "ODS", ["mysql_trade.orders"], ["pk_data.ods_order"]),
                item(2, "dwd_order", "DWD", ["pk_data.ods_order"], ["pk_data.dwd_order"]),
                item(3, "dwb_order", "DWB", ["pk_data.dwd_order"], ["pk_data.dwb_order"]),
                item(4, "dws_order", "DWS", ["pk_data.dwb_order"], ["pk_data.dws_order"]),
                item(5, "ads_order", "ADS", ["pk_data.dws_order"], ["pk_data.ads_order"]),
                item(6, "misc", "unknown", [], ["pk_data.fact_order"]),
            ]
        )
        report = wiki_index.build_reverse_report(idx, "mysql_trade.orders", include_summary=True)
        rendered = wiki_index.render_reverse(report)
        expected = """wiki-index reverse
==================
table: mysql_trade.orders
normalized_key: mysql_trade.orders
caveat: 基于 DataWorks 调度血缘，可能漏掉动态 SQL、脚本内临时表或未登记依赖。

Recommended
-----------
- [order] DWD dwd_order · pk_data.dwd_order · missing_knowledge_page · 明细定义层，通常优先作为业务口径候选。

ODS upstream
------------
- ods_order · inputs=['mysql_trade.orders'] · outputs=['pk_data.ods_order'] · missing_knowledge_page

Downstream candidates
---------------------
[order]
- DWD dwd_order · pk_data.dwd_order · missing_knowledge_page · 明细定义层，通常优先作为业务口径候选。
"""
        self.assertEqual(expected, rendered)

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
