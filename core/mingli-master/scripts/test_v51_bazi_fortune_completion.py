"""Task 7B completeness regressions for Bazi and bounded Fortune facts."""

from __future__ import annotations

import argparse
import copy
import unittest
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import yaml

import bazi_fact_adapter as bazi
import adapter_validate
import near_time_fortune_adapter as fortune
from evidence_contract import canonical_digest
from reading_engine.contracts import ReadingRequest
from reading_engine.providers import BaziProvider, FortuneProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "references" / "fixtures" / "bazi-fortune-v51.yaml"


def _fixtures() -> list[dict]:
    payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "mingli-bazi-fortune-fixtures-v1":
        raise AssertionError("unexpected Bazi/Fortune fixture schema")
    return list(payload.get("cases") or ())


def _birth(gender: str = "male") -> dict:
    facts, conflict = bazi.build_from_birth(
        "2000-10-18T06:45:00",
        timezone_name="Asia/Shanghai",
        location="上海",
        gender=gender,
        expected_pillars=None,
        zi_hour_policy="midnight",
    )
    if conflict:
        raise AssertionError("fixed birth fixture unexpectedly conflicts")
    return facts


class BaziFortuneFixtureContractTests(unittest.TestCase):
    def test_public_projection_keeps_only_source_pattern_audit_paths(self) -> None:
        provider = BaziProvider(ROOT)
        public = provider.public_basis_projection(
            {
                "output": {
                    "source_conditioned_patterns": [
                        {
                            "rule_id": "bazi/test#R-01",
                            "fact_paths": ["/chart_facts/output/day_master/stem"],
                            "predicate_audit": [
                                "/chart_facts/output/day_master/stem:eq:甲"
                            ],
                            "source_ref": {"private": "must-stay-hidden"},
                        }
                    ],
                    "interpretive_candidates": {
                        "fact_paths": ["internal-candidate-path"],
                        "predicate_audit": ["internal-candidate-audit"],
                        "status": "candidate_only",
                    },
                }
            }
        )

        pattern = public["source_conditioned_patterns"][0]
        self.assertEqual(
            pattern["fact_paths"],
            ["/chart_facts/output/day_master/stem"],
        )
        self.assertEqual(
            pattern["predicate_audit"],
            ["/chart_facts/output/day_master/stem:eq:甲"],
        )
        self.assertNotIn("source_ref", pattern)
        self.assertEqual(
            public["interpretive_candidates"],
            {"status": "candidate_only"},
        )

    def test_at_least_thirty_fixtures_cover_every_required_boundary_family(self) -> None:
        fixtures = _fixtures()
        counts = Counter(case["category"] for case in fixtures)

        self.assertGreaterEqual(len(fixtures), 30)
        self.assertGreaterEqual(counts["strong_weak_dispute"], 6)
        self.assertGreaterEqual(counts["following_dispute"], 3)
        self.assertGreaterEqual(counts["transformation_dispute"], 3)
        self.assertGreaterEqual(counts["seasonal_extreme"], 8)
        self.assertGreaterEqual(counts["luck_cycle_boundary"], 8)
        self.assertGreaterEqual(counts["long_horizon"], 6)
        self.assertEqual(len({case["id"] for case in fixtures}), len(fixtures))

    def test_disputed_natal_fixtures_never_become_hard_verdicts(self) -> None:
        for case in _fixtures():
            if not case["category"].endswith("dispute"):
                continue
            with self.subTest(case=case["id"]):
                facts = bazi.build_from_pillars(
                    list(case["input"]["pillars"]),
                    gender=None,
                    source="text",
                    source_ref=case["id"],
                )
                analysis = facts["output"]["interpretive_candidates"]
                self.assertEqual(
                    facts["output"]["day_master"]["element"],
                    case["expected"]["day_element"],
                )
                self.assertEqual(
                    facts["output"]["month_command"]["branch"],
                    case["expected"]["month_branch"],
                )
                self.assertEqual(analysis["strength"]["status"], "evidence_only")
                self.assertIsNone(analysis["strength"]["hard_verdict"])
                self.assertEqual(analysis["structure"]["status"], "candidate_only")
                self.assertIsNone(analysis["structure"]["hard_verdict"])
                self.assertEqual(
                    analysis["following_and_transformation"]["status"],
                    "requires_classical_adjudication",
                )
                shensha = facts["output"]["shensha_auxiliary"]
                self.assertEqual(shensha["precedence"], "auxiliary_only")
                self.assertEqual(shensha["may_override"], [])

    def test_shensha_auxiliary_is_calculated_and_never_promoted_to_core(self) -> None:
        facts = bazi.build_from_pillars(
            ["甲子", "丙寅", "壬辰", "辛酉"],
            gender=None,
            source="text",
            source_ref="task7b-shensha-source-sample",
        )
        auxiliary = facts["output"]["shensha_auxiliary"]
        names = {item["name"] for item in auxiliary["calculated_items"]}

        self.assertEqual(auxiliary["status"], "calculated_auxiliary_layer")
        self.assertEqual(names, {"驿马", "桃花"})
        self.assertEqual(auxiliary["precedence"], "auxiliary_only")
        self.assertEqual(auxiliary["may_override"], [])
        self.assertIn("month_command", auxiliary["cannot_override"])
        self.assertIn("strength", auxiliary["cannot_override"])
        self.assertTrue(
            all(
                item["source_dependency_id"]
                == "bazi.shensha.yima-taohua-auxiliary"
                for item in auxiliary["calculated_items"]
            )
        )

    def test_tiaohou_applicability_is_bound_to_day_stem_and_month_command(self) -> None:
        facts = bazi.build_from_pillars(
            ["甲子", "丙寅", "甲辰", "癸酉"],
            gender=None,
            source="text",
            source_ref="qiongtong-jia-wood-first-month",
        )
        identity = facts["output"]["tiaohou_markers"]["applicability_identity"]

        self.assertEqual(identity["day_stem"], "甲")
        self.assertEqual(identity["month_branch"], "寅")
        self.assertEqual(
            identity["source_dependency_id"],
            "bazi.seasonal-tiaohou.day-master-month",
        )
        self.assertNotIn("preferred_stems", facts["output"]["tiaohou_markers"])

    def test_seasonal_extreme_fixtures_bind_month_and_climate_facts(self) -> None:
        for case in _fixtures():
            if case["category"] != "seasonal_extreme":
                continue
            with self.subTest(case=case["id"]):
                facts, conflict = bazi.build_from_birth(
                    case["input"]["datetime"],
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    gender="male",
                    expected_pillars=None,
                    zi_hour_policy="midnight",
                )
                self.assertFalse(conflict)
                expected = case["expected"]
                self.assertEqual(
                    facts["calendar_normalization"]["ganzhi"]["month"],
                    expected["month_ganzhi"],
                )
                self.assertEqual(
                    facts["output"]["seasonal_profile"]["temperature"],
                    expected["temperature"],
                )
                self.assertEqual(
                    facts["output"]["seasonal_profile"]["moisture"],
                    expected["moisture"],
                )

    def test_luck_cycle_fixtures_switch_at_the_declared_instant(self) -> None:
        births = {gender: _birth(gender) for gender in ("male", "female")}
        for case in _fixtures():
            if case["category"] != "luck_cycle_boundary":
                continue
            with self.subTest(case=case["id"]):
                point = datetime.fromisoformat(case["input"]["instant"])
                result = bazi._extension_active_luck_cycle_interval(
                    point,
                    point + timedelta(microseconds=1),
                    births[case["input"]["gender"]],
                    transition_status="transition_period",
                )
                self.assertEqual(result["status"], case["expected"]["status"])
                self.assertEqual(
                    [item["sequence"] for item in result["cycles"]],
                    case["expected"]["sequences"],
                )

    def test_long_horizon_fixtures_are_complete_and_ordered(self) -> None:
        facts = _birth()
        for case in _fixtures():
            if case["category"] != "long_horizon":
                continue
            request = case["input"]
            if request["kind"] == "year":
                layers = bazi.build_year_fact_extensions(
                    facts,
                    start_year=int(request["start"]),
                    end_year=int(request["end"]),
                )
            elif request["kind"] == "month":
                layers = bazi.build_month_fact_extensions(
                    facts,
                    start_month=str(request["start"]),
                    end_month=str(request["end"]),
                )
            else:
                layers = bazi.build_day_fact_extensions(
                    facts,
                    start_date=str(request["start"]),
                    end_date=str(request["end"]),
                )
            keys = list(layers)
            self.assertEqual(len(keys), case["expected"]["count"])
            self.assertEqual(keys[0], str(case["expected"]["first"]))
            self.assertEqual(keys[-1], str(case["expected"]["last"]))


class BaziFortuneFactLayerTests(unittest.TestCase):
    def test_natal_fact_digest_ignores_wall_clock_adapter_metadata(self) -> None:
        first = _birth()
        second = _birth()

        self.assertEqual(bazi.natal_fact_digest(first), bazi.natal_fact_digest(second))

    def test_day_layer_splits_exact_jie_and_late_zi_boundaries(self) -> None:
        ordinary = _birth()
        li_chun_day = bazi.build_day_fact_extensions(
            ordinary,
            start_date="2024-02-04",
            end_date="2024-02-04",
        )["2024-02-04"]
        jie_segments = li_chun_day["ganzhi_segments"]

        self.assertEqual(len(jie_segments), 2)
        self.assertEqual(
            jie_segments[0]["end_exclusive"],
            jie_segments[1]["start_inclusive"],
        )
        self.assertNotEqual(
            jie_segments[0]["active_transits"]["month"],
            jie_segments[1]["active_transits"]["month"],
        )
        for segment in jie_segments:
            self.assertEqual(
                segment["seasonal_tiaohou_delta"]["active_month_branch"],
                segment["active_transits"]["month"][1],
            )

        late_zi, conflict = bazi.build_from_birth(
            "2000-10-18T06:45:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            gender="male",
            expected_pillars=None,
            zi_hour_policy="late-zi-next-day",
        )
        self.assertFalse(conflict)
        late_zi_day = bazi.build_day_fact_extensions(
            late_zi,
            start_date="2024-02-05",
            end_date="2024-02-05",
        )["2024-02-05"]
        zi_segments = late_zi_day["ganzhi_segments"]
        self.assertEqual(len(zi_segments), 2)
        self.assertIn("T23:00:00", zi_segments[1]["start_inclusive"])
        self.assertNotEqual(
            zi_segments[0]["active_transits"]["day"],
            zi_segments[1]["active_transits"]["day"],
        )

    def test_every_temporal_layer_exposes_structure_climate_and_auxiliary_separation(self) -> None:
        facts = _birth()
        collections = (
            bazi.build_year_fact_extensions(facts, start_year=2024, end_year=2024),
            bazi.build_month_fact_extensions(
                facts,
                start_month="2024-02",
                end_month="2024-02",
            ),
            bazi.build_day_fact_extensions(
                facts,
                start_date="2024-02-04",
                end_date="2024-02-04",
            ),
        )
        for layers in collections:
            for key, layer in layers.items():
                with self.subTest(key=key):
                    self.assertIn("active_luck_cycle", layer)
                    self.assertIn("structural_changes", layer)
                    self.assertIn("seasonal_tiaohou_delta", layer)
                    self.assertIn("shensha_auxiliary", layer)
                    self.assertEqual(
                        layer["shensha_auxiliary"]["precedence"],
                        "auxiliary_only",
                    )
                    self.assertNotIn(
                        "shensha",
                        layer["structural_changes"],
                    )

    def test_bazi_provider_supports_requested_day_horizon(self) -> None:
        calculation = BaziProvider(ROOT).calculate(
            ReadingRequest(
                query="看这三天",
                action="new",
                system="bazi",
                birth_data={
                    "datetime": "2000-10-18T06:45:00",
                    "timezone": "Asia/Shanghai",
                    "location": "上海",
                    "gender": "male",
                },
                reference_datetime="2024-02-04T12:00:00+08:00",
            )
        )
        self.assertEqual(
            calculation.facts["natal_fact_digest"],
            bazi.natal_fact_digest(calculation.facts["chart_facts"]),
        )
        extended = BaziProvider(ROOT).extend(
            calculation,
            ("timing",),
            {"kind": "day", "start": "2024-02-03", "end": "2024-02-05"},
        )

        self.assertEqual(extended.fact_extension.status, "complete")
        self.assertEqual(
            list(extended.fact_extension.facts["day_layers"]),
            ["2024-02-03", "2024-02-04", "2024-02-05"],
        )

    def test_fortune_is_one_day_view_over_the_same_natal_fact_identity(self) -> None:
        natal = _birth()
        args = argparse.Namespace(
            birth_datetime="2000-10-18T06:45:00",
            timezone="Asia/Shanghai",
            location="上海",
            longitude=None,
            latitude=None,
            coordinate_source=None,
            gender="male",
            expected_pillars=None,
            window="2026-07-24 00:00-2026-07-24 23:59",
            at="2026-07-24T12:00:00+08:00",
            zi_hour_policy="midnight",
            source_tool="adapter",
        )
        bounded = fortune.build_contract(args)

        self.assertEqual(
            bounded["birth_fact_layer"]["natal_fact_digest"],
            bazi.natal_fact_digest(natal),
        )
        self.assertEqual(bounded["bounded_view"]["period_count"], 1)
        self.assertEqual(
            bounded["bounded_view"]["base_system"],
            "bazi",
        )
        self.assertEqual(
            bounded["shensha_auxiliary"]["precedence"],
            "auxiliary_only",
        )
        self.assertEqual(
            bounded["bazi_day_fact_layer"]["active_transits"]["day"],
            bounded["transit_layers"]["day"]["pillar"],
        )
        self.assertEqual(
            bounded["bounded_view"]["base_fact_layer"],
            "bazi_day_fact_extension",
        )

    def test_fortune_rejects_a_window_that_spans_two_civil_days(self) -> None:
        args = argparse.Namespace(
            birth_datetime="2000-10-18T06:45:00",
            timezone="Asia/Shanghai",
            location="上海",
            longitude=None,
            latitude=None,
            coordinate_source=None,
            gender="male",
            expected_pillars=None,
            window="2026-07-24 23:00-2026-07-25 01:00",
            at="2026-07-24T12:00:00+08:00",
            zi_hour_policy="midnight",
            source_tool="adapter",
        )

        with self.assertRaisesRegex(ValueError, "one civil day"):
            fortune.build_contract(args)

    def test_fortune_provider_refuses_adjacent_day_extrapolation(self) -> None:
        provider = FortuneProvider(ROOT)
        calculation = provider.calculate(
            ReadingRequest(
                query="看今天",
                action="new",
                system="fortune",
                birth_data={
                    "birth_datetime": "2000-10-18T06:45:00",
                    "timezone": "Asia/Shanghai",
                    "location": "上海",
                    "gender": "male",
                },
                reference_datetime="2026-07-24T12:00:00+08:00",
            )
        )
        self.assertEqual(
            calculation.facts["natal_fact_digest"],
            calculation.facts["chart_facts"]["bounded_view"][
                "natal_fact_digest"
            ],
        )
        same_day = provider.extend(
            calculation,
            ("timing",),
            {"kind": "day", "start": "2026-07-24", "end": "2026-07-24"},
        )
        target_facts = same_day.fact_extension.facts["target_period_facts"]
        self.assertEqual(
            target_facts["selected_bazi_day_segment"]["active_transits"]["day"],
            target_facts["transit_layers"]["day"]["pillar"],
        )
        adjacent = provider.extend(
            calculation,
            ("timing",),
            {"kind": "day", "start": "2026-07-25", "end": "2026-07-25"},
        )

        self.assertEqual(adjacent.fact_extension.status, "unsupported")
        self.assertEqual(adjacent.fact_extension.facts, {})

    def test_conflict_arbitration_fail_closes_on_unverified_cross_layer_rule(self) -> None:
        facts = bazi.build_from_pillars(
            ["乙酉", "辛巳", "丙午", "癸巳"],
            gender="male",
            source="text",
            source_ref="synthetic-bz05-source-gate",
            question_contract={"domains": ["career"]},
        )
        tools = facts["output"]["interpretive_candidates"]["reasoning_tools"]
        arbitration = tools["conflict_arbitration"]
        result = arbitration["output"]

        self.assertEqual(arbitration["tool_id"], "bazi.tool.conflict_arbitration")
        self.assertEqual(
            arbitration["tool_kind"],
            "decision_stack_conflict_policy",
        )
        self.assertEqual(
            result["policy_anchor"],
            "references/matrices/bazi-core-decision-stack.md#3-冲突裁判",
        )
        self.assertEqual(
            result["status"],
            "unresolved_unverified_cross_layer_arbitrator",
        )
        self.assertIsNone(result["focus"])
        self.assertIsNone(result["selected_primary_view"])
        self.assertEqual(result["downgraded_layers"], [])
        self.assertIsNone(result["hard_verdict"])
        self.assertEqual(
            result["layers"],
            {
                "pattern_layer": tools[
                    "ziping_month_pattern_adjudication"
                ]["output"],
                "strength_flow_layer": tools["strength_evidence"]["output"],
                "tiaohou_layer": tools["tiaohou_candidates"]["output"],
            },
        )
        self.assertEqual(
            arbitration["source_refs"],
            [
                tools["ziping_month_pattern_adjudication"]["source_refs"][0],
                tools["strength_evidence"]["output"][
                    "day_master_root_support_adjudication"
                ]["source_ref"],
                tools["tiaohou_candidates"]["source_refs"][0],
            ],
        )
        self.assertTrue(
            all(
                source["verification_status"] == "verified"
                and bool(source["binding_digest"])
                for source in arbitration["source_refs"]
            )
        )
        self.assertEqual(
            result["unresolved_required_rule"],
            {
                "pack": "bazi/ditiansui-chanwei",
                "rule_id": "DR-02-06",
                "source_anchor": (
                    "references/books/bazi/ditiansui-chanwei/"
                    "rules.md#DR-02-06"
                ),
                "verification_status": "pending_verification",
            },
        )
        self.assertIn(
            "verified cross-layer priority rule is unavailable",
            result["unresolved_checks"],
        )
        self.assertIn(
            "career cannot uniquely map to a lineage focus",
            result["unresolved_checks"],
        )
        self.assertNotIn(
            "DR-02-06",
            {source["rule_id"] for source in arbitration["source_refs"]},
        )
        validation = adapter_validate.validate_payload("bazi", facts)
        self.assertTrue(validation["ok"], validation)

    def test_conflict_arbitration_rejects_resigned_semantic_tampering(self) -> None:
        facts = bazi.build_from_pillars(
            ["乙酉", "辛巳", "丙午", "癸巳"],
            gender="male",
            source="text",
            source_ref="synthetic-bz05-source-gate-tamper",
            question_contract={"domains": ["career"]},
        )

        def arbitration(payload: dict) -> dict:
            return payload["output"]["interpretive_candidates"][
                "reasoning_tools"
            ]["conflict_arbitration"]

        def resign(payload: dict) -> None:
            tool = arbitration(payload)
            tool["tool_digest"] = canonical_digest(
                {key: value for key, value in tool.items() if key != "tool_digest"}
            )

        def hard_verdict(payload: dict) -> None:
            arbitration(payload)["output"]["hard_verdict"] = "strong"

        def selected_primary_view(payload: dict) -> None:
            arbitration(payload)["output"]["selected_primary_view"] = (
                "strength_flow_layer"
            )

        def forged_source_ref(payload: dict) -> None:
            arbitration(payload)["source_refs"].append(
                {
                    "pack": "bazi/forged",
                    "rule_id": "FAKE-01",
                    "source_anchor": "references/books/bazi/forged#FAKE-01",
                    "verification_status": "verified",
                    "binding_digest": "f" * 64,
                }
            )

        def layer_drift(payload: dict) -> None:
            layers = arbitration(payload)["output"]["layers"]
            layers["pattern_layer"] = dict(layers["pattern_layer"])
            layers["pattern_layer"]["status"] = "forged_pattern_verdict"

        def malformed_domains(payload: dict) -> None:
            arbitration(payload)["output"]["requested_domains"] = [{}]

        for name, mutate in (
            ("hard_verdict", hard_verdict),
            ("selected_primary_view", selected_primary_view),
            ("source_refs", forged_source_ref),
            ("layer_drift", layer_drift),
            ("malformed_domains", malformed_domains),
        ):
            with self.subTest(tamper=name):
                tampered = copy.deepcopy(facts)
                mutate(tampered)
                resign(tampered)
                validation = adapter_validate.validate_payload("bazi", tampered)
                self.assertFalse(validation["ok"], validation)
                self.assertIn(
                    "bazi_conflict_arbitration_invalid",
                    validation["codes"],
                )

    def test_independent_validator_enforces_v51_bazi_and_fortune_layers(self) -> None:
        natal = _birth()
        missing_candidates = copy.deepcopy(natal)
        missing_candidates["output"].pop("interpretive_candidates")
        self.assertIn(
            "missing_output:interpretive_candidates",
            adapter_validate.validate_payload("bazi", missing_candidates)["codes"],
        )
        hard_verdict = copy.deepcopy(natal)
        hard_verdict["output"]["interpretive_candidates"]["strength"][
            "hard_verdict"
        ] = "strong"
        self.assertIn(
            "bazi_invalid_interpretive_candidate:strength",
            adapter_validate.validate_payload("bazi", hard_verdict)["codes"],
        )

        args = argparse.Namespace(
            birth_datetime="2000-10-18T06:45:00",
            timezone="Asia/Shanghai",
            location="上海",
            longitude=None,
            latitude=None,
            coordinate_source=None,
            gender="male",
            expected_pillars=None,
            window="2026-07-24 00:00-2026-07-24 23:59",
            at="2026-07-24T12:00:00+08:00",
            zi_hour_policy="midnight",
            source_tool="adapter",
        )
        bounded = fortune.build_contract(args)
        tampered = copy.deepcopy(bounded)
        tampered["bounded_view"]["natal_fact_digest"] = "0" * 64
        validation = adapter_validate.validate_payload("fortune", tampered)
        self.assertFalse(validation["ok"], validation)
        self.assertIn("fortune_invalid_bounded_view", validation["codes"])

        divergent = copy.deepcopy(bounded)
        divergent["selected_bazi_day_segment"]["active_transits"]["day"] = (
            "甲子"
        )
        validation = adapter_validate.validate_payload("fortune", divergent)
        self.assertFalse(validation["ok"], validation)
        self.assertIn("fortune_bazi_day_fact_divergence", validation["codes"])


if __name__ == "__main__":
    unittest.main()
