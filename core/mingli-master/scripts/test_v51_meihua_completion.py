"""Task 7G regressions for the deterministic Meihua Yishu provider."""

from __future__ import annotations

import copy
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import yaml

import audit_meihua_provider
import reading_source_plan
from reading_engine import calendar_core
from reading_engine.contracts import (
    AcceptedReading,
    NeedUserFact,
    PreparedReading,
    ReadingRequest,
)
from reading_engine.factory import build_production_engine
from reading_engine.meihua import (
    build_from_method,
    build_hexagram_catalog,
    cast_from_totals,
    seasonal_strength_for,
    trigram_for_number,
    validate_fact_layer,
)
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import MeihuaProvider, STRUCTURED_SYSTEMS
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "meihua-v51.yaml"


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _calendar(civil_datetime: str = "2024-02-10T12:00:00") -> dict:
    return calendar_core.normalize_calendar(
        civil_datetime,
        timezone_name="Asia/Shanghai",
        location="上海",
    )


def _intent() -> dict:
    return {
        "subject_refs": ["self"],
        "calculation_object": "concrete_event",
        "question_dimensions": ["outcome", "state"],
        "horizon": {"kind": "instant"},
        "requested_method": "meihua",
        "requested_granularity": "instant",
        "continuity": {
            "reading_id": None,
            "same_subject": False,
            "same_event": False,
        },
        "facts_present": ["casting_method", "event_datetime", "timezone", "location"],
        "facts_corrected": [],
        "evidence_questions": ["此卦的体用、互变和时令事实如何"],
    }


def _request(**changes: object) -> ReadingRequest:
    payload = {
        "query": "按梅花易数核对这件事",
        "action": "new",
        "system": "meihua",
        "intent": _intent(),
        "chart_data": {
            "casting_method": "supplied_hexagram",
            "upper_trigram": "兑",
            "lower_trigram": "离",
            "moving_line": 1,
            "provenance": {"kind": "user_supplied_complete_hexagram"},
        },
        "event_datetime": "2024-02-10T12:00:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    payload.update(changes)
    return ReadingRequest(**payload)


def _turn_request(
    chart: dict[str, object] | None = None,
    *,
    query: str = "按梅花易数核对这件事",
    include_default_chart: bool = True,
) -> ProviderRequest:
    facts: dict[str, object] = {
        "event_datetime": "2024-02-10T12:00:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    if chart is not None:
        facts.update(chart)
    elif include_default_chart:
        facts.update(
            {
                "casting_method": "supplied_hexagram",
                "upper_trigram": "兑",
                "lower_trigram": "离",
                "moving_line": 1,
                "provenance": {"kind": "user_supplied_complete_hexagram"},
            }
        )
    return ProviderRequest(
        query=query,
        subject_refs=("current_user",),
        object_id="concrete_event",
        dimension_ids=("outcome",),
        horizon={"kind": "instant", "start": None, "end": None},
        facts={"current_user": facts},
    )


class MeihuaFixtureContractTests(unittest.TestCase):
    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_meihua_provider.audit_meihua_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["hexagrams"], 64)
        self.assertGreaterEqual(report["counts"]["source_examples"], 30)
        self.assertEqual(report["counts"]["classical_examples"], 10)
        self.assertEqual(report["counts"]["source_rule_boundary_vectors"], 20)
        self.assertEqual(report["counts"]["casting_methods"], 5)
        self.assertGreaterEqual(report["counts"]["calendar_boundaries"], 8)
        self.assertEqual(report["counts"]["seasonal_profiles"], 5)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 3)
        self.assertEqual(report["findings"], [])

    def test_fixture_distinguishes_classical_cases_from_source_rule_vectors(self) -> None:
        examples = _fixture()["source_examples"]
        categories = Counter(case["category"] for case in examples)

        self.assertEqual(len(examples), 30)
        self.assertEqual(len({case["id"] for case in examples}), 30)
        self.assertTrue(all(case["source_anchor"] for case in examples))
        self.assertEqual(categories["classical_case"], 10)
        self.assertEqual(categories["trigram_remainder"], 8)
        self.assertEqual(categories["moving_remainder"], 6)
        self.assertEqual(categories["method_formula"], 6)
        classical = [case for case in examples if case["category"] == "classical_case"]
        self.assertTrue(all(case["source_contract"] for case in classical))

    def test_audit_rejects_provider_fixture_and_contract_sync_mutation(self) -> None:
        fixture = _fixture()
        case = fixture["source_examples"][0]
        case["input"]["upper_total"] += 1
        recalculated = cast_from_totals(**case["input"])
        case["expected"] = {
            "primary": recalculated["primary_hexagram"]["name"],
            "mutual": recalculated["mutual_hexagram"]["name"],
            "changed": recalculated["changed_hexagram"]["name"],
            "moving_line": recalculated["moving_line"],
        }
        case["source_contract"]["input"] = copy.deepcopy(case["input"])
        case["source_contract"]["expected"] = copy.deepcopy(case["expected"])

        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "meihua-mutated.yaml"
            mutated.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_meihua_provider.audit_meihua_provider(
                fixture_path=mutated
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "classical source-derived input mismatch: classical-guanmei",
            report["source_verification"]["findings"],
        )

    def test_calendar_fixtures_cover_required_boundaries_and_seasons(self) -> None:
        cases = _fixture()["calendar_boundaries"]
        categories = Counter(case["category"] for case in cases)

        self.assertGreaterEqual(categories["solar_term_boundary"], 2)
        self.assertGreaterEqual(categories["day_rollover"], 2)
        self.assertGreaterEqual(categories["leap_month"], 1)
        self.assertGreaterEqual(categories["timezone_boundary"], 2)
        for case in cases:
            with self.subTest(case=case["id"]):
                calendar = calendar_core.normalize_calendar(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location=case["location"],
                    zi_hour_policy=case["zi_hour_policy"],
                )
                self.assertEqual(
                    [calendar["ganzhi"][key] for key in ("year", "month", "day", "hour")],
                    case["expected_pillars"],
                )
                self.assertEqual(
                    [
                        calendar["lunar_date"]["year"],
                        calendar["lunar_date"]["month"],
                        calendar["lunar_date"]["day"],
                        calendar["lunar_date"]["is_leap_month"],
                    ],
                    case["expected_lunar"],
                )
                facts = build_from_method(
                    {"casting_method": "time"}, calendar_facts=calendar
                )["output"]
                expected_cast = case["expected_time_cast"]
                self.assertEqual(
                    facts["casting"]["inputs"]["lunar_year"],
                    case["expected_lunar"][0],
                )
                self.assertEqual(
                    facts["casting"]["inputs"]["year_branch_number"],
                    (case["expected_lunar"][0] - 4) % 12 + 1,
                )
                self.assertEqual(facts["totals"], expected_cast["totals"])
                self.assertEqual(
                    facts["primary_hexagram"]["name"], expected_cast["primary"]
                )
                self.assertEqual(
                    facts["changed_hexagram"]["name"], expected_cast["changed"]
                )
                self.assertEqual(facts["moving_line"], expected_cast["moving_line"])

    def test_all_thirty_examples_reproduce_complete_plates(self) -> None:
        for case in _fixture()["source_examples"]:
            with self.subTest(case=case["id"]):
                plate = cast_from_totals(**case["input"])
                expected = case["expected"]
                self.assertEqual(plate["primary_hexagram"]["name"], expected["primary"])
                self.assertEqual(plate["changed_hexagram"]["name"], expected["changed"])
                self.assertEqual(plate["moving_line"], expected["moving_line"])
                if "mutual" in expected:
                    self.assertEqual(plate["mutual_hexagram"]["name"], expected["mutual"])
                self.assertEqual(len(plate["primary_hexagram"]["lines_bottom_up"]), 6)
                self.assertEqual(len(plate["changed_hexagram"]["lines_bottom_up"]), 6)


class MeihuaPlateCalculationTests(unittest.TestCase):
    def test_remainder_zero_maps_to_kun_and_sixth_line(self) -> None:
        plate = cast_from_totals(
            upper_total=8,
            lower_total=16,
            moving_total=12,
        )

        self.assertEqual(trigram_for_number(8)["name"], "坤")
        self.assertEqual(trigram_for_number(16)["name"], "坤")
        self.assertEqual(plate["moving_line"], 6)
        self.assertEqual(plate["primary_hexagram"]["name"], "坤为地")

    def test_every_trigram_and_moving_remainder_boundary(self) -> None:
        expected_trigrams = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        for number in range(1, 65):
            with self.subTest(number=number):
                self.assertEqual(
                    trigram_for_number(number)["name"],
                    expected_trigrams[(number - 1) % 8],
                )
        for total in range(1, 49):
            with self.subTest(moving_total=total):
                self.assertEqual(
                    cast_from_totals(upper_total=1, lower_total=1, moving_total=total)["moving_line"],
                    (total - 1) % 6 + 1,
                )

    def test_all_384_single_line_changes_cover_all_hexagrams(self) -> None:
        catalog = build_hexagram_catalog()
        self.assertEqual(len(catalog), 64)
        for primary in catalog.values():
            for moving_line in range(1, 7):
                with self.subTest(primary=primary["name"], moving_line=moving_line):
                    plate = cast_from_totals(
                        upper_total=primary["upper_number"],
                        lower_total=primary["lower_number"],
                        moving_total=moving_line,
                    )
                    expected_bits = list(primary["lines_bottom_up"])
                    expected_bits[moving_line - 1] = 1 - expected_bits[moving_line - 1]
                    self.assertEqual(plate["primary_hexagram"]["name"], primary["name"])
                    self.assertEqual(plate["changed_hexagram"]["lines_bottom_up"], expected_bits)
                    self.assertNotEqual(plate["changed_hexagram"]["name"], primary["name"])

    def test_mutual_extraction_and_pure_qian_kun_exception_are_explicit(self) -> None:
        ordinary = cast_from_totals(upper_total=2, lower_total=3, moving_total=1)
        self.assertEqual(
            ordinary["mutual_hexagram"]["lines_bottom_up"],
            [0, 1, 1, 1, 1, 1],
        )
        self.assertEqual(ordinary["mutual_hexagram"]["source_plate"], "primary")

        qian = cast_from_totals(upper_total=1, lower_total=1, moving_total=1)
        kun = cast_from_totals(upper_total=8, lower_total=8, moving_total=6)
        self.assertEqual(qian["mutual_hexagram"]["source_plate"], "changed")
        self.assertEqual(kun["mutual_hexagram"]["source_plate"], "changed")
        self.assertEqual(qian["mutual_hexagram"]["exception_profile"], "pure_qian_kun")

    def test_body_use_relation_is_calculated_without_a_verdict(self) -> None:
        lower_use = cast_from_totals(upper_total=2, lower_total=3, moving_total=1)
        upper_use = cast_from_totals(upper_total=2, lower_total=3, moving_total=5)

        self.assertEqual(lower_use["body_use"]["body"]["position"], "upper")
        self.assertEqual(lower_use["body_use"]["use"]["position"], "lower")
        self.assertEqual(lower_use["body_use"]["relation"], "用克体")
        self.assertEqual(upper_use["body_use"]["body"]["position"], "lower")
        self.assertEqual(upper_use["body_use"]["use"]["position"], "upper")
        self.assertEqual(upper_use["body_use"]["status"], "calculated_relation_not_verdict")

    def test_mutual_and_changed_trigrams_have_body_relations_without_model_arithmetic(self) -> None:
        plate = cast_from_totals(upper_total=2, lower_total=3, moving_total=1)
        relations = plate["body_relation_facts"]

        self.assertEqual(len(relations), 5)
        self.assertEqual(
            {(row["source_plate"], row["position"]) for row in relations},
            {
                ("primary_use", "lower"),
                ("mutual", "lower"),
                ("mutual", "upper"),
                ("changed", "lower"),
                ("changed", "upper"),
            },
        )
        self.assertTrue(
            all(
                row["status"] == "calculated_relation_not_verdict"
                for row in relations
            )
        )

    def test_seasonal_strength_table_covers_all_month_branches(self) -> None:
        expected = {
            "寅": {"震": "旺", "坤": "衰"},
            "卯": {"巽": "旺", "艮": "衰"},
            "辰": {"坤": "旺", "坎": "衰"},
            "巳": {"离": "旺", "乾": "衰"},
            "午": {"离": "旺", "兑": "衰"},
            "未": {"艮": "旺", "坎": "衰"},
            "申": {"乾": "旺", "震": "衰"},
            "酉": {"兑": "旺", "巽": "衰"},
            "戌": {"坤": "旺", "坎": "衰"},
            "亥": {"坎": "旺", "离": "衰"},
            "子": {"坎": "旺", "离": "衰"},
            "丑": {"艮": "旺", "坎": "衰"},
        }
        for branch, cases in expected.items():
            for trigram, state in cases.items():
                with self.subTest(branch=branch, trigram=trigram):
                    self.assertEqual(seasonal_strength_for(trigram, branch)["state"], state)


class MeihuaMethodTests(unittest.TestCase):
    def test_time_method_consumes_shared_lunar_and_ganzhi_calendar(self) -> None:
        facts = build_from_method(
            {"casting_method": "time"},
            calendar_facts=_calendar(),
        )
        output = facts["output"]

        self.assertEqual(output["casting"]["inputs"]["year_branch_number"], 5)
        self.assertEqual(output["casting"]["inputs"]["lunar_month"], 1)
        self.assertEqual(output["casting"]["inputs"]["lunar_day"], 1)
        self.assertEqual(output["casting"]["inputs"]["hour_branch_number"], 7)
        self.assertEqual(output["primary_hexagram"]["name"], "山水蒙")
        self.assertEqual(output["changed_hexagram"]["name"], "山地剥")
        self.assertEqual(output["moving_line"], 2)
        self.assertEqual(output["seasonal_strength"]["body"]["state"], "衰")

    def test_time_method_uses_lunar_year_branch_across_lichun_new_year_gap(self) -> None:
        before_lichun = build_from_method(
            {"casting_method": "time"},
            calendar_facts=_calendar("2024-02-04T16:20:00"),
        )["output"]
        after_lichun = build_from_method(
            {"casting_method": "time"},
            calendar_facts=_calendar("2024-02-04T16:40:00"),
        )["output"]

        self.assertEqual(
            before_lichun["casting"]["inputs"]["lunar_year"], 2023
        )
        self.assertEqual(
            after_lichun["casting"]["inputs"]["lunar_year"], 2023
        )
        self.assertEqual(
            before_lichun["casting"]["inputs"]["year_branch_number"], 4
        )
        self.assertEqual(
            after_lichun["casting"]["inputs"]["year_branch_number"], 4
        )
        self.assertEqual(
            before_lichun["primary_hexagram"], after_lichun["primary_hexagram"]
        )

    def test_supplied_number_uses_number_and_calculated_hour_only(self) -> None:
        facts = build_from_method(
            {
                "casting_method": "supplied_number",
                "number": 9,
                "provenance": {"kind": "user_supplied_number"},
            },
            calendar_facts=_calendar(),
        )["output"]

        self.assertEqual(facts["primary_hexagram"]["name"], "天山遯")
        self.assertEqual(facts["changed_hexagram"]["name"], "风山渐")
        self.assertEqual(facts["moving_line"], 4)
        self.assertEqual(facts["casting_method"], "supplied_number")

    def test_sound_count_requires_observation_provenance(self) -> None:
        facts = build_from_method(
            {
                "casting_method": "sound_count",
                "count": 5,
                "observation_source": {"kind": "heard_count", "counted_once": True},
            },
            calendar_facts=_calendar(),
        )["output"]

        self.assertEqual(facts["primary_hexagram"]["name"], "风山渐")
        self.assertEqual(facts["changed_hexagram"]["name"], "水山蹇")
        self.assertEqual(facts["moving_line"], 6)

    def test_observation_requires_caller_classified_trigrams(self) -> None:
        facts = build_from_method(
            {
                "casting_method": "observation",
                "upper_trigram": "乾",
                "lower_trigram": "巽",
                "observation_source": {
                    "kind": "caller_classified_observation",
                    "upper_basis": "structured-visible-feature",
                    "lower_basis": "measured-direction",
                },
            },
            calendar_facts=_calendar(),
        )["output"]

        self.assertEqual(facts["primary_hexagram"]["name"], "天风姤")
        self.assertEqual(facts["changed_hexagram"]["name"], "乾为天")
        self.assertEqual(facts["moving_line"], 1)
        self.assertFalse(facts["casting"]["natural_language_classification"])

    def test_supplied_hexagram_preserves_exact_plate_and_moving_line(self) -> None:
        facts = build_from_method(
            {
                "casting_method": "supplied_hexagram",
                "upper_trigram": "兑",
                "lower_trigram": "离",
                "moving_line": 1,
                "provenance": {"kind": "user_supplied_complete_hexagram"},
            },
            calendar_facts=_calendar(),
        )["output"]

        self.assertEqual(facts["primary_hexagram"]["name"], "泽火革")
        self.assertEqual(facts["mutual_hexagram"]["name"], "天风姤")
        self.assertEqual(facts["changed_hexagram"]["name"], "泽山咸")
        self.assertEqual(facts["moving_line"], 1)

    def test_missing_unknown_or_implicit_methods_fail_closed(self) -> None:
        invalid = (
            {},
            {"casting_method": "random"},
            {"casting_method": "supplied_number"},
            {"casting_method": "sound_count", "count": 3},
            {"casting_method": "observation", "description": "一只鸟从东边飞来"},
            {"casting_method": "supplied_hexagram", "upper_trigram": "乾"},
        )
        for method in invalid:
            with self.subTest(method=method):
                with self.assertRaises(ValueError):
                    build_from_method(method, calendar_facts=_calendar())

    def test_complete_method_rejects_unconsumed_or_conflicting_fields(self) -> None:
        invalid = {
            "casting_method": "observation",
            "upper_trigram": "乾",
            "lower_trigram": "巽",
            "observation_source": {"kind": "caller_classified_observation"},
            "description": "这段自然语言不得被程序暗中分类",
        }

        with self.assertRaisesRegex(ValueError, "unsupported fields: description"):
            build_from_method(invalid, calendar_facts=_calendar())

    def test_identical_structured_input_has_identical_fact_digest(self) -> None:
        method = {
            "casting_method": "supplied_number",
            "number": 17,
            "provenance": {"kind": "repeatability_fixture"},
        }

        first = build_from_method(method, calendar_facts=_calendar())
        second = build_from_method(copy.deepcopy(method), calendar_facts=_calendar())

        self.assertEqual(first["fact_digest"], second["fact_digest"])
        self.assertEqual(first["output"], second["output"])

    def test_validator_recomputes_and_rejects_tampered_mutual_plate(self) -> None:
        facts = build_from_method(
            {
                "casting_method": "supplied_hexagram",
                "upper_trigram": "兑",
                "lower_trigram": "离",
                "moving_line": 1,
                "provenance": {"kind": "fixture"},
            },
            calendar_facts=_calendar(),
        )
        self.assertTrue(validate_fact_layer(facts)["ok"])

        tampered = copy.deepcopy(facts)
        tampered["output"]["mutual_hexagram"]["name"] = "乾为天"
        report = validate_fact_layer(tampered)
        self.assertFalse(report["ok"])
        self.assertIn("meihua_fact_digest_mismatch", report["codes"])


class MeihuaProviderTests(unittest.TestCase):
    def test_provider_binds_shared_calendar_and_stays_separate_from_liuyao(self) -> None:
        result = MeihuaProvider(ROOT).calculate(_request())
        output = result.facts["chart_facts"]["output"]

        self.assertEqual(result.system, "meihua")
        self.assertEqual(result.provider_id, "mingli-master.meihua.v1")
        self.assertRegex(result.facts["calendar_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(output["system_identity"], "meihua-yishu")
        self.assertNotIn("najia", output)
        self.assertNotIn("six_relatives", output)

    def test_refine_preserves_plate_but_refreshes_result_identity(self) -> None:
        provider = MeihuaProvider(ROOT)
        base = provider.calculate(_request())
        refined = provider.refine(_request(query="只追问体用关系"), base)

        self.assertEqual(refined.facts["fact_digest"], base.facts["fact_digest"])
        self.assertNotEqual(refined.result_hash, base.result_hash)

    def test_provider_does_not_claim_uncalculated_future_horizons(self) -> None:
        provider = MeihuaProvider(ROOT)
        base = provider.calculate(_request())

        instant = provider.extend(base, ("outcome", "state"), {"kind": "instant"})
        instant_timing = provider.extend(base, ("timing",), {"kind": "instant"})
        future = provider.extend(base, ("timing",), {"kind": "day"})

        self.assertEqual(instant.fact_extension.status, "complete")
        self.assertEqual(instant_timing.fact_extension.status, "unsupported")
        self.assertEqual(
            instant_timing.fact_extension.unsupported_dimensions, ("timing",)
        )
        self.assertEqual(future.fact_extension.status, "unsupported")
        self.assertEqual(future.fact_extension.unsupported_dimensions, ("timing",))

    def test_recast_without_new_method_facts_does_not_inherit_old_plate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["meihua"].descriptor
            first_turn = engine.prepare_turn(descriptor, _turn_request())
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "梅花卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)

            recast = engine.prepare_turn(
                descriptor,
                _turn_request(
                    include_default_chart=False, query="另一件事重新起梅花卦"
                ),
                state_token=first_turn.state_token,
                transition="restart",
            )

            self.assertIsInstance(recast.result, NeedUserFact)
            self.assertEqual(recast.result.system, "meihua")
            self.assertEqual(recast.result.missing_facts, ("casting_method",))

            resumed = engine.prepare_turn(
                descriptor,
                _turn_request(
                    {
                        "casting_method": "supplied_number",
                        "number": 17,
                        "provenance": {"kind": "user_supplied_number"},
                    },
                    query="改用数字起卦",
                ),
                state_token=recast.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading)
            self.assertEqual(resumed.result.action, "recast")
            self.assertEqual(resumed.result.parent_reading_id, first.reading_id)
            self.assertEqual(resumed.result.root_reading_id, first.reading_id)
            resumed_internal = engine.store.load_prepared(resumed.result.reading_id)
            self.assertEqual(
                resumed_internal.calculation.facts["chart_facts"]["output"][
                    "casting_method"
                ],
                "supplied_number",
            )

    def test_initial_missing_method_intake_resumes_from_named_structured_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["meihua"].descriptor
            pending = engine.prepare_turn(
                descriptor, _turn_request(include_default_chart=False)
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertEqual(pending.result.missing_facts, ("casting_method",))

            resumed = engine.prepare_turn(
                descriptor,
                _turn_request(
                    {
                        "casting_method": "supplied_number",
                        "number": 9,
                        "provenance": {"kind": "user_supplied_number"},
                    },
                    query="数字起卦",
                ),
                state_token=pending.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading)

    def test_capability_factory_and_missing_inputs_use_real_provider(self) -> None:
        capability = PROVIDER_CAPABILITIES["meihua"]
        self.assertEqual(capability.mode, "calculation")
        self.assertEqual(capability.dimensions, ("outcome", "state"))
        self.assertEqual(missing_required_inputs("meihua", _request()), ())
        missing = missing_required_inputs(
            "meihua",
            _request(chart_data={"casting_method": "observation"}),
        )
        self.assertIn("upper_trigram", missing)
        self.assertIn("observation_source", missing)

        engine = build_production_engine(
            skill_dir=ROOT,
            store_root=ROOT / ".work" / "task7g-test-store",
        )
        self.assertIsInstance(engine.providers["meihua"], MeihuaProvider)
        self.assertNotIn("meihua", STRUCTURED_SYSTEMS)

    def test_source_plan_requires_complete_meihua_fact_contract(self) -> None:
        result = MeihuaProvider(ROOT).calculate(_request())
        plan = reading_source_plan.compile_source_plan(
            "meihua",
            {"requested_dimensions": ["outcome", "state"]},
            result.indexed_facts(),
        )

        self.assertEqual(
            plan["required_packs"],
            [
                "divination/meihua-yishu",
                "divination/zhouyi-zhezhong",
                "divination/huangji-jingshi",
            ],
        )
        self.assertTrue(all(row["satisfied"] for row in plan["applicability_conditions"]), plan)


if __name__ == "__main__":
    unittest.main()
