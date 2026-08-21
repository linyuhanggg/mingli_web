#!/usr/bin/env python3
"""Metadata checks for the small v4 skill contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"


def _frontmatter() -> dict[str, object]:
    text = SKILL.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        raise AssertionError("SKILL.md is missing YAML frontmatter")
    loaded = yaml.safe_load(match.group(1))
    if not isinstance(loaded, dict):
        raise AssertionError("SKILL.md frontmatter must be a mapping")
    return loaded


class SkillMetadataTests(unittest.TestCase):
    def test_public_release_surfaces_identify_v5(self) -> None:
        readme = README.read_text(encoding="utf-8")
        changelog = CHANGELOG.read_text(encoding="utf-8")

        self.assertIn("版本-V5.1", readme)
        self.assertIn("| 当前版本 | V5.1 Provider Contract Hardened Core |", readme)
        self.assertIn("## V5.1 Provider Contract Hardened Core", changelog)

    def test_frontmatter_identifies_the_skill_and_explicit_scope(self) -> None:
        metadata = _frontmatter()

        self.assertEqual(metadata.get("name"), "mingli-master")
        description = str(metadata.get("description", ""))
        self.assertIn("命理", description)
        self.assertIn("明确", description)
        self.assertIn("同一份解读", description)
        self.assertNotIn("Cues:", description)
        self.assertLessEqual(len(description), 1024)

    def test_skill_body_describes_one_adapter_without_an_execution_recipe(self) -> None:
        body = SKILL.read_text(encoding="utf-8")

        self.assertIn("JSON Adapter", body)
        self.assertNotIn("scripts/", body)
        self.assertNotIn("json_cli.py", body)
        self.assertNotIn("run_reading_transaction.sh", body)

    def test_metadata_does_not_embed_a_system_trigger_inventory(self) -> None:
        description = str(_frontmatter().get("description", ""))

        for stale_inventory_item in (
            "紫微",
            "六爻",
            "梅花",
            "大六壬",
            "奇门",
            "太乙",
            "择日",
            "风水",
            "相法",
        ):
            self.assertNotIn(stale_inventory_item, description)


if __name__ == "__main__":
    unittest.main()
