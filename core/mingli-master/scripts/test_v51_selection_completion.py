#!/usr/bin/env python3
"""Task 7K regressions for the deterministic Selection candidate engine."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import yaml

import adapter_validate
import audit_selection_provider
import audit_test_session
import audit_provider_completeness
import reading_source_plan
import structured_chart_adapter
from reading_engine import selection
from reading_engine.contracts import CalculationResult, PreparedReading, ReadingRequest
from reading_engine.evidence_rules import match_rule, production_evidence_rules
from reading_engine.factory import build_production_engine
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import STRUCTURED_SYSTEMS, SelectionProvider
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/selection-v51.yaml"
FACT_PROFILE = ROOT / "references/matrices/selection-fact-layer-profile.yaml"
REFINEMENT_PROFILE = ROOT / "references/matrices/shensha-ss-b2-selection-refinement.yaml"
SELECTION_CONTRACT_DOCS = (
    ROOT / "references/matrices/selection-fact-layer-profile.md",
    ROOT / "references/matrices/shensha-cross-system-index.md",
    ROOT / "references/matrices/shensha-distillation-backlog.md",
    ROOT / "references/matrices/shensha-source-book-matrix.md",
    ROOT / "references/matrices/shensha-source-book-matrix.yaml",
    ROOT / "references/matrices/shensha-ss-b10-bibliography-plan.md",
    ROOT / "references/matrices/shensha-ss-b2-selection-refinement.md",
    ROOT / "references/matrices/shensha-ss-b5-yangzhai-refinement.md",
    ROOT / "references/books/fengshui/yangzhai-shishu/procedures.md",
    ROOT / "references/books/fengshui/yangzhai-shishu/rules.md",
    ROOT / "references/regression/natural-language-regression.yaml",
    ROOT / "test-prompts.json",
)
ACTIVE_SELECTION_DOCS = tuple(
    sorted((ROOT / "references/books/selection").rglob("*.md"))
) + (ROOT / "references/system-cards/selection.md",)
EVENT_PROFILES = {
    "generic_selection",
    "marriage",
    "construction_renovation",
    "burial_funeral",
    "travel_office",
    "business_opening_transaction",
    "medical",
}
DEFAULT_REQUESTED_ACTIONS = {
    "generic_selection": [],
    "marriage": ["嫁娶"],
    "construction_renovation": ["修造"],
    "burial_funeral": ["安葬"],
    "travel_office": ["出行"],
    "business_opening_transaction": ["开市"],
    "medical": ["求医疗病"],
}


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _spec(**changes: object) -> dict:
    value: dict[str, object] = {
        "event_profile": "business_opening_transaction",
        "date_range": {"start": "2026-07-24", "end": "2026-07-28"},
        "hard_constraints": {},
        "participant_facts": [],
        "include_folk_comparison": False,
    }
    value.update(changes)
    if "requested_actions" not in changes:
        value["requested_actions"] = DEFAULT_REQUESTED_ACTIONS[str(value["event_profile"])]
    return value


def _intent() -> dict:
    return {
        "subject_refs": ["event"],
        "calculation_object": "calendar_choice",
        "question_dimensions": ["timing", "state"],
        "horizon": {"kind": "day", "start": "2026-07-24", "end": "2026-07-28"},
        "requested_method": "selection",
        "requested_granularity": "exact_day",
        "continuity": {
            "reading_id": None,
            "same_subject": False,
            "same_event": False,
        },
        "facts_present": ["event_profile", "date_range", "timezone", "location"],
        "facts_corrected": [],
        "evidence_questions": ["哪些候选日满足官方用事条件，排除原因是什么"],
    }


def _request(**changes: object) -> ReadingRequest:
    payload: dict[str, object] = {
        "query": "为开业在这个日期范围内择日",
        "action": "new",
        "system": "selection",
        "intent": _intent(),
        "timezone": "Asia/Shanghai",
        "location": "上海",
        "chart_data": {"selection_spec": _spec()},
    }
    payload.update(changes)
    return ReadingRequest(**payload)


def _turn_request(request: ReadingRequest) -> ProviderRequest:
    """Project a legacy-style request onto the provider turn surface."""

    intent = dict(request.intent or {})
    facts: dict[str, object] = dict(
        (request.chart_data or {}).get("selection_spec") or {}
    )
    if request.timezone:
        facts["timezone"] = request.timezone
    if request.location:
        facts["location"] = request.location
    return ProviderRequest(
        query=request.query,
        subject_refs=("event",),
        object_id="calendar_choice",
        dimension_ids=tuple(
            intent.get("question_dimensions") or ("timing", "state")
        ),
        horizon=dict(
            intent.get("horizon")
            or {"kind": "day", "start": None, "end": None}
        ),
        facts={"event": facts},
    )


def _prepare(engine, request: ReadingRequest):
    """Run one production prepare turn for the selection capability."""

    return engine.prepare_turn(
        engine.providers["selection"].descriptor, _turn_request(request)
    ).result


class SelectionFixtureContractTests(unittest.TestCase):
    def test_lunar_python_fixture_replays_xieji_luohou_source_rule(self) -> None:
        supplied = next(
            case["input"]
            for case in _fixture()["external_reference_cases"]
            if case["id"] == "lunar-python-01"
        )
        spec = {
            "event_profile": supplied["event_profile"],
            "requested_actions": supplied["requested_actions"],
            "requested_scopes": supplied["requested_scopes"],
            "directional_context": supplied["directional_context"],
            "date_range": {"start": supplied["date"], "end": supplied["date"]},
            "hard_constraints": {
                "time_windows": [{"start": "12:00", "end": "12:01"}]
            },
            "participant_facts": [],
            "include_folk_comparison": False,
        }
        result = SelectionProvider(ROOT).calculate(
            ReadingRequest(
                query="Task 7N Xieji source witness",
                action="new",
                system="selection",
                timezone=supplied["timezone"],
                location=supplied["location"],
                chart_data={"selection_spec": spec},
            )
        )
        candidates = result.facts["chart_facts"]["output"]["calendar_candidates"]

        self.assertEqual(len(candidates), 1)
        self.assertIn("XR-18", candidates[0]["active_source_rule_ids"])

    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_test_session.load_report("selection")
        if report is None:
            report = audit_selection_provider.audit_selection_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["external_reference_cases"], 30)
        self.assertEqual(report["counts"]["external_unexplained_mismatches"], 0)
        self.assertEqual(report["counts"]["published_calendar_cases"], 30)
        self.assertEqual(report["counts"]["published_calendar_mismatches"], 0)
        self.assertGreaterEqual(report["counts"]["boundary_cases"], 6)
        self.assertEqual(report["counts"]["event_profiles"], 7)
        self.assertEqual(report["counts"]["event_rule_cases"], 30)
        self.assertEqual(report["counts"]["event_rule_mismatches"], 0)
        self.assertEqual(report["counts"]["event_fact_definitions"], 74)
        self.assertEqual(report["counts"]["event_fact_formula_cases"], 222)
        self.assertEqual(report["counts"]["event_fact_positive_cases"], 74)
        self.assertEqual(report["counts"]["event_fact_negative_cases"], 74)
        self.assertEqual(report["counts"]["event_fact_boundary_cases"], 74)
        self.assertEqual(report["counts"]["event_fact_formula_mismatches"], 0)
        self.assertEqual(report["counts"]["evidence_fact_bindings"], 68)
        self.assertEqual(report["counts"]["donggong_classified_profile_rows"], 1008)
        self.assertGreaterEqual(report["counts"]["no_candidate_cases"], 1)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 6)
        self.assertEqual(report["counts"]["donggong_raw_rows"], 144)
        self.assertEqual(report["counts"]["donggong_unique_ids"], 144)
        self.assertEqual(report["findings"], [])

    def test_completeness_audit_rejects_mutated_source_or_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_copy = root / "source.yaml"
            fixture_copy = root / "fixture.yaml"
            source_copy.write_text(
                (ROOT / "references/matrices/selection-source-tables-v1.yaml")
                .read_text(encoding="utf-8")
                .replace("opaque_numeric_score: false", "opaque_numeric_score: true", 1),
                encoding="utf-8",
            )
            fixture_copy.write_text(
                FIXTURE.read_text(encoding="utf-8").replace(
                    "candidate_count: 1", "candidate_count: 99", 1
                ),
                encoding="utf-8",
            )

            source_report = audit_selection_provider.audit_selection_provider(
                source_table_path=source_copy
            )
            fixture_report = audit_selection_provider.audit_selection_provider(
                fixture_path=fixture_copy
            )

        self.assertFalse(source_report["provider_ready"])
        self.assertIn("Selection source-table artifact hash mismatch", source_report["findings"])
        self.assertFalse(fixture_report["provider_ready"])
        self.assertIn("Selection fixture artifact hash mismatch", fixture_report["findings"])

    def test_hash_mismatch_never_runs_live_provider_replays(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture_copy = Path(temporary) / "fixture.yaml"
            fixture_copy.write_text(
                FIXTURE.read_text(encoding="utf-8").replace(
                    "candidate_count: 1", "candidate_count: 99", 1
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                audit_selection_provider.SelectionProvider,
                "calculate",
                side_effect=AssertionError("live provider must not run"),
            ):
                report = audit_selection_provider.audit_selection_provider(
                    fixture_path=fixture_copy
                )

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "Selection fixture artifact hash mismatch", report["findings"]
        )

    def test_completeness_audit_rejects_missing_event_evidence_or_donggong_contract(self) -> None:
        source = yaml.safe_load(
            (ROOT / "references/matrices/selection-source-tables-v1.yaml")
            .read_text(encoding="utf-8")
        )
        mutations = []

        missing_event = copy.deepcopy(source)
        del missing_event["event_fact_definitions"]["bujiang_day"]
        mutations.append(
            (missing_event, "Selection event fact definition coverage mismatch")
        )

        missing_binding = copy.deepcopy(source)
        del missing_binding["evidence_fact_bindings"]["rules"]["XR-05"]
        mutations.append(
            (missing_binding, "Selection evidence fact binding coverage mismatch")
        )

        wrong_primary_scope = copy.deepcopy(source)
        wrong_primary_scope["primary_classical_rule_witnesses"][
            "xieji-xunshan-luohou-v1"
        ]["explicitly_taboo_actions"] = ["修方"]
        mutations.append(
            (
                wrong_primary_scope,
                "Selection primary classical rule witness invalid: "
                "xieji-xunshan-luohou-v1",
            )
        )

        missing_verdict = copy.deepcopy(source)
        missing_verdict["donggong_event_verdicts"]["profiles"]["marriage"][
            "avoid"
        ].remove("DG-D001")
        mutations.append(
            (missing_verdict, "Selection Donggong classification hash mismatch: marriage")
        )

        with tempfile.TemporaryDirectory() as temporary:
            for index, (payload, expected) in enumerate(mutations):
                with self.subTest(expected=expected):
                    path = Path(temporary) / f"selection-source-{index}.yaml"
                    path.write_text(
                        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                        encoding="utf-8",
                    )
                    report = audit_selection_provider.audit_selection_provider(
                        source_table_path=path
                    )
                    self.assertFalse(report["provider_ready"])
                    observed = [
                        *report["findings"],
                        *report["source_verification"].get("findings", ()),
                    ]
                    self.assertIn(expected, observed)

    def test_thirty_frozen_external_examples_match_or_declare_exact_boundary_difference(self) -> None:
        observed_differences: list[tuple[str, str]] = []
        for case in _fixture()["external_reference_cases"]:
            with self.subTest(case=case["id"]):
                record = selection.build_day_record(
                    case["input"]["date"],
                    timezone_name=case["input"]["timezone"],
                    location=case["input"]["location"],
                    event_profile="generic_selection",
                )
                expected = case["expected"]
                self.assertEqual(record["calendar"]["lunar_date"], expected["lunar_date"])
                self.assertEqual(record["calendar"]["ganzhi"]["year"], expected["ganzhi"]["year"])
                self.assertEqual(record["calendar"]["ganzhi"]["day"], expected["ganzhi"]["day"])
                self.assertEqual(record["mansion"]["short_name"], expected["mansion"])
                self.assertEqual(record["clash"]["zodiac"], expected["clash"][-1])
                if case["id"] == "lunar-python-03":
                    self.assertEqual(record["calendar"]["boundary_status"], "intra_day_jie_boundary")
                    self.assertEqual(record["jianchu"]["value"], "收")
                    self.assertEqual(record["day_path"]["runtime_name"], "青龙")
                    observed_differences.append((case["id"], "comparator_day_boundary_inconsistency"))
                else:
                    self.assertEqual(record["jianchu"]["value"], expected["jianchu"])
                    self.assertEqual(record["day_path"]["runtime_name"], expected["day_twelve_god"])
                    self.assertEqual(record["day_path"]["class"], expected["huanghei"])

        self.assertEqual(
            observed_differences,
            [("lunar-python-03", "comparator_day_boundary_inconsistency")],
        )

    def test_exact_jie_boundary_is_calculated_with_intra_day_variants(self) -> None:
        record = selection.build_day_record(
            "2024-02-04",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="generic_selection",
        )

        self.assertEqual(record["calendar"]["ganzhi"]["month"], "乙丑")
        self.assertEqual(record["jianchu"]["value"], "收")
        self.assertEqual(
            {(item["month_ganzhi"], item["jianchu"]) for item in record["hour_facts"]},
            {("乙丑", "收"), ("丙寅", "成")},
        )
        self.assertEqual(record["calendar"]["boundary_status"], "intra_day_jie_boundary")
        shen = next(row for row in record["hour_facts"] if row["branch"] == "申")
        self.assertEqual(shen["month_ganzhi_variants"], ["乙丑", "丙寅"])
        self.assertEqual(
            shen["jianchu_variants"],
            [
                {"month_ganzhi": "乙丑", "value": "收"},
                {"month_ganzhi": "丙寅", "value": "成"},
            ],
        )

    def test_late_night_exact_jie_is_not_missed_by_hour_sampling(self) -> None:
        record = selection.build_day_record(
            "2024-12-06",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="generic_selection",
        )

        self.assertEqual(record["calendar"]["boundary_status"], "intra_day_jie_boundary")
        self.assertEqual(record["calendar"]["month_ganzhi_variants"], ["乙亥", "丙子"])
        self.assertEqual(
            record["calendar"]["month_boundary_jie"]["name"],
            "大雪",
        )

    def test_every_day_has_complete_hour_ganzhi_and_twelve_path_facts(self) -> None:
        record = selection.build_day_record(
            "2024-01-01",  # 甲子 day in the frozen calendar profile
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="generic_selection",
        )
        hours = record["hour_facts"]

        self.assertEqual(record["calendar"]["ganzhi"]["day"], "甲子")
        self.assertEqual(len(hours), 12)
        self.assertEqual([item["branch"] for item in hours], list(selection.BRANCHES))
        self.assertEqual(
            [item["ganzhi"] for item in hours],
            list("甲子乙丑丙寅丁卯戊辰己巳庚午辛未壬申癸酉甲戌乙亥"[index:index + 2]
                 for index in range(0, 24, 2)),
        )
        self.assertEqual(
            [item["twelve_path_god"] for item in hours],
            ["金匮", "天德", "白虎", "玉堂", "天牢", "玄武", "司命", "勾陈", "青龙", "明堂", "天刑", "朱雀"],
        )
        self.assertEqual(
            [item["class"] for item in hours],
            ["huang", "huang", "hei", "huang", "hei", "hei", "huang", "hei", "huang", "huang", "hei", "hei"],
        )

    def test_annual_and_monthly_three_sha_are_separate_source_derived_facts(self) -> None:
        record = selection.build_day_record(
            "2026-07-24",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="generic_selection",
        )

        self.assertEqual(
            record["annual_gods"]["three_sha"],
            {
                "trine": "寅午戌",
                "jie_sha_branch": "亥",
                "zai_sha_branch": "子",
                "sui_sha_branch": "丑",
                "sector": "north",
            },
        )
        self.assertEqual(
            record["monthly_gods"]["three_sha"],
            {
                "trine": "亥卯未",
                "jie_sha_branch": "申",
                "zai_sha_branch": "酉",
                "sui_sha_branch": "戌",
                "sector": "west",
            },
        )

    def test_all_event_profiles_use_exact_official_action_contracts(self) -> None:
        for profile in EVENT_PROFILES:
            with self.subTest(profile=profile):
                facts = selection.build_fact_layer(
                    _spec(
                        event_profile=profile,
                        date_range={"start": "2026-07-24", "end": "2026-07-24"},
                    ),
                    timezone_name="Asia/Shanghai",
                    location="上海",
                )
                candidate = facts["output"]["calendar_candidates"][0]
                event = candidate["official_event_rules"]
                self.assertEqual(event["profile"], profile)
                self.assertTrue(set(event["yi_matches"]).issubset(set(candidate["official_yiji"]["yi"])))
                self.assertTrue(set(event["ji_matches"]).issubset(set(candidate["official_yiji"]["ji"])))
                self.assertNotIn("free_text_match", event)

    def test_every_event_profile_emits_all_source_declared_structured_facts(self) -> None:
        profiles = selection.source_table()["event_profiles"]
        for profile, contract in profiles.items():
            with self.subTest(profile=profile):
                record = selection.build_day_record(
                    "2026-07-24",
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    event_profile=profile,
                )
                facts = record["event_specific_facts"]
                self.assertEqual(
                    set(facts), set(contract["required_event_fact_fields"])
                )
                for field, value in facts.items():
                    self.assertEqual(value["status"], "calculated", field)
                    self.assertTrue(value["source_anchors"], field)
                    self.assertIn("active", value, field)

    def test_medical_folk_facts_use_exact_renshen_and_visit_day_tables(self) -> None:
        renshen = selection.build_day_record(
            "2024-01-01",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="medical",
            include_folk_comparison=True,
        )["event_specific_facts"]["renshen_location"]
        taboo = selection.build_day_record(
            "2024-01-07",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="medical",
            include_folk_comparison=True,
        )["event_specific_facts"]["visit_sick_taboo_days"]
        ordinary = selection.build_day_record(
            "2024-01-08",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="medical",
            include_folk_comparison=True,
        )["event_specific_facts"]["visit_sick_taboo_days"]

        self.assertEqual(renshen["value"]["day_ganzhi"], "甲子")
        self.assertEqual(renshen["value"]["stem_location"], "头")
        self.assertEqual(renshen["value"]["branch_location"], "目")
        self.assertTrue(taboo["active"])
        self.assertEqual(taboo["value"]["day_ganzhi"], "庚午")
        self.assertFalse(ordinary["active"])

    def test_universal_all_actions_taboo_is_a_hard_elimination(self) -> None:
        for profile in ("generic_selection", "marriage", "business_opening_transaction"):
            with self.subTest(profile=profile):
                record = selection.build_day_record(
                    "2026-01-02",
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    event_profile=profile,
                )

                self.assertFalse(record["eligibility"]["eligible"])
                self.assertIn(
                    "official_universal_avoidance",
                    {row["code"] for row in record["rejection_reasons"]},
                )

    def test_directional_scope_requires_structured_direction_and_never_guesses(self) -> None:
        with self.assertRaisesRegex(ValueError, "directional_context.site_branch"):
            selection.build_fact_layer(
                _spec(
                    event_profile="construction_renovation",
                    date_range={"start": "2026-07-24", "end": "2026-07-24"},
                    requested_scopes=["directional_judgment"],
                ),
                timezone_name="Asia/Shanghai",
                location="上海",
            )

        facts = selection.build_fact_layer(
            _spec(
                event_profile="construction_renovation",
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
                requested_scopes=["directional_judgment"],
                directional_context={"site_branch": "子"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        candidate = facts["output"]["calendar_candidates"][0]

        self.assertEqual(candidate["scope_status"]["requested_scopes"], ["directional_judgment"])
        self.assertEqual(candidate["directional_facts"]["site_branch"], "子")
        self.assertTrue(candidate["directional_facts"]["evaluated_hits"])

        mountain = selection.build_day_record(
            "2024-01-02",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="construction_renovation",
            requested_actions=["修造"],
            requested_scopes=["directional_judgment"],
            directional_context={"site_mountain": "乙"},
        )
        self.assertEqual(mountain["directional_facts"]["site_mountain"], "乙")
        luohou = mountain["event_specific_facts"]["luohou"]
        self.assertFalse(luohou["active"])
        self.assertEqual(luohou["rank_effect"], "informational")
        self.assertEqual(
            luohou["value"],
            {
                "formula": "xunshan_luohou",
                "value": "乙",
                "site_field": "site_mountain",
                "site_value": "乙",
                "matched": True,
                "applicable": False,
                "applicable_actions": ["立向"],
                "explicitly_exempt_actions": ["开山", "修方"],
                "requested_actions": ["修造"],
            },
        )
        self.assertTrue(mountain["eligibility"]["eligible"])
        self.assertFalse(
            any(
                reason.get("event_fact_field") == "luohou"
                for reason in mountain["rejection_reasons"]
            )
        )
        construction_actions = selection.source_table()["event_profiles"][
            "construction_renovation"
        ]["official_terms"]
        self.assertIn("立向", construction_actions)
        self.assertIn("开山", construction_actions)
        self.assertIn("修方", construction_actions)

        mountain_layer = selection.build_fact_layer(
            _spec(
                event_profile="construction_renovation",
                date_range={"start": "2024-01-02", "end": "2024-01-02"},
                requested_actions=["修造"],
                requested_scopes=["directional_judgment"],
                directional_context={"site_mountain": "乙"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        normalized = mountain_layer["input"]["selection_spec"]["directional_context"]
        self.assertEqual(normalized, {"site_mountain": "乙"})
        mountain_candidate = mountain_layer["output"]["calendar_candidates"][0]
        self.assertEqual(
            mountain_candidate["directional_facts"]["site_mountain"], "乙"
        )
        self.assertFalse(mountain_candidate["event_specific_facts"]["luohou"]["active"])
        self.assertTrue(mountain_candidate["eligibility"]["eligible"])
        exact_times = mountain_layer["output"]["date_time_candidates"]
        self.assertTrue(exact_times)
        self.assertTrue(
            all(
                not any(
                    reason.get("code") == "event_fact_hard_elimination"
                    and reason.get("event_fact_field") == "luohou"
                    for reason in candidate["rejection_reasons"]
                )
                for candidate in exact_times
            )
        )

    def test_informational_direction_hits_never_bypass_declarative_rank_effects(self) -> None:
        facts = selection.build_fact_layer(
            _spec(
                event_profile="construction_renovation",
                requested_actions=["搬移"],
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
                requested_scopes=["directional_judgment"],
                directional_context={"site_branch": "子"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        day = facts["output"]["calendar_candidates"][0]

        self.assertTrue(day["directional_facts"]["evaluated_hits"])
        self.assertTrue(day["eligibility"]["eligible"])
        self.assertFalse(
            any(
                reason["code"] == "directional_conflict"
                for reason in day["rejection_reasons"]
            )
        )
        self.assertFalse(
            any(
                reason["code"] == "directional_conflict"
                for candidate in facts["output"]["date_time_candidates"]
                for reason in candidate["rejection_reasons"]
            )
        )

    def test_participant_branch_opposition_is_an_explicit_hard_elimination(self) -> None:
        baseline = selection.build_fact_layer(
            _spec(date_range={"start": "2026-07-24", "end": "2026-07-24"}),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        day_branch = baseline["output"]["calendar_candidates"][0]["calendar"]["ganzhi"]["day"][1]
        participant_branch = selection.OPPOSITE_BRANCHES[day_branch]
        facts = selection.build_fact_layer(
            _spec(
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
                participant_facts=[{"id": "owner", "year_branch": participant_branch}],
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        candidate = facts["output"]["calendar_candidates"][0]

        self.assertFalse(candidate["eligibility"]["eligible"])
        self.assertEqual(candidate["participant_clashes"][0]["participant_id"], "owner")
        self.assertIn("participant_branch_clash", {row["code"] for row in candidate["rejection_reasons"]})

    def test_participant_clash_can_be_declared_comparison_only_by_structured_constraint(self) -> None:
        baseline = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        day_branch = baseline["output"]["calendar_candidates"][0]["calendar"]["ganzhi"]["day"][1]
        participant_branch = selection.OPPOSITE_BRANCHES[day_branch]
        facts = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
                hard_constraints={"participant_clash_is_hard": False},
                participant_facts=[{"id": "owner", "year_branch": participant_branch}],
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        candidate = facts["output"]["calendar_candidates"][0]

        self.assertTrue(candidate["eligibility"]["eligible"])
        self.assertEqual(len(candidate["participant_clashes"]), 1)
        self.assertEqual(candidate["ranking_components"]["participant_clash_count"], 1)

    def test_structured_time_window_filters_hours_without_natural_language_parsing(self) -> None:
        facts = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
                hard_constraints={"time_windows": [{"start": "09:00", "end": "11:00"}]},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        hours = facts["output"]["calendar_candidates"][0]["hour_facts"]

        self.assertEqual(
            [row["branch"] for row in hours if row["hard_constraint_eligible"]],
            ["巳"],
        )

    def test_time_windows_intersect_real_double_hour_intervals_not_sample_points(self) -> None:
        cases = (
            ({"start": "00:30", "end": "01:00"}, "子"),
            ({"start": "01:15", "end": "01:45"}, "丑"),
            ({"start": "23:15", "end": "23:45"}, "子"),
        )
        for window, expected_branch in cases:
            with self.subTest(window=window):
                facts = selection.build_fact_layer(
                    _spec(
                        event_profile="generic_selection",
                        date_range={"start": "2026-07-24", "end": "2026-07-24"},
                        hard_constraints={"time_windows": [window]},
                    ),
                    timezone_name="Asia/Shanghai",
                    location="上海",
                )
                hours = facts["output"]["calendar_candidates"][0]["hour_facts"]

                self.assertEqual(
                    [row["branch"] for row in hours if row["hard_constraint_eligible"]],
                    [expected_branch],
                )
                matching = next(row for row in hours if row["branch"] == expected_branch)
                self.assertTrue(matching["civil_time_segments"])
                if window["start"].startswith("23:"):
                    eligible_zi = [
                        row
                        for row in facts["output"]["date_time_candidates"]
                        if row["hour_branch"] == "子"
                        and row["eligibility"]["eligible"]
                    ]
                    self.assertEqual(
                        [(row["civil_start"], row["civil_end_exclusive"]) for row in eligible_zi],
                        [("23:15", "23:45")],
                    )

    def test_two_civil_zi_segments_keep_distinct_ranges_under_one_midnight_day(self) -> None:
        record = selection.build_day_record(
            "2026-07-24",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="generic_selection",
        )
        zi = next(row for row in record["hour_facts"] if row["branch"] == "子")

        self.assertEqual(
            {item["ganzhi"]["hour"] for item in zi["calendar_variants"]},
            {"甲子"},
        )
        self.assertEqual(
            {(item["civil_start"], item["civil_end_exclusive"]) for item in zi["calendar_variants"]},
            {("00:00", "01:00"), ("23:00", "24:00")},
        )

    def test_jie_inside_one_double_hour_splits_time_facts_and_rankable_candidates(self) -> None:
        facts = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2024-02-04", "end": "2024-02-04"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        output = facts["output"]
        record = output["calendar_candidates"][0]
        shen = next(
            row
            for row in record["hour_facts"]
            if row["branch"] == "申"
        )

        self.assertEqual(
            {item["ganzhi"]["month"] for item in shen["calendar_variants"]},
            {"乙丑", "丙寅"},
        )
        self.assertEqual(
            {item["jianchu"] for item in shen["calendar_variants"]},
            {"收", "成"},
        )
        boundary_clock = record["calendar"]["month_boundary_jie"]["datetime"].split(
            "T", 1
        )[1][:-6]
        before, after = shen["calendar_variants"]
        self.assertEqual(before["civil_end_exclusive"], boundary_clock)
        self.assertEqual(after["civil_start"], boundary_clock)
        self.assertGreaterEqual(len(output["date_time_candidates"]), 13)
        self.assertTrue(output["ranking"]["ordered_date_time_candidate_ids"])
        shen_candidates = [
            row
            for row in output["date_time_candidates"]
            if row["hour_branch"] == "申"
        ]
        self.assertEqual(
            {row["official_event_rules"]["calendar_month_ganzhi"] for row in shen_candidates},
            {"乙丑", "丙寅"},
        )
        self.assertTrue(
            all(row["official_event_rules"]["assessment_digest"] for row in shen_candidates)
        )
        self.assertEqual(
            {
                row["monthly_gods"]["month_build_branch"]
                for row in shen_candidates
            },
            {"丑", "寅"},
        )
        self.assertTrue(all(row["annual_gods"] for row in shen_candidates))
        self.assertEqual(
            len(output["ranking"]["ordered_date_time_candidate_ids"]),
            len(set(output["ranking"]["ordered_date_time_candidate_ids"])),
        )

    def test_jie_day_validity_is_derived_from_exact_time_candidates_not_noon(self) -> None:
        facts = selection.build_fact_layer(
            _spec(
                event_profile="construction_renovation",
                requested_actions=["筑堤防"],
                date_range={"start": "2024-08-07", "end": "2024-08-07"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        output = facts["output"]
        date_record = output["calendar_candidates"][0]
        date_id = date_record["candidate_id"]
        eligible_times = output["eligible_date_time_candidates"]
        boundary_clock = date_record["calendar"]["month_boundary_jie"]["datetime"].split(
            "T", 1
        )[1][:-6]

        self.assertGreater(len(eligible_times), 0)
        self.assertTrue(
            all(row["civil_end_exclusive"] <= boundary_clock for row in eligible_times)
        )
        self.assertFalse(output["no_valid_candidate"])
        self.assertEqual(output["ranking"]["eligible_candidate_ids"], [date_id])
        self.assertEqual(
            [row["candidate_id"] for row in output["eligible_candidates"]],
            [date_id],
        )
        ranked_day = output["eligible_candidates"][0]
        full_day = output["calendar_candidates"][0]
        best_time_id = ranked_day["best_candidate_time_id"]
        best_time = next(
            row
            for row in output["date_time_candidates"]
            if row["candidate_time_id"] == best_time_id
        )
        self.assertEqual(best_time_id, output["ranking"]["eligible_date_time_candidate_ids"][0])
        self.assertEqual(full_day["official_event_rules"], best_time["official_event_rules"])
        self.assertEqual(full_day["event_specific_facts"], best_time["event_specific_facts"])
        self.assertEqual(ranked_day["ranking_components"]["official_event_avoid_count"], 0)
        self.assertEqual(ranked_day["ranking_components"]["basis_candidate_time_id"], best_time_id)

    def test_exact_requested_action_does_not_inherit_sibling_action_avoidance(self) -> None:
        allowed = selection.build_fact_layer(
            _spec(
                event_profile="construction_renovation",
                requested_actions=["搬移"],
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )["output"]["calendar_candidates"][0]
        avoided = selection.build_fact_layer(
            _spec(
                event_profile="construction_renovation",
                requested_actions=["破土"],
                date_range={"start": "2026-07-24", "end": "2026-07-24"},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )["output"]["calendar_candidates"][0]

        self.assertTrue(allowed["eligibility"]["eligible"])
        self.assertEqual(allowed["official_event_rules"]["yi_matches"], ["搬移"])
        self.assertEqual(allowed["official_event_rules"]["ji_matches"], [])
        self.assertIn(
            "破土",
            allowed["official_event_rules"]["unrequested_action_observations"]["ji_matches"],
        )
        self.assertFalse(avoided["eligibility"]["eligible"])
        self.assertEqual(avoided["official_event_rules"]["ji_matches"], ["破土"])

    def test_non_generic_profile_requires_supported_exact_requested_actions(self) -> None:
        with self.assertRaisesRegex(ValueError, "requested_actions"):
            selection.build_fact_layer(
                {
                    "event_profile": "marriage",
                    "date_range": {"start": "2026-07-24", "end": "2026-07-24"},
                },
                timezone_name="Asia/Shanghai",
                location="上海",
            )
        with self.assertRaisesRegex(ValueError, "requested_actions"):
            selection.build_fact_layer(
                _spec(event_profile="marriage", requested_actions=["开市"]),
                timezone_name="Asia/Shanghai",
                location="上海",
            )

    def test_dst_gaps_and_folds_are_resolved_as_structured_time_facts(self) -> None:
        spring = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2026-03-08", "end": "2026-03-08"},
                hard_constraints={"time_windows": [{"start": "02:15", "end": "02:45"}]},
            ),
            timezone_name="America/New_York",
            location="New York",
        )
        spring_candidate = spring["output"]["calendar_candidates"][0]

        self.assertFalse(spring_candidate["eligibility"]["eligible"])
        self.assertIn("no_allowed_hour", {row["code"] for row in spring_candidate["rejection_reasons"]})
        spring_chou = next(
            row for row in spring_candidate["hour_facts"] if row["branch"] == "丑"
        )
        self.assertEqual(
            spring_chou["timezone_resolution"]["nonexistent_minute_count"], 60
        )
        self.assertEqual(
            [
                (
                    row["civil_start"],
                    row["civil_end_exclusive"],
                    row["utc_offset_seconds"],
                    row["fold"],
                )
                for row in spring_chou["calendar_variants"]
            ],
            [("01:00", "02:00", -18000, 0)],
        )

        autumn = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2026-11-01", "end": "2026-11-01"},
                hard_constraints={"time_windows": [{"start": "01:15", "end": "01:45"}]},
            ),
            timezone_name="America/New_York",
            location="New York",
        )
        autumn_hours = autumn["output"]["calendar_candidates"][0]["hour_facts"]
        chou = next(row for row in autumn_hours if row["branch"] == "丑")

        self.assertTrue(chou["hard_constraint_eligible"])
        self.assertEqual(chou["timezone_resolution"]["ambiguous_minute_count"], 60)
        self.assertEqual(chou["timezone_resolution"]["utc_offset_seconds"], [-18000, -14400])
        self.assertEqual(
            {
                (
                    row["civil_start"],
                    row["civil_end_exclusive"],
                    row["utc_offset_seconds"],
                    row["fold"],
                )
                for row in chou["calendar_variants"]
            },
            {
                ("01:00", "02:00", -14400, 0),
                ("01:00", "02:00", -18000, 1),
                ("02:00", "03:00", -18000, 0),
            },
        )
        eligible_fold = autumn["output"]["eligible_date_time_candidates"]
        self.assertEqual(len(eligible_fold), 2)
        self.assertEqual(
            {(row["civil_start"], row["civil_end_exclusive"]) for row in eligible_fold},
            {("01:15", "01:45")},
        )
        self.assertEqual({row["fold"] for row in eligible_fold}, {0, 1})
        self.assertEqual(len({row["instant_utc"] for row in eligible_fold}), 2)

    def test_time_window_crops_the_effective_candidate_interval(self) -> None:
        facts = selection.build_fact_layer(
            _spec(
                event_profile="generic_selection",
                date_range={"start": "2026-02-09", "end": "2026-02-09"},
                hard_constraints={"time_windows": [{"start": "01:15", "end": "01:45"}]},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        eligible = facts["output"]["eligible_date_time_candidates"]

        self.assertEqual(len(eligible), 1)
        self.assertEqual(
            (eligible[0]["civil_start"], eligible[0]["civil_end_exclusive"]),
            ("01:15", "01:45"),
        )
        self.assertEqual(
            eligible[0]["effective_allowed_intervals"],
            [{"start": "01:15", "end_exclusive": "01:45"}],
        )

    def test_hard_exclusions_can_produce_an_explicit_no_candidate_result(self) -> None:
        facts = selection.build_fact_layer(
            _spec(
                date_range={"start": "2026-07-24", "end": "2026-07-25"},
                hard_constraints={"excluded_dates": ["2026-07-24", "2026-07-25"]},
            ),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        output = facts["output"]

        self.assertTrue(output["no_valid_candidate"])
        self.assertEqual(output["ranking"]["eligible_candidate_ids"], [])
        self.assertEqual(len(output["eliminations"]), 2)
        self.assertTrue(all(row["rejection_reasons"] for row in output["eliminations"]))

    def test_folk_comparison_never_changes_official_rank_or_eligibility(self) -> None:
        shared = {
            "event_profile": "generic_selection",
            "date_range": {"start": "2026-08-13", "end": "2026-08-13"},
        }
        official = selection.build_fact_layer(
            _spec(**shared, include_folk_comparison=False),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        compared = selection.build_fact_layer(
            _spec(**shared, include_folk_comparison=True),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        first = official["output"]["calendar_candidates"][0]
        second = compared["output"]["calendar_candidates"][0]

        self.assertEqual(first["official_assessment_digest"], second["official_assessment_digest"])
        self.assertEqual(first["eligibility"], second["eligibility"])
        self.assertEqual(official["output"]["ranking"]["eligible_candidate_ids"], compared["output"]["ranking"]["eligible_candidate_ids"])
        self.assertNotIn("folk_comparison", first)
        self.assertIn("folk_comparison", second)
        self.assertFalse(second["folk_comparison"]["affects_official_rank"])

    def test_donggong_all_rows_have_frozen_profile_verdicts_and_expose_conflict(self) -> None:
        table = selection.source_table()["donggong_event_verdicts"]
        row_ids = {row["id"] for row in selection._donggong_rows().values()}
        for profile, verdicts in table["profiles"].items():
            with self.subTest(profile=profile):
                classified = [
                    identifier
                    for verdict in ("recommend", "avoid", "mixed_conditional")
                    for identifier in verdicts[verdict]
                ]
                self.assertEqual(len(classified), len(set(classified)))
                self.assertTrue(set(classified).issubset(row_ids))
                self.assertEqual(
                    row_ids,
                    set(classified)
                    | {
                        identifier
                        for identifier in row_ids
                        if selection.donggong_event_verdict(identifier, profile)
                        == "not_stated"
                    },
                )

        record = selection.build_day_record(
            "2026-02-09",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="generic_selection",
            include_folk_comparison=True,
        )
        comparison = record["folk_comparison"]

        self.assertTrue(record["eligibility"]["eligible"])
        self.assertEqual(comparison["donggong_row"]["id"], "DG-D001")
        self.assertEqual(comparison["donggong_verdict"], "avoid")
        self.assertTrue(comparison["disagreement"])
        self.assertEqual(comparison["disagreement_sources"], ["donggong"])

        burial = selection.build_day_record(
            "2024-02-10",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="burial_funeral",
            requested_actions=["安葬"],
            include_folk_comparison=True,
        )
        self.assertTrue(burial["event_specific_facts"]["sansang_day"]["active"])
        self.assertFalse(burial["eligibility"]["eligible"])
        self.assertEqual(burial["folk_comparison"]["official_assessment"], "eliminated")
        self.assertEqual(burial["folk_comparison"]["donggong_verdict"], "avoid")
        self.assertNotIn("donggong", burial["folk_comparison"]["disagreement_sources"])

    def test_yuqia_yang_gong_june_date_is_source_exact_second_not_third(self) -> None:
        second = selection.folk_rule_hits(6, 2, "甲子")
        third = selection.folk_rule_hits(6, 3, "乙丑")

        self.assertIn("folk.yang-gong-thirteen", {row["id"] for row in second})
        self.assertNotIn("folk.yang-gong-thirteen", {row["id"] for row in third})

    def test_same_input_is_digest_deterministic_and_has_no_opaque_score(self) -> None:
        first = selection.build_fact_layer(
            _spec(), timezone_name="Asia/Shanghai", location="上海"
        )
        second = selection.build_fact_layer(
            copy.deepcopy(_spec()), timezone_name="Asia/Shanghai", location="上海"
        )

        self.assertEqual(first, second)
        self.assertEqual(first["fact_digest"], second["fact_digest"])
        self.assertEqual(first["output"]["ranking"]["method"], "explainable_lexicographic_v1")
        self.assertFalse(first["output"]["ranking"]["opaque_numeric_score"])
        self.assertNotIn("score", first["output"]["ranking"])

    def test_safety_boundaries_are_structured_facts_not_fixed_answer_sentences(self) -> None:
        facts = selection.build_fact_layer(
            _spec(event_profile="medical"),
            timezone_name="Asia/Shanghai",
            location="上海",
        )

        self.assertTrue(facts["warnings"])
        self.assertTrue(all(isinstance(item, dict) for item in facts["warnings"]))
        self.assertEqual(
            {item["code"] for item in facts["warnings"]},
            {
                "traditional_reference_not_event_guarantee",
                "professional_medical_care_controls",
            },
        )

    def test_digest_is_stable_across_python_hash_seeds(self) -> None:
        script = """
from reading_engine.selection import build_fact_layer
facts = build_fact_layer(
    {
        'event_profile': 'business_opening_transaction',
        'requested_actions': ['开市'],
        'date_range': {'start': '2026-07-24', 'end': '2026-07-28'},
    },
    timezone_name='Asia/Shanghai',
    location='上海',
)
print(facts['fact_digest'])
"""
        digests = []
        for seed in ("1", "2", "37"):
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = seed
            environment["PYTHONPATH"] = str(ROOT / "scripts")
            digests.append(
                subprocess.check_output(
                    [sys.executable, "-c", script],
                    cwd=ROOT,
                    env=environment,
                    text=True,
                ).strip()
            )

        self.assertEqual(len(set(digests)), 1, digests)

    def test_validation_recomputes_and_rejects_nested_tampering(self) -> None:
        facts = selection.build_fact_layer(
            _spec(), timezone_name="Asia/Shanghai", location="上海"
        )
        tampered = copy.deepcopy(facts)
        tampered["output"]["calendar_candidates"][0]["jianchu"]["value"] = "破"
        tampered["fact_digest"] = selection.fact_digest(tampered)

        report = selection.validate_fact_layer(tampered)

        self.assertFalse(report["ok"])
        self.assertIn("selection_candidate_facts_mismatch", report["codes"])

    def test_runtime_range_and_range_size_fail_closed(self) -> None:
        for spec in (
            _spec(date_range={"start": "1900-12-31", "end": "1900-12-31"}),
            _spec(date_range={"start": "2101-01-01", "end": "2101-01-01"}),
            _spec(date_range={"start": "2026-01-01", "end": "2027-12-31"}),
        ):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    selection.build_fact_layer(
                        spec, timezone_name="Asia/Shanghai", location="上海"
                    )
        with self.assertRaisesRegex(ValueError, "requested_scopes must be a list"):
            selection.normalize_spec(
                _spec(requested_scopes="directional_judgment")
            )


class SelectionProviderActivationTests(unittest.TestCase):
    def test_ephemeral_runtime_reuse_preserves_every_selection_fact(self) -> None:
        arguments = {
            "spec": _spec(
                date_range={"start": "2026-07-24", "end": "2026-07-24"}
            ),
            "timezone_name": "Asia/Shanghai",
            "location": "上海",
        }
        lunar_constructor = selection.Lunar
        with mock.patch.object(
            selection,
            "Lunar",
            side_effect=lunar_constructor,
        ) as reused_constructor:
            reused = selection.build_fact_layer(**arguments)

        original_aligned_runtime = selection._aligned_runtime

        def without_context(local_datetime, calendar, runtime_context=None):
            del runtime_context
            return original_aligned_runtime(local_datetime, calendar, None)

        with (
            mock.patch.object(
                selection,
                "Lunar",
                side_effect=lunar_constructor,
            ) as uncached_constructor,
            mock.patch.object(
                selection,
                "_aligned_runtime",
                side_effect=without_context,
            ),
        ):
            independently_recalculated = selection.build_fact_layer(**arguments)

        self.assertEqual(reused, independently_recalculated)
        self.assertLess(
            reused_constructor.call_count,
            uncached_constructor.call_count,
        )
        self.assertGreaterEqual(
            uncached_constructor.call_count,
            2 * reused_constructor.call_count - 1,
        )

    def _prepare_bounded_range(self, end: str) -> tuple[PreparedReading, float]:
        intent = _intent()
        intent["horizon"] = {
            "kind": "day",
            "start": "2026-07-24",
            "end": end,
        }
        request = _request(
            intent=intent,
            chart_data={
                "selection_spec": _spec(
                    date_range={"start": "2026-07-24", "end": end}
                )
            },
        )
        started = time.monotonic()
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(
                skill_dir=ROOT,
                store_root=temporary,
            )
            prepared = _prepare(engine, request)
        elapsed = time.monotonic() - started
        self.assertIsInstance(prepared, PreparedReading)
        return prepared, elapsed

    def test_one_day_prepared_payload_and_fact_index_are_bounded(self) -> None:
        prepared, elapsed = self._prepare_bounded_range("2026-07-24")
        encoded = json.dumps(
            prepared.to_dict(), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

        self.assertLess(len(encoded), 1_500_000)
        self.assertLess(len(prepared.fact_index), 3_000)
        self.assertLess(len(prepared.basis_text.encode("utf-8")), 200_000)
        self.assertLess(elapsed, 5.0)

    def test_thirty_two_day_prepared_payload_and_fact_index_are_bounded(self) -> None:
        prepared, elapsed = self._prepare_bounded_range("2026-08-24")
        encoded = json.dumps(
            prepared.to_dict(), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        basis_facts = SelectionProvider(ROOT).public_basis_projection(
            prepared.calculation.facts["chart_facts"]
        )

        self.assertLess(len(encoded), 16_000_000)
        self.assertLess(len(prepared.fact_index), 25_000)
        self.assertLess(len(prepared.basis_text.encode("utf-8")), 500_000)
        self.assertLess(elapsed, 20.0)
        self.assertLessEqual(len(basis_facts["eliminations"]), 12)
        for field in (
            "ordered_candidate_ids",
            "eligible_candidate_ids",
            "ordered_date_time_candidate_ids",
            "eligible_date_time_candidate_ids",
        ):
            self.assertLessEqual(len(basis_facts["ranking"][field]), 12)
        self.assertEqual(
            basis_facts["basis_projection"]["complete_counts"][
                "calendar_candidates"
            ],
            32,
        )

    def test_selection_fact_profiles_require_provider_and_forbid_semantic_gate(self) -> None:
        fact_profile = yaml.safe_load(FACT_PROFILE.read_text(encoding="utf-8"))
        refinement = yaml.safe_load(REFINEMENT_PROFILE.read_text(encoding="utf-8"))["refinement"]

        for policy in (fact_profile["policy"], refinement["policy"]):
            self.assertTrue(policy["requires_deterministic_selection_provider"])
            self.assertTrue(policy["current_model_final_review"])
            self.assertFalse(policy["semantic_gate"])
            self.assertNotIn("requires_tool_selection_lisuan", policy)
            self.assertNotIn("rerun_gate_check_after_final_rewrite", policy)
        self.assertTrue(
            fact_profile["policy"]["structured_event_profile_and_exact_actions"]
        )
        self.assertFalse(fact_profile["policy"]["natural_language_alias_routing"])
        self.assertTrue(
            all("aliases" not in profile for profile in fact_profile["event_profiles"].values())
        )

    def test_selection_is_a_deterministic_calculation_capability(self) -> None:
        capability = PROVIDER_CAPABILITIES["selection"]

        self.assertEqual(capability.mode, "calculation")
        self.assertEqual(capability.objects, ("calendar_choice",))
        self.assertEqual(
            capability.required_inputs,
            ("event_profile", "requested_actions", "date_range", "timezone", "location"),
        )
        self.assertNotIn("selection", STRUCTURED_SYSTEMS)

    def test_required_inputs_are_read_from_structured_spec_not_request_prose(self) -> None:
        empty = _request(chart_data={}, timezone=None, location=None)
        fake = _request(
            chart_data={"calendar_candidates": [{"date": "2026-07-24"}]},
            timezone=None,
            location=None,
        )

        self.assertEqual(
            missing_required_inputs("selection", empty),
            ("event_profile", "date_range", "timezone", "location"),
        )
        self.assertEqual(missing_required_inputs("selection", fake), missing_required_inputs("selection", empty))
        self.assertEqual(missing_required_inputs("selection", _request()), ())
        missing_action = _request(
            chart_data={
                "selection_spec": {
                    "event_profile": "marriage",
                    "date_range": {"start": "2026-07-24", "end": "2026-07-24"},
                }
            }
        )
        self.assertEqual(
            missing_required_inputs("selection", missing_action),
            ("requested_actions",),
        )

    def test_provider_calculates_without_a_user_supplied_chart(self) -> None:
        result = SelectionProvider(ROOT).calculate(_request())

        self.assertEqual(result.provider_id, "mingli-master.selection.v1")
        self.assertNotIn("validated_user_provided_chart", result.diagnostics)
        self.assertEqual(result.facts["chart_facts"]["fact_layer_status"], "deterministic_selection_candidates")
        self.assertGreaterEqual(len(result.facts["chart_facts"]["output"]["calendar_candidates"]), 1)

    def test_provider_input_payload_has_canonical_declared_digest_preimages(self) -> None:
        input_payload: dict[str, object] = {}
        original_create = CalculationResult.create

        def capture_create(**kwargs: object) -> CalculationResult:
            input_payload.update(dict(kwargs["input_payload"]))
            return original_create(**kwargs)

        with mock.patch.object(CalculationResult, "create", side_effect=capture_create):
            SelectionProvider(ROOT).calculate(_request())

        self.assertNotIn("input_digest", input_payload)
        self.assertTrue(
            audit_provider_completeness._declared_input_digests_have_preimages(
                input_payload
            )
        )

    def test_factory_registers_the_deterministic_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)

        self.assertIsInstance(engine.providers["selection"], SelectionProvider)

    def test_full_transaction_prepares_ranked_facts_for_evidence_without_internal_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            prepared = _prepare(engine, _request(reading_id=None))

        self.assertIsInstance(prepared, PreparedReading)
        self.assertEqual(prepared.system, "selection")
        self.assertEqual(prepared.calculation.provider_id, "mingli-master.selection.v1")
        self.assertTrue(
            any(
                "/calendar_candidates/" in fact.path
                for fact in prepared.fact_index
            )
        )

    def test_every_selection_rule_has_exact_calculated_fact_predicates(self) -> None:
        rules = [
            rule
            for rule in production_evidence_rules()
            if rule.system == "selection"
        ]

        self.assertEqual(len(rules), 68)
        for rule in rules:
            with self.subTest(rule=rule.rule_id):
                if rule.rule_id == "selection/xingli-kaoyuan#KR-05":
                    # The audited five-tigers/five-rats methodology binds to
                    # the calculated four pillars and must not self-authorize
                    # via the provider-written active_source_rule_ids fact.
                    self.assertEqual(
                        [
                            (item.path_suffix, item.operator)
                            for item in rule.required_fact_predicates
                        ],
                        [
                            ("/calendar/ganzhi/year", "nonempty"),
                            ("/calendar/ganzhi/month", "nonempty"),
                            ("/calendar/ganzhi/day", "nonempty"),
                            ("/calendar/ganzhi/hour", "nonempty"),
                        ],
                    )
                    continue
                self.assertGreaterEqual(len(rule.required_fact_predicates), 2)
                self.assertEqual(
                    rule.required_fact_predicates[0].path_suffix,
                    "/fact_layer_status",
                )
                self.assertEqual(
                    rule.required_fact_predicates[0].value,
                    "deterministic_selection_candidates",
                )

    def test_source_conditioned_patterns_are_exact_identities_without_verdicts(self) -> None:
        facts = selection.build_fact_layer(
            _spec(date_range={"start": "2026-07-24", "end": "2026-07-24"}),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        patterns = facts["output"]["source_conditioned_patterns"]

        self.assertEqual(
            [row["rule_id"] for row in patterns],
            ["selection/xingli-kaoyuan#KR-05"],
        )
        self.assertTrue(
            all(row["status"] == "predicate_matched_not_verdict" for row in patterns)
        )
        self.assertTrue(all(row["fact_paths"] for row in patterns))
        self.assertTrue(all(row["predicate_audit"] for row in patterns))
        self.assertTrue(
            all("verdict" not in key for row in patterns for key in row)
        )

    def test_source_pattern_suffix_index_matches_complete_fact_index(self) -> None:
        indexed = {
            "chart_facts": {
                "fact_layer_status": "deterministic_selection_candidates",
                "output": {
                    "calendar_candidates": [
                        {
                            "calendar": {
                                "ganzhi": {
                                    "year": "甲辰",
                                    "month": "辛未",
                                    "day": "己丑",
                                    "hour": "庚午",
                                }
                            },
                            "active_source_rule_ids": [
                                f"rule-{index}" for index in range(12)
                            ],
                            "unrelated": {"large": [1, 2, 3]},
                        }
                    ]
                },
            }
        }
        rules = tuple(
            rule
            for rule in production_evidence_rules()
            if rule.system == "selection" and rule.runtime_active
        )
        suffixes = tuple(
            dict.fromkeys(
                predicate.path_suffix
                for rule in rules
                for predicate in (
                    *rule.required_fact_predicates,
                    *rule.excluded_fact_predicates,
                )
            )
        )
        expected = {
            path: value
            for path, value in selection._fact_leaves(indexed)
            if any(
                path.endswith(suffix) or f"{suffix}/" in path
                for suffix in suffixes
            )
        }

        actual = list(selection._fact_leaves_at_suffixes(indexed, suffixes))

        self.assertEqual(dict(actual), expected)
        self.assertEqual(
            actual,
            list(selection._fact_leaves_at_suffixes(indexed, suffixes)),
        )
        self.assertFalse(any("unrelated" in path for path, _ in actual))

    def test_extension_preserves_source_conditioned_patterns(self) -> None:
        provider = SelectionProvider(ROOT)
        extended = provider.extend(
            provider.calculate(_request()),
            tuple(provider.capability.dimensions),
            {"kind": "day", "start": "2026-07-24", "end": "2026-07-24"},
        )

        self.assertIsNotNone(extended.fact_extension)
        extension = extended.fact_extension.to_dict()
        patterns = extension["facts"]["source_conditioned_patterns"]
        self.assertEqual(
            [row["rule_id"] for row in patterns],
            ["selection/xingli-kaoyuan#KR-05"],
        )
        public = provider.public_extension_projection(extension)
        self.assertEqual(public["facts"]["source_conditioned_patterns"], patterns)
        self.assertEqual(
            public["facts"]["basis_projection"]["complete_counts"][
                "source_conditioned_patterns"
            ],
            1,
        )

    def test_selection_evidence_is_fact_bound_and_has_registered_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            prepared = _prepare(engine, _request(reading_id=None))

        self.assertIsInstance(prepared, PreparedReading)
        nodes = (*prepared.evidence, *prepared.counter_evidence)
        self.assertTrue(nodes)
        self.assertTrue(all(node.fact_refs for node in nodes))
        self.assertTrue(
            all(not node.lineage.startswith("unregistered:") for node in nodes)
        )
        known = {fact.fact_id for fact in prepared.fact_index}
        self.assertTrue(all(set(node.fact_refs) <= known for node in nodes))

    def test_yuqia_rules_bind_to_the_actual_structured_hit_path(self) -> None:
        intent = _intent()
        intent["horizon"] = {
            "kind": "day",
            "start": "2026-08-13",
            "end": "2026-08-13",
        }
        request = _request(
            intent=intent,
            chart_data={
                "selection_spec": _spec(
                    date_range={"start": "2026-08-13", "end": "2026-08-13"},
                    include_folk_comparison=True,
                )
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            prepared = _prepare(engine, request)

        for local_rule_id in ("JR-05", "JR-06"):
            rule = next(
                item
                for item in production_evidence_rules()
                if item.system == "selection"
                and item.local_rule_id == local_rule_id
            )
            # Folk Yuxiaji rules stay runtime-inactive until their source
            # meaning and applicability pass the independent semantic audit.
            self.assertFalse(rule.runtime_active)
            self.assertFalse(match_rule(rule, prepared.fact_index)[0])
            # The predicate contract itself must still bind to the exact
            # structured hit path calculated by the provider.
            audited = replace(rule, runtime_active=True)
            matched, fact_refs, _audit = match_rule(audited, prepared.fact_index)
            self.assertTrue(matched, local_rule_id)
            self.assertTrue(fact_refs, local_rule_id)

    def test_directional_evidence_requires_a_calculated_directional_scope(self) -> None:
        rule = next(
            item
            for item in production_evidence_rules()
            if item.system == "selection" and item.local_rule_id == "XR-02"
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            without_direction = _prepare(engine, _request())
            with_direction = _prepare(
                engine,
                _request(
                    chart_data={
                        "selection_spec": _spec(
                            requested_scopes=["directional_judgment"],
                            directional_context={"site_branch": "子"},
                        )
                    }
                ),
            )

        self.assertIsInstance(without_direction, PreparedReading)
        self.assertIsInstance(with_direction, PreparedReading)
        # XR-02 stays runtime-inactive pending its semantic source audit, so
        # even a calculated directional hit cannot retrieve it in production.
        self.assertFalse(rule.runtime_active)
        self.assertFalse(match_rule(rule, with_direction.fact_index)[0])
        # Its predicate contract must still require the calculated
        # directional scope instead of matching on the bare request.
        audited = replace(rule, runtime_active=True)
        self.assertFalse(match_rule(audited, without_direction.fact_index)[0])
        self.assertTrue(match_rule(audited, with_direction.fact_index)[0])

    def test_luohou_exact_witness_retrieves_only_on_the_calculated_hit(self) -> None:
        rules = [
            item
            for item in production_evidence_rules()
            if item.system == "selection" and item.local_rule_id == "XR-18"
        ]
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertIn("止忌立向", rule.quote)
        self.assertIn("开山、修方不忌", rule.quote)
        self.assertIn("仅作方位信息，不作硬淘汰", rule.quote)

        def prepared_for(site_mountain: str, action: str = "立向") -> PreparedReading:
            intent = {
                **_intent(),
                "evidence_questions": [
                    "巡山罗睺命中时为什么只作方位信息而不直接硬淘汰"
                ],
                "horizon": {
                    "kind": "day",
                    "start": "2024-01-02",
                    "end": "2024-01-02",
                },
            }
            request = _request(
                query="巡山罗睺命中时为什么只作方位信息而不直接硬淘汰",
                intent=intent,
                chart_data={
                    "selection_spec": _spec(
                        event_profile="construction_renovation",
                        requested_actions=[action],
                        date_range={"start": "2024-01-02", "end": "2024-01-02"},
                        requested_scopes=["directional_judgment"],
                        directional_context={"site_mountain": site_mountain},
                    )
                },
            )
            with tempfile.TemporaryDirectory() as temporary:
                engine = build_production_engine(
                    skill_dir=ROOT,
                    store_root=temporary,
                )
                prepared = _prepare(engine, request)
            self.assertIsInstance(prepared, PreparedReading)
            return prepared

        hit = prepared_for("乙")
        miss = prepared_for("甲")
        matched, fact_refs, _audit = match_rule(rule, hit.fact_index)
        self.assertTrue(matched)
        self.assertTrue(fact_refs)
        self.assertFalse(match_rule(rule, miss.fact_index)[0])
        exempt = prepared_for("乙", "开山")
        self.assertFalse(match_rule(rule, exempt.fact_index)[0])
        exact_rule_id = "selection/xieji-bianfang-shu#XR-18"
        self.assertIn(exact_rule_id, {node.rule_id for node in hit.evidence})
        self.assertNotIn(
            exact_rule_id,
            {
                node.rule_id
                for node in (*miss.evidence, *miss.counter_evidence)
            },
        )

    def test_inactive_direction_and_shensha_rules_do_not_retrieve(self) -> None:
        rules = {
            item.local_rule_id: item
            for item in production_evidence_rules()
            if item.system == "selection" and item.local_rule_id in {"KR-09", "KR-13"}
        }
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            inactive_direction = _prepare(
                engine,
                _request(
                    intent={
                        **_intent(),
                        "horizon": {
                            "kind": "day",
                            "start": "2026-07-24",
                            "end": "2026-07-24",
                        },
                    },
                    chart_data={
                        "selection_spec": _spec(
                            event_profile="construction_renovation",
                            requested_actions=["搬移"],
                            date_range={"start": "2026-07-24", "end": "2026-07-24"},
                            requested_scopes=["directional_judgment"],
                            directional_context={"site_branch": "巳"},
                        )
                    }
                ),
            )
            inactive_side_waste = _prepare(
                engine,
                _request(
                    intent={
                        **_intent(),
                        "horizon": {
                            "kind": "day",
                            "start": "2026-07-24",
                            "end": "2026-07-24",
                        },
                    },
                    chart_data={
                        "selection_spec": _spec(
                            event_profile="marriage",
                            requested_actions=["嫁娶"],
                            date_range={"start": "2026-07-24", "end": "2026-07-24"},
                        )
                    }
                ),
            )

        self.assertIsInstance(inactive_direction, PreparedReading)
        self.assertIsInstance(inactive_side_waste, PreparedReading)
        self.assertFalse(match_rule(rules["KR-09"], inactive_direction.fact_index)[0])
        self.assertFalse(match_rule(rules["KR-13"], inactive_side_waste.fact_index)[0])

    def test_marriage_participant_scope_requires_complete_two_party_branch_facts(self) -> None:
        partial = selection.build_day_record(
            "2026-07-24",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="marriage",
            requested_actions=["嫁娶"],
            participant_facts=[{"id": "a", "year_branch": "子"}],
        )
        complete = selection.build_day_record(
            "2026-07-24",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="marriage",
            requested_actions=["嫁娶"],
            participant_facts=[
                {"id": "a", "year_branch": "子", "day_branch": "寅"},
                {"id": "b", "year_branch": "丑", "day_branch": "卯"},
            ],
        )

        self.assertFalse(partial["scope_status"]["participant_specific"])
        self.assertEqual(partial["participant_scope"]["status"], "partial_input_general_only")
        self.assertTrue(complete["scope_status"]["participant_specific"])
        self.assertEqual(complete["participant_scope"]["status"], "couple_specific")

    def test_burial_three_mourning_and_tujin_are_source_calculated(self) -> None:
        three_mourning_dates = {
            "spring": ("2024-02-10", 1, "辰"),
            "summer": ("2024-05-19", 4, "未"),
            "autumn": ("2024-08-14", 7, "戌"),
            "winter": ("2024-01-02", 11, "丑"),
        }
        for season, (civil_date, lunar_month, taboo_branch) in (
            three_mourning_dates.items()
        ):
            with self.subTest(rule="sansang_day", season=season):
                record = selection.build_day_record(
                    civil_date,
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    event_profile="burial_funeral",
                    requested_actions=["安葬"],
                )
                fact = record["event_specific_facts"]["sansang_day"]
                self.assertTrue(fact["active"])
                self.assertFalse(record["eligibility"]["eligible"])
                self.assertIn(
                    {
                        "code": "event_fact_hard_elimination",
                        "event_fact_field": "sansang_day",
                        "source_anchors": fact["source_anchors"],
                        "rank_effect": "hard_elimination",
                    },
                    record["rejection_reasons"],
                )
                self.assertEqual(
                    fact["value"],
                    {
                        "lunar_month": lunar_month,
                        "season": season,
                        "day_branch": taboo_branch,
                        "taboo_branch": taboo_branch,
                        "matched": True,
                        "applicable": True,
                        "applicable_actions": ["安葬"],
                        "requested_actions": ["安葬"],
                        "authority": "chen_zixing_zaozang_classical_witness",
                    },
                )

                for sibling_action in ("破土", "启攒"):
                    with self.subTest(
                        rule="sansang_day",
                        season=season,
                        sibling_action=sibling_action,
                    ):
                        sibling = selection.build_day_record(
                            civil_date,
                            timezone_name="Asia/Shanghai",
                            location="上海",
                            event_profile="burial_funeral",
                            requested_actions=[sibling_action],
                        )["event_specific_facts"]["sansang_day"]
                        self.assertFalse(sibling["active"])
                        self.assertTrue(sibling["value"]["matched"])
                        self.assertFalse(sibling["value"]["applicable"])

        ordinary = selection.build_day_record(
            "2024-02-11",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="burial_funeral",
            requested_actions=["安葬"],
        )["event_specific_facts"]
        self.assertFalse(ordinary["sansang_day"]["active"])

        tujin_dates = {
            "spring": ("2024-02-17", 1, "亥"),
            "summer": ("2024-05-14", 4, "寅"),
            "autumn": ("2024-08-09", 7, "巳"),
            "winter": ("2024-01-09", 11, "申"),
        }
        for season, (civil_date, lunar_month, taboo_branch) in tujin_dates.items():
            with self.subTest(rule="tujin", season=season, action="破土"):
                record = selection.build_day_record(
                    civil_date,
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    event_profile="burial_funeral",
                    requested_actions=["破土"],
                )
                applicable = record["event_specific_facts"]["tujin"]
                self.assertTrue(applicable["active"])
                self.assertFalse(record["eligibility"]["eligible"])
                self.assertIn(
                    {
                        "code": "event_fact_hard_elimination",
                        "event_fact_field": "tujin",
                        "source_anchors": applicable["source_anchors"],
                        "rank_effect": "hard_elimination",
                    },
                    record["rejection_reasons"],
                )
                self.assertEqual(
                    applicable["value"],
                    {
                        "lunar_month": lunar_month,
                        "season": season,
                        "day_branch": taboo_branch,
                        "taboo_branch": taboo_branch,
                        "matched": True,
                        "applicable": True,
                        "applicable_actions": ["破土"],
                        "requested_actions": ["破土"],
                        "authority": "chen_zixing_zaozang_classical_witness",
                    },
                )

            with self.subTest(rule="tujin", season=season, action="安葬"):
                inapplicable = selection.build_day_record(
                    civil_date,
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    event_profile="burial_funeral",
                    requested_actions=["安葬"],
                )["event_specific_facts"]["tujin"]
                self.assertFalse(inapplicable["active"])
                self.assertTrue(inapplicable["value"]["matched"])
                self.assertFalse(inapplicable["value"]["applicable"])
                self.assertEqual(inapplicable["value"]["applicable_actions"], ["破土"])

        season_boundaries = (
            ("2024-02-09", 12, "winter"),
            ("2024-02-10", 1, "spring"),
            ("2024-05-07", 3, "spring"),
            ("2024-05-08", 4, "summer"),
            ("2024-08-03", 6, "summer"),
            ("2024-08-04", 7, "autumn"),
            ("2024-10-31", 9, "autumn"),
            ("2024-11-01", 10, "winter"),
        )
        for civil_date, lunar_month, expected_season in season_boundaries:
            with self.subTest(boundary=civil_date):
                facts = selection.build_day_record(
                    civil_date,
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    event_profile="burial_funeral",
                    requested_actions=["安葬"],
                )["event_specific_facts"]["sansang_day"]["value"]
                self.assertEqual(facts["lunar_month"], lunar_month)
                self.assertEqual(facts["season"], expected_season)

        leap = selection.build_day_record(
            "2023-03-23",
            timezone_name="Asia/Shanghai",
            location="上海",
            event_profile="burial_funeral",
            requested_actions=["安葬"],
        )
        self.assertTrue(leap["calendar"]["lunar_date"]["is_leap_month"])
        self.assertEqual(leap["event_specific_facts"]["sansang_day"]["value"]["season"], "spring")
        self.assertTrue(leap["event_specific_facts"]["sansang_day"]["active"])

    def test_folk_medical_evidence_requires_its_exact_calculated_predicate(self) -> None:
        rules = {
            item.local_rule_id: item
            for item in production_evidence_rules()
            if item.system == "selection"
            and item.local_rule_id in {"JR-11", "JR-12"}
        }

        def prepare(civil_date: str) -> PreparedReading:
            intent = _intent()
            intent["horizon"] = {
                "kind": "day",
                "start": civil_date,
                "end": civil_date,
            }
            request = _request(
                intent=intent,
                chart_data={
                    "selection_spec": _spec(
                        event_profile="medical",
                        date_range={"start": civil_date, "end": civil_date},
                        include_folk_comparison=True,
                    )
                },
            )
            with tempfile.TemporaryDirectory() as temporary:
                engine = build_production_engine(
                    skill_dir=ROOT, store_root=temporary
                )
                prepared = _prepare(engine, request)
            self.assertIsInstance(prepared, PreparedReading)
            return prepared

        taboo = prepare("2024-01-07")
        ordinary = prepare("2024-01-08")

        for rule in rules.values():
            # Folk medical rules stay runtime-inactive pending their
            # independent semantic source-and-applicability audit.
            self.assertFalse(rule.runtime_active)
            self.assertFalse(match_rule(rule, taboo.fact_index)[0])
        audited = {
            local_id: replace(rule, runtime_active=True)
            for local_id, rule in rules.items()
        }
        self.assertTrue(match_rule(audited["JR-11"], taboo.fact_index)[0])
        self.assertTrue(match_rule(audited["JR-12"], taboo.fact_index)[0])
        self.assertTrue(match_rule(audited["JR-11"], ordinary.fact_index)[0])
        self.assertFalse(match_rule(audited["JR-12"], ordinary.fact_index)[0])

    def test_refine_reuses_calculation_but_rebinds_latest_question(self) -> None:
        provider = SelectionProvider(ROOT)
        first = provider.calculate(_request())
        refined = provider.refine(
            _request(query="只比较前两名的官方宜忌", action="continue"),
            first,
        )

        self.assertEqual(refined.facts["chart_digest"], first.facts["chart_digest"])
        self.assertNotEqual(refined.result_hash, first.result_hash)
        self.assertIn("selection_candidates_reused_without_recalculation", refined.diagnostics)

    def test_bounded_extension_exposes_ranked_candidate_facts(self) -> None:
        provider = SelectionProvider(ROOT)
        base = provider.calculate(_request())
        result = provider.extend(
            base,
            ("timing", "state"),
            {"kind": "day", "start": "2026-07-24", "end": "2026-07-28"},
        )

        self.assertEqual(result.fact_extension.status, "complete")
        self.assertIn("calendar_candidates", result.fact_extension.facts)
        self.assertIn("ranking", result.fact_extension.facts)

    def test_month_extension_rebuilds_the_declared_calendar_range(self) -> None:
        provider = SelectionProvider(ROOT)
        base = provider.calculate(_request())

        result = provider.extend(
            base,
            ("timing", "state"),
            {"kind": "month", "start": "2026-07", "end": "2026-07"},
        )

        self.assertEqual(result.fact_extension.status, "complete")
        candidates = result.fact_extension.facts["calendar_candidates"]
        self.assertEqual(candidates[0]["civil_date"], "2026-07-01")
        self.assertEqual(candidates[-1]["civil_date"], "2026-07-31")
        self.assertEqual(len(candidates), 31)

    def test_selection_audit_rejects_a_base_day_wrapped_as_month_extension(self) -> None:
        horizon = {"kind": "month", "start": "2026-07", "end": "2026-07"}
        wrapped_base = {"calendar_candidates": [{"civil_date": "2026-07-24"}]}
        complete_month = {
            "calendar_candidates": [
                {"civil_date": f"2026-07-{day:02d}"} for day in range(1, 32)
            ]
        }

        self.assertFalse(
            audit_selection_provider._extension_covers_declared_range(
                wrapped_base, horizon
            )
        )
        self.assertTrue(
            audit_selection_provider._extension_covers_declared_range(
                complete_month, horizon
            )
        )

    def test_selection_audit_rejects_date_renamed_candidate_clones(self) -> None:
        provider = SelectionProvider(ROOT)
        base = provider.calculate(_request())
        horizon = {"kind": "month", "start": "2026-07", "end": "2026-07"}
        result = provider.extend(base, ("timing", "state"), horizon)
        facts = result.fact_extension.facts
        spec = base.facts["chart_facts"]["input"]["selection_spec"]

        self.assertTrue(
            audit_selection_provider._extension_samples_match_independent_build(
                facts,
                horizon,
                spec=spec,
                timezone_name="Asia/Shanghai",
                location="上海",
            )
        )
        forged = copy.deepcopy(facts)
        forged["calendar_candidates"][-1] = copy.deepcopy(
            forged["calendar_candidates"][0]
        )
        forged["calendar_candidates"][-1]["civil_date"] = "2026-07-31"
        self.assertFalse(
            audit_selection_provider._extension_samples_match_independent_build(
                forged,
                horizon,
                spec=spec,
                timezone_name="Asia/Shanghai",
                location="上海",
            )
        )

    def test_non_ziwei_target_date_nonce_is_never_calculated(self) -> None:
        provider = SelectionProvider(ROOT)
        base = provider.calculate(_request())

        result = provider.extend(
            base,
            ("timing", "state"),
            {
                "kind": "month",
                "start": "2026-07",
                "end": "2026-07",
                "target_date": "2026-07-24",
            },
        )

        self.assertEqual(result.fact_extension.status, "unsupported")
        self.assertEqual(result.fact_extension.facts, {})

    def test_adapter_validator_accepts_complete_facts_and_rejects_missing_hours(self) -> None:
        facts = SelectionProvider(ROOT).calculate(_request()).facts["chart_facts"]
        self.assertTrue(adapter_validate.validate_payload("selection", facts)["ok"])
        broken = copy.deepcopy(facts)
        broken["output"]["calendar_candidates"][0]["hour_facts"].pop()

        report = adapter_validate.validate_payload("selection", broken)

        self.assertFalse(report["ok"])
        self.assertIn("selection_invalid_hour_facts", report["codes"])

    def test_public_fact_profile_is_enforced_independently_of_rebuild(self) -> None:
        facts = SelectionProvider(ROOT).calculate(_request()).facts["chart_facts"]
        profile = yaml.safe_load(FACT_PROFILE.read_text(encoding="utf-8"))
        required = profile["base_required_fields"]

        self.assertTrue(set(required["adapter"]).issubset(facts["adapter"]))
        self.assertTrue(set(required["input"]).issubset(facts["input"]))
        self.assertTrue(
            set(required["calendar_normalization"]).issubset(
                facts["calendar_normalization"]
            )
        )
        self.assertTrue(
            set(required["candidate_record"]).issubset(
                facts["output"]["calendar_candidates"][0]
            )
        )
        self.assertTrue(
            set(required["date_time_candidate_record"]).issubset(
                facts["output"]["date_time_candidates"][0]
            )
        )

        broken_adapter = copy.deepcopy(facts)
        broken_adapter["adapter"].pop("license_status")
        broken_adapter["fact_digest"] = selection.fact_digest(broken_adapter)
        self.assertIn(
            "selection_schema_missing:adapter.license_status",
            selection.validate_fact_layer(broken_adapter)["codes"],
        )

        broken_candidate = copy.deepcopy(facts)
        broken_candidate["output"]["calendar_candidates"][0].pop("day_path")
        broken_candidate["fact_digest"] = selection.fact_digest(broken_candidate)
        self.assertIn(
            "selection_schema_missing:candidate_record.day_path",
            selection.validate_fact_layer(broken_candidate)["codes"],
        )

    def test_source_plan_requires_complete_deterministic_layers(self) -> None:
        contract = SelectionProvider.SOURCE_ROUTE
        self.assertEqual(
            contract["chart"]["required_fields"],
            [
                "event_profile",
                "calendar_candidates",
                "date_time_candidates",
                "eligible_candidates",
                "eligible_date_time_candidates",
                "eliminations",
                "ranking",
                "lineage_policy",
                "source_conditioned_patterns",
            ],
        )

    def test_source_plan_activates_folk_books_only_for_explicit_comparison(self) -> None:
        goal = {
            "evidence_questions": ["候选日的官方与民俗依据分别是什么"],
            "question_dimensions": ["timing"],
            "requested_dimensions": ["timing"],
            "calculation_object": "calendar_choice",
        }
        official_facts = selection.build_fact_layer(
            _spec(include_folk_comparison=False),
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        comparison_facts = selection.build_fact_layer(
            _spec(include_folk_comparison=True),
            timezone_name="Asia/Shanghai",
            location="上海",
        )

        official = reading_source_plan.compile_source_plan(
            "selection", goal, {"chart_facts": official_facts}
        )
        compared = reading_source_plan.compile_source_plan(
            "selection", goal, {"chart_facts": comparison_facts}
        )

        self.assertEqual(
            official["required_packs"],
            ["selection/xieji-bianfang-shu", "selection/xingli-kaoyuan"],
        )
        self.assertEqual(official["comparison_packs"], [])
        self.assertEqual(
            compared["comparison_packs"],
            ["selection/yuqia-ji", "selection/donggong-zeri"],
        )

    def test_legacy_structured_adapter_rejects_selection(self) -> None:
        with self.assertRaises(ValueError):
            structured_chart_adapter.build_payload(
                "selection",
                {
                    "provenance": {
                        "source_type": "user_text",
                        "calculation_status": "not_recalculated",
                        "raw_excerpt": "fake",
                        "uncertainties": [],
                    },
                    "calendar_normalization": {"status": "supplied"},
                    "output": {},
                },
            )

    def test_production_matrices_name_the_real_provider_and_no_semantic_gate(self) -> None:
        for path in (*SELECTION_CONTRACT_DOCS, *ACTIVE_SELECTION_DOCS):
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("tool.selection.lisuan", content)
                self.assertNotIn("gate_check.py --mode answer", content)


if __name__ == "__main__":
    unittest.main()
