import io
import json
import subprocess
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


FORBIDDEN = [
    "jdbc:",
    "://",
    "host",
    "address",
    "endpoint",
    "port",
    "username",
    "password",
    "accessKey",
    "secret",
    "token",
]


def assert_clean(testcase: unittest.TestCase, payload) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    for token in FORBIDDEN:
        testcase.assertNotIn(token.lower(), lowered)


def ds_item(name, ds_type, content, **extra):
    item = {
        "Name": name,
        "DataSourceType": ds_type,
        "Content": json.dumps(content, ensure_ascii=False),
        "GmtModified": "2026-07-03T00:00:00+08:00",
    }
    item.update(extra)
    return item


class FakeDatasourceClient:
    def __init__(self, resolutions):
        self.resolutions = resolutions

    def list_datasource_resolutions(self, project_id):
        return self.resolutions


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Task049DatasourceResolutionTest(unittest.TestCase):
    def test_parse_direct_database_and_never_leaks_raw_content(self):
        item = ds_item(
            "mysql_ds",
            "mysql",
            {
                "database": "loan_biz",
                "jdbcUrl": "jdbc:mysql://example.internal:3306/loan_biz",
                "username": "user",
                "password": "secret",
                "address": [{"host": "example.internal", "port": 3306}],
            },
        )
        resolution = dataworks_client.parse_datasource_resolution(item)
        payload = dataworks_client.datasource_resolution_to_map(resolution)
        self.assertEqual("mysql_ds", payload["datasource_name"])
        self.assertEqual("mysql", payload["db_type"])
        self.assertEqual("loan_biz", payload["database_name"])
        self.assertEqual("parsed", payload["resolution"])
        assert_clean(self, payload)

    def test_parse_mysql_jdbc_path_and_sqlserver_database_name(self):
        mysql = dataworks_client.parse_datasource_resolution(
            ds_item(
                "jdbc_mysql",
                "mysql",
                {"jdbcUrl": "jdbc:mysql://example.internal:3306/pak_backend?useUnicode=true", "username": "u", "password": "p"},
            )
        )
        sqlserver = dataworks_client.parse_datasource_resolution(
            ds_item(
                "jdbc_sqlserver",
                "sqlserver",
                {"jdbcUrl": "jdbc:sqlserver://example.internal:1433;databaseName=es_cdr_new", "username": "u", "password": "p"},
            )
        )
        self.assertEqual("pak_backend", mysql.database_name)
        self.assertEqual("es_cdr_new", sqlserver.database_name)
        assert_clean(self, dataworks_client.datasource_resolution_to_map(mysql))
        assert_clean(self, dataworks_client.datasource_resolution_to_map(sqlserver))

    def test_parse_mongodb_database_and_failed_without_raw_url(self):
        mongo = dataworks_client.parse_datasource_resolution(
            ds_item("mongo_ds", "mongodb", {"database": "pak_vendor_biz", "password": "p", "username": "u"})
        )
        failed = dataworks_client.parse_datasource_resolution(
            ds_item("bad_ds", "mysql", {"jdbcUrl": "jdbc:mysql://example.internal", "password": "p"})
        )
        self.assertEqual("pak_vendor_biz", mongo.database_name)
        self.assertEqual("failed", failed.resolution)
        self.assertIsNone(failed.database_name)
        assert_clean(self, dataworks_client.datasource_resolution_to_map(mongo))
        assert_clean(self, dataworks_client.datasource_resolution_to_map(failed))

    def test_sanitized_output_gate_catches_forbidden_tokens(self):
        with self.assertRaises(dataworks_client.DataWorksClientError):
            dataworks_client.assert_no_datasource_secrets({"jdbcUrl": "jdbc:mysql://x/y"})


class Task049MapIndexFreshnessTest(unittest.TestCase):
    def test_datasource_map_is_stable_sorted_and_clean(self):
        resolutions = [
            dataworks_client.parse_datasource_resolution(ds_item("z_ds", "mysql", {"database": "zdb", "password": "p"})),
            dataworks_client.parse_datasource_resolution(ds_item("a_ds", "mongodb", {"database": "adb", "username": "u"})),
        ]
        data = wiki_index.stable_datasource_map(resolutions, project_id=96107)
        self.assertEqual(["a_ds", "z_ds"], [item["datasource_name"] for item in data["items"]])
        self.assertEqual(1, data["map_version"])
        assert_clean(self, data)

    def test_attach_datasource_map_adds_optional_fields_without_bumping_index(self):
        index = {
            "index_version": 2,
            "items": [
                {"source_binding": "parsed", "source_datasource": "mysql_ds", "node_name": "ods.foo.extract"},
                {"source_binding": "inferred", "source_datasource": "other_ds", "node_name": "ods.foo.pre"},
                {"node_name": "legacy"},
            ],
        }
        data = wiki_index.stable_datasource_map(
            [dataworks_client.parse_datasource_resolution(ds_item("mysql_ds", "mysql", {"database": "loan_biz", "password": "p"}))],
            project_id=96107,
        )
        updated = wiki_index.attach_datasource_resolutions(index, data)
        self.assertEqual(2, updated["index_version"])
        self.assertEqual("loan_biz", updated["items"][0]["source_database"])
        self.assertEqual("mysql", updated["items"][0]["source_db_type"])
        self.assertNotIn("source_database", updated["items"][1])
        self.assertNotIn("source_database", updated["items"][2])
        assert_clean(self, updated)

    def test_old_index_reverse_output_unchanged_when_new_fields_absent(self):
        index = {
            "index_version": 2,
            "items": [
                {
                    "node_id": 1,
                    "node_name": "ods.foo.extract",
                    "table": "pk_data.ods_foo",
                    "inputs": ["online.foo"],
                    "outputs": ["pk_data.ods_foo"],
                    "layer": "ODS",
                    "dataworks_ref": "file:96107/1",
                },
                {
                    "node_id": 2,
                    "node_name": "dwd_foo",
                    "table": "pk_data.dwd_foo",
                    "inputs": ["pk_data.ods_foo"],
                    "outputs": ["pk_data.dwd_foo"],
                    "layer": "DWD",
                    "dataworks_ref": "file:96107/2",
                },
            ],
        }
        before = wiki_index.render_reverse(wiki_index.build_reverse_report(index, "online.foo"))
        # Re-render the same old index without source_database/source_db_type.
        after = wiki_index.render_reverse(wiki_index.build_reverse_report(json.loads(json.dumps(index)), "online.foo"))
        self.assertEqual(before, after)

    def test_datasource_freshness_diff_and_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / ".wiki/datasource_map.json",
                json.dumps(
                    {
                        "map_version": 1,
                        "project_id": 96107,
                        "source": {"kind": "ListDataSources", "env_type": 1},
                        "items": [
                            {"datasource_name": "mysql_ds", "db_type": "mysql", "database_name": "old_db", "resolution": "parsed"}
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
            fresh = dataworks_client.parse_datasource_resolution(ds_item("mysql_ds", "mysql", {"database": "new_db", "password": "p"}))
            report = wiki_freshness.evaluate_datasource_map(root, project_id=96107, client_factory=lambda: FakeDatasourceClient([fresh]))
            self.assertEqual("datasource_map", report["mode"])
            self.assertEqual(1, len(report["changes"]))
            self.assertEqual("changed", report["changes"][0]["status"])
            self.assertEqual("datasource_target_changed", report["review_queue_suggestions"][0]["type"])
            assert_clean(self, report)

            applied = wiki_freshness.evaluate_datasource_map(root, project_id=96107, client_factory=lambda: FakeDatasourceClient([fresh]), apply=True)
            self.assertTrue(applied["applied"]["map_written"])
            assert_clean(self, (root / ".wiki/datasource_map.json").read_text())

    def test_cli_datasource_map_and_check_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / ".wiki/datasource_map.json",
                json.dumps({"map_version": 1, "project_id": 96107, "source": {"kind": "ListDataSources", "env_type": 1}, "items": []}),
            )
            fresh = dataworks_client.parse_datasource_resolution(ds_item("mysql_ds", "mysql", {"database": "db", "password": "p"}))
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                rc = wiki_freshness.main(
                    ["--root", str(root), "--datasource-map", "--project-id", "96107", "--json"],
                    client_factory=lambda: FakeDatasourceClient([fresh]),
                )
            self.assertEqual(0, rc)
            payload = out.getvalue()
            self.assertEqual("datasource_map", json.loads(payload)["mode"])
            assert_clean(self, payload)

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = wiki_freshness.main(
                    ["--root", str(root), "--datasource-map", "--project-id", "96107", "--check"],
                    client_factory=lambda: FakeDatasourceClient([fresh]),
                )
            self.assertEqual(1, rc)

    def test_offline_core_tools_do_not_import_online_modules(self):
        code = (
            "import sys; sys.path.insert(0,'scripts'); "
            "import wiki_lint,wiki_graph,wiki_eval; "
            "mods=[m for m in sys.modules if any(k in m.lower() for k in ('dataworks','alibabacloud','sqlglot'))]; "
            "print(mods)"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=REPO, text=True, capture_output=True, check=True)
        self.assertEqual("[]", result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
