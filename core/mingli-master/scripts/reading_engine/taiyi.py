"""Deterministic annual Taiyi board for the selected Jinjing source profile."""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import calendar_core, evidence_rules


ROOT = Path(__file__).resolve().parents[2]
SOURCE_TABLE_PATH = ROOT / "references/matrices/taiyi-source-tables-v1.yaml"
SOURCE_TABLE_SHA256 = "a5ade0bfb7bcdf89aeb0862d5992fd6fb340d640ab1a593c6381cd480df5c393"
SOURCE_TABLE_SCHEMA = "mingli-taiyi-source-tables-v1"
TABLE_PROFILE = "taiyi-jinjing-annual-yang-board-v1"
ADAPTER_VERSION = "5.2.0"
FACT_SCHEMA_VERSION = "mingli-taiyi-facts-v1"
FACT_LAYER_STATUS = "deterministic_taiyi_annual_board"
FACT_LAYER_SCOPE = "annual_macro_historical_board_facts"
SOURCE_DEPENDENCIES = (
    "taiyi.calendar.annual-epoch-and-scope",
    "taiyi.cycle.six-ji-five-zi-yuan",
    "taiyi.plate.taiyi-tianmu-jishen-shiji",
    "taiyi.plate.host-guest-counts-and-generals",
    "taiyi.deities.independent-long-cycle-epochs",
    "taiyi.evidence.board-predicates-and-scope",
)
BOARD_PREDICATE_IDS = (
    "TY-P01",
    "TY-P02",
    "TY-P03",
    "TY-P04",
    "TY-P05",
    "TY-P06",
    "TY-P07",
    "TY-P08",
    "TY-P09",
    "TY-P10",
)
PATTERN_UNRESOLVED_CHECKS = (
    "并见格局、制化与主客关系",
    "宏观事项范围及盘面取用",
    "现实成败、吉凶与应期",
)

STEMS = tuple("甲乙丙丁戊己庚辛壬癸")
BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")
BRANCH_DOMAIN_ORDER = tuple("戌亥子丑寅卯辰巳午未申酉")
PALACE_FORWARD_FROM_ONE = (1, 2, 3, 4, 6, 7, 8, 9)
PALACE_FORWARD_FROM_SEVEN = (7, 8, 9, 1, 2, 3, 4, 6)
OPPOSITE_POSITION = {
    "乾": "巽",
    "巽": "乾",
    "午": "子",
    "子": "午",
    "艮": "坤",
    "坤": "艮",
    "卯": "酉",
    "酉": "卯",
}


def _digest(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _one_based_mod(value: int, modulus: int) -> int:
    return (int(value) - 1) % int(modulus) + 1


@lru_cache(maxsize=1)
def source_table() -> dict[str, Any]:
    if _sha256(SOURCE_TABLE_PATH) != SOURCE_TABLE_SHA256:
        raise RuntimeError("Taiyi source table hash mismatch")
    payload = yaml.safe_load(SOURCE_TABLE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SOURCE_TABLE_SCHEMA:
        raise RuntimeError("unsupported Taiyi source table schema")
    if payload.get("status") != "verified":
        raise RuntimeError("Taiyi source table is not verified")
    if payload.get("selected_convention", {}).get("id") != TABLE_PROFILE:
        raise RuntimeError("Taiyi source profile mismatch")
    rows = payload.get("annual_yang_72_source_rows") or ()
    if [row.get("bureau") for row in rows] != list(range(1, 73)):
        raise RuntimeError("Taiyi source table must contain exactly bureaus 1 through 72")
    predicates = payload.get("board_predicate_contracts") or ()
    if tuple(row.get("id") for row in predicates) != BOARD_PREDICATE_IDS:
        raise RuntimeError("Taiyi source table predicate contract is incomplete")
    return payload


def source_table_digest() -> str:
    source_table()
    return SOURCE_TABLE_SHA256


def _year_ganzhi(lunar_year: int) -> str:
    index = (int(lunar_year) - 4) % 60
    return STEMS[index % 10] + BRANCHES[index % 12]


def _cycle(accumulated_year: int) -> dict[str, Any]:
    table = source_table()
    cycle_position = _one_based_mod(accumulated_year, 360)
    bureau = _one_based_mod(accumulated_year, 72)
    zi_yuan = (cycle_position - 1) // 72 + 1
    return {
        "position_360": cycle_position,
        "ji": (cycle_position - 1) // 60 + 1,
        "year_in_ji": (cycle_position - 1) % 60 + 1,
        "zi_yuan": zi_yuan,
        "zi_yuan_head": table["cycles"]["zi_yuan_heads"][zi_yuan - 1],
        "year_in_zi_yuan": (cycle_position - 1) % 72 + 1,
        "bureau": bureau,
        "governance": table["cycles"]["governance_cycle"][
            _one_based_mod(accumulated_year, 3) - 1
        ],
    }


def _count_from_eye(
    eye: str,
    taiyi_position: str,
    *,
    ring: tuple[str, ...],
    main_palaces: Mapping[str, int],
) -> int:
    if eye == taiyi_position:
        return int(main_palaces[eye])
    total = int(main_palaces.get(eye, 1))
    index = (ring.index(eye) + 1) % len(ring)
    while ring[index] != taiyi_position:
        total += int(main_palaces.get(ring[index], 0))
        index = (index + 1) % len(ring)
    return total


def _major_general(count: int) -> int:
    return count // 10 if count % 10 == 0 else count % 10


def _assistant_general(major: int) -> int:
    return (major * 3) % 10 or 5


def _core_board(accumulated_year: int) -> dict[str, Any]:
    table = source_table()
    positions = table["positions"]
    cycle = _cycle(accumulated_year)
    bureau = int(cycle["bureau"])
    ring = tuple(str(value) for value in positions["sixteen_ring_forward"])
    main_palaces = {
        str(position): int(number)
        for position, number in positions["main_palaces"].items()
    }
    taiyi_order = tuple(str(value) for value in positions["taiyi_forward_order"])
    taiyi_position = taiyi_order[
        (_one_based_mod(accumulated_year, 24) - 1) // 3
    ]
    tianmu_row = positions["tianmu_expanded_cycle"][
        _one_based_mod(accumulated_year, 18) - 1
    ]
    tianmu_name = str(tianmu_row["name"])
    tianmu_position = str(tianmu_row["position"])
    jishen = BRANCHES[(2 - (bureau - 1)) % 12]
    shiji = ring[
        (
            ring.index(tianmu_position)
            + ring.index("艮")
            - ring.index(jishen)
        )
        % len(ring)
    ]
    host_count = _count_from_eye(
        tianmu_position,
        taiyi_position,
        ring=ring,
        main_palaces=main_palaces,
    )
    guest_count = _count_from_eye(
        shiji,
        taiyi_position,
        ring=ring,
        main_palaces=main_palaces,
    )
    host_general = _major_general(host_count)
    guest_general = _major_general(guest_count)
    computed = {
        "taiyi": taiyi_position,
        "tianmu": tianmu_name,
        "tianmu_position": tianmu_position,
        "host_count": host_count,
        "host_general": host_general,
        "host_assistant": _assistant_general(host_general),
        "shiji": shiji,
        "guest_count": guest_count,
        "guest_general": guest_general,
        "guest_assistant": _assistant_general(guest_general),
        "jishen": jishen,
    }
    source_row = table["annual_yang_72_source_rows"][bureau - 1]
    expected = {key: value for key, value in source_row.items() if key != "bureau"}
    if computed != expected:
        raise RuntimeError(f"Taiyi formula disagrees with source row for bureau {bureau}")
    return {**computed, "cycle": cycle}


def _deity_fact(
    name: str,
    position: Any,
    *,
    epoch_profile: str,
    accumulated_year: int,
    cycle_position: int,
    source_anchor: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "position": position,
        "epoch_profile": epoch_profile,
        "accumulated_year": int(accumulated_year),
        "cycle_position": int(cycle_position),
        "source_anchor": source_anchor,
        "status": "calculated_position_not_verdict",
    }


def _long_cycle_deities(lunar_year: int) -> dict[str, dict[str, Any]]:
    table = source_table()
    profiles = table["epoch_profiles"]
    upper_profile = "upper-jiayin-long-cycle-v1"
    wufu_profile = "wufu-dayou-long-cycle-v1"
    small_profile = "xiaoyou-four-deity-v1"
    upper = int(lunar_year) + int(profiles[upper_profile]["derived_ce_offset"])
    wufu_year = int(lunar_year) + int(profiles[wufu_profile]["derived_ce_offset"])
    small = int(lunar_year) + int(profiles[small_profile]["derived_ce_offset"])

    upper_360 = _one_based_mod(upper, 360)
    junji = BRANCH_DOMAIN_ORDER[(upper_360 - 1) // 30]
    upper_36 = _one_based_mod(upper_360, 36)
    chenji = BRANCH_DOMAIN_ORDER[(upper_36 - 1) // 3]
    upper_12 = _one_based_mod(upper_360, 12)
    minji = BRANCH_DOMAIN_ORDER[upper_12 - 1]

    wufu_position_225 = _one_based_mod(wufu_year, 225)
    wufu_position = ("乾", "艮", "巽", "坤", "中")[
        (wufu_position_225 - 1) // 45
    ]
    dayou_position_288 = _one_based_mod(wufu_year, 288)
    dayou_position = PALACE_FORWARD_FROM_SEVEN[
        (dayou_position_288 - 1) // 36
    ]

    xiaoyou_position_24 = _one_based_mod(small, 24)
    xiaoyou_position = PALACE_FORWARD_FROM_ONE[
        (xiaoyou_position_24 - 1) // 3
    ]

    four_cycle = table["long_cycle_deities"]["four_deity_cycle"]
    four_position_180 = _one_based_mod(small, 180)
    yuan = (four_position_180 - 1) // 60
    within_yuan = (four_position_180 - 1) % 60
    place_order = tuple(four_cycle["place_order"])

    def four_position(name: str) -> Any:
        starts = tuple(four_cycle["upper_middle_lower_starts"][name])
        start = place_order.index(starts[yuan])
        return place_order[(start + within_yuan // 3) % len(place_order)]

    return {
        "junji": _deity_fact(
            "君基", junji, epoch_profile=upper_profile,
            accumulated_year=upper, cycle_position=upper_360,
            source_anchor="fulltext.md L602-L604",
        ),
        "chenji": _deity_fact(
            "臣基", chenji, epoch_profile=upper_profile,
            accumulated_year=upper, cycle_position=upper_36,
            source_anchor="fulltext.md L606-L608",
        ),
        "minji": _deity_fact(
            "民基", minji, epoch_profile=upper_profile,
            accumulated_year=upper, cycle_position=upper_12,
            source_anchor="fulltext.md L610-L612",
        ),
        "wufu": _deity_fact(
            "五福", wufu_position, epoch_profile=wufu_profile,
            accumulated_year=wufu_year, cycle_position=wufu_position_225,
            source_anchor="fulltext.md L614-L617",
        ),
        "dayou": _deity_fact(
            "大游", dayou_position, epoch_profile=wufu_profile,
            accumulated_year=wufu_year, cycle_position=dayou_position_288,
            source_anchor="fulltext.md L619-L638",
        ),
        "xiaoyou": _deity_fact(
            "小游", xiaoyou_position, epoch_profile=small_profile,
            accumulated_year=small, cycle_position=xiaoyou_position_24,
            source_anchor="fulltext.md L644-L646",
        ),
        "sishen": _deity_fact(
            "四神", four_position("四神"), epoch_profile=small_profile,
            accumulated_year=small, cycle_position=four_position_180,
            source_anchor="fulltext.md L648-L651",
        ),
        "tianyi": _deity_fact(
            "天乙", four_position("天乙"), epoch_profile=small_profile,
            accumulated_year=small, cycle_position=four_position_180,
            source_anchor="fulltext.md L653-L655",
        ),
        "diyi": _deity_fact(
            "地乙", four_position("地乙"), epoch_profile=small_profile,
            accumulated_year=small, cycle_position=four_position_180,
            source_anchor="fulltext.md L661-L759",
        ),
        "zhifu": _deity_fact(
            "直符", four_position("直符"), epoch_profile=small_profile,
            accumulated_year=small, cycle_position=four_position_180,
            source_anchor="fulltext.md L657-L659",
        ),
    }


def _predicate(
    identifier: str,
    predicate: str,
) -> dict[str, Any]:
    contract = next(
        row
        for row in source_table()["board_predicate_contracts"]
        if row["id"] == identifier
    )
    rule = _verified_pattern_rule(identifier)
    return {
        "id": identifier,
        "name": contract["name"],
        "predicate": predicate,
        "fact_paths": [
            contract["left_fact_path"],
            contract["right_fact_path"],
        ],
        "source_anchor": f"fulltext.md {contract['source_anchor']}",
        "source_dependency_id": "taiyi.evidence.board-predicates-and-scope",
        "status": "predicate_matched_not_verdict",
        "identity_adjudication": {
            "status": "adjudicated_pattern_identity",
            "decision_scope": "taiyi_board_pattern_identity",
            "pattern_id": identifier,
            "pattern_name": str(contract["name"]),
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


@lru_cache(maxsize=10)
def _verified_pattern_rule(pattern_id: str) -> evidence_rules.EvidenceRule:
    """Resolve exactly one checked Taiyi board-pattern rule."""

    matches = [
        rule
        for rule in evidence_rules.production_evidence_rules()
        if rule.system == "taiyi" and rule.local_rule_id == pattern_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Taiyi pattern requires exactly one evidence rule: {pattern_id}"
        )
    rule = matches[0]
    if (
        not rule.runtime_active
        or rule.classical_binding_status != "verified"
        or not rule.classical_binding_digest
    ):
        raise RuntimeError(f"Taiyi pattern rule is not verified: {pattern_id}")
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
        "decision_scope": "taiyi_board_pattern_identity",
        "pattern_id": pattern_id,
        "pattern_name": pattern_name,
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


def _board_predicates(core: Mapping[str, Any]) -> list[dict[str, Any]]:
    taiyi_position = str(core["taiyi"])
    tianmu_position = str(core["tianmu_position"])
    shiji = str(core["shiji"])
    taiyi_palace = int(source_table()["positions"]["main_palaces"][taiyi_position])
    opposite = OPPOSITE_POSITION[taiyi_position]
    opposite_palace = int(source_table()["positions"]["main_palaces"][opposite])
    matched: list[dict[str, Any]] = []
    if shiji == taiyi_position:
        matched.append(_predicate(
            "TY-P01", "shiji_same_as_taiyi",
        ))
    if tianmu_position == taiyi_position:
        matched.append(_predicate(
            "TY-P02", "tianmu_wenchang_same_as_taiyi",
        ))
    if shiji == opposite:
        matched.append(_predicate(
            "TY-P03", "shiji_opposes_taiyi",
        ))
    if tianmu_position == opposite:
        matched.append(_predicate(
            "TY-P04", "tianmu_wenchang_opposes_taiyi",
        ))
    general_predicates = (
        ("TY-P05", "host_general", taiyi_palace),
        ("TY-P06", "host_assistant", taiyi_palace),
        ("TY-P07", "guest_general", taiyi_palace),
        ("TY-P08", "guest_assistant", taiyi_palace),
        ("TY-P09", "guest_general", opposite_palace),
        ("TY-P10", "guest_assistant", opposite_palace),
    )
    for identifier, field, expected in general_predicates:
        if int(core[field]) == expected:
            matched.append(_predicate(
                identifier,
                f"{field}_{'opposes' if expected == opposite_palace else 'same_as'}_taiyi",
            ))
    return matched


def board_digest(output: Mapping[str, Any]) -> str:
    identity = copy.deepcopy(dict(output))
    identity.pop("board_digest", None)
    return _digest(identity)


def fact_digest(facts: Mapping[str, Any]) -> str:
    identity = copy.deepcopy(dict(facts))
    identity.pop("fact_digest", None)
    return _digest(identity)


def build_annual_board_from_accumulated_year(
    accumulated_year: int,
    *,
    lunar_year: int | None = None,
) -> dict[str, Any]:
    annual_profile = source_table()["epoch_profiles"][
        "jinjing-annual-tang-jiazi-v1"
    ]
    offset = int(annual_profile["derived_ce_offset"])
    resolved_lunar_year = (
        int(lunar_year)
        if lunar_year is not None
        else int(accumulated_year) - offset
    )
    expected_accumulated = resolved_lunar_year + offset
    if expected_accumulated != int(accumulated_year):
        raise ValueError("Taiyi lunar year and accumulated year disagree")
    core = _core_board(int(accumulated_year))
    year_ganzhi = _year_ganzhi(resolved_lunar_year)
    year_branch = year_ganzhi[1]
    predicates = _board_predicates(core)
    source_rule_ids = ["TR-01", "TR-02", "TR-03", "TR-04", "TR-05", "TR-10", "TR-12"]
    if predicates:
        source_rule_ids.append("TR-09")
    output: dict[str, Any] = {
        "profile_id": TABLE_PROFILE,
        "calendar": {
            "lunar_year": resolved_lunar_year,
            "year_ganzhi": year_ganzhi,
            "annual_boundary": "lunar_new_year_from_shared_calendar",
        },
        "epoch": {
            "profile_id": "jinjing-annual-tang-jiazi-v1",
            "accumulated_year": int(accumulated_year),
            "anchor_lunar_year_ce": int(annual_profile["anchor_lunar_year_ce"]),
            "anchor_accumulated_year": int(annual_profile["anchor_accumulated_year"]),
            "derived_ce_offset": offset,
            "one_based": True,
            "source_anchor": str(annual_profile["source_anchor"]),
        },
        "cycle": core["cycle"],
        "taiyi": core["taiyi"],
        "tianmu": core["tianmu"],
        "tianmu_position": core["tianmu_position"],
        "wenchang": {
            "name": core["tianmu"],
            "position": core["tianmu_position"],
            "role": "host_eye_tianmu_wenchang",
        },
        "jishen": core["jishen"],
        "shiji": core["shiji"],
        "kemu": {
            "name": "始击",
            "position": core["shiji"],
            "role": "guest_eye_shiji_kemu",
        },
        "taisui": {"ganzhi": year_ganzhi, "position": year_branch},
        "heshen": {
            "position": source_table()["positions"]["branch_pairs"][year_branch],
            "relation": "year_branch_six_harmony",
        },
        "host_count": core["host_count"],
        "host_general": core["host_general"],
        "host_assistant": core["host_assistant"],
        "guest_count": core["guest_count"],
        "guest_general": core["guest_general"],
        "guest_assistant": core["guest_assistant"],
        "host_guest": {
            "host": {
                "eye": "tianmu_wenchang",
                "eye_position": core["tianmu_position"],
                "count": core["host_count"],
                "major_general_palace": core["host_general"],
                "assistant_general_palace": core["host_assistant"],
            },
            "guest": {
                "eye": "shiji_kemu",
                "eye_position": core["shiji"],
                "count": core["guest_count"],
                "major_general_palace": core["guest_general"],
                "assistant_general_palace": core["guest_assistant"],
            },
        },
        "four_generals": {
            "host_major": core["host_general"],
            "host_assistant": core["host_assistant"],
            "guest_major": core["guest_general"],
            "guest_assistant": core["guest_assistant"],
        },
        "board": {
            "taiyi_position": core["taiyi"],
            "tianmu_wenchang": {
                "name": core["tianmu"],
                "position": core["tianmu_position"],
            },
            "jishen": core["jishen"],
            "shiji_kemu": core["shiji"],
            "taisui": year_branch,
            "heshen": source_table()["positions"]["branch_pairs"][year_branch],
        },
        "long_cycle_deities": _long_cycle_deities(resolved_lunar_year),
        "board_predicates": predicates,
        "scope_contract": {
            "declared_scope": FACT_LAYER_SCOPE,
            "supported_objects": ["macro_historical"],
            "supported_horizons": ["year"],
            "unsupported_scopes": list(
                source_table()["selected_convention"]["unsupported_scopes"]
            ),
            "interpretation_policy": "calculated_facts_and_predicates_only_no_event_verdicts",
        },
        "source_rule_ids": source_rule_ids,
        "source_dependency_ids": list(SOURCE_DEPENDENCIES),
    }
    output["board_digest"] = board_digest(output)
    return output


def build_annual_board(lunar_year: int) -> dict[str, Any]:
    annual_profile = source_table()["epoch_profiles"][
        "jinjing-annual-tang-jiazi-v1"
    ]
    accumulated_year = int(lunar_year) + int(annual_profile["derived_ce_offset"])
    return build_annual_board_from_accumulated_year(
        accumulated_year,
        lunar_year=int(lunar_year),
    )


def build_fact_layer(calendar: Mapping[str, Any]) -> dict[str, Any]:
    calendar_payload = copy.deepcopy(dict(calendar))
    calendar_digest = calendar_core.validate_calendar_digest(calendar_payload)
    if calendar_digest is None:
        raise ValueError("Taiyi requires validated shared calendar facts")
    lunar = calendar_payload.get("lunar_date")
    if not isinstance(lunar, Mapping) or not isinstance(lunar.get("year"), int):
        raise ValueError("Taiyi shared calendar is missing the lunar year")
    output = build_annual_board(int(lunar["year"]))
    facts: dict[str, Any] = {
        "schema_version": FACT_SCHEMA_VERSION,
        "system": "taiyi",
        "fact_layer_status": FACT_LAYER_STATUS,
        "fact_layer_scope": FACT_LAYER_SCOPE,
        "adapter": {
            "name": "mingli.taiyi.annual",
            "version": ADAPTER_VERSION,
            "rule_profile": TABLE_PROFILE,
        },
        "source_table": {
            "path": "references/matrices/taiyi-source-tables-v1.yaml",
            "schema_version": SOURCE_TABLE_SCHEMA,
            "sha256": SOURCE_TABLE_SHA256,
        },
        "calendar_normalization": calendar_payload,
        "calendar_digest": calendar_digest,
        "output": output,
    }
    facts["fact_digest"] = fact_digest(facts)
    return facts


def validate_fact_layer(facts: Mapping[str, Any]) -> dict[str, Any]:
    codes: list[str] = []

    def invalid(code: str) -> None:
        if code not in codes:
            codes.append(code)

    expected_envelope = {
        "schema_version": FACT_SCHEMA_VERSION,
        "system": "taiyi",
        "fact_layer_status": FACT_LAYER_STATUS,
        "fact_layer_scope": FACT_LAYER_SCOPE,
    }
    if any(facts.get(key) != value for key, value in expected_envelope.items()):
        invalid("taiyi_provenance_mismatch")
    adapter = facts.get("adapter")
    if not isinstance(adapter, Mapping) or dict(adapter) != {
        "name": "mingli.taiyi.annual",
        "version": ADAPTER_VERSION,
        "rule_profile": TABLE_PROFILE,
    }:
        invalid("taiyi_provenance_mismatch")
    source = facts.get("source_table")
    if not isinstance(source, Mapping) or dict(source) != {
        "path": "references/matrices/taiyi-source-tables-v1.yaml",
        "schema_version": SOURCE_TABLE_SCHEMA,
        "sha256": SOURCE_TABLE_SHA256,
    }:
        invalid("taiyi_provenance_mismatch")

    calendar = facts.get("calendar_normalization")
    calendar_digest: str | None = None
    if isinstance(calendar, Mapping):
        try:
            calendar_digest = calendar_core.validate_calendar_digest(calendar)
        except (KeyError, TypeError, ValueError):
            calendar_digest = None
    if calendar_digest is None or facts.get("calendar_digest") != calendar_digest:
        invalid("taiyi_calendar_digest_mismatch")

    output = facts.get("output")
    if not isinstance(output, Mapping):
        invalid("taiyi_invalid_output")
    else:
        for row in output.get("board_predicates") or ():
            if (
                not isinstance(row, Mapping)
                or row.get("status") != "predicate_matched_not_verdict"
                or "verdict" in row
                or not _valid_pattern_adjudication(row)
            ):
                invalid("taiyi_invalid_predicate_fact")
                break
        if output.get("board_digest") != board_digest(output):
            invalid("taiyi_board_digest_mismatch")
        lunar = calendar.get("lunar_date") if isinstance(calendar, Mapping) else None
        if isinstance(lunar, Mapping) and isinstance(lunar.get("year"), int):
            try:
                expected_output = build_annual_board(int(lunar["year"]))
            except (KeyError, TypeError, ValueError, RuntimeError):
                invalid("taiyi_board_rebuild_failed")
            else:
                if dict(output) != expected_output:
                    invalid("taiyi_board_facts_mismatch")
        else:
            invalid("taiyi_board_rebuild_failed")

    if facts.get("fact_digest") != fact_digest(facts):
        invalid("taiyi_fact_digest_mismatch")
    return {"ok": not codes, "codes": codes}


__all__ = [
    "ADAPTER_VERSION",
    "BOARD_PREDICATE_IDS",
    "FACT_LAYER_SCOPE",
    "FACT_LAYER_STATUS",
    "SOURCE_DEPENDENCIES",
    "TABLE_PROFILE",
    "board_digest",
    "build_annual_board",
    "build_annual_board_from_accumulated_year",
    "build_fact_layer",
    "fact_digest",
    "source_table",
    "source_table_digest",
    "validate_fact_layer",
]
