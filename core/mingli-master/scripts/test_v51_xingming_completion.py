"""Task 7E regressions for the deterministic Xingming/Qizheng provider."""

from __future__ import annotations

import copy
import unittest
from collections import Counter
from pathlib import Path

import yaml

import audit_xingming_provider
import reading_source_plan
from reading_engine.contracts import ReadingRequest
from reading_engine.contracts import canonical_digest
from reading_engine.factory import build_production_engine
from reading_engine.providers import STRUCTURED_SYSTEMS, XingmingProvider
from reading_engine.xingming import (
    BAILIU_TOTAL_YEARS,
    CLASSICAL_POINT_NAMES,
    HOUSE_NAMES,
    build_from_birth,
    build_requested_limit_layers,
    calculate_bailiu_limits,
    calculate_four_residuals,
    calculate_ming_degree,
    calculate_transformations,
    validate_fact_layer,
)
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "xingming-v51.yaml"
ALGORITHM_SAMPLES = ROOT / "references" / "fixtures" / "algorithm-source-samples-v51.yaml"
BLOCKED_PACKS = {
    "xingming/qizheng-siyu-tianjing",
    "xingming/qizheng-quanshu-dacheng",
    "xingming/minghai-quanbian",
}


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _request(**changes: object) -> ReadingRequest:
    payload = {
        "query": "按七政四余核对命盘与当前限层",
        "action": "new",
        "system": "xingming",
        "intent": {
            "subject": {"kind": "self"},
            "object": "natal",
            "event": {"kind": "natal"},
            "question_dimensions": ["state", "timing"],
            "requested_horizon": {"kind": "life"},
            "requested_granularity": "life",
            "evidence_questions": ["七政四余命身度与宫限事实如何"],
            "explicit_method": "xingming",
        },
        "birth_data": {
            "datetime": "2000-01-01T20:00:00",
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "longitude": 121.4737,
            "latitude": 31.2304,
            "coordinate_source": "fixture:WGS84",
            "gender": "male",
        },
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    payload.update(changes)
    return ReadingRequest(**payload)


class XingmingFixtureContractTests(unittest.TestCase):
    def test_source_conditioned_patterns_are_exact_identities_without_verdicts(self) -> None:
        facts = build_from_birth(
            "2000-01-01T20:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            longitude=121.4737,
            latitude=31.2304,
            coordinate_source="fixture:WGS84",
        )
        patterns = facts["output"]["source_conditioned_patterns"]

        self.assertEqual(
            {pattern["rule_id"] for pattern in patterns},
            {
                "xingming/guotian-jing#GR-01-01",
                "xingming/xingming-suyuan#XR-M01",
                "xingming/xingxue-dacheng#XXDC-M01",
            },
        )
        self.assertTrue(
            all(
                pattern["status"] == "predicate_matched_not_verdict"
                and pattern["source_dependency_id"]
                == "xingming.source-conditioned-patterns"
                for pattern in patterns
            )
        )

    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_xingming_provider.audit_xingming_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertGreaterEqual(report["counts"]["reference_charts"], 30)
        self.assertEqual(report["counts"]["classical_points"], 11)
        self.assertEqual(report["counts"]["houses"], 12)
        self.assertEqual(report["counts"]["transformations_per_stem"], 10)
        self.assertEqual(report["findings"], [])

    def test_fixture_has_thirty_independent_charts_and_boundary_families(self) -> None:
        fixture = _fixture()
        charts = fixture["reference_charts"]
        categories = Counter(case["category"] for case in charts)

        self.assertEqual(fixture["schema_version"], "mingli-xingming-fixtures-v51")
        self.assertGreaterEqual(len(charts), 30)
        self.assertEqual(len({case["id"] for case in charts}), len(charts))
        self.assertGreaterEqual(categories["date_boundary"], 4)
        self.assertGreaterEqual(categories["location_boundary"], 4)
        self.assertGreaterEqual(categories["timezone_boundary"], 4)
        self.assertGreaterEqual(categories["reference_chart"], 18)
        self.assertTrue(
            all(len(case["expected_longitudes"]) == 7 for case in charts)
        )

    def test_thirty_reference_charts_match_frozen_upstream_oracle(self) -> None:
        for case in _fixture()["reference_charts"]:
            with self.subTest(case=case["id"]):
                facts = build_from_birth(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location=case["location"],
                    longitude=case["longitude"],
                    latitude=case["latitude"],
                    coordinate_source=case["coordinate_source"],
                )
                actual = {
                    item["body"]: item["longitude_degrees"]
                    for item in facts["output"]["positions"]
                    if item["body"] in case["expected_longitudes"]
                }
                for body, expected in case["expected_longitudes"].items():
                    self.assertAlmostEqual(actual[body], expected, places=8)


class XingmingFactLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.facts = build_from_birth(
            "2000-01-01T20:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            longitude=121.4737,
            latitude=31.2304,
            coordinate_source="fixture:WGS84",
        )

    def test_eleven_points_and_twelve_houses_are_complete(self) -> None:
        output = self.facts["output"]
        positions = output["positions"]
        houses = output["houses"]

        self.assertEqual([item["classical_name"] for item in positions], list(CLASSICAL_POINT_NAMES))
        self.assertEqual(len(positions), 11)
        self.assertEqual([item["name"] for item in houses], list(HOUSE_NAMES))
        self.assertEqual(len(houses), 12)
        self.assertTrue(all(0 <= item["longitude_degrees"] < 360 for item in positions))
        self.assertTrue(all(0 <= item["start_degree"] < 360 for item in houses))
        self.assertTrue(all(item["fact_status"] == "calculated_not_interpreted" for item in positions))

    def test_coordinate_and_pseudo_point_conventions_are_explicit(self) -> None:
        output = self.facts["output"]
        conventions = output["conventions"]
        positions = {item["classical_name"]: item for item in output["positions"]}

        self.assertEqual(conventions["zodiac"], "tropical")
        self.assertEqual(conventions["coordinate_frame"], "geocentric_true_ecliptic_of_date")
        self.assertEqual(conventions["precession"], "equinox_of_date_by_astronomy_engine")
        self.assertEqual(conventions["house_profile"], "topocentric-equal-house-mingshen-opposition-v1")
        self.assertEqual(
            conventions["luoji_identity"],
            "guolao-luohou-descending-jidu-ascending-v1",
        )
        self.assertEqual(positions["罗睺"]["point_kind"], "calculated_lunar_node")
        self.assertEqual(positions["计都"]["point_kind"], "calculated_lunar_node_opposition")
        self.assertEqual(
            positions["罗睺"]["trace"]["profile"],
            "astronomy-engine-interpolated-descending-node-v1",
        )
        self.assertEqual(positions["罗睺"]["motion_state"], "retrograde")
        self.assertEqual(positions["计都"]["motion_state"], "retrograde")
        self.assertEqual(positions["紫炁"]["point_kind"], "classical_mean_pseudo_point")
        self.assertEqual(positions["月孛"]["point_kind"], "classical_mean_pseudo_point")
        self.assertFalse(positions["紫炁"]["observed_body"])
        self.assertFalse(positions["月孛"]["observed_body"])
        self.assertEqual(
            conventions["ziqi"],
            "xingxue-dated-mean-ziqi-v1",
        )

    def test_ming_shen_and_luo_ji_are_exact_oppositions(self) -> None:
        output = self.facts["output"]
        ming_shen = output["ming_shen"]
        positions = {item["classical_name"]: item for item in output["positions"]}

        self.assertAlmostEqual(
            (ming_shen["shen_degree"] - ming_shen["ming_degree"]) % 360,
            180.0,
            places=10,
        )
        self.assertAlmostEqual(
            (positions["计都"]["longitude_degrees"] - positions["罗睺"]["longitude_degrees"]) % 360,
            180.0,
            places=10,
        )

    def test_ten_stems_each_map_ten_transformations_bijectively(self) -> None:
        expected_rows = {
            "天禄": "火孛木金土月水气计罗",
            "天暗": "孛木金土月水气计罗火",
            "天福": "木金土月水气计罗火孛",
            "天耗": "金土月水气计罗火孛木",
            "天荫": "土月水气计罗火孛木金",
            "天贵": "月水气计罗火孛木金土",
            "天刑": "水气计罗火孛木金土月",
            "天印": "气计罗火孛木金土月水",
            "天囚": "计罗火孛木金土月水气",
            "天权": "罗火孛木金土月水气计",
        }
        normalized = {
            "火": "火星", "孛": "月孛", "木": "木星", "金": "金星",
            "土": "土星", "月": "太阴", "水": "水星", "气": "紫炁",
            "计": "计都", "罗": "罗睺",
        }
        for stem in "甲乙丙丁戊己庚辛壬癸":
            with self.subTest(stem=stem):
                mapping = calculate_transformations(stem)
                self.assertEqual(len(mapping), 10)
                self.assertEqual(len({item["transformation"] for item in mapping}), 10)
                self.assertEqual(len({item["classical_body"] for item in mapping}), 10)
                self.assertTrue(all(item["source_dependency_id"] == "xingming.transformations.ten-stem-table" for item in mapping))
                stem_index = "甲乙丙丁戊己庚辛壬癸".index(stem)
                self.assertEqual(
                    {item["transformation"]: item["classical_body"] for item in mapping},
                    {
                        label: normalized[row[stem_index]]
                        for label, row in expected_rows.items()
                    },
                )

    def test_bailiu_is_one_hundred_years_six_months_not_106_years(self) -> None:
        limits = calculate_bailiu_limits(42.5)

        self.assertEqual(BAILIU_TOTAL_YEARS, 100.5)
        self.assertEqual(len(limits), 12)
        self.assertEqual(
            [item["house"] for item in limits],
            ["命宫", "相貌", "福德", "官禄", "迁移", "疾厄", "妻妾", "奴仆", "男女", "田宅", "兄弟", "财帛"],
        )
        self.assertEqual(
            [item["duration_years"] for item in limits],
            [15.0, 10.0, 11.0, 15.0, 8.0, 7.0, 11.0, 4.5, 4.5, 4.5, 5.0, 5.0],
        )
        self.assertEqual(limits[-1]["age_end_years"], 100.5)
        self.assertEqual(sum(item["duration_years"] for item in limits), 100.5)

    def test_location_changes_ming_degree_but_not_geocentric_planets(self) -> None:
        east = self.facts
        west = build_from_birth(
            "2000-01-01T12:00:00Z",
            timezone_name="UTC",
            location="格林尼治",
            longitude=0.0,
            latitude=51.4779,
            coordinate_source="fixture:WGS84",
        )
        east_positions = {item["body"]: item["longitude_degrees"] for item in east["output"]["positions"]}
        west_positions = {item["body"]: item["longitude_degrees"] for item in west["output"]["positions"]}

        for body in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            self.assertAlmostEqual(east_positions[body], west_positions[body], places=8)
        self.assertNotAlmostEqual(
            east["output"]["ming_shen"]["ming_degree"],
            west["output"]["ming_shen"]["ming_degree"],
            places=4,
        )

    def test_repeated_input_is_digest_stable_and_validator_fails_closed(self) -> None:
        repeated = build_from_birth(
            "2000-01-01T20:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            longitude=121.4737,
            latitude=31.2304,
            coordinate_source="fixture:WGS84",
        )
        self.assertEqual(self.facts["natal_fact_digest"], repeated["natal_fact_digest"])
        self.assertTrue(validate_fact_layer(self.facts)["ok"])

        tampered = copy.deepcopy(self.facts)
        tampered["output"]["positions"][0]["longitude_degrees"] += 1
        report = validate_fact_layer(tampered)
        self.assertFalse(report["ok"])
        self.assertIn("xingming_ephemeris_position_mismatch", report["codes"])

        convention_tampered = copy.deepcopy(self.facts)
        convention_tampered["conventions"]["luoji_identity"] = "swapped"
        convention_tampered["output"]["conventions"]["luoji_identity"] = "swapped"
        convention_tampered["natal_fact_digest"] = canonical_digest(
            {
                "schema_version": convention_tampered["schema_version"],
                "system": convention_tampered["system"],
                "calendar_digest": convention_tampered["calendar_normalization"]["calendar_digest"],
                "ephemeris_digest": convention_tampered["ephemeris"]["ephemeris_digest"],
                "conventions": convention_tampered["conventions"],
                "output": convention_tampered["output"],
            }
        )
        convention_report = validate_fact_layer(convention_tampered)
        self.assertFalse(convention_report["ok"])
        self.assertIn("xingming_convention_mismatch", convention_report["codes"])

    def test_month_horizon_uses_the_real_last_day(self) -> None:
        layer = build_requested_limit_layers(
            self.facts,
            horizon={"kind": "month", "start": "2024-02", "end": "2024-02"},
        )

        self.assertEqual(
            [row["date"] for row in layer["requested_limit_layers"]],
            ["2024-02-01", "2024-02-29"],
        )

    def test_requested_dates_outside_bailiu_table_remain_explicit_facts(self) -> None:
        layer = build_requested_limit_layers(
            self.facts,
            horizon={"kind": "range", "start": "1999-12-01", "end": "2101-01-01"},
        )

        rows = layer["requested_limit_layers"]
        self.assertEqual(rows[0]["status"], "not_applicable_before_birth")
        self.assertIsNone(rows[0]["house"])
        self.assertEqual(rows[1]["status"], "outside_source_table")
        self.assertIsNone(rows[1]["house"])

    def test_coordinates_are_required_for_a_real_house_chart(self) -> None:
        with self.assertRaisesRegex(ValueError, "longitude and latitude"):
            build_from_birth(
                "2000-01-01T20:00:00",
                timezone_name="Asia/Shanghai",
                location="上海",
            )

    def test_registered_independent_algorithm_samples_match(self) -> None:
        cases = yaml.safe_load(ALGORITHM_SAMPLES.read_text(encoding="utf-8"))["cases"]

        ming_case = cases["xingming-topocentric-ming-j2000-greenwich"]
        ming = calculate_ming_degree(
            ming_case["input"]["instant"],
            longitude=ming_case["input"]["longitude"],
            latitude=ming_case["input"]["latitude"],
        )
        tolerance = ming_case["expected"]["tolerance_degrees"]
        self.assertAlmostEqual(
            ming["ming_degree"], ming_case["expected"]["ming_degree"],
            delta=tolerance,
        )
        self.assertAlmostEqual(
            ming["shen_degree"], ming_case["expected"]["shen_degree"],
            delta=tolerance,
        )

        residual_case = cases["xingming-residual-points-j2000"]
        residuals = calculate_four_residuals(residual_case["input"]["instant"])
        tolerance = residual_case["expected"]["tolerance_degrees"]
        for name in ("罗睺", "计都", "紫炁", "月孛"):
            self.assertAlmostEqual(
                residuals[name]["longitude_degrees"],
                residual_case["expected"][name],
                delta=tolerance,
            )

        transformation_case = cases["xingming-ten-stem-transformations-jia"]
        transformations = calculate_transformations(
            transformation_case["input"]["year_stem"]
        )
        self.assertEqual(
            [row["transformation"] for row in transformations],
            transformation_case["expected"]["transformations"],
        )
        self.assertEqual(
            [row["classical_body"] for row in transformations],
            transformation_case["expected"]["classical_bodies"],
        )

        limit_case = cases["xingming-bailiu-100-years-six-months"]
        limits = calculate_bailiu_limits(limit_case["input"]["ming_degree"])
        self.assertEqual(
            [row["house"] for row in limits],
            limit_case["expected"]["houses"],
        )
        self.assertEqual(
            [row["duration_years"] for row in limits],
            limit_case["expected"]["duration_years"],
        )
        self.assertEqual(
            limits[-1]["age_end_years"],
            limit_case["expected"]["total_years"],
        )


class XingmingProviderTests(unittest.TestCase):
    def test_provider_is_calculation_not_generic_validation(self) -> None:
        result = XingmingProvider(ROOT).calculate(_request())

        self.assertEqual(result.system, "xingming")
        self.assertEqual(result.provider_id, "mingli-master.xingming.v1")
        self.assertNotEqual(result.provider_id, "validated-user-chart")
        self.assertEqual(result.facts["chart_facts"]["fact_layer_status"], "calculated_xingming_facts")
        self.assertRegex(result.facts["calendar_digest"], r"^[0-9a-f]{64}$")
        self.assertRegex(result.facts["ephemeris_digest"], r"^[0-9a-f]{64}$")

    def test_capability_and_factory_activate_only_the_real_provider(self) -> None:
        capability = PROVIDER_CAPABILITIES["xingming"]
        self.assertEqual(capability.mode, "calculation")
        self.assertEqual(
            capability.extension_outputs,
            ("requested_limit_layers", "annual_transformations"),
        )
        self.assertEqual(missing_required_inputs("xingming", _request()), ())

        engine = build_production_engine(
            skill_dir=ROOT,
            store_root=ROOT / ".work" / "task7e-test-store",
        )
        self.assertIsInstance(engine.providers["xingming"], XingmingProvider)
        self.assertNotIn("xingming", STRUCTURED_SYSTEMS)

    def test_source_plan_uses_complete_facts_and_excludes_blocked_packs(self) -> None:
        result = XingmingProvider(ROOT).calculate(_request())
        plan = reading_source_plan.compile_source_plan(
            "xingming",
            {"requested_dimensions": ["state", "timing"]},
            result.indexed_facts(),
        )

        self.assertTrue(set(plan["required_packs"]).isdisjoint(BLOCKED_PACKS))
        self.assertEqual(
            plan["chart_contract"]["required_fields"],
            [
                "ephemeris",
                "positions",
                "houses",
                "ming_shen",
                "transformations",
                "major_limits",
                "source_conditioned_patterns",
            ],
        )
        self.assertTrue(all(item["satisfied"] for item in plan["applicability_conditions"]), plan)

    def test_requested_limit_layers_are_complete_and_digest_bound(self) -> None:
        provider = XingmingProvider(ROOT)
        base = provider.calculate(_request())
        extended = provider.extend(
            base,
            ("timing",),
            {"kind": "year", "start": "2026-01-01", "end": "2026-12-31"},
        )

        self.assertEqual(extended.fact_extension.status, "complete")
        self.assertEqual(
            extended.fact_extension.base_calculation_digest,
            base.result_hash,
        )
        self.assertEqual(
            extended.fact_extension.facts["limit_profile"],
            "dongwei-bailiu-100y6m-v1",
        )
        self.assertTrue(extended.fact_extension.facts["requested_limit_layers"])
        annual = extended.fact_extension.facts["annual_transformations"]
        self.assertEqual([item["year"] for item in annual], [2026])
        self.assertEqual(annual[0]["year_ganzhi"], "丙午")
        self.assertEqual(len(annual[0]["transformations"]), 10)

        outside = provider.extend(
            base,
            ("timing",),
            {"kind": "date", "end": "2101-01-01"},
        )
        self.assertEqual(outside.fact_extension.status, "unsupported")
        self.assertEqual(outside.fact_extension.facts, {})

    def test_refine_reuses_chart_without_reusing_latest_judgment(self) -> None:
        provider = XingmingProvider(ROOT)
        base = provider.calculate(_request())
        refined = provider.refine(
            _request(query="只追问当前宫限"),
            base,
        )

        self.assertEqual(refined.facts["natal_fact_digest"], base.facts["natal_fact_digest"])
        self.assertEqual(refined.facts["ephemeris_digest"], base.facts["ephemeris_digest"])
        self.assertNotEqual(refined.result_hash, base.result_hash)


if __name__ == "__main__":
    unittest.main()
