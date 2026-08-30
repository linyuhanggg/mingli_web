#!/usr/bin/env python3
"""MING-71 Ziwei Provider single-fact-source migration regressions."""

from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import adapter_validate
import ziwei_fact_adapter
from fact_contracts.common import CanonicalFactsError, EngineProvenance
from fact_contracts.ziwei import ZiweiCanonicalFacts, ZiweiFactContract
from reading_engine.contracts import ReadingRequest
from reading_engine.providers import ZiweiProvider
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
        query="排紫微盘",
        action="new",
        system="ziwei",
        timezone=str(case_kwargs["timezone_name"]),
        location=str(case_kwargs["location"]),
        birth_data=birth,
    )


class Ming71ZiweiEngineAdapterMigrationTests(unittest.TestCase):
    def test_adapter_has_no_legacy_payload_binding_entrypoint(self) -> None:
        self.assertNotIn(
            "bind_canonical_facts",
            ziwei_fact_adapter.ZiweiEngineAdapter.__dict__,
        )

    def test_provider_replays_wave0_through_the_engine_adapter(self) -> None:
        fixtures = {case["case_id"]: case for case in _load_cases()}
        ziwei_cases = [case for case in CASES if case.system == "ziwei"]
        original = ziwei_fact_adapter.ZiweiEngineAdapter.adapt
        requests: list[object] = []

        def tracked(adapter: object, request: object) -> object:
            requests.append(request)
            return original(adapter, request)  # type: ignore[arg-type]

        with patch.object(
            ziwei_fact_adapter.ZiweiEngineAdapter,
            "adapt",
            new=tracked,
        ):
            for definition in ziwei_cases:
                with self.subTest(case=definition.case_id):
                    result = ZiweiProvider(ROOT).calculate(
                        _request(dict(definition.kwargs))
                    )
                    actual = copy.deepcopy(result.facts["chart_facts"])
                    actual["adapter"].pop("generated_at", None)
                    self.assertEqual(
                        actual,
                        fixtures[definition.case_id]["expected_canonical_facts"],
                    )
                    self.assertTrue(
                        FORBIDDEN_RAW_KEYS.isdisjoint(_walk_keys(actual))
                    )

        self.assertEqual(len(requests), len(ziwei_cases))
        self.assertTrue(
            all(
                isinstance(
                    request,
                    ziwei_fact_adapter.ZiweiNormalizedEngineRequest,
                )
                for request in requests
            )
        )

    def test_provider_temporal_extension_uses_the_same_typed_adapter(self) -> None:
        definition = next(case for case in CASES if case.system == "ziwei")
        provider = ZiweiProvider(ROOT)
        base = provider.calculate(_request(dict(definition.kwargs)))
        original = ziwei_fact_adapter.ZiweiEngineAdapter.adapt
        requests: list[object] = []

        def tracked(adapter: object, request: object) -> object:
            requests.append(request)
            return original(adapter, request)  # type: ignore[arg-type]

        with patch.object(
            ziwei_fact_adapter.ZiweiEngineAdapter,
            "adapt",
            new=tracked,
        ):
            extended = provider.extend(
                base,
                ("timing",),
                {"kind": "month", "start": "2026-07", "end": "2026-07"},
            )

        self.assertEqual(len(requests), 1)
        self.assertIsInstance(
            requests[0],
            ziwei_fact_adapter.ZiweiTemporalEngineRequest,
        )
        self.assertIsNotNone(extended.fact_extension)
        assert extended.fact_extension is not None
        facts = extended.fact_extension.facts
        self.assertEqual(
            facts["schema_version"],
            "mingli-ziwei-temporal-fact-v1",
        )
        self.assertTrue(adapter_validate.validate_ziwei_extension(facts)["ok"])
        self.assertTrue(FORBIDDEN_RAW_KEYS.isdisjoint(_walk_keys(facts)))

    def test_temporal_canonical_facts_fail_closed_on_raw_or_private_values(
        self,
    ) -> None:
        definition = next(case for case in CASES if case.system == "ziwei")
        base = ZiweiProvider(ROOT).calculate(_request(dict(definition.kwargs)))
        request = ziwei_fact_adapter.ZiweiTemporalEngineRequest.for_horizon(
            base.facts["chart_facts"],
            {"kind": "month", "start": "2026-07", "end": "2026-07"},
        )
        result = ziwei_fact_adapter.ZiweiEngineAdapter().adapt(request)

        self.assertIsInstance(result.canonical_facts, ZiweiCanonicalFacts)
        payload = result.canonical_facts.to_payload()
        self.assertEqual(payload["schema_version"], "mingli-ziwei-temporal-fact-v1")

        raw = copy.deepcopy(payload)
        raw["engine_raw_json"] = {"requestedHoroscopes": {}}
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(raw, result.provenance)

        nested = copy.deepcopy(payload)
        nested["active_major_limit_segments"][0]["major_limit"][
            "third_party_payload"
        ] = {"raw": True}
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(nested, result.provenance)

        runtime_object = copy.deepcopy(payload)
        runtime_object["active_major_limit"]["name"] = object()
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(
                runtime_object,
                result.provenance,
            )

        forged_provenance = EngineProvenance(
            engine_id="forged-engine",
            engine_version=result.provenance.engine_version,
            policy_profile=result.provenance.policy_profile,
            time_basis=result.provenance.time_basis,
        )
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(
                payload,
                forged_provenance,
            )

    def test_historical_shanghai_dst_stays_in_the_owned_time_normalizer(
        self,
    ) -> None:
        result = ZiweiProvider(ROOT).calculate(
            ReadingRequest(
                query="历史时区边界",
                action="new",
                system="ziwei",
                timezone="Asia/Shanghai",
                location="synthetic:shanghai-1945-dst",
                birth_data={
                    "birth_datetime": "1945-08-15T12:00:00",
                    "timezone": "Asia/Shanghai",
                    "location": "synthetic:shanghai-1945-dst",
                    "gender": "female",
                    "zi_hour_policy": "midnight",
                    "time_basis_policy": "civil",
                },
            )
        )

        facts = result.facts["chart_facts"]
        calendar = facts["calendar_normalization"]
        self.assertEqual(calendar["timezone_offset_seconds"], 9 * 60 * 60)
        self.assertEqual(calendar["dst_offset_seconds"], 60 * 60)
        self.assertEqual(
            calendar["timezone_details"]["standard_offset_seconds"],
            8 * 60 * 60,
        )
        self.assertEqual(calendar["time_basis"]["policy"], "civil")
        self.assertEqual(
            facts["adapter"]["engine_contract"]["name"],
            "iztro",
        )

    def test_target_snapshot_compatibility_facade_uses_the_typed_adapter(
        self,
    ) -> None:
        definition = next(case for case in CASES if case.system == "ziwei")
        base = ZiweiProvider(ROOT).calculate(_request(dict(definition.kwargs)))
        original = ziwei_fact_adapter.ZiweiEngineAdapter.adapt
        requests: list[object] = []
        results: list[object] = []

        def tracked(adapter: object, request: object) -> object:
            requests.append(request)
            result = original(adapter, request)  # type: ignore[arg-type]
            results.append(result)
            return result

        with patch.object(
            ziwei_fact_adapter.ZiweiEngineAdapter,
            "adapt",
            new=tracked,
        ):
            snapshot = ziwei_fact_adapter.build_target_fact_snapshot(
                base.facts["chart_facts"],
                "2026-07-15",
            )

        self.assertEqual(len(requests), 1)
        self.assertIsInstance(
            requests[0],
            ziwei_fact_adapter.ZiweiTemporalEngineRequest,
        )
        self.assertEqual(snapshot["schema_version"], "mingli-ziwei-target-fact-v1")
        self.assertTrue(FORBIDDEN_RAW_KEYS.isdisjoint(_walk_keys(snapshot)))
        target_result = results[0]
        self.assertIsInstance(target_result.canonical_facts, ZiweiCanonicalFacts)

        raw = copy.deepcopy(snapshot)
        raw["monthly"]["engine_raw_json"] = {}
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(
                raw,
                target_result.provenance,
            )

        invalid_date = copy.deepcopy(snapshot)
        invalid_date["target_date"] = 20260715
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(
                invalid_date,
                target_result.provenance,
            )


if __name__ == "__main__":
    unittest.main()
