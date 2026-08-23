#!/usr/bin/env python3
"""Contract tests for cross-art synthesis source rules. Catalog remains unbound."""

from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "references" / "matrices" / "cross-art-synthesis-source-rules-v1.yaml"
SAMPLES = ROOT / "references" / "fixtures" / "cross-art-synthesis-samples-v1.yaml"
VIEW_SCHEMA = (
    ROOT.parents[1]
    / "contracts"
    / "schemas"
    / "views"
    / "cross-art-synthesis-view-v1.schema.json"
)
FORBIDDEN_OUTPUT_RE = re.compile(
    r"\b(fused_score|winner|arbitration|weighted_average)\b",
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


class CrossArtSynthesisSourceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
        self.samples = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))

    def test_matrix_excludes_fusion_and_stays_off_runtime(self) -> None:
        self.assertEqual(
            self.rules["schema_version"], "mingli-cross-art-synthesis-source-rules-v1"
        )
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(
            self.rules["provider_status"], "local_provider_not_in_runtime"
        )
        excluded = set(self.rules["excluded_methods"])
        self.assertGreaterEqual(
            excluded,
            {
                "averaged_luck_verdict",
                "weighted_score_fusion",
                "silent_winner_selection",
                "inventing_missing_arts",
                "dimension_fact_scope_as_convergence",
                "provider_scope_name_as_disagreement",
                "bushi_one_principle_as_fusion",
            },
        )
        dumped = json.dumps(self.rules, ensure_ascii=False)
        self.assertNotRegex(dumped, r"\bTODO\b|\bTBD\b|placeholder")
        lookup: dict[str, str] = dict(self.rules.get("lookup") or {})
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        self.assertEqual(lookup, {})
        providers = ROOT / "resources" / "runtime" / "providers"
        self.assertFalse(any(providers.glob("*cross-art-synthesis*")))
        catalog = ROOT / "resources" / "runtime" / "catalog-v1.json"
        self.assertNotIn("cross-art-synthesis", catalog.read_text(encoding="utf-8"))

    def test_samples_keep_empty_luck_lookup(self) -> None:
        lookup: dict[str, str] = dict(self.rules.get("lookup") or {})
        for rule in self.rules["rules"]:
            lookup.update(rule.get("lookup") or {})
        self.assertEqual(lookup, {})
        for case_id, case in self.samples["cases"].items():
            expected = case["expected"]
            self.assertIsNone(expected["hard_verdict"], case_id)
            self.assertIs(expected["forced_resolution"], False, case_id)
            self.assertEqual(expected["convergence"], [], case_id)
            if expected["match_status"] == "unmatched":
                self.assertIsNone(expected.get("region_match"))
                self.assertNotIn(expected.get("lookup_key"), lookup)

    def test_source_registry_hash_and_excerpt_when_fulltext_present(self) -> None:
        for key, title in (
            ("guotian_no_one_end", "果老星宗"),
            ("ziwei_star_setup", "紫微斗数全书"),
            ("huozhu_six_relatives", "火珠林"),
            ("bushi_one_principle", "卜筮正宗"),
        ):
            source = self.rules["source_registry"][key]
            self.assertEqual(source["title"], title)
            self.assertRegex(source["sha256"], SHA256_RE)
            fulltext = _research_fulltext(source["normalized_path"])
            if fulltext is None:
                self.skipTest(f"local {title} fulltext is not installed")
            self.assertEqual(_sha256(fulltext), source["sha256"])
            text = fulltext.read_text(encoding="utf-8")
            self.assertIn(source["exact_excerpt"], text)
            for rule in self.rules["rules"]:
                if rule["primary_sources"][0]["title"] != title:
                    continue
                excerpt = rule.get("exact_excerpt")
                if excerpt:
                    self.assertIn(excerpt, text, rule["id"])

    def test_view_schema_rejects_verdict_fields(self) -> None:
        from jsonschema import Draft202012Validator

        view_schema = json.loads(VIEW_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(view_schema)
        view = {
            "schema_version": "cross-art-synthesis-view/v1",
            "product_id": "hecan",
            "subject_ref": "sid-0123456789abcdef0123456789abcdef",
            "dimension_id": "career",
            "selected_art_ids": ["bazi", "ziwei"],
            "present_art_ids": ["bazi", "ziwei"],
            "missing_art_ids": [],
            "convergence": [],
            "disagreements": [
                {
                    "arts": ["bazi", "ziwei"],
                    "kind": "source_disagreement_retained",
                    "display_text": "两术对事业方向的来源谓词不一致，分歧保留",
                    "fact_refs": ["fact:profile/calculated/bazi/career"],
                    "source_rule_id": "cross-art-synthesis/guotian-jing#CAS-GX-01",
                }
            ],
            "evidence_sufficiency": {
                "present_count": 2,
                "missing_art_ids": [],
                "status": "all_selected_present",
            },
            "source_identity": {
                "source_pack": "xingming/guotian-jing",
                "source_dependency_id": "cross-art.retain-disagreement",
                "source_rule_id": "cross-art-synthesis/guotian-jing#CAS-GX-01",
                "source_anchor": "fulltext.md#L1530",
            },
            "active_source_rule_ids": [
                "cross-art-synthesis/guotian-jing#CAS-GX-01"
            ],
            "source_dependency_ids": ["cross-art.retain-disagreement"],
            "source_status": "exact_rule_bound",
            "source_gaps": [
                "dimension_fact_scope is not 互证",
            ],
            "limitations": [
                "v1 只钉比较行合同，不写裁决算法。",
            ],
            "forced_resolution": False,
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
                    {**view, "fused_score": 0.8}
                )
            )
        )
        self.assertTrue(
            list(
                Draft202012Validator(view_schema).iter_errors(
                    {**view, "forced_resolution": True}
                )
            )
        )
        self.assertIsNone(
            FORBIDDEN_OUTPUT_RE.search(json.dumps(view, ensure_ascii=False))
        )


if __name__ == "__main__":
    unittest.main()
