#!/usr/bin/env python3
"""MING-69 Bazi Provider migration regressions."""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import bazi_fact_adapter
from reading_engine.contracts import ReadingRequest
from reading_engine.providers import BaziProvider, _public_calendar_normalization
from test_oss_chart_wave0_golden_baseline import (
    CASES,
    FORBIDDEN_RAW_KEYS,
    _load_cases,
    _walk_keys,
)


ROOT = Path(__file__).resolve().parents[1]


def _request(case_kwargs: dict[str, object]) -> ReadingRequest:
    birth = {
        "birth_datetime": case_kwargs["civil_datetime"],
        "timezone": case_kwargs["timezone_name"],
        "location": case_kwargs["location"],
        "gender": case_kwargs["gender"],
        "zi_hour_policy": case_kwargs["zi_hour_policy"],
        "time_basis_policy": case_kwargs["time_basis_policy"],
        "longitude": case_kwargs["longitude"],
        "latitude": case_kwargs["latitude"],
        "coordinate_source": case_kwargs["coordinate_source"],
    }
    return ReadingRequest(
        query="排八字",
        action="new",
        system="bazi",
        timezone=str(case_kwargs["timezone_name"]),
        location=str(case_kwargs["location"]),
        birth_data=birth,
    )


class Ming69BaziEngineAdapterMigrationTests(unittest.TestCase):
    def test_adapter_has_no_legacy_payload_binding_entrypoint(self) -> None:
        self.assertNotIn(
            "bind_canonical_facts",
            bazi_fact_adapter.BaziEngineAdapter.__dict__,
        )

    def test_provider_replays_wave0_without_the_legacy_subprocess_source(self) -> None:
        fixtures = {case["case_id"]: case for case in _load_cases()}
        bazi_cases = [case for case in CASES if case.system == "bazi"]

        with patch(
            "reading_engine.providers.bazi_calc._run_adapter",
            side_effect=AssertionError("legacy Bazi subprocess was invoked"),
        ):
            for definition in bazi_cases:
                with self.subTest(case=definition.case_id):
                    result = BaziProvider(ROOT).calculate(
                        _request(dict(definition.kwargs))
                    )
                    actual = copy.deepcopy(result.facts["chart_facts"])
                    public_calendar = actual.pop("public_calendar_normalization")
                    actual["adapter"].pop("generated_at", None)

                    expected = fixtures[definition.case_id][
                        "expected_canonical_facts"
                    ]
                    self.assertEqual(actual, expected)
                    self.assertEqual(
                        public_calendar,
                        _public_calendar_normalization(
                            expected["calendar_normalization"]
                        ),
                    )
                    self.assertTrue(
                        FORBIDDEN_RAW_KEYS.isdisjoint(_walk_keys(actual))
                    )

    def test_supplied_pillars_also_bypass_the_legacy_subprocess_source(self) -> None:
        request = ReadingRequest(
            query="排八字",
            action="new",
            system="bazi",
            timezone="Asia/Shanghai",
            location="synthetic:supplied-pillars",
            birth_data={"gender": "male"},
            chart_data={"pillars": ["庚辰", "丙戌", "己酉", "丁卯"]},
        )
        with patch(
            "reading_engine.providers.bazi_calc._run_adapter",
            side_effect=AssertionError("legacy Bazi subprocess was invoked"),
        ):
            result = BaziProvider(ROOT).calculate(request)

        actual = copy.deepcopy(result.facts["chart_facts"])
        actual.pop("public_calendar_normalization")
        actual["adapter"].pop("generated_at", None)
        expected = bazi_fact_adapter.build_from_pillars(
            ["庚辰", "丙戌", "己酉", "丁卯"],
            gender="male",
            source="text",
            source_ref="user_text",
            question_contract={"domains": [], "gender": "male"},
        )
        expected["adapter"].pop("generated_at", None)

        self.assertEqual(actual, expected)
        self.assertEqual(actual["fact_layer_scope"], "natal_static")
        self.assertTrue(FORBIDDEN_RAW_KEYS.isdisjoint(_walk_keys(actual)))

    def test_provider_preserves_question_domain_routing(self) -> None:
        definition = next(case for case in CASES if case.system == "bazi")
        request = replace(
            _request(dict(definition.kwargs)),
            intent={
                "subject_refs": ["current_user"],
                "calculation_object": "natal",
                "question_dimensions": ["career"],
                "horizon": {"kind": "life", "start": None, "end": None},
                "requested_method": None,
                "requested_granularity": "directional",
                "continuity": {
                    "reading_id": None,
                    "same_subject": False,
                    "same_event": False,
                },
                "facts_present": [],
                "facts_corrected": [],
                "evidence_questions": [],
            },
        )

        facts = BaziProvider(ROOT).calculate(request).facts["chart_facts"]
        arbitration = facts["output"]["interpretive_candidates"][
            "reasoning_tools"
        ]["conflict_arbitration"]
        self.assertEqual(arbitration["output"]["requested_domains"], ["work"])

    def test_provider_preserves_birth_vs_pillars_conflict_stop(self) -> None:
        definition = next(case for case in CASES if case.system == "bazi")
        request = _request(dict(definition.kwargs))
        request = replace(
            request,
            birth_data={
                **request.birth_data,
                "expected_pillars": ["甲子", "乙丑", "丙寅", "丁卯"],
            },
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Bazi birth data conflict with the supplied four pillars",
        ):
            BaziProvider(ROOT).calculate(request)

    def test_provider_preserves_runtime_error_for_invalid_time_policy_input(
        self,
    ) -> None:
        definition = next(case for case in CASES if case.system == "bazi")
        request = _request(dict(definition.kwargs))
        request = replace(
            request,
            birth_data={
                **request.birth_data,
                "time_basis_policy": "local_apparent_solar-v1",
                "longitude": None,
                "latitude": None,
                "coordinate_source": None,
            },
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "local_apparent_solar-v1 requires measured coordinates",
        ):
            BaziProvider(ROOT).calculate(request)

    def test_day_extension_preserves_legacy_relation_order(self) -> None:
        definition = next(case for case in CASES if case.system == "bazi")
        provider = BaziProvider(ROOT)
        calculation = provider.calculate(_request(dict(definition.kwargs)))

        extended = provider.extend(
            calculation,
            ("timing",),
            {"kind": "day", "start": "2007-07-09", "end": "2007-07-09"},
        )
        extension = extended.fact_extension
        self.assertIsNotNone(extension)
        assert extension is not None
        relations = extension.facts["day_layers"]["2007-07-09"][
            "branch_relations"
        ]

        self.assertEqual(
            [
                (row["type"], row["natal_position"], row["natal_branch"])
                for row in relations
            ],
            [
                ("六合", "day", "酉"),
                ("六害", "hour", "卯"),
                ("六冲", "month", "戌"),
                ("自刑", "year", "辰"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
