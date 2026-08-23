#!/usr/bin/env python3
"""Build a deterministic Da Liu Ren fact layer.

The adapter calculates calendar facts, month general, heaven/earth plate, four
lessons, three transmissions, and heavenly generals. Three transmissions are
derived from an auditable classical nine-method implementation. The vendored
720-record table is retained only as a fixed cross-check witness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from reading_engine import calendar_core


VERSION = "2.1.0"
ADAPTER_NAME = "mingli-master.liuren_fact_adapter"
SCHEMA_VERSION = "mingli-liuren-fact-v1"
TRANSMISSION_HIDDEN_STEM_PROFILE = "sexagenary-day-xun-v1"

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
JIAZI = tuple(STEMS[index % 10] + BRANCHES[index % 12] for index in range(60))
VALID_JIAZI = set(JIAZI)
DAY_BRANCHES = set("卯辰巳午未申")
BAZHUAN_DAYS = {"甲寅", "庚申", "丁未", "己未", "癸丑"}
MENG_BRANCHES = set("寅巳申亥")
ZHONG_BRANCHES = set("子卯午酉")
JI_BRANCHES = set("辰戌丑未")

CLASH = dict(zip(BRANCHES, "午未申酉戌亥子丑寅卯辰巳"))
PUNISHMENT = {
    "寅": "巳", "巳": "申", "申": "寅",
    "丑": "戌", "戌": "未", "未": "丑",
    "子": "卯", "卯": "子",
    "辰": "辰", "午": "午", "酉": "酉", "亥": "亥",
}
STEM_COMBINATION = {
    "甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛",
    "辛": "丙", "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊",
}
TRINE_FORWARD = {
    "巳": "酉", "酉": "丑", "丑": "巳",
    "申": "子", "子": "辰", "辰": "申",
    "寅": "午", "午": "戌", "戌": "寅",
    "亥": "卯", "卯": "未", "未": "亥",
}
BIEZHE_PROFILES = {
    "daliuren-daquan-body-branch": "柔日取支前三合本支（课经正文口径）",
    "daliuren-daquan-upper-over-branch": "柔日取支前三合所临上神（订讹存疑口径）",
}

STEM_LODGE = {
    "甲": "寅", "乙": "辰", "丙": "巳", "丁": "未", "戊": "巳",
    "己": "未", "庚": "申", "辛": "戌", "壬": "亥", "癸": "丑",
}
ELEMENT = {
    **dict(zip(STEMS, "木木火火土土金金水水")),
    **dict(zip(BRANCHES, "水土木木土火火土金金土水")),
}
OVERCOMES = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
POLARITY = {
    **{stem: ("阳" if index % 2 == 0 else "阴") for index, stem in enumerate(STEMS)},
    **{branch: ("阳" if index % 2 == 0 else "阴") for index, branch in enumerate(BRANCHES)},
}

MONTH_GENERAL_NAMES = {
    "亥": "登明", "戌": "河魁", "酉": "从魁", "申": "传送",
    "未": "小吉", "午": "胜光", "巳": "太乙", "辰": "天罡",
    "卯": "太冲", "寅": "功曹", "丑": "大吉", "子": "神后",
}
TERM_TO_MONTH_GENERAL = {
    "雨水": "亥", "惊蛰": "亥", "春分": "戌", "清明": "戌",
    "谷雨": "酉", "立夏": "酉", "小满": "申", "芒种": "申",
    "夏至": "未", "小暑": "未", "大暑": "午", "立秋": "午",
    "处暑": "巳", "白露": "巳", "秋分": "辰", "寒露": "辰",
    "霜降": "卯", "立冬": "卯", "小雪": "寅", "大雪": "寅",
    "冬至": "丑", "小寒": "丑", "大寒": "子", "立春": "子",
}
JIEQI_NAMES = (
    "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明",
    "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋",
    "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
)

HEAVENLY_GENERAL_ORDER = (
    "贵人", "腾蛇", "朱雀", "六合", "勾陈", "青龙",
    "天空", "白虎", "太常", "玄武", "太阴", "天后",
)
GUIREN_PROFILES = {
    "official-corrected": {
        "day": dict(zip(STEMS, "未申酉亥丑子丑寅卯巳")),
        "night": dict(zip(STEMS, "丑子亥酉未申未午巳卯")),
        "source": "《钦定协纪辨方书》天乙贵人表；《六壬大全》四库提要订正说明",
    },
    "traditional-common": {
        "day": dict(zip(STEMS, "丑子亥亥丑子丑午巳巳")),
        "night": dict(zip(STEMS, "未申酉酉未申未寅卯卯")),
        "source": "《六壬大全》正文沿用的通行昼夜贵人口径",
    },
}

TABLE_PATH = Path(__file__).resolve().parent / "data" / "liuren-720-transmissions.json"
TABLE_SHA256 = "f4e77cce9d72c000aae228d1d07ed1ca9361baf3fbbad9f41f5fbe4ca346483b"
TABLE_UPSTREAM_COMMIT = "8e9a7b53245c8ae19fa12773087e1f90b3376d5e"
TABLE_ALLOWED_LABELS = {"重审", "元首", "比用", "知一", "涉害", "遥克", "昴星", "别责", "八专", "伏吟", "反吟"}
SOURCE_TABLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "matrices"
    / "liuren-source-tables-v1.yaml"
)
SOURCE_TABLE_SHA256 = "49095999aaef2b16000e201969f5ca5b1a02bf5c3e340ae0770d95f3cfe27415"


def _utc_now() -> str:
    return datetime.now(tz=ZoneInfo("UTC")).isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def _transmission_table() -> dict[str, list[dict[str, str]]]:
    raw = TABLE_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != TABLE_SHA256:
        raise RuntimeError(f"liuren 720 table checksum mismatch: {digest}")
    return json.loads(raw.decode("utf-8"))


@lru_cache(maxsize=1)
def _source_table() -> dict[str, Any]:
    raw = SOURCE_TABLE_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_TABLE_SHA256:
        raise RuntimeError(f"liuren source table checksum mismatch: {digest}")
    payload = yaml.safe_load(raw.decode("utf-8"))
    if payload.get("schema_version") != "mingli-liuren-source-tables-v1":
        raise RuntimeError("unsupported Liuren source table schema")
    return payload


def _classical_method_label_variant(
    day_ganzhi: str,
    hour_branch: str,
    month_general: str,
) -> dict[str, Any] | None:
    matches = [
        row
        for row in _source_table().get("method_label_variants") or ()
        if row.get("input")
        == {
            "day": day_ganzhi,
            "hour_branch": hour_branch,
            "month_general": month_general,
        }
    ]
    if len(matches) > 1:
        raise RuntimeError("duplicate Liuren method-label source variant")
    if not matches:
        return None
    return {key: value for key, value in matches[0].items() if key != "input"}


@lru_cache(maxsize=1)
def audit_transmission_table() -> dict[str, Any]:
    table = _transmission_table()
    invalid: list[str] = []
    direct_candidate_mismatches: list[dict[str, Any]] = []
    method_label_disagreements: list[dict[str, Any]] = []
    result_disagreements: list[dict[str, Any]] = []
    if set(table) != set(JIAZI):
        invalid.append("day_key_set")
    records = 0
    for day in JIAZI:
        rows = table.get(day, [])
        if len(rows) != 12:
            invalid.append(f"{day}:record_count={len(rows)}")
        for index, record in enumerate(rows):
            records += 1
            transmissions = record.get("干支组合", "")
            label = record.get("格局", "")
            if len(transmissions) != 3 or any(item not in BRANCHES for item in transmissions):
                invalid.append(f"{day}:{index}:transmissions")
            if label not in TABLE_ALLOWED_LABELS:
                invalid.append(f"{day}:{index}:label={label}")
            offset = (index - BRANCHES.index(STEM_LODGE[day[0]])) % 12
            heaven_plate = {
                earth: BRANCHES[(BRANCHES.index(earth) + offset) % 12]
                for earth in BRANCHES
            }
            lessons = _four_lessons(day, heaven_plate)
            direct, _ = _direct_candidates(lessons)
            if direct and transmissions and transmissions[0] not in {item["upper"] for item in direct}:
                direct_candidate_mismatches.append({
                    "day": day,
                    "offset": offset,
                    "initial": transmissions[0],
                    "candidates": sorted({item["upper"] for item in direct}, key=BRANCHES.index),
                })
            calculated = _calculate_transmissions(day, lessons, heaven_plate, offset)
            method = calculated["method"]
            canonical_table = "比用" if label == "知一" else label
            label_disagreement = offset not in {0, 6} and canonical_table != method["primary"]
            if label_disagreement:
                method_label_disagreements.append({
                    "day": day,
                    "offset": offset,
                    "table": label,
                    "derived": method["primary"],
                })
            classical_transmissions = "".join(calculated["transmissions"])
            if transmissions != classical_transmissions:
                result_disagreements.append({
                    "day": day,
                    "offset": offset,
                    "table": transmissions,
                    "classical": classical_transmissions,
                    "method": method["primary"],
                })
    return {
        "days": len(table),
        "records": records,
        "invalid_records": invalid,
        "direct_candidate_mismatches": direct_candidate_mismatches,
        "method_label_disagreements": method_label_disagreements,
        "result_disagreements": result_disagreements,
        "sha256": TABLE_SHA256,
        "upstream": "https://github.com/look-fate/liuren-ts-lib/blob/8e9a7b53245c8ae19fa12773087e1f90b3376d5e/src/sanchuan.json",
        "upstream_commit": TABLE_UPSTREAM_COMMIT,
        "license": "Apache-2.0",
    }


def _compact_transmission_table_audit() -> dict[str, Any]:
    audit = audit_transmission_table()
    return {
        "days": audit["days"],
        "records": audit["records"],
        "invalid_record_count": len(audit["invalid_records"]),
        "direct_candidate_mismatch_count": len(audit["direct_candidate_mismatches"]),
        "method_label_disagreement_count": len(audit["method_label_disagreements"]),
        "result_disagreement_count": len(audit["result_disagreements"]),
        "sha256": audit["sha256"],
        "upstream": audit["upstream"],
        "upstream_commit": audit["upstream_commit"],
        "license": audit["license"],
        "authority": "cross_check_only",
    }


def expected_hour_pillar(day_ganzhi: str, hour_branch: str) -> str:
    if day_ganzhi not in VALID_JIAZI:
        raise ValueError(f"invalid sexagenary day pillar: {day_ganzhi!r}")
    if hour_branch not in BRANCHES:
        raise ValueError(f"invalid hour branch: {hour_branch!r}")
    stem_index = ((STEMS.index(day_ganzhi[0]) % 5) * 2 + BRANCHES.index(hour_branch)) % 10
    return STEMS[stem_index] + hour_branch


def _validate_chart_inputs(
    day_ganzhi: str,
    hour_ganzhi: str,
    month_general: str,
    *,
    strict_hour_pillar: bool = True,
) -> None:
    if day_ganzhi not in VALID_JIAZI:
        raise ValueError(f"invalid sexagenary day pillar: {day_ganzhi!r}")
    if hour_ganzhi not in VALID_JIAZI:
        raise ValueError(f"invalid sexagenary hour pillar: {hour_ganzhi!r}")
    expected = expected_hour_pillar(day_ganzhi, hour_ganzhi[1])
    if strict_hour_pillar and hour_ganzhi != expected:
        raise ValueError(
            f"incompatible hour pillar: {hour_ganzhi} cannot occur on {day_ganzhi} day; expected {expected}"
        )
    if month_general not in BRANCHES:
        raise ValueError(f"invalid month general: {month_general!r}")


def _heaven_plate(month_general: str, hour_branch: str) -> tuple[dict[str, str], int]:
    offset = (BRANCHES.index(month_general) - BRANCHES.index(hour_branch)) % 12
    return {
        earth: BRANCHES[(BRANCHES.index(earth) + offset) % 12]
        for earth in BRANCHES
    }, offset


def _relation(lower: str, upper: str) -> str:
    lower_element = ELEMENT[lower]
    upper_element = ELEMENT[upper]
    if OVERCOMES[lower_element] == upper_element:
        return "下贼上"
    if OVERCOMES[upper_element] == lower_element:
        return "上克下"
    if GENERATES[lower_element] == upper_element:
        return "下生上"
    if GENERATES[upper_element] == lower_element:
        return "上生下"
    return "比和"


def _four_lessons(day_ganzhi: str, heaven_plate: dict[str, str]) -> list[dict[str, Any]]:
    day_stem, day_branch = day_ganzhi
    first_lower_lodge = STEM_LODGE[day_stem]
    first_upper = heaven_plate[first_lower_lodge]
    second_upper = heaven_plate[first_upper]
    third_upper = heaven_plate[day_branch]
    fourth_upper = heaven_plate[third_upper]
    raw = (
        (day_stem, first_upper, first_lower_lodge),
        (first_upper, second_upper, first_upper),
        (day_branch, third_upper, day_branch),
        (third_upper, fourth_upper, third_upper),
    )
    return [
        {
            "lesson": index,
            "lower": lower,
            "lower_lodge": lodge,
            "upper": upper,
            "relation": _relation(lower, upper),
        }
        for index, (lower, upper, lodge) in enumerate(raw, start=1)
    ]


def _unique_lessons(lessons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for lesson in lessons:
        key = (lesson["lower"], lesson["upper"])
        if key not in seen:
            seen.add(key)
            result.append(lesson)
    return result


def _same_polarity_candidates(day_stem: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in candidates if POLARITY[item["upper"]] == POLARITY[day_stem]]


def _dedupe_by_upper(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate["upper"] not in seen:
            seen.add(candidate["upper"])
            result.append(candidate)
    return result


def _direct_candidates(lessons: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    unique = _unique_lessons(lessons)
    thieves = [item for item in unique if item["relation"] == "下贼上"]
    upper_attacks = [item for item in unique if item["relation"] == "上克下"]
    if thieves:
        return _dedupe_by_upper(thieves), "下贼上"
    if upper_attacks:
        return _dedupe_by_upper(upper_attacks), "上克下"
    return [], None


def _ground_class(branch: str) -> str:
    if branch in MENG_BRANCHES:
        return "孟"
    if branch in ZHONG_BRANCHES:
        return "仲"
    return "季"


def _lodged_stems(branch: str) -> list[str]:
    return [stem for stem, lodge in STEM_LODGE.items() if lodge == branch]


def _candidate_harm_trace(candidate: dict[str, Any]) -> dict[str, Any]:
    upper = candidate["upper"]
    ground = candidate["lower_lodge"]
    mode = candidate.get("_harm_mode")
    if mode is None:
        if candidate["relation"] == "下贼上":
            mode = "path_overcomes_upper"
        elif candidate["relation"] == "上克下":
            mode = "upper_overcomes_path"
        else:
            raise ValueError("shehai candidate lacks a usable overcome direction")

    positions: list[dict[str, Any]] = []
    cursor = (BRANCHES.index(ground) + 1) % 12
    for _ in range(11):
        branch = BRANCHES[cursor]
        if branch == upper:
            break
        lodged = _lodged_stems(branch)
        if mode == "path_overcomes_upper":
            branch_hit = OVERCOMES[ELEMENT[branch]] == ELEMENT[upper]
            stem_hits = [stem for stem in lodged if OVERCOMES[ELEMENT[stem]] == ELEMENT[upper]]
        else:
            branch_hit = OVERCOMES[ELEMENT[upper]] == ELEMENT[branch]
            stem_hits = [stem for stem in lodged if OVERCOMES[ELEMENT[upper]] == ELEMENT[stem]]
        positions.append({
            "ground": branch,
            "branch_hit": branch_hit,
            "lodged_stems": lodged,
            "lodged_stem_hits": stem_hits,
            "depth_added": int(branch_hit) + len(stem_hits),
        })
        cursor = (cursor + 1) % 12
    else:
        raise RuntimeError("shehai traversal did not reach the candidate's home branch")

    return {
        "lesson": candidate["lesson"],
        "upper": upper,
        "starting_ground": ground,
        "ground_class": _ground_class(ground),
        "mode": mode,
        "path": positions,
        "depth": sum(item["depth_added"] for item in positions),
    }


def _select_shehai(
    day_stem: str,
    candidates: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    traces = [_candidate_harm_trace(candidate) for candidate in candidates]
    max_depth = max(item["depth"] for item in traces)
    deepest_uppers = {item["upper"] for item in traces if item["depth"] == max_depth}
    deepest = [candidate for candidate in candidates if candidate["upper"] in deepest_uppers]
    tie_break = "unique_deepest"
    subtype = "涉害"

    if len(deepest) > 1:
        meng = [item for item in deepest if item["lower_lodge"] in MENG_BRANCHES]
        zhong = [item for item in deepest if item["lower_lodge"] in ZHONG_BRANCHES]
        if meng:
            finalists = meng
            tie_break = "meng_before_zhong_ji"
            subtype = "见机"
        elif zhong:
            finalists = zhong
            tie_break = "zhong_before_ji"
            subtype = "察微"
        else:
            finalists = deepest
            tie_break = "ji_only"
            subtype = "察微"

        if len(finalists) > 1:
            anchor = lessons[0]["upper"] if POLARITY[day_stem] == "阳" else lessons[2]["upper"]
            anchor_match = [item for item in finalists if item["upper"] == anchor]
            if anchor_match:
                selected = anchor_match[0]
                tie_break = "repeat_equal_day_upper" if POLARITY[day_stem] == "阳" else "repeat_equal_branch_upper"
            else:
                selected = min(finalists, key=lambda item: item["lesson"])
                tie_break = "repeat_equal_first_visible_lesson"
            subtype = "缀瑕/复等"
        else:
            selected = finalists[0]
    else:
        selected = deepest[0]

    return selected, {
        "subtype": subtype,
        "candidate_harm_paths": traces,
        "maximum_depth": max_depth,
        "deepest_candidates": [item["upper"] for item in deepest],
        "tie_break": tie_break,
        "selected": selected["upper"],
        "source_anchor": "daliuren-daquan L7082/L7212",
    }


def _select_by_comparison(
    day_stem: str,
    candidates: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    same = _same_polarity_candidates(day_stem, candidates)
    comparison = {
        "day_stem": day_stem,
        "day_polarity": POLARITY[day_stem],
        "original_candidates": [item["upper"] for item in candidates],
        "same_polarity_candidates": [item["upper"] for item in same],
    }
    if len(same) == 1:
        selected = same[0]
        comparison.update({"result": "比用/知一", "selected": selected["upper"]})
        return selected, "比用", comparison

    shehai_candidates = same if len(same) > 1 else candidates
    selected, shehai = _select_shehai(day_stem, shehai_candidates, lessons)
    comparison.update({
        "result": "涉害",
        "shehai_candidate_basis": "俱比" if same else "俱不比",
        "shehai": shehai,
        "selected": selected["upper"],
    })
    return selected, "涉害", comparison


def _ordinary_transmissions(initial: str, heaven_plate: dict[str, str]) -> tuple[str, str, str]:
    middle = heaven_plate[initial]
    return initial, middle, heaven_plate[middle]


def _fuyin_transmissions(
    initial: str,
    lessons: list[dict[str, Any]],
) -> tuple[tuple[str, str, str], dict[str, Any]]:
    day_upper = lessons[0]["upper"]
    branch_upper = lessons[2]["upper"]
    trace: list[dict[str, str]] = []
    if PUNISHMENT[initial] == initial:
        middle = branch_upper if initial == day_upper else day_upper
        trace.append({"step": "middle", "rule": "initial_self_punishment_switch_day_branch", "branch": middle})
    else:
        middle = PUNISHMENT[initial]
        trace.append({"step": "middle", "rule": "punishment", "branch": middle})

    proposed_final = PUNISHMENT[middle]
    if proposed_final == middle or proposed_final == initial:
        final = CLASH[middle]
        trace.append({"step": "final", "rule": "middle_blocked_use_clash", "branch": final})
    else:
        final = proposed_final
        trace.append({"step": "final", "rule": "punishment", "branch": final})
    return (initial, middle, final), {"punishment_clash_trace": trace}


def _calculate_transmissions(
    day_ganzhi: str,
    lessons: list[dict[str, Any]],
    heaven_plate: dict[str, str],
    offset: int,
    *,
    biezhe_profile: str = "daliuren-daquan-body-branch",
) -> dict[str, Any]:
    if biezhe_profile not in BIEZHE_PROFILES:
        raise ValueError(f"unsupported biezhe profile: {biezhe_profile!r}")

    day_stem, day_branch = day_ganzhi
    direct, direct_direction = _direct_candidates(lessons)
    upper_lessons = _dedupe_by_upper(_unique_lessons(lessons))
    remote_god_over_day = [
        {**item, "_harm_mode": "upper_overcomes_path"}
        for item in upper_lessons
        if OVERCOMES[ELEMENT[item["upper"]]] == ELEMENT[day_stem]
    ]
    remote_day_over_god = [
        {**item, "_harm_mode": "path_overcomes_upper"}
        for item in upper_lessons
        if OVERCOMES[ELEMENT[day_stem]] == ELEMENT[item["upper"]]
    ]
    method: dict[str, Any] = {
        "calculation_source": "classical_nine-method_algorithm",
        "direct_direction": direct_direction,
        "direct_candidates": [item["upper"] for item in direct],
        "remote_god_over_day": [item["upper"] for item in remote_god_over_day],
        "remote_day_over_god": [item["upper"] for item in remote_day_over_god],
        "rule_order": ["贼克", "比用/知一", "涉害", "遥克", "昴星", "别责", "八专", "伏吟", "反吟"],
    }

    def select_direct() -> tuple[dict[str, Any], str, dict[str, Any]]:
        if len(direct) == 1:
            name = "重审" if direct_direction == "下贼上" else "元首"
            selected = direct[0]
            return selected, name, {
                "result": name,
                "original_candidates": [selected["upper"]],
                "selected": selected["upper"],
            }
        return _select_by_comparison(day_stem, direct, lessons)

    if offset == 0:
        if direct:
            selected, selection_method, selection_trace = select_direct()
            initial = selected["upper"]
            use_method = f"伏吟有克/{selection_method}"
        else:
            initial = lessons[0]["upper"] if POLARITY[day_stem] == "阳" else lessons[2]["upper"]
            selection_trace = {
                "result": "伏吟无克刚干柔辰",
                "day_polarity": POLARITY[day_stem],
                "selected": initial,
            }
            use_method = "伏吟无克刑传"
        transmissions, special_trace = _fuyin_transmissions(initial, lessons)
        method.update({
            "primary": "伏吟",
            "use_method": use_method,
            "source_anchor": "daliuren-daquan L7696/L7818",
            "selection_trace": selection_trace,
            "special_trace": special_trace,
        })
    elif offset == 6:
        if direct:
            selected, selection_method, selection_trace = select_direct()
            initial = selected["upper"]
            transmissions = _ordinary_transmissions(initial, heaven_plate)
            use_method = f"反吟有克/{selection_method}"
        else:
            if day_branch not in {"丑", "未"}:
                raise RuntimeError(f"unresolved no-ke fanyin day outside the classical six-day set: {day_ganzhi}")
            initial = "亥" if day_branch == "丑" else "巳"
            transmissions = (initial, lessons[2]["upper"], lessons[0]["upper"])
            selection_trace = {
                "result": "井栏射",
                "day_branch": day_branch,
                "well_rail_initial": initial,
                "middle_from": "branch_upper",
                "final_from": "day_upper",
            }
            use_method = "井栏射"
        method.update({
            "primary": "反吟",
            "use_method": use_method,
            "source_anchor": "daliuren-daquan L7874/L7960",
            "selection_trace": selection_trace,
        })
        if not direct:
            method["well_rail_trace"] = selection_trace
    elif direct:
        selected, primary, selection_trace = select_direct()
        initial = selected["upper"]
        transmissions = _ordinary_transmissions(initial, heaven_plate)
        source_anchor = "daliuren-daquan L7082/L7212" if primary == "涉害" else "daliuren-daquan L6996"
        method.update({
            "primary": primary,
            "use_method": primary,
            "source_anchor": source_anchor,
            "selection_trace": selection_trace,
        })
    elif day_ganzhi in BAZHUAN_DAYS:
        if POLARITY[day_stem] == "阳":
            starting = lessons[0]["upper"]
            initial = BRANCHES[(BRANCHES.index(starting) + 2) % 12]
            direction = "forward"
        else:
            starting = lessons[3]["upper"]
            initial = BRANCHES[(BRANCHES.index(starting) - 2) % 12]
            direction = "reverse"
        transmissions = (initial, lessons[0]["upper"], lessons[0]["upper"])
        method.update({
            "primary": "八专",
            "use_method": "八专无克顺逆三神",
            "source_anchor": "daliuren-daquan L7556/L7652",
            "selection_trace": {
                "result": "八专",
                "starting_branch": starting,
                "count_includes_start": True,
                "direction": direction,
                "selected": initial,
            },
        })
    elif remote_god_over_day or remote_day_over_god:
        remote = remote_god_over_day or remote_day_over_god
        remote_name = "蒿矢" if remote_god_over_day else "弹射"
        if len(remote) == 1:
            selected = remote[0]
            selection_method = "single_remote_candidate"
            selection_trace = {
                "result": selection_method,
                "original_candidates": [selected["upper"]],
                "selected": selected["upper"],
            }
        else:
            selected, selection_method, selection_trace = _select_by_comparison(day_stem, remote, lessons)
        initial = selected["upper"]
        transmissions = _ordinary_transmissions(initial, heaven_plate)
        method.update({
            "primary": "遥克",
            "use_method": remote_name if selection_method == "single_remote_candidate" else f"{remote_name}/{selection_method}",
            "source_anchor": "daliuren-daquan L7268",
            "selection_trace": selection_trace,
        })
    elif len({item["upper"] for item in lessons}) == 3:
        day_upper = lessons[0]["upper"]
        if POLARITY[day_stem] == "阳":
            combined_stem = STEM_COMBINATION[day_stem]
            combined_lodge = STEM_LODGE[combined_stem]
            initial = heaven_plate[combined_lodge]
            selection_trace = {
                "result": "刚日干合上神",
                "combined_stem": combined_stem,
                "combined_stem_lodge": combined_lodge,
                "selected": initial,
            }
        else:
            trine_branch = TRINE_FORWARD[day_branch]
            trine_upper = heaven_plate[trine_branch]
            initial = trine_branch if biezhe_profile == "daliuren-daquan-body-branch" else trine_upper
            selection_trace = {
                "result": "柔日支前三合",
                "trine_forward_branch": trine_branch,
                "upper_over_trine_branch": trine_upper,
                "biezhe_profile": biezhe_profile,
                "selected": initial,
            }
            method["source_variant"] = {
                "type": "biezhe_yin_source_variant",
                "adopted_profile": biezhe_profile,
                "adopted_initial": initial,
                "alternate_initial": trine_upper if initial == trine_branch else trine_branch,
                "resolution": "profile is explicit; never switch silently",
            }
        transmissions = (initial, day_upper, day_upper)
        method.update({
            "primary": "别责",
            "use_method": "别责",
            "source_anchor": "daliuren-daquan L7514/L7550",
            "biezhe_profile": biezhe_profile,
            "selection_trace": selection_trace,
        })
    else:
        inverse_plate = {heaven: earth for earth, heaven in heaven_plate.items()}
        if POLARITY[day_stem] == "阳":
            initial = heaven_plate["酉"]
            transmissions = (initial, lessons[2]["upper"], lessons[0]["upper"])
            use_method = "阳仰酉上"
            selected_from = "earth_you_above"
        else:
            initial = inverse_plate["酉"]
            transmissions = (initial, lessons[0]["upper"], lessons[2]["upper"])
            use_method = "阴俯酉下"
            selected_from = "heaven_you_below"
        method.update({
            "primary": "昴星",
            "use_method": use_method,
            "source_anchor": "daliuren-daquan L7410/L7436",
            "selection_trace": {
                "result": use_method,
                "selected_from": selected_from,
                "selected": initial,
            },
        })

    method["selected_initial"] = transmissions[0]
    method["calculated_transmissions"] = "".join(transmissions)
    return {"transmissions": transmissions, "method": method}


def _day_night(hour_branch: str, profile: str) -> str:
    if profile != "civil-double-hour":
        raise ValueError(f"unsupported day/night profile: {profile!r}")
    return "day" if hour_branch in DAY_BRANCHES else "night"


def _heavenly_generals(
    day_stem: str,
    hour_branch: str,
    heaven_plate: dict[str, str],
    guiren_profile: str,
    day_night_profile: str,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    if guiren_profile not in GUIREN_PROFILES:
        raise ValueError(f"unsupported guiren profile: {guiren_profile!r}")
    period = _day_night(hour_branch, day_night_profile)
    profile = GUIREN_PROFILES[guiren_profile]
    noble_branch = profile[period][day_stem]
    noble_earth = next(earth for earth, heaven in heaven_plate.items() if heaven == noble_branch)
    direction = "forward" if noble_earth in set("亥子丑寅卯辰") else "reverse"
    noble_index = BRANCHES.index(noble_earth)
    by_earth: dict[str, str] = {}
    for index, general in enumerate(HEAVENLY_GENERAL_ORDER):
        earth_index = (noble_index + index) % 12 if direction == "forward" else (noble_index - index) % 12
        by_earth[BRANCHES[earth_index]] = general
    rows = [
        {"earth": earth, "heaven": heaven_plate[earth], "general": by_earth[earth]}
        for earth in BRANCHES
    ]
    return rows, {
        "branch": noble_branch,
        "period": period,
        "earth_position": noble_earth,
        "direction": direction,
        "profile": guiren_profile,
        "day_night_profile": day_night_profile,
        "source": profile["source"],
    }


def _six_relative(day_stem: str, branch: str) -> str:
    day_element = ELEMENT[day_stem]
    branch_element = ELEMENT[branch]
    if day_element == branch_element:
        return "兄弟"
    if GENERATES[day_element] == branch_element:
        return "子孙"
    if GENERATES[branch_element] == day_element:
        return "父母"
    if OVERCOMES[day_element] == branch_element:
        return "妻财"
    return "官鬼"


def _xunkong(day_ganzhi: str) -> dict[str, Any]:
    day_index = JIAZI.index(day_ganzhi)
    start = (day_index // 10) * 10
    present = {JIAZI[index][1] for index in range(start, start + 10)}
    empty = [branch for branch in BRANCHES if branch not in present]
    return {"xun": JIAZI[start], "branches": empty}


def _xun_hidden_stem(day_ganzhi: str, branch: str) -> str | None:
    """Return the stem occupying ``branch`` in the day xun, or null if void."""

    if day_ganzhi not in VALID_JIAZI:
        raise ValueError(f"invalid sexagenary day pillar: {day_ganzhi!r}")
    if branch not in BRANCHES:
        raise ValueError(f"invalid transmission branch: {branch!r}")
    start = (JIAZI.index(day_ganzhi) // 10) * 10
    for ganzhi in JIAZI[start : start + 10]:
        if ganzhi[1] == branch:
            return ganzhi[0]
    return None


def _structural_patterns(day_ganzhi: str, lessons: list[dict[str, Any]], offset: int) -> list[str]:
    patterns: list[str] = []
    if offset == 0:
        patterns.append("伏吟")
    if offset == 6:
        patterns.append("反吟")
    if day_ganzhi in BAZHUAN_DAYS:
        patterns.append("八专日")
    if len(set(item["upper"] for item in lessons)) < 4:
        patterns.append("四课不备")
    return patterns


def _build_core(
    *,
    day_ganzhi: str,
    hour_ganzhi: str,
    month_general: str,
    question: str,
    location: str,
    guiren_profile: str,
    day_night_profile: str,
    biezhe_profile: str,
    strict_hour_pillar: bool = True,
) -> dict[str, Any]:
    _validate_chart_inputs(
        day_ganzhi,
        hour_ganzhi,
        month_general,
        strict_hour_pillar=strict_hour_pillar,
    )
    if not question.strip():
        raise ValueError("a concrete divination question is required")
    if not location.strip():
        raise ValueError("location is required")

    heaven_plate, offset = _heaven_plate(month_general, hour_ganzhi[1])
    lessons = _four_lessons(day_ganzhi, heaven_plate)
    first_upper = lessons[0]["upper"]
    record = _transmission_table()[day_ganzhi][BRANCHES.index(first_upper)]
    calculated = _calculate_transmissions(
        day_ganzhi,
        lessons,
        heaven_plate,
        offset,
        biezhe_profile=biezhe_profile,
    )
    method = calculated["method"]
    canonical_table_label = "比用" if record["格局"] == "知一" else record["格局"]
    label_disagreement = offset not in {0, 6} and canonical_table_label != method["primary"]
    result_disagreement = record["干支组合"] != method["calculated_transmissions"]
    method.update({
        "table_label": record["格局"],
        "table_transmissions": record["干支组合"],
        "table_disagreement": label_disagreement,
        "table_result_disagreement": result_disagreement,
    })
    label_variant = _classical_method_label_variant(
        day_ganzhi,
        hour_ganzhi[1],
        month_general,
    )
    if label_variant:
        if label_variant.get("calculated_label") != method["primary"]:
            raise RuntimeError(
                "Liuren source-label variant contradicts the calculated method"
            )
        if label_variant.get("transmissions") != method["calculated_transmissions"]:
            raise RuntimeError(
                "Liuren source-label variant contradicts calculated transmissions"
            )
    method["source_label_variants"] = [dict(label_variant)] if label_variant else []

    generals, noble = _heavenly_generals(
        day_ganzhi[0], hour_ganzhi[1], heaven_plate, guiren_profile, day_night_profile
    )
    general_by_heaven = {item["heaven"]: item["general"] for item in generals}
    transmissions = [
        {
            "stage": stage,
            "branch": branch,
            "hidden_stem": _xun_hidden_stem(day_ganzhi, branch),
            "heavenly_general": general_by_heaven[branch],
            "six_relative": _six_relative(day_ganzhi[0], branch),
        }
        for stage, branch in zip(("initial", "middle", "final"), calculated["transmissions"])
    ]

    conflicts: list[dict[str, Any]] = []
    if label_disagreement:
        conflicts.append({
            "type": "transmission_table_method_label",
            "table_label": method["table_label"],
            "classical_derived_label": method["primary"],
            "resolution": "used the classical algorithm; retained the table label only as conflicting witness metadata",
        })
    if result_disagreement:
        conflicts.append({
            "type": "transmission_table_result",
            "table_transmissions": method["table_transmissions"],
            "classical_transmissions": method["calculated_transmissions"],
            "resolution": "used the auditable classical algorithm; the 720 table cannot override it",
        })
    if "source_variant" in method:
        conflicts.append(method["source_variant"])
    if label_variant:
        conflicts.append(
            {
                "type": "classical_method_label_variant",
                **label_variant,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "fact_layer_status": "deterministic_liuren_chart",
        "fact_layer_scope": "concrete_short_event",
        "adapter": {
            "name": ADAPTER_NAME,
            "version": VERSION,
            "generated_at": _utc_now(),
            "rule_profile": {
                "transmissions": "daliuren-daquan-wyg-classical-nine-method-v2",
                "guiren": guiren_profile,
                "day_night": day_night_profile,
                "month_general": "solar-term-pair-boundary",
                "biezhe": biezhe_profile,
                "transmission_hidden_stems": TRANSMISSION_HIDDEN_STEM_PROFILE,
                "hour_stem_validation": (
                    "five-rat-strict"
                    if strict_hour_pillar
                    else "shared-calendar-authoritative"
                ),
            },
            "license_status": "local_code; vendored table Apache-2.0",
        },
        "input": {
            "question": question.strip(),
            "location": location.strip(),
            "normalized_chart_input": {
                "day": day_ganzhi,
                "hour": hour_ganzhi,
                "month_general": month_general,
            },
        },
        "calendar_normalization": {
            "status": "supplied_chart_inputs",
            "civil_datetime": "not_supplied",
            "lunar_date": {"status": "not_calculated_in_chart_mode"},
            "ganzhi": {"day": day_ganzhi, "hour": hour_ganzhi},
            "solar_terms": {"status": "month_general_supplied", "month_general": month_general},
        },
        "output": {
            "earth_plate": list(BRANCHES),
            "heaven_plate": [{"earth": earth, "heaven": heaven_plate[earth]} for earth in BRANCHES],
            "plate_offset": offset,
            "month_general": {"branch": month_general, "name": MONTH_GENERAL_NAMES[month_general]},
            "day_hour": {"day": day_ganzhi, "hour": hour_ganzhi},
            "four_lessons": lessons,
            "three_transmissions": transmissions,
            "transmission_method": method,
            "structural_patterns": _structural_patterns(day_ganzhi, lessons, offset),
            "heavenly_generals": generals,
            "noble_person": noble,
            "xunkong": _xunkong(day_ganzhi),
        },
        "source_trace": {
            "classical_primary": [
                "《大六壬大全》卷一起例与卷七课经：入手法、比用、涉害、遥克、昴星、别责、八专、伏吟、返吟",
                "Kanripo KR3g0031 文渊阁转写卷一、卷五交叉见证",
            ],
            "interpretive_witness": [
                "《六壬指南》卷一《心印赋》及陈注；其涉害口径另存，不覆盖本 adapter 的大全/WYG profile",
                "《大六壬秘本》仅作类象与专项解释旁证，不参与本 adapter 取传",
            ],
            "guiren_profile": GUIREN_PROFILES[guiren_profile]["source"],
            "transmission_hidden_stems": {
                "calculation_source": TRANSMISSION_HIDDEN_STEM_PROFILE,
                "source_pack": "san-shi/liuren-miben",
                "source_anchor": "quote-index.md#LM-Q008",
                "source_scope": (
                    "xun-table and void-branch witness only; stem assignment is "
                    "the deterministic sixty-Jiazi enumeration"
                ),
            },
            "transmission_table": _compact_transmission_table_audit(),
        },
        "trace": [
            (
                "validated supplied day/hour sexagenary compatibility with the five-rat hour rule"
                if strict_hour_pillar
                else "accepted the authoritative shared-calendar day/hour pillars; Liuren placement uses the calculated hour branch"
            ),
            "placed month general over the hour branch and built the twelve-position heaven plate",
            "derived four lessons from day stem lodge and day branch",
            "derived the initial, middle, and final transmissions with the classical nine-method algorithm",
            "mapped each transmission branch to its occupied stem in the day xun; xunkong branches remain null",
            "cross-checked the calculated result against a fixed 60x12 table without allowing the table to override it",
            "placed heavenly generals under the explicitly selected guiren and day/night profiles",
        ],
        "warnings": [
            "This payload is a deterministic traditional-calculation fact layer, not empirical proof that divination predicts real events.",
            "Do not silently switch guiren, day/night, timezone, Zi-hour, or month-general profiles between casts.",
            "Use Da Liu Ren for one concrete short-event question; broad daily fortune remains on the Bazi near-time route.",
        ],
        "conflicts": conflicts,
    }


def build_from_chart(
    *,
    day_ganzhi: str,
    hour_ganzhi: str,
    month_general: str,
    question: str,
    location: str,
    guiren_profile: str = "official-corrected",
    day_night_profile: str = "civil-double-hour",
    biezhe_profile: str = "daliuren-daquan-body-branch",
) -> dict[str, Any]:
    return _build_core(
        day_ganzhi=day_ganzhi,
        hour_ganzhi=hour_ganzhi,
        month_general=month_general,
        question=question,
        location=location,
        guiren_profile=guiren_profile,
        day_night_profile=day_night_profile,
        biezhe_profile=biezhe_profile,
    )


def build_from_datetime(
    civil_datetime: str,
    *,
    timezone_name: str,
    location: str,
    question: str,
    guiren_profile: str = "official-corrected",
    day_night_profile: str = "civil-double-hour",
    zi_hour_policy: str = "midnight",
    biezhe_profile: str = "daliuren-daquan-body-branch",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    coordinate_accuracy_meters: float | None = None,
    time_basis_policy: str = "civil",
) -> dict[str, Any]:
    normalized_location = str(location).strip()
    calendar = calendar_core.normalize_calendar(
        civil_datetime,
        timezone_name=timezone_name,
        location=normalized_location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        coordinate_accuracy_meters=coordinate_accuracy_meters,
        zi_hour_policy=zi_hour_policy,
        time_basis_policy=time_basis_policy,
    )
    pillars = dict(calendar["ganzhi"])
    previous_term = calendar["solar_terms"]["previous"]
    month_general = TERM_TO_MONTH_GENERAL[previous_term["name"]]

    payload = _build_core(
        day_ganzhi=pillars["day"],
        hour_ganzhi=pillars["hour"],
        month_general=month_general,
        question=question,
        location=normalized_location,
        guiren_profile=guiren_profile,
        day_night_profile=day_night_profile,
        biezhe_profile=biezhe_profile,
        strict_hour_pillar=True,
    )
    payload["input"].update({
        "civil_datetime": civil_datetime,
        "timezone": timezone_name,
        "zi_hour_policy": zi_hour_policy,
        "longitude": longitude,
        "latitude": latitude,
        "coordinate_source": coordinate_source,
        "coordinate_accuracy_meters": coordinate_accuracy_meters,
        "time_basis_policy": time_basis_policy,
    })
    payload["calendar_normalization"] = calendar
    payload["trace"].insert(0, "converted civil date to lunar date and four pillars with sxtwl")
    payload["trace"].insert(1, "selected month general from the current solar-term pair")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    cast = subparsers.add_parser("cast", help="Cast from a civil datetime")
    cast.add_argument("--datetime", required=True, dest="civil_datetime")
    cast.add_argument("--timezone", required=True)
    cast.add_argument("--location", required=True)
    cast.add_argument("--longitude", type=float)
    cast.add_argument("--latitude", type=float)
    cast.add_argument("--coordinate-source")
    cast.add_argument("--coordinate-accuracy-meters", type=float)
    cast.add_argument("--question", required=True)
    cast.add_argument("--guiren-profile", choices=tuple(GUIREN_PROFILES), default="official-corrected")
    cast.add_argument("--day-night-profile", choices=("civil-double-hour",), default="civil-double-hour")
    cast.add_argument("--zi-hour-policy", choices=("midnight", "late-zi-next-day"), default="midnight")
    cast.add_argument("--biezhe-profile", choices=tuple(BIEZHE_PROFILES), default="daliuren-daquan-body-branch")
    cast.add_argument("--time-basis-policy", default="civil")
    cast.add_argument("--output")

    chart = subparsers.add_parser("chart", help="Build from supplied day/hour/month-general facts")
    chart.add_argument("--day", required=True, dest="day_ganzhi")
    chart.add_argument("--hour", required=True, dest="hour_ganzhi")
    chart.add_argument("--month-general", required=True)
    chart.add_argument("--location", required=True)
    chart.add_argument("--question", required=True)
    chart.add_argument("--guiren-profile", choices=tuple(GUIREN_PROFILES), default="official-corrected")
    chart.add_argument("--day-night-profile", choices=("civil-double-hour",), default="civil-double-hour")
    chart.add_argument("--biezhe-profile", choices=tuple(BIEZHE_PROFILES), default="daliuren-daquan-body-branch")
    chart.add_argument("--output")

    table_audit = subparsers.add_parser("audit-table", help="Print the full fixed-table cross-check audit")
    table_audit.add_argument("--output")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.mode == "cast":
            payload = build_from_datetime(
                args.civil_datetime,
                timezone_name=args.timezone,
                location=args.location,
                question=args.question,
                guiren_profile=args.guiren_profile,
                day_night_profile=args.day_night_profile,
                zi_hour_policy=args.zi_hour_policy,
                biezhe_profile=args.biezhe_profile,
                longitude=args.longitude,
                latitude=args.latitude,
                coordinate_source=args.coordinate_source,
                coordinate_accuracy_meters=args.coordinate_accuracy_meters,
                time_basis_policy=args.time_basis_policy,
            )
        elif args.mode == "chart":
            payload = build_from_chart(
                day_ganzhi=args.day_ganzhi,
                hour_ganzhi=args.hour_ganzhi,
                month_general=args.month_general,
                location=args.location,
                question=args.question,
                guiren_profile=args.guiren_profile,
                day_night_profile=args.day_night_profile,
                biezhe_profile=args.biezhe_profile,
            )
        else:
            payload = audit_transmission_table()
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
