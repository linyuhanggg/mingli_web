#!/usr/bin/env python3
"""Regression tests for the distributable reference catalog."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mingli_pack
import search_bm25


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "catalog" / "catalog.json"
REQUIRED_PACK_FILES = (
    "index.md",
    "chapter-map.md",
    "terms.md",
    "rules.md",
    "procedures.md",
    "quote-index.md",
    "validation.md",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_all_ready_entries_resolve_to_complete_distilled_packs(self) -> None:
        entries = self.catalog["ready_reference_packs"]
        self.assertEqual(self.catalog["ready_count"], len(entries))
        self.assertEqual(len(entries), 55)
        for entry in entries:
            index = ROOT / entry["skill_index_path"]
            self.assertTrue(index.is_file(), entry["skill_index_path"])
            self.assertEqual(_sha256(index), entry["skill_index_sha256"])
            for name in REQUIRED_PACK_FILES:
                self.assertTrue((index.parent / name).is_file(), f"{index.parent}/{name}")

    def test_every_pack_has_consolidated_provenance_and_fulltext_checksum(self) -> None:
        for entry in self.catalog["ready_reference_packs"]:
            self.assertTrue(entry["source_anchor_url"].startswith(("http://", "https://")))
            self.assertRegex(entry["local_fulltext_sha256"], r"^[0-9a-f]{64}$")
            if entry["local_fulltext_policy"] == "verified_excerpt_distributed":
                self.assertEqual((entry["system"], entry["slug"]), ("san-shi", "qimen-faqiao"))
                excerpt = ROOT / entry["local_fulltext_path"]
                self.assertTrue(excerpt.is_file())
                self.assertEqual(_sha256(excerpt), entry["local_fulltext_sha256"])
                self.assertTrue(entry["local_fulltext_required_for_runtime"])
                self.assertEqual(
                    entry["redistribution_status"],
                    "ancient_text_public_domain_with_mit_transcription_provenance",
                )
            else:
                self.assertEqual(entry["local_fulltext_policy"], "local_only_not_distributed")
                self.assertFalse(entry["local_fulltext_required_for_runtime"])
                self.assertEqual(
                    entry["redistribution_status"],
                    "distilled_pack_only_source_licence_review_pending",
                )

    def test_catalog_contains_no_stale_layout_or_absolute_file_links(self) -> None:
        text = CATALOG.read_text(encoding="utf-8")
        self.assertNotIn('"references/bazi/', text)
        self.assertNotIn('"sources/normalized/', text)
        self.assertNotIn('"sources/derived/', text)
        self.assertNotIn("file:///Users/", text)

    def test_complete_transcriptions_are_not_tracked_for_release(self) -> None:
        if not (ROOT / ".git").exists() and not (ROOT / ".git").is_file():
            self.skipTest("not running from a Git checkout")
        tracked = subprocess.run(
            ["git", "ls-files", "references/fulltext/**"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(tracked, "")

    def test_fulltext_consumers_use_the_current_catalog_field(self) -> None:
        entry = self.catalog["ready_reference_packs"][0]
        expected = ROOT / entry["local_fulltext_path"]

        self.assertEqual(mingli_pack.catalog_fulltext_path(entry), expected)
        self.assertEqual(search_bm25.catalog_fulltext_path(entry), expected)

    def test_search_consumers_emit_the_product_simplified_canonical(self) -> None:
        self.assertIn("阴阳", search_bm25.tokenize("陰陽"))
        self.assertEqual(mingli_pack.compact("  陰陽  亥夘未木合  "), "阴阳 亥卯未木合")

    def test_regex_search_matches_the_canonical_view_of_real_l2460_text(self) -> None:
        raw_line = (
            "行合，即三合也。亥夘未木合，主繁宂驳杂；寅午戌火合，主侣党不正；"
            "巳酉丑金合，主矫革离异；申子辰水合，主流动无滞。"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fulltext = root / "references/fulltext/san-shi/daliuren-daquan/fulltext.md"
            fulltext.parent.mkdir(parents=True)
            fulltext.write_text("\n" * 2459 + raw_line + "\n", encoding="utf-8")
            raw_before_search = fulltext.read_bytes()

            with patch.object(mingli_pack, "SKILL_ROOT", root):
                hits = mingli_pack.search_file(
                    fulltext,
                    re.compile(mingli_pack.canonicalize("亥夘未木合")),
                    context=0,
                )

            self.assertEqual(len(hits), 1)
            self.assertTrue(
                hits[0].startswith(
                    "references/fulltext/san-shi/daliuren-daquan/fulltext.md:L2460: "
                )
            )
            self.assertIn("亥卯未木合", hits[0])
            self.assertEqual(fulltext.read_bytes(), raw_before_search)
            self.assertIn("亥夘未木合", fulltext.read_text(encoding="utf-8"))

    def test_regex_search_keeps_other_layers_and_no_hit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index = root / "references/books/san-shi/daliuren-daquan/index.md"
            index.parent.mkdir(parents=True)
            index.write_text("# 陰陽五行\n\n普通索引行\n", encoding="utf-8")

            with patch.object(mingli_pack, "SKILL_ROOT", root):
                hits = mingli_pack.search_file(
                    index,
                    re.compile(mingli_pack.canonicalize(r"陰陽.*行")),
                    context=0,
                )
                misses = mingli_pack.search_file(
                    index,
                    re.compile(mingli_pack.canonicalize("不存在的词")),
                    context=0,
                )

            self.assertEqual(
                hits,
                ["references/books/san-shi/daliuren-daquan/index.md:L1: # 阴阳五行"],
            )
            self.assertEqual(misses, [])

    def test_generated_catalog_has_no_drift_and_renders_blocked_raw_status(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "audit_reference_catalog.py"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        markdown = (
            ROOT / "references" / "catalog" / "D2_READY_REFERENCE_PACKS.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| blocked |", markdown)
        self.assertIn("| acquired |", markdown)


if __name__ == "__main__":
    unittest.main()
