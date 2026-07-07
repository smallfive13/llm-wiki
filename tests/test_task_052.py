import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, Optional


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
WIKI = REPO / "bin/wiki"
CONF = REPO / ".wiki-cli.conf"

sys.path.insert(0, str(SCRIPTS))

import dataworks_client  # noqa: E402
import wiki_eval  # noqa: E402
import wiki_freshness  # noqa: E402
import wiki_graph  # noqa: E402
import wiki_index  # noqa: E402
import wiki_lint  # noqa: E402
from wiki_common import resolve_instance_root_arg  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_instance(root: Path) -> None:
    for directory in [
        "wiki/topics",
        "wiki/sources",
        "wiki/entities",
        "wiki/decisions",
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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-07-07T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-07-07T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        (
            '{"version":1,"auto_capture":false,"default_visibility":"private",'
            '"hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},'
            '"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-07-07T00:00:00+08:00"}\n'
        ),
    )


def clean_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "WIKI_PY",
            "ALIBABA_CLOUD_ACCESS_KEY_ID",
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        }
    }
    if extra:
        env.update(extra)
    return env


class Task052EnvConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._existing_conf = CONF.read_text(encoding="utf-8") if CONF.exists() else None
        CONF.unlink(missing_ok=True)

    def tearDown(self) -> None:
        CONF.unlink(missing_ok=True)
        if self._existing_conf is not None:
            CONF.write_text(self._existing_conf, encoding="utf-8")

    def run_wiki(self, args: list[str], *, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(WIKI), *args],
            cwd=REPO,
            env=env or clean_env({"WIKI_PY": sys.executable}),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_old_and_new_subcommands_forward_to_expected_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            fake_python = Path(tmp) / "fake-python"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                f"printf '%s\\n' \"$@\" >> {marker!s}\n"
                "exit 0\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            env = clean_env({"WIKI_PY": str(fake_python)})
            cases = [
                (["lint", "--x"], "scripts/wiki_lint.py\n--x"),
                (["graph"], "scripts/wiki_graph.py"),
                (["eval", "--json"], "scripts/wiki_eval.py\n--json"),
                (["init", "--root", "x"], "scripts/wiki_init.py\n--root\nx"),
                (["freshness", "--help"], "scripts/wiki_freshness.py\n--help"),
                (["index", "reverse", "--help"], "scripts/wiki_index.py\nreverse\n--help"),
                (["evidence", "--help"], "scripts/dataworks_client.py\nevidence\n--help"),
            ]
            for args, expected in cases:
                marker.unlink(missing_ok=True)
                result = self.run_wiki(args, env=env)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn(expected, marker.read_text(encoding="utf-8"))

    def test_alias_resolves_in_all_five_root_aware_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "instance"
            init_instance(root)
            CONF.write_text(f"root.pk={root}\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(0, wiki_lint.main(["--root", "@pk", "--check-only"]))
                self.assertEqual(0, wiki_graph.main(["--root", "@pk", "--json"]))
                self.assertEqual(0, wiki_eval.main(["--root", "@pk", "--json"]))
                self.assertEqual(0, wiki_freshness.main(["--root", "@pk", "--json"], client_factory=lambda: None))
                self.assertEqual(2, wiki_index.main(["reverse", "--root", "@pk", "--table", "pk_data.ods_x"]))

    def test_alias_errors_and_dot_slash_real_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "instance"
            init_instance(root)

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                self.assertEqual(2, wiki_freshness.main(["--root", "@missing"], client_factory=lambda: None))
            self.assertIn("add root.missing=", err.getvalue())

            CONF.write_text("root.bad=/no/such/path\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                self.assertEqual(2, wiki_index.main(["reverse", "--root", "@bad", "--table", "pk_data.ods_x"]))
            self.assertIn("instance root not found: /no/such/path", err.getvalue())

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as raised:
                    wiki_lint.main(["--root", "@bad!", "--check-only"])
                self.assertEqual(2, raised.exception.code)
            self.assertIn("alias must match", err.getvalue())

            at_dir = Path(tmp) / "@pk"
            init_instance(at_dir)
            self.assertEqual(at_dir.resolve(), resolve_instance_root_arg(Path(tmp), "./@pk"))

    def test_conf_security_hard_fail_and_weak_keyword_warning(self) -> None:
        hard_cases = [
            "ACCESS_KEY_SECRET=abc\n",
            "root.pk=/tmp/LTAIabcdefghijkl\n",
            "python=/usr/bin/python\nroot.pk=/tmp/x\npassword=abc\n",
        ]
        for text in hard_cases:
            with self.subTest(text=text):
                CONF.write_text(text, encoding="utf-8")
                result = self.run_wiki(["doctor"])
                self.assertEqual(2, result.returncode)
                self.assertIn("credential-like content is not allowed", result.stderr)

        CONF.write_text("root.tk=/data/tokenized-features\n", encoding="utf-8")
        result = self.run_wiki(["doctor"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("@tk -> /data/tokenized-features", result.stdout)
        self.assertIn("warnings:", result.stdout)
        self.assertIn("weak keyword", result.stdout)

        CONF.write_text("unknown.key=value\n", encoding="utf-8")
        result = self.run_wiki(["doctor"])
        self.assertEqual(2, result.returncode)
        self.assertIn("unsupported key", result.stderr)

    def test_doctor_does_not_print_credential_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "instance"
            init_instance(root)
            CONF.write_text(f"python={sys.executable}\nroot.pk={root}\n", encoding="utf-8")
            result = self.run_wiki(
                ["doctor"],
                env=clean_env(
                    {
                        "ALIBABA_CLOUD_ACCESS_KEY_ID": "id-value-should-not-print",
                        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "secret-value-should-not-print",
                    }
                ),
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("ALIBABA_CLOUD_ACCESS_KEY_ID: present", result.stdout)
        self.assertIn("ALIBABA_CLOUD_ACCESS_KEY_SECRET: present", result.stdout)
        self.assertNotIn("id-value-should-not-print", result.stdout)
        self.assertNotIn("secret-value-should-not-print", result.stdout)
        self.assertIn("@pk ->", result.stdout)

    def test_offline_imports_do_not_load_online_modules(self) -> None:
        for name in list(sys.modules):
            if any(token in name.lower() for token in ("dataworks", "wiki_index", "alibabacloud", "sqlglot")):
                sys.modules.pop(name, None)
        import importlib

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
