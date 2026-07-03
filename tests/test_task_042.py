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
        "snapshot_date": "2026-07-03",
        "source_window": {"mode": "fixture"},
        "items": items,
    }


class Task042ReverseSummaryWarningTest(unittest.TestCase):
    def test_include_summary_candidate_suppresses_not_found_warning(self):
        idx = index(
            [
                item(1, "ddm_asset_limit_loan_dtl", "DDM", [], ["pk_data.ddm_asset_limit_loan_dtl"]),
                item(2, "edw_asset_report", "EDW", [], ["pk_data.edw_asset_report"]),
            ]
        )

        ddm = wiki_index.build_reverse_report(idx, "pk_data.ddm_asset_limit_loan_dtl", include_summary=True)
        edw = wiki_index.build_reverse_report(idx, "pk_data.edw_asset_report", include_summary=True)

        self.assertEqual(["ddm_asset_limit_loan_dtl"], [item["node_name"] for item in ddm["summary_candidates"]])
        self.assertEqual(["edw_asset_report"], [item["node_name"] for item in edw["summary_candidates"]])
        self.assertNotIn("索引中未命中该表", "\n".join(ddm["warnings"]))
        self.assertNotIn("索引中未命中该表", "\n".join(edw["warnings"]))

    def test_true_missing_table_still_warns(self):
        idx = index([item(1, "dwd_asset_loan_list", "DWD", [], ["pk_data.dwd_asset_loan_list"])])

        report = wiki_index.build_reverse_report(idx, "pk_data.not_existing_table", include_summary=True)

        self.assertEqual([], report["summary_candidates"])
        self.assertEqual([], report["recommended"])
        self.assertIn("索引中未命中该表", report["warnings"][0])


if __name__ == "__main__":
    unittest.main()
