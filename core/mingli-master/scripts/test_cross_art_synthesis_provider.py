#!/usr/bin/env python3
"""Local 合参裁决 Provider. Not in catalog; no hard_verdict or fusion."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from reading_engine.cross_art_synthesis import CrossArtSynthesisProvider


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
RULES = ROOT / "references" / "matrices" / "cross-art-synthesis-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "cross-art-synthesis-samples-v1.yaml"
VIEW_SCHEMA = (
    REPO / "contracts" / "schemas" / "views" / "cross-art-synthesis-view-v1.schema.json"
)
CATALOG = ROOT / "resources" / "runtime" / "catalog-v1.json"
FORBIDDEN_FIELD_RE = r"\b(fused_score|winner|arbitration|weighted_average)\b"


class CrossArtSynthesisProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = CrossArtSynthesisProvider(ROOT)
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
        self.assertNotIn("cross-art-synthesis", CATALOG.read_text(encoding="utf-8"))
        providers_dir = ROOT / "resources" / "runtime" / "providers"
        self.assertFalse(any(providers_dir.glob("*cross-art-synthesis*")))
        self.assertEqual(
            self.provider.provider_id, "mingli-master.cross-art-synthesis.v1"
        )
        self.assertEqual(
            self.provider.provider_version, "retain-disagreement-no-fusion-v1"
        )

    def test_independent_samples_match_adjudicator(self) -> None:
        self.assertGreaterEqual(len(self.samples["cases"]), 4)
        for case_id, case in self.samples["cases"].items():
            with self.subTest(case_id):
                view = self.provider.project(case["input"])
                self.validator.validate(view)
                expected = case["expected"]
                self.assertEqual(view["product_id"], expected["product_id"], case_id)
                self.assertEqual(view["source_status"], expected["source_status"], case_id)
                self.assertEqual(
                    view["source_identity"]["source_rule_id"],
                    expected["source_rule_id"],
                    case_id,
                )
                self.assertEqual(
                    view["evidence_sufficiency"]["status"],
                    expected["evidence_status"],
                    case_id,
                )
                self.assertEqual(
                    view["missing_art_ids"], expected["missing_art_ids"], case_id
                )
                self.assertEqual(view["convergence"], expected["convergence"], case_id)
                self.assertIsNone(view["hard_verdict"], case_id)
                self.assertIs(view["forced_resolution"], False, case_id)
                dumped = json.dumps(view, ensure_ascii=False)
                self.assertNotRegex(dumped, FORBIDDEN_FIELD_RE)
                if "disagreements" in expected:
                    self.assertEqual(
                        view["disagreements"], expected["disagreements"], case_id
                    )
                if expected.get("disagreement_kind"):
                    self.assertTrue(
                        any(
                            row["kind"] == expected["disagreement_kind"]
                            for row in view["disagreements"]
                        ),
                        case_id,
                    )
                if expected["match_status"] == "unmatched":
                    self.assertEqual(view["convergence"], [])
                    self.assertEqual(view["disagreements"], [])
                    self.assertEqual(view["source_status"], "unmatched")

    def test_matching_predicates_are_corroboration_not_fusion(self) -> None:
        view = self.provider.project(
            {
                "product_id": "hecan",
                "selected_art_ids": ["bazi", "ziwei"],
                "dimension_id": "career",
                "present_art_ids": ["bazi", "ziwei"],
                "art_signals": {
                    "bazi": {
                        "predicate_id": "career_direction",
                        "value": "正官可见",
                        "fact_refs": ["fact:profile/calculated/bazi/career"],
                    },
                    "ziwei": {
                        "predicate_id": "career_direction",
                        "value": "正官可见",
                        "fact_refs": ["fact:profile/calculated/ziwei/career"],
                    },
                },
            }
        )
        self.validator.validate(view)
        self.assertEqual(len(view["convergence"]), 1)
        self.assertEqual(view["disagreements"], [])
        self.assertEqual(view["convergence"][0]["kind"], "source_bound_corroboration")
        self.assertIsNone(view["hard_verdict"])
        self.assertIs(view["forced_resolution"], False)
        self.assertNotRegex(json.dumps(view), FORBIDDEN_FIELD_RE)

    def test_missing_art_is_not_invented(self) -> None:
        view = self.provider.project(
            {
                "product_id": "hecan",
                "selected_art_ids": ["bazi", "ziwei", "qizheng"],
                "dimension_id": "career",
                "present_art_ids": ["bazi", "ziwei"],
                "art_signals": {
                    "bazi": {
                        "predicate_id": "career_direction",
                        "value": "正官可见",
                        "fact_refs": ["fact:bazi/career"],
                    },
                    "ziwei": {
                        "predicate_id": "career_direction",
                        "value": "正官可见",
                        "fact_refs": ["fact:ziwei/career"],
                    },
                    "qizheng": {
                        "predicate_id": "career_direction",
                        "value": "发明缺术",
                        "fact_refs": ["fact:qizheng/career"],
                    },
                },
            }
        )
        self.validator.validate(view)
        self.assertEqual(view["missing_art_ids"], ["qizheng"])
        self.assertEqual(view["evidence_sufficiency"]["status"], "partial")
        self.assertNotIn("qizheng", view["present_art_ids"])
        for row in view["convergence"] + view["disagreements"]:
            self.assertNotIn("qizheng", row["arts"])
        self.assertIsNone(view["hard_verdict"])

    def test_insufficient_arts_cannot_corroborate(self) -> None:
        view = self.provider.project(
            {
                "product_id": "wenshi",
                "selected_art_ids": ["liuyao", "qimen", "daliuren"],
                "dimension_id": "outcome",
                "present_art_ids": ["liuyao"],
            }
        )
        self.validator.validate(view)
        self.assertEqual(
            view["evidence_sufficiency"]["status"], "insufficient_for_corroboration"
        )
        self.assertEqual(view["convergence"], [])
        self.assertEqual(view["disagreements"][0]["kind"], "insufficient_arts")
        self.assertIsNone(view["hard_verdict"])
        self.assertIs(view["forced_resolution"], False)

    def test_rejects_fusion_input_fields(self) -> None:
        with self.assertRaises(ValueError):
            self.provider.project(
                {
                    "product_id": "hecan",
                    "selected_art_ids": ["bazi", "ziwei"],
                    "dimension_id": "career",
                    "present_art_ids": ["bazi", "ziwei"],
                    "winner": "bazi",
                }
            )
        with self.assertRaises(ValueError):
            self.provider.project(
                {
                    "product_id": "hecan",
                    "selected_art_ids": ["bazi", "ziwei"],
                    "dimension_id": "career",
                    "present_art_ids": ["bazi", "ziwei"],
                    "fused_score": 0.8,
                }
            )


if __name__ == "__main__":
    unittest.main()
