import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dataworks_client  # noqa: E402
import wiki_index  # noqa: E402


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
        last_synced="2026-06-25T00:00:00+08:00",
    )


class Task033ReverseLookupTest(unittest.TestCase):
    def test_normalize_table_key_connects_dotted_ods_stage_to_underscore_table(self):
        self.assertEqual(
            "pk_data.ods_pak_listing_autosync_3_tb_repay_record",
            wiki_index.normalize_table_key("pk_data.ods.pak_listing_autosync_3_tb_repay_record.extract"),
        )
        self.assertEqual(
            "pk_data.ods_pak_listing_autosync_3_tb_repay_record",
            wiki_index.normalize_table_key("pk_data.ods_pak_listing_autosync_3_tb_repay_record"),
        )

    def test_identity_suffixes_are_not_merged(self):
        self.assertNotEqual(
            wiki_index.normalize_table_key("pk_data.dwb_asset_debt_dtl_snp"),
            wiki_index.normalize_table_key("pk_data.dwb_asset_debt_dtl_dly"),
        )

    def test_reverse_stops_at_first_detail_layer_and_keeps_domain_group(self):
        index = wiki_index.stable_index(
            [
                node(1, "ods.repay.extract", ["pk_data.ods.pak_listing_autosync_3_tb_repay_record.pre"], ["pk_data.ods.pak_listing_autosync_3_tb_repay_record.extract"]),
                node(2, "ods_pak_listing_autosync_3_tb_repay_record", ["pk_data.ods.pak_listing_autosync_3_tb_repay_record.extract"], ["pk_data.ods_pak_listing_autosync_3_tb_repay_record"]),
                node(3, "dwd_asset_repay_record", ["pk_data.ods_pak_listing_autosync_3_tb_repay_record"], ["pk_data.dwd_asset_repay_record"]),
                node(4, "dwb_asset_repay_dtl", ["pk_data.dwd_asset_repay_record"], ["pk_data.dwb_asset_repay_dtl"]),
                node(5, "dws_asset_repay_sum", ["pk_data.dwb_asset_repay_dtl"], ["pk_data.dws_asset_repay_sum"]),
            ],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-25",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki/asset-mappings").mkdir(parents=True)
            (root / "wiki/asset-mappings/repay.md").write_text("physical_table: pk_data.dwd_asset_repay_record\n", encoding="utf-8")
            report = wiki_index.build_reverse_report(
                index,
                "pk_data.ods.pak_listing_autosync_3_tb_repay_record.extract",
                root=root,
            )
        self.assertEqual("pk_data.ods_pak_listing_autosync_3_tb_repay_record", report["normalized_key"])
        self.assertEqual(["dwd_asset_repay_record"], [item["node_name"] for item in report["downstream_candidates"]])
        self.assertEqual(["asset"], list(report["domain_groups"]))
        self.assertEqual("has_knowledge_page", report["downstream_candidates"][0]["review"])
        self.assertEqual([], report["summary_candidates"])

    def test_include_summary_is_explicit(self):
        index = wiki_index.stable_index(
            [
                node(1, "dwd_asset_repay_record", ["pk_data.dwd_asset_repay_record"], ["pk_data.dwd_asset_repay_record"]),
                node(2, "dws_asset_repay_sum", ["pk_data.dwd_asset_repay_record"], ["pk_data.dws_asset_repay_sum"]),
            ],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-25",
        )
        hidden = wiki_index.build_reverse_report(index, "pk_data.dwd_asset_repay_record")
        shown = wiki_index.build_reverse_report(index, "pk_data.dwd_asset_repay_record", include_summary=True)
        self.assertEqual([], hidden["summary_candidates"])
        self.assertEqual(["dws_asset_repay_sum"], [item["node_name"] for item in shown["summary_candidates"]])

    def test_multiple_domains_are_grouped_without_cross_domain_expansion(self):
        index = wiki_index.stable_index(
            [
                node(1, "ods_source", [], ["pk_data.ods_trade_order"]),
                node(2, "dwd_asset_order", ["pk_data.ods_trade_order"], ["pk_data.dwd_asset_order"]),
                node(3, "dwd_risk_order", ["pk_data.ods_trade_order"], ["pk_data.dwd_risk_order"]),
                node(4, "dwb_fin_order", ["pk_data.dwd_asset_order"], ["pk_data.dwb_fin_order"]),
            ],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-25",
        )
        report = wiki_index.build_reverse_report(index, "pk_data.ods_trade_order")
        self.assertEqual(["asset", "risk"], list(report["domain_groups"]))
        self.assertEqual(["dwd_asset_order", "dwd_risk_order"], [item["node_name"] for item in report["downstream_candidates"]])

    def test_no_downstream_fallback_keeps_caveat(self):
        index = wiki_index.stable_index(
            [node(1, "ods_only", [], ["pk_data.ods_trade_order"])],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-25",
        )
        report = wiki_index.build_reverse_report(index, "pk_data.ods_trade_order")
        self.assertEqual(["ods_only"], [item["node_name"] for item in report["upstream_ods"]])
        self.assertTrue(report["warnings"])
        self.assertIn("动态 SQL", report["caveat"])

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

    def test_reverse_json_contains_domain_groups(self):
        index = wiki_index.stable_index(
            [node(1, "dwd_asset_order", ["pk_data.ods_trade_order"], ["pk_data.dwd_asset_order"])],
            project_id=96107,
            project_identifier="pk_data",
            snapshot_date="2026-06-25",
        )
        report = wiki_index.build_reverse_report(index, "pk_data.ods_trade_order")
        encoded = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.assertIn("domain_groups", encoded)


if __name__ == "__main__":
    unittest.main()
