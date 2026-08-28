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


@dataclass(frozen=True)
class _PrivateEngineRequest:
    normalized: str


class _RawThirdPartyValue:
    pass


class _HappyFakeAdapter(
    EngineAdapterBase[
        str,
        _PrivateEngineRequest,
        _RawThirdPartyValue,
        _FakeCanonicalFacts,
    ]
):
    art_id = "fixture"

    def _build_engine_request(self, request: str) -> _PrivateEngineRequest:
        return _PrivateEngineRequest(normalized=request)

    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        if request != _PrivateEngineRequest(normalized="normalized"):
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


class _OrderedHappyFakeAdapter(_HappyFakeAdapter):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def _build_engine_request(self, request: str) -> _PrivateEngineRequest:
        self.calls.append("build_request")
        return super()._build_engine_request(request)

    def _provenance(self, request: str) -> EngineProvenance:
        self.calls.append("provenance")
        return super()._provenance(request)

    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        self.calls.append("invoke")
        return super()._invoke_engine(request)

    def _project_engine_output(
        self,
        request: str,
        output: _RawThirdPartyValue,
        provenance: EngineProvenance,
    ) -> _FakeCanonicalFacts:
        self.calls.append("project")
        return super()._project_engine_output(request, output, provenance)


class _FailingFakeAdapter(_HappyFakeAdapter):
    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        del request
        raise RuntimeError("third-party raw exception detail")


class _ValueErrorFailingFakeAdapter(_HappyFakeAdapter):
    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        del request
        raise ValueError("third-party-secret-detail")


class _OwnedPolicyFailingFakeAdapter(_HappyFakeAdapter):
    def __init__(self) -> None:
        self.engine_invoked = False

    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        self.engine_invoked = True
        return super()._invoke_engine(request)

    def _provenance(self, request: str) -> EngineProvenance:
        del request
        raise ValueError("owned policy validation failed")


class _OwnedProvenanceCause(Exception):
    pass


class _OwnedProvenanceFailure(ValueError):
    pass


class _ProvenanceTracebackFailingFakeAdapter(_HappyFakeAdapter):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def _build_engine_request(self, request: str) -> _PrivateEngineRequest:
        self.calls.append("build_request")
        return _PrivateEngineRequest(normalized=f"private:{request}")

    def _provenance(self, request: str) -> EngineProvenance:
        self.calls.append("provenance")
        if request != "normalized":
            raise AssertionError("unexpected normalized request")
        try:
            raise _OwnedProvenanceCause("owned provenance cause")
        except _OwnedProvenanceCause as cause:
            raise _OwnedProvenanceFailure(
                "owned provenance validation failed"
            ) from cause

    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        self.calls.append("invoke")
        return super()._invoke_engine(request)


class _InvocationFailure(Exception):
    def __init__(self, private_request: _PrivateEngineRequest) -> None:
        super().__init__("invocation retained private request")
        self.private_request = private_request


class _InvocationTracebackFailingFakeAdapter(_HappyFakeAdapter):
    def _invoke_engine(
        self,
        request: _PrivateEngineRequest,
    ) -> _RawThirdPartyValue:
        raise _InvocationFailure(request)


class _ProjectionFailure(Exception):
    def __init__(self, private_output: _RawThirdPartyValue) -> None:
        super().__init__("projection retained private output")
        self.private_output = private_output


class _ProjectionFailingFakeAdapter(_HappyFakeAdapter):
    def _project_engine_output(
        self,
        request: str,
        output: _RawThirdPartyValue,
        provenance: EngineProvenance,
    ) -> _FakeCanonicalFacts:
        del request, provenance
        raise _ProjectionFailure(output)


class _ProvenanceMismatchFakeAdapter(_HappyFakeAdapter):
    def _project_engine_output(
        self,
        request: str,
        output: _RawThirdPartyValue,
        provenance: EngineProvenance,
    ) -> _FakeCanonicalFacts:
        del request, output, provenance
        return _FakeCanonicalFacts(
            provenance=EngineProvenance(
                engine_id="mismatched-engine",
                engine_version="9.9",
                policy_profile="mismatched-policy",
                time_basis="true_solar",
            ),
            value="projected-with-mismatched-provenance",
        )


def _reachable_private_adapter_state(value: object) -> str | None:
    """Name private adapter state reachable from one frame-local value."""

    pending = [value]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))

        if current is _PrivateEngineRequest:
            return "private request type"
        if current is _RawThirdPartyValue:
            return "private output type"
        if current is _InvocationFailure:
            return "original invocation exception type"
        if current is _ProjectionFailure:
            return "original projection exception type"
        if isinstance(current, _PrivateEngineRequest):
            return "private engine request"
        if isinstance(current, _RawThirdPartyValue):
            return "private engine output"
        if isinstance(current, _InvocationFailure):
            return "original invocation exception"
        if isinstance(current, _ProjectionFailure):
            return "original projection exception"
        if isinstance(current, str):
            if "invocation retained private request" in current:
                return "original invocation exception message"
            if "projection retained private output" in current:
                return "original exception message"
            continue
        if isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, (list, tuple, set, frozenset)):
            pending.extend(current)
        elif isinstance(current, BaseException):
            pending.extend(current.args)
            pending.extend(vars(current).values())
            pending.extend((current.__cause__, current.__context__))
        elif type(current).__module__ == __name__ and hasattr(
            current,
            "__dict__",
        ):
            pending.extend(vars(current).values())

    return None


class EngineAdapterProtocolTests(unittest.TestCase):
    def assert_traceback_private_state_isolated(
        self,
        error: BaseException,
    ) -> list[str]:
        frame_names: list[str] = []
        pending = [error]
        seen_errors: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in seen_errors:
                continue
            seen_errors.add(id(current))

            traceback = current.__traceback__
            while traceback is not None:
                frame = traceback.tb_frame
                frame_names.append(frame.f_code.co_name)
                for local_name, local_value in dict(frame.f_locals).items():
                    self.assertIsNone(
                        _reachable_private_adapter_state(local_value),
                        msg=(
                            "private adapter state remains reachable from "
                            f"{type(current).__name__} traceback "
                            f"{frame.f_code.co_name}.{local_name}"
                        ),
                    )
                traceback = traceback.tb_next

            for chained in (current.__cause__, current.__context__):
                if chained is not None:
                    pending.append(chained)

        self.assertIn("adapt", frame_names)
        return frame_names

    def assert_normalized_error_isolated(
        self,
        error: EngineAdapterError,
        *,
        art_id: str,
        code: str,
    ) -> None:
        self.assertEqual(error.code, code)
        self.assertEqual(
            error.args,
            (f"{art_id} engine adapter failed ({code})",),
        )
        self.assertEqual(
            vars(error),
            {
                "art_id": art_id,
                "code": code,
            },
        )
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

        self.assert_traceback_private_state_isolated(error)

    def test_protocol_exposes_only_normalized_request_and_canonical_result(self) -> None:
        adapter = _OrderedHappyFakeAdapter()

        self.assertIsInstance(adapter, EngineAdapter)
        result = adapter.adapt("normalized")

        self.assertEqual(result.canonical_facts.value, "projected")
        self.assertEqual(result.provenance, result.canonical_facts.provenance)
        self.assertFalse(hasattr(result, "engine_output"))
        self.assertNotIn(
            "_RawThirdPartyValue",
            repr(result),
        )
        self.assertEqual(
            adapter.calls,
            ["build_request", "provenance", "invoke", "project"],
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

    def test_provenance_traceback_cannot_reach_private_state(self) -> None:
        adapter = _ProvenanceTracebackFailingFakeAdapter()

        try:
            adapter.adapt("normalized")
        except _OwnedProvenanceFailure as caught:
            error = caught
        else:
            self.fail("owned provenance validation did not fail")

        self.assertIs(type(error), _OwnedProvenanceFailure)
        self.assertEqual(error.args, ("owned provenance validation failed",))
        self.assertEqual(str(error), "owned provenance validation failed")
        self.assertIs(type(error.__cause__), _OwnedProvenanceCause)
        self.assertEqual(error.__cause__.args, ("owned provenance cause",))
        self.assertIs(error.__context__, error.__cause__)
        self.assertTrue(error.__suppress_context__)
        self.assertEqual(adapter.calls, ["build_request", "provenance"])

        frame_names = self.assert_traceback_private_state_isolated(error)
        self.assertIn("_provenance", frame_names)

    def test_invocation_traceback_cannot_reach_private_state(self) -> None:
        try:
            _InvocationTracebackFailingFakeAdapter().adapt("normalized")
        except EngineAdapterError as caught:
            error = caught
        else:
            self.fail("invocation failure was not normalized")

        self.assert_normalized_error_isolated(
            error,
            art_id="fixture",
            code="engine_execution_failed",
        )

    def test_projection_exception_cannot_retain_private_output(self) -> None:
        with self.assertRaises(EngineAdapterError) as raised:
            _ProjectionFailingFakeAdapter().adapt("normalized")

        error = raised.exception
        self.assertEqual(error.code, "canonical_projection_failed")
        self.assertEqual(
            error.args,
            ("fixture engine adapter failed (canonical_projection_failed)",),
        )
        self.assertEqual(
            vars(error),
            {
                "art_id": "fixture",
                "code": "canonical_projection_failed",
            },
        )
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def test_projection_traceback_cannot_reach_private_state(self) -> None:
        try:
            _ProjectionFailingFakeAdapter().adapt("normalized")
        except EngineAdapterError as caught:
            error = caught
        else:
            self.fail("projection failure was not normalized")

        self.assert_normalized_error_isolated(
            error,
            art_id="fixture",
            code="canonical_projection_failed",
        )

    def test_result_construction_traceback_cannot_reach_private_state(
        self,
    ) -> None:
        try:
            _ProvenanceMismatchFakeAdapter().adapt("normalized")
        except EngineAdapterError as caught:
            error = caught
        else:
            self.fail("provenance mismatch did not fail closed")

        self.assert_normalized_error_isolated(
            error,
            art_id="unknown",
            code="provenance_binding_mismatch",
        )

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

    def test_nested_canonical_fact_objects_are_recursively_closed(self) -> None:
        ziwei_case = _fixture("ziwei-normal-civil")
        ziwei_provenance = _provenance(ziwei_case)
        for path in ("palace", "nested_star"):
            hostile = copy.deepcopy(ziwei_case["expected_canonical_facts"])
            palace = hostile["output"]["palaces"][0]
            target = palace if path == "palace" else palace["majorStars"][0]
            target["third_party_payload"] = {
                "private_engine_output": "must-not-cross-provider",
            }

            with self.subTest(art="ziwei", path=path):
                with self.assertRaises(CanonicalFactsError):
                    ZiweiFactContract().bind_canonical_facts(
                        hostile,
                        ziwei_provenance,
                    )

        bazi_case = _fixture("bazi-normal-civil")
        bazi_hostile = copy.deepcopy(bazi_case["expected_canonical_facts"])
        bazi_hostile["output"]["day_master"]["third_party_payload"] = {
            "private_engine_output": "must-not-cross-provider",
        }
        with self.assertRaises(CanonicalFactsError):
            BaziFactContract().bind_canonical_facts(
                bazi_hostile,
                _provenance(bazi_case),
            )

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
