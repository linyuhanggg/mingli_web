"""Provider-specific preparation rules live inside each provider adapter."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from reading_engine import liuyao, physiognomy
from reading_engine.contracts import CalculationResult, ReadingRequest
from reading_engine.providers import (
    BaziProvider,
    FortuneProvider,
    LiurenProvider,
    LiuyaoProvider,
    MeihuaProvider,
    PhysiognomyProvider,
    SelectionProvider,
)
from reading_engine.provider_protocol import ProviderActionError
from reading_engine.runtime_context import RuntimeContext

ROOT = Path(__file__).resolve().parents[1]
SHA_A = hashlib.sha256(b"locality-fixture-asset").hexdigest()


def _physiognomy_spec() -> dict[str, object]:
    return {
        "schema_version": "mingli-physiognomy-input-v1",
        "observation_scope": "face",
        "subject_ref": "sid-0bac48405950e1d63b39cde30608d995",
        "requested_targets": [
            {
                "target_id": "tid-0902d05e906e853a141894141a50184e",
                "taxonomy": "anatomical_face_v1",
                "region": "forehead",
                "feature_kind": "visible_morphology",
                "required": True,
            }
        ],
        "assets": [
            {
                "asset_id": "aid-77072c872df89a9e9c89483dea1e14e5",
                "capture_id": "cid-421b5f386a3bd17c0403216536556e80",
                "subject_ref": "sid-0bac48405950e1d63b39cde30608d995",
                "media_type": "image/svg+xml",
                "sha256": SHA_A,
                "byte_length": 512,
                "pixel_width": 512,
                "pixel_height": 512,
                "pose_family": "frontal",
                "visible_subject_sides": "bilateral",
                "framing": "full_face",
                "supplied_visible_regions": ["forehead"],
                "quality": {
                    "lighting": "even",
                    "camera_angle": "frontal",
                    "focus": "sharp",
                    "resolution": "adequate",
                    "filtering": "none",
                    "color_fidelity": "calibrated",
                },
                "synthetic": True,
                "no_real_person": True,
            }
        ],
        "observations": [
            {
                "observation_id": "oid-8342798c96dfef210cb512918268d772",
                "target_id": "tid-0902d05e906e853a141894141a50184e",
                "source_type": "image_transcription",
                "transcription_actor": "current_vision_capable_caller",
                "provider_performed_vision": False,
                "asset_id": "aid-77072c872df89a9e9c89483dea1e14e5",
                "asset_sha256": SHA_A,
                "region": "forehead",
                "feature_kind": "visible_morphology",
                "visibility": "full",
                "region_anchor": {
                    "kind": "normalized_bbox",
                    "x": 0.25,
                    "y": 0.08,
                    "width": 0.5,
                    "height": 0.2,
                },
                "value": {"descriptor": "contour_rounded"},
                "occlusion": 0.0,
                "uncertainty": 0.1,
            }
        ],
        "confirmed_observation_ids": [],
        "comparison_relations": [],
        "source_layer_policy": "terminology_and_methodology_only",
    }


def _liuyao_calculation(
    *,
    method: str = "digital_coin",
    seed: str | None = None,
    provider_version: str | None = None,
    seed_source: str | None = None,
) -> CalculationResult:
    version = provider_version or liuyao.ADAPTER_VERSION
    casting: dict[str, object] = {"method": method}
    if seed is not None:
        casting["seed"] = seed
        casting["seed_source"] = (
            seed_source or liuyao.TRANSACTION_CAST_SEED_SOURCE
        )
    return CalculationResult.create(
        system="liuyao",
        provider_id="mingli-master.liuyao.v1",
        provider_version=version,
        input_payload={"fixture": True},
        facts={
            "chart_facts": {
                "adapter": {"version": version},
                "output": {"casting": casting},
            }
        },
    )


class SelectionProjectionTests(unittest.TestCase):
    def test_selection_projection_is_bounded_with_complete_counts(self) -> None:
        provider = SelectionProvider(ROOT)
        candidates = [{"candidate_id": f"cand-{index}"} for index in range(30)]
        chart_facts = {
            "output": {
                "event_profile": "generic_selection",
                "calendar_candidates": list(candidates),
                "date_time_candidates": list(candidates),
                "eligible_candidates": list(candidates),
                "eligible_date_time_candidates": list(candidates),
                "eliminations": list(candidates),
                "no_valid_candidate": False,
                "ranking": {
                    "ordered_candidate_ids": [f"cand-{i}" for i in range(30)],
                    "eligible_candidate_ids": [f"cand-{i}" for i in range(30)],
                    "ordered_date_time_candidate_ids": [],
                    "eligible_date_time_candidate_ids": [],
                },
                "lineage_policy": {"policy": "separated"},
            }
        }
        visible = provider.public_basis_projection(chart_facts)
        self.assertLessEqual(len(visible["eligible_candidates"]), 12)
        self.assertLessEqual(len(visible["eliminations"]), 12)
        self.assertLessEqual(
            len(visible["ranking"]["ordered_candidate_ids"]), 12
        )
        counts = visible["basis_projection"]["complete_counts"]
        self.assertEqual(counts["eligible_candidates"], 30)
        self.assertEqual(counts["ranking.ordered_candidate_ids"], 30)
        self.assertTrue(
            visible["basis_projection"][
                "full_facts_remain_in_calculation_record"
            ]
        )

    def test_selection_extension_projection_is_bounded(self) -> None:
        provider = SelectionProvider(ROOT)
        extension = {
            "facts": {
                "status": "complete",
                "event_profile": "generic_selection",
                "calendar_candidates": [{"row": i} for i in range(20)],
                "ranking": {
                    "eligible_candidate_ids": [f"cand-{i}" for i in range(20)],
                    "eligible_date_time_candidate_ids": [],
                },
            }
        }
        projected = provider.public_extension_projection(extension)
        facts = projected["facts"]
        self.assertLessEqual(len(facts["eligible_candidate_ids"]), 12)
        self.assertEqual(
            facts["basis_projection"]["complete_counts"]["calendar_candidates"],
            20,
        )


class ObservationPrivacyTests(unittest.TestCase):
    def test_physiognomy_projection_is_provider_owned_and_private_safe(
        self,
    ) -> None:
        provider = PhysiognomyProvider(ROOT)
        chart_facts = physiognomy.build_fact_layer(_physiognomy_spec())
        visible = provider.public_basis_projection(chart_facts)
        self.assertEqual(visible, physiognomy.public_projection(chart_facts))
        rendered = json.dumps(visible, ensure_ascii=False)
        for private in ("active_source_rule_ids", SHA_A, "asset_id"):
            self.assertNotIn(private, rendered)

    def test_physiognomy_extension_stays_private(self) -> None:
        self.assertTrue(PhysiognomyProvider.extension_is_private)

    def test_liuyao_projection_delegates_to_provider_module(self) -> None:
        provider = LiuyaoProvider(ROOT)
        calculation = _liuyao_calculation(seed="ab" * 32)
        chart_facts = calculation.facts["chart_facts"]
        visible = provider.public_basis_projection(chart_facts)
        projected = liuyao.public_projection(chart_facts)
        expected = projected.get("output")
        if not isinstance(expected, dict):
            expected = projected
        self.assertEqual(visible, expected)
        self.assertNotIn("ab" * 32, json.dumps(visible, ensure_ascii=False))


class DefaultProfileEnrichmentTests(unittest.TestCase):
    def _request(self) -> ReadingRequest:
        return ReadingRequest(
            query="宽泛总览",
            action="new",
            goal={"use_default_profile": True},
            intent={
                "subject_refs": ["current_user"],
                "calculation_object": "near_time_personal",
                "question_dimensions": ["state"],
                "horizon": {"kind": "day", "start": None, "end": None},
                "continuity": {
                    "reading_id": None,
                    "same_subject": False,
                    "same_event": False,
                },
                "facts_present": [],
                "facts_corrected": [],
                "evidence_questions": [],
                "requested_granularity": "day",
            },
        )

    def _context(self) -> RuntimeContext:
        return RuntimeContext(
            now_iso="2026-07-28T10:00:00+08:00",
            default_timezone_name="Asia/Shanghai",
            subject_profiles={
                "current_user": {
                    "birth_datetime": "1990-01-01T08:30:00",
                    "timezone": "Asia/Shanghai",
                    "location": "上海",
                    "gender": "male",
                }
            },
        )

    def test_fortune_provider_reads_profile_from_injected_context(self) -> None:
        provider = FortuneProvider(ROOT)
        enriched = provider.enrich_request(self._request(), self._context())
        self.assertEqual(
            enriched.birth_data.get("birth_datetime"),
            "1990-01-01T08:30:00",
        )

    def test_bazi_provider_normalizes_datetime_alias(self) -> None:
        provider = BaziProvider(ROOT)
        enriched = provider.enrich_request(self._request(), self._context())
        self.assertEqual(enriched.birth_data.get("datetime"), "1990-01-01T08:30:00")

    def test_profile_requires_explicit_opt_in(self) -> None:
        provider = FortuneProvider(ROOT)
        request = self._request()
        request = ReadingRequest(**{**request.to_dict(), "goal": {}})
        self.assertEqual(
            provider.enrich_request(request, self._context()),
            request,
        )

    def test_other_subject_never_receives_default_profile(self) -> None:
        provider = FortuneProvider(ROOT)
        request = self._request()
        intent = dict(request.intent)
        intent["subject_refs"] = ["other_person"]
        request = ReadingRequest(**{**request.to_dict(), "intent": intent})
        self.assertEqual(
            provider.enrich_request(request, self._context()),
            request,
        )


class InjectedClockAndTimezoneTests(unittest.TestCase):
    def test_liuren_defaults_come_from_runtime_context(self) -> None:
        provider = LiurenProvider(ROOT)
        request = ReadingRequest(
            query="这件事如何",
            action="new",
            intent={
                "subject_refs": ["current_user"],
                "calculation_object": "concrete_event",
                "question_dimensions": ["outcome"],
                "horizon": {"kind": "instant", "start": None, "end": None},
                "continuity": {
                    "reading_id": None,
                    "same_subject": False,
                    "same_event": False,
                },
                "facts_present": [],
                "facts_corrected": [],
                "evidence_questions": [],
                "requested_granularity": "day",
            },
        )
        context = RuntimeContext(
            now_iso="2026-07-28T10:00:00+08:00",
            default_timezone_name="Asia/Shanghai",
        )
        enriched = provider.enrich_request(request, context)
        self.assertEqual(enriched.timezone, "Asia/Shanghai")
        self.assertEqual(
            enriched.reference_datetime, "2026-07-28T10:00:00+08:00"
        )
        # supplied values always win over injected defaults
        explicit = ReadingRequest(
            **{
                **request.to_dict(),
                "timezone": "UTC",
                "event_datetime": "2026-07-01T00:00:00",
            }
        )
        self.assertEqual(provider.enrich_request(explicit, context), explicit)


class LiuyaoCastOwnershipTests(unittest.TestCase):
    def test_reserved_seed_fields_are_rejected_by_the_provider(self) -> None:
        provider = LiuyaoProvider(ROOT)
        polluted = ReadingRequest(
            query="fixture",
            metadata={liuyao.TRANSACTION_CAST_SEED_KEY: "x"},
        )
        with self.assertRaises(ValueError):
            provider.reject_reserved_request_fields(polluted)
        chart_polluted = ReadingRequest(query="fixture", chart_data={"seed": "x"})
        with self.assertRaises(ValueError):
            provider.reject_reserved_request_fields(chart_polluted)

    def test_persisted_seed_replay_and_legacy_recast_rule(self) -> None:
        provider = LiuyaoProvider(ROOT)
        seed = "ab" * 32
        replayable = _liuyao_calculation(seed=seed)
        self.assertEqual(
            provider.persisted_transaction_cast_seed(replayable),
            liuyao.normalize_transaction_cast_seed(seed),
        )
        manual = _liuyao_calculation(method="supplied_complete_cast")
        self.assertIsNone(provider.persisted_transaction_cast_seed(manual))
        legacy = _liuyao_calculation(seed=seed, provider_version="legacy-0")
        with self.assertRaises(ProviderActionError) as raised:
            provider.persisted_transaction_cast_seed(legacy)
        self.assertEqual(raised.exception.code, "action_requires_recast")

    def test_correction_may_not_silently_replace_cast(self) -> None:
        provider = LiuyaoProvider(ROOT)
        calculation = _liuyao_calculation(method="supplied_complete_cast")
        replacing = ReadingRequest(
            query="fixture",
            chart_data={"casting_method": "digital_coin"},
        )
        message = provider.correction_replaces_cast(calculation, replacing)
        self.assertTrue(message)
        annotating = ReadingRequest(query="fixture", chart_data={})
        self.assertIsNone(
            provider.correction_replaces_cast(calculation, annotating)
        )

    def test_restart_generates_fresh_seed_and_replay_reuses_it(self) -> None:
        provider = LiuyaoProvider(ROOT)
        request = ReadingRequest(
            query="fixture",
            system="liuyao",
            chart_data={"casting_method": "digital_coin"},
        )
        replayed = provider.inject_transaction_cast(request, "cd" * 32)
        self.assertEqual(
            replayed.metadata[liuyao.TRANSACTION_CAST_SEED_KEY],
            liuyao.normalize_transaction_cast_seed("cd" * 32),
        )
        fresh_one = provider.inject_transaction_cast(request, None)
        fresh_two = provider.inject_transaction_cast(request, None)
        seed_one = fresh_one.metadata[liuyao.TRANSACTION_CAST_SEED_KEY]
        seed_two = fresh_two.metadata[liuyao.TRANSACTION_CAST_SEED_KEY]
        self.assertNotEqual(seed_one, seed_two)
        manual = ReadingRequest(
            query="fixture",
            system="liuyao",
            chart_data={"tosses": [6, 7, 8, 9, 7, 8]},
        )
        self.assertEqual(provider.inject_transaction_cast(manual, None), manual)

    def test_recast_replaces_chart_data_is_declared_by_cast_providers(
        self,
    ) -> None:
        for provider_class in (LiuyaoProvider, MeihuaProvider, PhysiognomyProvider):
            self.assertTrue(
                getattr(provider_class, "recast_replaces_chart_data", False),
                provider_class.__name__,
            )



class ProviderAdapterSeamTests(unittest.TestCase):
    """All 13 production adapters live behind descriptor + prepare."""

    def test_every_production_adapter_satisfies_the_protocol(self) -> None:
        from reading_engine.catalog import CatalogLoader
        from reading_engine.provider_protocol import ProviderAdapter
        from reading_engine.provider_registry import ProviderRegistry

        catalog = CatalogLoader(ROOT / "resources/runtime").load()
        registry = ProviderRegistry(
            catalog,
            skill_root=ROOT,
            construction={"skill_dir": ROOT},
        )
        adapters = registry.adapters()
        self.assertEqual(len(adapters), 14)
        for capability_id, adapter in adapters.items():
            with self.subTest(capability=capability_id):
                self.assertIsInstance(adapter, ProviderAdapter)
                self.assertEqual(adapter.descriptor.id, capability_id)
                self.assertTrue(callable(adapter.prepare))

    def test_production_factory_routes_through_adapter_prepare(self) -> None:
        import tempfile

        from reading_engine.interface import ReadingInterface
        from reading_engine.interface_contracts import (
            HorizonSelection,
            IntentSelection,
            Prepare,
            Prepared,
        )

        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            interface = ReadingInterface(
                skill_root=ROOT, store_root=Path(tmp)
            )
            adapters = interface.engine.providers
            for capability_id, adapter in adapters.items():
                original = adapter.prepare

                def wrapped(request, context, *, _original=original, _id=capability_id):
                    calls.append(_id)
                    return _original(request, context)

                object.__setattr__(adapter, "prepare", wrapped) if False else setattr(
                    adapter, "prepare", wrapped
                )
            result = interface.execute(
                Prepare(
                    query="看一下这个八字",
                    intent=IntentSelection(
                        subject_refs=("subject:client",),
                        capability_id="bazi",
                        object_id="natal",
                        dimension_ids=(),
                        horizon=HorizonSelection(kind_id="year"),
                    ),
                    facts={
                        "subject:client": {
                            "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                            "timezone": "Asia/Shanghai",
                            "location": "福建省福州市",
                            "gender": "female",
                            "time_basis_policy": "civil",
                        }
                    },
                )
            )
        self.assertIsInstance(result, Prepared, result)
        self.assertTrue(calls, "production prepare must call adapter.prepare")


if __name__ == "__main__":
    unittest.main()
