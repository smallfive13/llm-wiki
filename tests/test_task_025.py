import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/wiki_init.py"

IGNORE_TEXT = (
    "# 检索优化（rg / fd 原生读 .ignore，对 agent 答疑透明；不影响 wiki_lint/graph 的 Python 扫描）。\n"
    "# 答疑只需 wiki/ + 上下文层（purpose/index/overview/log）；原始材料、图片、派生层、图谱不参与全文检索。\n"
    "# ingest 若需检索已归档原文，用 `rg --no-ignore` 或显式路径；raw/dropbox/（待处理投料）刻意保留可搜。\n"
    "raw/sources/\n"
    "raw/source_manifest.json\n"
    "maps/\n"
    ".wiki/\n"
)
IGNORE_LINES = IGNORE_TEXT.splitlines()
GITIGNORE_REQUIRED = [
    "# wiki 派生层（可重建，不进 Git）",
    "**/.wiki/id_index.json",
    "**/.wiki/inbox_index.json",
    "**/.wiki/normalized_alias_index.json",
    "**/.wiki/cache.json",
    "**/.wiki/search_index/",
    "**/.wiki/lightrag/",
    "!**/.wiki/schema_sync.json",
    "**/maps/graph-data.json",
    "**/maps/knowledge-graph.md",
    "**/maps/graph-insights.md",
    "# Obsidian 每机器配置",
    "**/.obsidian/workspace.json",
    "**/.obsidian/workspace-mobile.json",
]


def run_init(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )


class Task025IgnoreFileTest(unittest.TestCase):
    def test_new_instance_writes_ignore_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inst"
            result = run_init("--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertEqual(IGNORE_TEXT, (root / ".ignore").read_text(encoding="utf-8"))
            self.assertFalse((root / ".git").exists())

    @unittest.skipUnless(shutil.which("rg"), "rg 不在 PATH（conda run / CI 镜像）")
    def test_rg_uses_ignore_and_keeps_wiki_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inst"
            result = run_init("--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            (root / "raw/sources/x.md").write_text("needle-task-025\n", encoding="utf-8")
            (root / "wiki/topics/y.md").write_text("needle-task-025\n", encoding="utf-8")

            rg = subprocess.run(
                ["rg", "--files-with-matches", "needle-task-025", str(root)],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, rg.returncode, rg.stderr + rg.stdout)
            matches = {Path(line).relative_to(root).as_posix() for line in rg.stdout.splitlines()}
            self.assertEqual({"wiki/topics/y.md"}, matches)

    def test_existing_ignore_preserves_user_line_and_appends_missing_standard_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inst"
            root.mkdir()
            (root / ".ignore").write_text("custom/path/\nraw/sources/\n", encoding="utf-8")

            result = run_init("--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            lines = (root / ".ignore").read_text(encoding="utf-8").splitlines()
            self.assertEqual("custom/path/", lines[0])
            self.assertEqual(1, lines.count("custom/path/"))
            for line in IGNORE_LINES:
                self.assertEqual(1, lines.count(line), line)

    def test_ignore_directory_is_config_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inst"
            (root / ".ignore").mkdir(parents=True)

            result = run_init("--root", str(root))
            self.assertEqual(2, result.returncode)
            output = result.stderr + result.stdout
            self.assertIn("expected file but found directory", output)
            self.assertIn(".ignore", output)
            self.assertNotIn("Traceback", output)

    def test_gitignore_still_appends_missing_lines_and_preserves_user_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inst"
            root.mkdir()
            (root / ".gitignore").write_text("custom-git\n**/.wiki/id_index.json\n", encoding="utf-8")

            result = run_init("--root", str(root), "--git")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
            self.assertEqual("custom-git", lines[0])
            self.assertEqual(1, lines.count("custom-git"))
            for line in GITIGNORE_REQUIRED:
                self.assertEqual(1, lines.count(line), line)


if __name__ == "__main__":
    unittest.main()
