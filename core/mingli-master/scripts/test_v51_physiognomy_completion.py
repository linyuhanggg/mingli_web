#!/usr/bin/env python3
"""Task 7M regressions for the bounded Physiognomy observation provider."""

from __future__ import annotations

import copy
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import yaml

import adapter_validate
import audit_physiognomy_provider
import physiognomy_fixture_reference
import reading_source_plan
import structured_chart_adapter
from reading_engine import physiognomy
from reading_engine.contracts import (
    AcceptedReading,
    NeedUserFact,
    PreparedReading,
    ReadingRequest,
    canonical_digest,
)
from reading_engine.evidence_rules import match_rule, production_evidence_rules
from reading_engine.factory import build_production_engine
from reading_engine.fact_index import build_fact_index
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import PhysiognomyProvider, STRUCTURED_SYSTEMS, StructuredChartProvider
from reading_engine.structured_input import normalize_structured_chart
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
_SPEC_PROVIDER = PhysiognomyProvider(ROOT)


def _merge_physiognomy_resume_spec(original_spec, supplied_spec, missing_facts):
    return _SPEC_PROVIDER.merge_intake_spec(
        original_spec, supplied_spec, missing_facts, "resume"
    )


def _merge_physiognomy_correction_resume_spec(
    original_spec, supplied_spec, missing_facts
):
    return _SPEC_PROVIDER.merge_intake_spec(
        original_spec, supplied_spec, missing_facts, "correct"
    )


FIXTURE = ROOT / "references/fixtures/physiognomy-v51.yaml"
SOURCE_TABLE = ROOT / "references/matrices/physiognomy-source-tables-v1.yaml"
ASSET_ROOT = ROOT / "references/fixtures/assets/physiognomy"
SHA_A = "a" * 64
SHA_B = "b" * 64


def _quality(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "lighting": "even",
        "camera_angle": "frontal",
        "focus": "sharp",
        "resolution": "adequate",
        "filtering": "none",
        "color_fidelity": "calibrated",
    }
    value.update(changes)
    return value


def _asset(identifier: str = "aid-77072c872df89a9e9c89483dea1e14e5", **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "asset_id": identifier,
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
        "supplied_visible_regions": [
            "forehead",
            "left_eyebrow",
            "right_eyebrow",
            "left_eye",
            "right_eye",
            "nose",
            "mouth",
            "chin",
            "jawline",
            "left_ear",
            "right_ear",
            "left_cheek",
            "right_cheek",
            "complexion",
        ],
        "quality": _quality(),
        "synthetic": True,
        "no_real_person": True,
    }
    value.update(changes)
    return value


def _target(
    identifier: str = "tid-0902d05e906e853a141894141a50184e",
    region: str = "forehead",
    *,
    required: bool = True,
    feature_kind: str = "visible_morphology",
) -> dict[str, object]:
    return {
        "target_id": identifier,
        "taxonomy": "anatomical_face_v1",
        "region": region,
        "feature_kind": feature_kind,
        "required": required,
    }


def _anchor(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "kind": "normalized_bbox",
        "x": 0.25,
        "y": 0.08,
        "width": 0.5,
        "height": 0.2,
    }
    value.update(changes)
    return value


def _image_observation(
    identifier: str = "oid-8342798c96dfef210cb512918268d772",
    target_id: str = "tid-0902d05e906e853a141894141a50184e",
    region: str = "forehead",
    descriptor: str = "contour_rounded",
    **changes: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "observation_id": identifier,
        "target_id": target_id,
        "source_type": "image_transcription",
        "transcription_actor": "current_vision_capable_caller",
        "provider_performed_vision": False,
        "asset_id": "aid-77072c872df89a9e9c89483dea1e14e5",
        "asset_sha256": SHA_A,
        "region": region,
        "feature_kind": "visible_morphology",
        "visibility": "full",
        "region_anchor": _anchor(),
        "value": {"descriptor": descriptor},
        "occlusion": 0.0,
        "uncertainty": 0.1,
    }
    value.update(changes)
    return value


def _text_observation(
    identifier: str = "oid-3f9940e7b3a29384af836283a3fb739a",
    target_id: str = "tid-0902d05e906e853a141894141a50184e",
    region: str = "forehead",
    descriptor: str = "contour_rounded",
    **changes: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "observation_id": identifier,
        "target_id": target_id,
        "source_type": "user_text",
        "source_ref": "rid-"
        + hashlib.sha256(f"caller-visible-description:{identifier}".encode("utf-8")).hexdigest()[:32],
        "region": region,
        "feature_kind": "visible_morphology",
        "visibility": "full",
        "value": {"descriptor": descriptor},
        "quality": {
            "lighting": "not_applicable",
            "camera_angle": "caller_description",
            "focus": "not_applicable",
            "resolution": "not_applicable",
            "filtering": "not_applicable",
            "color_fidelity": "not_applicable",
        },
        "occlusion": 0.0,
        "uncertainty": 0.2,
    }
    value.update(changes)
    return value


def _correction_observation(
    identifier: str = "oid-d2404a725325875299736d44739b9f32",
    target_id: str = "tid-0902d05e906e853a141894141a50184e",
    region: str = "forehead",
    descriptor: str = "contour_flat",
    **changes: object,
) -> dict[str, object]:
    """Build an exact-schema image correction without vision-only fields."""

    value = _image_observation(
        identifier,
        target_id,
        region,
        descriptor,
        source_type="user_correction",
        supersedes_observation_id="oid-8342798c96dfef210cb512918268d772",
    )
    value.pop("transcription_actor")
    value.pop("provider_performed_vision")
    value.update(changes)
    return value


def _spec(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "mingli-physiognomy-input-v1",
        "observation_scope": "face",
        "subject_ref": "sid-0bac48405950e1d63b39cde30608d995",
        "requested_targets": [_target()],
        "assets": [_asset()],
        "observations": [_image_observation()],
        "confirmed_observation_ids": [],
        "comparison_relations": [],
        "source_layer_policy": "terminology_and_methodology_only",
    }
    value.update(changes)
    return value


def _intent(reading_id: str | None = None, *, same_event: bool = False) -> dict[str, object]:
    return {
        "subject_refs": ["sid-0bac48405950e1d63b39cde30608d995"],
        "calculation_object": "visible_observation",
        "question_dimensions": ["state", "source_comparison"],
        "horizon": {"kind": "instant", "start": None, "end": None},
        "requested_method": "physiognomy" if reading_id is None else None,
        "requested_granularity": "region",
        "continuity": {
            "reading_id": reading_id,
            "same_subject": reading_id is not None,
            "same_event": same_event,
        },
        "facts_present": ["physiognomy_spec"],
        "facts_corrected": [],
        "evidence_questions": ["这些可见观察对应哪些历史术语及来源边界"],
    }


def _request(**changes: object) -> ReadingRequest:
    payload: dict[str, object] = {
        "query": "只整理这项可见观察和古籍术语边界",
        "action": "new",
        "system": "physiognomy",
        "intent": _intent(),
        "chart_data": {"physiognomy_spec": _spec()},
        "image_supplied": True,
    }
    payload.update(changes)
    return ReadingRequest(**payload)


def _provider_request(
    spec: dict[str, object],
    *,
    query: str = "只整理这项可见观察和古籍术语边界",
) -> ProviderRequest:
    return ProviderRequest(
        query=query,
        subject_refs=("sid-0bac48405950e1d63b39cde30608d995",),
        object_id="visible_observation",
        dimension_ids=("state", "source_comparison"),
        horizon={"kind": "instant", "start": None, "end": None},
        facts={
            "sid-0bac48405950e1d63b39cde30608d995": {
                "physiognomy_spec": spec
            }
        },
    )


class PhysiognomyProviderContractTests(unittest.TestCase):
    def test_normalizes_visible_observation_without_performing_vision(self) -> None:
        facts = physiognomy.build_fact_layer(_spec())

        self.assertEqual(facts["fact_layer_status"], "observation_driven_physiognomy_facts")
        self.assertFalse(facts["observation_provenance"]["provider_performed_vision"])
        self.assertEqual(facts["output"]["active_observation_ids"], ["oid-8342798c96dfef210cb512918268d772"])
        self.assertEqual(facts["output"]["critical_missing"], [])
        self.assertFalse(
            {"verdict", "conclusion", "prediction"}
            & set(facts["output"])
        )
        self.assertNotIn("diagnosis", json.dumps(facts, ensure_ascii=False).lower())

    def test_image_without_caller_observation_stays_missing(self) -> None:
        facts = physiognomy.build_fact_layer(_spec(observations=[]))
        self.assertEqual(facts["output"]["active_observation_ids"], [])
        self.assertEqual(facts["output"]["critical_missing"], ["visible_observation:tid-0902d05e906e853a141894141a50184e"])
        self.assertFalse(facts["observation_provenance"]["provider_performed_vision"])

    def test_profile_never_mirrors_hidden_subject_side(self) -> None:
        asset = _asset(
            pose_family="left_profile",
            visible_subject_sides="left",
            supplied_visible_regions=["left_eye", "left_ear", "nose", "mouth", "chin"],
            quality=_quality(camera_angle="profile"),
        )
        target = _target("tid-1884a8475f4cc1b54e1781627b28ba87", "right_ear")
        observation = _image_observation(
            "oid-d6aa3affce80d4300693ee1bcebca93a",
            "tid-1884a8475f4cc1b54e1781627b28ba87",
            "right_ear",
            "outline_visible",
        )

        with self.assertRaisesRegex(ValueError, "not visible|hidden|coverage"):
            physiognomy.build_fact_layer(_spec(assets=[asset], requested_targets=[target], observations=[observation]))

        missing = physiognomy.build_fact_layer(_spec(assets=[asset], requested_targets=[target], observations=[]))
        self.assertEqual(missing["output"]["missing_targets"][0]["reason"], "not_visible_in_supplied_view")

    def test_partial_framing_uses_explicit_coverage_and_anchor(self) -> None:
        asset = _asset(framing="upper_crop", supplied_visible_regions=["forehead", "left_eyebrow", "right_eyebrow"])
        facts = physiognomy.build_fact_layer(_spec(assets=[asset]))
        self.assertEqual(facts["output"]["critical_missing"], [])

        target = _target("tid-169e009c140e16305ddddc5154bb2518", "mouth")
        with self.assertRaisesRegex(ValueError, "coverage"):
            physiognomy.build_fact_layer(
                _spec(
                    assets=[asset],
                    requested_targets=[target],
                    observations=[_image_observation("oid-7b499507e5b266b445595ae1328c8e68", "tid-169e009c140e16305ddddc5154bb2518", "mouth", "mouth_closed")],
                )
            )

    def test_low_light_low_resolution_occlusion_and_uncertainty_are_bounded(self) -> None:
        mutations = (
            ("low_light", _asset(quality=_quality(lighting="low")), _image_observation()),
            ("low_resolution", _asset(quality=_quality(resolution="low")), _image_observation()),
            ("occluded", _asset(), _image_observation(occlusion=0.500001)),
            ("uncertain", _asset(), _image_observation(uncertainty=0.500001)),
        )
        for name, asset, observation in mutations:
            with self.subTest(name=name):
                facts = physiognomy.build_fact_layer(_spec(assets=[asset], observations=[observation]))
                self.assertEqual(facts["output"]["active_observation_ids"], [])
                self.assertIn("observation_resolution:tid-0902d05e906e853a141894141a50184e", facts["output"]["critical_missing"])
                self.assertGreaterEqual(len(facts["output"]["uncertainties"]), 1)

    def test_quality_threshold_is_inclusive_at_one_half(self) -> None:
        for value, active in ((0.499999, True), (0.5, True), (0.500001, False)):
            with self.subTest(value=value):
                facts = physiognomy.build_fact_layer(_spec(observations=[_image_observation(occlusion=value, uncertainty=value)]))
                self.assertEqual(bool(facts["output"]["active_observation_ids"]), active)

    def test_filter_rules_are_feature_specific(self) -> None:
        color_filter = _asset(quality=_quality(filtering="color_only", color_fidelity="uncalibrated"))
        morphology = physiognomy.build_fact_layer(_spec(assets=[color_filter]))
        self.assertEqual(morphology["output"]["critical_missing"], [])

        geometry_filter = _asset(quality=_quality(filtering="geometry_altering"))
        blocked = physiognomy.build_fact_layer(_spec(assets=[geometry_filter]))
        self.assertIn("observation_resolution:tid-0902d05e906e853a141894141a50184e", blocked["output"]["critical_missing"])

        complexion_target = _target("tid-5049648dd29eee6e9298139d301498e0", "complexion", feature_kind="capture_color")
        complexion_observation = _image_observation(
            "oid-35d1505ace0bbd7c7fddf80b7bdc5743",
            "tid-5049648dd29eee6e9298139d301498e0",
            "complexion",
            "tone_even_visible",
            feature_kind="capture_color",
        )
        complexion = physiognomy.build_fact_layer(
            _spec(assets=[color_filter], requested_targets=[complexion_target], observations=[complexion_observation])
        )
        self.assertIn("observation_resolution:tid-5049648dd29eee6e9298139d301498e0", complexion["output"]["critical_missing"])

    def test_descriptor_taxonomy_is_bound_to_feature_kind(self) -> None:
        filtered = _asset(
            quality=_quality(
                filtering="color_only",
                color_fidelity="uncalibrated",
            )
        )
        color_as_morphology = _image_observation(
            "oid-2008131904dd40f2d0789dea205aba72",
            "tid-0c79bf88e930abc6220481f9393bc22f",
            "complexion",
            "tone_even_visible",
            feature_kind="visible_morphology",
        )
        morphology_as_color = _image_observation(
            "oid-252966c49576405345dae12edf407211",
            "tid-35b1829f6693e3b3f814c939b5fb3a41",
            "complexion",
            "region_visible",
            feature_kind="capture_color",
        )
        cases = (
            (
                _target(
                    "tid-0c79bf88e930abc6220481f9393bc22f",
                    "complexion",
                    feature_kind="visible_morphology",
                ),
                color_as_morphology,
            ),
            (
                _target(
                    "tid-35b1829f6693e3b3f814c939b5fb3a41",
                    "complexion",
                    feature_kind="capture_color",
                ),
                morphology_as_color,
            ),
        )
        for target, observation in cases:
            with self.subTest(feature_kind=target["feature_kind"]), self.assertRaisesRegex(
                ValueError,
                "descriptor.*feature|feature.*descriptor",
            ):
                physiognomy.build_fact_layer(
                    _spec(
                        assets=[filtered],
                        requested_targets=[target],
                        observations=[observation],
                    )
                )

    def test_capture_color_requires_calibrated_image_bound_provenance(self) -> None:
        target = _target(
            "tid-35b1829f6693e3b3f814c939b5fb3a41",
            "complexion",
            feature_kind="capture_color",
        )
        for source_type in ("user_text", "user_file", "user_correction"):
            observation = _text_observation(
                "oid-34a8264226f7b7f6d9cbfe3724065bf6",
                "tid-35b1829f6693e3b3f814c939b5fb3a41",
                "complexion",
                "tone_even_visible",
                source_type=source_type,
                feature_kind="capture_color",
            )
            if source_type == "user_correction":
                observation["supersedes_observation_id"] = "oid-6dbd28fc451546c5c420d06caf87134f"
                parent = _text_observation(
                    "oid-6dbd28fc451546c5c420d06caf87134f",
                    "tid-35b1829f6693e3b3f814c939b5fb3a41",
                    "complexion",
                    "tone_even_visible",
                    feature_kind="capture_color",
                )
                observations = [parent, observation]
            else:
                observations = [observation]
            with self.subTest(source_type=source_type), self.assertRaisesRegex(
                ValueError,
                "capture_color.*image|calibrated image",
            ):
                physiognomy.build_fact_layer(
                    _spec(
                        assets=[],
                        requested_targets=[target],
                        observations=observations,
                    )
                )

    def test_different_capture_or_lighting_is_never_auto_equivalent(self) -> None:
        second_asset = _asset(
            "aid-8b8e7d374de785aac5c32d4b4504e94f",
            capture_id="cid-5287e79011b0517c92131c5c2220b104",
            sha256=SHA_B,
            quality=_quality(lighting="uneven"),
        )
        second = _image_observation(
            "oid-b51686f393db969715aaf7ad57246325",
            descriptor="contour_flat",
            asset_id="aid-8b8e7d374de785aac5c32d4b4504e94f",
            asset_sha256=SHA_B,
        )
        facts = physiognomy.build_fact_layer(_spec(assets=[_asset(), second_asset], observations=[_image_observation(), second]))

        self.assertEqual(len(facts["output"]["cross_capture_variations"]), 1)
        self.assertEqual(facts["output"]["observation_conflicts"], [])
        self.assertFalse(
            facts["output"]["cross_capture_variations"][0]["auto_equivalent"]
        )

    def test_same_capture_conflict_blocks_until_explicit_confirmation(self) -> None:
        conflicting = _image_observation("oid-b51686f393db969715aaf7ad57246325", descriptor="contour_flat")
        unresolved = physiognomy.build_fact_layer(_spec(observations=[_image_observation(), conflicting]))
        self.assertEqual(unresolved["output"]["active_observation_ids"], [])
        self.assertIn("observation_resolution:tid-0902d05e906e853a141894141a50184e", unresolved["output"]["critical_missing"])
        self.assertEqual(len(unresolved["output"]["observation_conflicts"]), 1)

        resolved = physiognomy.build_fact_layer(
            _spec(observations=[_image_observation(), conflicting], confirmed_observation_ids=["oid-8342798c96dfef210cb512918268d772"])
        )
        self.assertEqual(resolved["output"]["active_observation_ids"], ["oid-8342798c96dfef210cb512918268d772"])
        self.assertEqual(resolved["output"]["critical_missing"], [])

    def test_same_capture_conflict_blocks_even_when_another_capture_is_clean(self) -> None:
        conflicting = _image_observation(
            "oid-e7590c30cf2e0718ab763ae3986ca484",
            descriptor="contour_flat",
        )
        second_asset = _asset(
            "aid-8b8e7d374de785aac5c32d4b4504e94f",
            capture_id="cid-5287e79011b0517c92131c5c2220b104",
            sha256=SHA_B,
        )
        second_capture = _image_observation(
            "oid-790811bef2994143af57d5e572b0ae51",
            asset_id="aid-8b8e7d374de785aac5c32d4b4504e94f",
            asset_sha256=SHA_B,
        )
        facts = physiognomy.build_fact_layer(
            _spec(
                assets=[_asset(), second_asset],
                observations=[
                    _image_observation(),
                    conflicting,
                    second_capture,
                ],
            )
        )

        self.assertEqual(facts["output"]["active_observation_ids"], ["oid-790811bef2994143af57d5e572b0ae51"])
        self.assertIn(
            "observation_resolution:tid-0902d05e906e853a141894141a50184e",
            facts["output"]["critical_missing"],
        )
        self.assertTrue(facts["output"]["observation_conflicts"][0]["blocking"])

    def test_same_capture_visible_and_not_visible_claims_conflict(self) -> None:
        not_visible = _image_observation(
            "oid-d0a857e9d0d181131657e471e2d27ec5",
            visibility="not_visible",
            value=None,
            occlusion=1.0,
        )
        facts = physiognomy.build_fact_layer(
            _spec(observations=[_image_observation(), not_visible])
        )

        self.assertEqual(facts["output"]["active_observation_ids"], [])
        self.assertIn(
            "observation_resolution:tid-0902d05e906e853a141894141a50184e",
            facts["output"]["critical_missing"],
        )
        self.assertTrue(facts["output"]["observation_conflicts"][0]["blocking"])

    def test_confirmed_not_visible_resolution_is_order_independent(self) -> None:
        visible = _image_observation()
        hidden = _image_observation(
            "oid-44444444444444444444444444444444",
            visibility="not_visible",
            value=None,
            occlusion=1.0,
        )
        provider_results = []
        oracle_results = []
        for observations in ([visible, hidden], [hidden, visible]):
            spec = _spec(
                observations=observations,
                confirmed_observation_ids=[hidden["observation_id"]],
            )
            facts = physiognomy.build_fact_layer(spec)
            provider_results.append(
                (
                    facts["output"]["critical_missing"],
                    facts["output"]["missing_targets"][0]["reason"],
                )
            )
            oracle_results.append(
                physiognomy_fixture_reference.reference_projection(spec)[
                    "critical_missing"
                ]
            )
        expected = (
            ["visible_observation:tid-0902d05e906e853a141894141a50184e"],
            "not_visible_in_supplied_view",
        )
        self.assertEqual(provider_results, [expected, expected])
        self.assertEqual(oracle_results, [expected[0], expected[0]])

    def test_resolved_hidden_capture_does_not_mask_other_uncertain_leaf(self) -> None:
        hidden = _image_observation(
            "oid-44444444444444444444444444444444",
            visibility="not_visible",
            value=None,
            occlusion=1.0,
        )
        second_asset = _asset(
            "aid-55555555555555555555555555555555",
            capture_id="cid-99999999999999999999999999999999",
            sha256=SHA_B,
            quality=_quality(lighting="low"),
        )
        low_light_visible = _image_observation(
            "oid-66666666666666666666666666666666",
            asset_id=second_asset["asset_id"],
            asset_sha256=SHA_B,
        )
        spec = _spec(
            assets=[_asset(), second_asset],
            observations=[_image_observation(), hidden, low_light_visible],
            confirmed_observation_ids=[hidden["observation_id"]],
        )

        facts = physiognomy.build_fact_layer(spec)
        expected = [
            "observation_resolution:tid-0902d05e906e853a141894141a50184e"
        ]
        self.assertEqual(facts["output"]["critical_missing"], expected)
        self.assertEqual(
            physiognomy_fixture_reference.reference_projection(spec)[
                "critical_missing"
            ],
            expected,
        )
        self.assertIn(
            "lighting_low",
            {
                reason
                for uncertainty in facts["output"]["uncertainties"]
                for reason in uncertainty["reason_codes"]
            },
        )

    def test_multiple_resolved_capture_conflicts_do_not_overwrite_each_other(self) -> None:
        capture_low = "cid-11111111111111111111111111111111"
        capture_high = "cid-99999999999999999999999999999999"
        asset_b_id = "aid-55555555555555555555555555555555"

        def projection(*, swap_capture_ids: bool) -> tuple[list[str], list[str]]:
            assets = [
                _asset(capture_id=capture_high if swap_capture_ids else capture_low),
                _asset(
                    asset_b_id,
                    capture_id=capture_low if swap_capture_ids else capture_high,
                    sha256=SHA_B,
                ),
            ]
            hidden_a = _image_observation(
                "oid-55555555555555555555555555555555",
                visibility="not_visible",
                value=None,
                occlusion=1.0,
            )
            visible_b = _image_observation(
                "oid-66666666666666666666666666666666",
                asset_id=asset_b_id,
                asset_sha256=SHA_B,
            )
            uncertain_b = _image_observation(
                "oid-77777777777777777777777777777777",
                asset_id=asset_b_id,
                asset_sha256=SHA_B,
                visibility="uncertain",
                value=None,
                uncertainty=1.0,
            )
            spec = _spec(
                assets=assets,
                observations=[
                    _image_observation(),
                    hidden_a,
                    visible_b,
                    uncertain_b,
                ],
                confirmed_observation_ids=[
                    hidden_a["observation_id"],
                    uncertain_b["observation_id"],
                ],
            )
            facts = physiognomy.build_fact_layer(spec)
            return (
                facts["output"]["critical_missing"],
                physiognomy_fixture_reference.reference_projection(spec)[
                    "critical_missing"
                ],
            )

        expected = [
            "observation_resolution:tid-0902d05e906e853a141894141a50184e"
        ]
        self.assertEqual(projection(swap_capture_ids=False), (expected, expected))
        self.assertEqual(projection(swap_capture_ids=True), (expected, expected))

    def test_semantically_duplicate_targets_cannot_bypass_same_capture_conflict(self) -> None:
        second_target = _target("tid-e7fb13567bbba8d799963548d5c1e361")
        second_observation = _image_observation(
            "oid-56a3c38c6e63a0b6b9e5af7c1ce2f65d",
            "tid-e7fb13567bbba8d799963548d5c1e361",
            descriptor="contour_flat",
        )
        with self.assertRaisesRegex(ValueError, "semantic|duplicate.*target"):
            physiognomy.build_fact_layer(
                _spec(
                    requested_targets=[_target(), second_target],
                    observations=[_image_observation(), second_observation],
                )
            )

    def test_comparison_relation_requires_distinct_observations_of_one_target(self) -> None:
        mouth_target = _target("tid-169e009c140e16305ddddc5154bb2518", "mouth")
        mouth_observation = _image_observation(
            "oid-7b499507e5b266b445595ae1328c8e68",
            "tid-169e009c140e16305ddddc5154bb2518",
            "mouth",
            "mouth_closed",
        )
        invalid_relations = (
            {
                "relation": "same_target_user_confirmed",
                "target_id": "tid-0902d05e906e853a141894141a50184e",
                "observation_ids": ["oid-8342798c96dfef210cb512918268d772", "oid-7b499507e5b266b445595ae1328c8e68"],
            },
            {
                "relation": "same_target_user_confirmed",
                "target_id": "tid-0902d05e906e853a141894141a50184e",
                "observation_ids": ["oid-8342798c96dfef210cb512918268d772", "oid-8342798c96dfef210cb512918268d772"],
            },
        )
        for relation in invalid_relations:
            with self.subTest(relation=relation), self.assertRaises(ValueError):
                physiognomy.build_fact_layer(
                    _spec(
                        requested_targets=[_target(), mouth_target],
                        observations=[_image_observation(), mouth_observation],
                        comparison_relations=[relation],
                    )
                )

    def test_text_observation_can_be_corrected_without_image_provenance(self) -> None:
        original = _text_observation()
        correction = _text_observation(
            "oid-ad84fd033a041f3e68b16d872c48b1d6",
            descriptor="contour_flat",
            source_type="user_correction",
            supersedes_observation_id=original["observation_id"],
            source_ref=original["source_ref"],
        )
        facts = physiognomy.build_fact_layer(
            _spec(
                assets=[],
                observations=[original, correction],
            )
        )
        self.assertEqual(
            facts["output"]["active_observation_ids"],
            ["oid-ad84fd033a041f3e68b16d872c48b1d6"],
        )

    def test_user_correction_preserves_lineage_and_changes_digest(self) -> None:
        original = physiognomy.build_fact_layer(_spec())
        correction = _correction_observation(
            "oid-d2404a725325875299736d44739b9f32",
            descriptor="contour_flat",
        )
        corrected = physiognomy.build_fact_layer(_spec(observations=[_image_observation(), correction]))

        self.assertNotEqual(corrected["fact_digest"], original["fact_digest"])
        self.assertEqual(corrected["output"]["active_observation_ids"], ["oid-d2404a725325875299736d44739b9f32"])
        self.assertEqual(corrected["output"]["superseded_observation_ids"], ["oid-8342798c96dfef210cb512918268d772"])

    def test_superseded_and_resolved_losers_do_not_pollute_uncertainties(self) -> None:
        stale = _image_observation(uncertainty=0.9)
        correction = _correction_observation(
            "oid-d2404a725325875299736d44739b9f32",
            descriptor="contour_rounded",
        )
        corrected = physiognomy.build_fact_layer(
            _spec(observations=[stale, correction])
        )
        self.assertEqual(corrected["output"]["uncertainties"], [])

        uncertain_loser = _image_observation(
            "oid-44444444444444444444444444444444",
            visibility="uncertain",
            value=None,
            uncertainty=1.0,
        )
        resolved = physiognomy.build_fact_layer(
            _spec(
                observations=[_image_observation(), uncertain_loser],
                confirmed_observation_ids=[
                    "oid-8342798c96dfef210cb512918268d772"
                ],
            )
        )
        self.assertEqual(resolved["output"]["uncertainties"], [])

    def test_correction_to_not_visible_makes_target_missing(self) -> None:
        correction = _correction_observation(
            "oid-d2404a725325875299736d44739b9f32",
            visibility="not_visible",
            value=None,
        )
        facts = physiognomy.build_fact_layer(_spec(observations=[_image_observation(), correction]))
        self.assertEqual(facts["output"]["active_observation_ids"], [])
        self.assertEqual(facts["output"]["superseded_observation_ids"], ["oid-8342798c96dfef210cb512918268d772"])
        self.assertIn("visible_observation:tid-0902d05e906e853a141894141a50184e", facts["output"]["critical_missing"])

    def test_bad_correction_lineage_fails_closed(self) -> None:
        bad_cases = (
            _correction_observation("correction-missing", supersedes_observation_id="not-found"),
            _correction_observation("correction-region", "tid-169e009c140e16305ddddc5154bb2518", "mouth", "mouth_closed"),
        )
        for correction in bad_cases:
            with self.subTest(correction=correction["observation_id"]), self.assertRaises(ValueError):
                physiognomy.build_fact_layer(_spec(observations=[_image_observation(), correction]))

    def test_recursive_allowlist_rejects_inference_and_raw_media_fields(self) -> None:
        forbidden = (
            {"personality": "decisive"},
            {"value": {"descriptor": "contour_rounded", "wealth": "high"}},
            {"identity": {"name": "someone"}},
            {"raw_image_base64": "AAAA"},
            {"face_embedding": [0.1, 0.2]},
            {"exif": {"gps": "private"}},
        )
        for injected in forbidden:
            observation = _image_observation()
            observation.update(injected)
            with self.subTest(field=next(iter(injected))), self.assertRaises(ValueError):
                physiognomy.build_fact_layer(_spec(observations=[observation]))

    def test_source_type_uses_an_exact_conditional_schema(self) -> None:
        image_smuggling = _image_observation(
            quality={
                "raw_image_base64": "NESTED_SECRET",
                "personality": "invented",
            }
        )
        correction_smuggling = _correction_observation(
            source_ref="forged-source-ref",
            quality={"raw_image_base64": "NESTED_SECRET"},
            transcription_actor="forged-actor",
            provider_performed_vision=True,
        )
        text_smuggling = _text_observation(
            asset_id="aid-77072c872df89a9e9c89483dea1e14e5",
            asset_sha256=SHA_A,
            region_anchor=_anchor(),
        )
        for observation in (
            image_smuggling,
            correction_smuggling,
            text_smuggling,
        ):
            with self.subTest(source_type=observation["source_type"]), self.assertRaises(
                ValueError
            ):
                physiognomy.build_fact_layer(_spec(observations=[observation]))

    def test_opaque_identifiers_must_be_long_enough_for_exact_privacy_filtering(self) -> None:
        short_asset = _asset("a", capture_id="c", subject_ref="sub")
        short_target = _target("t")
        short_observation = _image_observation(
            "o",
            "t",
            asset_id="a",
            asset_sha256=SHA_A,
        )
        with self.assertRaisesRegex(ValueError, "opaque identifier"):
            physiognomy.build_fact_layer(
                _spec(
                    subject_ref="sub",
                    assets=[short_asset],
                    requested_targets=[short_target],
                    observations=[short_observation],
                )
            )

    def test_opaque_identifiers_reject_human_names_emails_and_non_ascii_text(self) -> None:
        for identifier in (
            "Alice Smith private",
            "Alice-Smith-private",
            "alice@example.com",
            "私人主体标识",
            "alicesmithprivate",
            "asset-alice-smith-1",
        ):
            spec = _spec(
                subject_ref=identifier,
                assets=[_asset(subject_ref=identifier)],
            )
            intent = _intent()
            intent["subject_refs"] = [identifier]
            with self.subTest(identifier=identifier), self.assertRaisesRegex(
                ValueError,
                "opaque identifier",
            ):
                PhysiognomyProvider(ROOT).calculate(
                    _request(
                        intent=intent,
                        chart_data={"physiognomy_spec": spec},
                    )
                )

    def test_opaque_identifiers_enforce_field_namespaces(self) -> None:
        private_subject = "aid-0123456789abcdef0123456789abcdef"
        with self.assertRaisesRegex(ValueError, "opaque identifier namespace"):
            physiognomy.build_fact_layer(
                _spec(
                    subject_ref=private_subject,
                    assets=[
                        _asset(
                            "sid-0123456789abcdef0123456789abcdef",
                            capture_id="tid-0123456789abcdef0123456789abcdef",
                            subject_ref=private_subject,
                        )
                    ],
                )
            )

    def test_subject_identifier_components_remain_private(self) -> None:
        private_subject = "sid-0123456789abcdef0123456789abcdef"
        facts = physiognomy.build_fact_layer(
            _spec(
                subject_ref=private_subject,
                assets=[_asset(subject_ref=private_subject)],
            )
        )
        self.assertTrue(
            physiognomy.public_copy_contains_private_provenance(
                facts, "0123456789abcdef0123456789abcdef"
            )
        )

    def test_unknown_descriptor_false_vision_and_malformed_anchor_fail_closed(self) -> None:
        observations = (
            _image_observation(descriptor="healthy_and_wealthy"),
            _image_observation(provider_performed_vision=True),
            _image_observation(region_anchor=_anchor(x=-0.1)),
            _image_observation(region_anchor=_anchor(width=0.0)),
        )
        for observation in observations:
            with self.subTest(observation=observation), self.assertRaises(ValueError):
                physiognomy.build_fact_layer(_spec(observations=[observation]))

    def test_asset_hash_subject_view_angle_and_annotation_binding_are_strict(self) -> None:
        bad_assets = (
            _asset(sha256="not-a-sha"),
            _asset(subject_ref="other-subject"),
            _asset(pose_family="left_profile", visible_subject_sides="left", quality=_quality(camera_angle="frontal")),
        )
        for asset in bad_assets:
            with self.subTest(asset=asset), self.assertRaises(ValueError):
                physiognomy.build_fact_layer(_spec(assets=[asset]))

    def test_three_quarter_pose_must_match_declared_visible_subject_side(self) -> None:
        bilateral = list(_asset()["supplied_visible_regions"])
        bad_assets = (
            _asset(
                pose_family="three_quarter_left",
                visible_subject_sides="right",
                supplied_visible_regions=[
                    region for region in bilateral if region != "right_ear"
                ],
                quality=_quality(camera_angle="three_quarter"),
            ),
            _asset(
                pose_family="three_quarter_right",
                visible_subject_sides="left",
                supplied_visible_regions=[
                    region for region in bilateral if region != "left_ear"
                ],
                quality=_quality(camera_angle="three_quarter"),
            ),
        )
        for asset in bad_assets:
            with self.subTest(pose=asset["pose_family"]), self.assertRaisesRegex(
                ValueError,
                "three_quarter|visible.*side",
            ):
                physiognomy.build_fact_layer(_spec(assets=[asset]))

    def test_partial_framing_cannot_claim_regions_outside_the_crop(self) -> None:
        cases = (
            (
                _asset(framing="upper_crop", supplied_visible_regions=["chin"]),
                _target("tid-22222222222222222222222222222222", "chin"),
                _image_observation(
                    "oid-22222222222222222222222222222222",
                    "tid-22222222222222222222222222222222",
                    "chin",
                    "contour_rounded",
                ),
            ),
            (
                _asset(framing="lower_crop", supplied_visible_regions=["forehead"]),
                _target("tid-33333333333333333333333333333333", "forehead"),
                _image_observation(
                    "oid-33333333333333333333333333333333",
                    "tid-33333333333333333333333333333333",
                    "forehead",
                    "contour_rounded",
                ),
            ),
        )
        for asset, target, observation in cases:
            with self.subTest(framing=asset["framing"]), self.assertRaisesRegex(
                ValueError,
                "framing.*coverage",
            ):
                physiognomy.build_fact_layer(
                    _spec(
                        assets=[asset],
                        requested_targets=[target],
                        observations=[observation],
                    )
                )

    def test_detail_pose_cannot_claim_the_opposite_subject_side(self) -> None:
        asset = _asset(
            pose_family="detail",
            visible_subject_sides="left",
            framing="region_crop",
            supplied_visible_regions=["right_eye"],
            quality=_quality(camera_angle="oblique"),
        )
        target = _target("tid-fdea5bb8ffda88fdc4efdb1f15922e4a", "right_eye")
        observation = _image_observation(
            "oid-0d8c54f4d7578744466d6b8cac8531fb",
            "tid-fdea5bb8ffda88fdc4efdb1f15922e4a",
            "right_eye",
            "aperture_open",
        )
        with self.assertRaisesRegex(ValueError, "side|visibility"):
            physiognomy.build_fact_layer(
                _spec(
                    assets=[asset],
                    requested_targets=[target],
                    observations=[observation],
                )
            )

    def test_three_quarter_view_keeps_visible_far_eye_and_cheek_regions(self) -> None:
        asset = _asset(
            pose_family="three_quarter_left",
            visible_subject_sides="left",
            supplied_visible_regions=["right_eye", "right_cheek"],
            quality=_quality(camera_angle="three_quarter"),
        )
        target = _target("tid-fdea5bb8ffda88fdc4efdb1f15922e4a", "right_eye")
        observation = _image_observation(
            "oid-0d8c54f4d7578744466d6b8cac8531fb",
            "tid-fdea5bb8ffda88fdc4efdb1f15922e4a",
            "right_eye",
            "aperture_open",
        )
        facts = physiognomy.build_fact_layer(
            _spec(
                assets=[asset],
                requested_targets=[target],
                observations=[observation],
            )
        )
        self.assertEqual(
            [
                item["region"]
                for item in facts["output"]["normalized_visible_observations"]
            ],
            ["right_eye"],
        )

    def test_profile_view_rejects_bilateral_width_descriptors(self) -> None:
        asset = _asset(
            pose_family="left_profile",
            visible_subject_sides="left",
            supplied_visible_regions=["forehead"],
            quality=_quality(camera_angle="profile"),
        )
        observation = _image_observation(descriptor="relative_width_broad")
        with self.assertRaisesRegex(ValueError, "descriptor.*pose|view"):
            physiognomy.build_fact_layer(
                _spec(assets=[asset], observations=[observation])
            )

    def test_relative_descriptors_require_visible_comparison_context(self) -> None:
        forehead_crop = _asset(
            pose_family="frontal",
            visible_subject_sides="bilateral",
            framing="region_crop",
            supplied_visible_regions=["forehead"],
        )
        forehead = _image_observation(descriptor="relative_width_broad")

        eye_crop = _asset(
            pose_family="frontal",
            visible_subject_sides="bilateral",
            framing="region_crop",
            supplied_visible_regions=["left_eye"],
        )
        eye_target = _target("tid-2635de0d1c8fd01dfa74b42f486e2f20", "left_eye")
        eye = _image_observation(
            "oid-3abf13b1572711368405b67def9bdb7a",
            "tid-2635de0d1c8fd01dfa74b42f486e2f20",
            "left_eye",
            "alignment_level",
        )
        for asset, target, observation in (
            (forehead_crop, _target(), forehead),
            (eye_crop, eye_target, eye),
        ):
            with self.subTest(region=target["region"]), self.assertRaisesRegex(
                ValueError,
                "context|framing|view",
            ):
                physiognomy.build_fact_layer(
                    _spec(
                        assets=[asset],
                        requested_targets=[target],
                        observations=[observation],
                    )
                )

    def test_region_anchor_must_cover_at_least_one_source_pixel_per_axis(self) -> None:
        observation = _image_observation(
            region_anchor=_anchor(width=5e-324, height=5e-324),
        )
        with self.assertRaisesRegex(ValueError, "pixel|anchor"):
            physiognomy.build_fact_layer(
                _spec(observations=[observation])
            )

    def test_capture_id_and_asset_hash_form_a_bijection(self) -> None:
        same_capture = _asset(
            "aid-8b8e7d374de785aac5c32d4b4504e94f",
            capture_id="cid-421b5f386a3bd17c0403216536556e80",
            sha256=SHA_B,
        )
        same_hash = _asset(
            "aid-8b8e7d374de785aac5c32d4b4504e94f",
            capture_id="cid-5287e79011b0517c92131c5c2220b104",
            sha256=SHA_A,
        )
        for asset in (same_capture, same_hash):
            with self.subTest(asset=asset["asset_id"]), self.assertRaisesRegex(
                ValueError,
                "capture/hash binding",
            ):
                physiognomy.build_fact_layer(_spec(assets=[_asset(), asset]))

    def test_request_subject_must_exactly_bind_the_observation_subject(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        provider.calculate(_request())
        wrong_subject = "sid-11111111111111111111111111111111"
        intent = _intent()
        intent["subject_refs"] = [wrong_subject]
        with self.assertRaisesRegex(ValueError, "subject binding mismatch"):
            provider.calculate(_request(intent=intent))

        for subject_refs in (
            [],
            ["sid-0bac48405950e1d63b39cde30608d995", wrong_subject],
        ):
            intent = _intent()
            intent["subject_refs"] = subject_refs
            with self.subTest(subject_refs=subject_refs), self.assertRaisesRegex(
                ValueError,
                "exactly one",
            ):
                provider.calculate(_request(intent=intent))

    def test_provider_rejects_raw_media_outside_the_physio_spec(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        requests = (
            _request(
                chart_data={
                    "physiognomy_spec": _spec(),
                    "raw_image_base64": "SECRET_RAW_MEDIA",
                }
            ),
            _request(
                metadata={
                    "capture": {
                        "image_url": "https://private.invalid/face.png",
                    }
                }
            ),
        )
        for request in requests:
            with self.subTest(request=request.to_dict()), self.assertRaisesRegex(
                ValueError,
                "raw media|chart_data|image_url|raw_image",
            ):
                provider.calculate(request)

    def test_long_plain_english_query_is_not_mistaken_for_base64_media(self) -> None:
        request = _request(
            query=(
                "Please organize only the supplied visible observation and its "
                "source boundary without inferring identity personality health "
                "wealth lifespan or any feature that is not directly visible. "
            )
            * 2,
        )
        calculation = PhysiognomyProvider(ROOT).calculate(request)
        self.assertEqual(calculation.system, "physiognomy")

    def test_natural_chinese_slash_enumerations_are_not_file_locators(self) -> None:
        for text in (
            "观察额头/眉眼/鼻部。",
            "采用明/清/民国分层。",
            "今天/明天/后天",
            "比较 x<y 与 a>b 的可见比例。",
        ):
            with self.subTest(text=text):
                self.assertEqual(physiognomy._raw_media_key_paths(text), ())
        self.assertNotEqual(
            physiognomy._raw_media_key_paths(
                "/Users/alice/Library/Photos/123"
            ),
            (),
        )

    def test_image_transcription_requires_request_image_presence_but_text_does_not(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        with self.assertRaisesRegex(ValueError, "image.*supplied|image presence"):
            provider.calculate(_request(image_supplied=False))

        text_only = _spec(
            assets=[],
            observations=[_text_observation()],
        )
        calculated = provider.calculate(
            _request(
                chart_data={"physiognomy_spec": text_only},
                image_supplied=False,
            )
        )
        self.assertEqual(calculated.system, "physiognomy")

    def test_fact_digest_is_stable_across_python_hash_seeds(self) -> None:
        program = """
from reading_engine import physiognomy
from test_v51_physiognomy_completion import _spec
print(physiognomy.build_fact_layer(_spec())['fact_digest'])
"""
        digests = []
        for seed in ("1", "17", "999"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            result = subprocess.run(
                [sys.executable, "-c", program], cwd=ROOT, env=environment,
                check=True, capture_output=True, text=True,
            )
            digests.append(result.stdout.strip())
        self.assertEqual(len(set(digests)), 1)


class PhysiognomyAuditAndIntegrationTests(unittest.TestCase):
    def test_machine_readable_audit_proves_fixture_and_source_contract(self) -> None:
        report = audit_physiognomy_provider.audit_physiognomy_provider()
        self.assertTrue(report["provider_ready"], report)
        self.assertGreaterEqual(report["counts"]["complete_fixtures"], 20)
        self.assertGreaterEqual(report["counts"]["unique_scenarios"], 20)
        self.assertGreaterEqual(report["counts"]["unique_assets"], 8)
        self.assertGreaterEqual(report["counts"]["boundary_fixtures"], 5)
        self.assertTrue(
            {"hidden_side", "low_light", "filtered", "contradictory", "corrected_to_missing"}
            <= set(report["boundary_categories"])
        )
        self.assertEqual(report["counts"]["fixture_mismatches"], 0)
        self.assertEqual(report["counts"]["observation_fact_key_mismatches"], 0)
        self.assertEqual(report["counts"]["oracle_mismatches"], 0)
        self.assertEqual(report["counts"]["asset_mismatches"], 0)
        self.assertEqual(report["counts"]["high_risk_activations"], 0)
        self.assertEqual(report["counts"]["evidence_rules_without_exact_predicates"], 0)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 3)
        self.assertEqual(report["counts"]["registered_source_packs"], 3)
        self.assertEqual(report["counts"]["independent_voting_source_packs"], 0)
        self.assertEqual(report["counts"]["algorithm_samples_executed"], 3)
        self.assertEqual(report["counts"]["algorithm_sample_mismatches"], 0)
        self.assertEqual(report["counts"]["safe_rule_role_mismatches"], 0)
        self.assertEqual(report["counts"]["source_priority_mismatches"], 0)
        self.assertEqual(len(report["source_lineage_registry_sha256"]), 64)
        self.assertEqual(report["findings"], [])

    def test_audit_rejects_source_table_and_fixture_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / SOURCE_TABLE.name
            fixture_path = root / FIXTURE.name
            source_path.write_text(
                SOURCE_TABLE.read_text(encoding="utf-8") + "\n# deliberate mutation\n",
                encoding="utf-8",
            )
            fixture_path.write_text(
                FIXTURE.read_text(encoding="utf-8") + "\n# deliberate mutation\n",
                encoding="utf-8",
            )

            source_report = audit_physiognomy_provider.audit_physiognomy_provider(
                source_table_path=source_path,
            )
            fixture_report = audit_physiognomy_provider.audit_physiognomy_provider(
                fixture_path=fixture_path,
            )

        self.assertFalse(source_report["provider_ready"])
        self.assertIn(
            "Physiognomy source-table artifact hash mismatch",
            source_report["findings"],
        )
        self.assertFalse(fixture_report["provider_ready"])
        self.assertIn(
            "Physiognomy fixture artifact hash mismatch",
            fixture_report["findings"],
        )

    def test_audit_rejects_unbounded_assets_and_stale_framing_ceiling(self) -> None:
        table = yaml.safe_load(SOURCE_TABLE.read_text(encoding="utf-8"))
        table["asset_contract"]["maximum_byte_length"] = 10**30
        table["asset_contract"]["maximum_pixel_axis"] = 0
        table["visibility_contract"]["framing_region_ceiling"][
            "upper_crop"
        ].append("mouth")
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / SOURCE_TABLE.name
            source_path.write_text(
                yaml.safe_dump(table, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            fixture["source_table_sha256"] = source_digest
            fixture_path = root / FIXTURE.name
            fixture_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            fixture_digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
            with (
                mock.patch.object(
                    audit_physiognomy_provider,
                    "SOURCE_TABLE_SHA256",
                    source_digest,
                ),
                mock.patch.object(
                    audit_physiognomy_provider,
                    "FIXTURE_SHA256",
                    fixture_digest,
                ),
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    source_table_path=source_path,
                    fixture_path=fixture_path,
                )

        self.assertIn(
            "Physiognomy asset size ceilings are unreasonable",
            report["findings"],
        )
        self.assertIn(
            "Physiognomy framing region ceilings are stale",
            report["findings"],
        )

    def test_audit_rejects_release_rule_hash_detached_from_source_profile(self) -> None:
        table = yaml.safe_load(SOURCE_TABLE.read_text(encoding="utf-8"))
        table["source_profiles"]["liuzhuang_xiangfa"][
            "release_rules_sha256"
        ] = "0" * 64
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / SOURCE_TABLE.name
            source_path.write_text(
                yaml.safe_dump(table, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            fixture["source_table_sha256"] = source_digest
            fixture_path = root / FIXTURE.name
            fixture_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            fixture_digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
            with (
                mock.patch.object(
                    audit_physiognomy_provider,
                    "SOURCE_TABLE_SHA256",
                    source_digest,
                ),
                mock.patch.object(
                    audit_physiognomy_provider,
                    "FIXTURE_SHA256",
                    fixture_digest,
                ),
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    source_table_path=source_path,
                    fixture_path=fixture_path,
                )

        self.assertIn(
            "Physiognomy release rule hash mismatch: liuzhuang_xiangfa",
            report["findings"],
        )

    def test_audit_rejects_release_rule_symlink_even_inside_release_root(self) -> None:
        real_rules = (
            ROOT
            / "references/books/physiognomy/liuzhuang-xiangfa/rules.md"
        )
        with tempfile.TemporaryDirectory() as temporary:
            fake_root = Path(temporary)
            target = fake_root / "targets/liuzhuang-rules.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(real_rules.read_bytes())
            candidate = (
                fake_root
                / "references/books/physiognomy/liuzhuang-xiangfa/rules.md"
            )
            candidate.parent.mkdir(parents=True)
            candidate.symlink_to(target)
            with mock.patch.object(
                audit_physiognomy_provider,
                "ROOT",
                fake_root,
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider()

        self.assertIn(
            "Physiognomy release rule path mismatch: liuzhuang_xiangfa",
            report["findings"],
        )

    def test_audit_counts_semantic_scenarios_referenced_assets_and_real_boundaries(self) -> None:
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        base_case = next(
            copy.deepcopy(case)
            for case in fixture["complete_cases"]
            if case["case_id"]
            == "complete-cross-capture-observation-specificity-separated"
        )
        duplicate_cases = []
        for index in range(21):
            case = copy.deepcopy(base_case)
            case["case_id"] = f"opaque-id-only-{index}"
            target_id = "tid-" + hashlib.sha256(
                f"opaque-target:{index}".encode("utf-8")
            ).hexdigest()[:32]
            case["input"]["requested_targets"][0]["target_id"] = target_id
            asset_ids: dict[str, str] = {}
            for asset_index, asset in enumerate(case["input"]["assets"]):
                old_asset_id = asset["asset_id"]
                asset_ids[old_asset_id] = "aid-" + hashlib.sha256(
                    f"opaque-asset:{index}:{asset_index}".encode("utf-8")
                ).hexdigest()[:32]
                asset["asset_id"] = asset_ids[old_asset_id]
                asset["capture_id"] = "cid-" + hashlib.sha256(
                    f"opaque-capture:{index}:{asset_index}".encode("utf-8")
                ).hexdigest()[:32]
            for observation_index, observation in enumerate(
                case["input"]["observations"]
            ):
                observation["target_id"] = target_id
                observation["observation_id"] = "oid-" + hashlib.sha256(
                    f"opaque-observation:{index}:{observation_index}".encode("utf-8")
                ).hexdigest()[:32]
                observation["asset_id"] = asset_ids[observation["asset_id"]]
            duplicate_cases.append(case)
        duplicate_cases[1]["input"]["assets"] = list(
            reversed(duplicate_cases[1]["input"]["assets"])
        )
        duplicate_cases[2]["input"]["requested_targets"] = list(
            reversed(duplicate_cases[2]["input"]["requested_targets"])
        )
        duplicate_cases[3]["input"]["observations"] = list(
            reversed(duplicate_cases[3]["input"]["observations"])
        )
        base_boundary = next(
            copy.deepcopy(case)
            for case in fixture["boundary_cases"]
            if case["category"] == "low_light"
        )
        false_hidden = next(
            copy.deepcopy(case)
            for case in fixture["boundary_cases"]
            if case["category"] == "hidden_side"
        )
        false_hidden["case_id"] = "false-hidden-side-schema-error"
        false_hidden["input"]["requested_targets"][0]["region"] = "left_ear"
        false_hidden["input"]["observations"][0]["region"] = "left_ear"
        false_hidden["input"]["observations"][0]["unexpected_field"] = True
        false_hidden["expected_error_regex"] = "unexpected"
        categories = (
            "hidden_side",
            "low_light",
            "filtered",
            "contradictory",
            "corrected_to_missing",
        )
        fixture["complete_cases"] = duplicate_cases
        fixture["boundary_cases"] = []
        for index, category in enumerate(categories):
            case = copy.deepcopy(base_boundary)
            case["case_id"] = f"false-boundary-label-{index}"
            case["category"] = category
            fixture["boundary_cases"].append(case)
        fixture["boundary_cases"][0] = false_hidden

        with tempfile.TemporaryDirectory() as temporary:
            fixture_path = Path(temporary) / "physiognomy-fixture.yaml"
            fixture_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            fixture_digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
            with mock.patch.object(
                audit_physiognomy_provider,
                "FIXTURE_SHA256",
                fixture_digest,
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    fixture_path=fixture_path,
                )

        self.assertFalse(report["provider_ready"], report)
        self.assertEqual(report["counts"]["unique_scenarios"], 1)
        self.assertEqual(report["counts"]["unique_assets"], 2)
        self.assertGreater(report["counts"]["boundary_mismatches"], 0)

    def test_audit_scenario_digest_tracks_anchor_gate_not_raw_dimensions(self) -> None:
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        base = next(
            copy.deepcopy(case["input"])
            for case in fixture["complete_cases"]
            if case["case_id"]
            == "complete-cross-capture-observation-specificity-separated"
        )
        below_minimum = copy.deepcopy(base)
        below_minimum["observations"][0]["region_anchor"]["width"] = 5e-324
        wrong_anchor_type = copy.deepcopy(base)
        wrong_anchor_type["observations"][0]["region_anchor"]["width"] = "0.5"
        wrong_anchor_kind = copy.deepcopy(base)
        wrong_anchor_kind["observations"][0]["region_anchor"]["kind"] = "pixels"
        dimension_only = copy.deepcopy(base)
        dimension_only["assets"][0]["pixel_width"] += 1

        base_digest = canonical_digest(
            audit_physiognomy_provider._semantic_scenario_payload(base)
        )
        below_digest = canonical_digest(
            audit_physiognomy_provider._semantic_scenario_payload(below_minimum)
        )
        dimension_digest = canonical_digest(
            audit_physiognomy_provider._semantic_scenario_payload(dimension_only)
        )
        self.assertNotEqual(base_digest, below_digest)
        self.assertNotEqual(
            base_digest,
            canonical_digest(
                audit_physiognomy_provider._semantic_scenario_payload(
                    wrong_anchor_type
                )
            ),
        )
        self.assertNotEqual(
            base_digest,
            canonical_digest(
                audit_physiognomy_provider._semantic_scenario_payload(
                    wrong_anchor_kind
                )
            ),
        )
        self.assertEqual(base_digest, dimension_digest)

    def test_audit_rejects_image_descriptor_not_grounded_in_annotation(self) -> None:
        annotation_path = ASSET_ROOT / "annotation-manifest-v1.yaml"
        annotation = yaml.safe_load(annotation_path.read_text(encoding="utf-8"))
        annotation["assets"]["front-even.svg"]["descriptors"] = {
            "forehead": ["contour_flat"]
        }
        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / annotation_path.name
            mutated_path.write_text(
                yaml.safe_dump(annotation, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            mutated_hash = hashlib.sha256(mutated_path.read_bytes()).hexdigest()
            with mock.patch.object(
                audit_physiognomy_provider,
                "ANNOTATION_SHA256",
                mutated_hash,
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    annotation_path=mutated_path,
                )

        self.assertFalse(report["provider_ready"])
        self.assertTrue(
            any(
                "descriptor annotation binding mismatch" in finding
                for finding in report["findings"]
            ),
            report,
        )

    def test_audit_checks_active_image_bound_user_correction_descriptor(self) -> None:
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        case = next(
            row
            for row in fixture["complete_cases"]
            if row["case_id"] == "complete-user-correction-replaces-visible"
        )
        original, correction = case["input"]["observations"]
        original["value"]["descriptor"] = "contour_rounded"
        correction["value"]["descriptor"] = "contour_flat"
        case["expected"]["active_descriptors"] = ["contour_flat"]
        with tempfile.TemporaryDirectory() as temporary:
            mutated_path = Path(temporary) / FIXTURE.name
            mutated_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            mutated_hash = hashlib.sha256(mutated_path.read_bytes()).hexdigest()
            with mock.patch.object(
                audit_physiognomy_provider,
                "FIXTURE_SHA256",
                mutated_hash,
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    fixture_path=mutated_path,
                )

        self.assertTrue(
            any(
                "descriptor annotation binding mismatch: "
                "complete-user-correction-replaces-visible" in finding
                for finding in report["findings"]
            ),
            report,
        )

    def test_audit_executes_the_hash_bound_oracle_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            oracle_path = Path(temporary) / "raising_oracle.py"
            oracle_path.write_text(
                "def reference_projection(spec):\n"
                "    raise RuntimeError('CUSTOM_ORACLE_EXECUTED')\n",
                encoding="utf-8",
            )
            oracle_digest = hashlib.sha256(oracle_path.read_bytes()).hexdigest()
            with mock.patch.object(
                audit_physiognomy_provider,
                "ORACLE_SHA256",
                oracle_digest,
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    oracle_path=oracle_path,
                )

        self.assertFalse(report["provider_ready"], report)
        self.assertGreater(report["counts"]["oracle_mismatches"], 0)
        self.assertTrue(
            any("CUSTOM_ORACLE_EXECUTED" in item for item in report["findings"]),
            report,
        )

    def test_audit_closes_matrix_sample_binding(self) -> None:
        matrix = yaml.safe_load(
            (ROOT / "references/matrices/algorithm-source-dependencies.yaml").read_text(
                encoding="utf-8"
            )
        )
        dependency = matrix["providers"]["physiognomy"]["dependencies"][0]
        dependency["independent_test_sample"]["input"] = "not the bound fixture"
        dependency["independent_test_sample"]["expected"] = (
            "arbitrary impossible output"
        )
        with tempfile.TemporaryDirectory() as temporary:
            matrix_path = Path(temporary) / "algorithm-source-dependencies.yaml"
            matrix_path.write_text(
                yaml.safe_dump(matrix, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_physiognomy_provider.audit_physiognomy_provider(
                matrix_path=matrix_path,
            )

        self.assertFalse(report["provider_ready"], report)
        self.assertTrue(
            any("sample binding mismatch" in item for item in report["findings"]),
            report,
        )

    def test_audit_rejects_oracle_import_through_scripts_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            oracle_path = Path(temporary) / "dependent_oracle.py"
            oracle_path.write_text(
                "from scripts.reading_engine import physiognomy\n"
                "def reference_projection(spec):\n"
                "    return physiognomy.build_fact_layer(spec)\n",
                encoding="utf-8",
            )
            oracle_digest = hashlib.sha256(oracle_path.read_bytes()).hexdigest()
            with mock.patch.object(
                audit_physiognomy_provider,
                "ORACLE_SHA256",
                oracle_digest,
            ):
                report = audit_physiognomy_provider.audit_physiognomy_provider(
                    oracle_path=oracle_path,
                )

        self.assertFalse(report["provider_ready"], report)
        self.assertIn(
            "Physiognomy oracle imports production provider code",
            report["findings"],
        )

    def test_fixture_assets_are_synthetic_hash_bound_and_nonidentifying(self) -> None:
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        manifest = fixture["asset_manifest"]
        self.assertGreaterEqual(len(manifest), 8)
        for item in manifest:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            self.assertTrue(item["synthetic"])
            self.assertTrue(item["no_real_person"])
            self.assertEqual(len(item["sha256"]), 64)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("<script", text.lower())
            self.assertNotIn("foreignObject", text)
            self.assertNotRegex(text, r"(?:https?:|data:image)")

    def test_capability_factory_and_generic_route_are_closed(self) -> None:
        capability = PROVIDER_CAPABILITIES["physiognomy"]
        self.assertEqual(capability.mode, "observation_driven_ready")
        self.assertEqual(capability.objects, ("visible_observation",))
        self.assertEqual(capability.horizons, ("instant",))
        self.assertNotIn("*", capability.dimensions)
        self.assertEqual(capability.required_inputs, ("physiognomy_spec",))
        self.assertNotIn("physiognomy", STRUCTURED_SYSTEMS)
        self.assertEqual(PhysiognomyProvider.SOURCE_ROUTE["pack_policy"], "locked")

        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
        self.assertIsInstance(engine.providers["physiognomy"], PhysiognomyProvider)
        with self.assertRaises(ValueError):
            StructuredChartProvider(ROOT, "physiognomy")
        with self.assertRaises(ValueError):
            structured_chart_adapter.build_payload("physiognomy", {"output": {}})
        with self.assertRaises(ValueError):
            normalize_structured_chart("physiognomy", {"output": {}})

    def test_missing_inputs_are_target_scoped_and_optional_gaps_do_not_block(self) -> None:
        empty = _request(chart_data={})
        missing = _request(chart_data={"physiognomy_spec": _spec(observations=[])})
        optional = _request(
            chart_data={
                "physiognomy_spec": _spec(
                    requested_targets=[_target(), _target("tid-169e009c140e16305ddddc5154bb2518", "mouth", required=False)],
                )
            }
        )
        self.assertEqual(missing_required_inputs("physiognomy", empty), ("physiognomy_spec",))
        self.assertEqual(missing_required_inputs("physiognomy", missing), ("visible_observation:tid-0902d05e906e853a141894141a50184e",))
        self.assertEqual(missing_required_inputs("physiognomy", optional), ())

    def test_provider_extends_only_visible_scope_and_never_outcome(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        calculated = provider.calculate(_request())
        self.assertEqual(calculated.provider_id, "mingli-master.physiognomy.v1")
        extended = provider.extend(calculated, ("state", "source_comparison"), {"kind": "instant", "start": None, "end": None})
        self.assertEqual(extended.fact_extension.status, "complete")
        rendered = json.dumps(extended.fact_extension.facts, ensure_ascii=False).lower()
        for forbidden in ("wealth", "health", "personality", "lifespan", "outcome_verdict"):
            self.assertNotIn(forbidden, rendered)

    def test_provider_maps_missing_visible_targets_to_state_only(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        calculated = provider.calculate(
            _request(
                chart_data={"physiognomy_spec": _spec(observations=[])}
            )
        )
        combined = provider.extend(
            calculated,
            ("state", "source_comparison"),
            {"kind": "instant", "start": None, "end": None},
        )
        state_only = provider.extend(
            calculated,
            ("state",),
            {"kind": "instant", "start": None, "end": None},
        )
        sources_only = provider.extend(
            calculated,
            ("source_comparison",),
            {"kind": "instant", "start": None, "end": None},
        )

        self.assertEqual(combined.fact_extension.status, "partial")
        self.assertEqual(
            combined.fact_extension.unsupported_dimensions, ("state",)
        )
        self.assertEqual(state_only.fact_extension.status, "unsupported")
        self.assertEqual(sources_only.fact_extension.status, "complete")

    def test_adapter_validator_accepts_only_exact_provider_fact_layer(self) -> None:
        facts = physiognomy.build_fact_layer(_spec())
        self.assertTrue(adapter_validate.validate_payload("physiognomy", facts)["ok"])
        tampered = copy.deepcopy(facts)
        tampered["observation_provenance"]["provider_performed_vision"] = True
        self.assertFalse(adapter_validate.validate_payload("physiognomy", tampered)["ok"])
        for forged_validation in (
            None,
            {"ok": False, "system": "bazi", "validator": "evil"},
            "trusted",
        ):
            forged = copy.deepcopy(facts)
            forged["validation"] = forged_validation
            self.assertFalse(
                adapter_validate.validate_payload("physiognomy", forged)["ok"]
            )
        missing = copy.deepcopy(facts)
        missing.pop("validation")
        self.assertFalse(adapter_validate.validate_payload("physiognomy", missing)["ok"])


class PhysiognomyEvidenceAndPrivacyTests(unittest.TestCase):
    def test_public_index_exposes_only_quality_accepted_observation_fact_keys(self) -> None:
        accepted = physiognomy.build_fact_layer(_spec())
        self.assertEqual(
            accepted["output"]["accepted_observation_fact_keys"],
            ["visible_morphology|forehead"],
        )
        self.assertEqual(
            physiognomy.indexed_fact_payload(accepted)["output"][
                "accepted_observation_fact_keys"
            ],
            ["visible_morphology|forehead"],
        )

        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        low_light = next(
            row
            for row in fixture["boundary_cases"]
            if row["case_id"] == "low-light-required-target"
        )
        rejected = physiognomy.build_fact_layer(low_light["input"])
        self.assertEqual(rejected["output"]["accepted_observation_fact_keys"], [])

    def test_terminology_scope_bindings_use_independent_visible_fact_keys(self) -> None:
        bindings = yaml.safe_load(
            (ROOT / "references/matrices/evidence-scope-bindings-v1.yaml").read_text(
                encoding="utf-8"
            )
        )["bindings"]
        for rule_id in (
            "physiognomy/liuzhuang-xiangfa#LZ-R01",
            "physiognomy/mayi-shenxiang#MR-02",
            "physiognomy/shenxiang-quanbian#SR-02-04",
        ):
            with self.subTest(rule=rule_id):
                predicates = bindings[rule_id]["predicates"]
                self.assertTrue(
                    any(
                        item["path_suffix"]
                        == "/output/accepted_observation_fact_keys"
                        for item in predicates
                    )
                )
                self.assertFalse(
                    any(
                        item["path_suffix"].endswith("/active_source_rule_ids")
                        for item in predicates
                    )
                )
        self.assertIn(
            {
                "path_suffix": "/output/accepted_observation_fact_keys",
                "operator": "descendant_eq",
                "value": "visible_morphology|nose",
            },
            bindings["physiognomy/mayi-shenxiang#MR-02"]["predicates"],
        )
        self.assertIn(
            {
                "path_suffix": "/output/accepted_observation_fact_keys",
                "operator": "descendant_eq",
                "value": "visible_morphology|forehead",
            },
            bindings["physiognomy/shenxiang-quanbian#SR-02-04"]["predicates"],
        )

    def test_every_physiognomy_rule_requires_provider_and_exact_rule_identity(self) -> None:
        rules = [rule for rule in production_evidence_rules() if rule.system == "physiognomy"]
        self.assertGreaterEqual(len(rules), 90)
        for rule in rules:
            predicates = [item.to_dict() for item in rule.required_fact_predicates]
            self.assertIn(
                {"path_suffix": "/fact_layer_status", "operator": "eq", "value": "observation_driven_physiognomy_facts"},
                predicates,
            )
            self.assertIn(
                {"path_suffix": "/active_source_rule_ids", "operator": "descendant_eq", "value": rule.rule_id},
                predicates,
            )

    def test_only_safe_allowlisted_rules_can_become_active(self) -> None:
        facts = physiognomy.build_fact_layer(_spec())
        active = set(facts["output"]["active_source_rule_ids"])
        self.assertTrue(active)
        self.assertTrue(active <= set(physiognomy.SAFE_SOURCE_RULE_IDS))
        unsafe = {
            "physiognomy/shenxiang-quanbian#SR-01-09",
            "physiognomy/shenxiang-quanbian#SR-05-07",
            "physiognomy/shenxiang-quanbian#SR-03-04",
            "physiognomy/mayi-shenxiang#MR-04",
        }
        self.assertFalse(active & unsafe)

    def test_exact_active_rule_matches_and_inactive_or_local_collision_does_not(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        calculation = provider.calculate(_request())
        indexed = build_fact_index(calculation, reading_id="reading-1", version=1)
        rules = {rule.rule_id: rule for rule in production_evidence_rules() if rule.system == "physiognomy"}
        active = set(calculation.facts["chart_facts"]["output"]["active_source_rule_ids"])
        independently_supported = {
            "physiognomy/liuzhuang-xiangfa#LZ-R01",
            "physiognomy/shenxiang-quanbian#SR-02-04",
        }
        self.assertTrue(independently_supported <= active)
        for rule_id in independently_supported:
            self.assertTrue(match_rule(rules[rule_id], indexed)[0], rule_id)
        for rule_id in (
            "physiognomy/liuzhuang-xiangfa#LZ-R05",
            "physiognomy/mayi-shenxiang#MR-01",
            "physiognomy/mayi-shenxiang#MR-02",
        ):
            self.assertIn(rule_id, active)
            self.assertFalse(match_rule(rules[rule_id], indexed)[0], rule_id)
        self.assertFalse(match_rule(rules["physiognomy/shenxiang-quanbian#SR-01-09"], indexed)[0])

    def test_source_plan_is_derived_only_from_active_rule_packs(self) -> None:
        facts = physiognomy.build_fact_layer(_spec())
        plan = reading_source_plan.compile_source_plan("physiognomy", {}, facts)
        active_packs = {
            rule_id.split("#", 1)[0]
            for rule_id in facts["output"]["active_source_rule_ids"]
        }
        expected_priority = [
            "physiognomy/liuzhuang-xiangfa",
            "physiognomy/shenxiang-quanbian",
            "physiognomy/mayi-shenxiang",
        ]
        self.assertEqual(
            plan["required_packs"],
            [pack for pack in expected_priority if pack in active_packs],
        )
        self.assertNotIn("physiognomy/bingjian", plan["required_packs"])
        expanded = reading_source_plan.compile_source_plan("physiognomy", {"source_packs": ["physiognomy/bingjian"]}, facts)
        self.assertEqual(expanded["required_packs"], plan["required_packs"])

    def test_source_comparison_covers_only_eligible_packs_with_registered_nonindependent_lineages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            outcome = engine.prepare_turn(
                engine.providers["physiognomy"].descriptor,
                _provider_request(_spec()),
            )
        prepared = outcome.result

        self.assertIsInstance(prepared, PreparedReading)
        active_packs = {
            str(fact.value).split("#", 1)[0]
            for fact in prepared.fact_index
            if "/active_source_rule_ids/" in fact.path
        }
        evidence_packs = {
            node.rule_id.split("#", 1)[0]
            for node in (*prepared.evidence, *prepared.counter_evidence)
        }
        self.assertEqual(
            active_packs,
            {
                "physiognomy/liuzhuang-xiangfa",
                "physiognomy/mayi-shenxiang",
                "physiognomy/shenxiang-quanbian",
            },
        )
        self.assertEqual(
            evidence_packs,
            {
                "physiognomy/liuzhuang-xiangfa",
                "physiognomy/shenxiang-quanbian",
            },
        )
        self.assertNotIn("physiognomy/mayi-shenxiang", evidence_packs)
        self.assertTrue(
            all(
                not node.lineage.startswith("unregistered:")
                for node in (*prepared.evidence, *prepared.counter_evidence)
            )
        )
        cross_pack = [
            relation
            for relation in prepared.source_relationships
            if relation.left_rule_id.split("#", 1)[0]
            != relation.right_rule_id.split("#", 1)[0]
        ]
        self.assertTrue(cross_pack)
        self.assertTrue(all(item.relation == "parallel" for item in cross_pack))

    def test_fact_index_and_source_plan_exclude_private_image_provenance(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        calculation = provider.calculate(_request())
        indexed = build_fact_index(calculation, reading_id="reading-1", version=1)
        paths = [item.path for item in indexed]
        rendered = json.dumps(
            [{"path": item.path, "value": item.value} for item in indexed],
            ensure_ascii=False,
        )
        for private in ("subject_ref", "asset_id", "capture_id", "sha256", "region_anchor", "normalized_bbox"):
            self.assertFalse(any(private in path for path in paths), private)
            self.assertNotIn(private, rendered)
        self.assertNotIn(SHA_A, rendered)

        facts = calculation.facts["chart_facts"]
        plan = reading_source_plan.compile_source_plan("physiognomy", {}, facts)
        serialized = json.dumps(plan, ensure_ascii=False)
        self.assertNotIn(SHA_A, serialized)
        self.assertNotIn("aid-77072c872df89a9e9c89483dea1e14e5", serialized)
        self.assertNotIn("cid-421b5f386a3bd17c0403216536556e80", serialized)

    def test_fact_index_and_public_answer_hide_source_layer_protocol(self) -> None:
        internal_values = (
            "primary_liuzhuang_lineage",
            "methodology_and_terminology_only",
            "liuzhuang_vs_compilation",
            "retain_separate_source_ids_without_forced_resolution",
            "mayi_web_layer_boundary",
        )
        calculation = PhysiognomyProvider(ROOT).calculate(_request())
        indexed = build_fact_index(
            calculation,
            reading_id="reading-1",
            version=1,
        )
        rendered = json.dumps(
            [{"path": item.path, "value": item.value} for item in indexed],
            ensure_ascii=False,
        )
        for value in internal_values:
            self.assertNotIn(value, rendered)

        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            outcome = engine.prepare_turn(
                engine.providers["physiognomy"].descriptor,
                _provider_request(_spec()),
            )
        self.assertIsInstance(outcome.result, PreparedReading)
        public_rendered = json.dumps(
            outcome.result.to_dict(), ensure_ascii=False
        )
        for value in internal_values:
            self.assertNotIn(value, public_rendered)

    def test_missing_target_projection_does_not_expose_opaque_target_id(self) -> None:
        calculation = PhysiognomyProvider(ROOT).calculate(
            _request(chart_data={"physiognomy_spec": _spec(observations=[])})
        )
        indexed = build_fact_index(calculation, reading_id="reading-1", version=1)
        rendered = json.dumps(
            [{"path": item.path, "value": item.value} for item in indexed],
            ensure_ascii=False,
        )

        self.assertNotIn("target_id", rendered)
        self.assertNotIn("tid-0902d05e906e853a141894141a50184e", rendered)

    def test_public_prepared_contract_hides_full_private_calculation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            outcome = engine.prepare_turn(
                engine.providers["physiognomy"].descriptor,
                _provider_request(_spec()),
            )
        prepared = outcome.result

        self.assertIsInstance(prepared, PreparedReading)
        self.assertIsNone(prepared.calculation)
        rendered = json.dumps(prepared.to_dict(), ensure_ascii=False)
        for private in (
            "asset_id",
            "aid-77072c872df89a9e9c89483dea1e14e5",
            "capture_id",
            "cid-421b5f386a3bd17c0403216536556e80",
            "region_anchor",
            "normalized_bbox",
            SHA_A,
        ):
            self.assertNotIn(private, rendered)

    def test_public_basis_excludes_protocol_ids_paths_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            outcome = engine.prepare_turn(
                engine.providers["physiognomy"].descriptor,
                _provider_request(_spec()),
            )
        prepared = outcome.result

        self.assertIsInstance(prepared, PreparedReading)
        self.assertNotRegex(prepared.basis_text, r"\b[0-9a-f]{64}\b")
        for internal in (
            "fact_digest",
            "extension_digest",
            "base_calculation_digest",
            "physiognomy/",
            "source_layer",
            "liuzhuang_vs_compilation",
            "mayi_web_layer_boundary",
        ):
            self.assertNotIn(internal, prepared.basis_text)

    def test_public_projection_retains_safe_quality_and_cross_capture_semantics(self) -> None:
        second_asset = _asset(
            "aid-8b8e7d374de785aac5c32d4b4504e94f",
            capture_id="cid-5287e79011b0517c92131c5c2220b104",
            sha256=SHA_B,
            quality=_quality(lighting="uneven"),
        )
        second = _image_observation(
            "oid-b51686f393db969715aaf7ad57246325",
            descriptor="contour_flat",
            asset_id="aid-8b8e7d374de785aac5c32d4b4504e94f",
            asset_sha256=SHA_B,
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            outcome = engine.prepare_turn(
                engine.providers["physiognomy"].descriptor,
                _provider_request(
                    _spec(
                        assets=[_asset(), second_asset],
                        observations=[_image_observation(), second],
                    )
                ),
            )

        self.assertIsInstance(outcome.result, PreparedReading)
        chart = {
            fact["ref"].rsplit("/", 1)[1]: fact["value"]
            for fact in outcome.preparation.public_facts
        }
        observations = chart["normalized_visible_observations"]
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0]["occlusion"], 0.0)
        self.assertEqual(observations[0]["quality"]["lighting"], "even")
        self.assertEqual(observations[0]["quality"]["camera_angle"], "frontal")
        self.assertEqual(observations[0]["quality"]["filtering"], "none")
        variations = chart["cross_capture_variations"]
        self.assertEqual(variations, [{
            "region": "forehead",
            "feature_kind": "visible_morphology",
            "capture_count": 2,
            "descriptor_count": 2,
            "auto_equivalent": False,
        }])
        rendered = json.dumps(
            list(outcome.preparation.public_facts), ensure_ascii=False
        )
        for private in ("aid-2a3418dbe8f2f7966219b778ec96db58", "cid-96f1451a878c4d3f847a15ba6844209f", SHA_A, SHA_B, "region_anchor", "target_id"):
            self.assertNotIn(private, rendered)
        comparison = chart["source_comparison"]
        self.assertTrue(comparison["disagreements_retained"])
        self.assertFalse(comparison["forced_resolution"])
        self.assertTrue(
            all(item["edition_caveat"] for item in comparison["sources"])
        )
        self.assertTrue(
            all(item["summary"] for item in comparison["disagreements"])
        )

    def test_privacy_gate_allows_public_projection_and_numeric_supersets(self) -> None:
        facts = physiognomy.build_fact_layer(_spec())
        safe_copy = json.dumps(
            physiognomy.public_projection(facts),
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertFalse(
            physiognomy.public_copy_contains_private_provenance(facts, safe_copy)
        )
        for public_number in ("5120", "1512", "1512px"):
            with self.subTest(public_number=public_number):
                self.assertFalse(
                    physiognomy.public_copy_contains_private_provenance(
                        facts,
                        public_number,
                    )
                )

    def test_public_projection_retains_optional_same_capture_conflict_without_ids(self) -> None:
        target_mouth = _target("tid-169e009c140e16305ddddc5154bb2518", "mouth", required=False)
        mouth_a = _image_observation(
            "oid-31f23d5b7179635631cab9b996f0f5ef",
            "tid-169e009c140e16305ddddc5154bb2518",
            "mouth",
            "mouth_closed",
        )
        mouth_b = _image_observation(
            "oid-bd2fbc44cda43e4ae03c4beaf632262a",
            "tid-169e009c140e16305ddddc5154bb2518",
            "mouth",
            "mouth_open",
        )
        request_spec = _spec(
            requested_targets=[_target(), target_mouth],
            observations=[_image_observation(), mouth_a, mouth_b],
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            outcome = engine.prepare_turn(
                engine.providers["physiognomy"].descriptor,
                _provider_request(request_spec),
            )

        self.assertIsInstance(outcome.result, PreparedReading)
        chart = {
            fact["ref"].rsplit("/", 1)[1]: fact["value"]
            for fact in outcome.preparation.public_facts
        }
        self.assertEqual(chart["observation_conflicts"], [{
            "region": "mouth",
            "feature_kind": "visible_morphology",
            "capture_scope": "same_capture",
            "observation_count": 2,
            "blocking": True,
            "resolved": False,
        }])
        rendered = json.dumps(
            list(outcome.preparation.public_facts), ensure_ascii=False
        )
        for private in ("tid-169e009c140e16305ddddc5154bb2518", "oid-31f23d5b7179635631cab9b996f0f5ef", "oid-bd2fbc44cda43e4ae03c4beaf632262a", "cid-421b5f386a3bd17c0403216536556e80"):
            self.assertNotIn(private, rendered)

    def test_security_scans_are_linear_on_unclosed_markdown_and_plain_percent_text(self) -> None:
        facts = physiognomy.build_fact_layer(_spec())
        samples = (
            ("%25" * 33_334)[:100_000],
            "[" * 20_000,
        )
        started = time.perf_counter()
        for sample in samples:
            self.assertEqual(physiognomy._raw_media_key_paths(sample), ())
            self.assertFalse(
                physiognomy.public_copy_contains_private_provenance(
                    facts,
                    sample,
                )
            )
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 1.0, elapsed)

    def test_private_fact_refs_cannot_bind_evidence(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        calculation = provider.calculate(_request())
        indexed = build_fact_index(calculation, reading_id="reading-1", version=1)
        rules = [rule for rule in production_evidence_rules() if rule.system == "physiognomy"]
        for rule in rules:
            eligible, refs, _ = match_rule(rule, indexed)
            if eligible:
                self.assertTrue(refs)
                self.assertTrue(
                    any("accepted_observation_fact_keys" in ref for ref in refs),
                    rule.rule_id,
                )
                self.assertTrue(
                    all(
                        private not in ref
                        for ref in refs
                        for private in (
                            "subject_ref",
                            "asset_id",
                            "capture_id",
                            "sha256",
                            "region_anchor",
                            "normalized_bbox",
                            "observation_provenance",
                        )
                    ),
                    rule.rule_id,
                )


class PhysiognomyTurnTests(unittest.TestCase):
    """Production-chain intake behavior on the adapter turn engine."""

    @staticmethod
    def _empty_request() -> ProviderRequest:
        return ProviderRequest(
            query="只整理这项可见观察和古籍术语边界",
            subject_refs=("sid-0bac48405950e1d63b39cde30608d995",),
            object_id="visible_observation",
            dimension_ids=("state", "source_comparison"),
            horizon={"kind": "instant", "start": None, "end": None},
            facts={"sid-0bac48405950e1d63b39cde30608d995": {}},
        )

    def test_missing_spec_intake_resumes_into_an_accepted_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["physiognomy"].descriptor
            pending = engine.prepare_turn(descriptor, self._empty_request())
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertEqual(pending.missing_fields, ("physiognomy_spec",))
            self.assertIsNotNone(pending.state_token)
            resumed = engine.prepare_turn(
                descriptor,
                _provider_request(_spec()),
                state_token=pending.state_token,
            )
            self.assertIsInstance(resumed.result, PreparedReading)
            accepted = engine.complete_turn(
                resumed.state_token,
                "本轮只描述已确认的可见观察及其术语边界。",
            )
        self.assertIsInstance(accepted, AcceptedReading)

    def test_incomplete_spec_intake_is_target_scoped_and_resumable(self) -> None:
        incomplete = _spec(observations=[])
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["physiognomy"].descriptor
            pending = engine.prepare_turn(
                descriptor, _provider_request(incomplete)
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertEqual(
                pending.missing_fields,
                ("visible_observation:tid-0902d05e906e853a141894141a50184e",),
            )
            resumed = engine.prepare_turn(
                descriptor,
                _provider_request(_spec()),
                state_token=pending.state_token,
            )
        self.assertIsInstance(resumed.result, PreparedReading)

    def test_resume_controls_cannot_change_an_unrelated_optional_target(self) -> None:
        mouth_target = _target("tid-169e009c140e16305ddddc5154bb2518", "mouth", required=False)
        mouth_closed = _image_observation(
            "oid-833c0059d4a57e8b98c4be0658f4217b",
            "tid-169e009c140e16305ddddc5154bb2518",
            "mouth",
            "mouth_closed",
        )
        mouth_open = _image_observation(
            "oid-a8bd5d520916c673914f29619fbb4ca0",
            "tid-169e009c140e16305ddddc5154bb2518",
            "mouth",
            "mouth_open",
        )
        original = _spec(
            requested_targets=[_target(), mouth_target],
            observations=[mouth_closed, mouth_open],
        )
        missing = {"visible_observation:tid-0902d05e906e853a141894141a50184e"}
        with self.assertRaisesRegex(ValueError, "pending target"):
            _merge_physiognomy_correction_resume_spec(
                original,
                {"confirmed_observation_ids": ["oid-a8bd5d520916c673914f29619fbb4ca0"]},
                missing,
            )

        second_asset = _asset(
            "aid-8b8e7d374de785aac5c32d4b4504e94f",
            capture_id="cid-5287e79011b0517c92131c5c2220b104",
            sha256=SHA_B,
        )
        mouth_other_capture = _image_observation(
            "oid-886fad068d412a22e17733496e4d0e2a",
            "tid-169e009c140e16305ddddc5154bb2518",
            "mouth",
            "mouth_open",
            asset_id="aid-8b8e7d374de785aac5c32d4b4504e94f",
            asset_sha256=SHA_B,
        )
        relation_original = _spec(
            requested_targets=[_target(), mouth_target],
            assets=[_asset(), second_asset],
            observations=[mouth_closed, mouth_other_capture],
        )
        relation = {
            "relation": "same_target_user_confirmed",
            "target_id": "tid-169e009c140e16305ddddc5154bb2518",
            "observation_ids": [
                "oid-833c0059d4a57e8b98c4be0658f4217b",
                "oid-886fad068d412a22e17733496e4d0e2a",
            ],
        }
        for merger in (
            _merge_physiognomy_resume_spec,
            _merge_physiognomy_correction_resume_spec,
        ):
            with self.subTest(merger=merger.__name__), self.assertRaisesRegex(
                ValueError,
                "pending target",
            ):
                merger(
                    relation_original,
                    {"comparison_relations": [relation]},
                    missing,
                )


if __name__ == "__main__":
    unittest.main()
