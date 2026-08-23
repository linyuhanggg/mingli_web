#!/usr/bin/env python3
"""Contract tests for physiognomy-palm source rules. Catalog remains unbound."""

from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "references" / "matrices" / "physiognomy-palm-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "physiognomy-palm-samples-v1.yaml"
INPUT_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "inputs"
    / "physiognomy-palm-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "views"
    / "physiognomy-palm-view-v1.schema.json"
)
FORBIDDEN_OUTPUT_RE = re.compile(
    r"\b(life_line|head_line|heart_line|fate_line|zhou_gong)\b",
    re.I,
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


class PhysiognomyPalmSourceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
        self.samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))

    def test_matrix_excludes_western_lines_and_stays_off_runtime(self) -> None:
        self.assertEqual(
            self.rules["schema_version"], "mingli-physiognomy-palm-source-rules-v1"
        )
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(
            self.rules["provider_status"], "local_provider_not_in_runtime"
        )
        excluded = set(self.rules["excluded_methods"])
        self.assertGreaterEqual(
            excluded,
            {
                "western_palmistry_life_head_heart_fate_lines",
                "mayi_modern_appendix_face_palm_twelve_palaces",
                "posture_observation",
                "combined_face_palm_posture",
                "health_lifespan_wealth_personality_verdict",
            },
        )
        dumped = json.dumps(self.rules, ensure_ascii=False)
        self.assertNotRegex(dumped, r"\bTODO\b|\bTBD\b|placeholder")
        lookup: dict[str, str] = dict(self.rules.get("lookup") or {})
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        self.assertEqual(lookup, {})
        providers = ROOT / "resources" / "runtime" / "providers"
        self.assertFalse(any(providers.glob("*palm*")))
        catalog = ROOT / "resources" / "runtime" / "catalog-v1.json"
        self.assertNotIn("physiognomy-palm", catalog.read_text(encoding="utf-8"))

    def test_samples_keep_empty_luck_lookup(self) -> None:
        lookup: dict[str, str] = dict(self.rules.get("lookup") or {})
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        terminology = self.rules["terminology_regions"]
        self.assertEqual(lookup, {})
        for case_id, case in self.samples["cases"].items():
            expected = case["expected"]
            self.assertIsNone(expected["hard_verdict"], case_id)
            self.assertEqual(expected["mode"], "palm", case_id)
            key = expected.get("lookup_key")
            if expected["match_status"] == "exact":
                self.assertIn(key, terminology, case_id)
            else:
                self.assertNotIn(key, terminology, case_id)
                self.assertIsNone(expected.get("region_match"))

    def test_source_registry_hash_and_excerpt_when_fulltext_present(self) -> None:
        source = self.rules["source_registry"]["mayi_limbs_handback"]
        self.assertRegex(source["sha256"], SHA256_RE)
        fulltext = _research_fulltext(source["normalized_path"])
        if fulltext is None:
            self.skipTest("local 麻衣神相 fulltext is not installed")
        self.assertEqual(_sha256(fulltext), source["sha256"])
        text = fulltext.read_text(encoding="utf-8")
        self.assertIn(source["exact_excerpt"], text)
        for rule in self.rules["rules"]:
            if rule["primary_sources"][0]["title"] != "麻衣神相":
                continue
            excerpt = rule.get("exact_excerpt")
            if excerpt:
                self.assertIn(excerpt, text, rule["id"])

    def test_input_and_view_schemas_reject_verdict_fields(self) -> None:
        from jsonschema import Draft202012Validator

        input_schema = json.loads(INPUT_SCHEMA.read_text(encoding="utf-8"))
        view_schema = json.loads(VIEW_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(input_schema)
        Draft202012Validator.check_schema(view_schema)
        valid_input = {
            "schema_version": "physiognomy-palm-input/v1",
            "mode": "palm",
            "observations": [
                {
                    "region_id": "hand_back",
                    "descriptor": "pattern_visible",
                    "visibility": "partial",
                    "uncertainty": 0.2,
                }
            ],
            "region_label": "手背纹",
            "subject_ref": None,
        }
        Draft202012Validator(input_schema).validate(valid_input)
        self.assertTrue(
            list(
                Draft202012Validator(input_schema).iter_errors(
                    {**valid_input, "life_line": 1}
                )
            )
        )
        self.assertTrue(
            list(
                Draft202012Validator(input_schema).iter_errors(
                    {**valid_input, "mode": "posture"}
                )
            )
        )
        view = {
            "schema_version": "physiognomy-palm-view/v1",
            "subject_ref": "sid-0123456789abcdef0123456789abcdef",
            "mode": "palm",
            "normalized": {
                "mode": "palm",
                "taxonomy": "anatomical_palm_classical_v1",
                "region_ids": ["hand_back"],
                "region_label": "手背纹",
            },
            "region_match": {
                "region_id": "hand_back",
                "lookup_key": "手背纹",
                "match_status": "exact",
                "source_rule_id": "physiognomy-palm/mayi-shenxiang#PP-MY-02",
                "source_excerpt": "手背之纹其验尚矣，故有人知之理",
            },
            "source_identity": {
                "source_pack": "physiognomy/mayi-shenxiang",
                "source_dependency_id": "physiognomy.palm-limbs-handback",
                "source_rule_id": "physiognomy-palm/mayi-shenxiang#PP-MY-02",
                "source_anchor": "fulltext.md#L1613",
            },
            "active_source_rule_ids": [
                "physiognomy-palm/mayi-shenxiang#PP-MY-02"
            ],
            "source_dependency_ids": ["physiognomy.palm-limbs-handback"],
            "source_status": "exact_rule_bound",
            "source_gaps": [
                "western palmistry lines are not sourced in v1",
            ],
            "limitations": [
                "v1 只输出手足/掌/五指/手背术语身份，不输出吉凶。",
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
                    {**view, "life_line": "continuous"}
                )
            )
        )
        self.assertIsNone(
            FORBIDDEN_OUTPUT_RE.search(json.dumps(view, ensure_ascii=False))
        )


if __name__ == "__main__":
    unittest.main()
