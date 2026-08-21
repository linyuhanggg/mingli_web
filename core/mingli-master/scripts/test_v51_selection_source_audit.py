#!/usr/bin/env python3
"""Pre-implementation source and dependency audit for deterministic Selection."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import audit_selection_provider
import audit_test_session
import build_selection_formula_fixtures
from reading_engine.evidence_rules import production_evidence_rules


ROOT = Path(__file__).resolve().parents[1]
SOURCE_TABLE = ROOT / "references/matrices/selection-source-tables-v1.yaml"
FIXTURE = ROOT / "references/fixtures/selection-v51.yaml"
MATRIX = ROOT / "references/matrices/algorithm-source-dependencies.yaml"
PROVENANCE = ROOT / "vendor/cnlunar-0.2.4/PROVENANCE.json"
LICENSE = ROOT / "vendor/cnlunar-0.2.4/LICENSE"
REQUIREMENTS = ROOT / "requirements.txt"
RESEARCH_ROOT = (
    Path(
        os.environ.get(
            "MINGLI_RESEARCH_ROOT",
            ROOT / "__missing_external_research__",
        )
    ).resolve()
    / "references/fulltext/selection"
)
SOURCE_TABLE_SHA256 = "3a32f9fe65b0ecb8b1285ef4578e5492cff9be622d44424c89bddd2346a93ec6"
CLASSICAL_BINDINGS_SHA256 = (
    "73c5a8a5d2041e7d49f838c70d0ca184fee060fd355a8f29b0fd6f9a0a7abc8d"
)
FIXTURE_SHA256 = "ec2ac7599b18b9ea8ad8762e8b7214aad0e7a402a3f9eaac1bf4f3a09bb18686"
EXTERNAL_CASES_SHA256 = "a9c8e8f227630b71008b9f9647b39b36a32c782041f1d0a29d414abe406270b1"
PUBLISHED_CASES_SHA256 = "de6a215b3ce0b01392efe00fed2ca826f5c5614528efa503b868dedff052f0f3"
FORMULA_CASES_SHA256 = "fcf1158ed93826f73b9caa6e5d5a3589ba74a03fdb3d88d34e358688b1d1edf4"
REQUIRED_DEPENDENCIES = {
    "selection.candidate-calendar-foundation",
    "selection.day-facts.jianchu-mansions-gods",
    "selection.hour-facts.ganzhi-and-twelve-gods",
    "selection.event-rules-and-lineage-conflicts",
    "selection.runtime.cnlunar-official-tables",
    "selection.source-conditioned-patterns",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class SelectionSourceAuditTests(unittest.TestCase):
    def test_source_and_fixture_artifacts_are_hash_bound(self) -> None:
        self.assertEqual(_sha256(SOURCE_TABLE), SOURCE_TABLE_SHA256)
        self.assertEqual(_sha256(FIXTURE), FIXTURE_SHA256)

    def test_primary_sources_retain_exact_formula_anchors(self) -> None:
        sources = {
            "xieji-bianfang-shu/fulltext.md": (
                "正月建寅則寅日起建順行十二辰是也",
                "月破者月建所衝之日也",
                "黄黒二道者黄道六黑道六共十有二以配十有二辰",
            ),
            "xingli-kaoyuan/fulltext.md": (
                "一元甲子日起虚",
                "二十八宿直日所屬七曜及異名",
                "旬中空亡者甲子旬中戌亥空",
            ),
            "yuqia-ji/fulltext.md": (
                "二十八宿",
                "彭祖百忌",
            ),
            "donggong-zeri/fulltext.md": (
                "既已擇日，還宜擇時",
                "下詳列各月每日之吉凶",
            ),
        }
        for relative, excerpts in sources.items():
            text = (RESEARCH_ROOT / relative).read_text(encoding="utf-8")
            for excerpt in excerpts:
                with self.subTest(source=relative, excerpt=excerpt):
                    self.assertIn(excerpt, text)

    def test_algorithm_matrix_declares_every_selection_dependency(self) -> None:
        profile = _load(MATRIX)["providers"]["selection"]
        self.assertEqual(profile["source_audit_status"], "source_verified")
        self.assertEqual(
            {row["id"] for row in profile["dependencies"]},
            REQUIRED_DEPENDENCIES,
        )
        for row in profile["dependencies"]:
            self.assertEqual(row["status"], "verified")
            if row["id"] == "selection.source-conditioned-patterns":
                self.assertEqual(
                    row["source_artifact"],
                    {
                        "path": "references/matrices/classical-evidence-bindings-v1.json",
                        "schema_version": "mingli-classical-evidence-bindings-v1",
                        "sha256": CLASSICAL_BINDINGS_SHA256,
                    },
                )
                continue
            self.assertEqual(
                row["source_artifact"],
                {
                    "path": "references/matrices/selection-source-tables-v1.yaml",
                    "schema_version": "mingli-selection-source-tables-v1",
                    "sha256": SOURCE_TABLE_SHA256,
                },
            )

    def test_selected_tables_are_complete_and_versioned(self) -> None:
        table = _load(SOURCE_TABLE)
        self.assertEqual(table["schema_version"], "mingli-selection-source-tables-v1")
        self.assertEqual(table["version"], "1.2.1")
        self.assertEqual(table["selected_profile"]["id"], "xieji-official-cnlunar-v1")
        self.assertEqual(len(table["jianchu"]["order"]), 12)
        self.assertEqual(len(table["huanghei"]["gods"]), 12)
        self.assertEqual(len(table["mansions"]["order"]), 28)
        self.assertEqual(len(table["hour_profiles"]["branches"]), 12)
        self.assertEqual(
            table["hour_profiles"]["civil_date_segments"]["子"],
            [["00:00", "01:00"], ["23:00", "24:00"]],
        )
        self.assertEqual(
            set(table["event_profiles"]),
            {
                "generic_selection",
                "marriage",
                "construction_renovation",
                "burial_funeral",
                "travel_office",
                "business_opening_transaction",
                "medical",
            },
        )
        self.assertEqual(table["ranking"]["method"], "explainable_lexicographic_v1")
        self.assertFalse(table["ranking"]["opaque_numeric_score"])

    def test_rank_effects_are_explicit_only_for_source_bound_mechanics(self) -> None:
        table = _load(SOURCE_TABLE)
        definitions = table["event_fact_definitions"]
        self.assertEqual(
            {
                field: definition["rank_effect"]
                for field, definition in definitions.items()
                if "rank_effect" in definition
            },
            {
                "sansang_day": "hard_elimination",
                "tujin": "hard_elimination",
                "luohou": "informational",
            },
        )
        construction_actions = set(
            table["event_profiles"]["construction_renovation"]["official_terms"]
        )
        self.assertTrue({"立向", "开山", "修方"} <= construction_actions)
        self.assertEqual(
            definitions["luohou"],
            {
                "kind": "direction_formula",
                "formula": "xunshan_luohou",
                "applicable_actions": ["立向"],
                "explicitly_exempt_actions": ["开山", "修方"],
                "rank_effect": "informational",
                "source_anchors": [
                    "XR-18",
                    "xieji-fulltext-L1699-L1700",
                    "xieji-fulltext-L10778",
                    "xieji-fulltext-L10969-L10970",
                    "xieji-fulltext-L11305",
                    "xieji-xunshan-luohou-v1",
                ],
            },
        )

    def test_luohou_witness_preserves_explicit_exemptions_and_mitigation(self) -> None:
        table = _load(SOURCE_TABLE)
        self.assertIn("primary_classical_rule_witnesses", table)
        witness = table["primary_classical_rule_witnesses"][
            "xieji-xunshan-luohou-v1"
        ]
        definition = table["event_fact_definitions"]["luohou"]
        source_profile = table["source_profiles"][witness["source_profile"]]
        source_path = RESEARCH_ROOT.parents[2] / source_profile["normalized_path"]
        source_text = source_path.read_text(encoding="utf-8")

        self.assertEqual(
            hashlib.sha256(source_path.read_bytes()).hexdigest(),
            source_profile["sha256"],
        )
        self.assertEqual(witness["source_anchor"], "L1699-L1700")
        self.assertEqual(
            hashlib.sha256(witness["exact_quote"].encode("utf-8")).hexdigest(),
            witness["exact_quote_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(witness["normalized_formula"].encode("utf-8")).hexdigest(),
            witness["normalized_formula_sha256"],
        )
        self.assertIn(witness["exact_quote"], source_text)
        self.assertIn("宗鏡曰巡山羅㬋忌立向不忌開山修方", source_text)
        self.assertIn("巡山羅㬋占向一白到則吉", source_text)
        self.assertIn("有吉星到山到向坐山乘旺猶可擇吉取用", source_text)
        self.assertIn("則與太歳同宫勿犯可也", source_text)
        self.assertIn("巡山羅㬋止忌立向", source_text)
        self.assertEqual(witness["event_fact_field"], "luohou")
        self.assertEqual(witness["evidence_rule_id"], "XR-18")
        self.assertEqual(witness["explicitly_taboo_actions"], ["立向"])
        self.assertEqual(witness["explicitly_exempt_actions"], ["开山", "修方"])
        self.assertEqual(witness["source_action_glyph_normalization"], {"开": "開"})
        self.assertEqual(
            witness["runtime_rank_policy"],
            "informational_until_same_palace_and_mitigation_facts_are_calculated",
        )
        self.assertEqual(
            hashlib.sha256(
                witness["runtime_evidence_statement"].encode("utf-8")
            ).hexdigest(),
            witness["runtime_evidence_statement_sha256"],
        )
        evidence_rule = next(
            item
            for item in production_evidence_rules()
            if item.system == "selection"
            and item.local_rule_id == witness["evidence_rule_id"]
        )
        self.assertEqual(evidence_rule.quote, witness["runtime_evidence_statement"])
        self.assertEqual(
            [
                (row["source_anchor"], row["role"])
                for row in witness["mitigation_witnesses"]
            ],
            [
                ("L10778", "one_white_mitigation"),
                ("L10969", "explicit_action_scope"),
                ("L10970", "non_same_palace_mitigation"),
                ("L10970", "same_palace_prohibition"),
                ("L11305", "explicit_action_scope_restatement"),
            ],
        )
        for row in witness["mitigation_witnesses"]:
            self.assertEqual(
                hashlib.sha256(row["exact_excerpt"].encode("utf-8")).hexdigest(),
                row["exact_excerpt_sha256"],
            )
            self.assertIn(row["exact_excerpt"], source_text)
        self.assertNotIn("rank_effect", witness)
        self.assertEqual(definition["rank_effect"], "informational")
        self.assertEqual(definition["applicable_actions"], ["立向"])
        self.assertEqual(definition["explicitly_exempt_actions"], ["开山", "修方"])
        event_dependency = next(
            row
            for row in _load(MATRIX)["providers"]["selection"]["dependencies"]
            if row["id"] == "selection.event-rules-and-lineage-conflicts"
        )
        self.assertEqual(
            event_dependency["primary_rule_witnesses"],
            [
                {
                    "id": "xieji-xunshan-luohou-v1",
                    **{
                        key: witness[key]
                        for key in (
                            "source_profile",
                            "source_anchor",
                            "event_profile",
                            "event_fact_field",
                            "directional_formula_key",
                            "evidence_rule_id",
                            "exact_quote_sha256",
                            "normalized_formula_sha256",
                            "explicitly_taboo_actions",
                            "explicitly_exempt_actions",
                            "source_action_glyph_normalization",
                            "runtime_rank_policy",
                            "runtime_evidence_statement_sha256",
                        )
                    },
                    "mitigation_witnesses": [
                        {
                            "source_anchor": row["source_anchor"],
                            "exact_excerpt_sha256": row["exact_excerpt_sha256"],
                            "role": row["role"],
                        }
                        for row in witness["mitigation_witnesses"]
                    ],
                }
            ],
        )

    def test_independent_hour_path_sample_matches_the_classical_start_rule(self) -> None:
        """子日申时起青龙; rotate the fixed god order without provider imports."""
        samples = _load(
            ROOT / "references/fixtures/algorithm-source-samples-v51.yaml"
        )["cases"]
        sample = samples["selection-hour-path-from-day-branch"]
        gods = [
            "青龙", "明堂", "天刑", "朱雀", "金匮", "天德",
            "白虎", "玉堂", "天牢", "玄武", "司命", "勾陈",
        ]
        branches = list("子丑寅卯辰巳午未申酉戌亥")
        qinglong_branch = "申"
        expected_gods = [
            gods[(branches.index(branch) - branches.index(qinglong_branch)) % 12]
            for branch in branches
        ]
        expected_classes = [
            "huang" if god in {"青龙", "明堂", "金匮", "天德", "玉堂", "司命"}
            else "hei"
            for god in expected_gods
        ]

        self.assertEqual(sample["input"]["day_branch"], "子")
        self.assertEqual(sample["expected"]["gods"], expected_gods)
        self.assertEqual(sample["expected"]["huanghei"], expected_classes)

    def test_reference_oracle_script_is_hash_bound_in_the_algorithm_matrix(self) -> None:
        dependencies = _load(MATRIX)["providers"]["selection"]["dependencies"]
        dependency = next(
            row
            for row in dependencies
            if row["id"] == "selection.event-rules-and-lineage-conflicts"
        )
        oracle = dependency["reference_oracle_artifact"]
        self.assertEqual(
            oracle,
            {
                "id": "independent_declarative_reference_evaluator_v1",
                "version": "1.1.0",
                "path": "scripts/selection_formula_reference.py",
                "sha256": hashlib.sha256(
                    (ROOT / "scripts/selection_formula_reference.py").read_bytes()
                ).hexdigest(),
                "independence": "recomputes directional formulas from source tables and raw structured action/direction inputs without provider event-fact or directional-fact outputs",
            },
        )

    def test_official_and_folk_rules_are_distinct_layers(self) -> None:
        table = _load(SOURCE_TABLE)
        lineages = table["lineages"]
        self.assertEqual(lineages["official"]["priority"], "primary")
        self.assertEqual(lineages["folk"]["priority"], "comparison_only")
        self.assertTrue(lineages["conflict_policy"]["preserve_disagreement"])
        self.assertFalse(lineages["conflict_policy"]["merge_verdicts"])
        self.assertEqual(
            {row["id"] for row in table["folk_rules"]},
            {
                "folk.yang-gong-thirteen",
                "folk.month-taboo",
                "folk.pengzu",
                "folk.donggong-monthly-day",
            },
        )

    def test_runtime_dependency_is_pinned_with_license_and_distribution_hashes(self) -> None:
        self.assertIn("cnlunar==0.2.4", REQUIREMENTS.read_text(encoding="utf-8").splitlines())
        provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(provenance["version"], "0.2.4")
        self.assertEqual(provenance["reviewed_upstream_commit"], "71e448a3ad4fa17bb731a57637ee0728e6f53d37")
        self.assertEqual(
            provenance["distribution_sha256"],
            "19689288604e86a3ef48dba23d39d6a7efbd5efabcb3923d4d656319762af4ea",
        )
        self.assertEqual(provenance["license_sha256"], _sha256(LICENSE))
        self.assertEqual(provenance["license"], "MIT")

    def test_thirty_engineering_comparator_examples_remain_separate(self) -> None:
        cases = _load(FIXTURE)["external_reference_cases"]
        canonical = json.dumps(
            cases,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), EXTERNAL_CASES_SHA256)
        self.assertEqual(
            {row["source"]["project"] for row in cases},
            {"6tail/lunar-python"},
        )
        self.assertEqual(
            {row["source"]["commit"] for row in cases},
            {"000c8a3d74eed098d6256a28fdd51b869324c559"},
        )
        self.assertTrue(
            all("engineering comparator" in row["source"]["role"] for row in cases)
        )

    def test_thirty_government_published_calendar_examples_are_hash_bound(self) -> None:
        fixture = _load(FIXTURE)
        cases = fixture["published_calendar_cases"]
        canonical = json.dumps(
            cases,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        self.assertEqual(len(cases), 30)
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(), PUBLISHED_CASES_SHA256
        )
        self.assertEqual(
            {source["publisher"] for source in fixture["published_calendar_sources"].values()},
            {"Hong Kong Observatory"},
        )
        self.assertTrue(
            all(
                source["artifact_url"].startswith(
                    "https://data.weather.gov.hk/weatherAPI/hko_data/calendar/"
                )
                for source in fixture["published_calendar_sources"].values()
            )
        )

        comparator_by_id = {
            row["id"]: row for row in fixture["external_reference_cases"]
        }
        for source_id, source in fixture["published_calendar_sources"].items():
            with self.subTest(source=source_id):
                local_path = ROOT / source["local_artifact_path"]
                artifact = local_path.read_bytes()
                self.assertTrue(local_path.is_file())
                self.assertEqual(
                    hashlib.sha256(artifact).hexdigest(),
                    source["artifact_sha256"],
                )
                cited_cases = [
                    case
                    for case in cases
                    if case["source_id"] == source_id
                ]
                self.assertTrue(cited_cases)
                self.assertTrue(
                    all(
                        audit_selection_provider.published_case_matches_artifact(
                            case,
                            comparator_by_id[case["comparator_case_id"]],
                            artifact,
                        )
                        for case in cited_cases
                    )
                )

    def test_published_calendar_case_is_checked_against_its_exact_csv_row(self) -> None:
        artifact = (
            "Gregorian Date,Chinese year (Gan-Zhi),Chinese year (Zodiac),"
            "Lunar month,Lunar Date\n"
            "1-Jan-24,癸卯年,兔,十一月,二十\n"
        ).encode("utf-8")
        case = {
            "source_anchor": "CSV row 2",
            "expected": {
                "lunar_year": 2023,
                "chinese_year_ganzhi": "癸卯",
                "lunar_month": 11,
                "lunar_day": 20,
                "is_leap_month": False,
            },
        }
        comparator = {"input": {"date": "2024-01-01"}}

        self.assertTrue(
            audit_selection_provider.published_case_matches_artifact(
                case, comparator, artifact
            )
        )
        wrong = copy.deepcopy(case)
        wrong["expected"]["lunar_day"] = 21
        self.assertFalse(
            audit_selection_provider.published_case_matches_artifact(
                wrong, comparator, artifact
            )
        )

    def test_tujin_formula_is_bound_to_an_exact_classical_witness(self) -> None:
        table = _load(SOURCE_TABLE)
        source = table["supplemental_classical_sources"][
            "chen-zixing-tujin-v1"
        ]
        definition = table["event_fact_definitions"]["tujin"]

        self.assertEqual(
            hashlib.sha256(source["exact_quote"].encode("utf-8")).hexdigest(),
            source["exact_quote_sha256"],
        )
        self.assertEqual(source["witness"], "CADAL02055581 digitized classical edition")
        self.assertIn("chen-zixing-tujin-v1", definition["source_anchors"])
        self.assertEqual(definition["kind"], "seasonal_branch_set")
        self.assertEqual(definition["applicable_actions"], ["破土"])
        self.assertEqual(
            definition["taboo_branches"],
            {"spring": "亥", "summer": "寅", "autumn": "巳", "winter": "申"},
        )

    def test_sansang_formula_is_bound_to_an_exact_classical_witness(self) -> None:
        table = _load(SOURCE_TABLE)
        source = table["supplemental_classical_sources"][
            "chen-zixing-sansang-v1"
        ]
        definition = table["event_fact_definitions"]["sansang_day"]

        self.assertEqual(
            hashlib.sha256(source["exact_quote"].encode("utf-8")).hexdigest(),
            source["exact_quote_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(source["normalized_formula"].encode("utf-8")).hexdigest(),
            source["normalized_formula_sha256"],
        )
        self.assertEqual(source["witness"], "CADAL02055581 digitized classical edition")
        self.assertIn("chen-zixing-sansang-v1", definition["source_anchors"])
        self.assertEqual(definition["authority"], "chen_zixing_zaozang_classical_witness")
        self.assertEqual(definition["applicable_actions"], ["安葬"])
        self.assertEqual(
            definition["taboo_branches"],
            {"spring": "辰", "summer": "未", "autumn": "戌", "winter": "丑"},
        )

        local_path = ROOT / source["local_artifact_path"]
        local_text = local_path.read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(local_path.read_bytes()).hexdigest(),
            source["local_artifact_sha256"],
        )
        self.assertIn(source["exact_quote"], local_text)

    def test_default_provider_audit_checks_local_published_artifacts(self) -> None:
        report = audit_test_session.load_report("selection")
        if report is None:
            report = audit_selection_provider.audit_selection_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["published_local_artifact_checks"], 3)
        self.assertEqual(report["counts"]["supplemental_local_artifact_checks"], 2)
        self.assertIn("primary_classical_rule_witness_checks", report["counts"])
        self.assertEqual(report["counts"]["primary_classical_rule_witness_checks"], 1)

    def test_every_event_formula_has_exact_regression_snapshots(self) -> None:
        fixture = _load(FIXTURE)
        cases = fixture["event_fact_formula_cases"]
        canonical = json.dumps(
            cases,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        self.assertEqual(len(fixture["event_fact_formula_sources"]), 74)
        self.assertEqual(len(cases), 222)
        self.assertEqual(
            fixture["event_fact_formula_fixture_policy"]["oracle_status"],
            "independent_declarative_reference_evaluator_v1",
        )
        evaluator_hash = hashlib.sha256(
            (ROOT / "scripts/selection_formula_reference.py").read_bytes()
        ).hexdigest()
        self.assertEqual(
            fixture["event_fact_formula_fixture_policy"][
                "reference_evaluator_sha256"
            ],
            evaluator_hash,
        )
        self.assertEqual(
            {
                source["reference_evaluator_sha256"]
                for source in fixture["event_fact_formula_sources"].values()
            },
            {evaluator_hash},
        )
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), FORMULA_CASES_SHA256)
        self.assertEqual(
            {
                (row["field"], row["sample_kind"])
                for row in cases
            },
            {
                (field, sample_kind)
                for field in fixture["event_fact_formula_sources"]
                for sample_kind in ("positive", "negative", "exact_jie_boundary")
            },
        )

    def test_formula_snapshot_audit_rejects_value_activation_and_duplicate_mutations(self) -> None:
        fixture = _load(FIXTURE)

        wrong_value = copy.deepcopy(fixture)
        wrong_value["event_fact_formula_cases"][0]["expected"][
            "value_sha256"
        ] = "0" * 64
        wrong_activation = copy.deepcopy(fixture)
        wrong_activation["event_fact_formula_cases"][0]["expected"]["active"] = not bool(
            wrong_activation["event_fact_formula_cases"][0]["expected"]["active"]
        )
        duplicated_case = copy.deepcopy(fixture)
        duplicated_case["event_fact_formula_cases"].append(
            copy.deepcopy(duplicated_case["event_fact_formula_cases"][0])
        )

        for mutated in (wrong_value, wrong_activation, duplicated_case):
            with self.subTest(case_count=len(mutated["event_fact_formula_cases"])):
                report = build_selection_formula_fixtures.audit_formula_fixtures(
                    mutated
                )
                self.assertFalse(report["ok"])

    def test_independent_formula_oracle_rejects_a_synchronized_provider_mutation(self) -> None:
        fixture = _load(FIXTURE)
        mutated_fixture = copy.deepcopy(fixture)
        for case in mutated_fixture["event_fact_formula_cases"]:
            if case["field"] == "tujin":
                case["expected"]["active"] = not bool(case["expected"]["active"])
                case["activation_contract"] = "exact_snapshot"

        original = build_selection_formula_fixtures.selection._event_specific_facts

        def flipped_tujin(*args, **kwargs):
            result = original(*args, **kwargs)
            if "tujin" in result:
                result["tujin"]["active"] = not bool(result["tujin"]["active"])
            return result

        build_selection_formula_fixtures._RECORD_CACHE.clear()
        try:
            with patch.object(
                build_selection_formula_fixtures.selection,
                "_event_specific_facts",
                side_effect=flipped_tujin,
            ):
                report = build_selection_formula_fixtures.audit_formula_fixtures(
                    mutated_fixture
                )
        finally:
            build_selection_formula_fixtures._RECORD_CACHE.clear()

        self.assertFalse(report["ok"])
        self.assertTrue(
            any(
                "independent formula reference mismatch" in mismatch
                for mismatch in report["mismatches"]
            ),
            report["mismatches"],
        )

    def test_independent_oracle_rejects_synchronized_direction_primitive_mutation(self) -> None:
        fixture = _load(FIXTURE)
        mutated_fixture = copy.deepcopy(fixture)
        original = build_selection_formula_fixtures.selection._directional_facts

        def corrupted_direction(*args, **kwargs):
            result = original(*args, **kwargs)
            result["xunshan_luohou_mountain"] = "甲"
            return result

        build_selection_formula_fixtures._RECORD_CACHE.clear()
        try:
            with patch.object(
                build_selection_formula_fixtures.selection,
                "_directional_facts",
                side_effect=corrupted_direction,
            ):
                for case in mutated_fixture["event_fact_formula_cases"]:
                    if case["field"] != "luohou":
                        continue
                    fact = build_selection_formula_fixtures._build(case["input"])[
                        "event_specific_facts"
                    ]["luohou"]
                    case["expected"] = {
                        "active": bool(fact["active"]),
                        "kind": str(fact["kind"]),
                        "value_sha256": build_selection_formula_fixtures.canonical_digest(
                            fact["value"]
                        ),
                    }
                    case["activation_contract"] = "exact_snapshot"
                build_selection_formula_fixtures._RECORD_CACHE.clear()
                report = build_selection_formula_fixtures.audit_formula_fixtures(
                    mutated_fixture
                )
        finally:
            build_selection_formula_fixtures._RECORD_CACHE.clear()

        self.assertFalse(report["ok"])
        self.assertTrue(
            any(
                "independent formula reference mismatch" in mismatch
                for mismatch in report["mismatches"]
            ),
            report["mismatches"],
        )


if __name__ == "__main__":
    unittest.main()
