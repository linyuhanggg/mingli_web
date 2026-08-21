#!/usr/bin/env python3
"""Provider-independent reference projection for Task 7M fixture inputs.

This oracle intentionally uses only Python's standard library and a small,
frozen restatement of the fixture contract.  It neither imports production
provider code nor reads fixture expected values.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DEFAULT_RULES = (
    "physiognomy/liuzhuang-xiangfa#LZ-R01",
    "physiognomy/liuzhuang-xiangfa#LZ-R02",
    "physiognomy/liuzhuang-xiangfa#LZ-R05",
    "physiognomy/mayi-shenxiang#MR-01",
    "physiognomy/mayi-shenxiang#MR-02",
    "physiognomy/shenxiang-quanbian#SR-02-04",
)
COLOR_RULES = (
    "physiognomy/liuzhuang-xiangfa#LZ-R03",
    "physiognomy/shenxiang-quanbian#SR-01-03",
)
MORPHOLOGY_BLOCKS = {
    "lighting": {"low", "backlit", "overexposed", "unknown"},
    "focus": {"blurred", "unknown"},
    "resolution": {"low", "unknown"},
    "filtering": {"geometry_altering", "suspected", "unknown"},
}


def _eligible(row: Mapping[str, Any], assets: Mapping[str, Mapping[str, Any]]) -> bool:
    if row.get("visibility") not in {"full", "partial"}:
        return False
    if float(row.get("occlusion", 1.0)) > 0.5:
        return False
    if float(row.get("uncertainty", 1.0)) > 0.5:
        return False
    asset_id = row.get("asset_id")
    if not asset_id:
        return True
    quality = assets[str(asset_id)]["quality"]
    if row.get("feature_kind") == "capture_color":
        return (
            row.get("region") == "complexion"
            and quality.get("lighting") == "even"
            and quality.get("camera_angle") in {"frontal", "three_quarter"}
            and quality.get("focus") == "sharp"
            and quality.get("resolution") in {"high", "adequate"}
            and quality.get("filtering") == "none"
            and quality.get("color_fidelity") == "calibrated"
        )
    return all(quality.get(field) not in blocked for field, blocked in MORPHOLOGY_BLOCKS.items())


def reference_projection(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Return the frozen stable projection for one complete fixture input."""

    assets = {
        str(row["asset_id"]): row
        for row in spec.get("assets") or ()
        if isinstance(row, Mapping)
    }
    observations = [
        dict(row)
        for row in spec.get("observations") or ()
        if isinstance(row, Mapping)
    ]
    for row in observations:
        asset_id = str(row.get("asset_id") or "")
        if not asset_id:
            continue
        asset = assets.get(asset_id)
        if asset is None or row.get("region") not in set(
            asset.get("supplied_visible_regions") or ()
        ):
            raise ValueError(
                "observation region is not visible in asset coverage"
            )
    superseded = {
        str(row["supersedes_observation_id"])
        for row in observations
        if row.get("supersedes_observation_id")
    }
    revision_leaves = [
        row
        for row in observations
        if str(row.get("observation_id")) not in superseded
    ]
    leaves = [row for row in revision_leaves if _eligible(row, assets)]
    confirmed = set(str(item) for item in spec.get("confirmed_observation_ids") or ())
    all_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in revision_leaves:
        capture = str(row.get("asset_id") or row.get("source_ref"))
        all_groups.setdefault((str(row["target_id"]), capture), []).append(row)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in leaves:
        capture = str(row.get("asset_id") or row.get("source_ref"))
        groups.setdefault((str(row["target_id"]), capture), []).append(row)
    conflicts: list[tuple[str, str]] = []
    rejected: set[str] = set()
    unresolved_targets: set[str] = set()
    for key, rows in all_groups.items():
        visible = [
            row for row in rows if row.get("visibility") in {"full", "partial"}
        ]
        unavailable = [
            row
            for row in rows
            if row.get("visibility") in {"not_visible", "uncertain"}
        ]
        if not visible or not unavailable:
            continue
        conflicts.append(key)
        selected = [
            row for row in rows if str(row.get("observation_id")) in confirmed
        ]
        if len(selected) == 1:
            rejected.update(
                str(row["observation_id"])
                for row in rows
                if row is not selected[0]
            )
        else:
            unresolved_targets.add(key[0])
            rejected.update(str(row["observation_id"]) for row in rows)
    for key, rows in groups.items():
        descriptors = {
            str((row.get("value") or {}).get("descriptor")) for row in rows
        }
        if len(descriptors) <= 1:
            continue
        conflicts.append(key)
        selected = [row for row in rows if str(row.get("observation_id")) in confirmed]
        if len(selected) == 1:
            rejected.update(
                str(row["observation_id"])
                for row in rows
                if row is not selected[0]
            )
        else:
            unresolved_targets.add(key[0])
            rejected.update(str(row["observation_id"]) for row in rows)
    active = [row for row in leaves if str(row["observation_id"]) not in rejected]

    by_target: dict[str, list[dict[str, Any]]] = {}
    for row in active:
        by_target.setdefault(str(row["target_id"]), []).append(row)
    cross_capture = 0
    for rows in by_target.values():
        captures = {str(row.get("asset_id") or row.get("source_ref")) for row in rows}
        descriptors = {str((row.get("value") or {}).get("descriptor")) for row in rows}
        if len(captures) > 1 and len(descriptors) > 1:
            cross_capture += 1

    active_target_ids = {str(row["target_id"]) for row in active}
    critical_missing: list[str] = []
    for target in spec.get("requested_targets") or ():
        if not isinstance(target, Mapping) or not target.get("required"):
            continue
        target_id = str(target["target_id"])
        if target_id in active_target_ids and target_id not in unresolved_targets:
            continue
        target_rows = [
            row
            for row in revision_leaves
            if (
                str(row.get("target_id")) == target_id
                and str(row.get("observation_id")) not in rejected
            )
        ]
        if target_id in unresolved_targets:
            prefix = "observation_resolution"
        elif not target_rows or all(
            row.get("visibility") == "not_visible" for row in target_rows
        ):
            prefix = "visible_observation"
        else:
            prefix = "observation_resolution"
        critical_missing.append(f"{prefix}:{target_id}")

    rules: list[str] = []
    if active:
        rules.extend(DEFAULT_RULES)
    if any(row.get("feature_kind") == "capture_color" for row in active):
        rules.extend(COLOR_RULES)
    return {
        "critical_missing": critical_missing,
        "active_observation_count": len(active),
        "conflict_count": len(conflicts),
        "cross_capture_variation_count": cross_capture,
        "superseded_observation_count": len(superseded),
        "active_source_rule_ids": sorted(set(rules)),
        "active_regions": sorted(str(row["region"]) for row in active),
        "active_descriptors": sorted(
            str((row.get("value") or {}).get("descriptor")) for row in active
        ),
    }


__all__ = ["reference_projection"]
