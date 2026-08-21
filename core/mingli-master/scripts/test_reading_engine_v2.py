"""Engine-level behaviour of the slim provider-adapter turn chain."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import reading_source_plan
from reading_engine.catalog import CatalogLoader
from reading_engine.contracts import (
    AcceptedReading,
    AnswerDraft,
    CalculationResult,
    ClaimTrace,
    EvidenceBundle,
    EvidenceNode,
    FactExtensionResult,
    PreparedReading,
    ReadingRequest,
)
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import (
    PROVIDER_CAPABILITIES,
    _AdapterSeam,
    missing_required_inputs,
)
from reading_engine.storage import AtomicReadingStore
from reading_engine.turns import TurnEngine

ROOT = Path(__file__).resolve().parents[1]
CATALOG = CatalogLoader(ROOT / "resources/runtime").load()


class StaticProvider(_AdapterSeam):
    """Deterministic fixture adapter bound to the real liuren descriptor."""

    provider_id = "test.liuren"
    provider_version = "4"
    capability = PROVIDER_CAPABILITIES["liuren"]

    def __init__(self, system: str = "liuren") -> None:
        self.system = system
        self.calls = 0
        self.capability = PROVIDER_CAPABILITIES.get(
            system, PROVIDER_CAPABILITIES["liuren"]
        )
        try:
            self.bind_descriptor(CATALOG.descriptor(system))
        except Exception:  # noqa: BLE001 - fixture systems fall back to liuren
            self.bind_descriptor(CATALOG.descriptor("liuren"))

    @staticmethod
    def missing_required_inputs(request: ReadingRequest) -> tuple[str, ...]:
        return missing_required_inputs("liuren", request)

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        self.calls += 1
        return CalculationResult.create(
            system=self.system,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload={
                "reference_datetime": request.reference_datetime,
                "timezone": request.timezone,
            },
            facts={
                "chart_facts": {
                    "output": {
                        "lesson_method": "元首",
                        "three_transmissions": ["子", "孙", "天后"],
                    }
                }
            },
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict,
    ) -> CalculationResult:
        base = calculation.base()
        extension = FactExtensionResult.create(
            system=base.system,
            base_calculation_digest=base.result_hash,
            requested_dimensions=requested_dimensions,
            horizon=horizon,
            status="complete",
            facts={
                "fixture_scope": {
                    dimension: "deterministic_fixture"
                    for dimension in requested_dimensions
                }
            },
        )
        return base.with_fact_extension(extension)

    def _bound_evidence(
        self,
        request: ReadingRequest,
        calculation: CalculationResult,
        intent_digest: str,
    ) -> tuple[EvidenceBundle, str]:
        """The fixture pins its evidence instead of querying the corpus."""

        bundle = EvidenceBundle.create(
            system=calculation.system,
            evidence=(
                EvidenceNode(
                    rule_id="lr-source-001",
                    source="大六壬大全",
                    anchor="卷一/发用",
                    applicability="调用方目标与当前课体共同限定",
                    assertion="发用为当前课的事实主线",
                    lineage="san-shi/daliuren-daquan",
                    quote_hash="a" * 64,
                    reading_id=str(request.reading_id),
                    version=int(request.transaction_version or 1),
                ),
            ),
            intent_digest=intent_digest,
        )
        return bundle, "课象"


def evidence_compiler(
    request: ReadingRequest,
    calculation: CalculationResult,
) -> EvidenceBundle:
    del request
    return EvidenceBundle.create(
        system=calculation.system,
        evidence=(
            EvidenceNode(
                rule_id="lr-source-001",
                source="大六壬大全",
                anchor="卷一/发用",
                applicability="调用方目标与当前课体共同限定",
                assertion="发用为当前课的事实主线",
                lineage="san-shi/daliuren-daquan",
                quote_hash="a" * 64,
            ),
        ),
    )


def build_engine(root: Path, provider: StaticProvider) -> TurnEngine:
    return TurnEngine(
        store=AtomicReadingStore(root),
        providers={provider.system: provider},
        catalog=CATALOG,
    )


def intent_for(
    system: str = "liuren",
    *,
    reading_id: str | None = None,
) -> dict[str, object]:
    objects = {
        "bazi": ("natal", "life"),
        "fortune": ("near_time_personal", "day"),
        "liuren": ("concrete_event", "instant"),
    }
    calculation_object, horizon = objects.get(system, ("supplied_chart", "instant"))
    return {
        "subject_refs": ["subject:test"],
        "calculation_object": calculation_object,
        "question_dimensions": ["outcome"],
        "horizon": {"kind": horizon, "start": None, "end": None},
        "requested_method": system if reading_id is None else None,
        "requested_granularity": "directional",
        "continuity": {
            "reading_id": reading_id,
            "same_subject": reading_id is not None,
            "same_event": reading_id is not None,
        },
        "facts_present": [],
        "facts_corrected": [],
        "evidence_questions": ["哪些规则适用于当前事实"],
    }


def new_request(query: str, **changes: object) -> ReadingRequest:
    values: dict[str, object] = {
        "query": query,
        "action": "new",
        "system": "liuren",
        "reference_datetime": "2026-07-22T22:13:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
        "intent": intent_for("liuren"),
    }
    values.update(changes)
    return ReadingRequest(**values)


def provider_request(
    query: str = "她现在大概在哪里？", **changes: object
) -> ProviderRequest:
    values: dict[str, object] = {
        "query": query,
        "subject_refs": ("subject:test",),
        "object_id": "concrete_event",
        "dimension_ids": ("outcome",),
        "horizon": {"kind": "instant", "start": None, "end": None},
        "facts": {
            "subject:test": {
                "event_datetime_or_reference_datetime": (
                    "2026-07-22T22:13:00+08:00"
                ),
                "timezone": "Asia/Shanghai",
            }
        },
    }
    values.update(changes)
    return ProviderRequest(**values)


def answer_for(
    prepared: PreparedReading,
    text: str = "测试主回答。",
    *,
    dimension: str | None = None,
) -> AnswerDraft:
    basis = "测试事实已列明。"
    public_copy = f"{basis}\n{text}"
    return AnswerDraft(
        visible_basis=basis,
        main_answer=text,
        public_copy=public_copy,
        visible_basis_span=(0, len(basis)),
        main_answer_span=(len(basis) + 1, len(public_copy)),
        claim_traces=(
            ClaimTrace(
                role="main",
                text=text,
                dimension=dimension or "",
                fact_refs=(prepared.fact_index[0].fact_id,),
                evidence_refs=(
                    (prepared.evidence[0].rule_id,) if prepared.evidence else ()
                ),
                counter_evidence_refs=(),
            ),
        ),
    )


def accept_prepared(
    engine: TurnEngine,
    prepared: PreparedReading,
    *,
    dimension: str | None = None,
    public_copy: str = "测试事实已列明。\n测试主回答。",
) -> AcceptedReading:
    # completion is one mechanical atomic commit of finished text; the
    # legacy per-dimension draft argument no longer selects anything
    del dimension
    accepted = engine.commit_prepared(
        prepared.reading_id, prepared.prepared_digest, public_copy
    )
    if not isinstance(accepted, AcceptedReading):
        raise AssertionError(f"expected accepted reading, got {accepted!r}")
    return accepted


class TurnChainTests(unittest.TestCase):
    def test_query_wording_is_opaque_to_the_bound_capability(self) -> None:
        for query in (
            "整点玄乎的瞅瞅她这会儿猫哪儿呢",
            "这句话故意同时提到八字六壬和普通计算",
            "387×42 等于多少",
            "昨天那件事后来怎样",
        ):
            with self.subTest(query=query):
                with tempfile.TemporaryDirectory() as temporary:
                    provider = StaticProvider()
                    engine = build_engine(Path(temporary), provider)
                    turn = engine.prepare_turn(
                        provider.descriptor, provider_request(query)
                    )
                self.assertIsInstance(turn.result, PreparedReading, turn.result)
                self.assertEqual(turn.result.system, "liuren")
                self.assertEqual(provider.calls, 1)

    def test_missing_facts_come_from_capability_requirements(self) -> None:
        """Even without data, the adapter reports capability requirements."""

        from reading_engine.providers import BaziProvider

        with tempfile.TemporaryDirectory() as temporary:
            provider = BaziProvider(ROOT)
            provider.bind_descriptor(CATALOG.descriptor("bazi"))
            engine = TurnEngine(
                store=AtomicReadingStore(Path(temporary)),
                providers={"bazi": provider},
                catalog=CATALOG,
            )
            turn = engine.prepare_turn(
                provider.descriptor,
                provider_request(
                    "任何写法都一样",
                    object_id="natal",
                    horizon={"kind": "life", "start": None, "end": None},
                    facts={},
                ),
            )

        self.assertEqual(
            turn.result.missing_facts, ("birth_datetime_or_four_pillars",)
        )
        self.assertIsNotNone(turn.state_token)

    def test_prepare_replay_reuses_the_staged_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            first = engine.prepare_turn(provider.descriptor, provider_request())
            self.assertIsInstance(first.result, PreparedReading, first.result)
            replay = engine.prepare_turn(
                provider.descriptor,
                provider_request(),
                state_token=first.state_token,
            )

        self.assertIsInstance(replay.result, PreparedReading, replay.result)
        self.assertEqual(replay.result.reading_id, first.result.reading_id)
        self.assertEqual(replay.state_token, first.state_token)
        self.assertEqual(provider.calls, 1)

    def test_new_turn_starts_an_unrelated_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            first = engine.prepare_turn(
                provider.descriptor, provider_request("第一件事")
            )
            self.assertIsInstance(first.result, PreparedReading, first.result)
            accepted = accept_prepared(engine, first.result)
            second = engine.prepare_turn(
                provider.descriptor, provider_request("第二件事")
            )

        self.assertIsInstance(accepted, AcceptedReading)
        self.assertIsInstance(second.result, PreparedReading, second.result)
        self.assertNotEqual(second.result.reading_id, first.result.reading_id)
        self.assertEqual(provider.calls, 2)

    def test_complete_commits_then_replays_first_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            turn = engine.prepare_turn(provider.descriptor, provider_request())
            self.assertIsInstance(turn.result, PreparedReading, turn.result)
            first = engine.complete_turn(
                turn.state_token, "事实已列明。\n候应结论一。"
            )
            self.assertIsInstance(first, AcceptedReading, first)
            replay = engine.complete_turn(
                turn.state_token, "完全不同的第二份稿子。"
            )

        self.assertIsInstance(replay, AcceptedReading, replay)
        self.assertEqual(replay.public_copy, first.public_copy)

    def test_continue_after_accept_carries_prior_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            turn = engine.prepare_turn(provider.descriptor, provider_request())
            self.assertIsInstance(turn.result, PreparedReading, turn.result)
            text = "事实已列明。\n第一轮结论。"
            accepted = engine.complete_turn(turn.state_token, text)
            self.assertIsInstance(accepted, AcceptedReading, accepted)
            follow = engine.prepare_turn(
                provider.descriptor,
                provider_request("那她会主动联系吗？"),
                state_token=turn.state_token,
            )
            self.assertIsInstance(follow.result, PreparedReading, follow.result)
            staged = engine.store.load_prepared(follow.result.reading_id)

        self.assertEqual(follow.prior_answer, text)
        self.assertEqual(staged.parent_reading_id, turn.result.reading_id)
        self.assertEqual(staged.reading_id, turn.result.reading_id)
        self.assertEqual(staged.version, 2)
        self.assertEqual(provider.calls, 2)

    def test_concurrent_same_restart_prepares_one_child_once(self) -> None:
        import threading

        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            first = engine.prepare_turn(provider.descriptor, provider_request())
            accepted = engine.complete_turn(first.state_token, "第一轮正文。")
            self.assertIsInstance(accepted, AcceptedReading, accepted)
            barrier = threading.Barrier(4)
            outcomes: list = []
            lock = threading.Lock()

            def restart() -> None:
                barrier.wait()
                result = engine.prepare_turn(
                    provider.descriptor,
                    provider_request("重新起一轮"),
                    state_token=first.state_token,
                    transition="restart",
                )
                with lock:
                    outcomes.append(result)

            threads = [threading.Thread(target=restart) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(len(outcomes), 4)
            self.assertTrue(
                all(isinstance(item.result, PreparedReading) for item in outcomes),
                outcomes,
            )
            reading_ids = {item.result.reading_id for item in outcomes}
            versions = {item.result.version for item in outcomes}
            self.assertEqual(len(reading_ids), 1, reading_ids)
            self.assertNotIn(first.result.reading_id, reading_ids)
            self.assertEqual(versions, {1})
            self.assertEqual(provider.calls, 2)

    def test_correct_stays_on_reading_and_restart_creates_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            first = engine.prepare_turn(provider.descriptor, provider_request())
            engine.complete_turn(first.state_token, "第一轮正文。")

            corrected = engine.prepare_turn(
                provider.descriptor,
                provider_request("修正资料后重算"),
                state_token=first.state_token,
                transition="correct",
            )
            self.assertIsInstance(corrected.result, PreparedReading, corrected.result)
            corrected_record = engine.store.load_prepared(
                corrected.result.reading_id
            )
            self.assertEqual(corrected.result.reading_id, first.result.reading_id)
            self.assertEqual(corrected.result.version, 2)
            self.assertEqual(corrected_record.supersedes_version, 1)
            engine.complete_turn(corrected.state_token, "修正后的正文。")

            restarted = engine.prepare_turn(
                provider.descriptor,
                provider_request("重新起一轮"),
                state_token=corrected.state_token,
                transition="restart",
            )
            self.assertIsInstance(restarted.result, PreparedReading, restarted.result)
            restarted_record = engine.store.load_prepared(
                restarted.result.reading_id
            )
            self.assertNotEqual(restarted.result.reading_id, first.result.reading_id)
            self.assertEqual(restarted.result.version, 1)
            self.assertEqual(
                restarted_record.parent_reading_id,
                first.result.reading_id,
            )
            self.assertEqual(
                restarted_record.root_reading_id,
                first.result.reading_id,
            )

    def test_capability_registry_contains_facts_not_verdict_controls(self) -> None:
        capability = PROVIDER_CAPABILITIES["liuren"]

        self.assertNotEqual(capability.mode, "unavailable")
        self.assertIn("three_transmissions", capability.outputs)
        for forbidden in (
            "directional_prediction_allowed",
            "direct_answer_allowed",
            "fact_assertion_allowed",
            "confidence_ceiling",
        ):
            self.assertNotIn(forbidden, capability.to_dict())

    def test_source_plan_consumes_goal_and_current_facts(self) -> None:
        goal = {
            "requested_resolution": "比较主证和反证",
            "evidence_questions": ["发用如何落到当前事实"],
        }
        plan = reading_source_plan.compile_source_plan(
            "liuren",
            goal,
            {"output": {"four_lessons": [], "three_transmissions": []}},
        )

        self.assertEqual(plan["requested_resolution"], "比较主证和反证")
        self.assertEqual(plan["evidence_questions"], goal["evidence_questions"])
        self.assertNotIn("query", plan)


if __name__ == "__main__":
    unittest.main()
