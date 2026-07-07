import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
WIKI = REPO / "bin/wiki"
SCRIPTS = REPO / "scripts"
PY312 = "/Users/zhangjunwu/soft/anaconda3/bin/conda run -n py312 python"


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
    write(root / "raw/source_manifest.json", '{"version":1,"sources":[],"updated_at":"2026-06-09T00:00:00+08:00"}\n')
    write(root / ".wiki/review_queue.json", '{"version":1,"items":[],"updated_at":"2026-06-09T00:00:00+08:00"}\n')
    write(
        root / ".wiki/capture_policy.json",
        (
            '{"version":1,"auto_capture":false,"default_visibility":"private",'
            '"hard_redact":{"patterns":[]},"soft_redact":{"patterns":[]},'
            '"exclude_paths":[],"max_inbox_files":100,"updated_at":"2026-06-09T00:00:00+08:00"}\n'
        ),
    )


def bad_page(root: Path) -> None:
    write(
        root / "wiki/topics/bad.md",
        "\n".join(
            [
                "---",
                "id: top_20260609_bad",
                "type: topic",
                "status: active",
                "confidence: medium",
                "created: 2026-06-09",
                "updated: 2026-06-09",
                "last_verified: 2026-06-09",
                "review: true",
                "source_ids: []",
                "related_ids: []",
                "sources: []",
                "related: []",
                "supersedes: []",
                "superseded_by: []",
                "evidence_count: 0",
                "visibility: invalid",
                "---",
                "",
                "# Bad",
                "",
            ]
        ),
    )


def env(extra: dict | None = None) -> dict:
    data = os.environ.copy()
    data["WIKI_PY"] = PY312
    if extra:
        data.update(extra)
    return data


def run_wrapper(args: list[str], *, cwd: Path = REPO, extra_env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(WIKI), *args], cwd=cwd, env=env(extra_env), text=True, capture_output=True, check=False)


def run_direct(script: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*shlex.split(PY312), str(SCRIPTS / script), *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


class Task022WikiWrapperTest(unittest.TestCase):
    def test_lint_eval_and_check_docs_match_direct_stdout_and_exit(self) -> None:
        cases = [
            ("lint", "wiki_lint.py", ["--root", "knowledge", "--check-only"]),
            ("eval", "wiki_eval.py", ["--root", "knowledge"]),
            ("lint", "wiki_lint.py", ["--root", "knowledge", "--check-docs"]),
        ]
        for subcommand, script, args in cases:
            with self.subTest(subcommand=subcommand, args=args):
                wrapper = run_wrapper([subcommand, *args])
                direct = run_direct(script, args)
                self.assertEqual(direct.returncode, wrapper.returncode)
                self.assertEqual(direct.stdout, wrapper.stdout)
                self.assertEqual(direct.stderr, wrapper.stderr)

    def test_lint_runs_from_arbitrary_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "instance"
            init_instance(root)
            other = Path(tmp) / "other cwd"
            other.mkdir()

            result = run_wrapper(["lint", "--root", str(root), "--check-only"], cwd=other)
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertIn("错误: 0", result.stdout)
            self.assertNotIn("must run from repo root", result.stderr)

    def test_argument_with_spaces_is_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "space dir"
            init_instance(root)
            result = run_wrapper(["lint", "--root", str(root), "--check-only"])
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertIn(str(root), result.stderr)

    def test_wiki_py_missing_command_reports_clear_error(self) -> None:
        result = subprocess.run(
            [str(WIKI), "lint", "--root", "knowledge", "--check-only"],
            cwd=REPO,
            env={**os.environ, "WIKI_PY": "/no/such/wiki-python-command"},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Python command not found", result.stderr)

    def test_empty_config_python_does_not_empty_exec(self) -> None:
        conf = REPO / ".wiki-cli.conf"
        existing = conf.read_text(encoding="utf-8") if conf.exists() else None
        try:
            conf.write_text("python=\n", encoding="utf-8")
            result = subprocess.run(
                [str(WIKI), "lint", "--root", "knowledge", "--check-only"],
                cwd=REPO,
                env={key: value for key, value in os.environ.items() if key != "WIKI_PY"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("python= is empty", result.stderr)
        finally:
            conf.unlink(missing_ok=True)
            if existing is not None:
                conf.write_text(existing, encoding="utf-8")

    def test_exit_code_passthrough_for_lint_error_and_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bad"
            init_instance(root)
            bad_page(root)
            lint_error = run_wrapper(["lint", "--root", str(root), "--check-only"])
            self.assertEqual(1, lint_error.returncode, lint_error.stderr + lint_error.stdout)
            self.assertIn("ENUM_INVALID", lint_error.stdout)

            config_error = run_wrapper(["lint", "--root", str(Path(tmp) / "missing"), "--check-only"])
            self.assertEqual(2, config_error.returncode)
            self.assertIn("instance root not found", config_error.stderr)

    def test_init_sync_schema_force_is_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "space dir"
            root.mkdir()
            (root / ".wiki-schema.md").write_text("local\n", encoding="utf-8")
            result = run_wrapper(["init", "--root", str(root), "--sync-schema", "--force"])
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertIn("action: forced", result.stdout)
            self.assertTrue((root / ".wiki/schema_sync.json").is_file())

    def test_unknown_subcommand_reports_error(self) -> None:
        result = run_wrapper(["bogus"])
        self.assertEqual(2, result.returncode)
        self.assertIn("unknown subcommand", result.stderr)

    def test_wiki_py_override_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            fake_python = Path(tmp) / "fake-python"
            real_python = sys.executable
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                f"echo \"$@\" > {marker!s}\n"
                f"exec {real_python!r} \"$@\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            result = subprocess.run(
                [str(WIKI), "lint", "--root", "knowledge", "--check-docs"],
                cwd=REPO,
                env={**os.environ, "WIKI_PY": str(fake_python)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertTrue(marker.is_file())
            self.assertIn("scripts/wiki_lint.py --root knowledge --check-docs", marker.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
