#!/usr/bin/env python3
"""Contract tests for name-analysis source rules. No Provider is loaded."""

from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "references" / "matrices" / "name-analysis-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "name-analysis-samples-v1.yaml"
INPUT_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "inputs"
    / "name-analysis-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "views"
    / "name-analysis-view-v1.schema.json"
)
FORBIDDEN_OUTPUT_RE = re.compile(
    r"\b(kangxi|wuge|sancai|stroke_count)\b",
    re.I,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TONE_TO_ELEMENT = {
    "宫": "earth",
    "商": "metal",
    "角": "wood",
    "徵": "fire",
    "羽": "water",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _research_fulltext(normalized_path: str) -> Path | None:
    roots: list[Path] = []
    env_root = os.environ.get("MINGLI_RESEARCH_ROOT")
    if env_root:
        roots.append(Path(env_root))
    roots.append(Path.home() / ".codex" / "skills" / "mingli-master")
    for root in roots:
        candidate = root / normalized_path
        if candidate.is_file():
            return candidate
    local = ROOT / normalized_path
    if local.is_file():
        return local
    return None


class NameAnalysisSourceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
        self.samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))

    def test_matrix_declares_contract_only_and_excludes_wuge(self) -> None:
        self.assertEqual(
            self.rules["schema_version"], "mingli-name-analysis-source-rules-v1"
        )
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(self.rules["provider_status"], "contract_only_no_provider")
        excluded = set(self.rules["excluded_methods"])
        self.assertGreaterEqual(
            excluded,
            {
                "kangxi_stroke_count",
                "wuge_sancai_numerology",
                "personality_or_luck_verdict",
            },
        )
        dumped = json.dumps(self.rules, ensure_ascii=False)
        self.assertNotRegex(dumped, r"\bTODO\b|\bTBD\b|placeholder")

    def test_pinned_surnames_match_independent_samples(self) -> None:
        lookup: dict[str, str] = {}
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        cases = self.samples["cases"]
        exact = [
            "name-analysis-zhao-jiao",
            "name-analysis-qian-zhi",
            "name-analysis-sun-gong",
            "name-analysis-wang-shang",
            "name-analysis-wu-yu",
        ]
        for case_id in exact:
            expected = cases[case_id]["expected"]
            key = expected["lookup_key"]
            self.assertEqual(lookup[key], expected["tone"], case_id)
            self.assertEqual(
                TONE_TO_ELEMENT[expected["tone"]], expected["element"], case_id
            )
            self.assertIsNone(expected["hard_verdict"])
        unmatched = cases["name-analysis-unmatched-surname"]["expected"]
        self.assertNotIn(unmatched["lookup_key"], lookup)
        self.assertEqual(unmatched["match_status"], "unmatched")

    def test_source_registry_hash_and_excerpt_when_fulltext_present(self) -> None:
        source = self.rules["source_registry"]["wuxing_jingji_wuyin"]
        self.assertRegex(source["sha256"], SHA256_RE)
        fulltext = _research_fulltext(source["normalized_path"])
        if fulltext is None:
            self.skipTest("local 五行精纪 fulltext is not installed")
        self.assertEqual(_sha256(fulltext), source["sha256"])
        text = fulltext.read_text(encoding="utf-8")
        self.assertIn(source["exact_excerpt"], text)
        for rule in self.rules["rules"]:
            excerpt = rule.get("exact_excerpt")
            if excerpt:
                self.assertIn(excerpt, text, rule["id"])

    def test_input_and_view_schemas_reject_wuge_fields(self) -> None:
        from jsonschema import Draft202012Validator

        input_schema = json.loads(INPUT_SCHEMA.read_text(encoding="utf-8"))
        view_schema = json.loads(VIEW_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(input_schema)
        Draft202012Validator.check_schema(view_schema)
        valid_input = {
            "schema_version": "name-analysis-input/v1",
            "name": "赵青",
            "usage_scene": "unspecified",
            "family_name": "赵",
            "given_name": "青",
            "subject_ref": None,
        }
        Draft202012Validator(input_schema).validate(valid_input)
        self.assertTrue(
            list(Draft202012Validator(input_schema).iter_errors({**valid_input, "wuge": 1}))
        )
        self.assertTrue(
            list(
                Draft202012Validator(input_schema).iter_errors(
                    {**valid_input, "name": "Alex"}
                )
            )
        )
        view = {
            "schema_version": "name-analysis-view/v1",
            "subject_ref": "name:赵青",
            "normalized": {
                "family_name": "赵",
                "given_name": "青",
                "graphemes": ["赵", "青"],
                "script": "hanzi",
            },
            "surname_wuyin": {
                "grapheme": "赵",
                "lookup_key": "趙",
                "tone": "角",
                "element": "wood",
                "match_status": "exact",
                "source_rule_id": "name-analysis/wuxing-jingji#NA-WX-02",
            },
            "given_name_wuyin": None,
            "seasonal_markers": {
                "status": "identity_only",
                "wang_branches": ["寅", "卯"],
                "de_branches": ["戌", "亥"],
                "hard_verdict": None,
                "source_rule_id": "name-analysis/wuxing-jingji#NA-WX-01b",
                "boundary": "markers only; no 贵盛 conclusion",
            },
            "source_identity": {
                "source_pack": "luming-nayin/wuxing-jingji",
                "source_dependency_id": "name-analysis.wuyin-xingshi",
                "source_rule_id": "name-analysis/wuxing-jingji#NA-WX-02",
                "source_anchor": "fulltext.md#L2961",
            },
            "active_source_rule_ids": [
                "name-analysis/wuxing-jingji#NA-WX-01",
                "name-analysis/wuxing-jingji#NA-WX-02",
            ],
            "source_dependency_ids": ["name-analysis.wuyin-xingshi"],
            "source_status": "exact_rule_bound",
            "source_gaps": ["given-name 五音 table is not in v1"],
            "limitations": [
                "v1 只输出姓氏五音身份，不输出康熙笔画、五格或吉凶。",
            ],
            "hard_verdict": None,
        }
        Draft202012Validator(view_schema).validate(view)
        self.assertTrue(
            list(
                Draft202012Validator(view_schema).iter_errors(
                    {**view, "hard_verdict": "吉"}
                )
            )
        )
        self.assertTrue(
            list(
                Draft202012Validator(view_schema).iter_errors(
                    {**view, "stroke_count": 14}
                )
            )
        )
        self.assertIsNone(
            FORBIDDEN_OUTPUT_RE.search(json.dumps(view, ensure_ascii=False))
        )


if __name__ == "__main__":
    unittest.main()
