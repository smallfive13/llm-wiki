import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import wiki_graph  # noqa: E402
from wiki_common import BASE_SCHEMA, MarkdownDoc, strip_code_spans  # noqa: E402


def doc(rel: str, pid: str, body: str, *, related_ids=None) -> MarkdownDoc:
    related_ids = related_ids or []
    return MarkdownDoc(
        path=Path(rel),
        rel=rel,
        fm={
            "id": pid,
            "type": "topic",
            "status": "active",
            "confidence": "medium",
            "review": True,
            "last_verified": "2026-01-01",
            "source_ids": [],
            "related_ids": related_ids,
            "supersedes": [],
        },
        body=body,
        line_map={},
        has_frontmatter=True,
    )


def build_fixture_edges(docs):
    redirects = wiki_graph.build_redirect_map(docs)
    nodes, _unknown = wiki_graph.build_nodes(docs, BASE_SCHEMA)
    lookups = {
        "alias": {},
        "path": {},
        "slug": {
            wiki_graph.normalize_wikilink_target(Path(item.rel).stem): wiki_graph.page_id(item)
            for item in docs
            if wiki_graph.page_id(item)
        },
        "ambiguous_slugs": set(),
    }
    return wiki_graph.build_edges(docs, nodes, redirects, lookups)


def edge_pairs(edges):
    return {(edge["source"], edge["target"], edge["relation"], edge["source_kind"]) for edge in edges}


class StripCodeSpansTest(unittest.TestCase):
    def test_preserves_length_and_newlines(self) -> None:
        text = "before `[[fake]]` after\n```py\n[[fake2]]\n```\nreal [[target]]\n"
        stripped = strip_code_spans(text)
        self.assertEqual(len(text), len(stripped))
        self.assertEqual(text.count("\n"), stripped.count("\n"))
        self.assertNotIn("[[fake]]", stripped)
        self.assertNotIn("[[fake2]]", stripped)
        self.assertIn("[[target]]", stripped)

    def test_fenced_block_boundaries(self) -> None:
        text = (
            "  ~~~python\n"
            "[[tilde-fake]]\n"
            "~~~~\n"
            "   ```js\n"
            "[[indented-fake]]\n"
            "````\n"
            "    ```\n"
            "[[not-fenced]]\n"
            "    ```\n"
        )
        stripped = strip_code_spans(text)
        self.assertNotIn("[[tilde-fake]]", stripped)
        self.assertNotIn("[[indented-fake]]", stripped)
        self.assertIn("[[not-fenced]]", stripped)

    def test_unclosed_fence_strips_to_eof(self) -> None:
        stripped = strip_code_spans("before\n```\n[[fake]]\nafter [[also-fake]]")
        self.assertIn("before", stripped)
        self.assertNotIn("[[fake]]", stripped)
        self.assertNotIn("[[also-fake]]", stripped)

    def test_inline_backtick_run_boundaries(self) -> None:
        text = "real [[target]] ``[[fake]] ` still fake`` `[[unclosed]]"
        stripped = strip_code_spans(text)
        self.assertIn("[[target]]", stripped)
        self.assertNotIn("[[fake]]", stripped)
        self.assertIn("[[unclosed]]", stripped)


class WikilinkParsingTest(unittest.TestCase):
    def test_parse_wikilink_unescapes_table_pipe_before_display_and_anchor(self) -> None:
        self.assertEqual("target-slug", wiki_graph.parse_wikilink(r"target-slug\|显示"))
        self.assertEqual("target-slug", wiki_graph.parse_wikilink(r"target-slug#section\|显示"))
        self.assertEqual("target-slug", wiki_graph.parse_wikilink(r" target-slug\ "))

    def test_build_edges_keeps_real_and_table_links_but_ignores_code_links(self) -> None:
        docs = [
            doc(
                "wiki/topics/source.md",
                "top_20260101_source",
                "\n".join(
                    [
                        "Real [[real-target|Real Target]].",
                        "Inline code `[[inline-fake]]`.",
                        "```python",
                        "[[fenced-fake]]",
                        "```",
                        "| col |",
                        "| --- |",
                        r"| [[table-target\|Table Target]] |",
                    ]
                ),
            ),
            doc("wiki/topics/real-target.md", "top_20260101_real-target", "# Real Target"),
            doc("wiki/topics/table-target.md", "top_20260101_table-target", "# Table Target"),
        ]
        edges, dangling, ambiguous = build_fixture_edges(docs)
        pairs = edge_pairs(edges)
        self.assertIn(("top_20260101_source", "top_20260101_real-target", "wikilink", "wikilink"), pairs)
        self.assertIn(("top_20260101_source", "top_20260101_table-target", "wikilink", "wikilink"), pairs)
        self.assertFalse(any(edge[1] == "top_20260101_inline-fake" for edge in pairs))
        self.assertFalse(any(edge[1] == "top_20260101_fenced-fake" for edge in pairs))
        self.assertEqual([], dangling)
        self.assertEqual([], ambiguous)

    def test_code_duplicate_slug_does_not_create_false_ambiguous(self) -> None:
        source = doc(
            "wiki/topics/source.md",
            "top_20260101_source",
            "Real [[real-target]].\n`[[dup]]`\n```md\n[[dup]]\n```\n",
        )
        docs = [
            source,
            doc("wiki/topics/real-target.md", "top_20260101_real-target", "# Real Target"),
            doc("wiki/topics/one/dup.md", "top_20260101_dup-one", "# Dup One"),
            doc("wiki/topics/two/dup.md", "top_20260101_dup-two", "# Dup Two"),
        ]
        redirects = wiki_graph.build_redirect_map(docs)
        nodes, _unknown = wiki_graph.build_nodes(docs, BASE_SCHEMA)
        lookups = wiki_graph.build_wikilink_lookup(Path(tempfile.gettempdir()), docs, redirects)
        edges, dangling, ambiguous = wiki_graph.build_edges(docs, nodes, redirects, lookups)
        self.assertIn(("top_20260101_source", "top_20260101_real-target", "wikilink", "wikilink"), edge_pairs(edges))
        self.assertEqual([], dangling)
        self.assertEqual([], ambiguous)

    def test_canonical_edges_do_not_use_stripped_body(self) -> None:
        docs = [
            doc(
                "wiki/topics/source.md",
                "top_20260101_source",
                "```md\n[[real-target]]\n```\n",
                related_ids=["top_20260101_real-target"],
            ),
            doc("wiki/topics/real-target.md", "top_20260101_real-target", "# Real Target"),
        ]
        edges, dangling, ambiguous = build_fixture_edges(docs)
        pairs = edge_pairs(edges)
        self.assertIn(("top_20260101_source", "top_20260101_real-target", "related", "canonical"), pairs)
        self.assertNotIn(("top_20260101_source", "top_20260101_real-target", "wikilink", "wikilink"), pairs)
        self.assertEqual([], dangling)
        self.assertEqual([], ambiguous)


if __name__ == "__main__":
    unittest.main()
