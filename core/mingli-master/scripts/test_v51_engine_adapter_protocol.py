"""Focused contract tests for the Provider-internal chart-engine seam."""

from __future__ import annotations

import copy
import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bazi_fact_adapter
import ziwei_fact_adapter
from fact_contracts.bazi import BaziCanonicalFacts, BaziFactContract
from fact_contracts.common import (
    CanonicalFactsError,
    EngineProvenance,
)
from fact_contracts.ziwei import ZiweiCanonicalFacts, ZiweiFactContract
from reading_engine.engine_adapter import (
    EngineAdapter,
    EngineAdapterBase,
    EngineAdapterError,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "references" / "fixtures" / "oss-chart-wave0"


def _fixture(case_id: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{case_id}.json").read_text(encoding="utf-8"))


def _provenance(case: dict[str, Any]) -> EngineProvenance:
    runtime = case["provenance"]["runtime"]
    return EngineProvenance(
        engine_id=runtime["engine_id"],
        engine_version=runtime["engine_version"],
        policy_profile=runtime["policy_profile"],
        time_basis=runtime["time_basis"],
    )


@dataclass(frozen=True)
class _FakeCanonicalFacts:
    provenance: EngineProvenance
    value: str


class _RawThirdPartyValue:
    pass


class _HappyFakeAdapter(
    EngineAdapterBase[str, dict[str, str], _RawThirdPartyValue, _FakeCanonicalFacts]
):
    art_id = "fixture"

    def _build_engine_request(self, request: str) -> dict[str, str]:
        return {"owned": request}

    def _invoke_engine(self, request: dict[str, str]) -> _RawThirdPartyValue:
        if request != {"owned": "normalized"}:
            raise AssertionError("owned request changed")
        return _RawThirdPartyValue()

    def _project_engine_output(
        self,
        request: str,
        output: _RawThirdPartyValue,
        provenance: EngineProvenance,
    ) -> _FakeCanonicalFacts:
        if request != "normalized" or not isinstance(output, _RawThirdPartyValue):
            raise AssertionError("private lifecycle was not preserved")
        return _FakeCanonicalFacts(provenance=provenance, value="projected")

    def _provenance(self, request: str) -> EngineProvenance:
        if request != "normalized":
            raise AssertionError("unexpected normalized request")
        return EngineProvenance(
            engine_id="fixture-engine",
            engine_version="1.0",
            policy_profile="fixture-policy",
            time_basis="civil",
        )


class _FailingFakeAdapter(_HappyFakeAdapter):
    def _invoke_engine(self, request: dict[str, str]) -> _RawThirdPartyValue:
        del request
        raise RuntimeError("third-party raw exception detail")


class _ValueErrorFailingFakeAdapter(_HappyFakeAdapter):
    def _invoke_engine(self, request: dict[str, str]) -> _RawThirdPartyValue:
        del request
        raise ValueError("third-party-secret-detail")


class _OwnedPolicyFailingFakeAdapter(_HappyFakeAdapter):
    def __init__(self) -> None:
        self.engine_invoked = False

    def _invoke_engine(self, request: dict[str, str]) -> _RawThirdPartyValue:
        self.engine_invoked = True
        return super()._invoke_engine(request)

    def _provenance(self, request: str) -> EngineProvenance:
        del request
        raise ValueError("owned policy validation failed")


class EngineAdapterProtocolTests(unittest.TestCase):
    def test_protocol_exposes_only_normalized_request_and_canonical_result(self) -> None:
        adapter = _HappyFakeAdapter()

        self.assertIsInstance(adapter, EngineAdapter)
        result = adapter.adapt("normalized")

        self.assertEqual(result.canonical_facts.value, "projected")
        self.assertEqual(result.provenance, result.canonical_facts.provenance)
        self.assertFalse(hasattr(result, "engine_output"))
        self.assertNotIn(
            "_RawThirdPartyValue",
            repr(result),
        )

    def test_third_party_exception_is_normalized_at_the_seam(self) -> None:
        with self.assertRaises(EngineAdapterError) as raised:
            _FailingFakeAdapter().adapt("normalized")

        self.assertEqual(raised.exception.code, "engine_execution_failed")
        self.assertNotIn("third-party raw exception detail", str(raised.exception))

    def test_third_party_value_error_is_normalized_without_retained_detail(
        self,
    ) -> None:
        with self.assertRaises(EngineAdapterError) as raised:
            _ValueErrorFailingFakeAdapter().adapt("normalized")

        error = raised.exception
        self.assertEqual(error.code, "engine_execution_failed")
        self.assertNotIn("third-party-secret-detail", str(error))
        self.assertNotIn("ValueError", repr(error))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def test_owned_policy_validation_finishes_before_engine_invocation(self) -> None:
        adapter = _OwnedPolicyFailingFakeAdapter()

        with self.assertRaisesRegex(ValueError, "owned policy validation failed"):
            adapter.adapt("normalized")

        self.assertFalse(adapter.engine_invoked)

    def test_bazi_and_ziwei_adapters_satisfy_the_same_minimal_protocol(self) -> None:
        self.assertIsInstance(bazi_fact_adapter.BaziEngineAdapter(), EngineAdapter)
        self.assertIsInstance(ziwei_fact_adapter.ZiweiEngineAdapter(), EngineAdapter)


class ArtSpecificCanonicalFactsTests(unittest.TestCase):
    def test_art_contracts_bind_distinct_nominal_fact_types(self) -> None:
        bazi_case = _fixture("bazi-normal-civil")
        ziwei_case = _fixture("ziwei-normal-civil")

        bazi = BaziFactContract().bind_canonical_facts(
            bazi_case["expected_canonical_facts"],
            _provenance(bazi_case),
        )
        ziwei = ZiweiFactContract().bind_canonical_facts(
            ziwei_case["expected_canonical_facts"],
            _provenance(ziwei_case),
        )

        self.assertIsInstance(bazi, BaziCanonicalFacts)
        self.assertNotIsInstance(bazi, ZiweiCanonicalFacts)
        self.assertIsInstance(ziwei, ZiweiCanonicalFacts)
        self.assertNotIsInstance(ziwei, BaziCanonicalFacts)
        self.assertEqual(
            bazi.to_payload(),
            bazi_case["expected_canonical_facts"],
        )
        self.assertEqual(
            ziwei.to_payload(),
            ziwei_case["expected_canonical_facts"],
        )

    def test_provenance_is_complete_and_cannot_be_selected_by_engine_output(self) -> None:
        for case_id, contract, engine_path in (
            (
                "bazi-normal-civil",
                BaziFactContract(),
                ("calendar_normalization", "calendar_convention", "engine"),
            ),
            (
                "ziwei-normal-civil",
                ZiweiFactContract(),
                ("adapter", "engine_contract", "name"),
            ),
        ):
            case = _fixture(case_id)
            provenance = _provenance(case)
            for field in (
                provenance.engine_id,
                provenance.engine_version,
                provenance.policy_profile,
                provenance.time_basis,
            ):
                self.assertTrue(field)
            hostile = copy.deepcopy(case["expected_canonical_facts"])
            target = hostile
            for key in engine_path[:-1]:
                target = target[key]
            target[engine_path[-1]] = "raw-output-selected-engine"

            with self.subTest(case=case_id):
                with self.assertRaises(CanonicalFactsError):
                    contract.bind_canonical_facts(hostile, provenance)

    def test_third_party_raw_containers_and_runtime_objects_fail_closed(self) -> None:
        case = _fixture("ziwei-normal-civil")
        provenance = _provenance(case)
        raw_json = copy.deepcopy(case["expected_canonical_facts"])
        raw_json["engine_raw_json"] = {"palaces": []}
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(raw_json, provenance)

        raw_object = copy.deepcopy(case["expected_canonical_facts"])
        raw_object["output"]["third_party_runtime_object"] = _RawThirdPartyValue()
        with self.assertRaises(CanonicalFactsError):
            ZiweiFactContract().bind_canonical_facts(raw_object, provenance)

    def test_canonical_fact_fields_are_closed_to_unknown_json_containers(
        self,
    ) -> None:
        for case_id, contract in (
            ("bazi-normal-civil", BaziFactContract()),
            ("ziwei-normal-civil", ZiweiFactContract()),
        ):
            case = _fixture(case_id)
            provenance = _provenance(case)
            for target in ("root", "output"):
                hostile = copy.deepcopy(case["expected_canonical_facts"])
                container = hostile if target == "root" else hostile["output"]
                container["third_party_payload"] = {
                    "raw": {"palaces": []},
                }

                with self.subTest(case=case_id, target=target):
                    with self.assertRaises(CanonicalFactsError):
                        contract.bind_canonical_facts(hostile, provenance)

    def test_canonical_fact_snapshots_are_detached_from_mutable_input(self) -> None:
        case = _fixture("bazi-normal-civil")
        payload = copy.deepcopy(case["expected_canonical_facts"])
        bound = BaziFactContract().bind_canonical_facts(
            payload,
            _provenance(case),
        )

        payload["output"]["four_pillars"]["year"] = "甲子"

        self.assertNotEqual(
            bound.to_payload()["output"]["four_pillars"]["year"],
            "甲子",
        )


if __name__ == "__main__":
    unittest.main()
