"""Provider-independent Task 7L fixture oracle.

This evaluator deliberately duplicates the small frozen mechanical contract.  It
must not import the production Fengshui provider or its source table.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


MOUNTAINS = tuple("子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥壬")
TRIGRAMS = (
    "坎", "坎", "艮", "艮", "艮", "震", "震", "震",
    "巽", "巽", "巽", "离", "离", "离", "坤", "坤",
    "坤", "兑", "兑", "兑", "乾", "乾", "乾", "坎",
)
EAST_GROUP = frozenset({"坎", "离", "震", "巽"})
FORM_PACKS = {
    "residential": frozenset(
        {"fengshui/huangdi-zhaijing", "fengshui/yangzhai-shishu"}
    ),
    "site_general": frozenset(
        {
            "fengshui/zangshu",
            "fengshui/hanlong-jing",
            "fengshui/yilong-jing",
            "fengshui/xuexin-fu",
        }
    ),
    "burial_cultural_study": frozenset(
        {
            "fengshui/zangshu",
            "fengshui/hanlong-jing",
            "fengshui/yilong-jing",
            "fengshui/xuexin-fu",
        }
    ),
}
OBSERVATION_RULES = {
    ("road", "axis_toward_entrance"): (
        "fengshui/yangzhai-shishu#YZS-R003",
    ),
    ("water", "observed_water"): (
        "fengshui/huangdi-zhaijing#HDZJ-R006",
        "fengshui/yangzhai-shishu#YZS-R001",
    ),
    ("water", "water_boundary_and_wind_shelter_observed"): (
        "fengshui/zangshu#R-02",
    ),
    ("water", "water_mouth_and_hall_observed"): (
        "fengshui/xuexin-fu#XXF-R01",
    ),
    ("water", "interlocking_water_pattern"): (
        "fengshui/xuexin-fu#XXF-R04",
    ),
    ("terrain", "highland_plainland_classification"): (
        "fengshui/hanlong-jing#R-01",
    ),
    ("terrain", "sheltered_open_hall"): (
        "fengshui/yilong-jing#R-05",
        "fengshui/xuexin-fu#XXF-R01",
    ),
    ("terrain", "water_boundary_and_wind_shelter_observed"): (
        "fengshui/zangshu#R-02",
    ),
    ("entrance", "observed_entrance"): (
        "fengshui/yangzhai-shishu#YZS-R014",
    ),
    ("layout", "observed_layout"): (
        "fengshui/huangdi-zhaijing#HDZJ-R006",
        "fengshui/yangzhai-shishu#YZS-R014",
    ),
}


def _mountain(degrees: Any) -> tuple[str, str]:
    if isinstance(degrees, bool) or not isinstance(degrees, (int, float)):
        raise TypeError("fixture degree must be numeric")
    value = float(degrees)
    if not math.isfinite(value) or not 0.0 <= value < 360.0:
        raise ValueError("fixture degree outside [0, 360)")
    index = int(math.floor(((value + 7.5) % 360.0) / 15.0))
    return MOUNTAINS[index], TRIGRAMS[index]


def _eligible(observation: Mapping[str, Any]) -> bool:
    quality = observation["quality"]
    if quality["readability"] in {"low", "unreadable"}:
        return False
    if quality["lighting"] == "low" or float(quality["occlusion"]) >= 0.5:
        return False
    if float(observation["uncertainty"]) > 0.5:
        return False
    if observation["source_type"] == "image_transcription" and observation[
        "kind"
    ] in {"road", "entrance", "layout", "opening"}:
        return quality["scale"] in {"known", "approximate"} and quality[
            "viewpoint"
        ] in {"top_down", "orthogonal", "aerial"}
    return True


def evaluate_complete_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Return the frozen projection used by complete observation fixtures."""

    scope = str(spec["property_scope"])
    requested = list(spec["requested_form_variables"])
    accepted = [row for row in spec["observations"] if _eligible(row)]
    accepted_kinds = {str(row["kind"]) for row in accepted}
    form_status = (
        "complete"
        if set(requested) <= accepted_kinds and len(accepted) == len(spec["observations"])
        else "partial"
    )

    active: set[str] = set()
    allowed_packs = FORM_PACKS[scope]
    for row in accepted:
        relation = str(row["value"].get("relation") or "")
        for rule_id in OBSERVATION_RULES.get((str(row["kind"]), relation), ()):
            if rule_id.split("#", 1)[0] in allowed_packs:
                active.add(rule_id)

    facing_mountain = None
    sitting_mountain = None
    origin_gua = None
    origin_group = None
    if "liqi" in spec["subprofiles"]:
        measurements = list(spec["compass_measurements"])
        confirmed = str(spec.get("confirmed_measurement_id") or "")
        selected = next(
            (
                row
                for row in measurements
                if not confirmed or row["measurement_id"] == confirmed
            ),
            None,
        )
        if selected is None:
            raise ValueError("complete Liqi fixture lacks selected measurement")
        corrected = (
            float(selected["facing_degrees"])
            + float(selected["correction_degrees"])
        ) % 360.0
        facing_mountain, _ = _mountain(corrected)
        sitting_mountain = MOUNTAINS[(MOUNTAINS.index(facing_mountain) + 12) % 24]

        origin_id = str(spec["liqi"]["origin_node_id"])
        origin = next(
            node for node in spec["layout_graph"]["nodes"]
            if node["node_id"] == origin_id
        )
        _, origin_gua = _mountain(
            (
                float(origin["direction_measurement"]["facing_degrees"])
                + float(origin["direction_measurement"]["correction_degrees"])
            )
            % 360.0
        )
        origin_group = "east_four" if origin_gua in EAST_GROUP else "west_four"
        active.update(
            {
                "fengshui/huangdi-zhaijing#HDZJ-R002",
                "fengshui/yangzhai-shishu#YZS-R007",
                "fengshui/yangzhai-sanyao#YZS-R005",
            }
        )
        nodes = {
            str(node["node_id"]): node for node in spec["layout_graph"]["nodes"]
        }
        for edge in spec["layout_graph"]["edges"]:
            if edge["boundary"] != "separating_wall_with_door":
                continue
            door = nodes[str(edge["door_id"])]
            _mountain(door["direction_measurement"]["facing_degrees"])
            active.add("fengshui/yangzhai-shishu#YZS-R006")

    return {
        "facing_mountain": facing_mountain,
        "sitting_mountain": sitting_mountain,
        "form_status": form_status,
        "origin_gua": origin_gua,
        "origin_group": origin_group,
        "active_source_rule_ids": sorted(active),
    }


__all__ = ["evaluate_complete_spec"]
