#!/usr/bin/env python3
"""Task 7J regressions for the deterministic annual Taiyi provider."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

import adapter_validate
import audit_taiyi_provider
import reading_evidence_bundle
import reading_source_plan
from reading_engine import calendar_core, taiyi
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.evidence_rules import match_rule, production_evidence_rules
from reading_engine.factory import build_production_engine
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import STRUCTURED_SYSTEMS, TaiyiProvider
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/taiyi-v51.yaml"


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _intent() -> dict:
    return {
        "subject_refs": ["annual-macro-period"],
        "calculation_object": "macro_historical",
        "question_dimensions": ["state", "timing"],
        "horizon": {"kind": "year", "start": "2024", "end": "2024"},
        "requested_method": "taiyi",
        "requested_granularity": "period",
        "continuity": {
            "reading_id": None,
            "same_subject": False,
            "same_event": False,
        },
        "facts_present": ["reference_datetime", "timezone", "location"],
        "facts_corrected": [],
        "evidence_questions": ["这个年局的确定性盘面与原典条件是什么"],
    }


def _request(**changes: object) -> ReadingRequest:
    payload = {
        "query": "按太乙金镜式经核对这个年局",
        "action": "new",
        "system": "taiyi",
        "intent": _intent(),
        "reference_datetime": "2024-06-21T12:00:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    payload.update(changes)
    return ReadingRequest(**payload)


class TaiyiFixtureContractTests(unittest.TestCase):
    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_taiyi_provider.audit_taiyi_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["counts"]["annual_source_boards"], 72)
        self.assertEqual(report["counts"]["external_reference_boards"], 30)
        self.assertEqual(report["counts"]["external_reference_mismatches"], 0)
        self.assertGreaterEqual(report["counts"]["calendar_boundaries"], 10)
        self.assertEqual(report["counts"]["cycle_positions"], 360)
        self.assertEqual(report["counts"]["long_cycle_years"], 360)
        self.assertEqual(report["counts"]["long_cycle_comparisons"], 3600)
        self.assertEqual(report["counts"]["long_cycle_mismatches"], 0)
        self.assertEqual(report["counts"]["external_raw_boards"], 72)
        self.assertEqual(report["counts"]["external_raw_mismatches"], 0)
        self.assertEqual(report["counts"]["predicate_boards"], 72)
        self.assertEqual(report["counts"]["predicate_mismatches"], 0)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 6)
        self.assertEqual(report["findings"], [])

    def test_audit_rejects_any_source_contract_artifact_mutation(self) -> None:
        source_path = ROOT / "references/matrices/taiyi-source-tables-v1.yaml"
        source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        mutations = {
            "formula_contract": lambda payload: payload["formula_contracts"].__setitem__(
                "bureau", "one_based_mod(accumulated_year + 1, 72)"
            ),
            "predicate_source_anchor": lambda payload: payload[
                "board_predicate_contracts"
            ][0].__setitem__("source_anchor", "L999"),
            "primary_source_identity": lambda payload: payload["source_profiles"][
                "taiyi_jinjing"
            ].__setitem__("sha256", "0" * 64),
        }

        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / source_path.name
            for name, mutate in mutations.items():
                with self.subTest(mutation=name):
                    payload = copy.deepcopy(source)
                    mutate(payload)
                    mutated_path.write_text(
                        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                        encoding="utf-8",
                    )
                    report = audit_taiyi_provider.audit_taiyi_provider(
                        source_table_path=mutated_path
                    )
                    self.assertFalse(report["provider_ready"], report)
                    self.assertIn(
                        "Taiyi source-table artifact hash mismatch",
                        report["findings"],
                    )

    def test_audit_rejects_external_reference_identity_mutation(self) -> None:
        fixture = _fixture()
        fixture["external_reference"]["commit"] = "0" * 40
        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / FIXTURE.name
            mutated_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_taiyi_provider.audit_taiyi_provider(
                fixture_path=mutated_path
            )

        self.assertFalse(report["provider_ready"], report)
        self.assertIn("Taiyi fixture artifact hash mismatch", report["findings"])

    def test_all_72_source_rows_are_recomputed_as_complete_boards(self) -> None:
        rows = taiyi.source_table()["annual_yang_72_source_rows"]
        self.assertEqual([row["bureau"] for row in rows], list(range(1, 73)))
        for row in rows:
            with self.subTest(bureau=row["bureau"]):
                board = taiyi.build_annual_board_from_accumulated_year(
                    int(row["bureau"])
                )
                self.assertEqual(
                    {
                        key: board[key]
                        for key in (
                            "taiyi",
                            "tianmu",
                            "tianmu_position",
                            "host_count",
                            "host_general",
                            "host_assistant",
                            "shiji",
                            "guest_count",
                            "guest_general",
                            "guest_assistant",
                            "jishen",
                        )
                    },
                    {key: value for key, value in row.items() if key != "bureau"},
                )

    def test_complete_360_year_cycle_preserves_all_independent_dimensions(self) -> None:
        states = [
            taiyi.build_annual_board_from_accumulated_year(year)["cycle"]
            for year in range(1, 361)
        ]

        self.assertEqual({row["ji"] for row in states}, set(range(1, 7)))
        self.assertEqual({row["zi_yuan"] for row in states}, set(range(1, 6)))
        self.assertEqual({row["bureau"] for row in states}, set(range(1, 73)))
        self.assertEqual({row["governance"] for row in states}, {"理天", "理地", "理人"})

    def test_thirty_frozen_external_boards_match_the_released_formula(self) -> None:
        for case in _fixture()["external_reference_cases"]:
            with self.subTest(case=case["id"]):
                board = taiyi.build_annual_board(int(case["lunar_year"]))
                self.assertEqual(board["cycle"]["bureau"], case["bureau"])
                self.assertEqual(
                    {
                        key: board[key]
                        for key in case["expected"]
                    },
                    case["expected"],
                )

    def test_calendar_boundaries_use_lunar_new_year_only(self) -> None:
        for case in _fixture()["calendar_boundary_cases"]:
            with self.subTest(case=case["id"]):
                calendar = calendar_core.normalize_calendar(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location=case["location"],
                )
                facts = taiyi.build_fact_layer(calendar)
                self.assertEqual(
                    facts["output"]["cycle"]["bureau"],
                    case["expected_bureau"],
                )
                self.assertEqual(
                    facts["output"]["calendar"]["lunar_year"],
                    case["expected_lunar_year"],
                )

    def test_long_cycle_deities_keep_their_four_epoch_profiles_separate(self) -> None:
        board = taiyi.build_annual_board(724)
        deities = board["long_cycle_deities"]

        self.assertEqual(
            board["epoch"]["accumulated_year"],
            1_937_281,
        )
        self.assertEqual(
            {row["epoch_profile"] for row in deities.values()},
            {
                "upper-jiayin-long-cycle-v1",
                "wufu-dayou-long-cycle-v1",
                "xiaoyou-four-deity-v1",
            },
        )
        self.assertEqual(
            set(deities),
            {
                "junji",
                "chenji",
                "minji",
                "wufu",
                "dayou",
                "xiaoyou",
                "sishen",
                "tianyi",
                "diyi",
                "zhifu",
            },
        )

    def test_board_predicates_are_exact_fact_relations_not_verdicts(self) -> None:
        covered = set()
        for bureau in range(1, 73):
            board = taiyi.build_annual_board_from_accumulated_year(bureau)
            for predicate in board["board_predicates"]:
                covered.add(predicate["id"])
                self.assertEqual(
                    predicate["status"],
                    "predicate_matched_not_verdict",
                )
                self.assertTrue(predicate["fact_paths"])
                self.assertNotIn("verdict", predicate)

        self.assertEqual(covered, set(taiyi.BOARD_PREDICATE_IDS))
        self.assertIn(
            "TY-P01",
            {
                row["id"]
                for row in taiyi.build_annual_board_from_accumulated_year(33)[
                    "board_predicates"
                ]
            },
        )
        self.assertNotIn(
            "TY-P01",
            {
                row["id"]
                for row in taiyi.build_annual_board_from_accumulated_year(1)[
                    "board_predicates"
                ]
            },
        )

    def test_same_input_has_identical_nested_digests(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-06-21T12:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        first = taiyi.build_fact_layer(calendar)
        second = taiyi.build_fact_layer(copy.deepcopy(calendar))

        self.assertEqual(first, second)
        self.assertEqual(first["fact_digest"], second["fact_digest"])
        self.assertEqual(
            first["output"]["board_digest"],
            second["output"]["board_digest"],
        )
        self.assertTrue(taiyi.validate_fact_layer(first)["ok"])

    def test_validation_rebuilds_the_board_and_rejects_nested_tampering(self) -> None:
        calendar = calendar_core.normalize_calendar(
            "2024-06-21T12:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        facts = taiyi.build_fact_layer(calendar)
        tampered = copy.deepcopy(facts)
        tampered["output"]["host_guest"]["host"]["count"] += 1
        tampered["output"]["board_digest"] = taiyi.board_digest(
            tampered["output"]
        )
        tampered["fact_digest"] = taiyi.fact_digest(tampered)

        report = taiyi.validate_fact_layer(tampered)

        self.assertFalse(report["ok"])
        self.assertIn("taiyi_board_facts_mismatch", report["codes"])


class TaiyiProviderActivationTests(unittest.TestCase):
    def test_taiyi_is_a_scoped_calculation_capability(self) -> None:
        capability = PROVIDER_CAPABILITIES["taiyi"]

        self.assertEqual(capability.mode, "calculation")
        self.assertEqual(capability.objects, ("macro_historical",))
        self.assertEqual(capability.horizons, ("year",))
        self.assertEqual(
            capability.required_inputs,
            ("reference_datetime", "timezone", "location"),
        )
        self.assertNotIn("taiyi", STRUCTURED_SYSTEMS)

    def test_supplied_chart_cannot_substitute_for_required_calendar_inputs(self) -> None:
        empty = _request(reference_datetime=None, timezone=None, location=None)
        supplied = _request(
            reference_datetime=None,
            timezone=None,
            location=None,
            chart_data={"ju": "一局", "taiyi_position": "乾"},
        )

        self.assertEqual(
            missing_required_inputs("taiyi", empty),
            ("reference_datetime", "timezone", "location"),
        )
        self.assertEqual(
            missing_required_inputs("taiyi", supplied),
            missing_required_inputs("taiyi", empty),
        )

    def test_provider_calculates_without_chart_data_and_ignores_fake_chart(self) -> None:
        provider = TaiyiProvider(ROOT)
        calculated = provider.calculate(_request())
        fake = provider.calculate(_request(chart_data={"ju": "伪造局"}))

        self.assertEqual(calculated.provider_id, "mingli-master.taiyi.v1")
        self.assertEqual(calculated.facts["chart_digest"], fake.facts["chart_digest"])
        self.assertNotIn("validated_user_provided_chart", calculated.diagnostics)
        self.assertEqual(
            calculated.facts["chart_facts"]["fact_layer_status"],
            "deterministic_taiyi_annual_board",
        )

    def test_factory_registers_the_deterministic_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)

        self.assertIsInstance(engine.providers["taiyi"], TaiyiProvider)

    def test_refine_reuses_the_board_but_rebinds_the_latest_question(self) -> None:
        provider = TaiyiProvider(ROOT)
        first = provider.calculate(_request())
        refined = provider.refine(
            _request(query="只追问这个年局的天目与客目", action="continue"),
            first,
        )

        self.assertEqual(refined.facts["chart_digest"], first.facts["chart_digest"])
        self.assertEqual(refined.facts["calendar_digest"], first.facts["calendar_digest"])
        self.assertNotEqual(refined.result_hash, first.result_hash)
        self.assertIn("taiyi_board_reused_without_recalculation", refined.diagnostics)

    def test_year_extension_exposes_calculated_scope_without_event_verdict(self) -> None:
        provider = TaiyiProvider(ROOT)
        base = provider.calculate(_request())
        result = provider.extend(base, ("state", "timing"), {"kind": "year"})

        self.assertEqual(result.fact_extension.status, "complete")
        extension = result.fact_extension.facts
        self.assertEqual(extension["status"], "calculated_annual_board_scope_not_verdict")
        self.assertIn("board", extension)
        self.assertNotIn("prediction", extension)

    def test_personal_or_event_scope_is_not_claimed_by_the_provider(self) -> None:
        capability = PROVIDER_CAPABILITIES["taiyi"]
        self.assertNotIn("natal", capability.objects)
        self.assertNotIn("near_time_personal", capability.objects)
        self.assertNotIn("concrete_event", capability.objects)

    def test_adapter_validator_rejects_incomplete_deterministic_board(self) -> None:
        facts = TaiyiProvider(ROOT).calculate(_request()).facts["chart_facts"]
        self.assertTrue(adapter_validate.validate_payload("taiyi", facts)["ok"])
        broken = copy.deepcopy(facts)
        del broken["output"]["long_cycle_deities"]["wufu"]

        report = adapter_validate.validate_payload("taiyi", broken)
        self.assertFalse(report["ok"])
        self.assertIn("taiyi_invalid_long_cycle_deities", report["codes"])

    def test_source_plan_requires_the_exact_deterministic_output_layers(self) -> None:
        contract = TaiyiProvider.SOURCE_ROUTE
        self.assertEqual(
            contract["chart"]["required_fields"],
            [
                "calendar",
                "epoch",
                "cycle",
                "board",
                "host_guest",
                "long_cycle_deities",
                "scope_contract",
            ],
        )


class TaiyiEvidenceActivationTests(unittest.TestCase):
    def _calculation(self, bureau: int) -> CalculationResult:
        output = taiyi.build_annual_board_from_accumulated_year(bureau)
        return CalculationResult.create(
            system="taiyi",
            provider_id=TaiyiProvider.provider_id,
            provider_version=TaiyiProvider.provider_version,
            input_payload={"bureau": bureau},
            facts={"chart_facts": {"output": output}},
        )

    def test_every_taiyi_rule_requires_a_calculated_fact_or_scope_identity(self) -> None:
        rules = [
            rule
            for rule in production_evidence_rules()
            if rule.source_pack == "san-shi/taiyi-shenshu"
        ]

        self.assertGreaterEqual(len(rules), len(taiyi.BOARD_PREDICATE_IDS))
        for rule in rules:
            with self.subTest(rule=rule.local_rule_id):
                self.assertTrue(rule.required_fact_predicates)

    def test_relation_evidence_activates_only_on_the_matching_board(self) -> None:
        rule = next(
            rule
            for rule in production_evidence_rules()
            if rule.rule_id == "san-shi/taiyi-shenshu#TY-P01"
        )
        matched = build_fact_index(
            self._calculation(33), reading_id="t" * 32, version=1
        )
        unmatched = build_fact_index(
            self._calculation(1), reading_id="u" * 32, version=1
        )

        self.assertTrue(match_rule(rule, matched)[0])
        self.assertFalse(match_rule(rule, unmatched)[0])

    def test_personal_scope_returns_zero_taiyi_evidence(self) -> None:
        calculation = self._calculation(33)
        goal = {
            "source_packs": ["san-shi/taiyi-shenshu"],
            "calculation_object": "natal",
            "question_dimensions": ["relationship"],
            "evidence_questions": ["我的个人感情会如何"],
        }
        plan = reading_source_plan.compile_source_plan(
            "taiyi", goal, calculation.facts
        )
        facts = build_fact_index(
            calculation, reading_id="v" * 32, version=1
        )
        bundle = reading_evidence_bundle.compile_evidence_bundle(
            goal,
            calculation.facts,
            plan,
            fact_index=facts,
            reading_id="v" * 32,
            version=1,
        )

        self.assertEqual(bundle.evidence, ())


if __name__ == "__main__":
    unittest.main()
