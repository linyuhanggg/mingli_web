"""Task 7F regressions for the deterministic Liuyao provider."""

from __future__ import annotations

import copy
import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import yaml

import audit_liuyao_provider
import reading_source_plan
from reading_engine import calendar_core, liuyao as liuyao_engine
from reading_engine.contracts import (
    AcceptedReading,
    InternalFailure,
    NeedUserFact,
    PreparedReading,
    ReadingRequest,
    canonical_digest,
)
from reading_engine.factory import build_production_engine
from reading_engine.liuyao import (
    JIAZI,
    build_fact_layer,
    build_hexagram_catalog,
    calculate_line_relations,
    cast_from_seed,
    public_projection,
    six_spirits_for,
    validate_fact_layer,
    xunkong_for,
)
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import LiuyaoProvider, STRUCTURED_SYSTEMS
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "liuyao-v51.yaml"
ALGORITHM_SAMPLES = (
    ROOT / "references" / "fixtures" / "algorithm-source-samples-v51.yaml"
)
RELATIVES = {"兄弟", "子孙", "妻财", "官鬼", "父母"}
TRANSACTION_CAST_SEED_KEY = "_transaction_liuyao_cast_seed_v1"


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _calendar() -> dict:
    return calendar_core.normalize_calendar(
        "2024-02-10T12:00:00",
        timezone_name="Asia/Shanghai",
        location="上海",
    )


def _calendar_for_classical_case(case: dict) -> dict:
    calendar = _calendar()
    calendar["ganzhi"]["month"] = next(
        ganzhi for ganzhi in JIAZI if ganzhi[1] == case["month_branch"]
    )
    calendar["ganzhi"]["day"] = case["day_ganzhi"]
    digest = calendar_core.calendar_digest(calendar)
    calendar["calendar_digest"] = digest
    calendar["digest"] = digest
    return calendar


def _request(**changes: object) -> ReadingRequest:
    payload = {
        "query": "按六爻核对这件事",
        "action": "new",
        "system": "liuyao",
        "reading_id": "reading-liuyao-fixture-001",
        "intent": {
            "subject_refs": ["self"],
            "calculation_object": "concrete_event",
            "question_dimensions": ["outcome", "timing"],
            "horizon": {"kind": "instant"},
            "requested_granularity": "instant",
            "evidence_questions": ["此卦的用神候选与动变关系如何"],
            "requested_method": "liuyao",
            "continuity": {
                "reading_id": None,
                "same_subject": False,
                "same_event": False,
            },
            "facts_present": ["cast", "event_datetime", "timezone", "location"],
            "facts_corrected": [],
        },
        "chart_data": {"tosses": [9, 7, 7, 7, 7, 6]},
        "event_datetime": "2024-02-10T12:00:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    payload.update(changes)
    return ReadingRequest(**payload)


def _turn_request(
    cast: object = (9, 7, 7, 7, 7, 6),
    *,
    query: str = "按六爻核对这件事",
) -> ProviderRequest:
    facts: dict[str, object] = {
        "event_datetime": "2024-02-10T12:00:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    if cast is not None:
        facts["cast"] = list(cast) if isinstance(cast, tuple) else cast
    return ProviderRequest(
        query=query,
        subject_refs=("current_user",),
        object_id="concrete_event",
        dimension_ids=("outcome",),
        horizon={"kind": "instant", "start": None, "end": None},
        facts={"current_user": facts},
    )


def _internal_digital_request(seed: str, **changes: object) -> ReadingRequest:
    metadata = dict(changes.pop("metadata", {}) or {})
    metadata[TRANSACTION_CAST_SEED_KEY] = seed
    return _request(
        chart_data={"casting_method": "digital_coin"},
        metadata=metadata,
        **changes,
    )


def _stable_tosses(case: dict) -> list[int]:
    bits = {
        "乾": "111", "兑": "110", "离": "101", "震": "100",
        "巽": "011", "坎": "010", "艮": "001", "坤": "000",
    }
    return [
        7 if bit == "1" else 8
        for bit in bits[case["lower"]] + bits[case["upper"]]
    ]


class LiuyaoFixtureContractTests(unittest.TestCase):
    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_liuyao_provider.audit_liuyao_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["hexagrams"], 64)
        self.assertGreaterEqual(report["counts"]["complete_reference_cases"], 30)
        self.assertEqual(report["counts"]["source_table_cases"], 64)
        self.assertGreaterEqual(report["counts"]["calendar_boundary_cases"], 7)
        self.assertEqual(report["counts"]["day_stem_boundaries"], 10)
        self.assertEqual(report["counts"]["xunkong_boundaries"], 6)
        self.assertEqual(report["findings"], [])

    def test_thirty_classical_examples_are_source_anchored_complete_casts(self) -> None:
        fixture = _fixture()
        source = fixture["classical_examples_source"]
        cases = fixture["classical_examples"]

        self.assertEqual(
            source["path"],
            "references/fulltext/divination/zengshan-buyi/fulltext.md",
        )
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(len(cases), 30)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertRegex(case["source_anchor"], r"^L\d+-L\d+$")
                self.assertTrue(case["source_heading"])
                self.assertIn(case["month_branch"], "子丑寅卯辰巳午未申酉戌亥")
                self.assertIn(case["day_ganzhi"], JIAZI)
                self.assertEqual(len(case["tosses"]), 6)
                self.assertTrue(all(value in {6, 7, 8, 9} for value in case["tosses"]))

        expectations = fixture["classical_fact_expectations"]
        self.assertEqual(set(expectations), {case["id"] for case in cases})
        for case_id, expected in expectations.items():
            with self.subTest(case=case_id):
                self.assertEqual(len(expected["source_lines_bottom_up"]), 6)
                self.assertTrue(
                    all(len(line) == 9 for line in expected["source_lines_bottom_up"])
                )
                self.assertEqual(len(expected["seasonal_states_bottom_up"]), 6)
                self.assertEqual(len(expected["month_relations_bottom_up"]), 6)
                self.assertEqual(len(expected["day_relations_bottom_up"]), 6)
                self.assertEqual(len(expected["xunkong"]), 2)
                self.assertEqual(len(expected["changed_xunkong_bottom_up"]), 6)
                self.assertEqual(
                    len(expected["changed_seasonal_states_bottom_up"]), 6
                )
                self.assertEqual(
                    len(expected["changed_month_relations_bottom_up"]), 6
                )
                self.assertEqual(
                    len(expected["changed_day_relations_bottom_up"]), 6
                )

    def test_classical_examples_reproduce_their_recorded_main_change_and_moving_lines(self) -> None:
        for case in _fixture()["classical_examples"]:
            with self.subTest(case=case["id"]):
                output = build_fact_layer(
                    case["tosses"],
                    calendar_facts=_calendar_for_classical_case(case),
                    casting={"method": "supplied_complete_cast"},
                )["output"]
                self.assertEqual(output["primary_hexagram"]["name"], case["primary"])
                self.assertEqual(output["changed_hexagram"]["name"], case["changed"])
                self.assertEqual(output["moving_lines"], case["moving_lines"])
                expected = _fixture()["classical_fact_expectations"][case["id"]]
                self.assertEqual(
                    [line["six_relative"] for line in output["lines"]],
                    [line[0] for line in expected["source_lines_bottom_up"]],
                )
                self.assertEqual(
                    [line["najia"]["element"] for line in output["lines"]],
                    [line[2] for line in expected["source_lines_bottom_up"]],
                )
                self.assertEqual(
                    [line["roles"] for line in output["lines"]],
                    [
                        [] if line[4] is None else [line[4]]
                        for line in expected["source_lines_bottom_up"]
                    ],
                )
                self.assertEqual(
                    [line["najia"]["branch"] for line in output["lines"]],
                    [line[1] for line in expected["source_lines_bottom_up"]],
                )
                self.assertEqual(
                    [line["six_relative"] for line in output["changed_plate_lines"]],
                    [line[5] for line in expected["source_lines_bottom_up"]],
                )
                self.assertEqual(
                    [line["najia"]["branch"] for line in output["changed_plate_lines"]],
                    [line[6] for line in expected["source_lines_bottom_up"]],
                )
                self.assertEqual(
                    [line["najia"]["element"] for line in output["changed_plate_lines"]],
                    [line[7] for line in expected["source_lines_bottom_up"]],
                )
                self.assertEqual(
                    [line["yin_yang"] for line in output["changed_plate_lines"]],
                    [
                        "阳" if line[8] in {"○", "⚊"} else "阴"
                        for line in expected["source_lines_bottom_up"]
                    ],
                )
                self.assertEqual(
                    [line["xunkong"] for line in output["changed_plate_lines"]],
                    expected["changed_xunkong_bottom_up"],
                )
                self.assertEqual(
                    [
                        line["month_day_strength"]["seasonal_state"]
                        for line in output["changed_plate_lines"]
                    ],
                    expected["changed_seasonal_states_bottom_up"],
                )
                self.assertEqual(
                    [
                        line["month_day_strength"]["month"]["branch_relation"]
                        for line in output["changed_plate_lines"]
                    ],
                    expected["changed_month_relations_bottom_up"],
                )
                self.assertEqual(
                    [
                        line["month_day_strength"]["day"]["branch_relation"]
                        for line in output["changed_plate_lines"]
                    ],
                    expected["changed_day_relations_bottom_up"],
                )
                self.assertEqual(output["xunkong"]["void_branches"], expected["xunkong"])
                self.assertEqual(
                    [line["month_day_strength"]["seasonal_state"] for line in output["lines"]],
                    expected["seasonal_states_bottom_up"],
                )
                self.assertEqual(
                    [line["month_day_strength"]["month"]["branch_relation"] for line in output["lines"]],
                    expected["month_relations_bottom_up"],
                )
                self.assertEqual(
                    [line["month_day_strength"]["day"]["branch_relation"] for line in output["lines"]],
                    expected["day_relations_bottom_up"],
                )

    def test_audit_rejects_mutated_classical_cast_without_research_root(self) -> None:
        fixture = _fixture()
        fixture["classical_examples"][0]["tosses"][0] = 7
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "liuyao-mutated.yaml"
            path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_liuyao_provider.audit_liuyao_provider(
                fixture_path=path
            )

        self.assertFalse(report["provider_ready"])
        self.assertEqual(report["source_verification"]["status"], "skipped")
        self.assertNotIn("findings", report["source_verification"])
        self.assertTrue(
            {
                "Liuyao fixture artifact hash mismatch",
                "classical changed mismatch: zengshan-01",
                "classical moving-line mismatch: zengshan-01",
            }.issubset(report["findings"]),
            report["findings"],
        )

    def test_audit_rejects_mutated_changed_plate_strength_expectation(self) -> None:
        fixture = _fixture()
        expected = fixture["classical_fact_expectations"]["zengshan-01"]
        expected["changed_seasonal_states_bottom_up"][0] = "旺"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "liuyao-mutated.yaml"
            path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_liuyao_provider.audit_liuyao_provider(
                fixture_path=path
            )

        self.assertFalse(report["provider_ready"])
        self.assertTrue(
            any("changed seasonal" in item for item in report["findings"]),
            report,
        )

    def test_changed_line_hidden_suppression_sample_is_consumed_exactly(self) -> None:
        samples = yaml.safe_load(ALGORITHM_SAMPLES.read_text(encoding="utf-8"))
        sample = samples["cases"]["liuyao-changed-line-suppresses-hidden"]
        output = build_fact_layer(
            sample["input"]["tosses_bottom_up"],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        expected = sample["expected"]

        self.assertEqual(output["primary_hexagram"]["name"], sample["input"]["main"])
        self.assertEqual(output["changed_hexagram"]["name"], sample["input"]["changed"])
        self.assertEqual(output["moving_lines"], expected["moving_lines"])
        self.assertEqual(
            output["changed_plate_lines"][3]["najia"]["ganzhi"],
            expected["line_4_changed"]["stem_branch"],
        )
        self.assertEqual(
            output["changed_plate_lines"][3]["six_relative"],
            expected["line_4_changed"]["six_relative"],
        )
        self.assertNotIn(
            expected["hidden_relative_excluded"],
            {line["six_relative"] for line in output["hidden_lines"]},
        )

    def test_fixture_contains_required_calendar_boundary_families(self) -> None:
        cases = _fixture()["calendar_boundary_cases"]
        categories = [case["category"] for case in cases]

        self.assertGreaterEqual(categories.count("solar_term_boundary"), 2)
        self.assertGreaterEqual(categories.count("day_rollover"), 2)
        self.assertGreaterEqual(categories.count("leap_month"), 1)
        self.assertGreaterEqual(categories.count("timezone_boundary"), 2)
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
                facts = build_fact_layer(
                    [7, 7, 7, 7, 7, 7],
                    calendar_facts=calendar,
                    casting={"method": "supplied_complete_cast"},
                )
                self.assertTrue(validate_fact_layer(facts)["ok"])

    def test_fixture_covers_all_sixty_four_source_table_hexagrams(self) -> None:
        cases = _fixture()["hexagram_reference_cases"]

        self.assertEqual(len(cases), 64)
        self.assertEqual(len({case["name"] for case in cases}), 64)
        self.assertEqual(len({(case["upper"], case["lower"]) for case in cases}), 64)

    def test_all_reference_cases_build_complete_source_bound_plates(self) -> None:
        catalog = build_hexagram_catalog()
        for case in _fixture()["hexagram_reference_cases"]:
            with self.subTest(hexagram=case["name"]):
                facts = build_fact_layer(
                    _stable_tosses(case),
                    calendar_facts=_calendar(),
                    casting={"method": "supplied_complete_cast"},
                )
                output = facts["output"]
                self.assertEqual(output["primary_hexagram"]["name"], case["name"])
                self.assertEqual(output["primary_hexagram"]["palace"], case["palace"])
                self.assertEqual(output["primary_hexagram"]["stage"], case["stage"])
                self.assertEqual(output["shi_ying"], {"shi": case["shi"], "ying": case["ying"]})
                self.assertEqual(len(output["lines"]), 6)
                self.assertTrue(all(line["najia"] for line in output["lines"]))
                self.assertEqual(catalog[case["name"]]["king_wen_number"], output["primary_hexagram"]["king_wen_number"])


class LiuyaoCalculationTests(unittest.TestCase):
    def test_qian_najia_shi_ying_relatives_and_six_spirits(self) -> None:
        facts = build_fact_layer(
            [7, 7, 7, 7, 7, 7],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )
        output = facts["output"]

        self.assertEqual(output["primary_hexagram"]["name"], "乾为天")
        self.assertEqual(output["shi_ying"], {"shi": 6, "ying": 3})
        self.assertEqual(
            [line["najia"]["ganzhi"] for line in output["lines"]],
            ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"],
        )
        self.assertEqual(
            [line["six_spirit"] for line in output["lines"]],
            six_spirits_for(output["calendar"]["day_stem"]),
        )
        self.assertEqual({line["six_relative"] for line in output["lines"]}, RELATIVES)

    def test_moving_lines_main_and_changed_hexagrams_are_exact(self) -> None:
        facts = build_fact_layer(
            [9, 7, 7, 7, 7, 6],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]

        self.assertEqual(facts["primary_hexagram"]["name"], "泽天夬")
        self.assertEqual(facts["changed_hexagram"]["name"], "天风姤")
        self.assertEqual(facts["moving_lines"], [1, 6])
        self.assertEqual(facts["casting_method"], "supplied_complete_cast")

    def test_all_moving_line_boundary_fixtures_match(self) -> None:
        for case in _fixture()["moving_boundaries"]:
            with self.subTest(case=case["id"]):
                output = build_fact_layer(
                    case["tosses"],
                    calendar_facts=_calendar(),
                    casting={"method": "supplied_complete_cast"},
                )["output"]
                self.assertEqual(output["moving_lines"], case["moving_lines"])
                self.assertEqual(output["primary_hexagram"]["name"], case["primary"])
                self.assertEqual(output["changed_hexagram"]["name"], case["changed"])

    def test_every_single_line_change_of_all_sixty_four_hexagrams_is_exact(self) -> None:
        cases = _fixture()["hexagram_reference_cases"]
        trigram_bits = {
            "乾": "111", "兑": "110", "离": "101", "震": "100",
            "巽": "011", "坎": "010", "艮": "001", "坤": "000",
        }
        trigram_by_bits = {bits: name for name, bits in trigram_bits.items()}
        name_by_pair = {
            (case["upper"], case["lower"]): case["name"] for case in cases
        }
        for case in cases:
            stable = _stable_tosses(case)
            primary_bits = trigram_bits[case["lower"]] + trigram_bits[case["upper"]]
            for line in range(1, 7):
                with self.subTest(hexagram=case["name"], line=line):
                    tosses = list(stable)
                    tosses[line - 1] = 9 if tosses[line - 1] == 7 else 6
                    changed_bits = list(primary_bits)
                    changed_bits[line - 1] = "0" if changed_bits[line - 1] == "1" else "1"
                    expected = name_by_pair[
                        (
                            trigram_by_bits["".join(changed_bits[3:])],
                            trigram_by_bits["".join(changed_bits[:3])],
                        )
                    ]
                    output = build_fact_layer(
                        tosses,
                        calendar_facts=_calendar(),
                        casting={"method": "supplied_complete_cast"},
                    )["output"]
                    self.assertEqual(output["primary_hexagram"]["name"], case["name"])
                    self.assertEqual(output["changed_hexagram"]["name"], expected)
                    self.assertEqual(output["moving_lines"], [line])

    def test_every_hexagram_single_line_change_reaches_the_frozen_target(self) -> None:
        cases = _fixture()["hexagram_reference_cases"]
        bits = {
            "乾": "111", "兑": "110", "离": "101", "震": "100",
            "巽": "011", "坎": "010", "艮": "001", "坤": "000",
        }
        by_bits = {
            bits[case["lower"]] + bits[case["upper"]]: case["name"]
            for case in cases
        }
        for case in cases:
            primary_bits = bits[case["lower"]] + bits[case["upper"]]
            for line in range(1, 7):
                changed_bits = list(primary_bits)
                changed_bits[line - 1] = "0" if changed_bits[line - 1] == "1" else "1"
                tosses = [7 if bit == "1" else 8 for bit in primary_bits]
                tosses[line - 1] = 9 if primary_bits[line - 1] == "1" else 6
                with self.subTest(hexagram=case["name"], line=line):
                    output = build_fact_layer(
                        tosses,
                        calendar_facts=_calendar(),
                        casting={"method": "supplied_complete_cast"},
                    )["output"]
                    self.assertEqual(output["primary_hexagram"]["name"], case["name"])
                    self.assertEqual(output["moving_lines"], [line])
                    self.assertEqual(
                        output["changed_hexagram"]["name"],
                        by_bits["".join(changed_bits)],
                    )

    def test_xunkong_covers_all_six_jia_cycles(self) -> None:
        expected = {
            "甲子": ["戌", "亥"], "甲戌": ["申", "酉"],
            "甲申": ["午", "未"], "甲午": ["辰", "巳"],
            "甲辰": ["寅", "卯"], "甲寅": ["子", "丑"],
        }
        for day, branches in expected.items():
            self.assertEqual(xunkong_for(day), branches)
        self.assertEqual(xunkong_for("癸酉"), ["戌", "亥"])

        rows = list(expected.values())
        for index, day in enumerate(JIAZI):
            with self.subTest(day=day):
                self.assertEqual(xunkong_for(day), rows[index // 10])

    def test_six_spirits_cover_all_ten_day_stems(self) -> None:
        starts = {
            "甲": "青龙", "乙": "青龙", "丙": "朱雀", "丁": "朱雀",
            "戊": "勾陈", "己": "螣蛇", "庚": "白虎", "辛": "白虎",
            "壬": "玄武", "癸": "玄武",
        }
        for stem, start in starts.items():
            spirits = six_spirits_for(stem)
            self.assertEqual(spirits[0], start)
            self.assertEqual(len(set(spirits)), 6)

    def test_month_break_day_clash_and_element_relations_are_facts(self) -> None:
        facts = calculate_line_relations(
            line_branch="子",
            line_element="水",
            month_branch="午",
            day_branch="丑",
        )

        self.assertTrue(facts["month"]["break"])
        self.assertEqual(facts["month"]["branch_relation"], "冲")
        self.assertEqual(facts["day"]["branch_relation"], "合")
        self.assertEqual(facts["month"]["element_relation"], "爻克月")

    def test_all_twelve_clash_and_combine_boundaries_are_exact(self) -> None:
        elements = {
            "子": "水", "丑": "土", "寅": "木", "卯": "木",
            "辰": "土", "巳": "火", "午": "火", "未": "土",
            "申": "金", "酉": "金", "戌": "土", "亥": "水",
        }
        clashes = dict(zip("子丑寅卯辰巳午未申酉戌亥", "午未申酉戌亥子丑寅卯辰巳"))
        combines = dict(zip("子丑寅卯辰巳午未申酉戌亥", "丑子亥戌酉申未午巳辰卯寅"))
        for branch in elements:
            with self.subTest(branch=branch):
                relations = calculate_line_relations(
                    line_branch=branch,
                    line_element=elements[branch],
                    month_branch=clashes[branch],
                    day_branch=combines[branch],
                )
                self.assertTrue(relations["month"]["break"])
                self.assertEqual(relations["month"]["branch_relation"], "冲")
                self.assertEqual(relations["day"]["branch_relation"], "合")

    def test_hidden_lines_fill_only_relatives_absent_from_visible_plate(self) -> None:
        output = build_fact_layer(
            [9, 7, 7, 7, 7, 6],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        visible = {line["six_relative"] for line in output["lines"]}
        hidden = output["hidden_lines"]

        self.assertTrue(hidden)
        self.assertTrue(all(row["six_relative"] not in visible for row in hidden))
        self.assertTrue(all(row["source_plate"] == "坤为地" for row in hidden))

    def test_changed_line_is_a_strength_scored_candidate_and_suppresses_same_relative_hidden_line(self) -> None:
        output = build_fact_layer(
            [6, 8, 8, 7, 8, 8],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        changed = output["lines"][0]["changed_line"]

        self.assertEqual(changed["six_relative"], "父母")
        self.assertIn("month", changed["month_day_strength"])
        self.assertIn("day", changed["month_day_strength"])
        self.assertFalse(
            any(row["six_relative"] == "父母" for row in output["hidden_lines"])
        )
        self.assertTrue(
            any(
                row["source"] == "changed_line" and row["line"] == 1
                for row in output["useful_spirit_candidates"]["父母"]
            )
        )

    def test_program_emits_shi_ying_and_moving_candidate_relation_graph(self) -> None:
        output = build_fact_layer(
            [6, 8, 8, 7, 8, 8],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        graph = output["shi_ying_moving_relations"]

        self.assertEqual(
            {graph["shi_ying"]["shi_line"], graph["shi_ying"]["ying_line"]},
            {output["shi_ying"]["shi"], output["shi_ying"]["ying"]},
        )
        self.assertTrue(graph["moving_to_candidates"])
        self.assertTrue(
            any(
                edge["source_line"] == 1
                and edge["target_source"] == "changed_line"
                for edge in graph["moving_to_candidates"]
            )
        )
        self.assertTrue(
            all(edge["fact_status"] == "calculated_relation_not_verdict" for edge in graph["moving_to_candidates"])
        )

    def test_shi_ying_relation_uses_shi_ying_role_labels_not_moving_candidate_labels(self) -> None:
        output = build_fact_layer(
            [8, 8, 8, 7, 8, 8],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        relation = output["shi_ying_moving_relations"]["shi_ying"]

        self.assertIn("世", relation["element_relation"])
        self.assertIn("应", relation["element_relation"])
        self.assertNotIn("动爻", relation["element_relation"])
        self.assertNotIn("候选", relation["element_relation"])

    def test_returning_restraint_and_combination_are_both_preserved(self) -> None:
        output = build_fact_layer(
            [9, 7, 7, 7, 7, 6],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        line_one = output["lines"][0]["changed_relation"]

        self.assertIn("回头克", line_one["relations"])
        self.assertIn("回头合", line_one["relations"])

    def test_returning_generation_is_preserved_as_a_neutral_relation(self) -> None:
        output = build_fact_layer(
            [7, 7, 7, 7, 9, 7],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]

        self.assertEqual(output["primary_hexagram"]["name"], "乾为天")
        self.assertEqual(output["changed_hexagram"]["name"], "火天大有")
        self.assertIn("回头生", output["lines"][4]["changed_relation"]["relations"])

    def test_returning_generation_is_preserved_as_a_neutral_changed_line_fact(self) -> None:
        output = build_fact_layer(
            [7, 7, 7, 7, 9, 7],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]

        self.assertEqual(output["primary_hexagram"]["name"], "乾为天")
        self.assertEqual(output["changed_hexagram"]["name"], "火天大有")
        self.assertEqual(output["moving_lines"], [5])
        self.assertIn("回头生", output["lines"][4]["changed_relation"]["relations"])

    def test_useful_spirit_candidates_are_complete_but_never_auto_selected(self) -> None:
        output = build_fact_layer(
            [7, 8, 9, 6, 7, 8],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )["output"]
        candidates = output["useful_spirit_candidates"]

        self.assertEqual(set(candidates), RELATIVES)
        self.assertTrue(all(candidates[relative] for relative in RELATIVES))
        self.assertEqual(output["useful_spirit_selection"]["status"], "evidence_bound")
        self.assertNotIn("selected", output["useful_spirit_selection"])

        requested = build_fact_layer(
            [7, 8, 9, 6, 7, 8],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
            requested_useful_spirit_relatives=("官鬼", "父母"),
        )["output"]
        self.assertEqual(
            set(requested["requested_useful_spirit_candidates"]),
            {"官鬼", "父母"},
        )

    def test_finance_two_visible_wealth_lines_selects_only_moving_line_by_verified_rule(self) -> None:
        output = build_fact_layer(
            [6, 6, 6, 6, 6, 7],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
            question_class="finance",
        )["output"]
        adjudication = output["useful_spirit_selection"]["role_adjudication"]
        line_adjudication = adjudication["specific_line_adjudication"]

        self.assertEqual(line_adjudication["visible_candidate_lines"], [3, 6])
        self.assertEqual(line_adjudication["moving_visible_candidate_lines"], [3])
        self.assertEqual(
            line_adjudication["status"],
            "adjudicated_single_moving_visible_line",
        )
        self.assertEqual(adjudication["specific_line_selection"], 3)
        self.assertEqual(line_adjudication["specific_line_selection"], 3)
        self.assertEqual(
            line_adjudication["selection_source_ref"]["rule_id"],
            "ZR-04-04",
        )
        self.assertEqual(
            line_adjudication["selection_source_ref"]["verification_status"],
            "verified",
        )
        self.assertIsNone(adjudication["hard_verdict"])
        self.assertIsNone(line_adjudication["hard_verdict"])

    def test_finance_multiple_or_absent_visible_wealth_lines_remain_unresolved(self) -> None:
        child_candidate = {"source": "visible_line", "line": 6, "moving": False}
        cases = (
            {
                "name": "two_static",
                "wealth": [
                    {"source": "visible_line", "line": 2, "moving": False},
                    {"source": "visible_line", "line": 5, "moving": False},
                ],
                "status": "unresolved_multiple_visible_lines",
                "visible_count": 2,
                "moving_count": 0,
                "check": "两个可见妻财爻同动静，须结合完整旺衰取舍",
            },
            {
                "name": "two_moving",
                "wealth": [
                    {"source": "visible_line", "line": 2, "moving": True},
                    {"source": "visible_line", "line": 5, "moving": True},
                ],
                "status": "unresolved_multiple_visible_lines",
                "visible_count": 2,
                "moving_count": 2,
                "check": "两个可见妻财爻同动静，须结合完整旺衰取舍",
            },
            {
                "name": "three_visible",
                "wealth": [
                    {"source": "visible_line", "line": 1, "moving": False},
                    {"source": "visible_line", "line": 3, "moving": True},
                    {"source": "visible_line", "line": 5, "moving": False},
                ],
                "status": "unresolved_multiple_visible_lines",
                "visible_count": 3,
                "moving_count": 1,
                "check": "多个可见妻财爻的取舍",
            },
            {
                "name": "hidden_only",
                "wealth": [
                    {"source": "hidden_line", "line": 4, "moving": False},
                ],
                "status": "unresolved_no_visible_line",
                "visible_count": 0,
                "moving_count": 0,
                "check": "妻财伏神或变爻的取用",
            },
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                adjudication = liuyao_engine._useful_spirit_role_adjudication(
                    question_class="finance",
                    candidate_pool={
                        "妻财": case["wealth"],
                        "子孙": [child_candidate],
                    },
                )
                line_adjudication = adjudication["specific_line_adjudication"]

                self.assertEqual(line_adjudication["status"], case["status"])
                self.assertEqual(
                    line_adjudication["visible_candidate_count"],
                    case["visible_count"],
                )
                self.assertEqual(
                    line_adjudication["moving_visible_candidate_count"],
                    case["moving_count"],
                )
                self.assertIsNone(adjudication["specific_line_selection"])
                self.assertIsNone(line_adjudication["specific_line_selection"])
                self.assertIsNone(line_adjudication["selection_source_ref"])
                self.assertIn(case["check"], adjudication["unresolved_checks"])
                self.assertIsNone(adjudication["hard_verdict"])
                self.assertIsNone(line_adjudication["hard_verdict"])

    def test_finance_unique_visible_wealth_line_remains_bound_to_hjc_r009(self) -> None:
        output = build_fact_layer(
            [6, 6, 6, 6, 7, 8],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
            question_class="finance",
        )["output"]
        adjudication = output["useful_spirit_selection"]["role_adjudication"]
        line_adjudication = adjudication["specific_line_adjudication"]

        self.assertEqual(line_adjudication["visible_candidate_lines"], [6])
        self.assertEqual(
            line_adjudication["status"],
            "adjudicated_unique_visible_line",
        )
        self.assertEqual(adjudication["specific_line_selection"], 6)
        self.assertEqual(
            line_adjudication["selection_source_ref"]["rule_id"],
            "HJC-R009",
        )
        self.assertEqual(
            line_adjudication["selection_source_ref"],
            adjudication["source_ref"],
        )
        self.assertIsNone(adjudication["hard_verdict"])
        self.assertIsNone(line_adjudication["hard_verdict"])

    def test_seeded_digital_cast_is_reproducible_and_records_coin_faces(self) -> None:
        first = cast_from_seed("fixture-seed")
        second = cast_from_seed("fixture-seed")

        self.assertEqual(first, second)
        self.assertEqual(len(first["tosses"]), 6)
        self.assertEqual(len(first["coin_faces"]), 6)
        self.assertTrue(all(len(row) == 3 for row in first["coin_faces"]))
        self.assertTrue(all(value in {6, 7, 8, 9} for value in first["tosses"]))

    def test_digital_coin_faces_follow_the_classical_three_coin_value_mapping(self) -> None:
        cast = cast_from_seed("fixture-seed")

        for values, faces, total in zip(
            cast["coin_values"], cast["coin_faces"], cast["tosses"]
        ):
            self.assertEqual(faces, ["背" if value == 3 else "字" for value in values])
            self.assertEqual(total, sum(values))

    def test_validator_recomputes_and_rejects_tampered_najia(self) -> None:
        facts = build_fact_layer(
            [7, 7, 7, 7, 7, 7],
            calendar_facts=_calendar(),
            casting={"method": "supplied_complete_cast"},
        )
        self.assertTrue(validate_fact_layer(facts)["ok"])

        tampered = copy.deepcopy(facts)
        tampered["output"]["lines"][0]["najia"]["ganzhi"] = "甲午"
        report = validate_fact_layer(tampered)
        self.assertFalse(report["ok"])
        self.assertIn("liuyao_fact_digest_mismatch", report["codes"])


class LiuyaoProviderTests(unittest.TestCase):
    def test_provider_calculates_supplied_cast_and_binds_shared_calendar(self) -> None:
        result = LiuyaoProvider(ROOT).calculate(_request())

        self.assertEqual(result.system, "liuyao")
        self.assertEqual(result.provider_id, "mingli-master.liuyao.v1")
        self.assertRegex(result.facts["calendar_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(result.facts["chart_facts"]["output"]["moving_lines"], [1, 6])

    def test_digital_coin_cast_replays_only_from_the_transaction_seed(self) -> None:
        provider = LiuyaoProvider(ROOT)
        request = _internal_digital_request("a" * 64)
        first = provider.calculate(request)
        again = provider.calculate(request)
        other = provider.calculate(
            _internal_digital_request("b" * 64)
        )

        casting = first.facts["chart_facts"]["output"]["casting"]
        self.assertEqual(casting["seed"], "a" * 64)
        self.assertEqual(casting["seed_source"], "transaction_csprng_v1")
        self.assertEqual(first.facts["cast_digest"], again.facts["cast_digest"])
        self.assertEqual(first.facts["chart_facts"]["output"]["casting"], again.facts["chart_facts"]["output"]["casting"])
        self.assertNotEqual(first.facts["cast_digest"], other.facts["cast_digest"])

    def test_direct_digital_provider_requires_a_transaction_seed(self) -> None:
        with self.assertRaisesRegex(ValueError, "transaction CSPRNG seed"):
            LiuyaoProvider(ROOT).calculate(
                _request(chart_data={"casting_method": "digital_coin"})
            )

    def test_fact_validator_rejects_a_weak_digital_transaction_seed(self) -> None:
        facts = build_fact_layer(
            cast_from_seed("a" * 64)["tosses"],
            calendar_facts=_calendar(),
            casting={
                "method": "digital_coin",
                "seed": "a" * 64,
                "seed_source": "transaction_csprng_v1",
            },
        )
        weakened = copy.deepcopy(facts)
        weakened["output"]["casting"]["seed"] = "x"
        weakened["output"]["casting"]["cast_digest"] = canonical_digest(
            {
                key: value
                for key, value in weakened["output"]["casting"].items()
                if key != "cast_digest"
            }
        )
        weakened["fact_digest"] = canonical_digest(
            {key: value for key, value in weakened.items() if key != "fact_digest"}
        )

        validation = validate_fact_layer(weakened)

        self.assertFalse(validation["ok"])
        self.assertIn("liuyao_invalid_transaction_seed", validation["codes"])

    def test_public_projection_is_an_allowlist_not_a_seed_blacklist(self) -> None:
        seed = "a" * 64
        generated = cast_from_seed(seed)
        facts = build_fact_layer(
            generated["tosses"],
            calendar_facts=_calendar(),
            casting={
                "method": "digital_coin",
                "seed": seed,
                "seed_source": "transaction_csprng_v1",
            },
        )
        facts["output"]["casting"]["seed_b64"] = base64.b64encode(
            bytes.fromhex(seed)
        ).decode("ascii")

        public = public_projection(facts)

        self.assertEqual(
            set(public["output"]["casting"]),
            {
                "method",
                "algorithm",
                "coin_values",
                "coin_faces",
                "tosses",
                "seed_source",
                "provenance",
                "source_dependency_id",
                "cast_digest",
                "seed_commitment",
            },
        )
        self.assertNotIn("seed_b64", public["output"]["casting"])

    def test_transaction_assigns_and_persists_the_first_digital_cast(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(
                skill_dir=ROOT,
                store_root=temporary,
            )
            with mock.patch(
                "reading_engine.providers.secrets.token_hex",
                return_value="c" * 64,
            ) as random_seed:
                turn = engine.prepare_turn(
                    engine.providers["liuyao"].descriptor,
                    _turn_request(cast="digital_coin"),
                )
            prepared = turn.result

            self.assertIsInstance(prepared, PreparedReading)
            random_seed.assert_called_once_with(32)
            stored = engine.store.load_prepared(prepared.reading_id)
            live_cast = stored.calculation.facts["chart_facts"]["output"]["casting"]
            stored_cast = stored.calculation.facts["chart_facts"]["output"]["casting"]
            self.assertEqual(live_cast, stored_cast)
            self.assertEqual(live_cast["seed"], "c" * 64)
            self.assertNotEqual(
                live_cast["seed"],
                canonical_digest(
                    {
                        "profile": "liuyao-digital-coin-v1",
                        "reading_id": prepared.reading_id,
                    }
                ),
            )
            self.assertTrue(live_cast["provenance"]["generated_once_and_preserved"])

            public_payload = prepared.to_dict()
            public_json = json.dumps(public_payload, ensure_ascii=False, sort_keys=True)
            self.assertNotIn("c" * 64, public_json)
            self.assertNotIn('"seed"', public_json)
            commitments = [
                fact.value
                for fact in prepared.fact_index
                if fact.path.endswith("/casting/seed_commitment")
            ]
            self.assertEqual(len(commitments), 1)
            self.assertRegex(str(commitments[0]), r"^[0-9a-f]{64}$")
            self.assertNotIn("c" * 64, prepared.basis_text)
            self.assertNotIn('"seed"', prepared.basis_text)

            restarted = build_production_engine(
                skill_dir=ROOT,
                store_root=temporary,
            ).store.load_prepared(prepared.reading_id)
            self.assertEqual(
                restarted.calculation.facts["chart_facts"]["output"]["casting"],
                live_cast,
            )
            replay = cast_from_seed(live_cast["seed"])
            self.assertEqual(replay["tosses"], live_cast["tosses"])
            self.assertEqual(replay["coin_values"], live_cast["coin_values"])
            self.assertEqual(replay["coin_faces"], live_cast["coin_faces"])

    def test_external_transaction_seed_is_rejected_before_any_reading_is_staged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            turn = engine.prepare_turn(
                engine.providers["liuyao"].descriptor,
                _turn_request(
                    cast={"casting_method": "digital_coin", "seed": "d" * 64}
                ),
            )

            self.assertIsInstance(turn.result, InternalFailure)
            self.assertEqual(list((Path(temporary) / "readings").iterdir()), [])

    def test_time_cast_and_incomplete_cast_fail_closed(self) -> None:
        provider = LiuyaoProvider(ROOT)
        for chart in (
            {},
            {"casting_method": "time"},
            {"tosses": [7, 8, 9]},
            {"tosses": [7, 8, 9, 6, 7, 10]},
            {"tosses": ["7", "8", "9", "6", "7", "8"]},
            {"tosses": [7.9, 8, 9, 6, 7, 8]},
            {"tosses": [True, 8, 9, 6, 7, 8]},
        ):
            with self.subTest(chart=chart):
                with self.assertRaises(ValueError):
                    provider.calculate(_request(chart_data=chart))

    def test_query_wording_cannot_change_the_calculated_candidate_pool(self) -> None:
        provider = LiuyaoProvider(ROOT)
        first = provider.calculate(_request(query="问工作"))
        second = provider.calculate(_request(query="问感情和钱财"))

        self.assertEqual(first.facts["fact_digest"], second.facts["fact_digest"])
        self.assertEqual(
            first.facts["chart_facts"]["output"]["useful_spirit_candidates"],
            second.facts["chart_facts"]["output"]["useful_spirit_candidates"],
        )
        self.assertNotEqual(first.result_hash, second.result_hash)

    def test_refine_preserves_cast_and_calculation_but_refreshes_result_identity(self) -> None:
        provider = LiuyaoProvider(ROOT)
        base = provider.calculate(_internal_digital_request("e" * 64))
        refined = provider.refine(_request(query="只追问应期"), base)

        self.assertEqual(refined.facts["cast_digest"], base.facts["cast_digest"])
        self.assertEqual(refined.facts["fact_digest"], base.facts["fact_digest"])
        self.assertNotEqual(refined.result_hash, base.result_hash)

    def test_capability_and_factory_activate_only_deterministic_provider(self) -> None:
        capability = PROVIDER_CAPABILITIES["liuyao"]
        self.assertEqual(capability.mode, "calculation")
        self.assertIn("useful_spirit_candidates", capability.outputs)
        self.assertEqual(capability.horizons, ("instant",))
        self.assertEqual(missing_required_inputs("liuyao", _request()), ())
        self.assertEqual(
            missing_required_inputs("liuyao", _request(chart_data={})),
            ("cast",),
        )

        engine = build_production_engine(
            skill_dir=ROOT,
            store_root=ROOT / ".work" / "task7f-test-store",
        )
        self.assertIsInstance(engine.providers["liuyao"], LiuyaoProvider)
        self.assertNotIn("liuyao", STRUCTURED_SYSTEMS)

    def test_provider_never_marks_uncalculated_future_horizons_complete(self) -> None:
        provider = LiuyaoProvider(ROOT)
        base = provider.calculate(_request())

        instant = provider.extend(base, ("outcome", "timing"), {"kind": "instant"})
        future = provider.extend(base, ("timing",), {"kind": "day"})

        self.assertEqual(instant.fact_extension.status, "complete")
        self.assertEqual(instant.fact_extension.horizon, {"kind": "instant"})
        self.assertEqual(future.fact_extension.status, "unsupported")
        self.assertEqual(future.fact_extension.unsupported_dimensions, ("timing",))

    def test_recast_without_new_cast_does_not_inherit_old_supplied_tosses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(descriptor, _turn_request())
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)

            recast = engine.prepare_turn(
                descriptor,
                _turn_request(cast=None, query="另一件事重新起卦"),
                state_token=first_turn.state_token,
                transition="restart",
            )

            self.assertIsInstance(recast.result, NeedUserFact)
            self.assertEqual(recast.result.system, "liuyao")
            self.assertEqual(recast.result.missing_facts, ("cast",))

            resumed = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="数字投币"),
                state_token=recast.state_token,
            )
            self.assertIsInstance(resumed.result, PreparedReading)
            self.assertEqual(resumed.result.action, "recast")
            self.assertEqual(resumed.result.parent_reading_id, first.reading_id)
            self.assertEqual(resumed.result.root_reading_id, first.reading_id)
            resumed_internal = engine.store.load_prepared(resumed.result.reading_id)
            self.assertEqual(
                resumed_internal.calculation.facts["chart_facts"]["output"]["casting_method"],
                "digital_coin",
            )

    def test_initial_missing_cast_intake_resumes_from_structured_cast_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            pending = engine.prepare_turn(descriptor, _turn_request(cast=None))
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertEqual(pending.result.missing_facts, ("cast",))

            resumed = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="数字投币"),
                state_token=pending.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading)
            resumed_internal = engine.store.load_prepared(resumed.result.reading_id)
            self.assertEqual(
                resumed_internal.calculation.facts["chart_facts"]["output"]["casting_method"],
                "digital_coin",
            )

    def test_recast_to_digital_coin_replaces_old_tosses_and_uses_child_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(descriptor, _turn_request())
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)
            old_cast = engine.store.load(first.reading_id).calculation.facts[
                "chart_facts"
            ]["output"]["casting"]

            recast = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="另一件事改用数字投币"),
                state_token=first_turn.state_token,
                transition="restart",
            )

            self.assertIsInstance(recast.result, PreparedReading)
            new_cast = engine.store.load_prepared(
                recast.result.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            self.assertEqual(new_cast["method"], "digital_coin")
            self.assertNotEqual(recast.result.reading_id, first.reading_id)
            self.assertNotEqual(new_cast["cast_digest"], old_cast["cast_digest"])

    def test_continue_and_correct_reuse_seed_while_recast_gets_a_new_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "reading_engine.providers.secrets.token_hex",
            side_effect=("1" * 64, "2" * 64),
        ) as random_seed:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(
                descriptor, _turn_request(cast="digital_coin")
            )
            self.assertIsInstance(first_turn.result, PreparedReading)
            first_cast = engine.store.load_prepared(
                first_turn.result.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)

            continued = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="继续追问"),
                state_token=first_turn.state_token,
            )
            self.assertIsInstance(continued.result, PreparedReading)
            continued_cast = engine.store.load_prepared(
                continued.result.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            self.assertEqual(continued_cast, first_cast)
            continued_accepted = engine.complete_turn(
                continued.state_token, "六爻卦象事实已列明。\n继续轮结论已复核。"
            )
            self.assertIsInstance(continued_accepted, AcceptedReading)

            corrected = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="更正用神关系"),
                state_token=continued.state_token,
                transition="correct",
            )
            self.assertIsInstance(corrected.result, PreparedReading)
            corrected_cast = engine.store.load_prepared(
                corrected.result.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            self.assertEqual(corrected_cast["seed"], first_cast["seed"])
            corrected_accepted = engine.complete_turn(
                corrected.state_token, "六爻卦象事实已列明。\n更正轮结论已复核。"
            )
            self.assertIsInstance(corrected_accepted, AcceptedReading)

            recast = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="换一件事重新起卦"),
                state_token=corrected.state_token,
                transition="restart",
            )
            self.assertIsInstance(recast.result, PreparedReading)
            recast_seed = engine.store.load_prepared(
                recast.result.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]["seed"]
            self.assertEqual(first_cast["seed"], "1" * 64)
            self.assertEqual(recast_seed, "2" * 64)
            self.assertNotEqual(recast_seed, first_cast["seed"])
            self.assertEqual(random_seed.call_count, 2)

    def test_correct_cannot_replace_a_digital_cast_with_supplied_tosses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "reading_engine.providers.secrets.token_hex",
            return_value="3" * 64,
        ):
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(
                descriptor, _turn_request(cast="digital_coin")
            )
            self.assertIsInstance(first_turn.result, PreparedReading)
            accepted = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(accepted, AcceptedReading)

            result = engine.prepare_turn(
                descriptor,
                _turn_request(
                    cast={
                        "casting_method": "supplied_complete_cast",
                        "tosses": [7, 7, 7, 7, 7, 7],
                    },
                    query="把原数字卦改成这一卦",
                ),
                state_token=first_turn.state_token,
                transition="correct",
            ).result

            self.assertIsInstance(result, InternalFailure)
            self.assertEqual(result.code, "action_requires_recast")
            stored = engine.store.load(accepted.reading_id)
            self.assertEqual(stored.accepted.version, 1)
            with self.assertRaises(RuntimeError):
                engine.store.load_prepared(accepted.reading_id)

    def test_correct_cannot_replace_supplied_cast_with_digital_coin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(descriptor, _turn_request())
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)

            corrected = engine.prepare_turn(
                descriptor,
                _turn_request(cast="digital_coin", query="把原卦改成数字投币"),
                state_token=first_turn.state_token,
                transition="correct",
            ).result

            self.assertIsInstance(corrected, InternalFailure)
            self.assertEqual(corrected.code, "action_requires_recast")

    def test_correct_cannot_replace_digital_cast_with_supplied_tosses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(
                descriptor, _turn_request(cast="digital_coin")
            )
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)

            corrected = engine.prepare_turn(
                descriptor,
                _turn_request(
                    cast=[7, 7, 7, 7, 7, 7], query="把数字卦改成手工六爻"
                ),
                state_token=first_turn.state_token,
                transition="correct",
            ).result

            self.assertIsInstance(corrected, InternalFailure)
            self.assertEqual(corrected.code, "action_requires_recast")

    def test_correct_cannot_change_supplied_tosses_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(descriptor, _turn_request())
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)

            corrected = engine.prepare_turn(
                descriptor,
                _turn_request(
                    cast=[7, 7, 7, 7, 7, 7], query="改掉原来的投掷结果"
                ),
                state_token=first_turn.state_token,
                transition="correct",
            ).result

            self.assertIsInstance(corrected, InternalFailure)
            self.assertEqual(corrected.code, "action_requires_recast")

    def test_digital_cast_requires_exact_csprng_provenance(self) -> None:
        generated = cast_from_seed("a" * 64)
        for seed_source in (None, "transaction_reading_id_v1"):
            casting = {
                "method": "digital_coin",
                "seed": generated["seed"],
                "coin_values": generated["coin_values"],
                "coin_faces": generated["coin_faces"],
            }
            if seed_source is not None:
                casting["seed_source"] = seed_source
            with self.subTest(seed_source=seed_source):
                with self.assertRaisesRegex(ValueError, "seed provenance"):
                    build_fact_layer(
                        generated["tosses"],
                        calendar_facts=_calendar(),
                        casting=casting,
                    )

    def test_correct_rejects_legacy_digital_provider_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["liuyao"].descriptor
            first_turn = engine.prepare_turn(
                descriptor, _turn_request(cast="digital_coin")
            )
            self.assertIsInstance(first_turn.result, PreparedReading)
            first = engine.complete_turn(
                first_turn.state_token, "六爻卦象事实已列明。\n本轮结论已复核。"
            )
            self.assertIsInstance(first, AcceptedReading)
            persisted = engine.store.load(first.reading_id)
            legacy_calculation = replace(
                persisted.calculation,
                provider_version="1.0.0",
            )
            legacy_record = replace(persisted, calculation=legacy_calculation)

            with mock.patch.object(engine.store, "load", return_value=legacy_record):
                corrected = engine.prepare_turn(
                    descriptor,
                    _turn_request(cast="digital_coin", query="更正用神关系"),
                    state_token=first_turn.state_token,
                    transition="correct",
                ).result

            self.assertIsInstance(corrected, InternalFailure)
            self.assertEqual(corrected.code, "action_requires_recast")

    def test_provider_version_marks_csprng_contract_revision(self) -> None:
        self.assertEqual(LiuyaoProvider.provider_version, "1.4.0")

    def test_source_plan_requires_complete_calculated_fact_contract(self) -> None:
        result = LiuyaoProvider(ROOT).calculate(_request())
        plan = reading_source_plan.compile_source_plan(
            "liuyao",
            {"requested_dimensions": ["outcome", "timing"]},
            result.indexed_facts(),
        )

        self.assertEqual(
            plan["required_packs"],
            [
                "divination/zengshan-buyi",
                "divination/bushi-zhengzong",
                "divination/huangjin-ce",
                "divination/huozhu-lin",
            ],
        )
        self.assertTrue(all(row["satisfied"] for row in plan["applicability_conditions"]), plan)


if __name__ == "__main__":
    unittest.main()
