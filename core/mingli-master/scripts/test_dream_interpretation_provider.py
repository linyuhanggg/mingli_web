#!/usr/bin/env python3
"""Empty-table 解梦 Provider. Not in catalog; unmatched is fail-closed."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from reading_engine.dream_interpretation import DreamInterpretationProvider


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
RULES = ROOT / "references" / "matrices" / "dream-interpretation-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "dream-interpretation-samples-v1.yaml"
VIEW_SCHEMA = (
    REPO / "contracts" / "schemas" / "views" / "dream-interpretation-view-v1.schema.json"
)
CATALOG = ROOT / "resources" / "runtime" / "catalog-v1.json"
FORBIDDEN_FIELD_RE = r"\b(zhou_gong|psychology|llm_generated)\b"


class DreamInterpretationProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DreamInterpretationProvider(ROOT)
        self.samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
        self.rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(
            json.loads(VIEW_SCHEMA.read_text(encoding="utf-8"))
        )

    def test_provider_status_is_local_and_not_catalogued(self) -> None:
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(
            self.rules["provider_status"], "local_provider_not_in_runtime"
        )
        self.assertEqual(self.rules.get("lookup") or {}, {})
        self.assertNotIn("dream-interpretation", CATALOG.read_text(encoding="utf-8"))
        self.assertNotIn("jiemeng", CATALOG.read_text(encoding="utf-8"))
        providers_dir = ROOT / "resources" / "runtime" / "providers"
        self.assertFalse(any(providers_dir.glob("*dream*")))
        self.assertEqual(
            self.provider.provider_id, "mingli-master.dream-interpretation.v1"
        )
        self.assertEqual(
            self.provider.provider_version, "yuqia-ji-zhanmeng-lookup-v1"
        )

    def test_independent_samples_are_fail_closed_unmatched(self) -> None:
        for case_id, case in self.samples["cases"].items():
            with self.subTest(case_id):
                view = self.provider.project(
                    {
                        "schema_version": "dream-interpretation-input/v1",
                        **case["input"],
                    }
                )
                self.validator.validate(view)
                expected = case["expected"]
                self.assertEqual(view["normalized"]["dream_text"], case["input"]["dream_text"])
                self.assertEqual(view["normalized"]["omen_key"], expected["omen_key"])
                self.assertEqual(view["normalized"]["script"], "hanzi")
                self.assertIsNone(view["omen_match"])
                self.assertEqual(view["source_status"], expected["source_status"])
                self.assertEqual(view["source_status"], "unmatched")
                self.assertIsNone(view["hard_verdict"])
                self.assertEqual(expected["match_status"], "unmatched")
                self.assertIsNone(expected["omen_match"])
                if expected.get("source_rule_id"):
                    self.assertEqual(
                        view["source_identity"]["source_rule_id"],
                        expected["source_rule_id"],
                    )
                self.assertEqual(
                    view["source_identity"]["source_pack"], "selection/yuqia-ji"
                )
                dumped = json.dumps(view, ensure_ascii=False)
                self.assertNotRegex(dumped, FORBIDDEN_FIELD_RE)
                self.assertIn(
                    "current yuqia-ji fulltext has no 占梦 omen table",
                    view["source_gaps"],
                )

    def test_empty_lookup_never_upgrades_rain_token(self) -> None:
        view = self.provider.project(
            {
                "schema_version": "dream-interpretation-input/v1",
                "dream_text": "梦见下雨",
                "omen_key": "雨",
            }
        )
        self.validator.validate(view)
        self.assertIsNone(view["omen_match"])
        self.assertEqual(view["source_status"], "unmatched")
        self.assertIsNone(view["hard_verdict"])

    def test_rejects_zhou_gong_and_latin_input(self) -> None:
        with self.assertRaises(ValueError):
            self.provider.project(
                {
                    "schema_version": "dream-interpretation-input/v1",
                    "dream_text": "梦见下雨",
                    "zhou_gong": {"雨": "财"},
                }
            )
        with self.assertRaises(ValueError):
            self.provider.project(
                {
                    "schema_version": "dream-interpretation-input/v1",
                    "dream_text": "I dreamed of rain",
                }
            )


if __name__ == "__main__":
    unittest.main()
