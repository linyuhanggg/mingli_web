"""Task 7D regressions for the deterministic early-Luming fact provider."""

from __future__ import annotations

import copy
import unittest
from collections import Counter
from pathlib import Path

import yaml

import audit_luming_provider
import reading_source_plan
import audit_luming_provider
import reading_source_plan
from reading_engine.contracts import ReadingRequest
from reading_engine.factory import build_production_engine
from reading_engine.luming import (
    BRANCHES,
    JIAZI,
    LU_BY_STEM,
    NAYIN_BY_JIAZI,
    STEMS,
    TIANYI_BY_STEM,
    YIMA_BY_BRANCH,
    build_fact_layer,
    calculate_taiyuan,
    nayin_for,
    validate_facts,
)
from reading_engine.providers import LumingProvider
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "luming-v51.yaml"
POSITIONS = ("year", "month", "day", "hour")


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


class LumingFixtureContractTests(unittest.TestCase):
    def test_machine_readable_completeness_audit_passes_before_route_activation(self) -> None:
        report = audit_luming_provider.audit_luming_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["nayin_rows"], 60)
        self.assertGreaterEqual(report["counts"]["source_examples"], 30)
        self.assertGreaterEqual(report["counts"]["calendar_boundaries"], 7)
        self.assertEqual(report["findings"], [])

    def test_machine_readable_provider_completeness_audit_passes(self) -> None:
        report = audit_luming_provider.audit_luming_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["nayin_rows"], 60)
        self.assertEqual(report["counts"]["source_examples"], 30)
        self.assertGreaterEqual(report["counts"]["calendar_boundaries"], 7)
        self.assertEqual(report["findings"], [])

    def test_fixture_has_all_sixty_nayin_and_thirty_cross_book_examples(self) -> None:
        fixture = _fixture()
        cycle = fixture["nayin_cycle"]
        examples = fixture["source_examples"]
        counts = Counter(case["source"] for case in examples)

        self.assertEqual(fixture["schema_version"], "mingli-luming-fixtures-v51")
        self.assertEqual(len(cycle), 60)
        self.assertEqual(len({row[0] for row in cycle}), 60)
        self.assertEqual(len(examples), 30)
        self.assertGreaterEqual(counts["李虚中命书"], 10)
        self.assertGreaterEqual(counts["五行精纪"], 10)
        self.assertGreaterEqual(counts["兰台妙选"], 10)
        self.assertEqual(len({case["id"] for case in examples}), 30)

    def test_all_sixty_nayin_rows_match_the_independent_fixture(self) -> None:
        expected = dict(_fixture()["nayin_cycle"])
        self.assertEqual(NAYIN_BY_JIAZI, expected)
        for jiazi, name in expected.items():
            with self.subTest(jiazi=jiazi):
                self.assertEqual(nayin_for(jiazi), name)

    def test_thirty_source_examples_reproduce_the_frozen_nayin(self) -> None:
        for case in _fixture()["source_examples"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    [nayin_for(pillar) for pillar in case["pillars"]],
                    case["expected_nayin"],
                )

    def test_taiyuan_formula_matches_both_preimplementation_examples(self) -> None:
        for case in _fixture()["taiyuan_cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(calculate_taiyuan(case["month_pillar"]), case["expected"])

    def test_fixture_count_and_boundary_families_meet_release_contract(self) -> None:
        fixture = _fixture()
        total = (
            len(fixture["source_examples"])
            + len(fixture["taiyuan_cases"])
            + len(fixture["calendar_cases"])
        )
        categories = Counter(case["category"] for case in fixture["calendar_cases"])

        self.assertGreaterEqual(total, 30)
        self.assertGreaterEqual(categories["solar_term_boundary"], 2)
        self.assertGreaterEqual(categories["day_rollover"], 2)
        self.assertGreaterEqual(categories["leap_month"], 1)
        self.assertGreaterEqual(categories["timezone_boundary"], 2)


class LumingFactLayerTests(unittest.TestCase):
    def test_source_conditioned_patterns_are_exact_identities_without_verdicts(self) -> None:
        facts = build_fact_layer(
            {"year": "乙丑", "month": "丙戌", "day": "己酉", "hour": "丁卯"},
            taiyuan_profile="wuxing-jingji-use-taiyuan-v1",
        )
        patterns = facts["output"]["source_conditioned_patterns"]

        self.assertIn(
            "luming-nayin/lantai-miaoxuan#LT-M01",
            {pattern["rule_id"] for pattern in patterns},
        )
        self.assertTrue(
            all(
                pattern["status"] == "predicate_matched_not_verdict"
                and pattern["source_dependency_id"]
                == "luming.source-conditioned-patterns"
                for pattern in patterns
            )
        )

    def test_three_yuan_profiles_remain_separate_and_contain_no_ten_gods(self) -> None:
        pillars = {"year": "庚辰", "month": "丙戌", "day": "己酉", "hour": "丁卯"}
        facts = build_fact_layer(
            pillars,
            taiyuan_profile="wuxing-jingji-use-taiyuan-v1",
        )
        output = facts["output"]
        li = output["three_yuan_profiles"]["li_xuzhong"]
        luo = output["three_yuan_profiles"]["luoluzi"]

        self.assertEqual(li["tianyuan"], ["庚", "丙", "己", "丁"])
        self.assertEqual(li["diyuan"], ["辰", "戌", "酉", "卯"])
        self.assertEqual(
            li["renyuan_nayin"],
            ["白蜡金", "屋上土", "大驿土", "炉中火"],
        )
        self.assertEqual(luo["tianyuan"], li["tianyuan"])
        self.assertEqual(luo["zhiyuan"], li["diyuan"])
        self.assertEqual(
            luo["renyuan_hidden_stems"],
            [["戊", "乙", "癸"], ["戊", "辛", "丁"], ["辛"], ["乙"]],
        )
        self.assertEqual(output["taiyuan"]["ganzhi"], "丁丑")
        self.assertEqual(output["taiyuan"]["nayin"], "涧下水")
        self.assertEqual(output["interpretation_status"], "facts_only")
        self.assertNotIn("ten_gods", str(output).lower())
        self.assertNotIn("十神", str(output))

    def test_taiyuan_conflict_is_explicit_and_never_silently_selected(self) -> None:
        pillars = {"year": "甲子", "month": "丙寅", "day": "甲辰", "hour": "辛未"}
        omitted = build_fact_layer(pillars)
        excluded = build_fact_layer(
            pillars,
            taiyuan_profile="wuxing-jingji-no-taiyuan-v1",
        )

        self.assertEqual(omitted["output"]["taiyuan"]["status"], "not_requested")
        self.assertEqual(
            excluded["output"]["taiyuan"]["status"],
            "excluded_by_selected_profile",
        )
        self.assertNotIn("ganzhi", excluded["output"]["taiyuan"])
        self.assertTrue(excluded["output"]["taiyuan"]["disputed"])

    def test_lu_ma_and_both_gui_recensions_are_calculated_as_neutral_relations(self) -> None:
        facts = build_fact_layer(
            {"year": "甲子", "month": "丙寅", "day": "甲辰", "hour": "辛未"}
        )
        relations = facts["output"]["relations"]

        self.assertEqual({row["anchor"] for row in relations["lu"]}, {"year", "day"})
        self.assertTrue(all(row["target_branch"] == "寅" for row in relations["lu"]))
        self.assertTrue(all(row["matched_positions"] == ["month"] for row in relations["lu"]))
        self.assertTrue(all(row["target_branch"] == "寅" for row in relations["ma"]))
        self.assertEqual(
            {row["recension"] for row in relations["gui"]},
            {"tianyi-branch-v1", "li-xuzhong-full-pillar-v1"},
        )
        branch_rows = [
            row for row in relations["gui"] if row["recension"] == "tianyi-branch-v1"
        ]
        self.assertTrue(all(row["candidates"] == ["丑", "未"] for row in branch_rows))
        self.assertTrue(all(row["matched_positions"] == ["hour"] for row in branch_rows))
        self.assertTrue(all(row["status"] == "calculated_relation_not_verdict" for row in relations["lu"] + relations["ma"] + relations["gui"]))

    def test_fact_digest_is_stable_and_source_roles_are_explicit(self) -> None:
        pillars = {"year": "甲子", "month": "丙寅", "day": "甲辰", "hour": "辛未"}
        first = build_fact_layer(pillars)
        second = build_fact_layer(pillars)

        self.assertEqual(first["natal_fact_digest"], second["natal_fact_digest"])
        self.assertEqual(
            [item["pack"] for item in first["source_lineage"]["calculation"]],
            [
                "luming-nayin/li-xuzhong-mingshu",
                "luming-nayin/luoluzi-sanming",
                "luming-nayin/wuxing-jingji",
            ],
        )
        self.assertEqual(
            [item["pack"] for item in first["source_lineage"]["interpretation"]],
            ["luming-nayin/lantai-miaoxuan"],
        )

    def test_every_lu_ma_gui_lookup_row_is_complete(self) -> None:
        self.assertEqual(set(LU_BY_STEM), set(STEMS))
        self.assertEqual(set(TIANYI_BY_STEM), set(STEMS))
        self.assertEqual(set(YIMA_BY_BRANCH), set(BRANCHES))
        self.assertEqual(len(JIAZI), 60)
        self.assertTrue(all(len(candidates) == 2 for candidates in TIANYI_BY_STEM.values()))

    def test_validator_fails_closed_on_nayin_and_relation_tampering(self) -> None:
        facts = build_fact_layer(
            {"year": "甲子", "month": "丙寅", "day": "甲辰", "hour": "辛未"}
        )
        bad_nayin = copy.deepcopy(facts)
        bad_nayin["output"]["pillars"]["year"]["nayin"]["name"] = "大海水"
        report = validate_facts(bad_nayin)
        self.assertFalse(report["ok"])
        self.assertIn("luming_nayin_mismatch", report["codes"])

        bad_relation = copy.deepcopy(facts)
        bad_relation["output"]["relations"]["lu"][0]["target_branch"] = "申"
        report = validate_facts(bad_relation)
        self.assertFalse(report["ok"])
        self.assertIn("luming_lu_relation_mismatch", report["codes"])


class LumingProviderTests(unittest.TestCase):
    def _request(self, **changes: object) -> ReadingRequest:
        payload = {
            "query": "按早期禄命体系核对事实",
            "action": "new",
            "system": "luming-nayin",
            "intent": {
                "subject": {"kind": "self"},
                "object": "natal",
                "event": {"kind": "natal"},
                "question_dimensions": ["state"],
                "requested_horizon": {"kind": "life"},
                "requested_granularity": "life",
                "evidence_questions": ["早期禄命三元事实如何"],
                "explicit_method": "luming-nayin",
            },
            "chart_data": {"pillars": ["庚辰", "丙戌", "己酉", "丁卯"]},
            "metadata": {"luming_taiyuan_profile": "wuxing-jingji-use-taiyuan-v1"},
        }
        payload.update(changes)
        return ReadingRequest(**payload)

    def test_provider_calculates_from_validated_pillars_without_generic_chart_mode(self) -> None:
        result = LumingProvider(ROOT).calculate(self._request())

        self.assertEqual(result.system, "luming-nayin")
        self.assertEqual(result.provider_id, "mingli-master.luming-nayin.v1")
        self.assertEqual(result.facts["chart_facts"]["fact_layer_status"], "calculated_early_luming_facts")
        self.assertEqual(result.facts["chart_facts"]["output"]["taiyuan"]["ganzhi"], "丁丑")
        self.assertNotEqual(result.provider_id, "validated-user-chart")

    def test_source_plan_sees_complete_facts_and_all_declared_books(self) -> None:
        result = LumingProvider(ROOT).calculate(self._request())
        plan = reading_source_plan.compile_source_plan(
            "luming-nayin",
            {"requested_dimensions": ["state"]},
            result.indexed_facts(),
        )

        self.assertEqual(
            plan["required_packs"],
            [
                "luming-nayin/li-xuzhong-mingshu",
                "luming-nayin/luoluzi-sanming",
                "luming-nayin/wuxing-jingji",
                "luming-nayin/lantai-miaoxuan",
            ],
        )
        self.assertTrue(
            all(item["satisfied"] for item in plan["applicability_conditions"]),
            plan["applicability_conditions"],
        )

    def test_birth_mode_consumes_the_shared_calendar_digest(self) -> None:
        request = self._request(
            chart_data={},
            birth_data={
                "datetime": "2000-10-18T06:45:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                "gender": "male",
            },
            timezone="Asia/Shanghai",
            location="上海",
        )
        first = LumingProvider(ROOT).calculate(request)
        second = LumingProvider(ROOT).calculate(request)

        self.assertRegex(first.facts["calendar_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(first.facts["calendar_digest"], second.facts["calendar_digest"])
        self.assertEqual(first.facts["natal_fact_digest"], second.facts["natal_fact_digest"])
        self.assertEqual(
            first.facts["calendar_digest"],
            first.facts["chart_facts"]["calendar_normalization"]["calendar_digest"],
        )

    def test_all_calendar_boundary_fixtures_reproduce_frozen_shared_facts(self) -> None:
        provider = LumingProvider(ROOT)
        for case in _fixture()["calendar_cases"]:
            with self.subTest(case=case["id"]):
                result = provider.calculate(
                    self._request(
                        chart_data={},
                        birth_data={
                            "datetime": case["datetime"],
                            "timezone": case["timezone"],
                            "location": case["location"],
                            "gender": "male",
                            "zi_hour_policy": case["zi_hour_policy"],
                        },
                        timezone=case["timezone"],
                        location=case["location"],
                    )
                )
                calendar = result.facts["chart_facts"]["calendar_normalization"]
                lunar = calendar["lunar_date"]
                self.assertEqual(
                    [calendar["ganzhi"][position] for position in POSITIONS],
                    case["expected_pillars"],
                )
                self.assertEqual(
                    [lunar["year"], lunar["month"], lunar["day"], lunar["is_leap_month"]],
                    case["expected_lunar"],
                )
                self.assertEqual(calendar["timezone_offset_seconds"], case["expected_offset_seconds"])

    def test_capability_becomes_calculation_only_after_complete_provider_exists(self) -> None:
        capability = PROVIDER_CAPABILITIES["luming-nayin"]
        self.assertEqual(capability.mode, "calculation")
        self.assertNotEqual(capability.mode, "unavailable")
        self.assertEqual(
            missing_required_inputs("luming-nayin", self._request()),
            (),
        )

    def test_production_factory_registers_the_deterministic_provider(self) -> None:
        engine = build_production_engine(
            skill_dir=ROOT,
            store_root=ROOT / ".work" / "task7d-test-store",
        )
        provider = engine.providers["luming-nayin"]
        self.assertIsInstance(provider, LumingProvider)
        self.assertEqual(provider.capability.mode, "calculation")

    def test_source_plan_requires_the_actual_calculated_fact_shapes(self) -> None:
        result = LumingProvider(ROOT).calculate(self._request())
        plan = reading_source_plan.compile_source_plan(
            "luming-nayin",
            {"evidence_questions": ["三元与禄马贵事实"]},
            result.facts,
        )

        self.assertEqual(
            plan["chart_contract"]["required_fields"],
            ["pillars", "three_yuan_profiles", "relations"],
        )
        self.assertTrue(
            all(item["satisfied"] for item in plan["applicability_conditions"]),
            plan["applicability_conditions"],
        )

    def test_life_extension_is_complete_and_temporal_extrapolation_is_rejected(self) -> None:
        provider = LumingProvider(ROOT)
        base = provider.calculate(self._request())
        life = provider.extend(base, ("state",), {"kind": "life"})
        day = provider.extend(
            base,
            ("timing",),
            {"kind": "day", "start": "2026-07-24", "end": "2026-07-24"},
        )

        self.assertEqual(life.fact_extension.status, "complete")
        self.assertEqual(day.fact_extension.status, "unsupported")
        self.assertEqual(day.result_hash, base.result_hash)


if __name__ == "__main__":
    unittest.main()
