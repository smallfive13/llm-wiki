"""TASK-051 (RFC-032): deployed-version code fetch + evidence snippets + binding lookup / origin."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import dataworks_client as dwc  # noqa: E402
import wiki_index  # noqa: E402


class _FakeModels:
    class GetFileVersionRequest:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs


class _FakeSdk:
    def __init__(self, body) -> None:
        self._body = body
        self.calls = 0

    def get_file_version(self, request):
        self.calls += 1

        class _Resp:
            pass

        resp = _Resp()
        resp.body = self._body
        return resp


class _FakeEvidenceClient:
    """Fake DataWorksClient for the evidence CLI path."""

    def __init__(self, content: str, *, version: int = 7, deployed: bool = True) -> None:
        self._content = content
        self._version = version
        self._deployed = deployed
        self.version_code_calls = 0

    def get_latest_deployed_version(self, raw_ref, **kwargs):
        if not self._deployed:
            return None
        return dwc.DataWorksFileVersion(
            file_version=self._version,
            commit_time_ms=None,
            commit_time_iso="2026-07-06T00:00:00+08:00",
            commit_user=None,
            change_type=None,
            status="DEPLOYED",
            use_type=None,
            file_name="fake.sql",
            comment=None,
        )

    def get_file_version_code(self, raw_ref, file_version):
        self.version_code_calls += 1
        return dwc.DataWorksFileCode(
            ref=dwc.parse_ref(raw_ref),
            content=self._content,
            content_path="Data.FileContent",
            sort_path="fake.sql",
            fingerprint=dwc.code_sha256([("fake.sql", self._content)]),
        )


def _run_cli(argv, client):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = dwc.main(argv, client_factory=lambda: client)
    return code, stdout.getvalue()


SAMPLE_SQL = "\n".join(
    ["-- header"]
    + [f"select col_{i} from t{i};" for i in range(1, 9)]
    + ["    ,sum(repay_amount) as repay_amount"]
    + [f"-- filler {i}" for i in range(1, 15)]
    + ["THIS_FAR_AWAY_LINE must never leak into snippet output"]
)


class GetFileVersionCodeTest(unittest.TestCase):
    def test_fetches_versioned_content_and_fingerprint(self):
        sdk = _FakeSdk({"Data": {"FileContent": "select 1;", "FileName": "a.sql"}})
        client = dwc.DataWorksClient(sdk, _FakeModels)
        code = client.get_file_version_code("file:96107/123", 5)
        self.assertEqual(code.content, "select 1;")
        self.assertEqual(code.content_path, "Data.FileContent")
        self.assertTrue(code.fingerprint.startswith("sha256:"))
        self.assertEqual(sdk.calls, 1)

    def test_missing_content_raises(self):
        client = dwc.DataWorksClient(_FakeSdk({"Data": {}}), _FakeModels)
        with self.assertRaises(dwc.DataWorksClientError) as ctx:
            client.get_file_version_code("file:96107/123", 5)
        self.assertEqual(ctx.exception.code, "CONTENT_MISSING")

    def test_invalid_version_rejected(self):
        client = dwc.DataWorksClient(_FakeSdk({}), _FakeModels)
        with self.assertRaises(dwc.DataWorksClientError) as ctx:
            client.get_file_version_code("file:96107/123", 0)
        self.assertEqual(ctx.exception.code, "INVALID_VERSION")


class ScanCodeEvidenceTest(unittest.TestCase):
    def test_hit_with_context_and_counts(self):
        report = dwc.scan_code_evidence(SAMPLE_SQL, ["repay_amount"], context=2)
        entry = report["patterns"][0]
        self.assertTrue(entry["matched"])
        self.assertEqual(entry["match_count"], 1)
        joined = "\n".join(entry["snippets"][0]["lines"])
        self.assertIn("repay_amount", joined)
        self.assertNotIn("THIS_FAR_AWAY_LINE", joined)

    def test_budget_caps_pathological_pattern(self):
        content = "\n".join(f"line {i}" for i in range(500))
        report = dwc.scan_code_evidence(content, ["."], context=5, max_total_lines=50)
        self.assertLessEqual(report["total_snippet_lines"], 50)
        self.assertTrue(report["truncated"])

    def test_invalid_regex(self):
        with self.assertRaises(dwc.DataWorksClientError) as ctx:
            dwc.scan_code_evidence("x", ["("])
        self.assertEqual(ctx.exception.code, "INVALID_PATTERN")


class EvidenceCliTest(unittest.TestCase):
    def test_snippets_only_and_cache_hit_on_second_run(self):
        client = _FakeEvidenceClient(SAMPLE_SQL)
        with tempfile.TemporaryDirectory() as tmp:
            argv = [
                "evidence",
                "--ref",
                "file:96107/555",
                "--pattern",
                "repay_amount",
                "--context",
                "2",
                "--cache-dir",
                tmp,
            ]
            code1, out1 = _run_cli(argv, client)
            code2, out2 = _run_cli(argv, client)
        self.assertEqual((code1, code2), (0, 0))
        self.assertIn("repay_amount", out1)
        self.assertIn("fingerprint: sha256:", out1)
        self.assertIn("cache: miss", out1)
        self.assertIn("cache: hit", out2)
        # 整段代码严禁落 stdout：远处未命中的行不得出现
        self.assertNotIn("THIS_FAR_AWAY_LINE", out1)
        self.assertNotIn("THIS_FAR_AWAY_LINE", out2)
        # 已提交版本不可变：第二次不再调 GetFileVersion
        self.assertEqual(client.version_code_calls, 1)

    def test_no_deployed_version_exits_1(self):
        client = _FakeEvidenceClient(SAMPLE_SQL, deployed=False)
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run_cli(
                ["evidence", "--ref", "file:96107/555", "--pattern", "x", "--cache-dir", tmp], client
            )
        self.assertEqual(code, 1)
        self.assertIn("NO_DEPLOYED_VERSION", out)

    def test_json_output_has_no_full_code(self):
        client = _FakeEvidenceClient(SAMPLE_SQL)
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run_cli(
                [
                    "evidence",
                    "--ref",
                    "file:96107/555",
                    "--pattern",
                    "repay_amount",
                    "--cache-dir",
                    tmp,
                    "--json",
                ],
                client,
            )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertNotIn("content", payload)
        self.assertNotIn("THIS_FAR_AWAY_LINE", out)


BINDING_INDEX = {
    "index_version": 2,
    "items": [
        {
            "node_id": 1,
            "node_name": "ods.loan_biz_autosync_2_user_feedback.extract",
            "table": "pk_data.ods.loan_biz_autosync_2_user_feedback.extract",
            "layer": "ODS",
            "inputs": [],
            "outputs": ["pk_data.ods.loan_biz_autosync_2_user_feedback.extract"],
            "source_binding": "parsed",
            "source_datasource": "loan_biz_autosync_3",
            "source_database": "loan_biz",
            "source_db_type": "mongodb",
            "source_tables": ["user_feedback"],
        },
        {
            "node_id": 2,
            "node_name": "ods_loan_biz_autosync_2_user_feedback",
            "table": "pk_data.ods_loan_biz_autosync_2_user_feedback",
            "layer": "ODS",
            "inputs": ["pk_data.ods.loan_biz_autosync_2_user_feedback.extract"],
            "outputs": ["pk_data.ods_loan_biz_autosync_2_user_feedback"],
            "source_binding": "inferred",
        },
        {
            "node_id": 3,
            "node_name": "dwd_user_feedback_dly",
            "table": "pk_data.dwd_user_feedback_dly",
            "layer": "DWD",
            "inputs": ["pk_data.ods_loan_biz_autosync_2_user_feedback"],
            "outputs": ["pk_data.dwd_user_feedback_dly"],
        },
    ],
}


class BindingLookupTest(unittest.TestCase):
    def _downstream_names(self, report):
        return {item["node_name"] for item in report["downstream_candidates"]}

    def test_database_qualified_query_hits(self):
        report = wiki_index.build_reverse_report(BINDING_INDEX, "loan_biz.user_feedback")
        self.assertIn("dwd_user_feedback_dly", self._downstream_names(report))

    def test_datasource_qualified_query_hits(self):
        report = wiki_index.build_reverse_report(BINDING_INDEX, "loan_biz_autosync_3.user_feedback")
        self.assertIn("dwd_user_feedback_dly", self._downstream_names(report))

    def test_basename_fallback_hits(self):
        report = wiki_index.build_reverse_report(BINDING_INDEX, "user_feedback")
        self.assertIn("dwd_user_feedback_dly", self._downstream_names(report))

    def test_non_parsed_items_add_no_binding_keys(self):
        self.assertEqual(wiki_index.item_binding_keys({"source_binding": "inferred", "source_tables": ["x"]}), set())
        self.assertEqual(wiki_index.item_binding_keys({}), set())

    def test_miss_warning_mentions_online_table_support(self):
        report = wiki_index.build_reverse_report(BINDING_INDEX, "no_such.table_here")
        self.assertTrue(report["warnings"])
        self.assertIn("索引中未命中该表", report["warnings"][0])
        self.assertIn("已支持直接输入线上表名反查", report["warnings"][0])


class OriginTest(unittest.TestCase):
    def test_traces_to_online_origin_and_denoises_same_chain(self):
        report = wiki_index.build_origin_report(BINDING_INDEX, "pk_data.dwd_user_feedback_dly")
        self.assertEqual(len(report["origins"]), 1)
        origin = report["origins"][0]
        self.assertEqual(origin["source_database"], "loan_biz")
        self.assertEqual(origin["source_table"], "user_feedback")
        self.assertEqual(origin["source_datasource"], "loan_biz_autosync_3")
        # 同链 inferred 阶段（node 2）应被去噪，不列为 unresolved
        self.assertEqual(report["unresolved_bindings"], [])
        self.assertFalse(report["warnings"])

    def test_unresolved_only_chain_is_reported(self):
        index = {
            "index_version": 2,
            "items": [
                {
                    "node_id": 10,
                    "node_name": "ods_only_inferred",
                    "table": "pk_data.ods_only_inferred",
                    "layer": "ODS",
                    "inputs": [],
                    "outputs": ["pk_data.ods_only_inferred"],
                    "source_binding": "inferred",
                },
                {
                    "node_id": 11,
                    "node_name": "dwd_x",
                    "table": "pk_data.dwd_x",
                    "layer": "DWD",
                    "inputs": ["pk_data.ods_only_inferred"],
                    "outputs": ["pk_data.dwd_x"],
                },
            ],
        }
        report = wiki_index.build_origin_report(index, "pk_data.dwd_x")
        self.assertEqual(report["origins"], [])
        self.assertEqual(len(report["unresolved_bindings"]), 1)
        self.assertEqual(report["unresolved_bindings"][0]["source_binding"], "inferred")

    def test_render_origin_contains_online_name(self):
        report = wiki_index.build_origin_report(BINDING_INDEX, "pk_data.dwd_user_feedback_dly")
        text = wiki_index.render_origin(report)
        self.assertIn("mongodb:loan_biz.user_feedback", text)
        self.assertIn("via datasource loan_biz_autosync_3", text)


class CachePathTest(unittest.TestCase):
    def test_roundtrip_and_naming(self):
        ref = dwc.parse_ref("file:96107/42")
        with tempfile.TemporaryDirectory() as tmp:
            path = dwc.store_cached_version_code(Path(tmp), ref, 3, "select 1;")
            self.assertEqual(path.name, "96107-42-v3.code")
            self.assertEqual(dwc.load_cached_version_code(Path(tmp), ref, 3), "select 1;")
            self.assertIsNone(dwc.load_cached_version_code(Path(tmp), ref, 4))

    def test_default_cache_dir_inside_engine_not_instance(self):
        cache_dir = dwc.default_version_cache_dir()
        self.assertEqual(cache_dir, REPO_ROOT / ".cache" / "dataworks" / "file_versions")


if __name__ == "__main__":
    unittest.main()
