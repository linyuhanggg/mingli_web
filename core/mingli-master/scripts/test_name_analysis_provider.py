#!/usr/bin/env python3
"""Surname 五音 lookup Provider against frozen samples. Not in catalog."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from reading_engine.name_analysis import NameAnalysisProvider


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
RULES = ROOT / "references" / "matrices" / "name-analysis-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "name-analysis-samples-v1.yaml"
VIEW_SCHEMA = REPO / "contracts" / "schemas" / "views" / "name-analysis-view-v1.schema.json"
CATALOG = ROOT / "resources" / "runtime" / "catalog-v1.json"
FORBIDDEN_FIELD_RE = r"\b(kangxi|wuge|sancai|stroke_count)\b"


class NameAnalysisProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = NameAnalysisProvider(ROOT)
        self.samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
        self.rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
        self.view_schema = json.loads(VIEW_SCHEMA.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.view_schema)

    def test_provider_status_is_local_and_not_catalogued(self) -> None:
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(
            self.rules["provider_status"], "local_provider_not_in_runtime"
        )
        self.assertNotIn("name-analysis", CATALOG.read_text(encoding="utf-8"))
        providers_dir = ROOT / "resources" / "runtime" / "providers"
        self.assertFalse(any(providers_dir.glob("*name-analysis*")))
        self.assertEqual(
            self.provider.provider_id, "mingli-master.name-analysis.v1"
        )
        self.assertEqual(
            self.provider.provider_version,
            "wuyin-xingshi-from-wuxing-jingji-v1",
        )

    def test_pinned_surnames_match_independent_samples(self) -> None:
        exact = [
            case_id
            for case_id, case in self.samples["cases"].items()
            if case["expected"].get("match_status") == "exact"
        ]
        self.assertGreaterEqual(len(exact), 10)
        for case_id in exact:
            case = self.samples["cases"][case_id]
            view = self.provider.project(
                {
                    "schema_version": "name-analysis-input/v1",
                    **case["input"],
                }
            )
            self.validator.validate(view)
            expected = case["expected"]
            wuyin = view["surname_wuyin"]
            self.assertEqual(view["normalized"]["family_name"], expected["family_name"])
            self.assertEqual(wuyin["lookup_key"], expected["lookup_key"])
            self.assertEqual(wuyin["tone"], expected["tone"])
            self.assertEqual(wuyin["element"], expected["element"])
            self.assertEqual(wuyin["match_status"], expected["match_status"])
            self.assertEqual(wuyin["source_rule_id"], expected["source_rule_id"])
            self.assertIsNone(view["given_name_wuyin"])
            self.assertIsNone(view["hard_verdict"])
            self.assertEqual(view["seasonal_markers"]["hard_verdict"], None)
            self.assertEqual(view["seasonal_markers"]["status"], "identity_only")
            self.assertEqual(view["source_status"], "exact_rule_bound")
            dumped = json.dumps(view, ensure_ascii=False)
            self.assertNotRegex(dumped, FORBIDDEN_FIELD_RE)
            self.assertNotIn('"wuge"', dumped)
            self.assertNotIn('"kangxi"', dumped)
            if "source_gaps" in expected:
                for gap in expected["source_gaps"]:
                    self.assertIn(gap, view["source_gaps"])

    def test_unmatched_surname_is_fail_closed(self) -> None:
        unmatched = [
            case_id
            for case_id, case in self.samples["cases"].items()
            if case["expected"].get("match_status") == "unmatched"
        ]
        self.assertIn("name-analysis-unmatched-surname", unmatched)
        self.assertIn("name-analysis-conflict-qu", unmatched)
        self.assertIn("name-analysis-conflict-xiong", unmatched)
        self.assertIn("name-analysis-conflict-duanmu", unmatched)
        self.assertIn("name-analysis-yiyun-diwu", unmatched)
        self.assertIn("name-analysis-yiyun-xiahou", unmatched)
        self.assertIn("name-analysis-yiyun-nanmen", unmatched)
        self.assertIn("name-analysis-ocr-nanguan", unmatched)
        self.assertIn("name-analysis-ocr-ping", unmatched)
        self.assertIn("name-analysis-ocr-xianyu", unmatched)
        self.assertIn("name-analysis-dup-chen", unmatched)
        self.assertIn("name-analysis-dup-zeng", unmatched)
        self.assertIn("name-analysis-dup-shi", unmatched)
        self.assertIn("name-analysis-dup-cen", unmatched)
        self.assertIn("name-analysis-dup-ji", unmatched)
        self.assertIn("name-analysis-dup-niu", unmatched)
        for case_id in unmatched:
            case = self.samples["cases"][case_id]
            view = self.provider.project(
                {
                    "schema_version": "name-analysis-input/v1",
                    **case["input"],
                }
            )
            self.validator.validate(view)
            expected = case["expected"]
            wuyin = view["surname_wuyin"]
            self.assertEqual(wuyin["lookup_key"], expected["lookup_key"], case_id)
            self.assertIsNone(wuyin["tone"], case_id)
            self.assertIsNone(wuyin["element"], case_id)
            self.assertEqual(wuyin["match_status"], "unmatched", case_id)
            self.assertEqual(view["source_status"], "unmatched", case_id)
            self.assertIsNone(view["seasonal_markers"], case_id)
            self.assertIsNone(view["given_name_wuyin"], case_id)
            self.assertIsNone(view["hard_verdict"], case_id)

    def test_explicit_family_and_given_name_split(self) -> None:
        view = self.provider.project(
            {
                "schema_version": "name-analysis-input/v1",
                "name": "赵青",
                "family_name": "赵",
                "given_name": "青",
                "usage_scene": "unspecified",
            }
        )
        self.validator.validate(view)
        self.assertEqual(view["normalized"]["graphemes"], ["赵", "青"])
        self.assertEqual(view["surname_wuyin"]["grapheme"], "赵")
        self.assertEqual(view["surname_wuyin"]["tone"], "角")

    def test_rejects_wuge_and_latin_input(self) -> None:
        with self.assertRaises(ValueError):
            self.provider.project(
                {
                    "schema_version": "name-analysis-input/v1",
                    "name": "赵青",
                    "usage_scene": "unspecified",
                    "wuge": {"天格": 1},
                }
            )
        with self.assertRaises(ValueError):
            self.provider.project(
                {
                    "schema_version": "name-analysis-input/v1",
                    "name": "Alex",
                    "usage_scene": "unspecified",
                }
            )


if __name__ == "__main__":
    unittest.main()
