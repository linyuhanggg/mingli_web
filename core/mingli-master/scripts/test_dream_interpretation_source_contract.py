#!/usr/bin/env python3
"""Contract tests for dream-interpretation source rules. Catalog remains unbound."""

from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "references" / "matrices" / "dream-interpretation-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "dream-interpretation-samples-v1.yaml"
INPUT_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "inputs"
    / "dream-interpretation-input-v1.schema.json"
)
VIEW_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "views"
    / "dream-interpretation-view-v1.schema.json"
)
FORBIDDEN_OUTPUT_RE = re.compile(
    r"\b(zhou_gong|psychology|llm_generated)\b",
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


class DreamInterpretationSourceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
        self.samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))

    def test_matrix_excludes_zhou_gong_and_stays_off_runtime(self) -> None:
        self.assertEqual(
            self.rules["schema_version"], "mingli-dream-interpretation-source-rules-v1"
        )
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(
            self.rules["provider_status"], "local_provider_not_in_runtime"
        )
        excluded = set(self.rules["excluded_methods"])
        self.assertGreaterEqual(
            excluded,
            {
                "zhou_gong_web_dictionary",
                "llm_generated_interpretation",
                "psychology_dreamwork",
                "liuyao_tengshe_mengmei_without_board",
                "daliuren_leixiang_mengxiang_without_board",
            },
        )
        dumped = json.dumps(self.rules, ensure_ascii=False)
        self.assertNotRegex(dumped, r"\bTODO\b|\bTBD\b|placeholder")
        lookup: dict[str, str] = dict(self.rules.get("lookup") or {})
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        self.assertEqual(lookup, {})
        providers = ROOT / "resources" / "runtime" / "providers"
        self.assertFalse(any(providers.glob("*dream*")))
        catalog = ROOT / "resources" / "runtime" / "catalog-v1.json"
        self.assertNotIn("dream-interpretation", catalog.read_text(encoding="utf-8"))

    def test_samples_are_unmatched_against_empty_lookup(self) -> None:
        lookup: dict[str, str] = dict(self.rules.get("lookup") or {})
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        cases = self.samples["cases"]
        for case_id, case in cases.items():
            expected = case["expected"]
            self.assertIsNone(expected["hard_verdict"], case_id)
            self.assertEqual(expected["match_status"], "unmatched", case_id)
            self.assertIsNone(expected["omen_match"], case_id)
            key = expected.get("lookup_key")
            if key:
                self.assertNotIn(key, lookup, case_id)

    def test_source_registry_hash_and_excerpt_when_fulltext_present(self) -> None:
        source = self.rules["source_registry"]["yuqia_ji_zhanmeng"]
        self.assertRegex(source["sha256"], SHA256_RE)
        fulltext = _research_fulltext(source["normalized_path"])
        if fulltext is None:
            self.skipTest("local 玉匣记 fulltext is not installed")
        self.assertEqual(_sha256(fulltext), source["sha256"])
        text = fulltext.read_text(encoding="utf-8")
        self.assertIn(source["exact_excerpt"], text)
        self.assertNotIn("梦见", text)
        self.assertNotIn("夢見", text)
        for rule in self.rules["rules"]:
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
            "schema_version": "dream-interpretation-input/v1",
            "dream_text": "梦见下雨",
            "background": None,
            "omen_key": "雨",
            "subject_ref": None,
        }
        Draft202012Validator(input_schema).validate(valid_input)
        self.assertTrue(
            list(
                Draft202012Validator(input_schema).iter_errors(
                    {**valid_input, "zhou_gong": 1}
                )
            )
        )
        self.assertTrue(
            list(
                Draft202012Validator(input_schema).iter_errors(
                    {**valid_input, "dream_text": "rain"}
                )
            )
        )
        view = {
            "schema_version": "dream-interpretation-view/v1",
            "subject_ref": "dream:雨",
            "normalized": {
                "dream_text": "梦见下雨",
                "omen_key": "雨",
                "script": "hanzi",
            },
            "omen_match": None,
            "source_identity": {
                "source_pack": "selection/yuqia-ji",
                "source_dependency_id": "dream.yuqia-zhanmeng",
                "source_rule_id": "dream-interpretation/yuqia-ji#DI-YQ-03",
                "source_anchor": "fulltext.md#L12",
            },
            "active_source_rule_ids": [
                "dream-interpretation/yuqia-ji#DI-YQ-01",
                "dream-interpretation/yuqia-ji#DI-YQ-02",
                "dream-interpretation/yuqia-ji#DI-YQ-03",
            ],
            "source_dependency_ids": ["dream.yuqia-zhanmeng"],
            "source_status": "unmatched",
            "source_gaps": ["current yuqia-ji fulltext has no 占梦 omen table"],
            "limitations": [
                "v1 只做玉匣记占梦查找；当前版本查找表为空，不输出周公网典、模型文案或吉凶。",
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
                    {**view, "interpretation": "必有财"}
                )
            )
        )
        self.assertIsNone(
            FORBIDDEN_OUTPUT_RE.search(json.dumps(view, ensure_ascii=False))
        )


if __name__ == "__main__":
    unittest.main()
