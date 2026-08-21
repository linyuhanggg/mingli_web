#!/usr/bin/env python3
"""Task 7L regressions for the observation-driven Fengshui provider."""

from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

import adapter_validate
import audit_fengshui_provider
import reading_source_plan
from reading_engine import fengshui, providers as reading_providers
from reading_engine.contracts import (
    AcceptedReading,
    NeedUserFact,
    PreparedReading,
    ReadingRequest,
)
from reading_engine.evidence_rules import match_rule, production_evidence_rules
from reading_engine.factory import build_production_engine
from reading_engine.fact_index import build_fact_index
from reading_engine.provider_protocol import ProviderRequest
from reading_engine.providers import FengshuiProvider, STRUCTURED_SYSTEMS
from reading_engine.providers import PROVIDER_CAPABILITIES, missing_required_inputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/fengshui-v51.yaml"
SOURCE_TABLE = ROOT / "references/matrices/fengshui-source-tables-v1.yaml"
MOUNTAINS = tuple("子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥壬")
TEST_ASSET_SHA256 = "a" * 64


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _quality(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "readability": "good",
        "lighting": "good",
        "scale": "known",
        "viewpoint": "top_down",
        "occlusion": 0.0,
    }
    value.update(changes)
    return value


def _direction_measurement(
    identifier: str,
    degrees: float,
    **changes: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "measurement_id": identifier,
        "facing_degrees": degrees,
        "method": "handheld_compass",
        "north_reference": "true",
        "correction_degrees": 0.0,
        "uncertainty_degrees": 0.5,
        "quality": "good",
        "source_type": "user_measurement",
        "source_ref": f"measured-{identifier}",
    }
    value.update(changes)
    return value


def _image_observation(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "observation_id": "obs-road-1",
        "subprofile": "form",
        "kind": "road",
        "source_type": "image_transcription",
        "asset_id": "site-image-1",
        "region_anchor": {
            "kind": "normalized_bbox",
            "x": 0.1,
            "y": 0.2,
            "width": 0.3,
            "height": 0.2,
        },
        "value": {"relation": "axis_toward_entrance"},
        "quality": _quality(),
        "uncertainty": 0.1,
    }
    value.update(changes)
    return value


def _text_observation(
    identifier: str,
    kind: str,
    relation: str,
) -> dict[str, object]:
    return {
        "observation_id": identifier,
        "subprofile": "form",
        "kind": kind,
        "source_type": "user_text",
        "source_ref": f"caller-observation-{identifier}",
        "value": {"relation": relation},
        "quality": _quality(
            lighting="not_applicable",
            scale="caller_described",
            viewpoint="caller_description",
        ),
        "uncertainty": 0.2,
    }


def _spec(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "mingli-fengshui-input-v1",
        "property_scope": "residential",
        "subprofiles": ["form", "liqi"],
        "requested_form_variables": ["road"],
        "liqi": {
            "selected_school": "bazhai",
            "origin_basis": "door_trigram",
            "origin_node_id": "entry",
        },
        "compass_measurements": [
            {
                "measurement_id": "compass-1",
                "facing_degrees": 180.0,
                "method": "handheld_compass",
                "north_reference": "true",
                "correction_degrees": 0.0,
                "uncertainty_degrees": 0.5,
                "quality": "good",
                "source_type": "user_measurement",
                "source_ref": "front-door-centerline",
            }
        ],
        "declared_orientation": {
            "facing_mountain": "午",
            "sitting_mountain": "子",
        },
        "building": {
            "completion_year": 2023,
            "occupation_year": 2024,
            "source_type": "user_text",
            "source_ref": "owner-record",
        },
        "assets": [
            {
                "asset_id": "site-image-1",
                "media_type": "image",
                "role": "site_photo",
                "sha256": TEST_ASSET_SHA256,
            }
        ],
        "observations": [_image_observation()],
        "layout_graph": {
            "nodes": [
                {
                    "node_id": "entry",
                    "kind": "entrance",
                    "direction_measurement": _direction_measurement(
                        "entry-direction",
                        180.0,
                    ),
                },
            ],
            "edges": [],
        },
    }
    value.update(changes)
    return value


def _intent() -> dict[str, object]:
    return {
        "subject_refs": ["residence-1"],
        "calculation_object": "spatial_observation",
        "question_dimensions": ["state", "location"],
        "horizon": {"kind": "instant", "start": None, "end": None},
        "requested_method": "fengshui",
        "requested_granularity": "directional",
        "continuity": {
            "reading_id": None,
            "same_subject": False,
            "same_event": False,
        },
        "facts_present": ["fengshui_spec"],
        "facts_corrected": [],
        "evidence_questions": ["当前实测坐向和可见形势支持哪些原典条件"],
    }


def _request(**changes: object) -> ReadingRequest:
    payload: dict[str, object] = {
        "query": "按实测坐向和现场图核对住宅",
        "action": "new",
        "system": "fengshui",
        "intent": _intent(),
        "chart_data": {"fengshui_spec": _spec()},
    }
    payload.update(changes)
    return ReadingRequest(**payload)


def _provider_request(
    spec: dict[str, object],
    *,
    query: str = "按实测坐向和现场图核对住宅",
) -> ProviderRequest:
    return ProviderRequest(
        query=query,
        subject_refs=("subject:residence-1",),
        object_id="spatial_observation",
        dimension_ids=("state",),
        horizon={"kind": "instant", "start": None, "end": None},
        facts={"subject:residence-1": {"fengshui_spec": spec}},
    )


class FengshuiCompletenessAuditTests(unittest.TestCase):
    def test_machine_readable_audit_passes_before_activation(self) -> None:
        report = audit_fengshui_provider.audit_fengshui_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertGreaterEqual(report["counts"]["complete_observation_fixtures"], 20)
        self.assertGreaterEqual(report["counts"]["partial_fixtures"], 1)
        self.assertGreaterEqual(report["counts"]["conflict_fixtures"], 1)
        self.assertGreaterEqual(report["counts"]["low_quality_fixtures"], 1)
        self.assertEqual(report["counts"]["compass_boundary_checks"], 48)
        self.assertEqual(report["counts"]["compass_boundary_mismatches"], 0)
        self.assertEqual(report["counts"]["fixture_mismatches"], 0)
        self.assertEqual(report["counts"]["observation_fact_key_mismatches"], 0)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 3)
        self.assertEqual(report["counts"]["evidence_rules_without_exact_predicates"], 0)
        self.assertEqual(report["findings"], [])

    def test_audit_rejects_source_table_and_fixture_mutation(self) -> None:
        source = SOURCE_TABLE.read_text(encoding="utf-8")
        fixture = FIXTURE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / SOURCE_TABLE.name
            fixture_path = root / FIXTURE.name
            source_path.write_text(
                source.replace("north-centered-half-open-24-mountains", "shifted-sectors", 1),
                encoding="utf-8",
            )
            fixture_path.write_text(
                fixture.replace("form_status: complete", "form_status: partial", 1),
                encoding="utf-8",
            )

            source_report = audit_fengshui_provider.audit_fengshui_provider(
                source_table_path=source_path
            )
            fixture_report = audit_fengshui_provider.audit_fengshui_provider(
                fixture_path=fixture_path
            )

        self.assertFalse(source_report["provider_ready"])
        self.assertIn("Fengshui source-table artifact hash mismatch", source_report["findings"])
        self.assertFalse(fixture_report["provider_ready"])
        self.assertIn("Fengshui fixture artifact hash mismatch", fixture_report["findings"])


class FengshuiCompassTests(unittest.TestCase):
    def test_all_twenty_four_half_open_boundaries_are_exact(self) -> None:
        for index, mountain in enumerate(MOUNTAINS):
            boundary = (7.5 + 15.0 * index) % 360.0
            before = (boundary - 0.0001) % 360.0
            with self.subTest(index=index, side="before"):
                self.assertEqual(fengshui.mountain_for_degrees(before), mountain)
            with self.subTest(index=index, side="at"):
                self.assertEqual(
                    fengshui.mountain_for_degrees(boundary),
                    MOUNTAINS[(index + 1) % 24],
                )

    def test_raw_degree_is_never_silently_wrapped(self) -> None:
        for value in (-0.0001, 360.0, 720.0, True, "180"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    fengshui.mountain_for_degrees(value)  # type: ignore[arg-type]

    def test_magnetic_correction_records_an_explicit_wrap(self) -> None:
        normalized = fengshui.normalize_compass_measurements(
            [
                {
                    "measurement_id": "wrap",
                    "facing_degrees": 359.0,
                    "method": "handheld_compass",
                    "north_reference": "magnetic",
                    "correction_degrees": 2.0,
                    "uncertainty_degrees": 0.25,
                    "quality": "good",
                    "source_type": "user_measurement",
                    "source_ref": "door-axis",
                }
            ]
        )

        row = normalized["measurements"][0]
        self.assertEqual(row["raw_degrees"], 359.0)
        self.assertEqual(row["corrected_unwrapped_degrees"], 361.0)
        self.assertEqual(row["normalized_degrees"], 1.0)
        self.assertEqual(row["wrap_count"], 1)
        self.assertEqual(normalized["facing"]["mountain"], "子")

    def test_uncertainty_crossing_a_sector_boundary_is_ambiguous(self) -> None:
        normalized = fengshui.normalize_compass_measurements(
            [
                {
                    "measurement_id": "edge",
                    "facing_degrees": 7.4,
                    "method": "handheld_compass",
                    "north_reference": "true",
                    "correction_degrees": 0.0,
                    "uncertainty_degrees": 0.2,
                    "quality": "good",
                    "source_type": "user_measurement",
                    "source_ref": "door-axis",
                }
            ]
        )

        self.assertEqual(normalized["status"], "ambiguous_boundary")
        self.assertEqual(normalized["candidate_mountains"], ["子", "癸"])
        self.assertIsNone(normalized["facing"])

    def test_all_exact_boundaries_with_zero_uncertainty_use_the_half_open_sector(self) -> None:
        for index in range(24):
            boundary = (7.5 + 15.0 * index) % 360.0
            expected = MOUNTAINS[(index + 1) % 24]
            expected_sitting = MOUNTAINS[(index + 13) % 24]
            measurement = copy.deepcopy(_spec()["compass_measurements"][0])
            measurement["facing_degrees"] = boundary
            measurement["uncertainty_degrees"] = 0.0

            with self.subTest(boundary=boundary):
                normalized = fengshui.normalize_compass_measurements([measurement])
                self.assertEqual(normalized["status"], "resolved")
                self.assertEqual(normalized["facing"]["mountain"], expected)
                facts = fengshui.build_fact_layer(
                    _spec(
                        compass_measurements=[measurement],
                        declared_orientation={
                            "facing_mountain": expected,
                            "sitting_mountain": expected_sitting,
                        },
                    )
                )
                self.assertEqual(
                    facts["output"]["compass"]["facing"]["mountain"],
                    expected,
                )

    def test_contradictory_measurements_and_declared_orientation_block_liqi(self) -> None:
        contradictory = copy.deepcopy(_spec())
        contradictory["compass_measurements"] = [
            copy.deepcopy(_spec()["compass_measurements"][0]),
            {
                **copy.deepcopy(_spec()["compass_measurements"][0]),
                "measurement_id": "compass-2",
                "facing_degrees": 90.0,
                "source_ref": "second-survey",
            },
        ]
        facts = fengshui.build_fact_layer(contradictory)

        self.assertEqual(facts["output"]["compass"]["status"], "conflict")
        self.assertEqual(facts["output"]["liqi"]["status"], "blocked")
        self.assertIn("confirmed_facing_measurement", facts["output"]["critical_missing"])

        declared = _spec(
            declared_orientation={"facing_mountain": "卯", "sitting_mountain": "酉"}
        )
        facts = fengshui.build_fact_layer(declared)
        self.assertIn("declared_orientation_conflict", {
            row["code"] for row in facts["output"]["conflicts"]
        })
        self.assertEqual(facts["output"]["liqi"]["status"], "blocked")


class FengshuiFixtureAndSchoolTests(unittest.TestCase):
    def test_at_least_twenty_complete_fixtures_reproduce_independent_expected_facts(self) -> None:
        cases = _fixture()["complete_observation_fixtures"]
        self.assertGreaterEqual(len(cases), 20)
        for case in cases:
            with self.subTest(case=case["id"]):
                spec = copy.deepcopy(case["input"]["fengshui_spec"])
                facts = fengshui.build_fact_layer(spec)
                output = facts["output"]
                expected = case["expected"]
                facing = output["compass"]["facing"]
                sitting = output["compass"]["sitting"]
                self.assertEqual(
                    facing["mountain"] if facing else None,
                    expected["facing_mountain"],
                )
                self.assertEqual(
                    sitting["mountain"] if sitting else None,
                    expected["sitting_mountain"],
                )
                bazhai = output["liqi"].get("bazhai") or {}
                self.assertEqual(bazhai.get("origin_gua"), expected["origin_gua"])
                self.assertEqual(
                    bazhai.get("origin_group"), expected["origin_group"]
                )
                self.assertEqual(output["form"]["status"], "complete")
                self.assertEqual(output["critical_missing"], [])
                self.assertEqual(
                    output["active_source_rule_ids"],
                    expected["active_source_rule_ids"],
                )

    def test_bazhai_younian_map_reproduces_all_eight_source_mnemonics(self) -> None:
        for case in _fixture()["bazhai_source_examples"]:
            with self.subTest(house_gua=case["house_gua"]):
                self.assertEqual(
                    fengshui.bazhai_star_map(case["house_gua"]),
                    case["expected_star_map"],
                )

    def test_bazhai_uses_the_explicit_measured_door_not_the_sitting_trigram(self) -> None:
        output = fengshui.build_fact_layer(_spec())["output"]
        bazhai = output["liqi"]["bazhai"]

        self.assertEqual(output["compass"]["sitting"]["trigram"], "坎")
        self.assertEqual(bazhai["basis"]["kind"], "door_trigram")
        self.assertEqual(bazhai["basis"]["node_id"], "entry")
        self.assertEqual(bazhai["origin_gua"], "离")
        self.assertEqual(
            bazhai["direction_star_map"],
            fengshui.bazhai_star_map("离"),
        )

    def test_period_metadata_never_silently_activates_xuankong(self) -> None:
        for completion_year in (2023, 2024):
            with self.subTest(completion_year=completion_year):
                spec = _spec(
                    building={
                        "completion_year": completion_year,
                        "occupation_year": completion_year,
                        "supplied_period": 9,
                        "source_type": "user_text",
                        "source_ref": "owner-record",
                    }
                )
                output = fengshui.build_fact_layer(spec)["output"]
                self.assertEqual(output["liqi"]["selected_school"], "bazhai")
                self.assertNotIn("xuankong", output["liqi"])
                self.assertNotIn("flying_stars", output["liqi"])
                self.assertEqual(
                    output["building_chronology"]["supplied_period"], 9
                )
                self.assertEqual(
                    output["building_chronology"]["period_use"],
                    "retained_not_calculated_for_bazhai",
                )

    def test_unsupported_school_fails_closed_instead_of_falling_back(self) -> None:
        for school in ("xuankong", "sanhe", "mixed", ""):
            with self.subTest(school=school):
                with self.assertRaisesRegex(ValueError, "unsupported Fengshui school"):
                    fengshui.build_fact_layer(
                        _spec(liqi={"selected_school": school})
                    )

    def test_separating_wall_door_starts_a_new_declared_layout_node(self) -> None:
        layout_observation = _text_observation(
            "layout-1",
            "layout",
            "observed_layout",
        )
        output = fengshui.build_fact_layer(
            _spec(
                requested_form_variables=["layout"],
                assets=[],
                observations=[layout_observation],
                layout_graph={
                    "nodes": [
                        {
                            "node_id": "entry",
                            "kind": "entrance",
                            "direction_measurement": _direction_measurement(
                                "entry-direction",
                                180.0,
                            ),
                        },
                        {
                            "node_id": "hall",
                            "kind": "room",
                            "observation_id": "layout-1",
                        },
                        {
                            "node_id": "inner-door",
                            "kind": "door",
                            "direction_measurement": _direction_measurement(
                                "inner-door-direction",
                                90.0,
                            ),
                        },
                        {
                            "node_id": "bedroom",
                            "kind": "room",
                            "observation_id": "layout-1",
                        },
                    ],
                    "edges": [
                        {
                            "from": "entry",
                            "to": "hall",
                            "boundary": "open",
                            "observation_id": "layout-1",
                        },
                        {
                            "from": "hall",
                            "to": "bedroom",
                            "boundary": "separating_wall_with_door",
                            "door_id": "inner-door",
                            "observation_id": "layout-1",
                        },
                    ],
                },
            )
        )["output"]

        self.assertEqual(
            output["liqi"]["bazhai"]["layout_resets"],
            [
                {
                    "door_id": "inner-door",
                    "from": "hall",
                    "to": "bedroom",
                    "start_mountain": "卯",
                    "source_rule_id": "fengshui/yangzhai-shishu#YZS-R006",
                }
            ],
        )

    def test_layout_graph_cannot_bypass_observation_or_measurement_provenance(self) -> None:
        bare_direction = _spec(
            layout_graph={
                "nodes": [
                    {
                        "node_id": "entry",
                        "kind": "entrance",
                        "direction_degrees": 180.0,
                    }
                ],
                "edges": [],
            }
        )
        with self.assertRaisesRegex(ValueError, "direction_measurement"):
            fengshui.build_fact_layer(bare_direction)

        unbound_edge = _spec(
            requested_form_variables=["layout"],
            assets=[],
            observations=[
                _text_observation("layout-1", "layout", "observed_layout")
            ],
            layout_graph={
                "nodes": [
                    {
                        "node_id": "entry",
                        "kind": "entrance",
                        "direction_measurement": _direction_measurement(
                            "entry-direction",
                            180.0,
                        ),
                    },
                    {
                        "node_id": "hall",
                        "kind": "room",
                        "observation_id": "layout-1",
                    },
                ],
                "edges": [
                    {"from": "entry", "to": "hall", "boundary": "open"}
                ],
            }
        )
        with self.assertRaisesRegex(ValueError, "edge observation_id"):
            fengshui.build_fact_layer(unbound_edge)

    def test_layout_provenance_cannot_reuse_unrelated_observation_kinds(self) -> None:
        direction_only_room = _spec(
            layout_graph={
                "nodes": [
                    {
                        "node_id": "entry",
                        "kind": "entrance",
                        "direction_measurement": _direction_measurement(
                            "entry-direction",
                            180.0,
                        ),
                    },
                    {
                        "node_id": "bedroom",
                        "kind": "room",
                        "direction_measurement": _direction_measurement(
                            "bedroom-direction",
                            90.0,
                        ),
                    },
                ],
                "edges": [],
            },
        )
        with self.assertRaisesRegex(ValueError, "room.*layout observation"):
            fengshui.build_fact_layer(direction_only_room)

        road_as_room = _spec(
            layout_graph={
                "nodes": [
                    {
                        "node_id": "entry",
                        "kind": "entrance",
                        "direction_measurement": _direction_measurement(
                            "entry-direction",
                            180.0,
                        ),
                    },
                    {
                        "node_id": "bedroom",
                        "kind": "room",
                        "observation_id": "obs-road-1",
                    },
                ],
                "edges": [],
            },
        )
        with self.assertRaisesRegex(ValueError, "room.*layout observation"):
            fengshui.build_fact_layer(road_as_room)

        layout_observation = _text_observation(
            "layout-1",
            "layout",
            "observed_layout",
        )
        road_as_partition = _spec(
            requested_form_variables=["road", "layout"],
            observations=[_image_observation(), layout_observation],
            layout_graph={
                "nodes": [
                    {
                        "node_id": "entry",
                        "kind": "entrance",
                        "direction_measurement": _direction_measurement(
                            "entry-direction",
                            180.0,
                        ),
                    },
                    {
                        "node_id": "hall",
                        "kind": "room",
                        "observation_id": "layout-1",
                    },
                    {
                        "node_id": "door",
                        "kind": "door",
                        "direction_measurement": _direction_measurement(
                            "door-direction",
                            90.0,
                        ),
                    },
                    {
                        "node_id": "bedroom",
                        "kind": "room",
                        "observation_id": "layout-1",
                    },
                ],
                "edges": [
                    {
                        "from": "hall",
                        "to": "bedroom",
                        "boundary": "separating_wall_with_door",
                        "door_id": "door",
                        "observation_id": "obs-road-1",
                    }
                ],
            },
        )
        with self.assertRaisesRegex(ValueError, "partition.*layout observation"):
            fengshui.build_fact_layer(road_as_partition)

    def test_form_only_partition_does_not_require_a_door_direction(self) -> None:
        layout_observation = _text_observation(
            "layout-1",
            "layout",
            "observed_layout",
        )
        output = fengshui.build_fact_layer(
            _spec(
                subprofiles=["form"],
                requested_form_variables=["layout"],
                liqi={},
                compass_measurements=[],
                declared_orientation={},
                assets=[],
                observations=[layout_observation],
                layout_graph={
                    "nodes": [
                        {
                            "node_id": "hall",
                            "kind": "room",
                            "observation_id": "layout-1",
                        },
                        {
                            "node_id": "door",
                            "kind": "door",
                            "observation_id": "layout-1",
                        },
                        {
                            "node_id": "bedroom",
                            "kind": "room",
                            "observation_id": "layout-1",
                        },
                    ],
                    "edges": [
                        {
                            "from": "hall",
                            "to": "bedroom",
                            "boundary": "separating_wall_with_door",
                            "door_id": "door",
                            "observation_id": "layout-1",
                        }
                    ],
                },
            )
        )["output"]

        self.assertEqual(output["form"]["status"], "complete")
        self.assertEqual(output["liqi"]["status"], "not_requested")
        self.assertEqual(output["critical_missing"], [])
        self.assertNotIn("bazhai", output["liqi"])


class FengshuiObservationTests(unittest.TestCase):
    def test_accepted_observation_fact_keys_are_row_scoped_and_quality_gated(self) -> None:
        accepted = _text_observation("accepted-water", "water", "observed_water")
        uncertain = _text_observation(
            "uncertain-boundary",
            "water",
            "water_boundary_and_wind_shelter_observed",
        )
        uncertain["quality"] = _quality(
            readability="low",
            lighting="not_applicable",
            scale="caller_described",
            viewpoint="caller_description",
        )
        facts = fengshui.build_fact_layer(
            _spec(
                property_scope="site_general",
                subprofiles=["form"],
                requested_form_variables=["water"],
                liqi={},
                compass_measurements=[],
                declared_orientation={},
                assets=[],
                observations=[accepted, uncertain],
                layout_graph={"nodes": [], "edges": []},
            )
        )

        self.assertEqual(
            facts["output"]["form"]["accepted_observation_fact_keys"],
            ["water|observed_water"],
        )

    def test_yilong_fixture_requires_both_hall_and_water_shelter_facts(self) -> None:
        case = next(
            row
            for row in _fixture()["complete_observation_fixtures"]
            if row["id"] == "FS-O21"
        )
        facts = fengshui.build_fact_layer(case["input"]["fengshui_spec"])

        self.assertEqual(
            set(facts["output"]["form"]["accepted_observation_fact_keys"]),
            {
                "terrain|sheltered_open_hall",
                "water|water_boundary_and_wind_shelter_observed",
            },
        )
        self.assertIn(
            "fengshui/yilong-jing#R-05",
            facts["output"]["active_source_rule_ids"],
        )

    def test_image_observation_requires_asset_region_quality_and_uncertainty(self) -> None:
        facts = fengshui.build_fact_layer(_spec())
        observation = facts["output"]["form"]["observations"][0]

        self.assertEqual(observation["source_type"], "image_transcription")
        self.assertEqual(observation["asset_id"], "site-image-1")
        self.assertEqual(observation["region_anchor"]["kind"], "normalized_bbox")
        self.assertEqual(observation["status"], "accepted_observation_not_verdict")
        self.assertTrue(observation["source_rule_ids"])
        self.assertEqual(observation["asset_sha256"], TEST_ASSET_SHA256)
        self.assertEqual(
            facts["output"]["observation_provenance"]["asset_sha256"],
            {"site-image-1": TEST_ASSET_SHA256},
        )

        mutations = {
            "missing_asset": lambda row: row.pop("asset_id"),
            "missing_anchor": lambda row: row.pop("region_anchor"),
            "missing_quality": lambda row: row.pop("quality"),
            "missing_uncertainty": lambda row: row.pop("uncertainty"),
        }
        for name, mutate in mutations.items():
            spec = copy.deepcopy(_spec())
            mutate(spec["observations"][0])
            with self.subTest(mutation=name):
                with self.assertRaises(ValueError):
                    fengshui.build_fact_layer(spec)

        missing_digest = copy.deepcopy(_spec())
        missing_digest["assets"][0].pop("sha256")
        with self.assertRaisesRegex(ValueError, "sha256"):
            fengshui.build_fact_layer(missing_digest)

    def test_low_quality_observation_is_retained_but_cannot_activate_a_claim(self) -> None:
        low = _image_observation(
            quality=_quality(readability="low", lighting="low", occlusion=0.7),
            uncertainty=0.8,
        )
        facts = fengshui.build_fact_layer(_spec(observations=[low]))
        form = facts["output"]["form"]

        self.assertEqual(form["observations"][0]["status"], "uncertain_observation")
        self.assertEqual(form["observations"][0]["source_rule_ids"], [])
        self.assertEqual(form["status"], "partial")
        self.assertIn("obs-road-1", form["uncertain_observation_ids"])

    def test_quality_enums_and_source_sensitive_precision_fail_closed(self) -> None:
        for field, value in (
            ("readability", "nonsense"),
            ("lighting", "pitch_black"),
            ("scale", "nonsense"),
            ("viewpoint", "nonsense"),
        ):
            with self.subTest(field=field):
                observation = _image_observation(
                    quality=_quality(**{field: value}),
                )
                with self.assertRaisesRegex(ValueError, f"quality.{field}"):
                    fengshui.build_fact_layer(_spec(observations=[observation]))

        for field, value in (
            ("lighting", "low"),
            ("scale", "unknown"),
            ("viewpoint", "oblique"),
        ):
            with self.subTest(field=field, value=value):
                observation = _image_observation(
                    quality=_quality(**{field: value}),
                )
                output = fengshui.build_fact_layer(
                    _spec(observations=[observation])
                )["output"]
                normalized = output["form"]["observations"][0]
                self.assertEqual(normalized["status"], "uncertain_observation")
                self.assertEqual(normalized["source_rule_ids"], [])
                self.assertIn("form_observation:road", output["critical_missing"])

        invalid_image_sentinels = _image_observation(
            quality=_quality(
                lighting="not_applicable",
                scale="caller_described",
                viewpoint="caller_description",
            )
        )
        with self.assertRaisesRegex(ValueError, "image_transcription quality"):
            fengshui.build_fact_layer(
                _spec(observations=[invalid_image_sentinels])
            )

    def test_incomplete_floorplan_is_partial_against_declared_variables(self) -> None:
        facts = fengshui.build_fact_layer(
            _spec(
                requested_form_variables=["road", "entrance", "layout"],
                observations=[_image_observation()],
            )
        )
        form = facts["output"]["form"]

        self.assertEqual(form["status"], "partial")
        self.assertEqual(form["requested_variables"], ["road", "entrance", "layout"])
        self.assertEqual(form["complete_variables"], ["road"])
        self.assertEqual(form["missing_variables"], ["entrance", "layout"])
        self.assertTrue(
            {"form_observation:entrance", "form_observation:layout"}
            <= set(facts["output"]["critical_missing"])
        )

    def test_building_provenance_rejects_llm_authority(self) -> None:
        building = copy.deepcopy(_spec()["building"])
        building["source_type"] = "llm"
        with self.assertRaisesRegex(ValueError, "building.source_type"):
            fengshui.build_fact_layer(_spec(building=building))

    def test_vision_or_llm_tool_claims_are_rejected_as_false_provenance(self) -> None:
        for source_tool in ("vision_ocr", "vision_only", "llm"):
            observation = _image_observation(source_tool=source_tool)
            with self.subTest(source_tool=source_tool):
                with self.assertRaisesRegex(ValueError, "source_tool"):
                    fengshui.build_fact_layer(_spec(observations=[observation]))

    def test_unknown_kind_and_unselected_form_cannot_be_silently_ignored(self) -> None:
        with self.assertRaisesRegex(ValueError, "observation kind"):
            fengshui.build_fact_layer(
                _spec(observations=[_image_observation(kind="invented_feature")])
            )
        with self.assertRaisesRegex(ValueError, "form subprofile"):
            fengshui.build_fact_layer(
                _spec(subprofiles=["liqi"], observations=[_image_observation()])
            )

    def test_missing_form_observation_remains_an_explicit_gap(self) -> None:
        facts = fengshui.build_fact_layer(
            _spec(
                subprofiles=["form"],
                liqi={},
                compass_measurements=[],
                observations=[],
                layout_graph={"nodes": [], "edges": []},
            )
        )
        output = facts["output"]

        self.assertEqual(output["form"]["status"], "missing_observation")
        self.assertEqual(output["form"]["claims"], [])
        self.assertIn("form_observation:road", output["critical_missing"])
        self.assertEqual(output["active_source_rule_ids"], [])


class FengshuiFactAndActivationTests(unittest.TestCase):
    def test_critical_gap_codes_map_to_exact_unavailable_dimensions(self) -> None:
        cases = {
            "confirmed_facing_measurement": {"direction", "location"},
            "bazhai_origin_door": {"direction", "location"},
            "bazhai_origin_door:entry": {"direction", "location"},
            "door_direction_measurement:entry": {"direction", "location"},
            "unknown_future_gap": {
                "current_state",
                "direction",
                "location",
                "state",
            },
        }
        for code, expected in cases.items():
            with self.subTest(code=code):
                self.assertEqual(
                    reading_providers._fengshui_incomplete_dimensions(
                        {"critical_missing": [code]}
                    ),
                    expected,
                )

    def test_fact_digest_is_deterministic_and_tamper_evident(self) -> None:
        first = fengshui.build_fact_layer(_spec())
        second = fengshui.build_fact_layer(copy.deepcopy(_spec()))
        self.assertEqual(first, second)
        self.assertEqual(first["fact_digest"], second["fact_digest"])
        self.assertTrue(fengshui.validate_fact_layer(first)["ok"])

        tampered = copy.deepcopy(first)
        tampered["output"]["compass"]["facing"]["mountain"] = "卯"
        self.assertFalse(fengshui.validate_fact_layer(tampered)["ok"])
        self.assertIn(
            "fengshui_fact_digest_mismatch",
            fengshui.validate_fact_layer(tampered)["codes"],
        )

    def test_fact_digest_is_stable_across_python_hash_seeds(self) -> None:
        program = """
import yaml
from pathlib import Path
from reading_engine import fengshui
root = Path.cwd()
fixture = yaml.safe_load((root / 'references/fixtures/fengshui-v51.yaml').read_text())
print(fengshui.build_fact_layer(fixture['hashseed_spec'])['fact_digest'])
"""
        digests = []
        for seed in ("1", "17", "999"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            result = subprocess.run(
                [sys.executable, "-c", program],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            digests.append(result.stdout.strip())
        self.assertEqual(len(set(digests)), 1)

    def test_capability_and_factory_activate_observation_driven_provider(self) -> None:
        capability = PROVIDER_CAPABILITIES["fengshui"]
        self.assertEqual(capability.mode, "observation_driven_ready")
        self.assertEqual(capability.objects, ("spatial_observation",))
        self.assertEqual(capability.required_inputs, ("fengshui_spec",))
        self.assertNotIn("fengshui", STRUCTURED_SYSTEMS)

        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
        self.assertIsInstance(engine.providers["fengshui"], FengshuiProvider)

    def test_missing_inputs_are_conditional_on_selected_subprofile(self) -> None:
        empty = _request(chart_data={})
        form_only = _request(
            chart_data={
                "fengshui_spec": _spec(
                    subprofiles=["form"],
                    liqi={},
                    compass_measurements=[],
                )
            }
        )
        liqi_without_compass = _request(
            chart_data={
                "fengshui_spec": _spec(compass_measurements=[])
            }
        )
        form_without_observation = _request(
            chart_data={
                "fengshui_spec": _spec(
                    subprofiles=["form"],
                    liqi={},
                    compass_measurements=[],
                    observations=[],
                    assets=[],
                    layout_graph={"nodes": [], "edges": []},
                )
            }
        )
        conflicting = copy.deepcopy(_spec())
        conflicting["compass_measurements"].append(
            _direction_measurement("compass-2", 90.0)
        )

        self.assertEqual(missing_required_inputs("fengshui", empty), ("fengshui_spec",))
        self.assertEqual(missing_required_inputs("fengshui", form_only), ())
        self.assertEqual(
            missing_required_inputs("fengshui", liqi_without_compass),
            ("confirmed_facing_measurement",),
        )
        self.assertEqual(
            missing_required_inputs("fengshui", form_without_observation),
            ("form_observation:road",),
        )
        self.assertIn(
            "confirmed_facing_measurement",
            missing_required_inputs(
                "fengshui",
                _request(chart_data={"fengshui_spec": conflicting}),
            ),
        )

    def test_provider_calculates_and_extends_only_observed_scope(self) -> None:
        provider = FengshuiProvider(ROOT)
        calculated = provider.calculate(_request())

        self.assertEqual(calculated.provider_id, "mingli-master.fengshui.v1")
        self.assertEqual(
            calculated.facts["chart_facts"]["fact_layer_status"],
            "observation_driven_fengshui_facts",
        )
        self.assertNotIn("validated_user_provided_chart", calculated.diagnostics)
        extended = provider.extend(
            calculated,
            ("state", "location"),
            {"kind": "instant", "start": None, "end": None},
        )
        self.assertEqual(extended.fact_extension.status, "complete")
        self.assertEqual(
            extended.fact_extension.facts["status"],
            "observed_spatial_scope_not_outcome_verdict",
        )
        self.assertNotIn("prediction", extended.fact_extension.facts)

    def test_target_date_nonce_cannot_create_a_fengshui_extension(self) -> None:
        provider = FengshuiProvider(ROOT)
        calculated = provider.calculate(_request())

        extended = provider.extend(
            calculated,
            ("state", "location"),
            {"kind": "instant", "target_date": "2026-07-24"},
        )

        self.assertEqual(extended.fact_extension.status, "unsupported")
        self.assertEqual(extended.fact_extension.facts, {})

    def test_provider_never_marks_a_critical_gap_complete(self) -> None:
        provider = FengshuiProvider(ROOT)
        spec = _spec(
            subprofiles=["form"],
            liqi={},
            compass_measurements=[],
            observations=[],
            assets=[],
            layout_graph={"nodes": [], "edges": []},
        )
        calculated = provider.calculate(
            _request(chart_data={"fengshui_spec": spec})
        )
        extended = provider.extend(
            calculated,
            ("state", "location"),
            {"kind": "instant", "start": None, "end": None},
        )

        self.assertEqual(extended.fact_extension.status, "unsupported")
        self.assertEqual(
            extended.fact_extension.unsupported_dimensions,
            ("state", "location"),
        )
        self.assertIn(
            "form_observation:road",
            calculated.facts["chart_facts"]["output"]["critical_missing"],
        )
        state_only = provider.extend(
            calculated,
            ("state",),
            {"kind": "instant", "start": None, "end": None},
        )
        location_only = provider.extend(
            calculated,
            ("location",),
            {"kind": "instant", "start": None, "end": None},
        )
        self.assertEqual(state_only.fact_extension.status, "unsupported")
        self.assertEqual(
            state_only.fact_extension.unsupported_dimensions, ("state",)
        )
        self.assertEqual(location_only.fact_extension.status, "unsupported")

    def test_refine_reuses_observations_but_a_correction_recalculates(self) -> None:
        provider = FengshuiProvider(ROOT)
        first = provider.calculate(_request())
        refined = provider.refine(
            _request(query="只追问门前道路", action="continue"),
            first,
        )

        self.assertEqual(refined.facts["fact_digest"], first.facts["fact_digest"])
        self.assertNotEqual(refined.result_hash, first.result_hash)
        self.assertIn("fengshui_observations_reused_without_invention", refined.diagnostics)

        corrected = provider.calculate(
            _request(
                action="correct",
                chart_data={"fengshui_spec": _spec(observations=[_image_observation(value={"relation": "parallel_to_entrance"})])},
            )
        )
        self.assertNotEqual(corrected.facts["fact_digest"], first.facts["fact_digest"])

    def test_adapter_validator_accepts_provider_payload_and_rejects_tampering(self) -> None:
        facts = fengshui.build_fact_layer(_spec())
        self.assertTrue(adapter_validate.validate_payload("fengshui", facts)["ok"])

        tampered = copy.deepcopy(facts)
        tampered["output"]["active_source_rule_ids"].append("R-01")
        report = adapter_validate.validate_payload("fengshui", tampered)
        self.assertFalse(report["ok"])
        self.assertIn("fengshui_unqualified_source_rule_id", report["codes"])


class FengshuiEvidenceAndTurnTests(unittest.TestCase):
    def test_observation_scope_bindings_use_independent_accepted_fact_keys(self) -> None:
        bindings = yaml.safe_load(
            (ROOT / "references/matrices/evidence-scope-bindings-v1.yaml").read_text(
                encoding="utf-8"
            )
        )["bindings"]
        expected = {
            "fengshui/yangzhai-shishu#YZS-R003": [
                "road|axis_toward_entrance"
            ],
            "fengshui/zangshu#R-02": [
                "water|water_boundary_and_wind_shelter_observed"
            ],
            "fengshui/xuexin-fu#XXF-R01": [
                "water|water_mouth_and_hall_observed"
            ],
            "fengshui/hanlong-jing#R-01": [
                "terrain|highland_plainland_classification"
            ],
            "fengshui/yilong-jing#R-05": [
                "terrain|sheltered_open_hall",
                "water|water_boundary_and_wind_shelter_observed",
            ],
        }
        for rule_id, values in expected.items():
            with self.subTest(rule=rule_id):
                predicates = bindings[rule_id]["predicates"]
                for value in values:
                    self.assertIn(
                        {
                            "path_suffix": "/output/form/accepted_observation_fact_keys",
                            "operator": "descendant_eq",
                            "value": value,
                        },
                        predicates,
                    )
                self.assertFalse(
                    any(
                        item["path_suffix"].endswith("/active_source_rule_ids")
                        for item in predicates
                    )
                )

    def test_every_fengshui_rule_requires_provider_and_exact_pack_rule_identity(self) -> None:
        rules = [rule for rule in production_evidence_rules() if rule.system == "fengshui"]
        self.assertGreaterEqual(len(rules), 179)
        for rule in rules:
            with self.subTest(rule=rule.rule_id):
                predicates = [item.to_dict() for item in rule.required_fact_predicates]
                self.assertIn(
                    {
                        "path_suffix": "/fact_layer_status",
                        "operator": "eq",
                        "value": "observation_driven_fengshui_facts",
                    },
                    predicates,
                )
                self.assertIn(
                    {
                        "path_suffix": "/active_source_rule_ids",
                        "operator": "descendant_eq",
                        "value": rule.rule_id,
                    },
                    predicates,
                )

    def test_only_exact_active_rule_matches_and_local_id_collision_does_not(self) -> None:
        provider = FengshuiProvider(ROOT)
        calculated = provider.calculate(_request())
        facts = build_fact_index(calculated, reading_id="reading-1", version=1)
        active = set(
            calculated.facts["chart_facts"]["output"]["active_source_rule_ids"]
        )
        rules = {
            rule.rule_id: rule
            for rule in production_evidence_rules()
            if rule.system == "fengshui"
        }
        self.assertIn("fengshui/yangzhai-shishu#YZS-R003", active)
        self.assertTrue(match_rule(rules["fengshui/yangzhai-shishu#YZS-R003"], facts)[0])
        self.assertFalse(match_rule(rules["fengshui/yangzhai-sanyao#YZS-R003"], facts)[0])

    def test_source_plan_selects_only_active_subprofile_and_school_packs(self) -> None:
        form = fengshui.build_fact_layer(
            _spec(
                subprofiles=["form"],
                liqi={},
                compass_measurements=[],
                layout_graph={"nodes": [], "edges": []},
            )
        )
        bazhai = fengshui.build_fact_layer(
            _spec(
                subprofiles=["liqi"],
                requested_form_variables=[],
                observations=[],
                assets=[],
            )
        )

        form_plan = reading_source_plan.compile_source_plan("fengshui", {}, form)
        bazhai_plan = reading_source_plan.compile_source_plan("fengshui", {}, bazhai)

        self.assertEqual(
            form_plan["required_packs"],
            ["fengshui/yangzhai-shishu"],
        )
        self.assertEqual(
            bazhai_plan["required_packs"],
            [
                "fengshui/huangdi-zhaijing",
                "fengshui/yangzhai-sanyao",
                "fengshui/yangzhai-shishu",
            ],
        )
        for facts, plan in ((form, form_plan), (bazhai, bazhai_plan)):
            active_packs = {
                rule_id.split("#", 1)[0]
                for rule_id in facts["output"]["active_source_rule_ids"]
            }
            self.assertTrue(active_packs <= set(plan["required_packs"]))
        self.assertFalse(
            {
                "fengshui/dili-bianzheng",
                "fengshui/qingnang-aoyu",
                "fengshui/shenshi-xuankong-xue",
            }.intersection(bazhai_plan["required_packs"])
        )

    def test_explicit_form_observations_bind_classical_form_sources_without_a_verdict(self) -> None:
        observations = [
            _text_observation(
                "terrain-plain",
                "terrain",
                "highland_plainland_classification",
            ),
            _text_observation(
                "terrain-hall",
                "terrain",
                "sheltered_open_hall",
            ),
            _text_observation(
                "water-shelter",
                "water",
                "water_boundary_and_wind_shelter_observed",
            ),
            _text_observation(
                "water-pattern",
                "water",
                "interlocking_water_pattern",
            ),
        ]
        facts = fengshui.build_fact_layer(
            _spec(
                property_scope="site_general",
                subprofiles=["form"],
                requested_form_variables=["terrain", "water"],
                liqi={},
                compass_measurements=[],
                declared_orientation={},
                assets=[],
                observations=observations,
                layout_graph={"nodes": [], "edges": []},
            )
        )
        active = set(facts["output"]["active_source_rule_ids"])
        self.assertTrue(
            {
                "fengshui/zangshu#R-02",
                "fengshui/hanlong-jing#R-01",
                "fengshui/yilong-jing#R-05",
                "fengshui/xuexin-fu#XXF-R01",
                "fengshui/xuexin-fu#XXF-R04",
            }
            <= active
        )
        self.assertEqual(facts["output"]["form"]["claims"], [])

        plan = reading_source_plan.compile_source_plan("fengshui", {}, facts)
        self.assertTrue(
            {
                "fengshui/zangshu",
                "fengshui/hanlong-jing",
                "fengshui/yilong-jing",
                "fengshui/xuexin-fu",
            }
            <= set(plan["required_packs"])
        )

    def test_property_scope_prevents_school_and_source_cross_layer_leakage(self) -> None:
        for property_scope in ("site_general", "burial_cultural_study"):
            with self.subTest(property_scope=property_scope):
                with self.assertRaisesRegex(ValueError, "property_scope"):
                    fengshui.build_fact_layer(
                        _spec(property_scope=property_scope)
                    )

        residential = fengshui.build_fact_layer(
            _spec(
                subprofiles=["form"],
                requested_form_variables=["water"],
                liqi={},
                compass_measurements=[],
                declared_orientation={},
                assets=[],
                observations=[
                    _text_observation(
                        "residential-water",
                        "water",
                        "water_boundary_and_wind_shelter_observed",
                    )
                ],
                layout_graph={"nodes": [], "edges": []},
            )
        )
        self.assertNotIn(
            "fengshui/zangshu#R-02",
            residential["output"]["active_source_rule_ids"],
        )

        burial = fengshui.build_fact_layer(
            _spec(
                property_scope="burial_cultural_study",
                subprofiles=["form"],
                requested_form_variables=["water"],
                liqi={},
                compass_measurements=[],
                declared_orientation={},
                assets=[],
                observations=[
                    _text_observation(
                        "burial-water",
                        "water",
                        "observed_water",
                    )
                ],
                layout_graph={"nodes": [], "edges": []},
            )
        )
        self.assertFalse(
            {
                "fengshui/huangdi-zhaijing#HDZJ-R006",
                "fengshui/yangzhai-shishu#YZS-R001",
            }.intersection(burial["output"]["active_source_rule_ids"])
        )

    def test_conflicting_compass_resume_accepts_only_the_confirmed_measurement(self) -> None:
        conflicting = copy.deepcopy(_spec())
        conflicting["compass_measurements"].append(
            _direction_measurement("compass-2", 90.0)
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["fengshui"].descriptor
            pending = engine.prepare_turn(
                descriptor, _provider_request(conflicting)
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertIn("confirmed_facing_measurement", pending.missing_fields)

            confirmed = copy.deepcopy(conflicting)
            confirmed["confirmed_measurement_id"] = "compass-1"
            resumed = engine.prepare_turn(
                descriptor,
                _provider_request(confirmed, query="以第一次为准"),
                state_token=pending.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading)
            stored = engine.store.load_prepared(resumed.result.reading_id)
            stored_spec = stored.request.chart_data["fengshui_spec"]
            self.assertEqual(stored_spec["confirmed_measurement_id"], "compass-1")
            self.assertEqual(stored_spec["liqi"], _spec()["liqi"])
            self.assertEqual(len(stored_spec["compass_measurements"]), 2)

    def test_confirmed_measurement_resolves_declared_orientation_conflict_on_resume(self) -> None:
        declared_conflict = _spec(
            declared_orientation={
                "facing_mountain": "卯",
                "sitting_mountain": "酉",
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["fengshui"].descriptor
            pending = engine.prepare_turn(
                descriptor, _provider_request(declared_conflict)
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertIn(
                "confirmed_facing_measurement", pending.result.missing_facts
            )

            confirmed = copy.deepcopy(declared_conflict)
            confirmed["confirmed_measurement_id"] = "compass-1"
            resumed = engine.prepare_turn(
                descriptor,
                _provider_request(confirmed, query="确认以 compass-1 实测为准"),
                state_token=pending.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading)
            output = resumed.result.calculation.facts["chart_facts"]["output"]
            self.assertEqual(output["compass"]["selection_policy"], "explicit_confirmed_measurement")
            self.assertEqual(output["liqi"]["status"], "calculated_selected_school_facts_not_verdict")
            self.assertEqual(output["critical_missing"], [])
            self.assertEqual(
                [row["code"] for row in output["conflicts"]],
                ["declared_orientation_overridden_by_confirmed_measurement"],
            )
            self.assertFalse(output["conflicts"][0]["blocking"])

    def test_form_observation_resume_preserves_original_question_and_spec(self) -> None:
        incomplete = _spec(
            subprofiles=["form"],
            liqi={},
            compass_measurements=[],
            observations=[],
            assets=[],
            layout_graph={"nodes": [], "edges": []},
        )
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["fengshui"].descriptor
            pending = engine.prepare_turn(
                descriptor, _provider_request(incomplete)
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertIn("form_observation:road", pending.missing_fields)

            completed = _spec(
                subprofiles=["form"],
                liqi={},
                compass_measurements=[],
            )
            resumed = engine.prepare_turn(
                descriptor,
                _provider_request(completed, query=""),
                state_token=pending.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading)
            stored = engine.store.load_prepared(resumed.result.reading_id)
            self.assertEqual(stored.request.query, _provider_request(incomplete).query)
            self.assertEqual(
                stored.calculation.facts["chart_facts"]["output"]["form"]["status"],
                "complete",
            )

    def test_correct_and_recast_can_atomically_remove_old_liqi_state(self) -> None:
        for transition, action in (("correct", "correct"), ("restart", "recast")):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temporary:
                engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
                descriptor = engine.providers["fengshui"].descriptor
                first = engine.prepare_turn(descriptor, _provider_request(_spec()))
                self.assertIsInstance(first.result, PreparedReading)
                accepted = engine.complete_turn(
                    first.state_token, "现场事实已列明。\n主回答。"
                )
                self.assertIsInstance(accepted, AcceptedReading)

                form_only = _spec(
                    subprofiles=["form"],
                    liqi={},
                    compass_measurements=[],
                    declared_orientation={},
                    layout_graph={"nodes": [], "edges": []},
                )
                changed = engine.prepare_turn(
                    descriptor,
                    _provider_request(form_only, query="改为只看形势"),
                    state_token=first.state_token,
                    transition=transition,
                )

                self.assertIsInstance(changed.result, PreparedReading)
                output = changed.result.calculation.facts["chart_facts"]["output"]
                self.assertEqual(output["liqi"]["status"], "not_requested")
                if action == "correct":
                    self.assertEqual(
                        changed.result.reading_id, first.result.reading_id
                    )
                else:
                    self.assertNotEqual(
                        changed.result.reading_id, first.result.reading_id
                    )
                self.assertEqual(changed.result.action, action)
                self.assertEqual(
                    changed.result.parent_reading_id, first.result.reading_id
                )
                self.assertEqual(
                    changed.result.root_reading_id, first.result.reading_id
                )
                if action == "correct":
                    self.assertEqual(changed.result.supersedes_version, 1)
                    self.assertEqual(changed.result.version, 2)
                else:
                    self.assertIsNone(changed.result.supersedes_version)

    def test_engine_requests_genuinely_missing_or_conflicting_facts(self) -> None:
        missing_form = _spec(
            subprofiles=["form"],
            liqi={},
            compass_measurements=[],
            observations=[],
            assets=[],
            layout_graph={"nodes": [], "edges": []},
        )
        low_form = _spec(
            subprofiles=["form"],
            liqi={},
            compass_measurements=[],
            observations=[
                _image_observation(
                    quality=_quality(lighting="low"),
                )
            ],
            layout_graph={"nodes": [], "edges": []},
        )
        conflicting = copy.deepcopy(_spec())
        conflicting["compass_measurements"].append(
            _direction_measurement("compass-2", 90.0)
        )

        for name, spec, expected in (
            ("missing_form", missing_form, "form_observation:road"),
            ("low_form", low_form, "form_observation:road"),
            ("conflicting_compass", conflicting, "confirmed_facing_measurement"),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
                descriptor = engine.providers["fengshui"].descriptor
                outcome = engine.prepare_turn(descriptor, _provider_request(spec))
                self.assertIsInstance(outcome.result, NeedUserFact)
                self.assertIn(expected, outcome.result.missing_facts)

    def test_engine_uses_real_fengshui_facts_and_exact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = build_production_engine(skill_dir=ROOT, store_root=temporary)
            descriptor = engine.providers["fengshui"].descriptor
            outcome = engine.prepare_turn(descriptor, _provider_request(_spec()))

        self.assertIsInstance(outcome.result, PreparedReading)
        self.assertEqual(outcome.result.system, "fengshui")
        self.assertGreaterEqual(len(outcome.result.evidence), 1)
        self.assertTrue(
            all(node.rule_id.startswith("fengshui/") for node in outcome.result.evidence)
        )


if __name__ == "__main__":
    unittest.main()
