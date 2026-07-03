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
import wiki_freshness  # noqa: E402
import wiki_index  # noqa: E402


def di_json(reader, writer=None):
    return json.dumps(
        {
            "type": "job",
            "version": "2.0",
            "steps": [
                {"category": "reader", "name": "reader", "stepType": reader[0], "parameter": reader[1]},
                writer
                or {
                    "category": "writer",
                    "name": "writer",
                    "stepType": "odps",
                    "parameter": {"datasource": "odps_target", "table": "pk_data.ods_target"},
                },
                {"category": "processor", "name": "processor", "parameter": {"nodes": [], "edges": []}},
            ],
        },
        ensure_ascii=False,
    )


class FakeNodeClient:
    def __init__(self, content_by_ref):
        self.content_by_ref = content_by_ref
        self.calls = []

    def get_file_code(self, raw_ref):
        self.calls.append(raw_ref)
        return type("FileCode", (), {"content": self.content_by_ref[raw_ref], "fingerprint": "sha256:new"})()

    def list_prod_nodes(self, project_id, max_pages=None):
        return [
            dataworks_client.DataWorksNode(
                node_id=1,
                node_name="ods.foo.extract",
                project_id=project_id,
                file_id=100,
                file_name="ods.foo.extract",
                file_path="ods/foo",
                file_version=1,
                program_type="DI",
                scheduler_type="NORMAL",
                repeatability=True,
                inputs=[],
                outputs=["pk_data.ods_foo"],
                tables=["pk_data.ods_foo"],
                fingerprint="sha256:old",
                last_synced="2026-07-03T00:00:00+08:00",
            ),
            dataworks_client.DataWorksNode(
                node_id=2,
                node_name="ods.foo.pre",
                project_id=project_id,
                file_id=200,
                file_name="ods.foo.pre",
                file_path="ods/foo_pre",
                file_version=1,
                program_type="PYODPS3",
                scheduler_type="NORMAL",
                repeatability=True,
                inputs=[],
                outputs=["pk_data.ods_foo_pre"],
                tables=["pk_data.ods_foo_pre"],
                fingerprint="sha256:py",
                last_synced="2026-07-03T00:00:00+08:00",
            ),
        ]


class FakeIncrementalClient:
    def __init__(self, content_by_ref, changes):
        self.content_by_ref = content_by_ref
        self.changes = changes
        self.calls = []

    def list_successful_prod_deployment_items(self, project_id, *, end_execute_time_ms=None, max_pages=None):
        return self.changes

    def get_file_code(self, raw_ref):
        self.calls.append(raw_ref)
        return type("FileCode", (), {"content": self.content_by_ref[raw_ref], "fingerprint": "sha256:new"})()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_index(root: Path, *, with_binding=True) -> None:
    item = {
        "index_version": 2,
        "project_id": 96107,
        "project_identifier": "pk_data",
        "snapshot_date": "2026-07-03",
        "source_window": {"mode": "fixture"},
        "items": [
            {
                "code_fingerprint": "sha256:old",
                "dataworks_ref": "file:96107/100",
                "file_id": 100,
                "file_path": "ods/foo",
                "fingerprint_version": "dw-code-v1",
                "inputs": [],
                "last_synced": "2026-07-03T00:00:00+08:00",
                "layer": "ODS",
                "layer_source": "name_prefix",
                "node_id": 1,
                "node_name": "ods.foo.extract",
                "outputs": ["pk_data.ods_foo"],
                "program_type": "DI",
                "table": "pk_data.ods_foo",
            },
            {
                "code_fingerprint": "sha256:old2",
                "dataworks_ref": "file:96107/200",
                "file_id": 200,
                "file_path": "ods/bar",
                "fingerprint_version": "dw-code-v1",
                "inputs": [],
                "last_synced": "2026-07-03T00:00:00+08:00",
                "layer": "ODS",
                "layer_source": "name_prefix",
                "node_id": 2,
                "node_name": "ods.bar.pre",
                "outputs": ["pk_data.ods_bar"],
                "program_type": "PYODPS3",
                "source_binding": "inferred",
                "table": "pk_data.ods_bar",
            },
        ],
    }
    if with_binding:
        item["items"][0].update(
            {
                "source_binding": "parsed",
                "source_datasource": "old_ds",
                "source_tables": ["old_table"],
            }
        )
    write(root / ".wiki/dataworks_index.json", json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


class Task047BindingParserTest(unittest.TestCase):
    def test_mysql_connection_tables_are_all_collected_and_writer_ignored(self):
        content = di_json(
            (
                "mysql",
                {"connection": [{"datasource": "mysql_ds", "table": ["orders", "orders_ext"]}], "where": "dt=${bizdate}"},
            ),
            writer={"category": "writer", "stepType": "odps", "parameter": {"datasource": "odps", "table": "pk_data.not_source"}},
        )
        binding = dataworks_client.parse_di_source_binding(content)
        self.assertEqual("parsed", binding.source_binding)
        self.assertEqual("mysql_ds", binding.source_datasource)
        self.assertEqual(["orders", "orders_ext"], binding.source_tables)
        self.assertNotIn("pk_data.not_source", binding.source_tables)

    def test_mongodb_collection_name_maps_to_source_tables(self):
        content = di_json(("mongodb", {"datasource": "mongo_ds", "collectionName": "loan_events", "query": "{}"}))
        binding = dataworks_client.parse_di_source_binding(content)
        self.assertEqual("parsed", binding.source_binding)
        self.assertEqual("mongo_ds", binding.source_datasource)
        self.assertEqual(["loan_events"], binding.source_tables)

    def test_sqlserver_uses_connection_shape(self):
        content = di_json(("sqlserver", {"connection": [{"datasource": "mssql_ds", "table": ["dbo.Customer"]}]}))
        binding = dataworks_client.parse_di_source_binding(content)
        self.assertEqual("parsed", binding.source_binding)
        self.assertEqual("mssql_ds", binding.source_datasource)
        self.assertEqual(["dbo.Customer"], binding.source_tables)

    def test_ambiguous_shapes_are_not_hard_parsed(self):
        multi = json.dumps({"steps": [{"category": "reader", "stepType": "mysql", "parameter": {}}, {"category": "reader", "stepType": "mongodb", "parameter": {}}]})
        self.assertEqual("ambiguous", dataworks_client.parse_di_source_binding(multi).source_binding)
        missing_table = di_json(("mysql", {"connection": [{"datasource": "mysql_ds", "table": []}]}))
        binding = dataworks_client.parse_di_source_binding(missing_table)
        self.assertEqual("ambiguous", binding.source_binding)
        self.assertTrue(binding.binding_warnings)

    def test_non_json_unparsed_and_pyodps_inferred(self):
        self.assertEqual("unparsed", dataworks_client.parse_di_source_binding("select 1", program_type="DI").source_binding)
        self.assertEqual("inferred", dataworks_client.parse_di_source_binding("# python", program_type="PYODPS3").source_binding)


class Task047IndexAndFreshnessTest(unittest.TestCase):
    def test_build_index_adds_optional_binding_fields_without_bumping_v2(self):
        client = FakeNodeClient(
            {
                "file:96107/100": di_json(("mysql", {"connection": [{"datasource": "mysql_ds", "table": ["orders"]}]})),
            }
        )
        idx = wiki_index.build_index(client, project_id=96107, project_identifier="pk_data", snapshot_date="2026-07-03")
        self.assertEqual(2, idx["index_version"])
        di_item = [item for item in idx["items"] if item["program_type"] == "DI"][0]
        py_item = [item for item in idx["items"] if item["program_type"] == "PYODPS3"][0]
        self.assertEqual("parsed", di_item["source_binding"])
        self.assertEqual("mysql_ds", di_item["source_datasource"])
        self.assertEqual(["orders"], di_item["source_tables"])
        self.assertEqual("inferred", py_item["source_binding"])

    def test_incremental_reparses_only_changed_di_or_parsed_items_and_reports_binding_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki").mkdir()
            write_index(root)
            changes = [
                dataworks_client.DataWorksDeploymentItem(1, 200, 1, 1780000000000, "2026-07-03T00:00:00+08:00", 2),
                dataworks_client.DataWorksDeploymentItem(2, 100, 2, 1780000001000, "2026-07-03T00:00:01+08:00", 2),
            ]
            client = FakeIncrementalClient(
                {
                    "file:96107/100": di_json(("mysql", {"connection": [{"datasource": "new_ds", "table": ["new_table"]}]})),
                    "file:96107/200": "# pyodps",
                },
                changes,
            )
            report = wiki_freshness.evaluate_deployment_incremental(root, project_id=96107, client_factory=lambda: client)
            self.assertEqual(["file:96107/100", "file:96107/200"], sorted(client.calls))
            by_file = {item["file_id"]: item for item in report["changed_files"]}
            self.assertNotIn("binding_changed", by_file[200])
            self.assertTrue(by_file[100]["binding_changed"])
            self.assertEqual("old_ds", by_file[100]["binding_previous"]["source_datasource"])
            self.assertEqual("new_ds", by_file[100]["binding_current"]["source_datasource"])
            self.assertEqual(["BINDING_CHANGED"], [item["code"] for item in report["warnings"]])
            self.assertEqual("source_binding_changed", report["review_queue_suggestions"][0]["type"])

    def test_incremental_apply_updates_binding_fields_but_not_page_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".wiki").mkdir()
            (root / "wiki/topics").mkdir(parents=True)
            write(root / "wiki/topics/foo.md", "---\nid: top_20260703_foo\ntype: topic\nstatus: active\ncreated: 2026-07-03\nupdated: 2026-07-03\nlast_verified: 2026-07-03\nreview: false\nsource_ids: []\nrelated_ids: []\nsources: []\nrelated: []\nsupersedes: []\nsuperseded_by: []\nevidence_count: 0\n---\n# Foo\n")
            write_index(root)
            changes = [dataworks_client.DataWorksDeploymentItem(2, 100, 2, 1780000001000, "2026-07-03T00:00:01+08:00", 2)]
            client = FakeIncrementalClient(
                {"file:96107/100": di_json(("mysql", {"connection": [{"datasource": "new_ds", "table": ["new_table"]}]}))},
                changes,
            )
            report = wiki_freshness.evaluate_deployment_incremental(root, project_id=96107, client_factory=lambda: client, apply=True)
            idx = json.loads((root / ".wiki/dataworks_index.json").read_text(encoding="utf-8"))
            item = idx["items"][0]
            self.assertTrue(report["applied"]["index_written"])
            self.assertEqual("new_ds", item["source_datasource"])
            self.assertEqual(["new_table"], item["source_tables"])
            self.assertIn("status: active", (root / "wiki/topics/foo.md").read_text(encoding="utf-8"))

    def test_offline_tools_do_not_import_online_modules(self):
        for name in list(sys.modules):
            if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud", "sqlglot")):
                sys.modules.pop(name, None)
        sys.path.insert(0, str(SCRIPTS))
        importlib.import_module("wiki_lint")
        importlib.import_module("wiki_graph")
        importlib.import_module("wiki_eval")
        leaked = [name for name in sys.modules if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud", "sqlglot"))]
        self.assertEqual([], leaked)


if __name__ == "__main__":
    unittest.main()
