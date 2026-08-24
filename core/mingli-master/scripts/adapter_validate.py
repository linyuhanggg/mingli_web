#!/usr/bin/env python3
"""Validate deterministic fact-layer adapter payloads for mingli-master."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from evidence_contract import (
    applicability_condition_index,
    canonical_facts_digest,
)
from liuren_fact_adapter import MONTH_GENERAL_NAMES, TERM_TO_MONTH_GENERAL
from reading_engine.calendar_core import normalize_calendar, validate_calendar_digest


_SKILL_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_TOP_LEVEL = ("adapter", "calendar_normalization", "output")
REQUIRED_ADAPTER = ("name", "version", "rule_profile")
REQUIRED_CALENDAR = ("civil_datetime", "lunar_date", "ganzhi", "solar_terms")
ZIWEI_YANG_STEMS = frozenset("甲丙戊庚壬")
ZIWEI_TRANSFORMATION_EFFECTS = ("禄", "权", "科", "忌")
ZIWEI_TRANSFORMATION_TABLE = {
    "甲": ("廉贞", "破军", "武曲", "太阳"),
    "乙": ("天机", "天梁", "紫微", "太阴"),
    "丙": ("天同", "天机", "文昌", "廉贞"),
    "丁": ("太阴", "天同", "天机", "巨门"),
    "戊": ("贪狼", "太阴", "右弼", "天机"),
    "己": ("武曲", "贪狼", "天梁", "文曲"),
    "庚": ("太阳", "武曲", "太阴", "天同"),
    "辛": ("巨门", "太阳", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "左辅", "武曲"),
    "癸": ("破军", "巨门", "太阴", "贪狼"),
}

SYSTEM_ALIASES = {
    "liuyao": "divination",
    "meihua": "divination",
    "divination/liuyao": "divination",
    "divination/meihua": "divination",
    "san-shi/liuren": "liuren",
    "san-shi/qimen": "qimen",
    "san-shi/taiyi": "taiyi",
    "near-time-fortune": "fortune",
}

#: The bazi required-output authority lives in
#: ``fact_contracts.bazi.BaziFactContract``; the generic table must not
#: carry bazi field names.
REQUIRED_OUTPUTS = {
    "ziwei": ("palaces", "ming_shen", "stars", "sihua", "major_limits"),
    "xingming": ("ephemeris", "positions", "houses"),
    "divination": ("hexagram", "moving_lines", "casting_method"),
    "liuren": ("four_lessons", "three_transmissions", "heavenly_generals", "month_general", "day_hour"),
    "qimen": ("ju", "chief", "palaces", "instruments_wonders", "stars_doors_deities", "xunkong"),
    "taiyi": ("taiyi_plate", "ju", "taiyi_position", "host_guest_counts"),
    "selection": (
        "event_profile", "calendar_candidates", "date_time_candidates",
        "eligible_candidates", "eligible_date_time_candidates", "eliminations",
        "ranking", "lineage_policy",
    ),
    "fengshui": ("facing_degrees", "period", "layout", "school_variables"),
    "physiognomy": ("observation_source", "observed_features", "uncertainty"),
}

DIVINATION_REQUIRED_OUTPUTS = {
    "liuyao": (
        "hexagram", "primary_hexagram", "changed_hexagram", "moving_lines",
        "shi_ying", "six_relatives", "six_spirits", "najia", "casting_method",
    ),
    "meihua": (
        "hexagram", "primary_hexagram", "mutual_hexagram", "changed_hexagram",
        "moving_lines", "body_use", "casting_method",
    ),
}

USER_PROVIDED_STATUS = "validated_user_provided_chart"
USER_PROVIDED_ADAPTER = "mingli-master.structured_chart_adapter"
USER_OUTPUT_TYPES: dict[tuple[str, str | None], dict[str, type | tuple[type, ...]]] = {
    ("ziwei", None): {
        "palaces": list, "ming_shen": dict, "stars": list,
        "sihua": dict, "major_limits": list,
    },
    ("xingming", None): {"ephemeris": dict, "positions": list, "houses": list},
    ("divination", "liuyao"): {
        "hexagram": str, "primary_hexagram": str, "changed_hexagram": str,
        "moving_lines": list, "shi_ying": dict, "six_relatives": list,
        "six_spirits": list, "najia": list, "casting_method": str,
    },
    ("divination", "meihua"): {
        "hexagram": str, "primary_hexagram": str, "mutual_hexagram": str,
        "changed_hexagram": str, "moving_lines": list, "body_use": dict,
        "casting_method": str,
    },
    ("taiyi", None): {
        "taiyi_plate": dict, "ju": str, "taiyi_position": str,
        "host_guest_counts": dict,
    },
    ("selection", None): {
        "calendar_candidates": list, "jianchu": dict, "shensha": dict,
        "huanghei": dict, "yiji": dict, "conflicts": dict,
    },
    ("fengshui", None): {
        "facing_degrees": (int, float), "period": str, "layout": dict,
        "school_variables": dict,
    },
    ("physiognomy", None): {
        "observation_source": str, "observed_features": list,
        "uncertainty": list,
    },
}
USER_OUTPUT_DICT_KEYS = {
    ("ziwei", None, "ming_shen"): ("ming", "shen"),
    ("divination", "liuyao", "shi_ying"): ("shi", "ying"),
    ("divination", "meihua", "body_use"): ("body", "use"),
    ("taiyi", None, "host_guest_counts"): ("host", "guest"),
}
USER_OUTPUT_LIST_DICT_FIELDS = {
    ("ziwei", None, "palaces"), ("ziwei", None, "stars"),
    ("ziwei", None, "major_limits"), ("xingming", None, "positions"),
    ("xingming", None, "houses"),
    ("selection", None, "calendar_candidates"),
}
FORTUNE_TRIPLE_FORMATIONS = {
    "三合": {
        "申子辰": "水", "亥卯未": "木", "寅午戌": "火", "巳酉丑": "金",
    },
    "三会": {
        "寅卯辰": "木", "巳午未": "火", "申酉戌": "金", "亥子丑": "水",
    },
    "三刑": {"寅巳申": None, "丑戌未": None},
}
FORTUNE_STEM_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
FORTUNE_ELEMENTS = ("木", "火", "土", "金", "水")
FORTUNE_POSITIONS = ("year", "month", "day", "hour")
FORTUNE_POSITION_LABELS = {
    "year": "年支", "month": "月支", "day": "日支", "hour": "时支",
}


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _valid_nested_value(value: Any) -> bool:
    if _valid_text(value) or _valid_number(value) or isinstance(value, bool):
        return True
    if isinstance(value, dict):
        return bool(value) and all(
            _valid_text(key) and _valid_nested_value(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return bool(value) and all(_valid_nested_value(item) for item in value)
    return False


def _validate_user_provided_nested_output(
    system: str,
    subsystem: str | None,
    output: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def invalid(path: str, message: str) -> None:
        findings.append(_finding(f"invalid_output:{path}", message))

    def require_text(record: dict[str, Any], path: str, *fields: str) -> None:
        if not isinstance(record, dict):
            invalid(path, f"{path} must be an object")
            return
        for field in fields:
            if not _valid_text(record.get(field)):
                invalid(f"{path}.{field}", f"{path}.{field} must be non-empty text")

    def require_number(record: dict[str, Any], path: str, *fields: str) -> None:
        if not isinstance(record, dict):
            invalid(path, f"{path} must be an object")
            return
        for field in fields:
            if not _valid_number(record.get(field)):
                invalid(f"{path}.{field}", f"{path}.{field} must be numeric")

    if system == "ziwei":
        palaces = output.get("palaces") if isinstance(output.get("palaces"), list) else []
        stars = output.get("stars") if isinstance(output.get("stars"), list) else []
        major_limits = output.get("major_limits") if isinstance(output.get("major_limits"), list) else []
        for index, palace in enumerate(palaces):
            require_text(palace, f"palaces[{index}]", "name", "branch")
        require_text(output.get("ming_shen") or {}, "ming_shen", "ming", "shen")
        for index, star in enumerate(stars):
            require_text(star, f"stars[{index}]", "name", "palace")
        sihua = output.get("sihua")
        if isinstance(sihua, dict) and not all(
            _valid_text(key) and _valid_text(value) for key, value in sihua.items()
        ):
            invalid("sihua", "sihua names and star values must be non-empty text")
        for index, limit in enumerate(major_limits):
            path = f"major_limits[{index}]"
            require_number(limit, path, "age_start", "age_end")
            require_text(limit, path, "palace")
            if isinstance(limit, dict) and (
                _valid_number(limit.get("age_start"))
                and _valid_number(limit.get("age_end"))
                and limit["age_start"] > limit["age_end"]
            ):
                invalid(path, "major limit age_start must not exceed age_end")

    elif system == "xingming":
        ephemeris = output.get("ephemeris")
        require_text(ephemeris, "ephemeris", "name", "version")
        positions = output.get("positions") if isinstance(output.get("positions"), list) else []
        houses = output.get("houses") if isinstance(output.get("houses"), list) else []
        for index, position in enumerate(positions):
            path = f"positions[{index}]"
            require_text(position, path, "body")
            require_number(position, path, "longitude")
            longitude = position.get("longitude") if isinstance(position, dict) else None
            if _valid_number(longitude) and not 0 <= float(longitude) < 360:
                invalid(f"{path}.longitude", "longitude must be in [0, 360)")
        for index, house in enumerate(houses):
            path = f"houses[{index}]"
            require_text(house, path, "name")
            require_number(house, path, "start_degree")

    elif system == "divination" and subsystem == "liuyao":
        shi_ying = output.get("shi_ying") if isinstance(output.get("shi_ying"), dict) else {}
        for field in ("shi", "ying"):
            value = shi_ying.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 6:
                invalid(f"shi_ying.{field}", f"shi_ying.{field} must be a line number from 1 to 6")
        if shi_ying.get("shi") == shi_ying.get("ying"):
            invalid("shi_ying", "shi and ying lines must differ")
        for key in ("six_relatives", "six_spirits", "najia"):
            values = output.get(key) if isinstance(output.get(key), list) else []
            for index, value in enumerate(values):
                if not _valid_text(value):
                    invalid(f"{key}[{index}]", f"{key} entries must be non-empty text")
        najia = output.get("najia") if isinstance(output.get("najia"), list) else []
        for index, value in enumerate(najia):
            if not isinstance(value, str):
                continue
            if not re.fullmatch(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]", value):
                invalid(f"najia[{index}]", "najia entries must be stem-branch pairs")

    elif system == "divination" and subsystem == "meihua":
        require_text(output.get("body_use"), "body_use", "body", "use")

    elif system == "taiyi":
        if not _valid_nested_value(output.get("taiyi_plate")):
            invalid("taiyi_plate", "taiyi_plate must contain non-empty structured values")
        counts = output.get("host_guest_counts")
        require_number(counts, "host_guest_counts", "host", "guest")

    elif system == "selection":
        candidates: list[str] = []
        candidate_records = output.get("calendar_candidates") if isinstance(output.get("calendar_candidates"), list) else []
        for index, candidate in enumerate(candidate_records):
            value = candidate.get("date") if isinstance(candidate, dict) else None
            try:
                parsed = date.fromisoformat(value) if isinstance(value, str) else None
            except ValueError:
                parsed = None
            if parsed is None:
                invalid(f"calendar_candidates[{index}].date", "candidate date must be ISO-8601")
            else:
                candidates.append(value)
        selection_maps = {
            key: output.get(key) if isinstance(output.get(key), dict) else {}
            for key in ("jianchu", "shensha", "huanghei", "yiji", "conflicts")
        }
        for key, mapping in selection_maps.items():
            if not isinstance(mapping, dict) or any(day not in mapping for day in candidates):
                invalid(key, f"{key} must cover every candidate date")
        for day in candidates:
            if not _valid_text(selection_maps["jianchu"].get(day)):
                invalid(f"jianchu.{day}", "jianchu value must be non-empty text")
            if not _valid_text(selection_maps["huanghei"].get(day)):
                invalid(f"huanghei.{day}", "huanghei value must be non-empty text")
            for key in ("shensha", "conflicts"):
                values = selection_maps[key].get(day)
                if not isinstance(values, list) or any(not _valid_text(item) for item in values):
                    invalid(f"{key}.{day}", f"{key} value must be a text list")
            yiji = selection_maps["yiji"].get(day)
            if not isinstance(yiji, dict) or not all(
                key in yiji
                and isinstance(yiji[key], list)
                and all(_valid_text(item) for item in yiji[key])
                for key in ("宜", "忌")
            ):
                invalid(f"yiji.{day}", "yiji must contain text lists for 宜 and 忌")

    elif system == "fengshui":
        for key in ("layout", "school_variables"):
            if not _valid_nested_value(output.get(key)):
                invalid(key, f"{key} must contain non-empty structured values")

    elif system == "physiognomy":
        for key in ("observed_features", "uncertainty"):
            values = output.get(key)
            if not isinstance(values, list) or any(not _valid_text(item) for item in values):
                invalid(key, f"{key} must contain text observations only")

    return findings


def _validate_user_provided_output(
    system: str,
    subsystem: str | None,
    output: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    schema = USER_OUTPUT_TYPES.get((system, subsystem))
    if schema is None:
        return [_finding("invalid_output:schema", "No Tier-B output schema for route")]
    for key, expected_type in schema.items():
        value = output.get(key)
        if isinstance(value, bool) or not isinstance(value, expected_type):
            findings.append(_finding(
                f"invalid_output:{key}",
                f"Tier-B output {key} has the wrong type",
            ))
            continue
        if isinstance(value, (str, list, dict)) and not value:
            findings.append(_finding(
                f"invalid_output:{key}",
                f"Tier-B output {key} must not be empty",
            ))
            continue
        required_keys = USER_OUTPUT_DICT_KEYS.get((system, subsystem, key), ())
        if required_keys and (
            not isinstance(value, dict)
            or any(not _has_key(value, field) for field in required_keys)
        ):
            findings.append(_finding(
                f"invalid_output:{key}",
                f"Tier-B output {key} is missing required members",
            ))
        if (system, subsystem, key) in USER_OUTPUT_LIST_DICT_FIELDS and (
            not isinstance(value, list)
            or any(not isinstance(item, dict) or not item for item in value)
        ):
            findings.append(_finding(
                f"invalid_output:{key}",
                f"Tier-B output {key} must contain non-empty objects",
            ))
    moving_lines = output.get("moving_lines")
    if isinstance(moving_lines, list) and (
        not moving_lines
        or any(isinstance(item, bool) or not isinstance(item, int) or not 1 <= item <= 6 for item in moving_lines)
    ):
        findings.append(_finding(
            "invalid_output:moving_lines",
            "Moving lines must be integers from 1 through 6",
        ))
    if subsystem == "liuyao":
        for key in ("six_relatives", "six_spirits", "najia"):
            value = output.get(key)
            if isinstance(value, list) and (
                len(value) != 6
                or any(not isinstance(item, str) or not item.strip() for item in value)
            ):
                findings.append(_finding(
                    f"invalid_output:{key}",
                    f"{key} must contain six non-empty line values",
                ))
    facing = output.get("facing_degrees")
    if system == "fengshui" and isinstance(facing, (int, float)) and not isinstance(facing, bool):
        if not 0 <= float(facing) < 360:
            findings.append(_finding(
                "invalid_output:facing_degrees",
                "Facing degrees must be in [0, 360)",
            ))
    findings.extend(
        _validate_user_provided_nested_output(system, subsystem, output)
    )
    return findings


def _fortune_element_role_family(
    day_master: str,
    target_element: str | None,
) -> str | None:
    if not target_element or day_master not in FORTUNE_STEM_ELEMENT:
        return None
    day_index = FORTUNE_ELEMENTS.index(FORTUNE_STEM_ELEMENT[day_master])
    target_index = FORTUNE_ELEMENTS.index(target_element)
    if day_index == target_index:
        return "比劫"
    if target_index == (day_index + 1) % 5:
        return "食伤"
    if target_index == (day_index + 2) % 5:
        return "财"
    if day_index == (target_index + 1) % 5:
        return "印"
    return "官杀"


def _expected_fortune_formations(
    natal_pillars: dict[str, Any],
    transit_layers: dict[str, Any],
    day_master: str,
) -> list[dict[str, Any]]:
    if not all(
        isinstance(natal_pillars.get(position), str)
        and len(natal_pillars[position]) == 2
        for position in FORTUNE_POSITIONS
    ) or not all(
        isinstance(transit_layers.get(layer), dict)
        and isinstance(transit_layers[layer].get("branch"), str)
        for layer in ("day", "month", "year", "major_luck")
    ):
        return []

    target_branch = transit_layers["day"]["branch"]
    occurrences: dict[str, list[dict[str, str]]] = {
        branch: [] for branch in "子丑寅卯辰巳午未申酉戌亥"
    }
    for layer in ("day", "month", "year", "major_luck"):
        branch = transit_layers[layer]["branch"]
        if branch not in occurrences:
            return []
        occurrences[branch].append({
            "scope": "transit",
            "layer": layer,
            "branch": branch,
        })
    for position in FORTUNE_POSITIONS:
        branch = natal_pillars[position][1]
        if branch not in occurrences:
            return []
        occurrences[branch].append({
            "scope": "natal",
            "position": position,
            "position_label": FORTUNE_POSITION_LABELS[position],
            "branch": branch,
        })

    formations: list[dict[str, Any]] = []
    for relation, patterns in FORTUNE_TRIPLE_FORMATIONS.items():
        for pattern, nominal_element in patterns.items():
            branches = list(pattern)
            if target_branch not in branches or any(
                not occurrences[branch] for branch in branches
            ):
                continue
            members: list[dict[str, str]] = []
            for branch in branches:
                if branch == target_branch:
                    day_member = next(
                        (
                            item
                            for item in occurrences[branch]
                            if item.get("scope") == "transit"
                            and item.get("layer") == "day"
                        ),
                        None,
                    )
                    members.append(day_member or occurrences[branch][0])
                else:
                    members.append(occurrences[branch][0])
            formations.append({
                "id": f"day-multi-formation-{len(formations) + 1:02d}",
                "relation": relation,
                "branches": branches,
                "nominal_element": nominal_element,
                "nominal_element_role_family": _fortune_element_role_family(
                    day_master,
                    nominal_element,
                ),
                "branch_set_status": (
                    "complete_branch_set_present_across_natal_and_timing_layers"
                ),
                "transformation_status": (
                    "unadjudicated_requires_classical_conditions"
                    if nominal_element else "not_applicable"
                ),
                "members": members,
                "target_day_involved": True,
                "scope": "cross_natal_and_active_timing_layers_not_specific_event",
            })
    return formations


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _has_key(data: dict[str, Any], key: str) -> bool:
    return key in data and not _is_missing(data[key])


# Fourth-acceptance P0-2: production-shape mechanism_bridge schema.
# A bridge authorises `<ten_god> → <event>` for the public gate ONLY when it
# is signed by concrete evidence records. Every field is required, and each
# has a distinct failure code so mutation tests can isolate one invariant at
# a time.
MECHANISM_BRIDGE_REQUIRED_FIELDS = (
    "id",
    "ten_god",
    "authorised_events",
    "applicable_conditions",
    "source_pack",
    "source_record_id",
    "source_path",
    "source_hash",
    "facts_digest",
    "evidence_digest",
)


def _index_evidence_bundle(evidence_bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Return per-pack indexes read from the REAL evidence bundle schema:
    packs[].pack, packs[].rule_evidence, packs[].quote_evidence,
    packs[].source_hashes[path].
    """
    if not isinstance(evidence_bundle, dict):
        return {"packs": {}, "facts_digest": None, "bundle_digest": None}
    packs_index: dict[str, dict[str, Any]] = {}
    for pack in evidence_bundle.get("packs") or []:
        if not isinstance(pack, dict):
            continue
        pack_id = pack.get("pack")
        if not isinstance(pack_id, str):
            continue
        record_paths: dict[str, str] = {}
        for section in ("rule_evidence", "quote_evidence"):
            for record in pack.get(section) or []:
                if not isinstance(record, dict):
                    continue
                rid = record.get("record_id")
                path = record.get("path")
                if isinstance(rid, str) and isinstance(path, str):
                    record_paths[rid] = path
        source_hashes = pack.get("source_hashes") if isinstance(pack.get("source_hashes"), dict) else {}
        packs_index[pack_id] = {
            "record_paths": record_paths,
            "source_hashes": {k: v for k, v in source_hashes.items() if isinstance(k, str)},
        }
    return {
        "packs": packs_index,
        "facts_digest": evidence_bundle.get("facts_digest"),
        "bundle_digest": evidence_bundle.get("bundle_digest"),
        "conditions": applicability_condition_index(evidence_bundle),
    }


def _validate_mechanism_bridges(
    payload: dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    contract = payload.get("public_claim_contract") if isinstance(payload.get("public_claim_contract"), dict) else None
    if not isinstance(contract, dict):
        return []
    bridges = contract.get("mechanism_bridges")
    if bridges is None or bridges == []:
        return []
    findings: list[dict[str, str]] = []
    if not isinstance(bridges, list):
        findings.append(_finding(
            "fortune_mechanism_bridge_invalid_schema",
            "public_claim_contract.mechanism_bridges must be a list",
        ))
        return findings

    evidence_index = _index_evidence_bundle(evidence_bundle)

    # Fourth-acceptance P0-2: when no evidence bundle is available and the
    # bridge list is non-empty, fail-closed. The gate cannot pretend to have
    # verified evidence bindings without an evidence bundle.
    if evidence_bundle is None:
        findings.append(_finding(
            "fortune_mechanism_bridge_missing_evidence_context",
            "mechanism_bridges present but no evidence bundle available; cannot verify",
        ))
        return findings

    seen_ids: set[str] = set()
    for idx, bridge in enumerate(bridges):
        if not isinstance(bridge, dict):
            findings.append(_finding(
                "fortune_mechanism_bridge_invalid_schema",
                f"mechanism_bridges[{idx}] must be a mapping",
            ))
            continue
        missing = [
            field for field in MECHANISM_BRIDGE_REQUIRED_FIELDS
            if field not in bridge or _is_missing(bridge.get(field))
        ]
        if missing:
            findings.append(_finding(
                "fortune_mechanism_bridge_invalid_schema",
                f"mechanism_bridges[{idx}] missing required fields: " + ", ".join(missing),
            ))
            continue
        bridge_id = bridge.get("id")
        if not isinstance(bridge_id, str) or bridge_id in seen_ids:
            findings.append(_finding(
                "fortune_mechanism_bridge_invalid_schema",
                f"mechanism_bridges[{idx}] has duplicate or non-string id",
            ))
            continue
        seen_ids.add(bridge_id)

        if not isinstance(bridge.get("authorised_events"), list) or not bridge["authorised_events"]:
            findings.append(_finding(
                "fortune_mechanism_bridge_invalid_schema",
                f"mechanism_bridges[{idx}] authorised_events must be a non-empty list",
            ))
            continue

        # Applicable conditions must carry explicit condition_ids so the
        # bridge cannot be reused across queries.
        applicable = bridge.get("applicable_conditions")
        if (
            not isinstance(applicable, dict)
            or not isinstance(applicable.get("condition_ids"), list)
            or not applicable["condition_ids"]
        ):
            findings.append(_finding(
                "fortune_mechanism_bridge_condition_ids_invalid",
                f"mechanism_bridges[{idx}] applicable_conditions.condition_ids must be a non-empty list",
            ))
            continue
        condition_ids = applicable["condition_ids"]
        if (
            any(not isinstance(item, str) or not item for item in condition_ids)
            or len(set(condition_ids)) != len(condition_ids)
        ):
            findings.append(_finding(
                "fortune_mechanism_bridge_condition_ids_invalid",
                f"mechanism_bridges[{idx}] condition_ids must be unique non-empty strings",
            ))
            continue
        condition_index = evidence_index["conditions"]
        unknown_conditions = [
            condition_id
            for condition_id in condition_ids
            if condition_id not in condition_index
        ]
        if unknown_conditions:
            findings.append(_finding(
                "fortune_mechanism_bridge_condition_ids_unknown",
                (
                    f"mechanism_bridges[{idx}] references conditions absent from"
                    f" the current source plan: {unknown_conditions}"
                ),
            ))
            continue
        unsatisfied_conditions = [
            condition_id
            for condition_id in condition_ids
            if condition_index[condition_id].get("satisfied") is not True
        ]
        if unsatisfied_conditions:
            findings.append(_finding(
                "fortune_mechanism_bridge_conditions_unsatisfied",
                (
                    f"mechanism_bridges[{idx}] references unsatisfied conditions:"
                    f" {unsatisfied_conditions}"
                ),
            ))
            continue

        # Pack must exist in evidence.
        source_pack = bridge.get("source_pack")
        pack_entry = evidence_index["packs"].get(source_pack)
        if pack_entry is None:
            findings.append(_finding(
                "fortune_mechanism_bridge_pack_not_in_evidence",
                f"mechanism_bridges[{idx}] source_pack={source_pack!r} is not in the current evidence bundle",
            ))
            continue

        # Record must be one of the ranked records in that pack.
        record_id = bridge.get("source_record_id")
        if record_id not in pack_entry["record_paths"]:
            findings.append(_finding(
                "fortune_mechanism_bridge_record_not_in_pack",
                f"mechanism_bridges[{idx}] source_record_id={record_id!r} is not among {source_pack!r} ranked records",
            ))
            continue

        # Path must match the ranked record path exactly.
        bridge_path = bridge.get("source_path")
        real_path = pack_entry["record_paths"].get(record_id)
        if bridge_path != real_path:
            findings.append(_finding(
                "fortune_mechanism_bridge_path_mismatch",
                f"mechanism_bridges[{idx}] source_path={bridge_path!r} does not match evidence record path {real_path!r}",
            ))
            continue

        # Hash must equal the pack's source_hashes[path].
        expected_hash = pack_entry["source_hashes"].get(real_path)
        source_hash = bridge.get("source_hash")
        if not isinstance(source_hash, str) or len(source_hash) != 64:
            findings.append(_finding(
                "fortune_mechanism_bridge_invalid_schema",
                f"mechanism_bridges[{idx}] source_hash must be a 64-character hex digest",
            ))
            continue
        try:
            int(source_hash, 16)
        except ValueError:
            findings.append(_finding(
                "fortune_mechanism_bridge_invalid_schema",
                f"mechanism_bridges[{idx}] source_hash must be hexadecimal",
            ))
            continue
        if source_hash != expected_hash:
            findings.append(_finding(
                "fortune_mechanism_bridge_hash_mismatch",
                f"mechanism_bridges[{idx}] source_hash does not match the pack's real file digest",
            ))
            continue

        # facts_digest and evidence_digest must match the current bundle.
        if bridge.get("facts_digest") != evidence_index["facts_digest"]:
            findings.append(_finding(
                "fortune_mechanism_bridge_facts_digest_mismatch",
                f"mechanism_bridges[{idx}] facts_digest does not match the current evidence bundle facts_digest",
            ))
            continue
        if bridge.get("evidence_digest") != evidence_index["bundle_digest"]:
            findings.append(_finding(
                "fortune_mechanism_bridge_evidence_digest_mismatch",
                f"mechanism_bridges[{idx}] evidence_digest does not match the current bundle_digest",
            ))
            continue

    return findings


def _finding(code: str, message: str, level: str = "error") -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def _expected_ziwei_direction(year_stem: str, gender: str) -> str | None:
    if year_stem not in set("甲乙丙丁戊己庚辛壬癸") or gender not in {"male", "female"}:
        return None
    is_yang = year_stem in ZIWEI_YANG_STEMS
    return (
        "forward"
        if (is_yang and gender == "male") or (not is_yang and gender == "female")
        else "reverse"
    )


def _validate_ziwei_calculated_payload(
    payload: dict[str, Any], output: dict[str, Any]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    palaces = output.get("palace_facts")
    stars = output.get("star_facts")
    if not isinstance(palaces, list) or len(palaces) != 12:
        findings.append(_finding(
            "ziwei_incomplete_palace_facts",
            "Calculated Ziwei output must expose twelve independent palace facts",
        ))
    elif {item.get("index") for item in palaces if isinstance(item, dict)} != set(range(12)):
        findings.append(_finding(
            "ziwei_invalid_palace_indexes",
            "Calculated Ziwei palace indexes must be exactly 0 through 11",
        ))
    if not isinstance(stars, list) or not stars:
        findings.append(_finding(
            "ziwei_missing_star_facts",
            "Calculated Ziwei output must expose independent star facts",
        ))
    patterns = output.get("source_conditioned_patterns")
    if not isinstance(patterns, list) or not patterns:
        findings.append(_finding(
            "ziwei_source_patterns_missing",
            "Calculated Ziwei output must expose verified source-conditioned patterns",
        ))
    else:
        for index, pattern in enumerate(patterns):
            if not isinstance(pattern, dict):
                findings.append(_finding(
                    "ziwei_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] must be an object",
                ))
                continue
            required = (
                "rule_id",
                "local_rule_id",
                "title",
                "source_pack",
                "source_anchor",
                "status",
                "fact_paths",
                "predicate_audit",
            )
            if any(
                not isinstance(pattern.get(field), str)
                or not pattern.get(field, "").strip()
                for field in required[:6]
            ):
                findings.append(_finding(
                    "ziwei_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] has invalid identity fields",
                ))
            if pattern.get("status") != "predicate_matched_not_verdict":
                findings.append(_finding(
                    "ziwei_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] must not be a verdict",
                ))
            for field in required[6:]:
                value = pattern.get(field)
                if not isinstance(value, list) or not value or not all(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    findings.append(_finding(
                        "ziwei_source_pattern_invalid",
                        f"source_conditioned_patterns[{index}].{field} must be non-empty text",
                    ))
            if "verdict" in pattern:
                findings.append(_finding(
                    "ziwei_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] must not contain verdict",
                ))

    normalized = ((payload.get("input") or {}).get("normalized_input") or {})
    gender = str(normalized.get("gender") or "")
    chinese_date = str(output.get("chinese_date") or "").split()
    year_pillar = chinese_date[0] if len(chinese_date) == 4 else ""
    expected_direction = _expected_ziwei_direction(year_pillar[:1], gender)
    direction_fact = (
        output.get("major_limit_direction")
        if isinstance(output.get("major_limit_direction"), dict)
        else {}
    )
    if (
        expected_direction is None
        or direction_fact.get("direction") != expected_direction
        or direction_fact.get("year_stem") != year_pillar[:1]
        or direction_fact.get("year_polarity")
        != ("yang" if year_pillar[:1] in ZIWEI_YANG_STEMS else "yin")
        or direction_fact.get("gender") != gender
    ):
        findings.append(_finding(
            "ziwei_major_limit_direction_mismatch",
            "Major-limit direction does not match year-stem polarity and gender",
        ))
    sequence = output.get("major_limit_sequence")
    if not isinstance(sequence, list) or len(sequence) != 12:
        findings.append(_finding(
            "ziwei_invalid_major_limit_sequence",
            "Ziwei must expose all twelve major-limit periods in age order",
        ))
    else:
        indexes = [item.get("palace_index") for item in sequence if isinstance(item, dict)]
        ranges = [item.get("range") for item in sequence if isinstance(item, dict)]
        step = 1 if expected_direction == "forward" else -1
        direction_ok = len(indexes) == 12 and all(
            isinstance(index, int)
            and isinstance(next_index, int)
            and (next_index - index) % 12 == step % 12
            for index, next_index in zip(indexes, indexes[1:])
        )
        range_ok = len(ranges) == 12 and all(
            isinstance(item, list)
            and len(item) == 2
            and item[1] == item[0] + 9
            and (
                position == 0
                or (
                    isinstance(ranges[position - 1], list)
                    and item[0] == ranges[position - 1][1] + 1
                )
            )
            for position, item in enumerate(ranges)
        )
        ming_branch = str((output.get("ming_shen") or {}).get("ming_branch") or "")
        first_is_ming = bool(sequence) and sequence[0].get("palace") == "命宫" and (
            not ming_branch or sequence[0].get("palace_branch") == ming_branch
        )
        if not direction_ok or not range_ok or not first_is_ming:
            findings.append(_finding(
                "ziwei_invalid_major_limit_sequence",
                "Ziwei major-limit ages or palace traversal do not match the declared direction",
            ))

    convention = (
        output.get("chart_convention")
        if isinstance(output.get("chart_convention"), dict)
        else {}
    )
    engine = convention.get("engine") if isinstance(convention.get("engine"), dict) else {}
    # iztro is cast on the policy-corrected effective instant, so the expected
    # time_index must be derived from the effective datetime (apparent solar
    # time when requested), not the raw civil hour.
    effective_source = (
        normalized.get("effective_datetime")
        or normalized.get("civil_datetime")
        or ""
    )
    try:
        cast_hour = datetime.fromisoformat(str(effective_source)).hour
    except ValueError:
        cast_hour = -1
    expected_time_index = (
        12 if cast_hour == 23 else ((cast_hour + 1) // 2 if cast_hour >= 0 else None)
    )
    expected_day_divide = (
        "forward"
        if normalized.get("zi_hour_policy") == "late-zi-next-day"
        else "current"
    )
    if (
        engine != {"name": "iztro", "version": "2.5.8"}
        or convention.get("fix_leap") is not True
        or convention.get("algorithm") != "default"
        or convention.get("time_index") != expected_time_index
        or convention.get("day_divide") != expected_day_divide
    ):
        findings.append(_finding(
            "ziwei_chart_convention_mismatch",
            "Ziwei chart convention diverges from the pinned engine profile",
        ))
    natal_transformations = (
        (output.get("transformation_layers") or {}).get("natal")
        if isinstance(output.get("transformation_layers"), dict)
        else None
    )
    expected_natal_stars = ZIWEI_TRANSFORMATION_TABLE.get(year_pillar[:1])
    if (
        not isinstance(natal_transformations, list)
        or len(natal_transformations) != 4
        or tuple(
            item.get("transformation")
            for item in natal_transformations
            if isinstance(item, dict)
        )
        != ZIWEI_TRANSFORMATION_EFFECTS
        or tuple(
            item.get("star")
            for item in natal_transformations
            if isinstance(item, dict)
        )
        != expected_natal_stars
        or any(
            not item.get("palace") or not item.get("palace_branch")
            for item in natal_transformations
            if isinstance(item, dict)
        )
    ):
        findings.append(_finding(
            "ziwei_incomplete_natal_transformations",
            "Natal Ziwei transformations must contain four located stem-bound facts",
        ))
    source_roles = (
        output.get("source_roles")
        if isinstance(output.get("source_roles"), dict)
        else {}
    )
    if (
        source_roles.get("calculation_primary")
        != ["ziwei/ziwei-doushu-quanshu"]
        or source_roles.get("classical_adjudication") != ["ziwei/taiwei-fu"]
        or source_roles.get("late_observational_commentary")
        != ["ziwei/feixing-ziwei-doushu-yuanzhi"]
    ):
        findings.append(_finding(
            "ziwei_source_role_mismatch",
            "Ziwei calculation, adjudication, and late commentary roles must remain separate",
        ))
    return findings


def _ziwei_temporal_layers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for segment in payload.get("active_major_limit_segments") or ():
        if isinstance(segment, dict) and isinstance(segment.get("major_limit"), dict):
            layers.append(segment["major_limit"])
    for wrapper in (payload.get("annual_layers") or {}).values():
        for segment in (wrapper or {}).get("segments") or ():
            if isinstance(segment, dict) and isinstance(segment.get("liu_nian"), dict):
                layers.append(segment["liu_nian"])
    for wrapper in (payload.get("monthly_layers") or {}).values():
        for segment in (wrapper or {}).get("segments") or ():
            if isinstance(segment, dict) and isinstance(segment.get("liu_yue"), dict):
                layers.append(segment["liu_yue"])
    return layers


def validate_ziwei_extension(payload: dict[str, Any]) -> dict[str, Any]:
    """Independently validate a deterministic Ziwei temporal fact extension."""

    findings: list[dict[str, str]] = []
    digest = str(payload.get("natal_fact_digest") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        findings.append(_finding(
            "ziwei_temporal_natal_digest_missing",
            "Ziwei temporal facts must bind a deterministic natal digest",
        ))
    source_roles = (
        payload.get("source_roles")
        if isinstance(payload.get("source_roles"), dict)
        else {}
    )
    if source_roles.get("late_observational_commentary") != [
        "ziwei/feixing-ziwei-doushu-yuanzhi"
    ]:
        findings.append(_finding(
            "ziwei_temporal_source_role_mismatch",
            "Late Ziwei observational material must remain commentary-only",
        ))
    layers = _ziwei_temporal_layers(payload)
    if not layers:
        findings.append(_finding(
            "ziwei_temporal_layers_missing",
            "Ziwei temporal extension contains no exact temporal layers",
        ))
    for layer in layers:
        palace_names = layer.get("palaceNames")
        palace_facts = layer.get("palace_facts")
        star_slots = layer.get("stars")
        star_facts = layer.get("star_facts")
        transformations = layer.get("transformation_facts")
        stem = str(layer.get("heavenlyStem") or "")
        expected_stars = ZIWEI_TRANSFORMATION_TABLE.get(stem)
        actual_effects = tuple(
            item.get("effect")
            for item in transformations or ()
            if isinstance(item, dict)
        )
        actual_stars = tuple(
            item.get("star")
            for item in transformations or ()
            if isinstance(item, dict)
        )
        if (
            not isinstance(palace_names, list)
            or len(palace_names) != 12
            or not isinstance(palace_facts, list)
            or len(palace_facts) != 12
            or [
                item.get("temporal_palace")
                for item in palace_facts
                if isinstance(item, dict)
            ]
            != palace_names
        ):
            findings.append(_finding(
                "ziwei_temporal_palace_mismatch",
                "Ziwei temporal layer must expose twelve matching palace facts",
            ))
        expected_star_count = sum(
            len(slot) for slot in star_slots or () if isinstance(slot, list)
        )
        if not isinstance(star_facts, list) or len(star_facts) != expected_star_count:
            findings.append(_finding(
                "ziwei_temporal_star_mismatch",
                "Ziwei temporal star facts diverge from the engine slots",
            ))
        if (
            actual_effects != ZIWEI_TRANSFORMATION_EFFECTS
            or expected_stars is None
            or actual_stars != expected_stars
            or tuple(layer.get("mutagen") or ()) != expected_stars
        ):
            findings.append(_finding(
                "ziwei_temporal_transformation_mismatch",
                "Ziwei temporal transformations diverge from the applicable stem table",
            ))
    return {
        "ok": not findings,
        "system": "ziwei",
        "findings": findings,
        "codes": [item["code"] for item in findings],
    }


LIUREN_STEMS = "甲乙丙丁戊己庚辛壬癸"
LIUREN_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
LIUREN_JIAZI_CYCLE = tuple(
    LIUREN_STEMS[index % 10] + LIUREN_BRANCHES[index % 12]
    for index in range(60)
)
LIUREN_JIAZI = set(LIUREN_JIAZI_CYCLE)
LIUREN_STEM_LODGE = {
    "甲": "寅", "乙": "辰", "丙": "巳", "丁": "未", "戊": "巳",
    "己": "未", "庚": "申", "辛": "戌", "壬": "亥", "癸": "丑",
}
LIUREN_GENERALS = {
    "贵人", "腾蛇", "朱雀", "六合", "勾陈", "青龙",
    "天空", "白虎", "太常", "玄武", "太阴", "天后",
}
LIUREN_BIEZHE_PROFILES = {
    "daliuren-daquan-body-branch",
    "daliuren-daquan-upper-over-branch",
}


def _validate_fortune_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if payload.get("fact_layer_status") != "near_time_bazi_transit_facts":
        findings.append(_finding("fortune_unverified_fact_status", "Near-time payload has the wrong fact status"))
    if payload.get("schema_version") != "mingli-near-time-fortune-v2":
        findings.append(_finding("fortune_unverified_schema", "Near-time payload is not the v2 mechanism schema"))
    if payload.get("contract_version") != "fortune-public-v6-mechanism-stack":
        findings.append(_finding("fortune_unverified_contract", "Near-time payload is not the v6 mechanism-stack contract"))

    adapter = payload.get("adapter") if isinstance(payload.get("adapter"), dict) else {}
    if adapter.get("name") != "mingli-master.near_time_fortune_adapter":
        findings.append(_finding("fortune_unverified_adapter", "Near-time payload was not produced by the bundled adapter"))
    if (
        adapter.get("version") != "2.2.1"
        or adapter.get("rule_profile") != "full-birth/transit-mechanism-stack-v5"
    ):
        findings.append(_finding(
            "fortune_stale_adapter_contract",
            "Near-time payload does not use the cross-layer formation-aware adapter contract",
        ))
    for field in ("version", "rule_profile", "generated_at"):
        if not _has_key(adapter, field):
            findings.append(_finding(f"fortune_missing_adapter:{field}", f"Missing near-time adapter field: {field}"))

    birth = payload.get("birth_fact_layer") if isinstance(payload.get("birth_fact_layer"), dict) else {}
    if birth.get("status") != "calculated_natal_chart_from_birth_datetime":
        findings.append(_finding("fortune_missing_full_birth_facts", "Near-time payload lacks a calculated birth chart"))
    for field in (
        "natal_pillars",
        "day_master",
        "month_command",
        "hidden_stems",
        "ten_gods",
        "element_inventory",
        "seasonal_profile",
        "tiaohou_markers",
        "interpretive_candidates",
        "shensha_auxiliary",
        "natal_fact_digest",
        "strength_evidence",
        "active_luck_cycle",
        "active_luck_cycle_detail",
    ):
        if not _has_key(birth, field):
            findings.append(_finding(f"fortune_missing_birth_fact:{field}", f"Missing birth fact: {field}"))

    natal_digest = birth.get("natal_fact_digest")
    if not isinstance(natal_digest, str) or re.fullmatch(r"[0-9a-f]{64}", natal_digest) is None:
        findings.append(_finding(
            "fortune_invalid_natal_fact_digest",
            "Near-time payload lacks a deterministic natal fact digest",
        ))
    bounded = payload.get("bounded_view") if isinstance(payload.get("bounded_view"), dict) else {}
    periods = bounded.get("periods")
    if (
        bounded.get("base_system") != "bazi"
        or bounded.get("base_fact_layer") != "bazi_day_fact_extension"
        or bounded.get("natal_fact_digest") != natal_digest
        or not isinstance(periods, list)
        or bounded.get("period_count") != len(periods)
        or payload.get("target_date") not in periods
    ):
        findings.append(_finding(
            "fortune_invalid_bounded_view",
            "Near-time payload is not bound to its Bazi natal identity and explicit target period",
        ))
    bazi_day = (
        payload.get("bazi_day_fact_layer")
        if isinstance(payload.get("bazi_day_fact_layer"), dict)
        else {}
    )
    selected_segment = (
        payload.get("selected_bazi_day_segment")
        if isinstance(payload.get("selected_bazi_day_segment"), dict)
        else {}
    )
    bazi_segments = bazi_day.get("ganzhi_segments")
    transit_layers = (
        payload.get("transit_layers")
        if isinstance(payload.get("transit_layers"), dict)
        else {}
    )
    selected_transits = (
        selected_segment.get("active_transits")
        if isinstance(selected_segment.get("active_transits"), dict)
        else {}
    )
    layer_identity_matches = all(
        selected_transits.get(layer)
        == (
            transit_layers.get(layer, {}).get("pillar")
            if isinstance(transit_layers.get(layer), dict)
            else None
        )
        for layer in ("year", "month", "day")
    )
    if (
        bazi_day.get("date") != payload.get("target_date")
        or not isinstance(bazi_segments, list)
        or not bazi_segments
        or selected_segment not in bazi_segments
        or not layer_identity_matches
    ):
        findings.append(_finding(
            "fortune_bazi_day_fact_divergence",
            "Near-time layers diverge from the selected authoritative Bazi day segment",
        ))
    shensha = payload.get("shensha_auxiliary") if isinstance(payload.get("shensha_auxiliary"), dict) else {}
    if shensha.get("precedence") != "auxiliary_only" or shensha.get("may_override") != []:
        findings.append(_finding(
            "fortune_invalid_shensha_precedence",
            "Near-time Shensha facts must remain an auxiliary non-overriding layer",
        ))

    natal_pillars = birth.get("natal_pillars") if isinstance(birth.get("natal_pillars"), dict) else {}
    valid_natal_pillars = (
        set(natal_pillars) == {"year", "month", "day", "hour"}
        and all(isinstance(value, str) and len(value) == 2 for value in natal_pillars.values())
    )
    if not valid_natal_pillars:
        findings.append(_finding("fortune_invalid_natal_pillars", "Near-time payload lacks all four natal pillars"))
    else:
        day_master = birth.get("day_master") if isinstance(birth.get("day_master"), dict) else {}
        month_command = birth.get("month_command") if isinstance(birth.get("month_command"), dict) else {}
        if day_master.get("stem") != str(natal_pillars["day"])[0]:
            findings.append(_finding("fortune_day_master_mismatch", "Day master disagrees with the natal day pillar"))
        if month_command.get("branch") != str(natal_pillars["month"])[1]:
            findings.append(_finding("fortune_month_command_mismatch", "Month command disagrees with the natal month pillar"))

    calendar = payload.get("calendar_normalization") if isinstance(payload.get("calendar_normalization"), dict) else {}
    for field in ("timezone", "location", "solar_date", "lunar_date", "ganzhi"):
        if not _has_key(calendar, field):
            findings.append(_finding(f"fortune_missing_calendar:{field}", f"Missing near-time calendar field: {field}"))
    if calendar.get("solar_date") != payload.get("target_date"):
        findings.append(_finding("fortune_target_calendar_mismatch", "Target date disagrees with normalized calendar date"))

    probes = payload.get("probe_times")
    if not isinstance(probes, list) or len(probes) < 2:
        findings.append(_finding("fortune_missing_probes", "Near-time payload needs at least two probes"))
    else:
        try:
            [datetime.fromisoformat(str(value)) for value in probes]
        except ValueError:
            findings.append(_finding("fortune_invalid_probes", "Near-time probe timestamps are not ISO-8601"))

    retired_fields = {
        "daywide_primary",
        "auxiliary_lenses",
        "domain_hypotheses",
        "interpretive_synthesis",
        "phase_profiles",
    }
    present_retired = sorted(retired_fields.intersection(payload))
    if present_retired:
        findings.append(_finding(
            "fortune_retired_semantic_fields",
            "Near-time payload still contains retired prose-selection fields: " + ", ".join(present_retired),
        ))

    ganzhi = calendar.get("ganzhi") if isinstance(calendar.get("ganzhi"), dict) else {}
    transit_layers = payload.get("transit_layers") if isinstance(payload.get("transit_layers"), dict) else {}
    if set(transit_layers) != {"major_luck", "year", "month", "day"}:
        findings.append(_finding("fortune_missing_transit_layers", "Near-time payload needs major-luck, year, month, and day layers"))
    expected_pillars = {
        "major_luck": birth.get("active_luck_cycle"),
        "year": ganzhi.get("year"),
        "month": ganzhi.get("month"),
        "day": ganzhi.get("day"),
    }
    for layer_name, expected_pillar in expected_pillars.items():
        layer = transit_layers.get(layer_name) if isinstance(transit_layers.get(layer_name), dict) else {}
        if layer.get("pillar") != expected_pillar or layer.get("layer") != layer_name:
            findings.append(_finding(
                f"fortune_transit_layer_mismatch:{layer_name}",
                f"Transit layer {layer_name} disagrees with calculated facts",
            ))
        if (
            not _has_key(layer, "stem_ten_god")
            or not isinstance(layer.get("branch_hidden_ten_gods"), list)
            or not isinstance(layer.get("branch_relations_to_natal"), list)
        ):
            findings.append(_finding(
                f"fortune_incomplete_transit_layer:{layer_name}",
                f"Transit layer {layer_name} lacks ten-god or branch-relation facts",
            ))

    mechanism_stack = payload.get("mechanism_stack") if isinstance(payload.get("mechanism_stack"), dict) else {}
    target_day = mechanism_stack.get("target_day") if isinstance(mechanism_stack.get("target_day"), dict) else {}
    day_layer = transit_layers.get("day") if isinstance(transit_layers.get("day"), dict) else {}
    expected_target = {
        "pillar": day_layer.get("pillar"),
        "stem": day_layer.get("stem"),
        "branch": day_layer.get("branch"),
        "stem_ten_god": day_layer.get("stem_ten_god"),
        "branch_hidden_ten_gods": day_layer.get("branch_hidden_ten_gods"),
        "relations_to_natal": day_layer.get("branch_relations_to_natal"),
    }
    if target_day != expected_target:
        findings.append(_finding("fortune_target_mechanism_mismatch", "Mechanism target day disagrees with the day transit layer"))
    if mechanism_stack.get("active_layers") != transit_layers:
        findings.append(_finding("fortune_active_layers_mismatch", "Mechanism stack does not bind the exact active transit layers"))
    natal_baseline = mechanism_stack.get("natal_baseline") if isinstance(
        mechanism_stack.get("natal_baseline"), dict
    ) else {}
    expected_baseline = {
        "day_master": birth.get("day_master"),
        "month_command": birth.get("month_command"),
        "seasonal_profile": birth.get("seasonal_profile"),
        "tiaohou_markers": birth.get("tiaohou_markers"),
        "element_inventory": birth.get("element_inventory"),
        "strength_evidence": birth.get("strength_evidence"),
    }
    if natal_baseline != expected_baseline:
        findings.append(_finding("fortune_natal_baseline_mismatch", "Mechanism stack does not bind the exact natal baseline"))

    decisive = mechanism_stack.get("decisive_mechanisms")
    decisive_ids: list[str] = []
    if not isinstance(decisive, list) or not decisive:
        findings.append(_finding("fortune_missing_decisive_mechanisms", "Mechanism stack lacks decisive current mechanisms"))
    else:
        decisive_ids = [
            str(item.get("id"))
            for item in decisive
            if isinstance(item, dict) and item.get("id")
        ]
        if len(decisive_ids) != len(decisive) or len(set(decisive_ids)) != len(decisive_ids):
            findings.append(_finding("fortune_invalid_mechanism_ids", "Decisive mechanism IDs must be present and unique"))
        allowed_families = {
            "transit_day_stem",
            "transit_day_branch_relations",
            "transit_day_multi_branch_formations",
        }
        if any(
            not isinstance(item, dict) or item.get("source_family") not in allowed_families
            for item in decisive
        ):
            findings.append(_finding("fortune_invalid_mechanism_family", "Decisive mechanisms use an unsupported source family"))
        if "day-stem-ten-god" not in decisive_ids:
            findings.append(_finding("fortune_missing_day_stem_mechanism", "Mechanism stack lacks the target day stem relation"))
        relation_mechanisms = [
            item
            for item in decisive
            if isinstance(item, dict) and item.get("source_family") == "transit_day_branch_relations"
        ]
        expected_relations = day_layer.get("branch_relations_to_natal")
        relation_facts = [
            {
                key: item.get(key)
                for key in (
                    "transit_branch",
                    "natal_position",
                    "natal_position_label",
                    "natal_branch",
                    "relation",
                )
            }
            for item in relation_mechanisms
        ]
        if relation_facts != expected_relations:
            findings.append(_finding("fortune_relation_mechanism_mismatch", "Mechanism records disagree with calculated day-branch relations"))

    formations = mechanism_stack.get("multi_branch_formations")
    day_master_stem = (birth.get("day_master") or {}).get("stem")
    expected_formations = _expected_fortune_formations(
        natal_pillars,
        transit_layers,
        str(day_master_stem or ""),
    )
    if not isinstance(formations, list) or formations != expected_formations:
        findings.append(_finding(
            "fortune_multi_branch_formation_mismatch",
            "Cross-layer formations do not match independently reconstructed natal and timing members",
        ))
        formations = []

    formation_ids = [
        str(item.get("id")) for item in formations
        if isinstance(item, dict) and item.get("id")
    ]
    decisive_formations = [
        item for item in decisive or []
        if isinstance(item, dict)
        and item.get("source_family") == "transit_day_multi_branch_formations"
    ]
    expected_decisive_formations = [{
        **item,
        "category": "multi_branch_formation",
        "source_family": "transit_day_multi_branch_formations",
        "layer": "day_cross_layer",
    } for item in formations]
    if decisive_formations != expected_decisive_formations:
        findings.append(_finding(
            "fortune_multi_branch_formation_mismatch",
            "Decisive mechanisms do not bind the calculated cross-layer formations",
        ))

    resolution = mechanism_stack.get("judgment_resolution")
    expected_primary = formation_ids or [
        str(item.get("id")) for item in decisive or []
        if isinstance(item, dict)
        and item.get("source_family") == "transit_day_branch_relations"
        and item.get("id")
    ] or ["day-stem-ten-god"]
    expected_level = (
        "cross_layer_formation" if formation_ids
        else "day_branch_relation" if expected_primary != ["day-stem-ten-god"]
        else "symbolic_low"
    )
    if (
        not isinstance(resolution, dict)
        or resolution.get("level") != expected_level
        or resolution.get("primary_mechanism_ids") != expected_primary
        or resolution.get("direction_status") != "requires_classical_interpretive_adjudication"
        or resolution.get("specific_life_event_status") != "unsupported_without_user_context"
    ):
        findings.append(_finding(
            "fortune_judgment_resolution_mismatch",
            "Judgment resolution does not prioritize the strongest calculated mechanism",
        ))
    # Fourth-acceptance P0-1 + P1-2: judgment_resolution MUST NOT carry any
    # `resolution_reason` in the fact layer. The reason is bound to real
    # records and conditions during evidence-bundle compilation. If the fact
    # adapter emits any resolution_reason (including a fake one), reject it.
    if isinstance(resolution, dict) and "resolution_reason" in resolution:
        findings.append(_finding(
            "fortune_judgment_resolution_reason_invalid",
            (
                "mechanism_stack.judgment_resolution.resolution_reason must not be"
                " set at the fact layer; the reason is generated during evidence-bundle"
                " compilation."
            ),
        ))
    if mechanism_stack.get("empirical_independence_claimed") is not False:
        findings.append(_finding("fortune_mechanism_independence_claim", "Traditional mechanism layers cannot claim empirical independence"))

    # Final-acceptance P1-2: validate exact dependency_groups structure.
    relation_ids = [
        str(item.get("id"))
        for item in (decisive or [])
        if isinstance(item, dict)
        and item.get("source_family") == "transit_day_branch_relations"
        and item.get("id")
    ]
    dependency_groups = mechanism_stack.get("dependency_groups")
    expected_dependency_groups = [
        {
            "id": "transit-day-stem",
            "mechanism_ids": ["day-stem-ten-god"],
            "independent_family_count": 1,
        },
        {
            "id": "transit-day-branch-relations",
            "mechanism_ids": relation_ids,
            "independent_family_count": 1,
        },
        {
            "id": "transit-day-multi-branch-formations",
            "mechanism_ids": formation_ids,
            "independent_family_count": 1,
        },
    ]
    if not isinstance(dependency_groups, list) or len(dependency_groups) != 3:
        findings.append(_finding(
            "fortune_dependency_groups_invalid",
            "dependency_groups must contain exactly 3 groups",
        ))
    else:
        for idx, (group, expected_group) in enumerate(
            zip(dependency_groups, expected_dependency_groups)
        ):
            if not isinstance(group, dict):
                findings.append(_finding(
                    "fortune_dependency_groups_invalid",
                    f"dependency_groups[{idx}] must be a mapping",
                ))
                break
            if group.get("id") != expected_group["id"]:
                findings.append(_finding(
                    "fortune_dependency_groups_invalid",
                    f"dependency_groups[{idx}] id must be {expected_group['id']!r}",
                ))
                break
            if group.get("mechanism_ids") != expected_group["mechanism_ids"]:
                findings.append(_finding(
                    "fortune_dependency_groups_invalid",
                    f"dependency_groups[{idx}] mechanism_ids mismatch",
                ))
                break
            if group.get("independent_family_count") != expected_group["independent_family_count"]:
                findings.append(_finding(
                    "fortune_dependency_groups_invalid",
                    f"dependency_groups[{idx}] independent_family_count must be 1",
                ))
                break
    # Fourth-acceptance P1-2: active_layer_metadata.note must be the exact
    # non-independence statement. Falsely claiming empirical independence, a
    # single space, or any other note text is rejected.
    _EXPECTED_ACTIVE_LAYER_NOTE = (
        "traditional layers are compared structurally, not counted as empirical votes"
    )
    # Final-acceptance P1-2: validate exact active_layer_metadata structure.
    active_layer_metadata = mechanism_stack.get("active_layer_metadata")
    if not isinstance(active_layer_metadata, dict):
        findings.append(_finding(
            "fortune_active_layer_metadata_invalid",
            "active_layer_metadata must be a mapping",
        ))
    else:
        if active_layer_metadata.get("id") != "active-timing-layers":
            findings.append(_finding(
                "fortune_active_layer_metadata_invalid",
                "active_layer_metadata.id must be 'active-timing-layers'",
            ))
        elif active_layer_metadata.get("layers") != ["major_luck", "year", "month", "day"]:
            findings.append(_finding(
                "fortune_active_layer_metadata_invalid",
                "active_layer_metadata.layers must be ['major_luck', 'year', 'month', 'day']",
            ))
        elif active_layer_metadata.get("independent_family_count") is not None:
            findings.append(_finding(
                "fortune_active_layer_metadata_invalid",
                "active_layer_metadata.independent_family_count must be null",
            ))
        elif active_layer_metadata.get("note") != _EXPECTED_ACTIVE_LAYER_NOTE:
            findings.append(_finding(
                "fortune_active_layer_metadata_invalid",
                (
                    "active_layer_metadata.note must state exactly that traditional"
                    " layers are compared structurally and are not empirical votes"
                ),
            ))

    source_families = payload.get("source_family_evidence") if isinstance(payload.get("source_family_evidence"), dict) else {}
    relation_family = source_families.get("transit_day_branch_relations") if isinstance(
        source_families.get("transit_day_branch_relations"), dict
    ) else {}
    if relation_family.get("independent_family_count") != 1:
        findings.append(_finding(
            "fortune_relation_pseudoreplication",
            "All relations produced by one transit day branch must remain one dependent source family",
        ))
    if relation_family.get("primary_eligible") is not False:
        findings.append(_finding("fortune_relation_promoted", "Transit branch relations cannot be promoted into independent votes"))

    formation_family = source_families.get("transit_day_multi_branch_formations") if isinstance(
        source_families.get("transit_day_multi_branch_formations"), dict
    ) else {}
    if (
        formation_family.get("independent_family_count") != 1
        or formation_family.get("signals") != formations
        or formation_family.get("primary_eligible") is not bool(formations)
    ):
        findings.append(_finding(
            "fortune_multi_branch_family_mismatch",
            "Cross-layer formations must remain one fact-bound source family",
        ))

    hour_family = source_families.get("transit_hour_stem") if isinstance(
        source_families.get("transit_hour_stem"), dict
    ) else {}
    if hour_family.get("independent_family_count") != 1:
        findings.append(_finding(
            "fortune_hour_pseudoreplication",
            "Repeated hour probes belong to one transit-hour-stem source family",
        ))
    hour_signals = hour_family.get("signals")
    if not isinstance(hour_signals, list) or not hour_signals:
        findings.append(_finding("fortune_missing_hour_signals", "Near-time payload lacks deduplicated hour signals"))
    else:
        unique_stems = {
            item.get("hour_stem")
            for item in hour_signals
            if isinstance(item, dict) and item.get("hour_stem")
        }
        if (
            len(unique_stems) != len(hour_signals)
            or hour_family.get("distinct_signal_count") != len(hour_signals)
        ):
            findings.append(_finding(
                "fortune_hour_signals_not_deduplicated",
                "Transit hour-stem signals must be deduplicated before counting",
            ))

    hour_profiles = payload.get("hour_profiles")
    if not isinstance(hour_profiles, list) or len(hour_profiles) != len(probes or []):
        findings.append(_finding("fortune_invalid_hour_profiles", "Queried hour facts must align with probe timestamps"))
    elif any(
        not isinstance(item, dict)
        or not _has_key(item, "at")
        or not _has_key(item, "hour_ganzhi")
        or not _has_key(item, "hour_stem_ten_god")
        or "lens" in item
        for item in hour_profiles
    ):
        findings.append(_finding("fortune_incomplete_hour_profiles", "Queried hour facts contain missing facts or retired semantic lenses"))

    contract = payload.get("public_claim_contract") if isinstance(payload.get("public_claim_contract"), dict) else {}
    if contract.get("decisive_mechanism_ids") != decisive_ids:
        findings.append(_finding("fortune_contract_mechanism_mismatch", "Public contract does not bind the current decisive mechanisms"))
    if contract.get("primary_mechanism_ids") != expected_primary:
        findings.append(_finding("fortune_contract_primary_mechanism_mismatch", "Public contract does not prioritize the strongest current mechanism"))
    if contract.get("require_phase_narrative") is not False:
        findings.append(_finding("fortune_contract_forces_phases", "Public contract must not require a phase narrative"))
    if contract.get("user_selected_domains_only") is not True:
        findings.append(_finding("fortune_contract_selects_domain", "Only user-selected event contexts may narrow a life domain"))
    if contract.get("supported_specific_events") != [] or contract.get("exact_event_claims") != []:
        findings.append(_finding("fortune_contract_invents_events", "Near-time facts cannot preselect a specific event"))
    if contract.get("required_coverage") != [
        "time_basis",
        "direct_judgment",
        "mechanism_explanation",
    ]:
        findings.append(_finding("fortune_contract_missing_coverage", "Public contract must require facts and mechanisms, not prose slots"))

    dialogue = payload.get("dialogue_contract")
    repair = dialogue.get("repair_after_user_dissatisfaction") if isinstance(dialogue, dict) else None
    continuation = dialogue.get("after_user_answers_probe") if isinstance(dialogue, dict) else None
    if (
        not isinstance(dialogue, dict)
        or dialogue.get("mode") != "answer_then_optional_probe"
        or dialogue.get("question_required") is not False
        or dialogue.get("maximum_follow_up_questions") != 1
        or not isinstance(repair, dict)
        or repair.get("mode") != "recalculate_answer_then_one_open_probe"
        or repair.get("question_required") is not True
        or repair.get("maximum_follow_up_questions") != 1
        or not isinstance(continuation, dict)
        or continuation.get("mode") != "continue_from_user_event_context"
        or continuation.get("reuse_validated_baseline") is not True
        or continuation.get("treat_reply_as_chart_proof") is not False
    ):
        findings.append(_finding(
            "fortune_invalid_dialogue_contract",
            "Daily dialogue must answer first, repair dissatisfaction with one open probe, and continue without confirmation laundering",
        ))

    return findings


def _validate_liuren_payload(payload: dict[str, Any], output: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    adapter = payload.get("adapter") if isinstance(payload.get("adapter"), dict) else {}
    rule_profile = adapter.get("rule_profile") if isinstance(adapter.get("rule_profile"), dict) else {}

    if payload.get("fact_layer_status") != "deterministic_liuren_chart":
        findings.append(_finding("liuren_unverified_fact_status", "Liuren payload lacks deterministic_liuren_chart status"))
    if adapter.get("name") != "mingli-master.liuren_fact_adapter":
        findings.append(_finding("liuren_unverified_adapter", "Liuren payload was not produced by the bundled adapter"))
    if rule_profile.get("transmissions") != "daliuren-daquan-wyg-classical-nine-method-v2":
        findings.append(_finding("liuren_unverified_rule_profile", "Liuren transmission rule profile is not the validated v2 profile"))
    if rule_profile.get("transmission_hidden_stems") != "sexagenary-day-xun-v1":
        findings.append(_finding(
            "liuren_unverified_transmission_hidden_stem_profile",
            "Liuren transmission hidden stems lack the validated day-xun profile",
        ))
    if rule_profile.get("biezhe") not in LIUREN_BIEZHE_PROFILES:
        findings.append(_finding("liuren_missing_biezhe_profile", "Liuren payload lacks an explicit supported yin-biezhe profile"))

    day_hour = output.get("day_hour") if isinstance(output.get("day_hour"), dict) else {}
    day = day_hour.get("day")
    hour = day_hour.get("hour")
    hour_stem_validation = rule_profile.get("hour_stem_validation")
    if hour_stem_validation != "five-rat-strict":
        findings.append(_finding(
            "liuren_missing_hour_stem_validation",
            "Liuren payload lacks a supported structured hour-stem validation policy",
        ))
    if day not in LIUREN_JIAZI or hour not in LIUREN_JIAZI:
        findings.append(_finding("liuren_invalid_day_hour", "Liuren day/hour pillars are not valid sexagenary pillars"))
    elif hour and hour_stem_validation == "five-rat-strict":
        expected_hour_stem = LIUREN_STEMS[
            ((LIUREN_STEMS.index(day[0]) % 5) * 2 + LIUREN_BRANCHES.index(hour[1])) % 10
        ]
        if hour[0] != expected_hour_stem:
            findings.append(_finding("liuren_incompatible_hour_stem", "Liuren hour stem is incompatible with the day stem"))

    calendar = (
        payload.get("calendar_normalization")
        if isinstance(payload.get("calendar_normalization"), dict)
        else {}
    )
    input_payload = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    normalized_input = (
        input_payload.get("normalized_chart_input")
        if isinstance(input_payload.get("normalized_chart_input"), dict)
        else {}
    )
    output_month_general = (
        output.get("month_general")
        if isinstance(output.get("month_general"), dict)
        else {}
    )
    if (
        normalized_input.get("day") != day
        or normalized_input.get("hour") != hour
        or normalized_input.get("month_general")
        != output_month_general.get("branch")
    ):
        findings.append(_finding(
            "liuren_input_output_mismatch",
            "Liuren normalized chart input and output pillars/month general must agree",
        ))
    calendar_status = calendar.get("status")
    datetime_context_present = any(
        key in input_payload
        for key in (
            "civil_datetime",
            "timezone",
            "zi_hour_policy",
            "longitude",
            "latitude",
            "coordinate_source",
            "coordinate_accuracy_meters",
        )
    )
    if (
        calendar_status not in {"calculated", "supplied_chart_inputs"}
        or (datetime_context_present and calendar_status != "calculated")
        or (
            not datetime_context_present
            and calendar_status != "supplied_chart_inputs"
        )
    ):
        findings.append(_finding(
            "liuren_calendar_status_mismatch",
            "Liuren calendar status must match datetime or supplied-chart input mode",
        ))
    if calendar_status == "calculated":
        calendar_ganzhi = (
            calendar.get("ganzhi") if isinstance(calendar.get("ganzhi"), dict) else {}
        )
        if (
            calendar_ganzhi.get("day") != day
            or calendar_ganzhi.get("hour") != hour
            or normalized_input.get("day") != day
            or normalized_input.get("hour") != hour
        ):
            findings.append(_finding(
                "liuren_calendar_output_mismatch",
                "Liuren calendar, normalized input, and output day/hour pillars must agree",
            ))
        calendar_policy = calendar.get("zi_hour_policy")
        convention = (
            calendar.get("calendar_convention")
            if isinstance(calendar.get("calendar_convention"), dict)
            else {}
        )
        if (
            input_payload.get("zi_hour_policy") != calendar_policy
            or convention.get("zi_hour_policy") != calendar_policy
        ):
            findings.append(_finding(
                "liuren_calendar_input_policy_mismatch",
                "Liuren input and calendar Zi-hour policies must agree",
            ))
        calendar_location = (
            calendar.get("location") if isinstance(calendar.get("location"), dict) else {}
        )
        input_civil = str(input_payload.get("civil_datetime") or "")
        calendar_civil = str(calendar.get("civil_datetime") or "")
        try:
            parsed_input_civil = datetime.fromisoformat(input_civil)
            parsed_calendar_civil = datetime.fromisoformat(calendar_civil)
            if parsed_input_civil.tzinfo is None:
                civil_context_matches = (
                    parsed_input_civil
                    == parsed_calendar_civil.replace(tzinfo=None)
                )
            else:
                civil_context_matches = (
                    parsed_input_civil == parsed_calendar_civil
                )
        except ValueError:
            civil_context_matches = False
        input_coordinate_source = (
            input_payload.get("coordinate_source") or "not_supplied"
        )
        if (
            not civil_context_matches
            or input_payload.get("timezone") != calendar.get("timezone")
            or input_payload.get("location") != calendar_location.get("name")
            or input_payload.get("longitude") != calendar_location.get("longitude")
            or input_payload.get("latitude") != calendar_location.get("latitude")
            or input_coordinate_source
            != calendar_location.get("coordinate_source")
            or input_payload.get("coordinate_accuracy_meters")
            != calendar_location.get("coordinate_accuracy_meters")
        ):
            findings.append(_finding(
                "liuren_calendar_input_context_mismatch",
                "Liuren input and calendar datetime/location context must agree",
            ))
        try:
            expected_calendar = normalize_calendar(
                str(input_payload.get("civil_datetime") or ""),
                timezone_name=str(input_payload.get("timezone") or ""),
                location=str(input_payload.get("location") or ""),
                longitude=input_payload.get("longitude"),
                latitude=input_payload.get("latitude"),
                coordinate_source=input_payload.get("coordinate_source"),
                coordinate_accuracy_meters=input_payload.get(
                    "coordinate_accuracy_meters"
                ),
                zi_hour_policy=str(input_payload.get("zi_hour_policy") or ""),
                time_basis_policy=str(
                    input_payload.get("time_basis_policy") or "civil"
                ),
            )
            calendar_matches_input = (
                validate_calendar_digest(calendar)
                == expected_calendar["calendar_digest"]
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            calendar_matches_input = False
        if not calendar_matches_input:
            findings.append(_finding(
                "liuren_calendar_input_digest_mismatch",
                "Liuren calendar must be the exact normalization of its bound input under the declared time-basis policy",
            ))
        previous_term = (
            expected_calendar.get("solar_terms", {}).get("previous", {})
            if calendar_matches_input
            else {}
        )
        expected_month_general = TERM_TO_MONTH_GENERAL.get(
            previous_term.get("name")
        )
        if (
            expected_month_general is None
            or output_month_general.get("branch") != expected_month_general
        ):
            findings.append(_finding(
                "liuren_calendar_month_general_mismatch",
                "Liuren month general must match the verified current solar-term pair",
            ))
    elif calendar_status == "supplied_chart_inputs":
        if set(normalized_input) != {"day", "hour", "month_general"}:
            findings.append(_finding(
                "liuren_supplied_input_shape_mismatch",
                "Liuren supplied-chart input must contain only day, hour, and month general",
            ))
        expected_supplied_calendar = {
            "status": "supplied_chart_inputs",
            "civil_datetime": "not_supplied",
            "lunar_date": {"status": "not_calculated_in_chart_mode"},
            "ganzhi": {"day": day, "hour": hour},
            "solar_terms": {
                "status": "month_general_supplied",
                "month_general": output_month_general.get("branch"),
            },
        }
        if calendar != expected_supplied_calendar:
            findings.append(_finding(
                "liuren_supplied_calendar_mismatch",
                "Liuren supplied-chart calendar and output must agree",
            ))

    earth_plate = output.get("earth_plate")
    if earth_plate != list(LIUREN_BRANCHES):
        findings.append(_finding("liuren_invalid_earth_plate", "Liuren earth plate must contain the twelve branches in fixed order"))

    heaven_rows = output.get("heaven_plate")
    plate_map: dict[str, str] = {}
    if not isinstance(heaven_rows, list) or len(heaven_rows) != 12:
        findings.append(_finding("liuren_invalid_heaven_plate", "Liuren heaven plate must contain twelve rows"))
    else:
        try:
            plate_map = {row["earth"]: row["heaven"] for row in heaven_rows if isinstance(row, dict)}
        except (KeyError, TypeError):
            plate_map = {}
        if set(plate_map) != set(LIUREN_BRANCHES) or set(plate_map.values()) != set(LIUREN_BRANCHES):
            findings.append(_finding("liuren_heaven_plate_not_bijection", "Liuren heaven plate is not a twelve-branch bijection"))
        else:
            offsets = {
                (LIUREN_BRANCHES.index(heaven) - LIUREN_BRANCHES.index(earth)) % 12
                for earth, heaven in plate_map.items()
            }
            if len(offsets) != 1 or output.get("plate_offset") not in offsets:
                findings.append(_finding("liuren_inconsistent_plate_offset", "Liuren heaven plate does not have one declared rotation offset"))

    month_general = output.get("month_general") if isinstance(output.get("month_general"), dict) else {}
    month_general_branch = month_general.get("branch")
    if month_general_branch not in LIUREN_BRANCHES:
        findings.append(_finding("liuren_invalid_month_general", "Liuren month general is missing or invalid"))
    elif month_general.get("name") != MONTH_GENERAL_NAMES[month_general_branch]:
        findings.append(_finding(
            "liuren_month_general_name_mismatch",
            "Liuren month-general name must match its branch",
        ))
    elif hour in LIUREN_JIAZI and plate_map:
        expected_offset = (LIUREN_BRANCHES.index(month_general_branch) - LIUREN_BRANCHES.index(hour[1])) % 12
        if output.get("plate_offset") != expected_offset:
            findings.append(_finding("liuren_month_general_hour_mismatch", "Liuren month general, hour, and plate offset disagree"))

    lessons = output.get("four_lessons")
    if not isinstance(lessons, list) or len(lessons) != 4:
        findings.append(_finding("liuren_invalid_four_lessons", "Liuren output must contain exactly four lessons"))
    elif day in LIUREN_JIAZI and set(plate_map) == set(LIUREN_BRANCHES):
        stem, branch = day
        first_lodge = LIUREN_STEM_LODGE[stem]
        first_upper = plate_map[first_lodge]
        second_upper = plate_map[first_upper]
        third_upper = plate_map[branch]
        fourth_upper = plate_map[third_upper]
        expected = (
            (stem, first_lodge, first_upper),
            (first_upper, first_upper, second_upper),
            (branch, branch, third_upper),
            (third_upper, third_upper, fourth_upper),
        )
        actual = tuple(
            (item.get("lower"), item.get("lower_lodge"), item.get("upper"))
            for item in lessons
            if isinstance(item, dict)
        )
        if actual != expected:
            findings.append(_finding("liuren_four_lessons_do_not_match_plate", "Liuren four lessons do not recompute from the day and heaven plate"))

    transmissions = output.get("three_transmissions")
    transmission_branches: list[str] = []
    if not isinstance(transmissions, list) or len(transmissions) != 3:
        findings.append(_finding("liuren_invalid_three_transmissions", "Liuren output must contain exactly three transmissions"))
    else:
        transmission_branches = [item.get("branch", "") for item in transmissions if isinstance(item, dict)]
        stages = [item.get("stage") for item in transmissions if isinstance(item, dict)]
        if stages != ["initial", "middle", "final"] or any(branch not in LIUREN_BRANCHES for branch in transmission_branches):
            findings.append(_finding("liuren_invalid_three_transmissions", "Liuren transmission stages or branches are invalid"))
        elif day in LIUREN_JIAZI:
            start = (LIUREN_JIAZI_CYCLE.index(day) // 10) * 10
            xun_rows = LIUREN_JIAZI_CYCLE[start : start + 10]
            stem_by_branch = {ganzhi[1]: ganzhi[0] for ganzhi in xun_rows}
            expected_empty = [
                branch for branch in LIUREN_BRANCHES if branch not in stem_by_branch
            ]
            xunkong = (
                output.get("xunkong")
                if isinstance(output.get("xunkong"), dict)
                else {}
            )
            if (
                xunkong.get("xun") != xun_rows[0]
                or xunkong.get("branches") != expected_empty
            ):
                findings.append(_finding(
                    "liuren_xunkong_mismatch",
                    "Liuren Xunkong must match the occupied branches of the day xun",
                ))
            for item in transmissions:
                if not isinstance(item, dict) or "hidden_stem" not in item:
                    findings.append(_finding(
                        "liuren_missing_transmission_hidden_stem",
                        "Every Liuren transmission must publish its day-xun hidden stem",
                    ))
                    break
                if item.get("hidden_stem") != stem_by_branch.get(item.get("branch")):
                    findings.append(_finding(
                        "liuren_transmission_hidden_stem_mismatch",
                        "Liuren transmission hidden stem does not match the day xun",
                    ))
                    break

    method = output.get("transmission_method") if isinstance(output.get("transmission_method"), dict) else {}
    if method.get("calculation_source") != "classical_nine-method_algorithm":
        findings.append(_finding("liuren_unverified_transmission_source", "Liuren transmissions were not marked as classical algorithm output"))
    if transmission_branches:
        rendered = "".join(transmission_branches)
        if method.get("selected_initial") != transmission_branches[0] or method.get("calculated_transmissions") != rendered:
            findings.append(_finding("liuren_transmission_trace_mismatch", "Liuren transmission method trace disagrees with the three transmissions"))

    generals = output.get("heavenly_generals")
    if not isinstance(generals, list) or len(generals) != 12:
        findings.append(_finding("liuren_invalid_heavenly_generals", "Liuren output must contain twelve heavenly generals"))
    else:
        earths = {item.get("earth") for item in generals if isinstance(item, dict)}
        heavens = {item.get("heaven") for item in generals if isinstance(item, dict)}
        names = {item.get("general") for item in generals if isinstance(item, dict)}
        if earths != set(LIUREN_BRANCHES) or heavens != set(LIUREN_BRANCHES) or names != LIUREN_GENERALS:
            findings.append(_finding("liuren_invalid_heavenly_generals", "Liuren heavenly-general rows are incomplete or duplicated"))

    return findings


def canonical_system(system: str) -> str:
    return SYSTEM_ALIASES.get(system, system)


def _validate_qimen_payload(
    payload: dict[str, Any], output: dict[str, Any]
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if payload.get("fact_layer_status") != "deterministic_qimen_chart":
        findings.append(_finding(
            "qimen_invalid_status",
            "Qimen production facts must come from the deterministic board adapter",
        ))
    ju = output.get("ju") if isinstance(output.get("ju"), dict) else {}
    number = ju.get("number")
    if (
        isinstance(number, bool)
        or not isinstance(number, int)
        or number not in range(1, 10)
        or output.get("dun") not in {"yang", "yin"}
        or output.get("yuan") not in {"upper", "middle", "lower"}
    ):
        findings.append(_finding(
            "qimen_invalid_ju",
            "Qimen Ju must declare Dun, Yuan, and a Ju number from one to nine",
        ))
    palaces = output.get("palaces") if isinstance(output.get("palaces"), list) else []
    palace_ids = {
        row.get("palace")
        for row in palaces
        if isinstance(row, dict)
    }
    if len(palaces) != 9 or palace_ids != set(range(1, 10)):
        findings.append(_finding(
            "qimen_invalid_palaces",
            "Qimen output must contain each of the nine palaces exactly once",
        ))
    else:
        earth_stems = {
            row.get("earth_stem") for row in palaces if isinstance(row, dict)
        }
        star_count = sum(
            len(row.get("stars") or ())
            for row in palaces
            if isinstance(row, dict)
        )
        heaven_stem_count = sum(
            len(row.get("heaven_stems") or ())
            for row in palaces
            if isinstance(row, dict)
        )
        door_count = sum(
            bool(row.get("door")) for row in palaces if isinstance(row, dict)
        )
        deity_count = sum(
            bool(row.get("deity")) for row in palaces if isinstance(row, dict)
        )
        if earth_stems != set("戊己庚辛壬癸丁丙乙"):
            findings.append(_finding(
                "qimen_invalid_earth_plate",
                "Qimen earth plate must contain the six instruments and three wonders exactly once",
            ))
        if star_count != 9 or heaven_stem_count != 9:
            findings.append(_finding(
                "qimen_invalid_stars",
                "Qimen rotating plate must contain nine stars and nine heaven tokens",
            ))
        if door_count != 8:
            findings.append(_finding(
                "qimen_invalid_doors",
                "Qimen rotating plate must contain eight doors",
            ))
        if deity_count != 8:
            findings.append(_finding(
                "qimen_invalid_deities",
                "Qimen rotating plate must contain eight deities",
            ))
    instruments_wonders = (
        output.get("instruments_wonders")
        if isinstance(output.get("instruments_wonders"), dict)
        else {}
    )
    six_instruments = instruments_wonders.get("six_instruments")
    three_wonders = instruments_wonders.get("three_wonders")
    earth_tokens = instruments_wonders.get("earth_plate")
    heaven_tokens = instruments_wonders.get("heaven_plate")
    token_kinds = {
        **{stem: "six_instrument" for stem in "戊己庚辛壬癸"},
        **{stem: "three_wonder" for stem in "乙丙丁"},
    }

    def valid_typed_tokens(rows: Any) -> bool:
        return (
            isinstance(rows, list)
            and len(rows) == 9
            and all(
                isinstance(row, dict)
                and row.get("palace") in range(1, 10)
                and row.get("stem") in token_kinds
                and row.get("kind") == token_kinds[row["stem"]]
                for row in rows
            )
        )

    if (
        six_instruments != list("戊己庚辛壬癸")
        or three_wonders != list("乙丙丁")
        or not valid_typed_tokens(earth_tokens)
        or not valid_typed_tokens(heaven_tokens)
    ):
        findings.append(_finding(
            "qimen_invalid_instruments_wonders",
            "Qimen must type all nine earth and heaven tokens as six instruments or three wonders",
        ))
    chief = output.get("chief") if isinstance(output.get("chief"), dict) else {}
    director = output.get("director") if isinstance(output.get("director"), dict) else {}
    if not _valid_text(chief.get("star")) or chief.get("destination_palace") not in range(1, 10):
        findings.append(_finding("qimen_invalid_chief", "Qimen chief star placement is incomplete"))
    if not _valid_text(director.get("door")) or director.get("destination_palace") not in range(1, 10):
        findings.append(_finding("qimen_invalid_director", "Qimen director door placement is incomplete"))
    xunkong = output.get("xunkong") if isinstance(output.get("xunkong"), dict) else {}
    if (
        xunkong.get("xun") not in {"甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅"}
        or not isinstance(xunkong.get("branches"), list)
        or len(xunkong.get("branches")) != 2
    ):
        findings.append(_finding("qimen_invalid_xunkong", "Qimen Xunkong facts are incomplete"))
    patterns = output.get("named_patterns")
    if not isinstance(patterns, list) or any(
        not isinstance(row, dict)
        or row.get("status") != "predicate_matched_not_verdict"
        or "verdict" in row
        for row in patterns
    ):
        findings.append(_finding(
            "qimen_invalid_pattern_facts",
            "Qimen named patterns must be calculated predicate matches without verdicts",
        ))
    return findings


def _validate_taiyi_payload(
    payload: dict[str, Any],
    output: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if payload.get("fact_layer_status") != "deterministic_taiyi_annual_board":
        findings.append(_finding(
            "taiyi_invalid_status",
            "Taiyi deterministic facts require the annual-board status",
        ))
    if payload.get("fact_layer_scope") != "annual_macro_historical_board_facts":
        findings.append(_finding(
            "taiyi_invalid_scope",
            "Taiyi provider scope must remain annual macro/historical board facts",
        ))
    required_maps = (
        "calendar",
        "epoch",
        "cycle",
        "board",
        "host_guest",
        "four_generals",
        "long_cycle_deities",
        "scope_contract",
    )
    for key in required_maps:
        if not isinstance(output.get(key), dict) or not output[key]:
            findings.append(_finding(
                f"taiyi_invalid_{key}",
                f"Taiyi {key} must be a non-empty structured fact layer",
            ))
    cycle = output.get("cycle") if isinstance(output.get("cycle"), dict) else {}
    bureau = cycle.get("bureau")
    if (
        isinstance(bureau, bool)
        or not isinstance(bureau, int)
        or not 1 <= bureau <= 72
    ):
        findings.append(_finding(
            "taiyi_invalid_cycle",
            "Taiyi cycle requires a bureau from 1 through 72",
        ))
    for field in (
        "taiyi",
        "tianmu",
        "tianmu_position",
        "jishen",
        "shiji",
    ):
        if not isinstance(output.get(field), str) or not output[field].strip():
            findings.append(_finding(
                "taiyi_invalid_board",
                f"Taiyi board is missing {field}",
            ))
    host_guest = (
        output.get("host_guest")
        if isinstance(output.get("host_guest"), dict)
        else {}
    )
    for side in ("host", "guest"):
        row = host_guest.get(side) if isinstance(host_guest.get(side), dict) else {}
        count = row.get("count")
        major = row.get("major_general_palace")
        assistant = row.get("assistant_general_palace")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count <= 0
            or isinstance(major, bool)
            or not isinstance(major, int)
            or not 1 <= major <= 9
            or isinstance(assistant, bool)
            or not isinstance(assistant, int)
            or not 1 <= assistant <= 9
        ):
            findings.append(_finding(
                "taiyi_invalid_host_guest",
                f"Taiyi {side} count and general facts are incomplete",
            ))
    long_cycle = (
        output.get("long_cycle_deities")
        if isinstance(output.get("long_cycle_deities"), dict)
        else {}
    )
    required_deities = {
        "junji", "chenji", "minji", "wufu", "dayou", "xiaoyou",
        "sishen", "tianyi", "diyi", "zhifu",
    }
    if set(long_cycle) != required_deities or any(
        not isinstance(row, dict)
        or not row.get("position")
        or not row.get("epoch_profile")
        or not row.get("source_anchor")
        for row in long_cycle.values()
    ):
        findings.append(_finding(
            "taiyi_invalid_long_cycle_deities",
            "Taiyi requires all ten independently epoch-bound long-cycle deity facts",
        ))
    predicates = output.get("board_predicates")
    if not isinstance(predicates, list) or any(
        not isinstance(row, dict)
        or not re.fullmatch(r"TY-P(?:0[1-9]|10)", str(row.get("id") or ""))
        or row.get("status") != "predicate_matched_not_verdict"
        or not isinstance(row.get("fact_paths"), list)
        or not row.get("fact_paths")
        for row in predicates or ()
    ):
        findings.append(_finding(
            "taiyi_invalid_board_predicates",
            "Taiyi board predicates must be exact fact-bound non-verdict records",
        ))
    scope = (
        output.get("scope_contract")
        if isinstance(output.get("scope_contract"), dict)
        else {}
    )
    if (
        scope.get("declared_scope") != "annual_macro_historical_board_facts"
        or scope.get("supported_objects") != ["macro_historical"]
        or scope.get("supported_horizons") != ["year"]
    ):
        findings.append(_finding(
            "taiyi_invalid_scope_contract",
            "Taiyi output must retain its annual macro/historical scope contract",
        ))
    digest = output.get("board_digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        findings.append(_finding(
            "taiyi_invalid_board_digest",
            "Taiyi output requires a SHA-256 board digest",
        ))
    return findings


def _normalize_contract_findings(
    system: str,
    returned: Any,
) -> list[dict[str, str]]:
    """Coerce a contract's ``validate_output`` return into lawful findings.

    The hook contract is ``list[Finding]`` where every finding carries
    string ``level``/``code``/``message``. Anything else - a mapping, a
    string, an item missing keys, an unknown level - is converted into an
    explicit structured finding, so ``validate_payload`` never raises and
    never merges an alien shape into its report.
    """

    if not isinstance(returned, list):
        return [_finding(
            "fact_contract_invalid_return",
            f"Provider fact contract for {system} returned a non-list value:"
            f" {type(returned).__name__} instead of a finding list",
        )]
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(returned):
        if (
            isinstance(item, dict)
            and item.get("level") in {"error", "warn"}
            and isinstance(item.get("code"), str)
            and item.get("code")
            and isinstance(item.get("message"), str)
        ):
            normalized.append({
                "level": item["level"],
                "code": item["code"],
                "message": item["message"],
            })
        else:
            normalized.append(_finding(
                "fact_contract_invalid_return",
                f"Provider fact contract for {system} produced an invalid"
                f" finding at index {index}:"
                f" {_classify_invalid_finding(item)}",
            ))
    return normalized


def _normalize_contract_required_keys(
    system: str,
    hook_name: str,
    returned: Any,
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    """Validate one required-key hook without iterating an alien value."""

    if type(returned) is not tuple:
        return (), [_finding(
            "fact_contract_invalid_return",
            f"Provider fact contract for {system} returned a non-tuple value"
            f" from {hook_name}: {type(returned).__name__}",
        )]
    if any(type(key) is not str or not key.strip() for key in returned):
        return (), [_finding(
            "fact_contract_invalid_return",
            f"Provider fact contract for {system} returned a non-text or blank"
            f" key from {hook_name}",
        )]
    return returned, []


def _classify_invalid_finding(item: Any) -> str:
    """Name why a contract finding item is unlawful, without echoing it.

    The classification never inlines the item's own content, so a hostile
    or buggy contract cannot smuggle arbitrary text into the report.
    """

    if not isinstance(item, dict):
        return "non-dict item"
    if item.get("level") not in {"error", "warn"}:
        return "invalid level"
    code = item.get("code")
    if not isinstance(code, str) or not code:
        return "missing code"
    return "invalid message"


def _load_fact_contract(
    system: str,
    catalog_root: Path | str | None,
) -> tuple[Any, list[dict[str, str]], bool]:
    """Resolve the optional Provider-owned fact contract for *system*.

    Returns ``(contract_or_None, load_findings, declared)`` where
    ``declared`` says whether the catalog carries a descriptor for the
    system at all. A broken declaration or a broken catalog never raises:
    it degrades into an explicit error finding so callers always receive a
    lawful, non-empty report.
    """

    root = (
        Path(catalog_root)
        if catalog_root is not None
        else _SKILL_ROOT / "resources" / "runtime"
    )
    try:
        # The import lives inside the guard on purpose: a mixed-version
        # install without the fact_contracts package must degrade into a
        # finding exactly like a broken catalog or entrypoint.
        from fact_contracts.registry import FactContractRegistry

        registry = FactContractRegistry(root, skill_root=_SKILL_ROOT)
        contract = registry.resolve(system)
        declared = registry.is_declared(system)
    except Exception as error:  # noqa: BLE001 - never-raise contract
        # The load failed, but the system may still be a declared Provider:
        # answer that question with a descriptor-only lookup so the facade
        # reports an unavailable capability instead of an unknown system.
        declared = False
        try:
            from fact_contracts.registry import FactContractRegistry

            declared = FactContractRegistry(
                root, skill_root=_SKILL_ROOT
            ).is_declared(system)
        except Exception:  # noqa: BLE001 - never-raise contract
            declared = False
        return None, [_finding(
            "fact_contract_load_failed",
            f"Provider fact contract for {system} could not be loaded: {error}",
        )], declared
    return contract, [], declared


def _validate_payload(
    system: str,
    payload: dict[str, Any],
    *,
    evidence_bundle: dict[str, Any] | None = None,
    catalog_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return structured validation findings for a fact-layer payload.

    Fourth-acceptance P0-2: `evidence_bundle` is optional but strongly
    recommended for any payload that carries `public_claim_contract.mechanism_bridges`.
    When bridges are present and evidence_bundle is None, the bridges are
    rejected fail-closed via `fortune_mechanism_bridge_missing_evidence_context`.
    """

    system = canonical_system(system)
    findings: list[dict[str, str]] = []

    if system == "fortune" and isinstance(evidence_bundle, dict):
        expected_facts_digest = evidence_bundle.get("facts_digest")
        current_facts_digest = canonical_facts_digest(payload)
        if expected_facts_digest != current_facts_digest:
            findings.append(_finding(
                "fortune_evidence_facts_digest_mismatch",
                "The evidence bundle is not bound to the current fact payload",
            ))

    # Section 4 hardening: refuse hand-calculated / manual fact layers before any
    # system-specific checks. This closes the loophole where a caller could pass
    # source_tool=manual to bypass deterministic adapters.
    hand_calculated_sources = {
        "manual", "none", "human", "hand", "hand_calculated",
        "vision_ocr", "vision_only", "llm", "gpt", "claude",
    }
    # Audit re-acceptance: check BOTH top-level and nested adapter.source_tool
    # so `adapter.source_tool=manual` cannot slip through.
    candidate_source_tools: list[str] = []
    if isinstance(payload.get("source_tool"), str):
        candidate_source_tools.append(payload["source_tool"].strip().lower())
    if isinstance(payload.get("adapter"), dict) and isinstance(
        payload["adapter"].get("source_tool"), str
    ):
        candidate_source_tools.append(payload["adapter"]["source_tool"].strip().lower())
    bad_source_tool = next(
        (tool for tool in candidate_source_tools if tool in hand_calculated_sources),
        None,
    )
    if bad_source_tool:
        findings.append(_finding(
            "hand_calculated_fact_layer_rejected",
            (
                f"Fact layer source_tool={bad_source_tool!r} is hand-calculated or"
                " model-inferred; formal readings require a deterministic adapter"
            ),
        ))
        return {
            "ok": False,
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }

    # Fourth-acceptance P0-2: any `public_claim_contract.mechanism_bridges`
    # entry must satisfy the strict schema before evidence / gate honour it.
    # The bridge validator receives the evidence bundle so it can verify
    # pack/record/path/hash/digest bindings.
    findings.extend(_validate_mechanism_bridges(payload, evidence_bundle))

    if system == "fortune":
        findings.extend(_validate_fortune_payload(payload))
        return {
            "ok": not any(item["level"] == "error" for item in findings),
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }

    if (
        system == "selection"
        and payload.get("fact_layer_status")
        == "deterministic_selection_candidates"
    ):
        from reading_engine import selection as selection_engine

        report = selection_engine.validate_fact_layer(payload)
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        candidates = (
            output.get("calendar_candidates")
            if isinstance(output.get("calendar_candidates"), list)
            else []
        )
        if any(
            not isinstance(candidate, dict)
            or not isinstance(candidate.get("hour_facts"), list)
            or len(candidate["hour_facts"]) != 12
            or [row.get("branch") for row in candidate["hour_facts"]]
            != list("子丑寅卯辰巳午未申酉戌亥")
            for candidate in candidates
        ):
            findings.append(_finding(
                "selection_invalid_hour_facts",
                "Every Selection candidate must contain twelve ordered deterministic hour facts",
            ))
        for code in report["codes"]:
            findings.append(_finding(code, f"Selection validation failed: {code}"))
        return {
            "ok": not any(item["level"] == "error" for item in findings),
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }

    if (
        system == "fengshui"
        and payload.get("fact_layer_status")
        == "observation_driven_fengshui_facts"
    ):
        from reading_engine import fengshui as fengshui_engine

        report = fengshui_engine.validate_fact_layer(payload)
        existing = {item["code"] for item in findings}
        for item in report["findings"]:
            if item["code"] not in existing:
                findings.append(dict(item))
                existing.add(item["code"])
        return {
            "ok": not any(item["level"] == "error" for item in findings),
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }
    if system == "fengshui":
        findings.append(_finding(
            "fengshui_dedicated_provider_required",
            "Fengshui facts must come from the observation-driven dedicated provider",
        ))
        return {
            "ok": False,
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }

    if (
        system == "physiognomy"
        and payload.get("fact_layer_status")
        == "observation_driven_physiognomy_facts"
    ):
        from reading_engine import physiognomy as physiognomy_engine

        report = physiognomy_engine.validate_fact_layer(payload)
        for code in report["codes"]:
            findings.append(_finding(
                code,
                f"Physiognomy validation failed: {code}",
            ))
        return {
            "ok": not any(item["level"] == "error" for item in findings),
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }
    if system == "physiognomy":
        findings.append(_finding(
            "physiognomy_dedicated_provider_required",
            "Physiognomy facts must come from the bounded observation provider",
        ))
        return {
            "ok": False,
            "system": system,
            "findings": findings,
            "codes": [item["code"] for item in findings],
        }

    fact_contract, contract_load_findings, system_declared = _load_fact_contract(
        system, catalog_root
    )
    findings.extend(contract_load_findings)

    # A contract that sets ``replaces_legacy_validation`` fully owns the
    # system's fact validation: the facade drops the legacy required-output
    # table, system overrides and legacy per-system validators for it.
    contract_owned = fact_contract is not None and bool(
        getattr(fact_contract, "replaces_legacy_validation", False)
    )

    if fact_contract is not None:
        # The legacy bazi conflict finding preceded every generic envelope
        # finding. Keep payload-level contract findings in that same slot so
        # the public finding order remains byte-for-byte compatible.
        payload_hook = getattr(
            fact_contract, "validate_conflict_state", None
        )
        if payload_hook is not None:
            try:
                state_findings = payload_hook(payload)
            except Exception as error:  # noqa: BLE001 - findings stay lawful
                findings.append(_finding(
                    "fact_contract_error",
                    f"Provider fact contract for {system} failed while"
                    f" validating payload state: {error}",
                ))
            else:
                findings.extend(
                    _normalize_contract_findings(system, state_findings)
                )

    if system not in REQUIRED_OUTPUTS and fact_contract is None:
        if system_declared:
            # The catalog knows this Provider, but nothing can validate its
            # facts: report the missing contract explicitly instead of
            # collapsing it into an ambiguous unknown system.
            findings.append(_finding(
                "fact_contract_unavailable",
                f"System {system} declares no usable fact contract; its fact"
                " validation capability is unavailable",
            ))
        else:
            findings.append(_finding("unknown_system", f"Unknown system: {system}"))
        return {"ok": False, "system": system, "findings": findings, "codes": [item["code"] for item in findings]}

    for key in REQUIRED_TOP_LEVEL:
        if not _has_key(payload, key):
            findings.append(_finding(f"missing_top_level:{key}", f"Missing top-level field: {key}"))

    adapter = payload.get("adapter") if isinstance(payload.get("adapter"), dict) else {}
    for key in REQUIRED_ADAPTER:
        if not _has_key(adapter, key):
            findings.append(_finding(f"missing_adapter:{key}", f"Missing adapter field: {key}"))

    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    required_outputs = () if contract_owned else REQUIRED_OUTPUTS.get(system, ())
    if (
        not contract_owned
        and system == "taiyi"
        and payload.get("fact_layer_status") == "deterministic_taiyi_annual_board"
    ):
        required_outputs = (
            "calendar",
            "epoch",
            "cycle",
            "board",
            "host_guest",
            "long_cycle_deities",
            "scope_contract",
        )
    if (
        not contract_owned
        and system == "divination"
        and payload.get("subsystem") in DIVINATION_REQUIRED_OUTPUTS
    ):
        required_outputs = DIVINATION_REQUIRED_OUTPUTS[payload["subsystem"]]
    if fact_contract is not None:
        try:
            returned_required_outputs = fact_contract.required_output_ids(
                payload, tuple(required_outputs)
            )
        except Exception as error:  # noqa: BLE001 - findings must stay lawful
            findings.append(_finding(
                "fact_contract_error",
                f"Provider fact contract for {system} failed while computing"
                f" required outputs: {error}",
            ))
        else:
            required_outputs, invalid_required_outputs = (
                _normalize_contract_required_keys(
                    system,
                    "required_output_ids",
                    returned_required_outputs,
                )
            )
            findings.extend(invalid_required_outputs)
    for key in required_outputs:
        if not _has_key(output, key):
            findings.append(_finding(f"missing_output:{key}", f"Missing {system} output field: {key}"))

    if fact_contract is not None and output:
        try:
            contract_findings = fact_contract.validate_output(payload, output)
        except Exception as error:  # noqa: BLE001 - findings must stay lawful
            findings.append(_finding(
                "fact_contract_error",
                f"Provider fact contract for {system} failed while validating"
                f" output: {error}",
            ))
        else:
            findings.extend(
                _normalize_contract_findings(system, contract_findings)
            )

    if (
        not contract_owned
        and system == "ziwei"
        and output
        and payload.get("fact_layer_status")
        == "calculated_ziwei_chart_from_birth_datetime"
    ):
        findings.extend(_validate_ziwei_calculated_payload(payload, output))

    if not contract_owned and system == "liuren" and output:
        findings.extend(_validate_liuren_payload(payload, output))

    if not contract_owned and system == "qimen" and output:
        findings.extend(_validate_qimen_payload(payload, output))

    if (
        not contract_owned
        and system == "taiyi"
        and output
        and payload.get("fact_layer_status")
        == "deterministic_taiyi_annual_board"
    ):
        findings.extend(_validate_taiyi_payload(payload, output))

    if payload.get("fact_layer_status") == USER_PROVIDED_STATUS:
        provenance = (
            payload.get("input", {}).get("provenance", {})
            if isinstance(payload.get("input"), dict)
            else {}
        )
        if payload.get("fact_layer_scope") != "supplied_facts_only":
            findings.append(_finding(
                "user_chart_invalid_scope",
                "A user-provided chart may authorize supplied facts only",
            ))
        if adapter.get("name") != USER_PROVIDED_ADAPTER:
            findings.append(_finding(
                "user_chart_invalid_adapter",
                "A user-provided chart must be normalized by structured_chart_adapter",
            ))
        if adapter.get("rule_profile") != "user-provided-no-recalculation":
            findings.append(_finding(
                "user_chart_invalid_rule_profile",
                "A user-provided chart must retain the no-recalculation profile",
            ))
        if provenance.get("source_type") not in {"user_text", "image_transcription", "user_file"}:
            findings.append(_finding(
                "user_chart_invalid_source_type",
                "User chart provenance must identify user text, image transcription, or a user file",
            ))
        if provenance.get("calculation_status") != "not_recalculated":
            findings.append(_finding(
                "user_chart_false_recalculation_claim",
                "A structural chart adapter must state not_recalculated",
            ))
        findings.extend(_validate_user_provided_output(
            system,
            str(payload.get("subsystem") or "") or None,
            output,
        ))

    if system not in {"fengshui", "physiognomy"}:
        calendar = payload.get("calendar_normalization") if isinstance(payload.get("calendar_normalization"), dict) else {}
        required_calendar = REQUIRED_CALENDAR
        if fact_contract is not None:
            try:
                returned_required_calendar = fact_contract.required_calendar_keys(
                    payload, REQUIRED_CALENDAR
                )
            except Exception as error:  # noqa: BLE001 - findings must stay lawful
                findings.append(_finding(
                    "fact_contract_error",
                    f"Provider fact contract for {system} failed while computing"
                    f" calendar requirements: {error}",
                ))
            else:
                required_calendar, invalid_required_calendar = (
                    _normalize_contract_required_keys(
                        system,
                        "required_calendar_keys",
                        returned_required_calendar,
                    )
                )
                findings.extend(invalid_required_calendar)
        for key in required_calendar:
            if not _has_key(calendar, key):
                findings.append(_finding(f"missing_calendar:{key}", f"Missing calendar_normalization field: {key}"))
        if calendar.get("status") == "calculated":
            try:
                validate_calendar_digest(calendar)
            except ValueError:
                findings.append(
                    _finding(
                        "calendar_digest_mismatch",
                        "Shared calendar facts are missing their digest or were modified after normalization",
                    )
                )
    elif not _has_key(payload, "calendar_normalization"):
        findings.append(
            _finding(
                "missing_calendar:calendar_normalization",
                "Missing calendar_normalization; use explicit not_applicable only for non-time fengshui tasks",
                "warn",
            )
        )

    if not payload.get("trace"):
        findings.append(_finding("missing_trace", "Missing trace list for reproducibility", "warn"))

    return {
        "ok": not any(item["level"] == "error" for item in findings),
        "system": system,
        "findings": findings,
        "codes": [item["code"] for item in findings],
    }


def validate_payload(
    system: str,
    payload: dict[str, Any],
    *,
    evidence_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one fact payload through the stable public facade."""

    return _validate_payload(
        system,
        payload,
        evidence_bundle=evidence_bundle,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True, help="System key, e.g. bazi, ziwei, liuren, selection")
    parser.add_argument("--file", required=True, help="JSON adapter payload")
    args = parser.parse_args()

    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    result = validate_payload(args.system, payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
