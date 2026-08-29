"""Direct contracts for the deterministic simplified-corpus rebuild."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build_simplified_corpus import (
    LEGACY_GOLDEN,
    _load_legacy,
    _validate_output_root,
    collect_passages,
    parse_quote_index,
    render_passage_index,
)


class BuildSimplifiedCorpusTests(unittest.TestCase):
    def test_rebuild_output_cannot_overwrite_raw_or_reuse_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            research = Path(temporary) / "research"
            research.mkdir()
            with self.assertRaisesRegex(ValueError, "read-only research"):
                _validate_output_root(research, research)
            with self.assertRaisesRegex(ValueError, "read-only research"):
                _validate_output_root(research, research / "derived")

            stale = Path(temporary) / "stale"
            stale.mkdir()
            (stale / "old.txt").write_text("old", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "absent or empty"):
                _validate_output_root(research, stale)

    def test_legacy_golden_is_verdict_only_migration_evidence(self) -> None:
        metadata, verdicts = _load_legacy(LEGACY_GOLDEN)

        self.assertEqual(metadata["accepted_passages"], 101_701)
        self.assertEqual(metadata["citation_count"], 19_418)
        self.assertEqual(
            metadata["comparator"]["role"],
            "migration_comparison_only_not_rule_source",
        )
        self.assertEqual(len(verdicts), 19_418)
        for record in verdicts.values():
            self.assertEqual(
                set(record),
                {"record_type", "citation_id", "status", "anchor"},
            )

    def test_quote_registry_parser_covers_all_supported_shapes(self) -> None:
        fixtures = {
            "table": """| id | quote | section | source_anchor |
|---|---|---|---|
| T-Q001 | 陰陽亥夘未木合 | 一 | fulltext.md L2 |
""",
            "fields": """### DLQ-001
- exact_quote: `陰陽亥夘未木合`
- normalized_anchor: `fulltext.md:L2`
""",
            "bold_fields": """### LM-Q001
- **exact_quote**: `陰陽亥夘未木合`
- **source_location**: fulltext.md L2
""",
        }

        parsed = {
            name: parse_quote_index(text, pack=f"fixture/{name}")
            for name, text in fixtures.items()
        }

        self.assertEqual([item.local_id for item in parsed["table"]], ["T-Q001"])
        self.assertEqual([item.local_id for item in parsed["fields"]], ["DLQ-001"])
        self.assertEqual([item.local_id for item in parsed["bold_fields"]], ["LM-Q001"])
        for citations in parsed.values():
            self.assertEqual(citations[0].quote, "陰陽亥夘未木合")
            self.assertEqual(citations[0].line_start, 2)
            self.assertEqual(citations[0].line_end, 2)

    def test_passage_index_is_simplified_and_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "references/fulltext/fixture/book/fulltext.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "# 陰陽五行\n\n- source_url: https://example.invalid\n亥夘未木合。\n「華山。」\n```\n",
                encoding="utf-8",
            )

            passages = collect_passages(root)
            first = render_passage_index(passages)
            second = render_passage_index(collect_passages(root))

            self.assertEqual(first, second)
            self.assertEqual(len(passages), 3)
            self.assertEqual(passages[0].text, "# 阴阳五行")
            self.assertEqual(passages[1].text, "亥卯未木合。")
            self.assertEqual(passages[1].norm, "亥卯未木合")
            self.assertEqual(passages[2].text, "「华山。」")
            self.assertEqual(passages[2].norm, "华山")


if __name__ == "__main__":
    unittest.main()
