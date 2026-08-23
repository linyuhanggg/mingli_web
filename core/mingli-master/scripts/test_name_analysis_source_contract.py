#!/usr/bin/env python3
"""Contract tests for name-analysis source rules. Catalog remains unbound."""

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

    def test_matrix_excludes_wuge_and_stays_off_runtime(self) -> None:
        self.assertEqual(
            self.rules["schema_version"], "mingli-name-analysis-source-rules-v1"
        )
        self.assertEqual(self.rules["runtime_binding"], "not_in_runtime")
        self.assertEqual(
            self.rules["provider_status"], "local_provider_not_in_runtime"
        )
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
            case_id
            for case_id, case in cases.items()
            if case["expected"].get("match_status") == "exact"
        ]
        self.assertGreaterEqual(len(exact), 10)
        for case_id in exact:
            expected = cases[case_id]["expected"]
            key = expected["lookup_key"]
            self.assertEqual(lookup[key], expected["tone"], case_id)
            self.assertEqual(
                TONE_TO_ELEMENT[expected["tone"]], expected["element"], case_id
            )
            self.assertIsNone(expected["hard_verdict"])
        for case_id, case in cases.items():
            expected = case["expected"]
            if expected.get("match_status") != "unmatched":
                continue
            self.assertNotIn(expected["lookup_key"], lookup, case_id)
            self.assertEqual(expected["match_status"], "unmatched")

    def test_lookup_has_no_cross_table_surname(self) -> None:
        by_tone: dict[str, set[str]] = {}
        for rule in self.rules["rules"]:
            mapping = rule.get("lookup") or {}
            if not mapping:
                continue
            tone = rule["tone"]
            by_tone.setdefault(tone, set()).update(mapping)
        seen: dict[str, str] = {}
        for tone, names in by_tone.items():
            for name in names:
                self.assertNotIn(name, seen, f"{name} in {seen.get(name)} and {tone}")
                seen[name] = tone
        self.assertNotIn("曲", seen)
        self.assertNotIn("熊", seen)
        self.assertGreaterEqual(len(seen), 80)
        conflicts = self.rules.get("cross_table_unmatched") or []
        self.assertGreaterEqual(len(conflicts), 8)
        for row in conflicts:
            surname = row["surname"]
            self.assertNotIn(surname, seen, surname)
            self.assertGreaterEqual(len(row.get("tables") or []), 2, surname)

        compounds = self.rules.get("compound_surnames") or {}
        self.assertEqual(set(compounds), {"角", "徵", "宫", "商", "羽"})
        for tone, names in compounds.items():
            self.assertTrue(names, tone)
            for name in names:
                self.assertGreaterEqual(len(name), 2, name)
                self.assertIn(name, seen, f"{name} missing from lookup")
                self.assertEqual(seen[name], tone, name)

        cases = self.samples["cases"]
        self.assertEqual(cases["name-analysis-tantai-jiao"]["expected"]["tone"], "角")
        self.assertEqual(cases["name-analysis-zhuge-zhi"]["expected"]["tone"], "徵")
        self.assertEqual(cases["name-analysis-shuiqiu-gong"]["expected"]["tone"], "宫")
        self.assertEqual(cases["name-analysis-linghu-shang"]["expected"]["tone"], "商")
        self.assertEqual(cases["name-analysis-huangfu-yu"]["expected"]["tone"], "羽")
        self.assertNotIn("端木", seen)
        self.assertEqual(
            cases["name-analysis-conflict-duanmu"]["expected"]["match_status"],
            "unmatched",
        )
        yiyun = self.rules.get("yiyun_bieyin_unmatched") or []
        self.assertGreaterEqual(len(yiyun), 8)
        for row in yiyun:
            surname = row["surname"]
            self.assertNotIn(surname, seen, surname)
        self.assertEqual(
            cases["name-analysis-yiyun-diwu"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-yiyun-xiahou"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-yiyun-nanmen"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertNotIn("第五", seen)
        self.assertNotIn("南门", seen)
        self.assertNotIn("南門", seen)
        self.assertNotIn("夏侯", seen)
        ocr = self.rules.get("ocr_fragment_unmatched") or []
        self.assertGreaterEqual(len(ocr), 8)
        for row in ocr:
            surname = row["surname"]
            self.assertNotIn(surname, seen, surname)
        self.assertEqual(
            cases["name-analysis-ocr-nanguan"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-ocr-ping"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-ocr-xianyu"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertNotIn("南官", seen)
        self.assertNotIn("平", seen)
        self.assertNotIn("鮮于", seen)
        self.assertNotIn("鲜于", seen)
        self.assertNotIn("鲜干", seen)
        dup = self.rules.get("zhengyin_duplicate_paste_unmatched") or []
        self.assertGreaterEqual(len(dup), 8)
        for row in dup:
            surname = row["surname"]
            self.assertNotIn(surname, seen, surname)
        self.assertEqual(
            cases["name-analysis-dup-chen"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-dup-zeng"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-dup-shi"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertNotIn("陳", seen)
        self.assertNotIn("陈", seen)
        self.assertNotIn("曾", seen)
        self.assertNotIn("史", seen)
        self.assertNotIn("宰", seen)
        self.assertNotIn("時", seen)
        self.assertNotIn("興", seen)
        gong_dup = self.rules.get("gongyin_duplicate_paste_unmatched") or []
        self.assertGreaterEqual(len(gong_dup), 8)
        for row in gong_dup:
            surname = row["surname"]
            self.assertNotIn(surname, seen, surname)
        self.assertEqual(
            cases["name-analysis-dup-cen"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-dup-ji"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertEqual(
            cases["name-analysis-dup-niu"]["expected"]["match_status"],
            "unmatched",
        )
        self.assertNotIn("岑", seen)
        self.assertNotIn("冀", seen)
        self.assertNotIn("隆", seen)
        self.assertNotIn("景", seen)
        self.assertNotIn("牛", seen)
        self.assertNotIn("也", seen)
        self.assertNotIn("奄", seen)
        self.assertNotIn("公", seen)

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
        self.assertIn("澹台大山", text)
        self.assertIn("諸葛瑯琊", text)
        self.assertIn("水丘吳興", text)
        self.assertIn("令狐太原", text)
        self.assertIn("皇甫（京兆）", text)
        self.assertIn("端木兰陵", text)
        self.assertIn("端木（鲁国）", text)
        self.assertIn("曲陳留", text)
        self.assertIn("曲臨海", text)
        self.assertIn("一雲商音", text)
        self.assertIn("第五陝西", text)
        self.assertIn("南門河南", text)
        self.assertIn("一云汾王", text)
        self.assertIn("夏侯谯国", text)
        self.assertIn("一雲上谷", text)
        self.assertIn("尉遲太原", text)
        self.assertIn("平風氣", text)
        self.assertIn("南官中吳", text)
        self.assertIn("次第京兆", text)
        self.assertIn("薛門東", text)
        self.assertIn("天花陝西", text)
        self.assertIn("問弓太原", text)
        self.assertIn("鲜干太原", text)
        self.assertIn("宰西河曾魯國勐鹹陽陳穎川", text)
        self.assertIn("陳穎川史穎兆時隴西興", text)
        self.assertIn("岑南陽熊豫章冀渤海隆南陽景晉陽", text)
        self.assertIn("天水牛陳曲吳興", text)

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
