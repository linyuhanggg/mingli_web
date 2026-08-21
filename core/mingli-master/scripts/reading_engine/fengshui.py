"""Observation-driven Fengshui facts for measured form and selected Bazhai scope.

This module normalizes caller-transcribed observations and explicit compass
measurements.  It does not perform vision, infer unobserved site features, mix
schools, or turn classical correspondences into real-world verdicts.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Mapping

import yaml

from . import evidence_rules
from .contracts import FactRef, canonical_digest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_TABLE_PATH = ROOT / "references/matrices/fengshui-source-tables-v1.yaml"
SOURCE_TABLE_SHA256 = "7d3f56abeb302736daf1f2822d45fd2ea9dccad69dc386f6175ffac060b42e9e"
SOURCE_TABLE_SCHEMA = "mingli-fengshui-source-tables-v1"
INPUT_SCHEMA_VERSION = "mingli-fengshui-input-v1"
FACT_SCHEMA_VERSION = "mingli-fengshui-facts-v1"
ADAPTER_VERSION = "1.0.0"
FACT_LAYER_STATUS = "observation_driven_fengshui_facts"
FACT_LAYER_SCOPE = "selected_form_and_bazhai_observations"
TABLE_PROFILE = "north-centered-half-open-24-mountains"
SOURCE_DEPENDENCIES = (
    "fengshui.observation.compass-layout-contract",
    "fengshui.form.observable-site-facts",
    "fengshui.liqi.bazhai-school",
)
MOUNTAINS = tuple("子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥壬")
SUPPORTED_SUBPROFILES = frozenset({"form", "liqi"})
SUPPORTED_SCHOOL = "bazhai"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


def _degree(value: Any, *, label: str = "degree") -> float:
    result = _number(value, label=label)
    if not 0.0 <= result < 360.0:
        raise ValueError(f"{label} must be in [0, 360)")
    return result


@lru_cache(maxsize=1)
def source_table() -> dict[str, Any]:
    actual = _sha256(SOURCE_TABLE_PATH)
    if actual != SOURCE_TABLE_SHA256:
        raise RuntimeError(
            f"Fengshui source table hash mismatch: expected {SOURCE_TABLE_SHA256}, got {actual}"
        )
    payload = yaml.safe_load(SOURCE_TABLE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Fengshui source table must be a mapping")
    if payload.get("schema_version") != SOURCE_TABLE_SCHEMA:
        raise RuntimeError("unsupported Fengshui source table schema")
    if payload.get("status") != "verified":
        raise RuntimeError("Fengshui source table is not verified")
    convention = payload.get("selected_convention") or {}
    if convention.get("id") != TABLE_PROFILE:
        raise RuntimeError("Fengshui compass convention mismatch")
    rows = payload.get("mountain_order_clockwise") or []
    if [row.get("index") for row in rows] != list(range(24)):
        raise RuntimeError("Fengshui mountain table must cover indices 0 through 23")
    if tuple(row.get("mountain") for row in rows) != MOUNTAINS:
        raise RuntimeError("Fengshui mountain order mismatch")
    return payload


def source_table_digest() -> str:
    source_table()
    return SOURCE_TABLE_SHA256


def mountain_for_degrees(degrees: float) -> str:
    """Return the half-open 24-mountain sector for an already normalized degree."""

    value = _degree(degrees, label="raw compass degree")
    index = int(math.floor(((value + 7.5) % 360.0) / 15.0))
    return MOUNTAINS[index]


def _mountain_profile(mountain: str) -> dict[str, Any]:
    for row in source_table()["mountain_order_clockwise"]:
        if row["mountain"] == mountain:
            return copy.deepcopy(row)
    raise ValueError(f"unknown 24-mountain identity: {mountain}")


def _circular_distance(left: float, right: float) -> float:
    delta = abs(left - right) % 360.0
    return min(delta, 360.0 - delta)


def _candidate_mountains(degrees: float, uncertainty: float) -> list[str]:
    if uncertainty == 0.0:
        return [mountain_for_degrees(degrees)]
    candidates = [
        str(row["mountain"])
        for row in source_table()["mountain_order_clockwise"]
        if _circular_distance(degrees, float(row["center_degrees"]))
        <= 7.5 + uncertainty + 1e-12
    ]
    if not candidates:
        return [mountain_for_degrees(degrees)]
    return candidates


def _orientation(degrees: float, mountain: str, measurement_ids: list[str]) -> dict[str, Any]:
    profile = _mountain_profile(mountain)
    return {
        "degrees": round(float(degrees), 10),
        "mountain": mountain,
        "trigram": profile["trigram"],
        "measurement_ids": list(measurement_ids),
        "source_dependency_id": "fengshui.observation.compass-layout-contract",
    }


def normalize_compass_measurements(
    measurements: list[Mapping[str, Any]],
    *,
    confirmed_measurement_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(measurements, list):
        raise TypeError("compass_measurements must be a list")
    if not measurements:
        return {
            "status": "missing",
            "measurements": [],
            "candidate_mountains": [],
            "facing": None,
            "sitting": None,
            "selection_policy": "no_measurement",
        }

    normalized: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for raw in measurements:
        if not isinstance(raw, Mapping):
            raise TypeError("each compass measurement must be an object")
        identifier = str(raw.get("measurement_id") or "").strip()
        if not identifier or identifier in identifiers:
            raise ValueError("compass measurement ids must be non-empty and unique")
        identifiers.add(identifier)
        method = str(raw.get("method") or "").strip()
        source_ref = str(raw.get("source_ref") or "").strip()
        source_type = str(raw.get("source_type") or "").strip()
        if not method or not source_ref:
            raise ValueError("compass measurement method and source_ref are required")
        if source_type not in {"user_measurement", "user_file"}:
            raise ValueError("compass source_type must be user_measurement or user_file")
        north_reference = str(raw.get("north_reference") or "").strip()
        if north_reference not in {"true", "magnetic", "grid"}:
            raise ValueError("north_reference must be true, magnetic, or grid")
        raw_degrees = _degree(raw.get("facing_degrees"), label="facing_degrees")
        correction = _number(raw.get("correction_degrees"), label="correction_degrees")
        if abs(correction) > 180.0:
            raise ValueError("correction_degrees must be in [-180, 180]")
        if north_reference == "true" and correction != 0.0:
            raise ValueError("true-north measurement correction must be zero")
        uncertainty = _number(
            raw.get("uncertainty_degrees"), label="uncertainty_degrees"
        )
        if not 0.0 <= uncertainty <= 180.0:
            raise ValueError("uncertainty_degrees must be in [0, 180]")
        quality = str(raw.get("quality") or "").strip()
        if quality not in {"good", "medium", "low", "unreadable"}:
            raise ValueError("compass quality must be good, medium, low, or unreadable")

        unwrapped = raw_degrees + correction
        normalized_degrees = unwrapped % 360.0
        wrap_count = math.floor(unwrapped / 360.0)
        candidates = _candidate_mountains(normalized_degrees, uncertainty)
        usable = quality in {"good", "medium"} and len(candidates) == 1
        normalized.append(
            {
                "measurement_id": identifier,
                "raw_degrees": raw_degrees,
                "method": method,
                "north_reference": north_reference,
                "correction_degrees": correction,
                "correction_operation": "add_to_raw",
                "corrected_unwrapped_degrees": unwrapped,
                "normalized_degrees": normalized_degrees,
                "wrap_count": wrap_count,
                "uncertainty_degrees": uncertainty,
                "quality": quality,
                "source_type": source_type,
                "source_ref": source_ref,
                "candidate_mountains": candidates,
                "status": "usable" if usable else (
                    "ambiguous_boundary" if len(candidates) > 1 else "low_quality"
                ),
            }
        )

    selected: list[dict[str, Any]]
    selection_policy: str
    if confirmed_measurement_id:
        selected = [
            row for row in normalized
            if row["measurement_id"] == confirmed_measurement_id
        ]
        if not selected:
            raise ValueError("confirmed_measurement_id does not identify a measurement")
        selection_policy = "explicit_confirmed_measurement"
    else:
        selected = list(normalized)
        selection_policy = "all_measurements_must_agree"

    if any(row["status"] == "ambiguous_boundary" for row in selected):
        candidates = list(dict.fromkeys(
            mountain
            for row in selected
            for mountain in row["candidate_mountains"]
        ))
        return {
            "status": "ambiguous_boundary",
            "measurements": normalized,
            "candidate_mountains": candidates,
            "facing": None,
            "sitting": None,
            "selection_policy": selection_policy,
        }
    if any(row["status"] == "low_quality" for row in selected):
        return {
            "status": "low_quality",
            "measurements": normalized,
            "candidate_mountains": list(dict.fromkeys(
                mountain
                for row in selected
                for mountain in row["candidate_mountains"]
            )),
            "facing": None,
            "sitting": None,
            "selection_policy": selection_policy,
        }
    mountains = {row["candidate_mountains"][0] for row in selected}
    if len(mountains) != 1:
        return {
            "status": "conflict",
            "measurements": normalized,
            "candidate_mountains": sorted(mountains, key=MOUNTAINS.index),
            "facing": None,
            "sitting": None,
            "selection_policy": selection_policy,
        }

    # Agreement is categorical; no unrequested averaging is performed.
    chosen = selected[0]
    facing_mountain = chosen["candidate_mountains"][0]
    facing_degrees = float(chosen["normalized_degrees"])
    sitting_index = (MOUNTAINS.index(facing_mountain) + 12) % 24
    sitting_mountain = MOUNTAINS[sitting_index]
    sitting_degrees = (facing_degrees + 180.0) % 360.0
    measurement_ids = [str(row["measurement_id"]) for row in selected]
    return {
        "status": "resolved",
        "measurements": normalized,
        "candidate_mountains": [facing_mountain],
        "facing": _orientation(facing_degrees, facing_mountain, measurement_ids),
        "sitting": _orientation(sitting_degrees, sitting_mountain, measurement_ids),
        "selection_policy": selection_policy,
    }


def bazhai_star_map(house_gua: str) -> dict[str, str]:
    maps = source_table()["bazhai"]["star_maps"]
    if house_gua not in maps:
        raise ValueError(f"invalid Bazhai house gua: {house_gua}")
    return copy.deepcopy(maps[house_gua])


def _normalize_region_anchor(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("kind") != "normalized_bbox":
        raise ValueError("image observation region_anchor must be normalized_bbox")
    result = {"kind": "normalized_bbox"}
    for field in ("x", "y", "width", "height"):
        result[field] = _number(raw.get(field), label=f"region_anchor.{field}")
    if not (
        0.0 <= result["x"] < 1.0
        and 0.0 <= result["y"] < 1.0
        and 0.0 < result["width"] <= 1.0
        and 0.0 < result["height"] <= 1.0
        and result["x"] + result["width"] <= 1.0
        and result["y"] + result["height"] <= 1.0
    ):
        raise ValueError("image observation region_anchor is outside the asset")
    return result


def _normalize_quality(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("observation quality is required")
    enums = source_table()["observation_contract"]["quality_enums"]
    result: dict[str, Any] = {}
    for field in ("readability", "lighting", "scale", "viewpoint"):
        value = str(raw.get(field) or "").strip()
        if value not in set(enums[field]):
            raise ValueError(
                f"observation quality.{field} must use the declared enum"
            )
        result[field] = value
    occlusion = _number(raw.get("occlusion"), label="observation quality.occlusion")
    if not 0.0 <= occlusion <= 1.0:
        raise ValueError("observation quality.occlusion must be in [0, 1]")
    result["occlusion"] = occlusion
    return result


def _normalize_assets(raw_assets: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_assets, list):
        raise TypeError("assets must be a list")
    assets: dict[str, dict[str, Any]] = {}
    for raw in raw_assets:
        if not isinstance(raw, Mapping):
            raise TypeError("each asset must be an object")
        identifier = str(raw.get("asset_id") or "").strip()
        if not identifier or identifier in assets:
            raise ValueError("asset ids must be non-empty and unique")
        media_type = str(raw.get("media_type") or "").strip()
        role = str(raw.get("role") or "").strip()
        sha256 = str(raw.get("sha256") or "").strip()
        if media_type != "image" or not role:
            raise ValueError("Fengshui assets must be role-labelled images")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError("Fengshui asset sha256 must be lowercase hexadecimal")
        assets[identifier] = {
            "asset_id": identifier,
            "media_type": media_type,
            "role": role,
            "sha256": sha256,
        }
    return assets


def _source_pack(rule_id: str) -> str:
    return rule_id.split("#", 1)[0]


def _observation_rule_ids(
    kind: str,
    value: Mapping[str, Any],
    *,
    allowed_source_packs: set[str],
) -> list[str]:
    profiles = source_table()["observation_contract"]["rule_activation"]
    mapping = profiles.get(kind) or {}
    relation = str(value.get("relation") or "")
    if relation in mapping:
        candidates = list(mapping[relation])
    else:
        generic = f"observed_{kind}"
        candidates = list(mapping.get(generic) or [])
    return [
        rule_id
        for rule_id in candidates
        if _source_pack(rule_id) in allowed_source_packs
    ]


def _normalize_observations(
    raw_observations: Any,
    *,
    assets: Mapping[str, Mapping[str, Any]],
    property_scope: str,
    requested_variables: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if not isinstance(raw_observations, list):
        raise TypeError("observations must be a list")
    contract = source_table()["observation_contract"]
    allowed_sources = set(contract["accepted_source_types"])
    allowed_kinds = set(contract["allowed_kinds"])
    forbidden_tools = set(contract["forbidden_source_tools"])
    maximum_uncertainty = float(contract["maximum_claim_uncertainty"])
    low_readability = set(contract["low_quality_readability"])
    quality_contracts = contract["source_quality_contracts"]
    image_claim_quality = contract["image_claim_quality"]
    allowed_source_packs = set(
        source_table()["property_scope_profiles"][property_scope][
            "allowed_form_source_packs"
        ]
    )
    identifiers: set[str] = set()
    observations: list[dict[str, Any]] = []
    active_ids: list[str] = []
    uncertain_ids: list[str] = []
    for raw in raw_observations:
        if not isinstance(raw, Mapping):
            raise TypeError("each observation must be an object")
        identifier = str(raw.get("observation_id") or "").strip()
        if not identifier or identifier in identifiers:
            raise ValueError("observation ids must be non-empty and unique")
        identifiers.add(identifier)
        subprofile = str(raw.get("subprofile") or "").strip()
        if subprofile != "form":
            raise ValueError("visible observations belong to the form subprofile")
        kind = str(raw.get("kind") or "").strip()
        if kind not in allowed_kinds:
            raise ValueError("observation kind is not supported")
        if kind not in requested_variables:
            raise ValueError("observation kind was not declared in requested_form_variables")
        source_type = str(raw.get("source_type") or "").strip()
        if source_type not in allowed_sources:
            raise ValueError("unsupported observation source_type")
        source_tool = raw.get("source_tool")
        if source_tool is not None:
            if str(source_tool) in forbidden_tools:
                raise ValueError("source_tool cannot claim vision or LLM fact authority")
            raise ValueError("source_tool is not part of the observation contract")
        value = raw.get("value")
        if not isinstance(value, Mapping) or not value:
            raise ValueError("observation value must be a non-empty object")
        quality = _normalize_quality(raw.get("quality"))
        if "uncertainty" not in raw:
            raise ValueError("observation uncertainty is required")
        uncertainty = _number(raw.get("uncertainty"), label="observation uncertainty")
        if not 0.0 <= uncertainty <= 1.0:
            raise ValueError("observation uncertainty must be in [0, 1]")

        normalized: dict[str, Any] = {
            "observation_id": identifier,
            "subprofile": subprofile,
            "kind": kind,
            "source_type": source_type,
            "value": copy.deepcopy(dict(value)),
            "quality": quality,
            "uncertainty": uncertainty,
        }
        if source_type == "image_transcription":
            image_contract = quality_contracts["image_transcription"]
            if (
                quality["lighting"] in set(image_contract["forbidden_lighting"])
                or quality["scale"] in set(image_contract["forbidden_scale"])
                or quality["viewpoint"] in set(image_contract["forbidden_viewpoint"])
            ):
                raise ValueError(
                    "image_transcription quality cannot use non-image sentinels"
                )
            asset_id = str(raw.get("asset_id") or "").strip()
            if asset_id not in assets:
                raise ValueError("image observation asset_id must identify a declared asset")
            normalized["asset_id"] = asset_id
            normalized["asset_sha256"] = str(assets[asset_id]["sha256"])
            normalized["region_anchor"] = _normalize_region_anchor(
                raw.get("region_anchor")
            )
        else:
            source_ref = str(raw.get("source_ref") or "").strip()
            if not source_ref:
                raise ValueError("non-image observation source_ref is required")
            normalized["source_ref"] = source_ref

        precision_eligible = True
        if (
            source_type == "image_transcription"
            and kind in set(image_claim_quality["precision_required_kinds"])
        ):
            precision_eligible = (
                quality["scale"]
                in set(image_claim_quality["precision_allowed_scale"])
                and quality["viewpoint"]
                in set(image_claim_quality["precision_allowed_viewpoint"])
            )
        eligible = (
            quality["readability"] not in low_readability
            and quality["lighting"]
            not in set(image_claim_quality["disallowed_lighting"])
            and quality["occlusion"] < 0.5
            and uncertainty <= maximum_uncertainty
            and precision_eligible
        )
        rule_ids = (
            _observation_rule_ids(
                kind,
                value,
                allowed_source_packs=allowed_source_packs,
            )
            if eligible
            else []
        )
        normalized["status"] = (
            "accepted_observation_not_verdict" if eligible else "uncertain_observation"
        )
        normalized["source_rule_ids"] = sorted(set(rule_ids))
        if eligible:
            active_ids.extend(rule_ids)
        else:
            uncertain_ids.append(identifier)
        observations.append(normalized)
    return observations, sorted(set(active_ids)), uncertain_ids


def _normalize_layout(
    raw: Any,
    *,
    accepted_observations: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if not isinstance(raw, Mapping):
        raise TypeError("layout_graph must be an object")
    contract = source_table()["layout_contract"]
    allowed_node_kinds = set(contract["allowed_node_kinds"])
    allowed_boundaries = set(contract["allowed_boundaries"])
    node_observation_kinds = {
        str(kind): set(str(item) for item in kinds)
        for kind, kinds in contract["node_observation_kinds"].items()
    }
    direction_proves_node = set(
        str(item) for item in contract["direction_measurement_proves_node_kinds"]
    )
    edge_observation_kinds = {
        str(boundary): set(str(item) for item in kinds)
        for boundary, kinds in contract["edge_observation_kinds"].items()
    }
    raw_nodes = raw.get("nodes")
    raw_edges = raw.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValueError("layout_graph requires nodes and edges lists")
    nodes: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for raw_node in raw_nodes:
        if not isinstance(raw_node, Mapping):
            raise TypeError("layout nodes must be objects")
        identifier = str(raw_node.get("node_id") or "").strip()
        kind = str(raw_node.get("kind") or "").strip()
        if not identifier or identifier in by_id or kind not in allowed_node_kinds:
            raise ValueError("layout node ids must be unique and kinds non-empty")
        node = {"node_id": identifier, "kind": kind}
        if any(field in raw_node for field in contract["forbidden_direction_fields"]):
            raise ValueError(
                "layout direction_degrees is forbidden; use direction_measurement"
            )
        observation_id = str(raw_node.get("observation_id") or "").strip()
        if observation_id:
            if observation_id not in accepted_observations:
                raise ValueError(
                    "layout node observation_id must identify an accepted observation"
                )
            observation_kind = str(
                accepted_observations[observation_id].get("kind") or ""
            )
            if observation_kind not in node_observation_kinds[kind]:
                if kind in {"room", "zone"}:
                    raise ValueError(
                        f"{kind} layout node requires an accepted layout observation"
                    )
                raise ValueError(
                    f"{kind} layout node observation must be entrance or layout"
                )
            node["observation_id"] = observation_id
        direction_measurement = raw_node.get("direction_measurement")
        if direction_measurement is not None:
            if not isinstance(direction_measurement, Mapping):
                raise TypeError("layout direction_measurement must be an object")
            normalized_direction = normalize_compass_measurements(
                [direction_measurement]
            )
            node["direction_measurement"] = copy.deepcopy(
                normalized_direction["measurements"][0]
            )
            node["direction_status"] = normalized_direction["status"]
            if normalized_direction["status"] == "resolved":
                direction = copy.deepcopy(normalized_direction["facing"])
                node["direction"] = direction
                node["mountain"] = direction["mountain"]
                node["trigram"] = direction["trigram"]
        elif not observation_id:
            raise ValueError(
                "layout node requires direction_measurement or accepted observation_id"
            )
        if kind not in direction_proves_node and not observation_id:
            raise ValueError(
                f"{kind} layout node requires an accepted layout observation"
            )
        nodes.append(node)
        by_id[identifier] = node

    edges: list[dict[str, Any]] = []
    resets: list[dict[str, Any]] = []
    missing: list[str] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, Mapping):
            raise TypeError("layout edges must be objects")
        source = str(raw_edge.get("from") or "").strip()
        target = str(raw_edge.get("to") or "").strip()
        boundary = str(raw_edge.get("boundary") or "").strip()
        if (
            source not in by_id
            or target not in by_id
            or boundary not in allowed_boundaries
        ):
            raise ValueError("layout edge endpoints and boundary must be valid")
        observation_id = str(raw_edge.get("observation_id") or "").strip()
        if observation_id not in accepted_observations:
            raise ValueError(
                "layout edge observation_id must identify an accepted observation"
            )
        observation_kind = str(
            accepted_observations[observation_id].get("kind") or ""
        )
        if observation_kind not in edge_observation_kinds[boundary]:
            if boundary == "separating_wall_with_door":
                raise ValueError(
                    "partition boundary requires an accepted layout observation"
                )
            raise ValueError(
                "layout edge observation must be an accepted layout or entrance observation"
            )
        edge = {
            "from": source,
            "to": target,
            "boundary": boundary,
            "observation_id": observation_id,
        }
        if boundary == "separating_wall_with_door":
            door_id = str(raw_edge.get("door_id") or "").strip()
            door = by_id.get(door_id)
            if not door or door.get("kind") != "door":
                raise ValueError("partition reset requires a declared door node")
            edge["door_id"] = door_id
            if "mountain" not in door:
                missing.append(f"door_direction_measurement:{door_id}")
            else:
                resets.append(
                    {
                        "door_id": door_id,
                        "from": source,
                        "to": target,
                        "start_mountain": door["mountain"],
                        "source_rule_id": "fengshui/yangzhai-shishu#YZS-R006",
                    }
                )
        edges.append(edge)
    return {"nodes": nodes, "edges": edges}, resets, list(dict.fromkeys(missing))


def _normalize_building(raw: Any, *, selected_school: str | None) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError("building must be an object")
    result: dict[str, Any] = {}
    for field in ("completion_year", "occupation_year", "supplied_period"):
        if field not in raw:
            continue
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"building.{field} must be an integer")
        if field.endswith("_year") and not 1000 <= value <= 3000:
            raise ValueError(f"building.{field} is outside the supported civil range")
        if field == "supplied_period" and not 1 <= value <= 9:
            raise ValueError("building.supplied_period must be 1 through 9")
        result[field] = value
    for field in ("source_type", "source_ref"):
        if field in raw:
            value = str(raw[field] or "").strip()
            if not value:
                raise ValueError(f"building.{field} must be non-empty")
            result[field] = value
    if result and not all(field in result for field in ("source_type", "source_ref")):
        raise ValueError("building chronology requires source_type and source_ref")
    if result and result.get("source_type") not in set(
        source_table()["building_chronology_contract"]["accepted_source_types"]
    ):
        raise ValueError("building.source_type is not an accepted caller source")
    if "supplied_period" in result:
        result["period_use"] = (
            "retained_not_calculated_for_bazhai"
            if selected_school == SUPPORTED_SCHOOL
            else "retained_not_calculated"
        )
    elif selected_school == SUPPORTED_SCHOOL:
        result["period_use"] = "not_required_for_bazhai"
    return result


def _declared_orientation_conflicts(
    raw: Any,
    compass: Mapping[str, Any],
    *,
    confirmed_measurement_id: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise TypeError("declared_orientation must be an object")
    if not raw:
        return []
    facing = str(raw.get("facing_mountain") or "").strip()
    sitting = str(raw.get("sitting_mountain") or "").strip()
    if facing not in MOUNTAINS or sitting not in MOUNTAINS:
        raise ValueError("declared orientation requires valid facing and sitting mountains")
    internally_inconsistent = (
        MOUNTAINS[(MOUNTAINS.index(facing) + 12) % 24] != sitting
    )
    calculated_facing = compass.get("facing")
    calculated_sitting = compass.get("sitting")
    calculated_mismatch = (
        isinstance(calculated_facing, Mapping)
        and isinstance(calculated_sitting, Mapping)
        and (
            calculated_facing.get("mountain") != facing
            or calculated_sitting.get("mountain") != sitting
        )
    )
    if confirmed_measurement_id and (
        internally_inconsistent or calculated_mismatch
    ):
        policy = source_table()["compass_conflict_resolution"]
        if not policy["confirmed_measurement_overrides_declared_orientation"]:
            raise RuntimeError(
                "confirmed-measurement precedence is not enabled by the source table"
            )
        return [
            {
                "code": "declared_orientation_overridden_by_confirmed_measurement",
                "blocking": False,
                "confirmed_measurement_id": confirmed_measurement_id,
                "declared_facing": facing,
                "declared_sitting": sitting,
                "calculated_facing": (
                    calculated_facing.get("mountain")
                    if isinstance(calculated_facing, Mapping)
                    else None
                ),
                "calculated_sitting": (
                    calculated_sitting.get("mountain")
                    if isinstance(calculated_sitting, Mapping)
                    else None
                ),
                "reasons": [
                    reason
                    for reason, present in (
                        ("declared_sitting_facing_not_opposite", internally_inconsistent),
                        ("declared_orientation_conflict", calculated_mismatch),
                    )
                    if present
                ],
            }
        ]

    conflicts: list[dict[str, Any]] = []
    if internally_inconsistent:
        conflicts.append(
            {
                "code": "declared_sitting_facing_not_opposite",
                "blocking": True,
                "declared_facing": facing,
                "declared_sitting": sitting,
            }
        )
    if calculated_mismatch:
        conflicts.append(
            {
                "code": "declared_orientation_conflict",
                "blocking": True,
                "declared_facing": facing,
                "declared_sitting": sitting,
                "calculated_facing": calculated_facing.get("mountain"),
                "calculated_sitting": calculated_sitting.get("mountain"),
            }
        )
    return conflicts


def _fact_digest_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(payload))
    result.pop("fact_digest", None)
    result.pop("validation", None)
    return result


def fact_digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest(_fact_digest_payload(payload))


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build stable paths consumed by the source-evidence matcher."""

    if isinstance(value, Mapping) and value:
        for key in sorted(value, key=str):
            token = _escape_fact_token(str(key))
            yield from _fact_leaves(value[key], f"{path}/{token}")
        return
    if isinstance(value, (list, tuple)) and value:
        for index, item in enumerate(value):
            yield from _fact_leaves(item, f"{path}/{index}")
        return
    yield path or "/", value


def _source_conditioned_patterns(
    output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose verified Fengshui applicability without creating a verdict."""

    indexed = {
        "chart_facts": {
            "fact_layer_status": FACT_LAYER_STATUS,
            "output": dict(output),
        }
    }
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.fengshui.v1",
            provider_version=ADAPTER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "fengshui":
            continue
        matched, fact_ids, predicate_audit = evidence_rules.match_rule(
            rule, fact_refs
        )
        if not matched:
            continue
        matches.append(
            {
                "rule_id": rule.rule_id,
                "local_rule_id": rule.local_rule_id,
                "title": rule.title,
                "source_pack": rule.source_pack,
                "source_anchor": rule.source_anchor,
                "status": "predicate_matched_not_verdict",
                "fact_paths": list(fact_ids),
                "predicate_audit": list(predicate_audit),
                "source_dependency_id": "fengshui.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def _build_fact_layer(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        raise TypeError("Fengshui spec must be an object")
    if spec.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError("unsupported Fengshui input schema")
    property_scope = str(spec.get("property_scope") or "").strip()
    if property_scope not in {"residential", "site_general", "burial_cultural_study"}:
        raise ValueError("unsupported Fengshui property_scope")
    scope_profile = source_table()["property_scope_profiles"][property_scope]
    raw_subprofiles = spec.get("subprofiles")
    if not isinstance(raw_subprofiles, list) or not raw_subprofiles:
        raise ValueError("Fengshui subprofiles must be a non-empty list")
    subprofiles = tuple(dict.fromkeys(str(item) for item in raw_subprofiles))
    if len(subprofiles) != len(raw_subprofiles):
        raise ValueError("Fengshui subprofiles must be unique")
    if set(subprofiles) - SUPPORTED_SUBPROFILES:
        raise ValueError("unsupported Fengshui subprofile")
    if set(subprofiles) - set(scope_profile["allowed_subprofiles"]):
        raise ValueError(
            "Fengshui property_scope does not allow the selected subprofile"
        )
    active_subprofiles = [
        name for name in ("form", "liqi") if name in subprofiles
    ]

    raw_requested_variables = spec.get("requested_form_variables")
    if not isinstance(raw_requested_variables, list):
        raise TypeError("requested_form_variables must be a list")
    requested_variables = tuple(str(item) for item in raw_requested_variables)
    allowed_kinds = set(source_table()["observation_contract"]["allowed_kinds"])
    if len(set(requested_variables)) != len(requested_variables):
        raise ValueError("requested_form_variables must be unique")
    if set(requested_variables) - allowed_kinds:
        raise ValueError("requested_form_variables contains an unsupported kind")
    if "form" in active_subprofiles and not requested_variables:
        raise ValueError("form subprofile requires requested_form_variables")
    if "form" not in active_subprofiles and requested_variables:
        raise ValueError(
            "requested_form_variables requires the form subprofile"
        )

    liqi_input = spec.get("liqi")
    if not isinstance(liqi_input, Mapping):
        raise TypeError("liqi must be an object")
    selected_school: str | None = None
    if "liqi" in active_subprofiles:
        selected_school = str(liqi_input.get("selected_school") or "").strip()
        if selected_school != SUPPORTED_SCHOOL:
            raise ValueError(
                f"unsupported Fengshui school: {selected_school or '<missing>'}"
            )
        school_profile = source_table()["school_profiles"][selected_school]
        if property_scope not in set(school_profile["allowed_property_scopes"]):
            raise ValueError(
                "Fengshui property_scope does not allow the selected school"
            )
        if liqi_input.get("origin_basis") != school_profile["origin_basis"]:
            raise ValueError(
                "unsupported Bazhai basis; only explicit door_trigram is source-verified"
            )
    elif liqi_input:
        raise ValueError("liqi settings require the liqi subprofile")

    assets = _normalize_assets(spec.get("assets"))
    observations, form_rule_ids, uncertain_observation_ids = _normalize_observations(
        spec.get("observations"),
        assets=assets,
        property_scope=property_scope,
        requested_variables=requested_variables,
    )
    if "form" not in active_subprofiles and observations:
        raise ValueError("observations require the form subprofile")
    accepted_observations_by_id = {
        row["observation_id"]: row
        for row in observations
        if row["status"] == "accepted_observation_not_verdict"
    }
    layout, layout_resets, layout_missing = _normalize_layout(
        spec.get("layout_graph"),
        accepted_observations=accepted_observations_by_id,
    )
    confirmed_measurement_id = (
        str(spec.get("confirmed_measurement_id") or "").strip() or None
    )
    compass = normalize_compass_measurements(
        spec.get("compass_measurements"),
        confirmed_measurement_id=confirmed_measurement_id,
    )
    conflicts = _declared_orientation_conflicts(
        spec.get("declared_orientation"),
        compass,
        confirmed_measurement_id=confirmed_measurement_id,
    )
    if compass["status"] == "conflict":
        conflicts.append(
            {
                "code": "compass_measurement_conflict",
                "blocking": True,
                "candidate_mountains": list(compass["candidate_mountains"]),
            }
        )
    building = _normalize_building(
        spec.get("building"), selected_school=selected_school
    )

    accepted_observations = [
        row for row in observations
        if row["status"] == "accepted_observation_not_verdict"
    ]
    accepted_observation_fact_keys = sorted(
        {
            f"{row['kind']}|{row['value']['relation']}"
            for row in accepted_observations
        }
    )
    accepted_kinds = {str(row["kind"]) for row in accepted_observations}
    complete_variables = [
        kind for kind in requested_variables if kind in accepted_kinds
    ]
    missing_variables = [
        kind for kind in requested_variables if kind not in accepted_kinds
    ]
    if "form" not in active_subprofiles:
        form = {
            "status": "not_requested",
            "requested_variables": [],
            "complete_variables": [],
            "missing_variables": [],
            "observations": [],
            "uncertain_observation_ids": [],
            "accepted_observation_fact_keys": [],
            "claims": [],
        }
        active_form_ids: list[str] = []
    elif not observations:
        form = {
            "status": "missing_observation",
            "requested_variables": list(requested_variables),
            "complete_variables": [],
            "missing_variables": list(missing_variables),
            "observations": [],
            "uncertain_observation_ids": [],
            "accepted_observation_fact_keys": [],
            "claims": [],
        }
        active_form_ids = []
    else:
        form = {
            "status": (
                "complete"
                if not missing_variables
                and len(accepted_observations) == len(observations)
                else "partial"
            ),
            "requested_variables": list(requested_variables),
            "complete_variables": complete_variables,
            "missing_variables": missing_variables,
            "observations": observations,
            "uncertain_observation_ids": uncertain_observation_ids,
            "accepted_observation_fact_keys": accepted_observation_fact_keys,
            "claims": [],
        }
        active_form_ids = form_rule_ids

    active_ids = list(active_form_ids)
    critical_missing: list[str] = (
        list(layout_missing) if "liqi" in active_subprofiles else []
    )
    uncertainties: list[dict[str, Any]] = [
        {
            "code": "uncertain_observation",
            "observation_id": identifier,
        }
        for identifier in uncertain_observation_ids
    ]
    if "form" in active_subprofiles:
        critical_missing.extend(
            f"form_observation:{kind}" for kind in missing_variables
        )

    liqi: dict[str, Any]
    compass_blocked = compass["status"] != "resolved" or any(
        bool(row.get("blocking", True)) for row in conflicts
    )
    bazhai_basis: dict[str, Any] | None = None
    if "liqi" in active_subprofiles:
        origin_node_id = str(liqi_input.get("origin_node_id") or "").strip()
        if not origin_node_id:
            critical_missing.append("bazhai_origin_door")
        else:
            origin_node = next(
                (
                    node
                    for node in layout["nodes"]
                    if node["node_id"] == origin_node_id
                ),
                None,
            )
            if origin_node is None:
                critical_missing.append(f"bazhai_origin_door:{origin_node_id}")
            elif origin_node["kind"] not in set(
                source_table()["layout_contract"]["bazhai_origin_node_kinds"]
            ):
                raise ValueError("Bazhai origin_node_id must identify an entrance or door")
            elif "direction" not in origin_node:
                critical_missing.append(
                    f"door_direction_measurement:{origin_node_id}"
                )
            else:
                direction = origin_node["direction"]
                measurement = origin_node["direction_measurement"]
                bazhai_basis = {
                    "kind": "door_trigram",
                    "node_id": origin_node_id,
                    "degrees": direction["degrees"],
                    "mountain": direction["mountain"],
                    "trigram": direction["trigram"],
                    "measurement_ids": list(direction["measurement_ids"]),
                    "source_type": measurement["source_type"],
                    "source_ref": measurement["source_ref"],
                    "source_dependency_id": direction["source_dependency_id"],
                }
    if "liqi" not in active_subprofiles:
        liqi = {"status": "not_requested", "selected_school": None}
    elif compass_blocked or bazhai_basis is None:
        if compass_blocked:
            critical_missing.append("confirmed_facing_measurement")
        liqi = {
            "status": "blocked",
            "selected_school": selected_school,
            "reason": (
                "confirmed_unambiguous_orientation_required"
                if compass_blocked
                else "measured_bazhai_origin_door_required"
            ),
        }
        if compass["status"] in {"ambiguous_boundary", "low_quality"}:
            uncertainties.append(
                {
                    "code": f"compass_{compass['status']}",
                    "candidate_mountains": list(compass["candidate_mountains"]),
                }
            )
    else:
        origin_gua = str(bazhai_basis["trigram"])
        east = set(source_table()["bazhai"]["east_group"])
        origin_group = "east_four" if origin_gua in east else "west_four"
        liqi = {
            "status": "calculated_selected_school_facts_not_verdict",
            "selected_school": SUPPORTED_SCHOOL,
            "bazhai": {
                "profile_id": source_table()["bazhai"]["profile_id"],
                "basis": bazhai_basis,
                "origin_gua": origin_gua,
                "origin_group": origin_group,
                "direction_star_map": bazhai_star_map(origin_gua),
                "layout_resets": layout_resets,
                "status": "calculated_correspondences_not_judgment",
            },
        }
        active_ids.extend(source_table()["calculated_rule_activation"]["compass"])
        active_ids.extend(source_table()["calculated_rule_activation"]["bazhai"])
        if layout_resets:
            active_ids.extend(
                source_table()["calculated_rule_activation"]["partition_door_reset"]
            )

    active_ids = sorted(set(active_ids))
    if any("#" not in identifier or not identifier.startswith("fengshui/") for identifier in active_ids):
        raise RuntimeError("Fengshui source rule ids must be pack-qualified")

    normalized_spec = copy.deepcopy(dict(spec))
    input_digest = canonical_digest(normalized_spec)
    output: dict[str, Any] = {
        "active_subprofiles": active_subprofiles,
        "observation_provenance": {
            "asset_ids": sorted(assets),
            "asset_sha256": {
                identifier: str(assets[identifier]["sha256"])
                for identifier in sorted(assets)
            },
            "observation_ids": [row["observation_id"] for row in observations],
            "source_types": sorted({row["source_type"] for row in observations}),
            "provider_performed_vision": False,
        },
        "compass": compass,
        "building_chronology": building,
        "layout_graph": layout,
        "form": form,
        "liqi": liqi,
        "active_source_rule_ids": active_ids,
        "conflicts": conflicts,
        "uncertainties": uncertainties,
        "critical_missing": list(dict.fromkeys(critical_missing)),
    }
    output["source_conditioned_patterns"] = _source_conditioned_patterns(output)

    payload: dict[str, Any] = {
        "schema_version": FACT_SCHEMA_VERSION,
        "system": "fengshui",
        "fact_layer_status": FACT_LAYER_STATUS,
        "fact_layer_scope": FACT_LAYER_SCOPE,
        "adapter": {
            "name": "mingli-master.fengshui",
            "version": ADAPTER_VERSION,
            "rule_profile": TABLE_PROFILE,
            "generated_at": "deterministic-observation-normalization",
        },
        "source_table": {
            "path": "references/matrices/fengshui-source-tables-v1.yaml",
            "sha256": SOURCE_TABLE_SHA256,
            "profile_id": TABLE_PROFILE,
        },
        "input": {
            "property_scope": property_scope,
            "fengshui_spec": normalized_spec,
            "input_digest": input_digest,
        },
        "calendar_normalization": {
            "status": "not_applicable",
            "reason": "spatial_observation_without_calendar_calculation",
        },
        "output": output,
        "source_dependency_ids": list(SOURCE_DEPENDENCIES),
        "trace": [
            "validated raw degrees before any explicit correction",
            "normalized caller-supplied observations without performing vision",
            "kept form and selected Bazhai facts in separate namespaces",
            "did not calculate Xuankong, Sanhe, outcomes, or unobserved features",
        ],
    }
    payload["fact_digest"] = fact_digest(payload)
    return payload


def build_fact_layer(spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = _build_fact_layer(spec)
    report = validate_fact_layer(payload)
    if not report["ok"]:
        raise RuntimeError(
            "Fengshui fact validation failed: " + ", ".join(report["codes"])
        )
    payload["validation"] = {
        "ok": True,
        "system": "fengshui",
        "validator": "mingli-master.fengshui.validate_fact_layer",
    }
    return payload


_PUBLIC_PROJECTION_PRIVATE_KEYS = frozenset(
    {
        "assets",
        "asset_id",
        "asset_ids",
        "asset_sha256",
        "sha256",
        "source_ref",
        "region_anchor",
        "observation_id",
        "observation_ids",
        "measurement_id",
        "measurement_ids",
        "node_id",
        "origin_node_id",
    }
)


def public_projection(facts: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded facts without caller media or observation provenance."""

    def redact(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): redact(item)
                for key, item in value.items()
                if str(key) not in _PUBLIC_PROJECTION_PRIVATE_KEYS
            }
        if isinstance(value, (list, tuple)):
            return [redact(item) for item in value]
        return copy.deepcopy(value)

    projected = redact(facts)
    raw_input = facts.get("input")
    if isinstance(raw_input, Mapping):
        projected["input"] = {
            "property_scope": raw_input.get("property_scope"),
            "input_digest": raw_input.get("input_digest"),
        }
    output = projected.get("output")
    if isinstance(output, dict):
        output.pop("observation_provenance", None)
    return projected


def required_intake_facts(spec: Mapping[str, Any]) -> tuple[str, ...]:
    """Return critical caller-owned facts before evidence compilation."""

    payload = _build_fact_layer(spec)
    missing = payload["output"]["critical_missing"]
    return tuple(str(item) for item in missing)


def validate_fact_layer(payload: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def invalid(code: str, message: str) -> None:
        findings.append({"code": code, "message": message, "level": "error"})

    if not isinstance(payload, Mapping):
        return {
            "ok": False,
            "codes": ["fengshui_payload_not_mapping"],
            "findings": [{
                "code": "fengshui_payload_not_mapping",
                "message": "Fengshui payload must be an object",
                "level": "error",
            }],
        }
    if payload.get("schema_version") != FACT_SCHEMA_VERSION:
        invalid("fengshui_schema_mismatch", "unexpected Fengshui fact schema")
    if payload.get("system") != "fengshui":
        invalid("fengshui_system_mismatch", "Fengshui payload system mismatch")
    if payload.get("fact_layer_status") != FACT_LAYER_STATUS:
        invalid("fengshui_status_mismatch", "Fengshui fact-layer status mismatch")
    if payload.get("fact_digest") != fact_digest(payload):
        invalid("fengshui_fact_digest_mismatch", "Fengshui fact digest mismatch")
    output = payload.get("output") if isinstance(payload.get("output"), Mapping) else {}
    active = output.get("active_source_rule_ids")
    if not isinstance(active, list) or any(
        not isinstance(item, str)
        or not item.startswith("fengshui/")
        or "#" not in item
        for item in active or []
    ):
        invalid(
            "fengshui_unqualified_source_rule_id",
            "Fengshui active source rules must use pack-qualified ids",
        )
    if "not_calculated_classical_rule_ids" in output:
        invalid(
            "fengshui_false_inactive_rule_surface",
            "Fengshui must not expose an evidence-matchable inactive-rule field",
        )
    input_payload = payload.get("input") if isinstance(payload.get("input"), Mapping) else {}
    spec = input_payload.get("fengshui_spec")
    if isinstance(spec, Mapping):
        try:
            rebuilt = _build_fact_layer(spec)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            invalid("fengshui_rebuild_failed", f"Fengshui input cannot rebuild: {exc}")
        else:
            for field in (
                "schema_version",
                "system",
                "fact_layer_status",
                "fact_layer_scope",
                "adapter",
                "source_table",
                "input",
                "calendar_normalization",
                "output",
                "source_dependency_ids",
                "trace",
                "fact_digest",
            ):
                if payload.get(field) != rebuilt.get(field):
                    invalid(
                        "fengshui_rebuild_mismatch",
                        f"Fengshui payload differs from rebuilt {field}",
                    )
                    break
    else:
        invalid("fengshui_missing_input_spec", "Fengshui input spec is missing")
    return {
        "ok": not findings,
        "codes": [item["code"] for item in findings],
        "findings": findings,
    }


__all__ = [
    "ADAPTER_VERSION",
    "FACT_LAYER_SCOPE",
    "FACT_LAYER_STATUS",
    "MOUNTAINS",
    "SOURCE_DEPENDENCIES",
    "SOURCE_TABLE_SHA256",
    "TABLE_PROFILE",
    "bazhai_star_map",
    "build_fact_layer",
    "fact_digest",
    "mountain_for_degrees",
    "normalize_compass_measurements",
    "public_projection",
    "required_intake_facts",
    "source_table",
    "source_table_digest",
    "validate_fact_layer",
]


def filtered_intake_spec(
    supplied: Mapping[str, Any],
    missing_facts: set[str],
) -> dict[str, Any] | None:
    """Return only Fengshui children authorized by the pending intake."""

    if "fengshui_spec" in missing_facts or "subprofiles" in missing_facts:
        return copy.deepcopy(dict(supplied))

    allowed: set[str] = set()
    if "requested_form_variables" in missing_facts:
        allowed.update(
            {
                "requested_form_variables",
                "assets",
                "observations",
                "layout_graph",
            }
        )
    if missing_facts & {
        "compass_measurements",
        "confirmed_facing_measurement",
    }:
        allowed.update(
            {
                "compass_measurements",
                "confirmed_measurement_id",
                "declared_orientation",
            }
        )
    if any(
        fact == "terrain_or_site_observation"
        or fact.startswith("form_observation:")
        for fact in missing_facts
    ):
        allowed.update({"assets", "observations", "layout_graph"})
    if any(
        fact == "bazhai_origin_door"
        or fact.startswith("bazhai_origin_door:")
        or fact.startswith("door_direction_measurement:")
        for fact in missing_facts
    ):
        allowed.update({"liqi", "layout_graph"})
    for field in (
        "liqi",
        "assets",
        "observations",
        "layout_graph",
    ):
        if field in missing_facts:
            allowed.add(field)
    if not allowed:
        return None
    return {
        key: copy.deepcopy(value)
        for key, value in supplied.items()
        if key in allowed
    }
