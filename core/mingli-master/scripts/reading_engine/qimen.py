"""Deterministic Shijia rotating-plate Qimen facts for the selected profile."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import calendar_core, evidence_rules


SCHEMA_VERSION = "mingli-qimen-facts-v1"
ADAPTER_VERSION = "5.2.0"
PROFILE_ID = "shijia-zhuanpan-chaibu-xieji-v1"
PROVIDER_VERSION = ADAPTER_VERSION
TABLE_PROFILE = PROFILE_ID
SOURCE_TABLE_RELPATH = Path("references/matrices/qimen-source-tables-v1.yaml")
SOURCE_TABLE_SHA256 = "9cde893927111cf82fdc14e414c9e46a2168a2cc012ef282340732155eba7a0f"
TABLE_SHA256 = SOURCE_TABLE_SHA256
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
JIAZI = tuple(
    STEMS[index % 10] + BRANCHES[index % 12]
    for index in range(60)
)
XUN_HEADS = ("甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅")
SOURCE_DEPENDENCIES = (
    "qimen.calendar.dun-yuan-ju",
    "qimen.plate.instruments-wonders-palaces",
    "qimen.plate.chief-director-stars-doors-deities",
    "qimen.markers.xunkong-horse",
    "qimen.patterns.board-predicates",
)
UPPER_YUAN_BRANCHES = frozenset("子午卯酉")
MIDDLE_YUAN_BRANCHES = frozenset("寅申巳亥")
LOWER_YUAN_BRANCHES = frozenset("辰戌丑未")
OPPOSITE_PALACE = {1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4}
FIVE_NOT_MEET_HOUR_STEM = {
    "甲": "庚", "乙": "辛", "丙": "壬", "丁": "癸", "戊": "甲",
    "己": "乙", "庚": "丙", "辛": "丁", "壬": "戊", "癸": "己",
}
PATTERN_UNRESOLVED_CHECKS = (
    "格局强弱、制化与并见关系",
    "事项用神及宫位关系",
    "事件成败、吉凶与应期",
)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def source_table() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    path = root / SOURCE_TABLE_RELPATH
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_TABLE_SHA256:
        raise RuntimeError(f"Qimen source table checksum mismatch: {digest}")
    payload = yaml.safe_load(raw.decode("utf-8"))
    if payload.get("schema_version") != "mingli-qimen-source-tables-v1":
        raise RuntimeError("unsupported Qimen source table schema")
    if (payload.get("selected_convention") or {}).get("id") != PROFILE_ID:
        raise RuntimeError("Qimen source table selected convention mismatch")
    default_definition = str(
        payload.get("named_pattern_definition_default") or ""
    )
    if not default_definition:
        raise RuntimeError("missing Qimen named-pattern definition version")
    for profile in payload.get("named_pattern_predicates") or ():
        profile.setdefault("definition_version", default_definition)
        profile.setdefault("source_profile", "qimen_tongzong")
    return payload


def source_table_digest() -> str:
    source_table()
    return SOURCE_TABLE_SHA256


def _require_ganzhi(value: str, *, label: str) -> int:
    try:
        return JIAZI.index(str(value))
    except ValueError as exc:
        raise ValueError(f"{label} must be one sexagenary stem-branch pair") from exc


def _symbol_head(day_ganzhi: str) -> str:
    index = _require_ganzhi(day_ganzhi, label="day_ganzhi")
    return JIAZI[index - index % 5]


def _yuan(symbol_head: str) -> str:
    branch = symbol_head[1]
    if branch in UPPER_YUAN_BRANCHES:
        return "upper"
    if branch in MIDDLE_YUAN_BRANCHES:
        return "middle"
    if branch in LOWER_YUAN_BRANCHES:
        return "lower"
    raise ValueError("unresolved Qimen Yuan")  # pragma: no cover


def _xun_profile(hour_ganzhi: str) -> tuple[str, int, dict[str, Any]]:
    index = _require_ganzhi(hour_ganzhi, label="hour_ganzhi")
    xun_index = index - index % 10
    xun = JIAZI[xun_index]
    profile = (source_table().get("xun_profiles") or {}).get(xun)
    if not isinstance(profile, dict):
        raise RuntimeError(f"missing Qimen Xun profile: {xun}")
    return xun, index - xun_index, profile


def _host_center(palace: int) -> int:
    return 2 if palace == 5 else palace


def _earth_plate(ju: int, dun: str) -> dict[int, str]:
    tokens = list((source_table().get("orders") or {})["earth_plate_tokens"])
    direction = 1 if dun == "yang" else -1
    return {
        ((ju - 1 + direction * offset) % 9) + 1: str(token)
        for offset, token in enumerate(tokens)
    }


def _palace_profiles() -> dict[int, dict[str, Any]]:
    return {
        int(palace): dict(profile)
        for palace, profile in (source_table().get("palaces") or {}).items()
    }


def _palace_for_branch(branch: str) -> int:
    for palace, profile in _palace_profiles().items():
        if branch in (profile.get("branches") or ()):
            return palace
    raise ValueError(f"unmapped Qimen branch: {branch}")


def _rotated_mapping(
    home_values: dict[int, str],
    *,
    home_start: int,
    destination: int,
    order_key: str,
) -> dict[int, str]:
    outer = [int(value) for value in source_table()["orders"][order_key]]
    shift = outer.index(destination) - outer.index(home_start)
    return {
        outer[(outer.index(home_palace) + shift) % len(outer)]: value
        for home_palace, value in home_values.items()
    }


def _director_destination(xun_palace: int, offset: int, dun: str) -> int:
    direction = 1 if dun == "yang" else -1
    raw = ((xun_palace - 1 + direction * offset) % 9) + 1
    return _host_center(raw)


def _deity_mapping(destination: int, dun: str) -> dict[int, str]:
    outer = [
        int(value)
        for value in source_table()["orders"]["deity_rotation_outer_palaces"]
    ]
    deities = list(source_table()["orders"]["deities"]["baihu_xuanwu_variant"])
    start = outer.index(destination)
    direction = 1 if dun == "yang" else -1
    return {
        outer[(start + direction * offset) % len(outer)]: str(deity)
        for offset, deity in enumerate(deities)
    }


def _pattern_record(
    profile: Mapping[str, Any],
    *,
    palace: int | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pattern_id = str(profile["id"])
    pattern_name = str(profile["name"])
    rule = _verified_pattern_rule(pattern_id)
    record = {
        "id": pattern_id,
        "name": pattern_name,
        "predicate": str(profile["predicate"]),
        "status": "predicate_matched_not_verdict",
        "source_anchor": str(profile["source_anchor"]),
        "source_profile": str(profile["source_profile"]),
        "definition_version": str(profile["definition_version"]),
        "source_dependency_id": "qimen.patterns.board-predicates",
        "identity_adjudication": {
            "status": "adjudicated_pattern_identity",
            "decision_scope": "qimen_named_pattern_identity",
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "palace": palace,
            "hard_verdict": None,
            "event_verdict": None,
            "source_ref": {
                "pack": rule.source_pack,
                "rule_id": rule.local_rule_id,
                "source_anchor": f"{rule.source_path}#{rule.local_rule_id}",
                "verification_status": rule.classical_binding_status,
                "binding_digest": rule.classical_binding_digest,
            },
            "unresolved_checks": list(PATTERN_UNRESOLVED_CHECKS),
        },
    }
    if palace is not None:
        record["palace"] = palace
    if details:
        record["details"] = copy.deepcopy(dict(details))
    return record


@lru_cache(maxsize=40)
def _verified_pattern_rule(pattern_id: str) -> evidence_rules.EvidenceRule:
    """Resolve one checked Qimen pattern rule by its local table id."""

    matches = [
        rule
        for rule in evidence_rules.production_evidence_rules()
        if rule.system == "qimen" and rule.local_rule_id == pattern_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Qimen pattern requires exactly one evidence rule: {pattern_id}"
        )
    rule = matches[0]
    if (
        not rule.runtime_active
        or rule.classical_binding_status != "verified"
        or not rule.classical_binding_digest
    ):
        raise RuntimeError(f"Qimen pattern rule is not verified: {pattern_id}")
    return rule


def _valid_pattern_adjudication(row: Mapping[str, Any]) -> bool:
    pattern_id = row.get("id")
    pattern_name = row.get("name")
    if not isinstance(pattern_id, str) or not isinstance(pattern_name, str):
        return False
    try:
        rule = _verified_pattern_rule(pattern_id)
    except RuntimeError:
        return False
    return row.get("identity_adjudication") == {
        "status": "adjudicated_pattern_identity",
        "decision_scope": "qimen_named_pattern_identity",
        "pattern_id": pattern_id,
        "pattern_name": pattern_name,
        "palace": row.get("palace"),
        "hard_verdict": None,
        "event_verdict": None,
        "source_ref": {
            "pack": rule.source_pack,
            "rule_id": rule.local_rule_id,
            "source_anchor": f"{rule.source_path}#{rule.local_rule_id}",
            "verification_status": rule.classical_binding_status,
            "binding_digest": rule.classical_binding_digest,
        },
        "unresolved_checks": list(PATTERN_UNRESOLVED_CHECKS),
    }


def detect_named_patterns(board: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Match only source-table predicates against a completed board."""

    palaces = {
        int(row["palace"]): row
        for row in board.get("palaces") or ()
        if isinstance(row, Mapping)
    }
    if set(palaces) != set(range(1, 10)):
        raise ValueError("Qimen pattern detection requires nine palaces")
    matches: list[dict[str, Any]] = []
    day_stem = str((board.get("day_hour") or {}).get("day_ganzhi") or "")[:1]
    hour_stem = str((board.get("day_hour") or {}).get("hour_ganzhi") or "")[:1]
    hour_ganzhi = str((board.get("day_hour") or {}).get("hour_ganzhi") or "")
    calendar_pillars = board.get("calendar_pillars") or {}
    calendar_stems = {
        key: str(calendar_pillars.get(key) or "")[:1]
        for key in ("year", "month", "day", "hour")
    }
    xun = str((board.get("xunkong") or {}).get("xun") or "")
    chief_destination = int((board.get("chief") or {}).get("destination_palace") or 0)
    hidden = str((board.get("chief") or {}).get("hidden_instrument") or "")
    star_palaces = {
        star: palace
        for palace, row in palaces.items()
        for star in row.get("stars") or ()
        if star != "天禽"
    }

    for profile in source_table().get("named_pattern_predicates") or ():
        predicate = str(profile.get("predicate") or "")
        if predicate == "chief_symbol_over_earth_stem":
            row = palaces.get(chief_destination, {})
            if row.get("earth_stem") == profile.get("lower"):
                matches.append(_pattern_record(profile, palace=chief_destination))
        elif predicate == "heaven_stem_over_hidden_jia":
            for palace, row in palaces.items():
                if (
                    row.get("earth_stem") == hidden
                    and profile.get("upper") in (row.get("heaven_stems") or ())
                ):
                    matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "heaven_stem_over_earth_stem":
            for palace, row in palaces.items():
                if (
                    profile.get("upper") in (row.get("heaven_stems") or ())
                    and row.get("earth_stem") == profile.get("lower")
                ):
                    matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "door_heaven_earth":
            for palace, row in palaces.items():
                if (
                    row.get("door") == profile.get("door")
                    and profile.get("upper") in (row.get("heaven_stems") or ())
                    and row.get("earth_stem") == profile.get("lower")
                ):
                    matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "door_heaven_deity":
            for palace, row in palaces.items():
                if (
                    row.get("door") == profile.get("door")
                    and profile.get("upper") in (row.get("heaven_stems") or ())
                    and row.get("deity") == profile.get("deity")
                ):
                    matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "doors_heaven_earth":
            doors = set(profile.get("doors") or ())
            for palace, row in palaces.items():
                if (
                    row.get("door") in doors
                    and profile.get("upper") in (row.get("heaven_stems") or ())
                    and row.get("earth_stem") == profile.get("lower")
                ):
                    matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "doors_heaven_in_palace":
            palace = int(profile.get("palace") or 0)
            row = palaces.get(palace, {})
            if (
                row.get("door") in set(profile.get("doors") or ())
                and profile.get("upper") in (row.get("heaven_stems") or ())
            ):
                matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "door_heaven_in_palace":
            palace = int(profile.get("palace") or 0)
            row = palaces.get(palace, {})
            if (
                row.get("door") == profile.get("door")
                and profile.get("upper") in (row.get("heaven_stems") or ())
            ):
                matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "door_heaven_earth_in_palace":
            palace = int(profile.get("palace") or 0)
            row = palaces.get(palace, {})
            if (
                row.get("door") == profile.get("door")
                and profile.get("upper") in (row.get("heaven_stems") or ())
                and row.get("earth_stem") == profile.get("lower")
            ):
                matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "heaven_stem_over_earth_cases":
            for upper, lower_stems in (profile.get("cases") or {}).items():
                for palace, row in palaces.items():
                    if (
                        upper in (row.get("heaven_stems") or ())
                        and row.get("earth_stem") in set(lower_stems or ())
                    ):
                        matches.append(_pattern_record(profile, palace=palace))
        elif predicate == "director_over_earth_stem":
            director_destination = int(
                (board.get("director") or {}).get("destination_palace") or 0
            )
            row = palaces.get(director_destination, {})
            if row.get("earth_stem") == profile.get("lower"):
                matches.append(
                    _pattern_record(profile, palace=director_destination)
                )
        elif predicate == "heaven_stem_over_calendar_stem":
            pillar = str(profile.get("pillar") or "")
            lower = calendar_stems.get(pillar, "")
            allowed_lower = set(profile.get("lower_stems") or ())
            if lower and (not allowed_lower or lower in allowed_lower):
                for palace, row in palaces.items():
                    if (
                        profile.get("upper") in (row.get("heaven_stems") or ())
                        and row.get("earth_stem") == lower
                    ):
                        matches.append(
                            _pattern_record(
                                profile,
                                palace=palace,
                                details={"calendar_pillar": pillar},
                            )
                        )
        elif predicate == "calendar_stem_over_earth_stem":
            pillar = str(profile.get("pillar") or "")
            upper = calendar_stems.get(pillar, "")
            if upper:
                for palace, row in palaces.items():
                    if (
                        upper in (row.get("heaven_stems") or ())
                        and row.get("earth_stem") == profile.get("lower")
                    ):
                        matches.append(
                            _pattern_record(
                                profile,
                                palace=palace,
                                details={"calendar_pillar": pillar},
                            )
                        )
        elif predicate == "hour_ganzhi_in_set":
            if hour_ganzhi in set(profile.get("cases") or ()):
                matches.append(
                    _pattern_record(
                        profile,
                        details={"hour_ganzhi": hour_ganzhi},
                    )
                )
        elif predicate == "time_net_palace_height":
            lower = calendar_stems.get(str(profile.get("pillar") or ""), "")
            if lower:
                for palace, row in palaces.items():
                    if (
                        profile.get("upper") in (row.get("heaven_stems") or ())
                        and row.get("earth_stem") == lower
                    ):
                        level = (
                            "low"
                            if palace in set(profile.get("low_palaces") or ())
                            else "high"
                            if palace in set(profile.get("high_palaces") or ())
                            else "unclassified"
                        )
                        matches.append(
                            _pattern_record(
                                profile,
                                palace=palace,
                                details={"height_class": level},
                            )
                        )
        elif predicate == "hour_stem_controls_day_stem":
            if FIVE_NOT_MEET_HOUR_STEM.get(day_stem) == hour_stem:
                matches.append(_pattern_record(profile))
        elif predicate == "all_rotating_stars_on_home_palaces":
            home = {
                str(data["star"]): palace
                for palace, data in _palace_profiles().items()
                if palace != 5
            }
            if all(star_palaces.get(star) == palace for star, palace in home.items()):
                matches.append(_pattern_record(profile))
        elif predicate == "all_rotating_stars_on_opposite_palaces":
            home = {
                str(data["star"]): palace
                for palace, data in _palace_profiles().items()
                if palace != 5
            }
            if all(
                star_palaces.get(star) == OPPOSITE_PALACE[palace]
                for star, palace in home.items()
            ):
                matches.append(_pattern_record(profile))
        elif predicate == "heaven_stem_in_palace":
            for stem, target_palaces in (profile.get("cases") or {}).items():
                for palace in target_palaces:
                    if stem in (palaces[int(palace)].get("heaven_stems") or ()):
                        matches.append(_pattern_record(profile, palace=int(palace)))
        elif predicate == "chief_destination_by_xun":
            target = int((profile.get("cases") or {}).get(xun) or 0)
            if chief_destination == target:
                matches.append(_pattern_record(profile, palace=chief_destination))
        elif predicate == "door_in_palace":
            for door, target_palaces in (profile.get("cases") or {}).items():
                for palace in target_palaces:
                    if palaces[int(palace)].get("door") == door:
                        matches.append(_pattern_record(profile, palace=int(palace)))
        else:
            raise RuntimeError(f"unsupported Qimen named-pattern predicate: {predicate}")
    return matches


def build_board(
    active_term: str,
    day_ganzhi: str,
    hour_ganzhi: str,
    *,
    year_ganzhi: str | None = None,
    month_ganzhi: str | None = None,
) -> dict[str, Any]:
    """Build one complete selected-profile rotating plate."""

    tables = source_table()
    if year_ganzhi is not None:
        _require_ganzhi(year_ganzhi, label="year_ganzhi")
    if month_ganzhi is not None:
        _require_ganzhi(month_ganzhi, label="month_ganzhi")
    term_profile = (tables.get("term_yuan_ju") or {}).get(str(active_term))
    if not isinstance(term_profile, dict):
        raise ValueError(f"unsupported Qimen active solar term: {active_term}")
    symbol_head = _symbol_head(day_ganzhi)
    yuan = _yuan(symbol_head)
    dun = str(term_profile["dun"])
    ju = int(term_profile[yuan])
    xun, hour_offset, xun_profile = _xun_profile(hour_ganzhi)
    hidden = str(xun_profile["hidden_instrument"])
    earth = _earth_plate(ju, dun)
    earth_palace_by_stem = {stem: palace for palace, stem in earth.items()}
    xun_palace = earth_palace_by_stem[hidden]
    hosted_xun_palace = _host_center(xun_palace)
    profiles = _palace_profiles()

    chief_identity = str(profiles[xun_palace]["star"])
    chief_rotation_star = (
        str(profiles[2]["star"]) if xun_palace == 5 else chief_identity
    )
    director_identity = str(profiles[hosted_xun_palace]["door"])
    hour_stem = hour_ganzhi[0]
    chief_target_stem = hidden if hour_stem == "甲" else hour_stem
    chief_destination = _host_center(earth_palace_by_stem[chief_target_stem])
    director_destination = _director_destination(xun_palace, hour_offset, dun)

    star_home = {
        palace: str(profile["star"])
        for palace, profile in profiles.items()
        if palace != 5
    }
    chief_home = next(
        palace for palace, star in star_home.items() if star == chief_rotation_star
    )
    star_destinations = _rotated_mapping(
        star_home,
        home_start=chief_home,
        destination=chief_destination,
        order_key="star_rotation_outer_palaces",
    )
    door_home = {
        palace: str(profile["door"])
        for palace, profile in profiles.items()
        if palace != 5
    }
    director_home = next(
        palace for palace, door in door_home.items() if door == director_identity
    )
    door_destinations = _rotated_mapping(
        door_home,
        home_start=director_home,
        destination=director_destination,
        order_key="door_rotation_outer_palaces",
    )
    deity_destinations = _deity_mapping(chief_destination, dun)

    star_destination_by_name = {
        star: palace for palace, star in star_destinations.items()
    }
    tianrui_destination = star_destination_by_name["天芮"]
    primary_heaven_stem = {
        destination: earth[home]
        for home, star in star_home.items()
        for destination in (star_destination_by_name[star],)
    }
    center_heaven_stem = earth[5]
    palace_rows: list[dict[str, Any]] = []
    for palace in range(1, 10):
        primary_star = star_destinations.get(palace)
        stars = [primary_star] if primary_star else []
        heaven_stems = [primary_heaven_stem[palace]] if primary_star else []
        if palace == tianrui_destination:
            stars.append("天禽")
            heaven_stems.append(center_heaven_stem)
        profile = profiles[palace]
        palace_rows.append(
            {
                "palace": palace,
                "trigram": str(profile["trigram"]),
                "direction": str(profile["direction"]),
                "branches": list(profile.get("branches") or ()),
                "earth_stem": earth[palace],
                "heaven_stems": heaven_stems,
                "stars": stars,
                "door": door_destinations.get(palace),
                "deity": deity_destinations.get(palace),
            }
        )

    void_branches = [str(value) for value in xun_profile["void_branches"]]
    void_palaces = sorted({_palace_for_branch(branch) for branch in void_branches})
    horse_profile = tables["horse_by_hour_branch"][hour_ganzhi[1]]
    six_instruments = [str(value) for value in tables["orders"]["six_instruments"]]
    three_wonders = [str(value) for value in tables["orders"]["three_wonders"]]
    token_kind = {
        **{stem: "six_instrument" for stem in six_instruments},
        **{stem: "three_wonder" for stem in three_wonders},
    }
    instruments_wonders = {
        "six_instruments": six_instruments,
        "three_wonders": three_wonders,
        "earth_plate": [
            {
                "palace": row["palace"],
                "stem": row["earth_stem"],
                "kind": token_kind[row["earth_stem"]],
            }
            for row in palace_rows
        ],
        "heaven_plate": [
            {
                "palace": row["palace"],
                "stem": stem,
                "kind": token_kind[stem],
            }
            for row in palace_rows
            for stem in row["heaven_stems"]
        ],
        "hidden_jia": {"xun": xun, "instrument": hidden},
        "source_dependency_id": "qimen.plate.instruments-wonders-palaces",
    }
    board: dict[str, Any] = {
        "profile": {
            "id": PROFILE_ID,
            "version": str(tables["selected_convention"]["version"]),
            "board_type": str(tables["selected_convention"]["board_type"]),
            "ju_method": "chaibu",
            "center_hosting": "always_kun_2",
            "deity_profile": "baihu_xuanwu_variant",
            "incompatible_alternatives": copy.deepcopy(
                tables["selected_convention"]["incompatible_alternatives"]
            ),
        },
        "active_solar_term": str(active_term),
        "day_hour": {
            "day_ganzhi": day_ganzhi,
            "hour_ganzhi": hour_ganzhi,
        },
        "calendar_pillars": {
            "year": year_ganzhi,
            "month": month_ganzhi,
            "day": day_ganzhi,
            "hour": hour_ganzhi,
        },
        "dun": dun,
        "yuan": yuan,
        "symbol_head": symbol_head,
        "ju": {
            "number": ju,
            "dun": dun,
            "yuan": yuan,
            "source_dependency_id": "qimen.calendar.dun-yuan-ju",
        },
        "chief": {
            "star": chief_identity,
            "rotation_star": chief_rotation_star,
            "door": director_identity,
            "hidden_instrument": hidden,
            "xun_palace": xun_palace,
            "hosted_xun_palace": hosted_xun_palace,
            "destination_palace": chief_destination,
            "source_dependency_id": "qimen.plate.chief-director-stars-doors-deities",
        },
        "director": {
            "door": director_identity,
            "xun_palace": xun_palace,
            "destination_palace": director_destination,
            "hour_offset_in_xun": hour_offset,
            "source_dependency_id": "qimen.plate.chief-director-stars-doors-deities",
        },
        "palaces": palace_rows,
        "instruments_wonders": instruments_wonders,
        "stars_doors_deities": [
            {
                "palace": row["palace"],
                "heaven_stems": list(row["heaven_stems"]),
                "stars": list(row["stars"]),
                "door": row["door"],
                "deity": row["deity"],
            }
            for row in palace_rows
            if row["palace"] != 5
        ],
        "xunkong": {
            "xun": xun,
            "branches": void_branches,
            "palaces": void_palaces,
            "source_dependency_id": "qimen.markers.xunkong-horse",
        },
        "horse": {
            "hour_branch": hour_ganzhi[1],
            "branch": str(horse_profile["horse_branch"]),
            "palace": int(horse_profile["palace"]),
            "source_dependency_id": "qimen.markers.xunkong-horse",
        },
        "source_dependencies": list(SOURCE_DEPENDENCIES),
    }
    board["named_patterns"] = detect_named_patterns(board)
    board["board_digest"] = _digest(board)
    return board


def board_signature(board: Mapping[str, Any]) -> str:
    palaces = sorted(board.get("palaces") or (), key=lambda row: int(row["palace"]))
    if len(palaces) != 9:
        raise ValueError("Qimen board signature requires nine palaces")
    return "|".join(
        ":".join(
            (
                str(row["palace"]),
                "/".join(
                    (
                        str(row.get("earth_stem") or "-"),
                        "+".join(str(value) for value in row.get("heaven_stems") or ()) or "-",
                        "+".join(str(value) for value in row.get("stars") or ()) or "-",
                        str(row.get("door") or "-"),
                        str(row.get("deity") or "-"),
                    )
                ),
            )
        )
        for row in palaces
    )


def _fact_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    identity = copy.deepcopy(dict(payload))
    identity.pop("fact_digest", None)
    return identity


def build_fact_layer(calendar: Mapping[str, Any]) -> dict[str, Any]:
    calendar_payload = copy.deepcopy(dict(calendar))
    calendar_digest = calendar_core.validate_calendar_digest(calendar_payload)
    solar_terms = calendar_payload.get("solar_terms") or {}
    previous_term = solar_terms.get("previous") or {}
    pillars = calendar_payload.get("ganzhi") or {}
    board = build_board(
        str(previous_term.get("name") or ""),
        str(pillars.get("day") or ""),
        str(pillars.get("hour") or ""),
        year_ganzhi=str(pillars.get("year") or ""),
        month_ganzhi=str(pillars.get("month") or ""),
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": "qimen",
        "fact_layer_status": "deterministic_qimen_chart",
        "fact_layer_scope": "concrete_event_instant",
        "adapter": {
            "name": "mingli-master.qimen",
            "version": ADAPTER_VERSION,
            "source_tool": "deterministic_qimen_engine",
            "rule_profile": PROFILE_ID,
        },
        "calendar_normalization": calendar_payload,
        "calendar_digest": calendar_digest,
        "output": board,
        "source_table": {
            "path": SOURCE_TABLE_RELPATH.as_posix(),
            "sha256": SOURCE_TABLE_SHA256,
            "schema_version": "mingli-qimen-source-tables-v1",
        },
    }
    payload["fact_digest"] = _digest(_fact_identity(payload))
    report = validate_fact_layer(payload)
    if not report["ok"]:
        raise RuntimeError("invalid deterministic Qimen facts: " + ", ".join(report["codes"]))
    return payload


def validate_fact_layer(payload: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def reject(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    expected_adapter = {
        "name": "mingli-master.qimen",
        "version": ADAPTER_VERSION,
        "source_tool": "deterministic_qimen_engine",
        "rule_profile": PROFILE_ID,
    }
    expected_source_table = {
        "path": SOURCE_TABLE_RELPATH.as_posix(),
        "sha256": SOURCE_TABLE_SHA256,
        "schema_version": "mingli-qimen-source-tables-v1",
    }
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("system") != "qimen"
        or payload.get("fact_layer_scope") != "concrete_event_instant"
        or payload.get("adapter") != expected_adapter
        or payload.get("source_table") != expected_source_table
    ):
        reject(
            "qimen_provenance_mismatch",
            "Qimen fact envelope does not match the fixed provider and source identity",
        )
    if payload.get("fact_layer_status") != "deterministic_qimen_chart":
        reject("qimen_invalid_status", "Qimen facts must be a deterministic chart")
    calendar_payload = payload.get("calendar_normalization") or {}
    calendar_valid = False
    try:
        calendar_digest = calendar_core.validate_calendar_digest(
            calendar_payload
        )
        if payload.get("calendar_digest") != calendar_digest:
            reject("qimen_calendar_digest_mismatch", "Qimen calendar digest is not bound")
        else:
            calendar_valid = True
    except (TypeError, ValueError):
        reject("qimen_calendar_digest_mismatch", "Qimen calendar facts are invalid")
    output = payload.get("output") or {}
    if isinstance(output, Mapping):
        board_identity = copy.deepcopy(dict(output))
        supplied_board_digest = str(board_identity.pop("board_digest", ""))
        actual_board_digest = _digest(board_identity)
        if (
            not re.fullmatch(r"[0-9a-f]{64}", supplied_board_digest)
            or supplied_board_digest != actual_board_digest
        ):
            reject(
                "qimen_board_digest_mismatch",
                "Qimen board digest does not match the complete board",
            )
    if calendar_valid and isinstance(output, Mapping):
        solar_terms = calendar_payload.get("solar_terms") or {}
        previous_term = solar_terms.get("previous") or {}
        pillars = calendar_payload.get("ganzhi") or {}
        try:
            expected_board = build_board(
                str(previous_term.get("name") or ""),
                str(pillars.get("day") or ""),
                str(pillars.get("hour") or ""),
                year_ganzhi=str(pillars.get("year") or ""),
                month_ganzhi=str(pillars.get("month") or ""),
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            reject(
                "qimen_board_recalculation_failed",
                "Qimen board inputs cannot be reproduced from the bound calendar",
            )
        else:
            if dict(output) != expected_board:
                reject(
                    "qimen_board_facts_mismatch",
                    "Qimen board does not match its bound calendar and source profile",
                )
    palaces = output.get("palaces") if isinstance(output, Mapping) else None
    if (
        not isinstance(palaces, list)
        or len(palaces) != 9
        or {row.get("palace") for row in palaces if isinstance(row, Mapping)}
        != set(range(1, 10))
    ):
        reject("qimen_invalid_palaces", "Qimen requires nine unique palaces")
    else:
        if sum(len(row.get("stars") or ()) for row in palaces) != 9:
            reject("qimen_invalid_stars", "Qimen requires nine placed stars")
        if len([row for row in palaces if row.get("door")]) != 8:
            reject("qimen_invalid_doors", "Qimen requires eight placed doors")
        if len([row for row in palaces if row.get("deity")]) != 8:
            reject("qimen_invalid_deities", "Qimen requires eight placed deities")
        if len({row.get("earth_stem") for row in palaces}) != 9:
            reject("qimen_invalid_earth_plate", "Qimen earth plate must use nine unique tokens")
    if not isinstance(output.get("chief"), Mapping) or not isinstance(output.get("director"), Mapping):
        reject("qimen_invalid_chief_director", "Qimen requires Chief and Director facts")
    if not isinstance(output.get("xunkong"), Mapping) or not isinstance(output.get("horse"), Mapping):
        reject("qimen_invalid_xunkong_horse", "Qimen requires Xunkong and horse facts")
    for row in output.get("named_patterns") or ():
        if (
            not isinstance(row, Mapping)
            or row.get("status") != "predicate_matched_not_verdict"
            or "verdict" in row
            or not _valid_pattern_adjudication(row)
        ):
            reject(
                "qimen_invalid_pattern_fact",
                "Qimen named patterns require a source-bound identity adjudication",
            )
            break
    supplied_digest = str(payload.get("fact_digest") or "")
    actual_digest = _digest(_fact_identity(payload))
    if not re.fullmatch(r"[0-9a-f]{64}", supplied_digest) or supplied_digest != actual_digest:
        reject("qimen_fact_digest_mismatch", "Qimen fact digest does not match")
    return {
        "ok": not findings,
        "findings": findings,
        "codes": [item["code"] for item in findings],
    }


__all__ = [
    "ADAPTER_VERSION",
    "PROFILE_ID",
    "PROVIDER_VERSION",
    "SOURCE_DEPENDENCIES",
    "SOURCE_TABLE_SHA256",
    "TABLE_PROFILE",
    "TABLE_SHA256",
    "XUN_HEADS",
    "board_signature",
    "build_board",
    "build_fact_layer",
    "detect_named_patterns",
    "source_table",
    "source_table_digest",
    "validate_fact_layer",
]
