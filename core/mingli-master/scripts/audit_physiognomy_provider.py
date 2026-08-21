#!/usr/bin/env python3
"""Machine-readable completeness audit for the Task 7M observation provider."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

import audit_algorithm_sources
from audit_provider_preflight import provider_preflight_failure
import reading_source_plan
from evidence_independence import source_profile
from reading_engine import physiognomy
from reading_engine.contracts import ReadingRequest, canonical_digest
from reading_engine.evidence_rules import production_evidence_rules
from reading_engine.providers import PROVIDER_CAPABILITIES, PhysiognomyProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references/fixtures/physiognomy-v51.yaml"
SOURCE_TABLE = ROOT / "references/matrices/physiognomy-source-tables-v1.yaml"
ANNOTATIONS = ROOT / "references/fixtures/assets/physiognomy/annotation-manifest-v1.yaml"
ORACLE = ROOT / "scripts/physiognomy_fixture_reference.py"
MATRIX = ROOT / "references/matrices/algorithm-source-dependencies.yaml"
PROVIDER = ROOT / "scripts/reading_engine/physiognomy.py"
LINEAGE_REGISTRY = ROOT / "references/inference/source-lineages-v1.json"
FIXTURE_SHA256 = "e4d27b0ed84b128b180c790ac2302f944afea50c4b31a96c331ec7ef615d3258"
EXPECTED_PROVIDER_ID = "mingli-master.physiognomy.v1"
EXPECTED_PROVIDER_VERSION = "1.1.0"
SOURCE_TABLE_SHA256 = "e8c499b22fd15ba1e1b6b31d304b77891727c827682d8e58ebc95f7a2adad08d"
ANNOTATION_SHA256 = "33a4cafe1388a8315e0aec9159d94864e8abdbfbae0eab8c4c3eaa013f1a6384"
ORACLE_SHA256 = "a59b2b0779c8ca36437d574cbfe2c66b97af82ee881d557f2ac92a1295a1ed50"
PROVIDER_SHA256 = "58c783c228d1e85fc9f3dc1ad0f26076675d1e6848d1079eb46e1a67586d1eb1"
LINEAGE_REGISTRY_SHA256 = "6bf2af77cdb94d2d05e94b97726d7b0cb658dfda01e22886f749636d56ab94e0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _projection(facts: Mapping[str, Any]) -> dict[str, Any]:
    output = facts["output"]
    return {
        "critical_missing": list(output["critical_missing"]),
        "active_observation_count": len(output["active_observation_ids"]),
        "conflict_count": len(output["observation_conflicts"]),
        "cross_capture_variation_count": len(output["cross_capture_variations"]),
        "superseded_observation_count": len(output["superseded_observation_ids"]),
        "active_source_rule_ids": list(output["active_source_rule_ids"]),
        "active_regions": sorted(
            str(row["region"])
            for row in output["normalized_visible_observations"]
        ),
        "active_descriptors": sorted(
            str(row["descriptor"])
            for row in output["normalized_visible_observations"]
        ),
    }


def _within(anchor: Mapping[str, Any], annotation: list[Any]) -> bool:
    try:
        x, y, width, height = (float(annotation[index]) for index in range(4))
        return (
            float(anchor["x"]) + 1e-12 >= x
            and float(anchor["y"]) + 1e-12 >= y
            and float(anchor["x"]) + float(anchor["width"]) <= x + width + 1e-12
            and float(anchor["y"]) + float(anchor["height"]) <= y + height + 1e-12
        )
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def _oracle_imports_are_independent(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {item.name for item in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                return False
            names = {str(node.module or "")}
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.casefold()
            if "reading_engine" in lowered or "audit_physiognomy_provider" in lowered:
                return False
            continue
        else:
            continue
        if any(
            name == "reading_engine"
            or name.startswith("reading_engine.")
            or ".reading_engine" in name
            or name == "physiognomy"
            or name.endswith(".physiognomy")
            or "audit_physiognomy_provider" in name
            for name in names
        ):
            return False
    return True


def _load_oracle(path: Path):
    module_name = "_mingli_physio_oracle_" + _sha256(path)[:16]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the hash-bound Physiognomy oracle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    projection = getattr(module, "reference_projection", None)
    if not callable(projection):
        raise RuntimeError("Physiognomy oracle lacks reference_projection")
    return projection


def _semantic_scenario_payload(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Remove opaque identity and canonicalize unordered observation topology."""

    minimum_anchor_pixels = float(
        physiognomy.source_table()["visibility_contract"][
            "minimum_region_anchor_pixels_per_axis"
        ]
    )

    def stable(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def canonical(value: Any, *, sorted_list: bool = False) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): canonical(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, list):
            rows = [canonical(item) for item in value]
            return sorted(rows, key=stable) if sorted_list else rows
        return copy.deepcopy(value)

    assets = {
        str(item.get("asset_id")): item
        for item in spec.get("assets") or ()
        if isinstance(item, Mapping)
    }
    targets = {
        str(item.get("target_id")): item
        for item in spec.get("requested_targets") or ()
        if isinstance(item, Mapping)
    }
    observations = {
        str(item.get("observation_id")): item
        for item in spec.get("observations") or ()
        if isinstance(item, Mapping)
    }

    def target_signature(target_id: Any) -> dict[str, Any]:
        target = targets.get(str(target_id), {})
        return canonical(
            {
                key: value
                for key, value in target.items()
                if key != "target_id"
            }
        )

    def asset_signature(asset: Mapping[str, Any]) -> dict[str, Any]:
        omitted = {
            "asset_id",
            "capture_id",
            "subject_ref",
            "sha256",
            "byte_length",
            "pixel_width",
            "pixel_height",
            "synthetic",
            "no_real_person",
        }
        result = {
            key: value
            for key, value in asset.items()
            if key not in omitted
        }
        if isinstance(result.get("supplied_visible_regions"), list):
            result["supplied_visible_regions"] = sorted(
                result["supplied_visible_regions"]
            )
        return canonical(result)

    observation_cache: dict[str, dict[str, Any]] = {}

    def observation_signature(
        observation_id: Any,
        trail: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        identifier = str(observation_id)
        if identifier in observation_cache:
            return copy.deepcopy(observation_cache[identifier])
        observation = observations.get(identifier, {})
        omitted = {
            "observation_id",
            "target_id",
            "asset_id",
            "asset_sha256",
            "source_ref",
            "region_anchor",
            "supersedes_observation_id",
        }
        result: dict[str, Any] = {
            key: value
            for key, value in observation.items()
            if key not in omitted
        }
        result["target"] = target_signature(observation.get("target_id"))
        asset = assets.get(str(observation.get("asset_id") or ""))
        if asset is not None:
            result["asset"] = asset_signature(asset)
            anchor = observation.get("region_anchor")
            try:
                anchor_schema_valid = (
                    isinstance(anchor, Mapping)
                    and set(anchor) == {"kind", "x", "y", "width", "height"}
                    and anchor.get("kind") == "normalized_bbox"
                    and all(
                        isinstance(anchor.get(key), (int, float))
                        and not isinstance(anchor.get(key), bool)
                        for key in ("x", "y", "width", "height")
                    )
                )
                pixel_schema_valid = all(
                    isinstance(asset.get(key), int)
                    and not isinstance(asset.get(key), bool)
                    and int(asset[key]) > 0
                    for key in ("pixel_width", "pixel_height")
                )
                x = float(anchor["x"])
                y = float(anchor["y"])
                width = float(anchor["width"])
                height = float(anchor["height"])
                pixel_width = int(asset["pixel_width"])
                pixel_height = int(asset["pixel_height"])
                finite = all(
                    math.isfinite(item)
                    for item in (x, y, width, height)
                )
                in_bounds = (
                    anchor_schema_valid
                    and pixel_schema_valid
                    and finite
                    and x >= 0.0
                    and y >= 0.0
                    and width > 0.0
                    and height > 0.0
                    and x + width <= 1.0
                    and y + height <= 1.0
                )
                result["anchor_gate"] = {
                    "schema_valid": anchor_schema_valid and pixel_schema_valid,
                    "bbox_in_bounds": in_bounds,
                    "width_meets_minimum": (
                        in_bounds
                        and width * pixel_width >= minimum_anchor_pixels
                    ),
                    "height_meets_minimum": (
                        in_bounds
                        and height * pixel_height >= minimum_anchor_pixels
                    ),
                }
            except (KeyError, TypeError, ValueError, OverflowError):
                result["anchor_gate"] = {
                    "schema_valid": False,
                    "bbox_in_bounds": False,
                    "width_meets_minimum": False,
                    "height_meets_minimum": False,
                }
        elif observation.get("source_ref"):
            result["provenance_group"] = "non_image_source"
        parent_id = str(observation.get("supersedes_observation_id") or "")
        if parent_id:
            result["supersedes"] = (
                {"cycle": True}
                if parent_id in trail or parent_id == identifier
                else observation_signature(parent_id, trail | {identifier})
            )
        normalized = canonical(result)
        observation_cache[identifier] = normalized
        return copy.deepcopy(normalized)

    capture_groups: list[dict[str, Any]] = []
    capture_ids = {
        str(item.get("capture_id") or "")
        for item in assets.values()
        if item.get("capture_id")
    }
    for capture_id in capture_ids:
        group_assets = [
            item
            for item in assets.values()
            if str(item.get("capture_id") or "") == capture_id
        ]
        capture_groups.append(
            {
                "assets": sorted(
                    [asset_signature(item) for item in group_assets],
                    key=stable,
                ),
                "observations": sorted(
                    [
                        observation_signature(identifier)
                        for identifier, item in observations.items()
                        if str(item.get("asset_id") or "")
                        in {str(asset.get("asset_id")) for asset in group_assets}
                    ],
                    key=stable,
                ),
            }
        )

    non_image_groups: list[dict[str, Any]] = []
    source_refs = {
        str(item.get("source_ref") or "")
        for item in observations.values()
        if item.get("source_ref")
    }
    for source_ref in source_refs:
        non_image_groups.append(
            {
                "observations": sorted(
                    [
                        observation_signature(identifier)
                        for identifier, item in observations.items()
                        if str(item.get("source_ref") or "") == source_ref
                    ],
                    key=stable,
                )
            }
        )

    comparisons: list[dict[str, Any]] = []
    for relation in spec.get("comparison_relations") or ():
        if not isinstance(relation, Mapping):
            comparisons.append({"invalid": canonical(relation)})
            continue
        comparisons.append(
            {
                "relation": relation.get("relation"),
                "target": target_signature(relation.get("target_id")),
                "observations": sorted(
                    [
                        observation_signature(identifier)
                        for identifier in relation.get("observation_ids") or ()
                    ],
                    key=stable,
                ),
            }
        )

    return {
        "schema_version": spec.get("schema_version"),
        "observation_scope": spec.get("observation_scope"),
        "source_layer_policy": spec.get("source_layer_policy"),
        "requested_targets": sorted(
            [target_signature(identifier) for identifier in targets],
            key=stable,
        ),
        "capture_groups": sorted(capture_groups, key=stable),
        "non_image_groups": sorted(non_image_groups, key=stable),
        "confirmed_observations": sorted(
            [
                observation_signature(identifier)
                for identifier in spec.get("confirmed_observation_ids") or ()
            ],
            key=stable,
        ),
        "comparison_relations": sorted(comparisons, key=stable),
    }


def _boundary_declares_real_semantics(
    category: str,
    spec: Mapping[str, Any],
    expected: Mapping[str, Any] | None,
    error_pattern: str | None,
) -> bool:
    assets = [item for item in spec.get("assets") or () if isinstance(item, Mapping)]
    observations = [
        item for item in spec.get("observations") or () if isinstance(item, Mapping)
    ]
    if category == "hidden_side":
        assets_by_id = {
            str(asset.get("asset_id")): asset
            for asset in assets
        }
        hidden_observation = any(
            str(item.get("region") or "")
            not in set(
                (assets_by_id.get(str(item.get("asset_id") or "")) or {}).get(
                    "supplied_visible_regions"
                )
                or ()
            )
            for item in observations
            if item.get("asset_id")
        )
        return (
            hidden_observation
            and bool(error_pattern)
            and re.search(
                str(error_pattern),
                "observation region is not visible in asset coverage",
                re.IGNORECASE,
            )
            is not None
        )
    if category == "low_light":
        affected_assets = {
            str(asset.get("asset_id"))
            for asset in assets
            if str((asset.get("quality") or {}).get("lighting") or "")
            in {"low", "backlit", "overexposed", "unknown"}
        }
        return (
            any(
                str(item.get("asset_id")) in affected_assets
                and item.get("visibility") in {"full", "partial"}
                for item in observations
            )
            and int((expected or {}).get("active_observation_count", -1)) == 0
            and any(
                str(item).startswith("observation_resolution:")
                for item in (expected or {}).get("critical_missing") or ()
            )
        )
    if category == "filtered":
        affected_assets = {
            str(asset.get("asset_id"))
            for asset in assets
            if str((asset.get("quality") or {}).get("filtering") or "")
            in {"geometry_altering", "suspected", "unknown"}
        }
        return (
            any(
                str(item.get("asset_id")) in affected_assets
                and item.get("visibility") in {"full", "partial"}
                for item in observations
            )
            and int((expected or {}).get("active_observation_count", -1)) == 0
            and any(
                str(item).startswith("observation_resolution:")
                for item in (expected or {}).get("critical_missing") or ()
            )
        )
    if category == "contradictory":
        groups: dict[tuple[str, str], set[str]] = {}
        asset_capture = {
            str(item.get("asset_id")): str(item.get("capture_id"))
            for item in assets
        }
        for item in observations:
            descriptor = str((item.get("value") or {}).get("descriptor") or "")
            capture = asset_capture.get(str(item.get("asset_id")), "")
            groups.setdefault((str(item.get("target_id")), capture), set()).add(
                descriptor
            )
        return any(len(values) > 1 for values in groups.values()) and int(
            (expected or {}).get("conflict_count", 0)
        ) > 0
    if category == "corrected_to_missing":
        return any(
            item.get("source_type") == "user_correction"
            and item.get("supersedes_observation_id")
            and item.get("visibility") in {"not_visible", "uncertain"}
            for item in observations
        ) and int((expected or {}).get("superseded_observation_count", 0)) > 0
    return False


def _excerpt_is_in_declared_lines(text: str, excerpt: str, anchor: str) -> bool:
    lines = text.splitlines()
    selected: list[str] = []
    for match in re.finditer(r"L(\d+)(?:-L?(\d+))?", anchor):
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if 1 <= start <= end <= len(lines):
            selected.extend(lines[start - 1 : end])
    return bool(selected) and excerpt in "\n".join(selected)


def audit_physiognomy_provider(
    *,
    fixture_path: Path = FIXTURE,
    source_table_path: Path = SOURCE_TABLE,
    annotation_path: Path = ANNOTATIONS,
    oracle_path: Path = ORACLE,
    matrix_path: Path = MATRIX,
    research_root: Path | None = None,
) -> dict[str, Any]:
    """Audit the Task 7M observation provider for completeness.

    ``research_root`` is the release-time fulltext tree for source
    verification.  It is intentionally independent of ``audit_matrix``'s own
    optional research-root wiring so a portable checkout can prove runtime
    readiness without an external corpus, while a release build passes an
    explicit root to close the source-verification gate.  Runtime readiness
    (``provider_ready``) never depends on the external fulltext tree; the
    ``source_verification`` block is ``skipped`` without a root and verified
    when one is provided.
    """
    preflight = provider_preflight_failure(
        system="physiognomy",
        schema_version="mingli-physiognomy-provider-audit-v1",
        provider_class=PhysiognomyProvider,
        expected_mode="observation_driven_ready",
        expected_provider_id=EXPECTED_PROVIDER_ID,
        expected_provider_version=EXPECTED_PROVIDER_VERSION,
    )
    if preflight is not None:
        return preflight
    findings: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            findings.append(message)

    require(
        PhysiognomyProvider.provider_id == EXPECTED_PROVIDER_ID
        and PhysiognomyProvider.provider_version == EXPECTED_PROVIDER_VERSION,
        "Physiognomy provider identity drift",
    )
    require(
        PROVIDER_CAPABILITIES["physiognomy"].mode
        == "observation_driven_ready",
        "Physiognomy provider capability mode is not observation_driven_ready",
    )

    try:
        fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        fixture = {}
        findings.append(f"invalid Physiognomy fixture: {exc}")
    try:
        table = yaml.safe_load(source_table_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        table = {}
        findings.append(f"invalid Physiognomy source table: {exc}")
    try:
        annotations = yaml.safe_load(annotation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        annotations = {}
        findings.append(f"invalid Physiognomy annotation manifest: {exc}")

    oracle_fn = None
    oracle_independent = False
    try:
        oracle_independent = _oracle_imports_are_independent(oracle_path)
    except (OSError, SyntaxError, UnicodeError) as exc:
        findings.append(f"invalid Physiognomy oracle: {exc}")
    if oracle_independent:
        try:
            oracle_fn = _load_oracle(oracle_path)
        except (OSError, RuntimeError, ImportError, AttributeError) as exc:
            findings.append(f"invalid Physiognomy oracle loader: {exc}")

    require(_sha256(source_table_path) == SOURCE_TABLE_SHA256, "Physiognomy source-table artifact hash mismatch")
    require(_sha256(fixture_path) == FIXTURE_SHA256, "Physiognomy fixture artifact hash mismatch")
    require(_sha256(annotation_path) == ANNOTATION_SHA256, "Physiognomy annotation artifact hash mismatch")
    require(_sha256(oracle_path) == ORACLE_SHA256, "Physiognomy independent-oracle artifact hash mismatch")
    require(_sha256(PROVIDER) == PROVIDER_SHA256, "Physiognomy provider artifact hash mismatch")
    require(_sha256(LINEAGE_REGISTRY) == LINEAGE_REGISTRY_SHA256, "Physiognomy source-lineage registry hash mismatch")
    require(table.get("schema_version") == "mingli-physiognomy-source-tables-v1", "unexpected Physiognomy source-table schema")
    require(fixture.get("schema_version") == "mingli-physiognomy-fixtures-v1", "unexpected Physiognomy fixture schema")
    require(fixture.get("source_table_sha256") == SOURCE_TABLE_SHA256, "Physiognomy fixture source-table binding mismatch")
    require(annotations.get("schema_version") == "mingli-physiognomy-annotation-manifest-v1", "unexpected Physiognomy annotation schema")
    require(oracle_independent, "Physiognomy oracle imports production provider code")
    require(callable(oracle_fn), "Physiognomy hash-bound oracle is not executable")
    provider_source = PROVIDER.read_text(encoding="utf-8")
    require("physiognomy_fixture_reference" not in provider_source, "Physiognomy provider imports its fixture oracle")
    require("complete-front-" not in provider_source, "Physiognomy provider contains fixture identities")

    asset_contract = table.get("asset_contract") or {}
    maximum_byte_length = asset_contract.get("maximum_byte_length")
    maximum_pixel_axis = asset_contract.get("maximum_pixel_axis")
    require(
        type(maximum_byte_length) is int
        and 1 <= maximum_byte_length <= 100_000_000
        and type(maximum_pixel_axis) is int
        and 1 <= maximum_pixel_axis <= 100_000,
        "Physiognomy asset size ceilings are unreasonable",
    )

    observation_contract = table.get("observation_contract") or {}
    allowed_regions = set(observation_contract.get("allowed_regions") or ())
    visibility_contract = table.get("visibility_contract") or {}
    framing_ceiling = visibility_contract.get("framing_region_ceiling") or {}
    expected_framing_ceiling = {
        "full_face": allowed_regions,
        "upper_crop": {
            "forehead", "left_eyebrow", "right_eyebrow", "left_eye", "right_eye",
        },
        "lower_crop": {"nose", "mouth", "chin", "jawline"},
        "region_crop": allowed_regions,
        "partial_unknown": allowed_regions,
    }
    framing_ceiling_is_exact = (
        isinstance(framing_ceiling, Mapping)
        and set(visibility_contract.get("framing") or ())
        == set(expected_framing_ceiling)
        and set(framing_ceiling) == set(expected_framing_ceiling)
    )
    if framing_ceiling_is_exact:
        for framing, expected_regions in expected_framing_ceiling.items():
            actual = framing_ceiling.get(framing)
            if (
                not isinstance(actual, list)
                or len(actual) != len(set(actual))
                or set(actual) != expected_regions
            ):
                framing_ceiling_is_exact = False
                break
    require(
        framing_ceiling_is_exact,
        "Physiognomy framing region ceilings are stale",
    )

    privacy = table.get("privacy_contract") or {}
    required_private = {
        "subject_ref", "asset_id", "capture_id", "sha256", "asset_sha256",
        "region_anchor", "observation_id", "observation_ids",
        "confirmed_observation_ids", "supersedes_observation_id", "target_id",
        "source_ref",
    }
    required_tokens = required_private | {
        "normalized_bbox", "face_embedding", "biometric_template",
    }
    require(privacy.get("provider_accepts_raw_media") is False, "Physiognomy privacy contract must reject raw media")
    require(int(privacy.get("opaque_identifier_min_length") or 0) >= 36, "Physiognomy opaque identifiers are too short for exact filtering")
    require(
        privacy.get("opaque_identifier_pattern")
        == r"^(?:sid|aid|cid|tid|oid|rid)-[0-9a-f]{32,64}$",
        "Physiognomy opaque identifier pattern is not namespace-bound and high-entropy",
    )
    require(
        privacy.get("opaque_identifier_namespaces")
        == {
            "subject_ref": "sid", "asset_id": "aid", "capture_id": "cid",
            "target_id": "tid", "observation_id": "oid", "source_ref": "rid",
        },
        "Physiognomy opaque identifier namespace contract is stale",
    )
    require(required_private <= set(privacy.get("private_fact_fields") or ()), "Physiognomy private fact field contract is incomplete")
    require(required_tokens <= set(privacy.get("public_copy_forbidden_tokens") or ()), "Physiognomy public-copy token contract is incomplete")
    require(
        set(privacy.get("public_basis_allowlist") or ())
        == {
            "observation_scope", "normalized_visible_observations", "missing_targets",
            "uncertainties", "observation_conflicts", "cross_capture_variations",
            "source_comparison",
        },
        "Physiognomy public-basis allowlist is stale",
    )
    require(
        privacy.get("region_anchor_public_policy")
        == "semantic_region_only_coordinates_private",
        "Physiognomy region-anchor privacy policy is missing",
    )

    source_packs = {
        str(rule_id).split("#", 1)[0]
        for rule_id in (table.get("source_rule_activation") or {}).get("safe_rule_ids") or ()
    }
    registered_source_packs = 0
    independent_voting_source_packs = 0
    for pack in sorted(source_packs):
        try:
            profile = source_profile(pack)
        except ValueError:
            findings.append(f"Physiognomy source pack has no registered lineage: {pack}")
            continue
        registered_source_packs += 1
        if profile["counts_for_interpretive_independence"]:
            independent_voting_source_packs += 1
    require(
        independent_voting_source_packs == 0,
        "Physiognomy source layers must not become independent votes",
    )

    research_policy = table.get("research_source_policy") or {}
    require(
        research_policy.get("release_contains_normalized_fulltext") is False,
        "Physiognomy release research-source policy must exclude normalized fulltext",
    )
    require(
        research_policy.get("release_contains_hash_pinned_provenance") is True,
        "Physiognomy release research-source policy must retain pinned provenance",
    )
    for profile_id, profile in (table.get("source_profiles") or {}).items():
        require(
            bool(str(profile.get("normalized_sha256") or "")),
            f"Physiognomy research source hash is missing: {profile_id}",
        )
        require(
            bool(str(profile.get("exact_excerpt") or "")),
            f"Physiognomy exact excerpt is missing: {profile_id}",
        )
        pack = str(profile.get("pack") or "")
        release_rules_relative = str(profile.get("release_rules_path") or "")
        release_rules_candidate = ROOT / release_rules_relative
        release_rules_path = release_rules_candidate.resolve()
        expected_release_rules_relative = f"references/books/{pack}/rules.md"
        try:
            release_rules_path.relative_to(ROOT.resolve())
            release_path_is_bounded = True
        except ValueError:
            release_path_is_bounded = False
        require(
            release_path_is_bounded
            and release_rules_relative == expected_release_rules_relative
            and release_rules_path.is_file()
            and not release_rules_candidate.is_symlink(),
            f"Physiognomy release rule path mismatch: {profile_id}",
        )
        if release_rules_path.is_file():
            require(
                _sha256(release_rules_path)
                == profile.get("release_rules_sha256"),
                f"Physiognomy release rule hash mismatch: {profile_id}",
            )

    manifest = fixture.get("asset_manifest") or []
    manifest_asset_hashes: set[str] = set()
    asset_path_by_hash: dict[str, Path] = {}
    asset_root = (ROOT / "references/fixtures/assets/physiognomy").resolve()
    for index, item in enumerate(manifest):
        if not isinstance(item, Mapping):
            findings.append(f"Physiognomy asset manifest row is not an object: {index}")
            continue
        path = (ROOT / str(item.get("path") or "")).resolve()
        try:
            path.relative_to(asset_root)
        except ValueError:
            findings.append(f"Physiognomy asset escapes fixture root: {index}")
            continue
        require(path.is_file() and not path.is_symlink(), f"Physiognomy fixture asset missing or symlinked: {path.name}")
        if not path.is_file():
            continue
        digest = _sha256(path)
        manifest_asset_hashes.add(digest)
        asset_path_by_hash[digest] = path
        require(digest == item.get("sha256"), f"Physiognomy asset hash mismatch: {path.name}")
        require(path.stat().st_size == item.get("byte_length"), f"Physiognomy asset byte length mismatch: {path.name}")
        require(item.get("synthetic") is True and item.get("no_real_person") is True, f"Physiognomy fixture asset is not declared synthetic: {path.name}")
        require(item.get("license") == "CC0-1.0", f"Physiognomy fixture asset license mismatch: {path.name}")
        text = path.read_text(encoding="utf-8")
        require(text.lstrip().startswith("<svg"), f"Physiognomy fixture asset is not SVG: {path.name}")
        require(not re.search(r"<script|foreignObject|(?:href|src)\s*=|data:image", text, re.IGNORECASE), f"Physiognomy fixture SVG contains executable or external content: {path.name}")

    annotation_assets = (annotations.get("assets") or {}) if isinstance(annotations, Mapping) else {}
    complete_cases = fixture.get("complete_cases") or []
    case_ids: set[str] = set()
    scenario_digests: set[str] = set()
    fixture_mismatches = 0
    oracle_mismatches = 0
    annotation_mismatches = 0
    high_risk_activations = 0
    referenced_asset_hashes: set[str] = set()
    qualifying_cases = 0
    provider_calculations = 0
    provider_extensions = 0
    determinism_checks = 0
    deterministic_mismatches = 0
    invented_observations = 0
    observation_fact_key_mismatches = 0

    def provider_request(
        spec: Mapping[str, Any],
        *,
        label: str,
    ) -> ReadingRequest:
        subject_ref = str(spec.get("subject_ref") or "")
        observations = list(spec.get("observations") or ())
        image_supplied = bool(spec.get("assets")) or any(
            isinstance(item, Mapping)
            and item.get("source_type") == "image_transcription"
            for item in observations
        )
        return ReadingRequest(
            query=f"Task 7N Physiognomy provider replay {label}",
            action="new",
            system="physiognomy",
            intent={
                "subject_refs": [subject_ref],
                "calculation_object": "visible_observation",
                "question_dimensions": list(
                    PROVIDER_CAPABILITIES["physiognomy"].dimensions
                ),
                "horizon": {"kind": "instant", "start": None, "end": None},
                "requested_method": "physiognomy",
                "requested_granularity": "region",
                "continuity": {
                    "reading_id": None,
                    "same_subject": False,
                    "same_event": False,
                },
                "facts_present": ["physiognomy_spec"],
                "facts_corrected": [],
                "evidence_questions": ["可见观察对应哪些历史术语及来源边界"],
            },
            chart_data={"physiognomy_spec": copy.deepcopy(dict(spec))},
            image_supplied=image_supplied,
        )

    def live_provider_pair(
        spec: Mapping[str, Any],
        *,
        label: str,
    ) -> dict[str, Any]:
        nonlocal provider_calculations
        nonlocal provider_extensions
        nonlocal determinism_checks
        nonlocal deterministic_mismatches
        nonlocal invented_observations
        nonlocal observation_fact_key_mismatches
        request = provider_request(spec, label=label)
        results = []
        errors: list[Exception] = []
        for _ in range(2):
            provider_calculations += 1
            try:
                results.append(PhysiognomyProvider(ROOT).calculate(request))
            except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                errors.append(exc)
        if errors or len(results) != 2:
            raise ValueError(
                "live provider calculation failed: "
                + " | ".join(str(item) for item in errors)
            )
        first, second = results
        supplied_ids = {
            str(item.get("observation_id") or "")
            for item in spec.get("observations") or ()
            if isinstance(item, Mapping)
        }
        for result in results:
            if (
                result.system != "physiognomy"
                or result.provider_id != PhysiognomyProvider.provider_id
                or result.provider_version != PhysiognomyProvider.provider_version
            ):
                raise ValueError("live provider identity mismatch")
            emitted_ids = {
                str(item)
                for item in result.facts["chart_facts"]["output"][
                    "active_observation_ids"
                ]
            }
            invented_observations += len(emitted_ids - supplied_ids)
            output = result.facts["chart_facts"]["output"]
            expected_fact_keys = sorted(
                {
                    f"{row['feature_kind']}|{row['region']}"
                    for row in output["normalized_visible_observations"]
                }
            )
            if output.get("accepted_observation_fact_keys") != expected_fact_keys:
                observation_fact_key_mismatches += 1
        if (
            first.result_hash != second.result_hash
            or first.input_hash != second.input_hash
            or canonical_digest(first.facts) != canonical_digest(second.facts)
        ):
            deterministic_mismatches += 1
            raise ValueError("live provider calculation is nondeterministic")
        determinism_checks += 1

        dimensions = tuple(
            PROVIDER_CAPABILITIES["physiognomy"].dimensions
        )
        horizon = {"kind": "instant"}
        extended = []
        for result in results:
            provider_extensions += 1
            extended.append(
                PhysiognomyProvider(ROOT).extend(result, dimensions, horizon)
            )
        first_extension = extended[0].fact_extension
        second_extension = extended[1].fact_extension
        expected_status = (
            "partial"
            if first.facts["chart_facts"]["output"]["critical_missing"]
            else "complete"
        )
        if (
            first_extension is None
            or second_extension is None
            or first_extension.status != expected_status
            or second_extension.status != expected_status
            or first_extension.extension_digest
            != second_extension.extension_digest
            or canonical_digest(first_extension.facts)
            != canonical_digest(second_extension.facts)
        ):
            deterministic_mismatches += 1
            raise ValueError("live provider extension is incomplete or nondeterministic")
        determinism_checks += 1
        return first.facts["chart_facts"]

    for index, case in enumerate(complete_cases):
        if not isinstance(case, Mapping):
            findings.append(f"Physiognomy complete fixture is not an object: {index}")
            continue
        case_id = str(case.get("case_id") or "")
        case_finding_start = len(findings)
        require(bool(case_id) and case_id not in case_ids, f"Physiognomy fixture id is empty or duplicate: {case_id}")
        case_ids.add(case_id)
        spec = case.get("input")
        expected = case.get("expected")
        if not isinstance(spec, Mapping) or not isinstance(expected, Mapping):
            findings.append(f"Physiognomy fixture lacks direct input/expected: {case_id}")
            continue
        scenario_digests.add(canonical_digest(_semantic_scenario_payload(spec)))
        try:
            facts = live_provider_pair(spec, label=case_id)
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            fixture_mismatches += 1
            findings.append(f"Physiognomy fixture provider failure {case_id}: {exc}")
            continue
        provider_projection = _projection(facts)
        oracle_result: dict[str, Any] | None = None
        if callable(oracle_fn):
            try:
                oracle_result = oracle_fn(spec)
            except Exception as exc:  # audit must report the executed oracle path
                oracle_mismatches += 1
                findings.append(
                    f"Physiognomy independent oracle failure {case_id}: {exc}"
                )
        if provider_projection != dict(expected):
            fixture_mismatches += 1
            findings.append(f"Physiognomy fixture expected mismatch: {case_id}")
        if oracle_result is None or oracle_result != dict(expected) or oracle_result != provider_projection:
            oracle_mismatches += 1
            findings.append(f"Physiognomy independent oracle mismatch: {case_id}")
        unsafe = set(facts["output"]["active_source_rule_ids"]) - set(physiognomy.SAFE_SOURCE_RULE_IDS)
        if unsafe:
            high_risk_activations += len(unsafe)
            findings.append(f"Physiognomy high-risk source activation: {case_id}")
        assets = {
            str(row.get("asset_id")): row
            for row in spec.get("assets") or ()
            if isinstance(row, Mapping)
        }
        active_observation_ids = {
            str(item)
            for item in facts["output"]["active_observation_ids"]
        }
        for observation in spec.get("observations") or ():
            if not isinstance(observation, Mapping) or not observation.get("asset_id"):
                continue
            asset = assets.get(str(observation["asset_id"]))
            if asset is not None and asset.get("sha256"):
                referenced_asset_hashes.add(str(asset["sha256"]))
            path = asset_path_by_hash.get(str((asset or {}).get("sha256")))
            regions = (
                (annotation_assets.get(path.name) or {}).get("regions")
                if path is not None and isinstance(annotation_assets, Mapping)
                else {}
            )
            descriptors = (
                (annotation_assets.get(path.name) or {}).get("descriptors")
                if path is not None and isinstance(annotation_assets, Mapping)
                else {}
            )
            annotation = regions.get(observation.get("region")) if isinstance(regions, Mapping) else None
            if not isinstance(annotation, list) or not _within(observation.get("region_anchor") or {}, annotation):
                annotation_mismatches += 1
                findings.append(f"Physiognomy annotation binding mismatch: {case_id}")
            if (
                str(observation.get("observation_id"))
                in active_observation_ids
                and observation.get("visibility") in {"full", "partial"}
            ):
                descriptor = str((observation.get("value") or {}).get("descriptor") or "")
                allowed_descriptors = (
                    descriptors.get(observation.get("region"))
                    if isinstance(descriptors, Mapping)
                    else None
                )
                if (
                    not isinstance(allowed_descriptors, list)
                    or descriptor not in allowed_descriptors
                ):
                    annotation_mismatches += 1
                    findings.append(
                        "Physiognomy descriptor annotation binding mismatch: "
                        + case_id
                    )

        if len(findings) == case_finding_start:
            qualifying_cases += 1

    require(len(complete_cases) >= 20, "Physiognomy requires at least 20 complete fixtures")
    require(len(scenario_digests) == len(complete_cases), "Physiognomy complete fixtures must have unique scenario digests")
    require(
        len(referenced_asset_hashes) >= 8,
        "Physiognomy complete fixtures require at least eight referenced assets",
    )
    require(
        qualifying_cases >= 20,
        "Physiognomy live provider replay requires at least 20 qualifying cases",
    )
    require(
        invented_observations == 0,
        "Physiognomy live provider invented observations absent from supplied input",
    )
    require(
        observation_fact_key_mismatches == 0,
        "Physiognomy accepted observation fact keys are not visibility-gated",
    )

    boundary_cases = fixture.get("boundary_cases") or []
    boundary_categories: set[str] = set()
    boundary_mismatches = 0
    for index, case in enumerate(boundary_cases):
        if not isinstance(case, Mapping):
            boundary_mismatches += 1
            findings.append(f"Physiognomy boundary fixture is not an object: {index}")
            continue
        case_id = str(case.get("case_id") or "")
        category = str(case.get("category") or "")
        boundary_categories.add(category)
        spec = case.get("input")
        if not isinstance(spec, Mapping):
            boundary_mismatches += 1
            findings.append(f"Physiognomy boundary fixture lacks input: {case_id}")
            continue
        error_pattern = case.get("expected_error_regex")
        expected = case.get("expected")
        if not _boundary_declares_real_semantics(
            category,
            spec,
            expected if isinstance(expected, Mapping) else None,
            error_pattern if isinstance(error_pattern, str) else None,
        ):
            boundary_mismatches += 1
            findings.append(
                f"Physiognomy boundary label lacks declared input semantics: {case_id}"
            )
        if isinstance(error_pattern, str):
            error_messages: list[str] = []
            request = provider_request(spec, label=case_id)
            for _ in range(2):
                provider_calculations += 1
                try:
                    PhysiognomyProvider(ROOT).calculate(request)
                except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                    error_messages.append(str(exc))
            if (
                len(error_messages) != 2
                or error_messages[0] != error_messages[1]
                or re.search(error_pattern, error_messages[0], re.IGNORECASE)
                is None
            ):
                boundary_mismatches += 1
                findings.append(f"Physiognomy boundary error mismatch: {case_id}")
            else:
                determinism_checks += 1
            if callable(oracle_fn):
                try:
                    oracle_fn(spec)
                except Exception as exc:  # independent boundary execution
                    if re.search(error_pattern, str(exc), re.IGNORECASE) is None:
                        boundary_mismatches += 1
                        oracle_mismatches += 1
                        findings.append(
                            f"Physiognomy boundary oracle error mismatch {case_id}: {exc}"
                        )
                else:
                    boundary_mismatches += 1
                    oracle_mismatches += 1
                    findings.append(
                        f"Physiognomy boundary oracle failed to reject: {case_id}"
                    )
            continue
        if not isinstance(expected, Mapping):
            boundary_mismatches += 1
            findings.append(f"Physiognomy boundary fixture lacks expected projection: {case_id}")
            continue
        try:
            provider_projection = _projection(
                live_provider_pair(spec, label=case_id)
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            boundary_mismatches += 1
            findings.append(f"Physiognomy boundary provider failure {case_id}: {exc}")
            continue
        oracle_result = None
        if callable(oracle_fn):
            try:
                oracle_result = oracle_fn(spec)
            except Exception as exc:
                oracle_mismatches += 1
                findings.append(
                    f"Physiognomy boundary oracle failure {case_id}: {exc}"
                )
        if provider_projection != dict(expected) or oracle_result != dict(expected):
            boundary_mismatches += 1
            findings.append(f"Physiognomy boundary projection mismatch: {case_id}")
    required_boundary_categories = {
        "hidden_side",
        "low_light",
        "filtered",
        "contradictory",
        "corrected_to_missing",
    }
    require(
        required_boundary_categories <= boundary_categories,
        "Physiognomy boundary fixture categories are incomplete",
    )
    reported_boundary_categories = set(boundary_categories)
    if complete_cases:
        reported_boundary_categories.add("complete")
    if boundary_categories & {"hidden_side", "corrected_to_missing"}:
        reported_boundary_categories.add("missing")
    if "contradictory" in boundary_categories:
        reported_boundary_categories.add("conflict")
    if boundary_categories & {"low_light", "filtered"}:
        reported_boundary_categories.add("low_quality")
    if "corrected_to_missing" in boundary_categories:
        reported_boundary_categories.add("correction")

    evidence_rules = [rule for rule in production_evidence_rules() if rule.system == "physiognomy"]
    unpredicated = 0
    for rule in evidence_rules:
        predicates = [item.to_dict() for item in rule.required_fact_predicates]
        expected_predicates = [
            {"path_suffix": "/fact_layer_status", "operator": "eq", "value": "observation_driven_physiognomy_facts"},
            {"path_suffix": "/active_source_rule_ids", "operator": "descendant_eq", "value": rule.rule_id},
        ]
        if not all(predicate in predicates for predicate in expected_predicates):
            unpredicated += 1
    expected_corpus_counts = {
        "physiognomy/bingjian": 31,
        "physiognomy/liuzhuang-xiangfa": 5,
        "physiognomy/mayi-shenxiang": 5,
        "physiognomy/shenxiang-quanbian": 49,
    }
    actual_corpus_counts = {
        pack: sum(rule.source_pack == pack for rule in evidence_rules)
        for pack in expected_corpus_counts
    }
    require(
        len(evidence_rules) == 90 and actual_corpus_counts == expected_corpus_counts,
        "Physiognomy evidence index does not match the frozen 90-rule corpus",
    )
    require(unpredicated == 0, "Physiognomy evidence rules lack exact provider predicates")

    activation = table.get("source_rule_activation") or {}
    safe_rule_ids = tuple(str(item) for item in activation.get("safe_rule_ids") or ())
    expected_safe_rule_ids = {
        "physiognomy/liuzhuang-xiangfa#LZ-R01",
        "physiognomy/liuzhuang-xiangfa#LZ-R02",
        "physiognomy/liuzhuang-xiangfa#LZ-R03",
        "physiognomy/liuzhuang-xiangfa#LZ-R05",
        "physiognomy/mayi-shenxiang#MR-01",
        "physiognomy/mayi-shenxiang#MR-02",
        "physiognomy/shenxiang-quanbian#SR-01-03",
        "physiognomy/shenxiang-quanbian#SR-02-04",
    }
    if set(safe_rule_ids) != expected_safe_rule_ids:
        safe_rule_role_mismatches = 1
        findings.append("Physiognomy safe rule allowlist differs from frozen eight IDs")
    else:
        safe_rule_role_mismatches = 0
    declared_roles = activation.get("evidence_roles") or {}
    required_roles = {"methodology_rule", "terminology_only", "edition_boundary"}
    if set(declared_roles) != required_roles:
        safe_rule_role_mismatches += 1
        findings.append("Physiognomy safe evidence-role declarations are incomplete")
    declared_role_by_rule: dict[str, str] = {}
    for role, rule_ids in declared_roles.items():
        if not isinstance(rule_ids, list):
            safe_rule_role_mismatches += 1
            findings.append(f"Physiognomy evidence role is not a list: {role}")
            continue
        for rule_id in rule_ids:
            identifier = str(rule_id)
            if identifier in declared_role_by_rule:
                safe_rule_role_mismatches += 1
                findings.append(
                    f"Physiognomy safe rule has duplicate role declarations: {identifier}"
                )
            declared_role_by_rule[identifier] = str(role)
    if set(declared_role_by_rule) != set(safe_rule_ids):
        safe_rule_role_mismatches += 1
        findings.append("Physiognomy safe rule roles do not cover the exact allowlist")
    evidence_by_id = {rule.rule_id: rule for rule in evidence_rules}
    for rule_id in safe_rule_ids:
        rule = evidence_by_id.get(rule_id)
        if rule is None or rule.evidence_role != declared_role_by_rule.get(rule_id):
            safe_rule_role_mismatches += 1
            findings.append(f"Physiognomy safe rule role mismatch: {rule_id}")
    activation_ids = {
        str(rule_id)
        for key in (
            "baseline_methodology",
            "any_active_visible_region",
            "active_capture_color",
        )
        for rule_id in activation.get(key) or ()
    }
    if activation_ids != expected_safe_rule_ids:
        safe_rule_role_mismatches += 1
        findings.append(
            "Physiognomy activation groups do not cover the frozen safe rules exactly"
        )
    role_counts = {
        role: sum(rule.evidence_role == role for rule in evidence_rules)
        for role in {
            "verdict_prohibited",
            "terminology_only",
            "methodology_rule",
            "edition_boundary",
        }
    }
    if role_counts != {
        "verdict_prohibited": 82,
        "terminology_only": 5,
        "methodology_rule": 2,
        "edition_boundary": 1,
    }:
        safe_rule_role_mismatches += 1
        findings.append("Physiognomy evidence-role distribution is not frozen")

    expected_priority = tuple(
        str(profile.get("pack"))
        for source_layer in (table.get("source_layer_contract") or {}).get(
            "priority_order"
        )
        or ()
        for profile in (table.get("source_profiles") or {}).values()
        if isinstance(profile, Mapping)
        and str(profile.get("source_layer") or "") == str(source_layer)
    )
    source_priority_mismatches = int(
        expected_priority != tuple(PhysiognomyProvider.SOURCE_PRIORITY)
    )
    if complete_cases and isinstance(complete_cases[0], Mapping):
        first_spec = complete_cases[0].get("input")
        if isinstance(first_spec, Mapping):
            try:
                provider_priority = tuple(
                    str(item.get("pack"))
                    for item in physiognomy.build_fact_layer(first_spec)["output"][
                        "source_layers"
                    ]
                )
            except (KeyError, TypeError, ValueError, RuntimeError):
                provider_priority = ()
            if provider_priority != expected_priority:
                source_priority_mismatches += 1
    if source_priority_mismatches:
        findings.append("Physiognomy source-plan priority differs from source table")
    require(
        source_packs
        == {
            "physiognomy/liuzhuang-xiangfa",
            "physiognomy/shenxiang-quanbian",
            "physiognomy/mayi-shenxiang",
        },
        "Physiognomy safe source-pack set is not exact",
    )

    matrix_payload = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    resolved_research_root = (
        research_root.resolve()
        if research_root is not None
        else audit_algorithm_sources._research_root(matrix_payload, ROOT)
    )
    # Runtime matrix audit stays research-root-free: its structural findings
    # (schema, dependencies, release-located sources) are runtime readiness
    # properties.  The fulltext-tree checks run only inside the release-time
    # ``source_verification`` gate, so an explicit research root can never
    # flip ``provider_ready``.
    algorithm_report = audit_algorithm_sources.audit_matrix(
        matrix_payload,
        root=ROOT,
        systems=("physiognomy",),
    )
    findings.extend(
        f"algorithm source audit: {item}"
        for item in algorithm_report["findings"]
    )
    source_verification: dict[str, Any] = {
        "status": "skipped",
        "detail": "no explicit research source root; fulltext verification is a release-time gate, not a runtime readiness condition",
    }
    if resolved_research_root is not None:
        # Release-time source verification.  The ``source_report`` block
        # carries every ``audit_matrix`` finding, including the fulltext-tree
        # checks that only run against an explicit research root.  Runtime
        # readiness (``provider_ready``) stays independent of the external
        # corpus: the provider, digests, oracle, and annotation checks above
        # never touch the fulltext tree.
        source_report = audit_algorithm_sources.audit_matrix(
            matrix_payload,
            root=ROOT,
            systems=("physiognomy",),
            research_root=resolved_research_root,
        )
        source_verification["source_report"] = {
            "ok": bool(source_report.get("ok")),
            "research_sources_verified": bool(
                source_report.get("research_sources_verified")
            ),
            "dependency_count": int(source_report.get("dependency_count") or 0),
            "findings": list(source_report.get("findings") or ()),
        }
        if source_report.get("ok") and not source_report.get("findings"):
            source_verification["ok"] = True
            source_verification["status"] = "verified"
        else:
            source_verification["ok"] = False
            source_verification["status"] = "failed"
            source_verification["findings"] = list(
                source_report.get("findings") or ()
            )

    algorithm_samples_executed = 0
    algorithm_sample_mismatches = 0
    sample_contract = table.get("algorithm_sample_contract") or {}
    sample_path = (ROOT / str(sample_contract.get("path") or "")).resolve()
    try:
        sample_path.relative_to(ROOT.resolve())
    except ValueError:
        findings.append("Physiognomy algorithm sample artifact escapes release root")
        sample_payload: dict[str, Any] = {}
    else:
        try:
            sample_payload = yaml.safe_load(sample_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            sample_payload = {}
            findings.append(f"invalid Physiognomy algorithm sample artifact: {exc}")
    require(
        sample_path.is_file()
        and _sha256(sample_path) == sample_contract.get("sha256"),
        "Physiognomy algorithm sample artifact hash mismatch",
    )
    require(
        sample_payload.get("schema_version")
        == "mingli-algorithm-source-samples-v1",
        "unexpected Physiognomy algorithm sample schema",
    )
    bindings = sample_contract.get("bindings") or {}
    expected_sample_ids = {
        "physiognomy-region-quality",
        "physiognomy-no-invisible-feature",
        "physiognomy-user-correction",
    }
    require(
        isinstance(bindings, Mapping) and set(bindings) == expected_sample_ids,
        "Physiognomy algorithm sample bindings are incomplete",
    )
    matrix_samples = {
        str((dependency.get("independent_test_sample") or {}).get("id") or ""):
        dependency.get("independent_test_sample") or {}
        for dependency in ((matrix_payload.get("providers") or {}).get("physiognomy") or {}).get("dependencies") or ()
        if isinstance(dependency, Mapping)
    }
    sample_cases = sample_payload.get("cases") or {}
    for sample_id in sorted(expected_sample_ids):
        mismatch_messages: list[str] = []
        binding = bindings.get(sample_id) if isinstance(bindings, Mapping) else None
        sample = sample_cases.get(sample_id) if isinstance(sample_cases, Mapping) else None
        matrix_sample = matrix_samples.get(sample_id)
        if not isinstance(binding, Mapping) or not isinstance(sample, Mapping):
            mismatch_messages.append("missing hash-bound sample or fixture binding")
            section_name = ""
            fixture_case_id = ""
        else:
            section_name = str(binding.get("fixture_section") or "")
            fixture_case_id = str(binding.get("fixture_case_id") or "")
        section = fixture.get(section_name) if section_name else None
        bound_case = next(
            (
                item
                for item in section or ()
                if isinstance(item, Mapping)
                and str(item.get("case_id") or "") == fixture_case_id
            ),
            None,
        ) if isinstance(section, list) else None
        expected_input = {
            "provider_fixture_section": section_name,
            "provider_fixture_case_id": fixture_case_id,
        }
        if not isinstance(sample, Mapping) or sample.get("input") != expected_input:
            mismatch_messages.append("hash-bound sample input differs from binding")
        if not isinstance(bound_case, Mapping):
            mismatch_messages.append("bound provider fixture case is missing")
            expected_sample = None
        elif isinstance(bound_case.get("expected_error_regex"), str):
            expected_sample = {
                "expected_error_regex": bound_case["expected_error_regex"]
            }
        else:
            expected_sample = bound_case.get("expected")
        if not isinstance(sample, Mapping) or sample.get("expected") != expected_sample:
            mismatch_messages.append("hash-bound sample expected differs from provider fixture")
        if (
            not isinstance(matrix_sample, Mapping)
            or matrix_sample.get("source_path") != sample_contract.get("path")
            or matrix_sample.get("source_anchor") != sample_id
            or matrix_sample.get("source")
            != f"{sample_contract.get('path')}::{sample_id}"
            or matrix_sample.get("input") != (sample or {}).get("input")
            or matrix_sample.get("expected") != (sample or {}).get("expected")
        ):
            mismatch_messages.append("matrix sample binding mismatch")

        if isinstance(bound_case, Mapping) and callable(oracle_fn):
            algorithm_samples_executed += 1
            spec = bound_case.get("input")
            error_pattern = bound_case.get("expected_error_regex")
            expected_projection = bound_case.get("expected")
            if not isinstance(spec, Mapping):
                mismatch_messages.append("bound sample input is not an object")
            elif isinstance(error_pattern, str):
                for label, operation in (
                    ("provider", lambda: physiognomy.build_fact_layer(spec)),
                    ("oracle", lambda: oracle_fn(spec)),
                ):
                    try:
                        operation()
                    except Exception as exc:
                        if re.search(error_pattern, str(exc), re.IGNORECASE) is None:
                            mismatch_messages.append(
                                f"{label} sample error mismatch: {exc}"
                            )
                    else:
                        mismatch_messages.append(f"{label} sample failed to reject")
            elif isinstance(expected_projection, Mapping):
                try:
                    provider_result = _projection(
                        physiognomy.build_fact_layer(spec)
                    )
                    oracle_result = oracle_fn(spec)
                except Exception as exc:
                    mismatch_messages.append(f"sample execution failed: {exc}")
                else:
                    if (
                        provider_result != dict(expected_projection)
                        or oracle_result != dict(expected_projection)
                    ):
                        mismatch_messages.append("executed sample projection mismatch")
        for message in dict.fromkeys(mismatch_messages):
            findings.append(f"Physiognomy algorithm sample {sample_id}: {message}")
        if mismatch_messages:
            algorithm_sample_mismatches += 1

    counts = {
        "qualifying_cases": qualifying_cases,
        "route_owned_cases": len(complete_cases),
        "provider_calculations": provider_calculations,
        "provider_extensions": provider_extensions,
        "determinism_checks": determinism_checks,
        "deterministic_mismatches": deterministic_mismatches,
        "invented_observations": invented_observations,
        "observation_fact_key_mismatches": observation_fact_key_mismatches,
        "complete_fixtures": len(complete_cases),
        "unique_scenarios": len(scenario_digests),
        "unique_assets": len(referenced_asset_hashes),
        "fixture_mismatches": fixture_mismatches,
        "oracle_mismatches": oracle_mismatches,
        "asset_mismatches": sum(
            1 for item in findings if "asset" in item.lower() and "mismatch" in item.lower()
        ),
        "annotation_mismatches": annotation_mismatches,
        "high_risk_activations": high_risk_activations,
        "evidence_rules": len(evidence_rules),
        "evidence_rules_without_exact_predicates": unpredicated,
        "algorithm_dependencies": int(algorithm_report["dependency_count"]),
        "registered_source_packs": registered_source_packs,
        "independent_voting_source_packs": independent_voting_source_packs,
        "boundary_fixtures": len(boundary_cases),
        "boundary_case_count": len(boundary_cases),
        "boundary_mismatches": boundary_mismatches,
        "algorithm_samples_executed": algorithm_samples_executed,
        "algorithm_sample_mismatches": algorithm_sample_mismatches,
        "safe_rule_role_mismatches": safe_rule_role_mismatches,
        "source_priority_mismatches": source_priority_mismatches,
    }
    return {
        "schema_version": "mingli-physiognomy-provider-audit-v1",
        "system": "physiognomy",
        "provider_ready": not findings,
        "status": "pass" if not findings else "fail",
        "provider": {
            "provider_id": PhysiognomyProvider.provider_id,
            "provider_version": PhysiognomyProvider.provider_version,
            "capability_mode": PROVIDER_CAPABILITIES["physiognomy"].mode,
        },
        "route_owned_case_ids": [
            str(case.get("case_id") or "") for case in complete_cases
        ],
        "source_table_sha256": _sha256(source_table_path),
        "fixture": {
            "path": str(fixture_path),
            "sha256": _sha256(fixture_path),
            "expected_sha256": FIXTURE_SHA256,
        },
        "fixture_sha256": _sha256(fixture_path),
        "annotation_sha256": _sha256(annotation_path),
        "oracle_sha256": _sha256(oracle_path),
        "provider_sha256": _sha256(PROVIDER),
        "source_lineage_registry_sha256": _sha256(LINEAGE_REGISTRY),
        "counts": counts,
        "boundary_categories": sorted(reported_boundary_categories),
        "source_verification": source_verification,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--source-table", type=Path, default=SOURCE_TABLE)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    args = parser.parse_args(argv)
    report = audit_physiognomy_provider(
        fixture_path=args.fixture,
        source_table_path=args.source_table,
        annotation_path=args.annotations,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
