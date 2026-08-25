"""Deterministic, source-profiled date-selection candidate engine.

The module accepts only structured intent. It calculates calendar and almanac facts,
keeps official and folk lineages separate, and emits explainable ranking components;
it does not interpret request prose or produce a real-world event guarantee.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from cnlunar import Lunar
from cnlunar import config as cnlunar_config

from . import calendar_core, evidence_rules
from .contracts import FactRef, canonical_digest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_TABLE_PATH = ROOT / "references/matrices/selection-source-tables-v1.yaml"
FACT_PROFILE_PATH = ROOT / "references/matrices/selection-fact-layer-profile.yaml"
DONGGONG_TABLE_PATH = (
    ROOT / "references/books/selection/donggong-zeri/monthly-day-table.md"
)

ADAPTER_NAME = "mingli-master.selection"
ADAPTER_VERSION = "1.3.0"
TABLE_PROFILE = "xieji-official-cnlunar-v1"
FACT_LAYER_STATUS = "deterministic_selection_candidates"
FACT_LAYER_SCOPE = "bounded_candidate_ranking_not_event_guarantee"
MAX_RANGE_DAYS = 366
SUPPORTED_SCOPES = frozenset(("directional_judgment",))
UNIVERSAL_AVOIDANCE = "诸事不宜"
SOURCE_DEPENDENCIES = (
    "selection.candidate-calendar-foundation",
    "selection.day-facts.jianchu-mansions-gods",
    "selection.hour-facts.ganzhi-and-twelve-gods",
    "selection.event-rules-and-lineage-conflicts",
    "selection.runtime.cnlunar-official-tables",
    "selection.source-conditioned-patterns",
)

BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")
TWENTY_FOUR_MOUNTAINS = tuple("壬子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥")
STEMS = tuple("甲乙丙丁戊己庚辛壬癸")
ZODIACS = tuple("鼠牛虎兔龙蛇马羊猴鸡狗猪")
OPPOSITE_BRANCHES = {
    branch: BRANCHES[(index + 6) % 12]
    for index, branch in enumerate(BRANCHES)
}
JIANCHU = tuple("建除满平定执破危成收开闭")
PATH_GODS = (
    "青龙", "明堂", "天刑", "朱雀", "金贵", "天德",
    "白虎", "玉堂", "天牢", "玄武", "司命", "勾陈",
)
HUANG_PATH_INDICES = frozenset((0, 1, 4, 5, 7, 10))
PATH_START_INDICES = (8, 10, 0, 2, 4, 6, 8, 10, 0, 2, 4, 6)
HOUR_REPRESENTATIVES = (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)
HOUR_CIVIL_SEGMENTS = (
    ((0, 60), (1380, 1440)),
    ((60, 180),),
    ((180, 300),),
    ((300, 420),),
    ((420, 540),),
    ((540, 660),),
    ((660, 780),),
    ((780, 900),),
    ((900, 1020),),
    ((1020, 1140),),
    ((1140, 1260),),
    ((1260, 1380),),
)
YANG_GONG_DATES = frozenset(
    (
        (1, 13), (2, 11), (3, 9), (4, 7), (5, 5), (6, 2),
        (7, 1), (7, 29), (8, 27), (9, 25), (10, 23),
        (11, 21), (12, 19),
    )
)
MONTH_TABOO_DAYS = frozenset((5, 14, 23))
DONGGONG_JIANCHU_GLYPHS = {
    "建": "建", "除": "除", "满": "滿", "平": "平", "定": "定", "执": "執",
    "破": "破", "危": "危", "成": "成", "收": "收", "开": "開", "闭": "閉",
}
THREE_SHA_BY_TRINE = (
    ("申子辰", "巳", "午", "未", "south"),
    ("巳酉丑", "寅", "卯", "辰", "east"),
    ("寅午戌", "亥", "子", "丑", "north"),
    ("亥卯未", "申", "酉", "戌", "west"),
)


@lru_cache(maxsize=1)
def source_table() -> dict[str, Any]:
    payload = yaml.safe_load(SOURCE_TABLE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != (
        "mingli-selection-source-tables-v1"
    ):
        raise RuntimeError("invalid Selection source table")
    return payload


def _clean_unique(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _parse_iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO civil date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO civil date") from exc


def _normalize_hard_constraints(raw: Any) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ValueError("hard_constraints must be an object")
    constraints: dict[str, Any] = {}
    for field in ("excluded_dates",):
        values = raw.get(field) or []
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"hard_constraints.{field} must be a list")
        constraints[field] = sorted(
            {_parse_iso_date(item, field).isoformat() for item in values}
        )
    for field in ("allowed_weekdays", "excluded_weekdays"):
        values = raw.get(field) or []
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"hard_constraints.{field} must be a list")
        normalized = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 7:
                raise ValueError(f"hard_constraints.{field} values must be ISO weekdays 1..7")
            normalized.append(value)
        constraints[field] = sorted(set(normalized))
    for field in ("allowed_hour_branches", "excluded_hour_branches"):
        values = raw.get(field) or []
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"hard_constraints.{field} must be a list")
        normalized = list(dict.fromkeys(str(value) for value in values))
        if any(value not in BRANCHES for value in normalized):
            raise ValueError(f"hard_constraints.{field} contains an invalid branch")
        constraints[field] = normalized
    for field in ("earliest_date", "latest_date"):
        value = raw.get(field)
        constraints[field] = (
            _parse_iso_date(value, f"hard_constraints.{field}").isoformat()
            if value is not None
            else None
        )
    windows = raw.get("time_windows") or []
    if not isinstance(windows, (list, tuple)):
        raise ValueError("hard_constraints.time_windows must be a list")
    normalized_windows: list[dict[str, str]] = []
    for index, window in enumerate(windows):
        if not isinstance(window, Mapping):
            raise ValueError(f"time_windows[{index}] must be an object")
        start = str(window.get("start") or "")
        end = str(window.get("end") or "")
        for label, value in (("start", start), ("end", end)):
            try:
                parsed = datetime.strptime(value, "%H:%M")
            except ValueError as exc:
                raise ValueError(
                    f"time_windows[{index}].{label} must be HH:MM"
                ) from exc
            if parsed.strftime("%H:%M") != value:
                raise ValueError(f"time_windows[{index}].{label} must be HH:MM")
        if start == end:
            raise ValueError("a time window cannot have equal start and end")
        normalized_windows.append({"start": start, "end": end})
    constraints["time_windows"] = normalized_windows
    participant_hard = raw.get("participant_clash_is_hard", True)
    if not isinstance(participant_hard, bool):
        raise ValueError("hard_constraints.participant_clash_is_hard must be boolean")
    constraints["participant_clash_is_hard"] = participant_hard
    return constraints


def _normalize_participants(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        raw = []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("participant_facts must be a list")
    participants: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, participant in enumerate(raw):
        if not isinstance(participant, Mapping):
            raise ValueError(f"participant_facts[{index}] must be an object")
        identity = str(participant.get("id") or "").strip()
        if not identity or identity in seen:
            raise ValueError("participant ids must be non-empty and unique")
        row = {"id": identity}
        for field in ("year_branch", "day_branch"):
            value = participant.get(field)
            if value is not None:
                value = str(value)
                if value not in BRANCHES:
                    raise ValueError(f"participant {identity} has invalid {field}")
                row[field] = value
        if len(row) == 1:
            raise ValueError(f"participant {identity} has no supported branch fact")
        participants.append(row)
        seen.add(identity)
    return participants


def _participant_scope(
    event_profile: str,
    participants: list[dict[str, str]],
) -> dict[str, Any]:
    required_fields = ("year_branch", "day_branch")
    complete_ids = [
        row["id"]
        for row in participants
        if all(row.get(field) for field in required_fields)
    ]
    incomplete = [
        {
            "id": row["id"],
            "missing_fields": [
                field for field in required_fields if not row.get(field)
            ],
        }
        for row in participants
        if row["id"] not in complete_ids
    ]
    required_count = 2 if event_profile == "marriage" else 1
    specific = len(complete_ids) >= required_count and not incomplete
    if specific:
        status = "couple_specific" if event_profile == "marriage" else "participant_specific"
    elif participants:
        status = "partial_input_general_only"
    else:
        status = "general_only_no_participant_data"
    return {
        "status": status,
        "participant_specific": specific,
        "required_complete_participant_count": required_count,
        "complete_participant_ids": complete_ids,
        "incomplete_participants": incomplete,
        "required_fields_per_participant": list(required_fields),
    }


def normalize_spec(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("selection_spec must be an object")
    profile = str(raw.get("event_profile") or "")
    profiles = source_table()["event_profiles"]
    if profile not in profiles:
        raise ValueError("event_profile is missing or unsupported")
    raw_actions = raw.get("requested_actions")
    if raw_actions is None and profile == "generic_selection":
        raw_actions = []
    if not isinstance(raw_actions, (list, tuple)):
        raise ValueError("requested_actions must be a list")
    requested_actions = _clean_unique(raw_actions)
    supported_actions = [
        str(item) for item in profiles[profile].get("official_terms") or ()
    ]
    if profile != "generic_selection" and not requested_actions:
        raise ValueError("requested_actions requires at least one exact event action")
    unsupported_actions = sorted(set(requested_actions) - set(supported_actions))
    if unsupported_actions:
        raise ValueError(
            f"requested_actions contains actions outside event_profile: {unsupported_actions}"
        )
    requested_action_set = set(requested_actions)
    requested_actions = [
        action for action in supported_actions if action in requested_action_set
    ]
    date_range = raw.get("date_range")
    if not isinstance(date_range, Mapping):
        raise ValueError("date_range must be an object")
    start = _parse_iso_date(date_range.get("start"), "date_range.start")
    end = _parse_iso_date(date_range.get("end"), "date_range.end")
    if end < start:
        raise ValueError("date_range.end precedes date_range.start")
    day_count = (end - start).days + 1
    if day_count > MAX_RANGE_DAYS:
        raise ValueError(f"date range exceeds {MAX_RANGE_DAYS} civil days")
    if start < date(1901, 1, 1) or end > date(2100, 12, 31):
        raise ValueError("cnlunar 0.2.4 supports Selection only from 1901 through 2100")
    include_folk = raw.get("include_folk_comparison", False)
    if not isinstance(include_folk, bool):
        raise ValueError("include_folk_comparison must be boolean")
    raw_scopes = raw.get("requested_scopes") or []
    if not isinstance(raw_scopes, (list, tuple)):
        raise ValueError("requested_scopes must be a list")
    requested_scopes = _clean_unique(raw_scopes)
    unsupported_scopes = sorted(set(requested_scopes) - SUPPORTED_SCOPES)
    if unsupported_scopes:
        raise ValueError(f"unsupported Selection requested_scopes: {unsupported_scopes}")
    raw_direction = raw.get("directional_context")
    if raw_direction is not None and not isinstance(raw_direction, Mapping):
        raise ValueError("directional_context must be an object")
    direction: dict[str, str] | None = None
    if isinstance(raw_direction, Mapping):
        site_branch = str(raw_direction.get("site_branch") or "")
        site_mountain = str(raw_direction.get("site_mountain") or "")
        if site_branch and site_branch not in BRANCHES:
            raise ValueError(
                "directional_context.site_branch must be a valid branch"
            )
        if site_mountain and site_mountain not in TWENTY_FOUR_MOUNTAINS:
            raise ValueError(
                "directional_context.site_mountain must be a valid twenty-four mountain"
            )
        if not (site_branch or site_mountain):
            raise ValueError(
                "directional_context.site_branch or site_mountain is required"
            )
        direction = {
            field: value
            for field, value in (
                ("site_branch", site_branch),
                ("site_mountain", site_mountain),
            )
            if value
        }
    if "directional_judgment" in requested_scopes and direction is None:
        raise ValueError(
            "directional_context.site_branch or site_mountain is required for "
            "directional_judgment"
        )
    return {
        "event_profile": profile,
        "requested_actions": requested_actions,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "hard_constraints": _normalize_hard_constraints(raw.get("hard_constraints")),
        "participant_facts": _normalize_participants(raw.get("participant_facts")),
        "requested_scopes": requested_scopes,
        "directional_context": direction,
        "include_folk_comparison": include_folk,
    }


def _jianchu(month_branch: str, day_branch: str) -> str:
    return JIANCHU[(BRANCHES.index(day_branch) - BRANCHES.index(month_branch)) % 12]


def _day_path(month_branch: str, day_branch: str) -> dict[str, str]:
    offset = (
        BRANCHES.index(day_branch) - PATH_START_INDICES[BRANCHES.index(month_branch)]
    ) % 12
    return {
        "name": "金匮" if PATH_GODS[offset] == "金贵" else PATH_GODS[offset],
        "runtime_name": PATH_GODS[offset],
        "class": "huang" if offset in HUANG_PATH_INDICES else "hei",
        "source_dependency_id": "selection.day-facts.jianchu-mansions-gods",
    }


def _hour_path(day_branch: str, hour_branch: str) -> dict[str, str]:
    offset = (
        BRANCHES.index(hour_branch) - PATH_START_INDICES[BRANCHES.index(day_branch)]
    ) % 12
    return {
        "name": "金匮" if PATH_GODS[offset] == "金贵" else PATH_GODS[offset],
        "runtime_name": PATH_GODS[offset],
        "class": "huang" if offset in HUANG_PATH_INDICES else "hei",
    }


RuntimeContext = dict[tuple[datetime, str, str, str, str], Lunar]


def _aligned_runtime(
    local_datetime: datetime,
    calendar: Mapping[str, Any],
    runtime_context: RuntimeContext | None = None,
) -> Lunar:
    ganzhi = calendar["ganzhi"]
    context_key = (
        local_datetime,
        str(ganzhi["year"]),
        str(ganzhi["month"]),
        str(ganzhi["day"]),
        str(ganzhi["hour"]),
    )
    if runtime_context is not None and context_key in runtime_context:
        return runtime_context[context_key]
    runtime = Lunar(local_datetime, godType="8char", year8Char="beginningOfSpring")
    runtime.year8Char = str(ganzhi["year"])
    runtime.month8Char = str(ganzhi["month"])
    runtime.day8Char = str(ganzhi["day"])
    runtime.get_earthNum()
    runtime.get_heavenNum()
    runtime.get_season()
    runtime.get_today12DayOfficer()
    runtime.angelDemon = runtime.get_AngelDemon()
    if runtime_context is not None:
        runtime_context[context_key] = runtime
    return runtime


def _official_event_rules_for_calendar(
    calendar: Mapping[str, Any],
    event_profile: str,
    requested_actions: list[str] | tuple[str, ...],
    runtime_context: RuntimeContext | None = None,
) -> dict[str, Any]:
    profiles = source_table()["event_profiles"]
    if event_profile not in profiles:
        raise ValueError("unsupported event profile")
    local_datetime = datetime.fromisoformat(str(calendar["civil_datetime"]))
    runtime = _aligned_runtime(
        local_datetime.replace(tzinfo=None),
        calendar,
        runtime_context,
    )
    official_yi = _clean_unique(runtime.goodThing)
    official_ji = _clean_unique(runtime.badThing)
    declared_actions = [
        str(item) for item in profiles[event_profile].get("official_terms") or ()
    ]
    requested_set = {str(item) for item in requested_actions}
    requested = [item for item in declared_actions if item in requested_set]
    if requested_set - set(declared_actions):
        raise ValueError("requested_actions contains an action outside event_profile")
    universal_terms = [
        str(item)
        for item in source_table()["event_rule_contract"].get(
            "universal_avoidance_terms", (UNIVERSAL_AVOIDANCE,)
        )
    ]
    rules = {
        "profile": event_profile,
        "declared_actions": declared_actions,
        "requested_actions": requested,
        "action_assessments": [
            {
                "action": item,
                "yi": item in official_yi,
                "ji": item in official_ji,
                "status": (
                    "conflict"
                    if item in official_yi and item in official_ji
                    else "recommend"
                    if item in official_yi
                    else "avoid"
                    if item in official_ji
                    else "not_stated"
                ),
            }
            for item in requested
        ],
        "yi_matches": [item for item in requested if item in official_yi],
        "ji_matches": [item for item in requested if item in official_ji],
        "unrequested_action_observations": {
            "yi_matches": [
                item for item in declared_actions if item not in requested and item in official_yi
            ],
            "ji_matches": [
                item for item in declared_actions if item not in requested and item in official_ji
            ],
            "affects_eligibility": False,
        },
        "universal_avoidance_matches": [
            item for item in universal_terms if item in official_ji
        ],
        "calendar_month_ganzhi": str(calendar["ganzhi"]["month"]),
        "matching_operation": "exact_structured_action_identity",
    }
    rules["universal_avoidance"] = bool(rules["universal_avoidance_matches"])
    day_path = _day_path(
        str(calendar["ganzhi"]["month"])[1],
        str(calendar["ganzhi"]["day"])[1],
    )
    rules["day_path"] = copy.deepcopy(day_path)
    rules["assessment_digest"] = canonical_digest(rules)
    return {
        "official_yiji": {"yi": official_yi, "ji": official_ji},
        "daily_shensha": {
            "good_gods": _clean_unique(runtime.goodGodName),
            "bad_gods": _clean_unique(runtime.badGodName),
        },
        "day_path": day_path,
        "rules": rules,
    }


def _calendar_for(
    civil_date: str,
    hour: int,
    *,
    minute: int = 0,
    second: int = 0,
    timezone_name: str,
    location: str,
    longitude: Any = None,
    latitude: Any = None,
    coordinate_source: Any = None,
) -> dict[str, Any]:
    return calendar_core.normalize_calendar(
        f"{civil_date}T{hour:02d}:{minute:02d}:{second:02d}",
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        zi_hour_policy="midnight",
        time_basis_policy="civil",
    )


def _minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def _format_minute(value: int) -> str:
    if value == 1440:
        return "24:00"
    return f"{value // 60:02d}:{value % 60:02d}"


def _format_local_clock(value: datetime) -> str:
    rendered = value.strftime("%H:%M:%S.%f")
    return rendered.rstrip("0").rstrip(".")


def _valid_local_instants(
    civil_date: str,
    minute_of_day: int,
    timezone_name: str,
) -> tuple[datetime, ...]:
    zone = ZoneInfo(timezone_name)
    naive = datetime.fromisoformat(
        f"{civil_date}T{minute_of_day // 60:02d}:{minute_of_day % 60:02d}:00"
    )
    fold_zero = naive.replace(tzinfo=zone, fold=0)
    fold_one = naive.replace(tzinfo=zone, fold=1)
    if fold_zero.utcoffset() == fold_one.utcoffset():
        # PEP 495's fold flag is ignored outside a gap/fold.  The common path
        # is therefore already a single valid local instant and needs no UTC
        # round trip; transition minutes still take the exact validation path
        # below.
        return (fold_zero,)
    result: list[datetime] = []
    seen_utc: set[str] = set()
    for candidate in (fold_zero, fold_one):
        roundtrip = candidate.astimezone(timezone.utc).astimezone(zone)
        if roundtrip.replace(tzinfo=None) != naive:
            continue
        instant = candidate.astimezone(timezone.utc).isoformat()
        if instant not in seen_utc:
            result.append(candidate)
            seen_utc.add(instant)
    return tuple(sorted(result, key=lambda item: item.astimezone(timezone.utc)))


def _minute_in_windows(
    minute: int,
    windows: tuple[tuple[int, int], ...],
) -> bool:
    if not windows:
        return True
    for start, end in windows:
        if start < end and start <= minute < end:
            return True
        if start > end and (minute >= start or minute < end):
            return True
    return False


def _calendar_variant_summary(calendar: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "civil_datetime": str(calendar["civil_datetime"]),
        "instant_utc": str(calendar["instant_utc"]),
        "utc_offset_seconds": int(calendar["timezone_offset_seconds"]),
        "fold": int(calendar["timezone_details"]["fold"]),
        "lunar_date": copy.deepcopy(calendar["lunar_date"]),
        "solar_terms": copy.deepcopy(calendar["solar_terms"]),
        "ganzhi": copy.deepcopy(calendar["ganzhi"]),
        "calendar_digest": str(calendar["calendar_digest"]),
    }


def _calendar_state_key(calendar: Mapping[str, Any]) -> tuple[Any, ...]:
    ganzhi = calendar["ganzhi"]
    return (
        str(ganzhi["year"]),
        str(ganzhi["month"]),
        str(ganzhi["day"]),
        str(ganzhi["hour"]),
        int(calendar["timezone_offset_seconds"]),
        int(calendar["timezone_details"]["fold"]),
    )


def _variant_intervals(
    calendars: list[dict[str, Any]],
    segments: tuple[tuple[int, int], ...],
    minute_candidates: Mapping[int, tuple[datetime, ...]],
) -> list[dict[str, Any]]:
    coverage: list[tuple[int, int, int, int, int, int]] = []
    for segment_start, segment_end in segments:
        active: dict[tuple[int, int], int] = {}
        for minute in range(segment_start, segment_end):
            keys = {
                (
                    int((instant.utcoffset() or timedelta(0)).total_seconds()),
                    int(instant.fold),
                )
                for instant in minute_candidates[minute]
            }
            for key in list(active):
                if key not in keys:
                    coverage.append(
                        (*key, active.pop(key), minute, segment_start, segment_end)
                    )
            for key in keys:
                active.setdefault(key, minute)
        for key, start in active.items():
            coverage.append(
                (*key, start, segment_end, segment_start, segment_end)
            )

    result: list[dict[str, Any]] = []
    for (
        utc_offset,
        fold,
        coverage_start,
        coverage_end,
        segment_start,
        segment_end,
    ) in coverage:
        values = []
        for calendar in calendars:
            local = datetime.fromisoformat(str(calendar["civil_datetime"]))
            minute = local.hour * 60 + local.minute
            if not coverage_start <= minute < coverage_end:
                continue
            if int(calendar["timezone_offset_seconds"]) != utc_offset:
                continue
            if int(calendar["timezone_details"]["fold"]) != fold:
                continue
            values.append(calendar)
        if not values:
            raise RuntimeError("timezone coverage lacks a calculated calendar anchor")
        unique: list[dict[str, Any]] = []
        seen_states: set[tuple[Any, ...]] = set()
        for calendar in sorted(
            values,
            key=lambda item: datetime.fromisoformat(str(item["civil_datetime"])),
        ):
            state = _calendar_state_key(calendar)
            if state in seen_states:
                continue
            unique.append(calendar)
            seen_states.add(state)
        starts = [
            _format_minute(coverage_start),
            *[
                _format_local_clock(
                    datetime.fromisoformat(str(item["civil_datetime"]))
                )
                for item in unique[1:]
            ],
        ]
        ends = [*starts[1:], _format_minute(coverage_end)]
        for calendar, start, end in zip(unique, starts, ends):
            summary = _calendar_variant_summary(calendar)
            summary.update(
                {
                    "civil_start": start,
                    "civil_end_exclusive": end,
                    "segment_start": _format_minute(segment_start),
                    "segment_end_exclusive": _format_minute(segment_end),
                    "jianchu": _jianchu(
                        str(calendar["ganzhi"]["month"])[1],
                        str(calendar["ganzhi"]["day"])[1],
                    ),
                }
            )
            result.append(summary)
    return sorted(
        result,
        key=lambda item: (
            _clock_seconds(str(item["civil_start"])),
            int(item["utc_offset_seconds"]),
            int(item["fold"]),
        ),
    )


def _hour_facts(
    civil_date: str,
    *,
    timezone_name: str,
    location: str,
    day_branch: str,
    event_profile: str,
    requested_actions: list[str],
    directional_context: Mapping[str, str] | None,
    hard_constraints: Mapping[str, Any],
    boundary_instants: tuple[datetime, ...] = (),
    longitude: Any = None,
    latitude: Any = None,
    coordinate_source: Any = None,
    runtime_context: RuntimeContext | None = None,
) -> list[dict[str, Any]]:
    allowed = set(hard_constraints.get("allowed_hour_branches") or BRANCHES)
    excluded = set(hard_constraints.get("excluded_hour_branches") or ())
    windows = list(hard_constraints.get("time_windows") or ())
    minute_windows = tuple(
        (_minutes(window["start"]), _minutes(window["end"]))
        for window in windows
    )
    result: list[dict[str, Any]] = []
    for index, (branch, hour, segments) in enumerate(
        zip(BRANCHES, HOUR_REPRESENTATIVES, HOUR_CIVIL_SEGMENTS)
    ):
        minute_candidates = {
            minute: _valid_local_instants(civil_date, minute, timezone_name)
            for start, end in segments
            for minute in range(start, end)
        }
        valid_minutes = [
            minute for minute, candidates in minute_candidates.items() if candidates
        ]
        if not valid_minutes:
            raise ValueError(f"{civil_date} {branch} contains no valid local instant")
        preferred_minute = hour * 60
        anchor_minute = (
            preferred_minute
            if minute_candidates.get(preferred_minute)
            else valid_minutes[0]
        )
        ambiguous_minute = next(
            (
                minute
                for minute, candidates in minute_candidates.items()
                if len(candidates) > 1
            ),
            None,
        )
        segment_anchor_minutes = [
            next(
                minute
                for minute in range(start, end)
                if minute_candidates[minute]
            )
            for start, end in segments
            if any(minute_candidates[minute] for minute in range(start, end))
        ]
        transition_anchor_minutes: list[int] = []
        for start, end in segments:
            previous_signature: tuple[tuple[int, int], ...] | None = None
            for minute in range(start, end):
                signature = tuple(
                    (
                        int(
                            (instant.utcoffset() or timedelta(0)).total_seconds()
                        ),
                        int(instant.fold),
                    )
                    for instant in minute_candidates[minute]
                )
                if (
                    signature
                    and previous_signature is not None
                    and signature != previous_signature
                ):
                    transition_anchor_minutes.append(minute)
                previous_signature = signature
        variant_minutes = list(
            dict.fromkeys(
                [
                    anchor_minute,
                    *segment_anchor_minutes,
                    *transition_anchor_minutes,
                    *([ambiguous_minute] if ambiguous_minute is not None else []),
                ]
            )
        )
        calendars: list[dict[str, Any]] = []
        seen_instants: set[str] = set()
        for minute in variant_minutes:
            for instant in minute_candidates[minute]:
                calendar_variant = calendar_core.normalize_calendar(
                    instant.isoformat(),
                    timezone_name=timezone_name,
                    location=location,
                    longitude=longitude,
                    latitude=latitude,
                    coordinate_source=coordinate_source,
                    zi_hour_policy="midnight",
                    time_basis_policy="civil",
                )
                instant_utc = str(calendar_variant["instant_utc"])
                if instant_utc not in seen_instants:
                    calendars.append(calendar_variant)
                    seen_instants.add(instant_utc)
        zone = ZoneInfo(timezone_name)
        for boundary_instant in boundary_instants:
            localized = boundary_instant.astimezone(zone)
            boundary_minute = localized.hour * 60 + localized.minute
            if not any(start <= boundary_minute < end for start, end in segments):
                continue
            calendar_variant = calendar_core.normalize_calendar(
                boundary_instant.isoformat(),
                timezone_name=timezone_name,
                location=location,
                longitude=longitude,
                latitude=latitude,
                coordinate_source=coordinate_source,
                zi_hour_policy="midnight",
                time_basis_policy="civil",
            )
            instant_utc = str(calendar_variant["instant_utc"])
            if instant_utc not in seen_instants:
                calendars.append(calendar_variant)
                seen_instants.add(instant_utc)
        calendar = calendars[0]
        month_ganzhi = str(calendar["ganzhi"]["month"])
        month_ganzhi_variants = list(
            dict.fromkeys(str(item["ganzhi"]["month"]) for item in calendars)
        )
        path = _hour_path(day_branch, branch)
        common_constraint_reasons: list[str] = []
        if branch not in allowed:
            common_constraint_reasons.append("hour_branch_not_allowed")
        if branch in excluded:
            common_constraint_reasons.append("hour_branch_excluded")
        segment_status: dict[tuple[str, str], dict[str, Any]] = {}
        for start, end in segments:
            reasons = list(common_constraint_reasons)
            window_overlap = any(
                minute_candidates[minute]
                and _minute_in_windows(minute, minute_windows)
                for minute in range(start, end)
            )
            if not window_overlap:
                reasons.append("outside_time_windows")
            segment_status[(_format_minute(start), _format_minute(end))] = {
                "hard_constraint_eligible": not reasons,
                "constraint_reasons": reasons,
                "window_overlap": window_overlap,
            }
        constraint_reasons = list(common_constraint_reasons)
        if not any(
            item["window_overlap"] for item in segment_status.values()
        ):
            constraint_reasons.append("outside_time_windows")
        nonexistent_count = sum(
            not candidates for candidates in minute_candidates.values()
        )
        ambiguous_count = sum(
            len(candidates) > 1 for candidates in minute_candidates.values()
        )
        utc_offsets = sorted(
            {
                int((instant.utcoffset() or timedelta(0)).total_seconds())
                for candidates in minute_candidates.values()
                for instant in candidates
            }
        )
        calendar_variants = _variant_intervals(
            calendars, segments, minute_candidates
        )
        for variant in calendar_variants:
            status = segment_status[
                (variant["segment_start"], variant["segment_end_exclusive"])
            ]
            variant.update(copy.deepcopy(status))
            event_assessment = _official_event_rules_for_calendar(
                variant,
                event_profile,
                requested_actions,
                runtime_context,
            )
            variant["official_yiji"] = event_assessment["official_yiji"]
            variant["daily_shensha"] = event_assessment["daily_shensha"]
            variant["day_path"] = event_assessment["day_path"]
            variant["official_event_rules"] = event_assessment["rules"]
            variant_year = str(variant["ganzhi"]["year"])
            variant_month = str(variant["ganzhi"]["month"])
            variant_year_branch = variant_year[1]
            variant_month_branch = variant_month[1]
            variant["annual_gods"] = {
                "tai_sui_branch": variant_year_branch,
                "sui_po_branch": OPPOSITE_BRANCHES[variant_year_branch],
                "three_sha": _three_sha(variant_year_branch),
                "source_lineage": "xieji-xingli-official-v1",
            }
            variant["monthly_gods"] = {
                "month_build_branch": variant_month_branch,
                "month_break_branch": OPPOSITE_BRANCHES[variant_month_branch],
                "three_sha": _three_sha(variant_month_branch),
                "source_lineage": "xieji-xingli-official-v1",
            }
            variant["directional_facts"] = _directional_facts(
                variant_year, variant_month_branch, directional_context
            )
        civil_time_segments = []
        for start, end in segments:
            row = {
                "start": _format_minute(start),
                "end_exclusive": _format_minute(end),
            }
            row.update(copy.deepcopy(segment_status[(row["start"], row["end_exclusive"])]))
            civil_time_segments.append(row)
        result.append(
            {
                "index": index,
                "branch": branch,
                "representative_local_time": f"{hour:02d}:00",
                "calculation_anchor_local_time": _format_minute(anchor_minute),
                "civil_time_segments": civil_time_segments,
                "ganzhi": str(calendar["ganzhi"]["hour"]),
                "month_ganzhi": month_ganzhi,
                "month_ganzhi_variants": month_ganzhi_variants,
                "jianchu_variants": [
                    {
                        "month_ganzhi": value,
                        "value": _jianchu(value[1], day_branch),
                    }
                    for value in month_ganzhi_variants
                ],
                "calendar_digest": str(calendar["calendar_digest"]),
                "calendar_variants": calendar_variants,
                "timezone_resolution": {
                    "status": (
                        "contains_ambiguous_local_times"
                        if ambiguous_count
                        else "contains_nonexistent_local_times"
                        if nonexistent_count
                        else "stable"
                    ),
                    "valid_minute_count": len(valid_minutes),
                    "ambiguous_minute_count": ambiguous_count,
                    "nonexistent_minute_count": nonexistent_count,
                    "utc_offset_seconds": utc_offsets,
                },
                "jianchu": _jianchu(month_ganzhi[1], day_branch),
                "twelve_path_god": path["name"],
                "runtime_name": path["runtime_name"],
                "class": path["class"],
                "hard_constraint_eligible": not constraint_reasons,
                "constraint_reasons": constraint_reasons,
                "source_dependency_id": "selection.hour-facts.ganzhi-and-twelve-gods",
            }
        )
    return result


@lru_cache(maxsize=1)
def _donggong_rows() -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for line in DONGGONG_TABLE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| DG-D"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 10:
            raise RuntimeError("invalid Donggong structured table row")
        identifier, month, month_branch, day_label, line_anchor, summary, good, bad, risks, verified = cells
        jianchu = day_label[0]
        row = {
            "id": identifier,
            "month": month,
            "month_branch": month_branch,
            "day_label": day_label,
            "line_anchor": line_anchor,
            "summary": summary,
            "recommended_uses": good,
            "avoid_uses": bad,
            "risk_terms": risks,
            "verified_against_scan": verified.lower() == "true",
            "status": "comparison_only_unverified_against_scan",
        }
        rows[(month_branch, jianchu)] = row
    if len(rows) != 144:
        raise RuntimeError("Donggong structured table must contain 144 rows")
    return rows


def donggong_event_verdict(identifier: str, event_profile: str) -> str:
    contract = source_table()["donggong_event_verdicts"]
    profiles = contract["profiles"]
    if event_profile not in profiles:
        raise ValueError("unsupported Donggong event profile")
    known_ids = {row["id"] for row in _donggong_rows().values()}
    if identifier not in known_ids:
        raise ValueError("unknown Donggong row identifier")
    matches = [
        verdict
        for verdict in ("recommend", "avoid", "mixed_conditional")
        if identifier in profiles[event_profile][verdict]
    ]
    if len(matches) > 1:
        raise RuntimeError("Donggong event verdict categories overlap")
    return matches[0] if matches else str(contract["default"])


def folk_rule_hits(lunar_month: int, lunar_day: int, day_ganzhi: str) -> list[dict[str, Any]]:
    if len(day_ganzhi) != 2 or day_ganzhi[0] not in STEMS or day_ganzhi[1] not in BRANCHES:
        raise ValueError("day_ganzhi must be one stem-branch pair")
    hits: list[dict[str, Any]] = []
    if (lunar_month, lunar_day) in YANG_GONG_DATES:
        hits.append(
            {
                "id": "folk.yang-gong-thirteen",
                "status": "comparison_only",
                "source": "玉匣记",
            }
        )
    if lunar_day in MONTH_TABOO_DAYS:
        hits.append(
            {
                "id": "folk.month-taboo",
                "status": "comparison_only",
                "source": "玉匣记",
            }
        )
    taboo = (
        str(cnlunar_config.pengTatooList[STEMS.index(day_ganzhi[0])])
        + "；"
        + str(cnlunar_config.pengTatooList[10 + BRANCHES.index(day_ganzhi[1])])
    )
    hits.append(
        {
            "id": "folk.pengzu",
            "status": "comparison_only_not_general_elimination",
            "source": "玉匣记",
            "text": taboo,
        }
    )
    return hits


def _build_folk_comparison(
    *,
    lunar_month: int,
    lunar_day: int,
    day_ganzhi: str,
    month_branch: str,
    jianchu: str,
    event_profile: str,
    official_eligible: bool,
) -> dict[str, Any]:
    """Compare folk lineages against the final official candidate state."""

    hits = folk_rule_hits(lunar_month, lunar_day, day_ganzhi)
    avoid_hits = [row for row in hits if row["id"] != "folk.pengzu"]
    donggong = copy.deepcopy(
        _donggong_rows()[(month_branch, DONGGONG_JIANCHU_GLYPHS[jianchu])]
    )
    donggong_verdict = donggong_event_verdict(donggong["id"], event_profile)
    disagreement_sources: list[str] = []
    if official_eligible and avoid_hits:
        disagreement_sources.append("yuqia")
    donggong_conflicts = (
        official_eligible and donggong_verdict in {"avoid", "mixed_conditional"}
    ) or (
        not official_eligible
        and donggong_verdict in {"recommend", "mixed_conditional"}
    )
    if donggong_conflicts:
        disagreement_sources.append("donggong")
    return {
        "affects_official_rank": False,
        "yuqia_rule_hits": hits,
        "donggong_row": donggong,
        "donggong_verdict": donggong_verdict,
        "donggong_boundary": "frozen_row_profile_classification_v1",
        "disagreement": bool(disagreement_sources),
        "disagreement_sources": disagreement_sources,
        "official_assessment": "eligible" if official_eligible else "eliminated",
        "folk_assessment": {
            "yuqia": "comparison_avoid" if avoid_hits else "no_mechanical_avoid_hit",
            "donggong": donggong_verdict,
        },
    }


def _hard_date_reasons(civil: date, constraints: Mapping[str, Any]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    value = civil.isoformat()
    if value in set(constraints.get("excluded_dates") or ()):
        reasons.append({"code": "excluded_date", "field": "hard_constraints.excluded_dates", "value": value})
    allowed_weekdays = set(constraints.get("allowed_weekdays") or ())
    if allowed_weekdays and civil.isoweekday() not in allowed_weekdays:
        reasons.append({"code": "weekday_not_allowed", "field": "hard_constraints.allowed_weekdays", "value": civil.isoweekday()})
    if civil.isoweekday() in set(constraints.get("excluded_weekdays") or ()):
        reasons.append({"code": "weekday_excluded", "field": "hard_constraints.excluded_weekdays", "value": civil.isoweekday()})
    earliest = constraints.get("earliest_date")
    if earliest and value < earliest:
        reasons.append({"code": "before_earliest_date", "field": "hard_constraints.earliest_date", "value": value})
    latest = constraints.get("latest_date")
    if latest and value > latest:
        reasons.append({"code": "after_latest_date", "field": "hard_constraints.latest_date", "value": value})
    return reasons


def _participant_clashes(day_branch: str, participants: list[dict[str, str]]) -> list[dict[str, str]]:
    clashes: list[dict[str, str]] = []
    for participant in participants:
        for field in ("year_branch", "day_branch"):
            supplied = participant.get(field)
            if supplied and OPPOSITE_BRANCHES[supplied] == day_branch:
                clashes.append(
                    {
                        "participant_id": participant["id"],
                        "fact_field": field,
                        "participant_branch": supplied,
                        "candidate_day_branch": day_branch,
                        "relation": "exact_opposition",
                    }
                )
    return clashes


def _three_sha(branch: str) -> dict[str, str]:
    for trine, jie_sha, zai_sha, sui_sha, sector in THREE_SHA_BY_TRINE:
        if branch in trine:
            return {
                "trine": trine,
                "jie_sha_branch": jie_sha,
                "zai_sha_branch": zai_sha,
                "sui_sha_branch": sui_sha,
                "sector": sector,
            }
    raise ValueError("invalid branch for three-sha calculation")


def _directional_facts(
    year_ganzhi: str,
    month_branch: str,
    directional_context: Mapping[str, str] | None,
) -> dict[str, Any]:
    year_stem = year_ganzhi[0]
    year_branch = year_ganzhi[1]
    raw_site_branch = (
        directional_context.get("site_branch")
        if isinstance(directional_context, Mapping)
        else None
    )
    raw_site_mountain = (
        directional_context.get("site_mountain")
        if isinstance(directional_context, Mapping)
        else None
    )
    site_branch = str(raw_site_branch) if raw_site_branch else None
    site_mountain = str(raw_site_mountain) if raw_site_mountain else None
    formulas = source_table()["directional_formulas"]
    dajiangjun = str(formulas["dajiangjun_by_year_branch"][year_branch])
    jinshen = [
        str(item) for item in formulas["jinshen_qisha_by_year_stem"][year_stem]
    ]
    xunshan_luohou = str(
        formulas["xunshan_luohou_by_year_branch"][year_branch]
    )
    hits: list[dict[str, str]] = []
    if site_branch:
        annual_three_sha = _three_sha(year_branch)
        monthly_three_sha = _three_sha(month_branch)
        checks = (
            ("annual_tai_sui", year_branch),
            ("annual_sui_po", OPPOSITE_BRANCHES[year_branch]),
            ("annual_jie_sha", annual_three_sha["jie_sha_branch"]),
            ("annual_zai_sha", annual_three_sha["zai_sha_branch"]),
            ("annual_sui_sha", annual_three_sha["sui_sha_branch"]),
            ("monthly_build", month_branch),
            ("monthly_break", OPPOSITE_BRANCHES[month_branch]),
            ("monthly_jie_sha", monthly_three_sha["jie_sha_branch"]),
            ("monthly_zai_sha", monthly_three_sha["zai_sha_branch"]),
            ("monthly_sui_sha", monthly_three_sha["sui_sha_branch"]),
            ("annual_dajiangjun", dajiangjun),
            *(("annual_jinshen_qisha", branch) for branch in jinshen),
        )
        hits = [
            {"code": code, "site_branch": site_branch, "matched_branch": branch}
            for code, branch in checks
            if site_branch == branch
        ]
    return {
        "site_branch": site_branch,
        "site_mountain": site_mountain,
        "input_fields": [
            field
            for field, value in (
                ("site_branch", site_branch),
                ("site_mountain", site_mountain),
            )
            if value is not None
        ],
        "year_ganzhi": year_ganzhi,
        "dajiangjun_branch": dajiangjun,
        "jinshen_qisha_branches": jinshen,
        "xunshan_luohou_mountain": xunshan_luohou,
        "evaluated_hits": hits,
        "source_anchors": [
            "XR-03", "KR-09", "KR-10", "xieji-fulltext-L1699-L1700"
        ],
        "source_dependency_id": "selection.day-facts.jianchu-mansions-gods",
    }


def _event_specific_facts(
    event_profile: str,
    *,
    requested_actions: list[str] | tuple[str, ...],
    runtime: Lunar,
    yi_matches: list[str],
    ji_matches: list[str],
    universal_avoidance: bool,
    day_path: Mapping[str, Any],
    hours: list[dict[str, Any]],
    participant_hits: list[dict[str, str]],
    directional_facts: Mapping[str, Any],
    record_values: Mapping[str, Any],
    include_folk_comparison: bool,
) -> dict[str, dict[str, Any]]:
    contract = source_table()["event_profiles"][event_profile]
    definitions = source_table()["event_fact_definitions"]
    good_gods = _clean_unique(runtime.goodGodName)
    bad_gods = _clean_unique(runtime.badGodName)
    all_gods = set(good_gods) | set(bad_gods)
    jianchu = str(record_values["jianchu"]["value"])
    lunar = record_values["calendar"]["lunar_date"]
    day_ganzhi = str(record_values["calendar"]["ganzhi"]["day"])

    def evaluate(rule: Mapping[str, Any]) -> tuple[bool, Any]:
        kind = str(rule["kind"])
        if kind == "record":
            key = str(rule["record"])
            aliases = {
                "annual_three_sha": record_values["annual_gods"]["three_sha"],
                "monthly_three_sha": record_values["monthly_gods"]["three_sha"],
                "taisui_suipo": {
                    "tai_sui_branch": record_values["annual_gods"]["tai_sui_branch"],
                    "sui_po_branch": record_values["annual_gods"]["sui_po_branch"],
                },
            }
            value = aliases.get(key, record_values.get(key))
            return bool(value), copy.deepcopy(value)
        if kind in {"god_presence", "official_rejected_rule"}:
            names = [str(item) for item in rule.get("names") or ()]
            if not names and kind == "god_presence":
                return bool(all_gods), {
                    "matched_good_gods": good_gods,
                    "matched_bad_gods": bad_gods,
                }
            matched = [name for name in names if name in all_gods]
            value: dict[str, Any] = {
                "declared_names": names,
                "matched_good_gods": [name for name in names if name in good_gods],
                "matched_bad_gods": [name for name in names if name in bad_gods],
            }
            if kind == "official_rejected_rule":
                value["authority_status"] = "rejected_by_official_primary"
                value["observed_but_not_ranked"] = matched
                return False, value
            return bool(matched), value
        if kind == "mixed_official_and_rejected":
            official = [str(item) for item in rule.get("official_names") or ()]
            rejected = [str(item) for item in rule.get("rejected_names") or ()]
            official_matches = [name for name in official if name in all_gods]
            rejected_observed = [name for name in rejected if name in all_gods]
            return bool(official_matches), {
                "official_matches": official_matches,
                "officially_rejected_layer": rejected,
                "rejected_observed_but_not_ranked": rejected_observed,
            }
        if kind == "good_gods":
            return bool(good_gods), good_gods
        if kind == "bad_gods":
            return bool(bad_gods), bad_gods
        if kind == "hour_path":
            value = [
                {
                    "branch": row["branch"],
                    "path_god": row["twelve_path_god"],
                    "class": row["class"],
                    "eligible": row["hard_constraint_eligible"],
                }
                for row in hours
            ]
            return any(row["class"] == "huang" and row["eligible"] for row in value), value
        if kind == "event_yiji":
            value = {
                "yi_matches": list(yi_matches),
                "ji_matches": list(ji_matches),
                "universal_avoidance": universal_avoidance,
            }
            return bool(yi_matches or ji_matches or universal_avoidance), value
        if kind == "conflicts":
            value = {
                "yi_ji_overlap": sorted(set(runtime.goodThing) & set(runtime.badThing)),
                "universal_avoidance": universal_avoidance,
                "directional_hits": copy.deepcopy(directional_facts.get("evaluated_hits") or []),
                "participant_clashes": copy.deepcopy(participant_hits),
            }
            return bool(
                value["yi_ji_overlap"]
                or universal_avoidance
                or value["directional_hits"]
                or value["participant_clashes"]
            ), value
        if kind == "fixed_day_set":
            values = [str(item) for item in rule.get("day_ganzhi") or ()]
            return day_ganzhi in values, {
                "day_ganzhi": day_ganzhi,
                "matched": day_ganzhi in values,
                "authority": rule.get("authority"),
            }
        if kind == "lunar_zhoutang":
            positions = ("翁", "第", "灶", "妇", "厨", "夫", "姑", "堂")
            lunar_day = int(lunar["day"])
            index = (5 + lunar_day - 1) % 8 if runtime.lunarMonthLong else (3 - lunar_day + 1) % 8
            position = positions[index]
            return False, {
                "lunar_month_size": "large" if runtime.lunarMonthLong else "small",
                "lunar_day": lunar_day,
                "position": position,
                "calculated_favorable_in_rejected_method": position in {"第", "堂", "厨", "灶"},
                "authority_status": rule.get("authority"),
                "rank_effect": "none",
            }
        if kind == "participant_clashes":
            return bool(participant_hits), copy.deepcopy(participant_hits)
        if kind == "jianchu_membership":
            favorable = [str(item) for item in rule.get("favorable") or ()]
            return jianchu in favorable, {"jianchu": jianchu, "favorable": favorable}
        if kind == "direction_formula":
            formula = str(rule["formula"])
            key = {
                "dajiangjun": "dajiangjun_branch",
                "jinshen_qisha": "jinshen_qisha_branches",
                "xunshan_luohou": "xunshan_luohou_mountain",
            }[formula]
            value = copy.deepcopy(directional_facts[key])
            site_field = (
                "site_mountain"
                if formula == "xunshan_luohou"
                else "site_branch"
            )
            site = directional_facts.get(site_field)
            matched = site in value if isinstance(value, list) else site == value
            applicable_actions = [
                str(item) for item in rule.get("applicable_actions") or ()
            ]
            explicitly_exempt_actions = [
                str(item) for item in rule.get("explicitly_exempt_actions") or ()
            ]
            normalized_requested_actions = _clean_unique(requested_actions)
            applicable = (
                not applicable_actions
                or bool(set(normalized_requested_actions) & set(applicable_actions))
            ) and not bool(
                set(normalized_requested_actions) & set(explicitly_exempt_actions)
            )
            details = {
                "formula": formula,
                "value": value,
                "site_field": site_field,
                "site_value": site,
                "matched": matched,
            }
            if applicable_actions or explicitly_exempt_actions:
                details.update(
                    {
                        "applicable": applicable,
                        "applicable_actions": applicable_actions,
                        "explicitly_exempt_actions": explicitly_exempt_actions,
                        "requested_actions": normalized_requested_actions,
                    }
                )
            return bool(matched and applicable), details
        if kind == "directional_hits":
            hits = copy.deepcopy(directional_facts.get("evaluated_hits") or [])
            return bool(hits), {"site_branch": directional_facts.get("site_branch"), "hits": hits}
        if kind == "lunar_month_day_set":
            key = f"{abs(int(lunar['month']))}-{int(lunar['day'])}"
            values = [str(item) for item in rule.get("values") or ()]
            return key in values, {"lunar_month_day": key, "authority": rule.get("authority")}
        if kind == "lunar_day_set":
            values = [int(item) for item in rule.get("values") or ()]
            lunar_day = int(lunar["day"])
            return lunar_day in values, {"lunar_day": lunar_day, "authority": rule.get("authority")}
        if kind == "seasonal_branch_set":
            lunar_month = abs(int(lunar["month"]))
            seasons = rule.get("lunar_month_seasons") or {}
            season = next(
                (
                    str(name)
                    for name, months in seasons.items()
                    if lunar_month in [int(item) for item in months]
                ),
                "",
            )
            taboo_branch = str((rule.get("taboo_branches") or {}).get(season) or "")
            day_branch = day_ganzhi[1]
            matched = bool(taboo_branch and day_branch == taboo_branch)
            applicable_actions = [
                str(item) for item in rule.get("applicable_actions") or ()
            ]
            normalized_requested_actions = _clean_unique(requested_actions)
            applicable = not applicable_actions or bool(
                set(normalized_requested_actions) & set(applicable_actions)
            )
            return matched and applicable, {
                "lunar_month": lunar_month,
                "season": season,
                "day_branch": day_branch,
                "taboo_branch": taboo_branch,
                "matched": matched,
                "applicable": applicable,
                "applicable_actions": applicable_actions,
                "requested_actions": normalized_requested_actions,
                "authority": rule.get("authority"),
            }
        if kind == "composite":
            gods = [str(item) for item in rule.get("gods") or ()]
            jianchu_values = [str(item) for item in rule.get("jianchu") or ()]
            matched_gods = [name for name in gods if name in all_gods]
            active = jianchu in jianchu_values or bool(matched_gods)
            return active, {"jianchu": jianchu, "matched_gods": matched_gods}
        if kind == "renshen_location":
            medical = source_table()["folk_medical_tables"]
            return True, {
                "day_ganzhi": day_ganzhi,
                "stem_location": str(
                    medical["renshen_by_day_stem"][day_ganzhi[0]]
                ),
                "branch_location": str(
                    medical["renshen_by_day_branch"][day_ganzhi[1]]
                ),
                "hour_locations": [
                    {
                        "hour_branch": branch,
                        "location": str(
                            medical["renshen_by_hour_branch"][branch]
                        ),
                    }
                    for branch in BRANCHES
                ],
                "authority": "folk_comparison_only",
            }
        if kind == "day_ganzhi_set":
            values = [
                str(item)
                for item in source_table()["folk_medical_tables"][str(rule["table"])]
            ]
            return day_ganzhi in values, {
                "day_ganzhi": day_ganzhi,
                "values": values,
                "authority": "folk_comparison_only",
            }
        if kind == "folk_comparison":
            hits = folk_rule_hits(
                abs(int(lunar["month"])), int(lunar["day"]), day_ganzhi
            )
            applicable = [item for item in hits if item["id"] != "folk.pengzu"]
            return bool(applicable), {
                "enabled_in_output": include_folk_comparison,
                "rank_effect": "none",
                "hits": hits,
            }
        if kind == "medical_policy":
            return True, {"policy": "professional_medical_care_controls"}
        raise RuntimeError(f"unsupported Selection event fact kind: {kind}")

    result: dict[str, dict[str, Any]] = {}
    for field in contract["required_event_fact_fields"]:
        rule = definitions[field]
        active, value = evaluate(rule)
        result[field] = {
            "status": "calculated",
            "active": active,
            "value": value,
            "kind": str(rule["kind"]),
            "rank_effect": str(rule.get("rank_effect") or "informational"),
            "source_anchors": [str(item) for item in rule["source_anchors"]],
            "source_dependency_id": "selection.event-rules-and-lineage-conflicts",
        }
    return result


def _event_fact_rank_adjustments(
    event_facts: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Translate active declarative fact effects into explainable mechanics."""

    hard_reasons: list[dict[str, Any]] = []
    favorable_fields: list[str] = []
    for field, fact in event_facts.items():
        if fact.get("active") is not True or fact.get("evidence_applicable") is False:
            continue
        effect = str(fact.get("rank_effect") or "")
        if effect == "hard_elimination":
            hard_reasons.append(
                {
                    "code": "event_fact_hard_elimination",
                    "event_fact_field": str(field),
                    "source_anchors": [
                        str(item) for item in fact.get("source_anchors") or ()
                    ],
                    "rank_effect": effect,
                }
            )
        elif effect == "favorable_preference":
            favorable_fields.append(str(field))
    return hard_reasons, favorable_fields


def _active_source_rule_ids(
    event_facts: Mapping[str, Mapping[str, Any]],
    event_rules: Mapping[str, Any],
) -> list[str]:
    active = {
        "XR-01",
        "XR-03",
        "XR-04",
        "KR-02",
        "KR-05",
        "KR-08",
        "KR-14",
        "KR-15",
        "KR-01",
    }
    for fact in event_facts.values():
        if not isinstance(fact, Mapping) or fact.get("active") is not True:
            continue
        if fact.get("evidence_applicable") is False:
            continue
        for anchor in fact.get("source_anchors") or ():
            identifier = str(anchor)
            if identifier.startswith(("XR-", "KR-")):
                active.add(identifier)
    if (
        event_rules.get("yi_matches")
        or event_rules.get("ji_matches")
        or event_rules.get("universal_avoidance")
    ):
        active.update(("XR-08", "KR-17"))
    return sorted(active)


def build_day_record(
    civil_date: str,
    *,
    timezone_name: str,
    location: str,
    event_profile: str,
    requested_actions: list[str] | None = None,
    hard_constraints: Mapping[str, Any] | None = None,
    participant_facts: list[dict[str, str]] | None = None,
    requested_scopes: list[str] | None = None,
    directional_context: Mapping[str, str] | None = None,
    include_folk_comparison: bool = False,
    longitude: Any = None,
    latitude: Any = None,
    coordinate_source: Any = None,
    _runtime_context: RuntimeContext | None = None,
) -> dict[str, Any]:
    profiles = source_table()["event_profiles"]
    if event_profile not in profiles:
        raise ValueError("unsupported event profile")
    actions = _clean_unique(requested_actions or [])
    supported_actions = {
        str(item) for item in profiles[event_profile].get("official_terms") or ()
    }
    if any(item not in supported_actions for item in actions):
        raise ValueError("requested_actions contains an action outside event_profile")
    parsed_date = _parse_iso_date(civil_date, "civil_date")
    if parsed_date < date(1901, 1, 1) or parsed_date > date(2100, 12, 31):
        raise ValueError("civil date is outside the pinned runtime range")
    constraints = _normalize_hard_constraints(hard_constraints)
    participants = _normalize_participants(participant_facts)
    participant_scope = _participant_scope(event_profile, participants)
    if requested_scopes is not None and not isinstance(
        requested_scopes, (list, tuple)
    ):
        raise ValueError("requested_scopes must be a list")
    scopes = _clean_unique(requested_scopes or [])
    if sorted(set(scopes) - SUPPORTED_SCOPES):
        raise ValueError("unsupported Selection requested_scopes")
    direction = dict(directional_context) if directional_context else None
    if direction is not None and direction.get("site_branch") not in (None, "") and str(
        direction.get("site_branch")
    ) not in BRANCHES:
        raise ValueError("directional_context.site_branch must be a valid branch")
    if direction is not None and direction.get("site_mountain") not in (None, "") and str(
        direction.get("site_mountain")
    ) not in TWENTY_FOUR_MOUNTAINS:
        raise ValueError(
            "directional_context.site_mountain must be a valid twenty-four mountain"
        )
    if "directional_judgment" in scopes and (
        direction is None
        or not (direction.get("site_branch") or direction.get("site_mountain"))
    ):
        raise ValueError(
            "directional_context.site_branch or site_mountain is required for directional_judgment"
        )
    runtime_context = _runtime_context if _runtime_context is not None else {}
    noon_calendar = _calendar_for(
        civil_date,
        12,
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
    )
    day_start_calendar = _calendar_for(
        civil_date,
        0,
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
    )
    day_end_calendar = _calendar_for(
        civil_date,
        23,
        minute=59,
        second=59,
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
    )
    boundary_candidates = (
        noon_calendar["solar_terms"].get("previous_month_boundary_jie"),
        noon_calendar["solar_terms"].get("next_month_boundary_jie"),
    )
    month_boundary_jie = next(
        (
            copy.deepcopy(item)
            for item in boundary_candidates
            if isinstance(item, Mapping)
            and str(item.get("datetime") or "")[:10] == civil_date
        ),
        None,
    )
    boundary_instants: tuple[datetime, ...] = ()
    if month_boundary_jie:
        exact_boundary = datetime.fromisoformat(month_boundary_jie["datetime"])
        before_boundary = exact_boundary - timedelta(seconds=1)
        boundary_instants = tuple(
            item
            for item in (before_boundary, exact_boundary)
            if item.date() == parsed_date
        )
    local_noon = datetime.fromisoformat(f"{civil_date}T12:00:00")
    runtime = _aligned_runtime(local_noon, noon_calendar, runtime_context)
    ganzhi = noon_calendar["ganzhi"]
    year_branch = str(ganzhi["year"])[1]
    month_branch = str(ganzhi["month"])[1]
    day_branch = str(ganzhi["day"])[1]
    jianchu = _jianchu(month_branch, day_branch)
    day_path = _day_path(month_branch, day_branch)
    if runtime.today12DayOfficer != jianchu or runtime.today12DayGod != day_path["runtime_name"]:
        raise RuntimeError("aligned cnlunar day table differs from source formula")
    hours = _hour_facts(
        civil_date,
        timezone_name=timezone_name,
        location=location,
        day_branch=day_branch,
        event_profile=event_profile,
        requested_actions=actions,
        directional_context=direction,
        hard_constraints=constraints,
        boundary_instants=boundary_instants,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        runtime_context=runtime_context,
    )
    month_variants = list(
        dict.fromkeys(
            [
                str(day_start_calendar["ganzhi"]["month"]),
                *(item["month_ganzhi"] for item in hours),
                str(day_end_calendar["ganzhi"]["month"]),
            ]
        )
    )
    year_variants = list(
        dict.fromkeys(
            (
                str(day_start_calendar["ganzhi"]["year"]),
                str(noon_calendar["ganzhi"]["year"]),
                str(day_end_calendar["ganzhi"]["year"]),
            )
        )
    )
    day_event_assessment = _official_event_rules_for_calendar(
        noon_calendar,
        event_profile,
        actions,
        runtime_context,
    )
    official_yi = day_event_assessment["official_yiji"]["yi"]
    official_ji = day_event_assessment["official_yiji"]["ji"]
    event_rules = day_event_assessment["rules"]
    event_terms = tuple(event_rules["declared_actions"])
    yi_matches = list(event_rules["yi_matches"])
    ji_matches = list(event_rules["ji_matches"])
    universal_avoidance = bool(event_rules["universal_avoidance"])
    participant_hits = _participant_clashes(day_branch, participants)
    rejection_reasons = _hard_date_reasons(parsed_date, constraints)
    if constraints["participant_clash_is_hard"]:
        rejection_reasons.extend(
            {
                "code": "participant_branch_clash",
                "participant_id": row["participant_id"],
                "fact_field": row["fact_field"],
                "participant_branch": row["participant_branch"],
                "candidate_day_branch": day_branch,
            }
            for row in participant_hits
        )
    if not any(item["hard_constraint_eligible"] for item in hours):
        rejection_reasons.append(
            {
                "code": "no_allowed_hour",
                "field": "hard_constraints.hour_filters",
            }
        )
    directional_facts = _directional_facts(
        str(ganzhi["year"]), month_branch, direction
    )
    mechanical_rejection_reasons = copy.deepcopy(rejection_reasons)
    if universal_avoidance:
        rejection_reasons.append(
            {
                "code": "official_universal_avoidance",
                "profile": event_profile,
                "matched_action": UNIVERSAL_AVOIDANCE,
            }
        )
    if ji_matches:
        rejection_reasons.append(
            {
                "code": "official_event_avoidance",
                "profile": event_profile,
                "matched_actions": ji_matches,
            }
        )
    official_assessment = {
        "eligible": not rejection_reasons,
        "event_profile": event_profile,
        "yi_matches": yi_matches,
        "ji_matches": ji_matches,
        "day_path_class": day_path["class"],
        "good_god_count": len(runtime.goodGodName),
        "bad_god_count": len(runtime.badGodName),
        "rejection_reasons": copy.deepcopy(rejection_reasons),
    }
    record: dict[str, Any] = {
        "candidate_id": civil_date,
        "civil_date": civil_date,
        "weekday": parsed_date.isoweekday(),
        "scope_status": {
            "requested_scopes": scopes,
            "general_day_quality": True,
            "participant_specific": participant_scope["participant_specific"],
            "directional_judgment": "directional_judgment" in scopes,
            "directional_judgment_calculated": (
                "directional_judgment" in scopes and direction is not None
            ),
        },
        "calendar": {
            "lunar_date": copy.deepcopy(noon_calendar["lunar_date"]),
            "ganzhi": copy.deepcopy(ganzhi),
            "solar_terms": copy.deepcopy(noon_calendar["solar_terms"]),
            "calendar_digest": noon_calendar["calendar_digest"],
            "boundary_status": (
                "intra_day_jie_boundary" if len(month_variants) > 1 else "stable_month_branch"
            ),
            "month_ganzhi_variants": month_variants,
            "year_ganzhi_variants": year_variants,
            "month_boundary_jie": month_boundary_jie,
        },
        "jianchu": {
            "value": jianchu,
            "month_branch": month_branch,
            "day_branch": day_branch,
            "source_dependency_id": "selection.day-facts.jianchu-mansions-gods",
        },
        "mansion": {
            "name": str(runtime.today28Star),
            "short_name": str(runtime.today28Star)[0],
            "epoch_profile": "cnlunar-calibrated-daily-cycle-v1",
            "epoch_classification": "modern_engineering_calibration",
        },
        "day_path": day_path,
        "annual_gods": {
            "tai_sui_branch": year_branch,
            "sui_po_branch": OPPOSITE_BRANCHES[year_branch],
            "three_sha": _three_sha(year_branch),
            "source_lineage": "xieji-xingli-official-v1",
            "variants": [
                {
                    "year_ganzhi": value,
                    "tai_sui_branch": value[1],
                    "sui_po_branch": OPPOSITE_BRANCHES[value[1]],
                    "three_sha": _three_sha(value[1]),
                }
                for value in year_variants
            ],
        },
        "monthly_gods": {
            "month_build_branch": month_branch,
            "month_break_branch": OPPOSITE_BRANCHES[month_branch],
            "three_sha": _three_sha(month_branch),
            "source_lineage": "xieji-xingli-official-v1",
            "variants": [
                {
                    "month_ganzhi": value,
                    "month_build_branch": value[1],
                    "month_break_branch": OPPOSITE_BRANCHES[value[1]],
                    "three_sha": _three_sha(value[1]),
                }
                for value in month_variants
            ],
        },
        "daily_shensha": {
            "good_gods": _clean_unique(runtime.goodGodName),
            "bad_gods": _clean_unique(runtime.badGodName),
            "source_lineage": "xieji-xingli-official-v1",
        },
        "hour_facts": hours,
        "official_yiji": copy.deepcopy(day_event_assessment["official_yiji"]),
        "official_event_rules": copy.deepcopy(event_rules),
        "clash": {
            "day_branch": day_branch,
            "opposite_branch": OPPOSITE_BRANCHES[day_branch],
            "zodiac": ZODIACS[BRANCHES.index(OPPOSITE_BRANCHES[day_branch])],
            "runtime_text": str(runtime.chineseZodiacClash),
        },
        "participant_clashes": participant_hits,
        "participant_scope": participant_scope,
        "directional_facts": directional_facts,
        "eligibility": {"eligible": not rejection_reasons},
        "mechanical_rejection_reasons": mechanical_rejection_reasons,
        "rejection_reasons": rejection_reasons,
        "ranking_components": {
            "eligible": not rejection_reasons,
            "official_event_avoid_count": len(ji_matches),
            "official_event_recommend_count": len(yi_matches),
            "official_huang_day": day_path["class"] == "huang",
            "official_huang_hour": any(
                item["class"] == "huang" and item["hard_constraint_eligible"]
                for item in hours
            ),
            "participant_clash_count": len(participant_hits),
            "official_good_god_count": len(runtime.goodGodName),
            "official_bad_god_count": len(runtime.badGodName),
            "civil_date": civil_date,
        },
        "source_trace": [
            {"dependency_id": dependency, "profile": TABLE_PROFILE}
            for dependency in SOURCE_DEPENDENCIES
        ],
    }
    record["event_specific_facts"] = _event_specific_facts(
        event_profile,
        requested_actions=actions,
        runtime=runtime,
        yi_matches=yi_matches,
        ji_matches=ji_matches,
        universal_avoidance=universal_avoidance,
        day_path=day_path,
        hours=hours,
        participant_hits=participant_hits,
        directional_facts=directional_facts,
        record_values=record,
        include_folk_comparison=include_folk_comparison,
    )
    participant_fact = record["event_specific_facts"].get("participant_clashes")
    if isinstance(participant_fact, dict):
        participant_fact["evidence_applicable"] = participant_scope[
            "participant_specific"
        ]
        participant_fact["applicability_scope"] = participant_scope["status"]
    event_reasons, favorable_fields = _event_fact_rank_adjustments(
        record["event_specific_facts"]
    )
    record["rejection_reasons"].extend(event_reasons)
    record["eligibility"]["eligible"] = not record["rejection_reasons"]
    record["ranking_components"].update(
        {
            "eligible": not record["rejection_reasons"],
            "event_favorable_count": len(favorable_fields),
            "event_favorable_fields": favorable_fields,
        }
    )
    official_assessment.update(
        {
            "eligible": not record["rejection_reasons"],
            "rejection_reasons": copy.deepcopy(record["rejection_reasons"]),
            "event_fact_hard_eliminations": copy.deepcopy(event_reasons),
        }
    )
    record["official_assessment_digest"] = canonical_digest(official_assessment)
    if include_folk_comparison:
        lunar = noon_calendar["lunar_date"]
        record["folk_comparison"] = _build_folk_comparison(
            lunar_month=abs(int(lunar["month"])),
            lunar_day=int(lunar["day"]),
            day_ganzhi=str(ganzhi["day"]),
            month_branch=month_branch,
            jianchu=jianchu,
            event_profile=event_profile,
            official_eligible=bool(official_assessment["eligible"]),
        )
    return record


def _rank_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    components = candidate["ranking_components"]
    return (
        0 if components["eligible"] else 1,
        int(components["official_event_avoid_count"]),
        -int(components["official_event_recommend_count"]),
        -int(components["event_favorable_count"]),
        0 if components["official_huang_day"] else 1,
        0 if components["official_huang_hour"] else 1,
        int(components["participant_clash_count"]),
        str(components["civil_date"]),
    )


def _clock_seconds(value: str) -> float:
    if value == "24:00":
        return 86400.0
    parts = value.split(":")
    if len(parts) == 2:
        hour, minute = (int(item) for item in parts)
        second = 0.0
    elif len(parts) == 3:
        hour = int(parts[0])
        minute = int(parts[1])
        second = float(parts[2])
    else:
        raise ValueError("invalid civil clock value")
    return hour * 3600 + minute * 60 + second


def _format_clock_seconds(value: float) -> str:
    if value == 86400:
        return "24:00"
    whole = int(value)
    hour, remainder = divmod(whole, 3600)
    minute, second = divmod(remainder, 60)
    fraction = value - whole
    if second == 0 and fraction == 0:
        return f"{hour:02d}:{minute:02d}"
    rendered = f"{hour:02d}:{minute:02d}:{second:02d}"
    if fraction:
        rendered += f"{fraction:.6f}"[1:].rstrip("0")
    return rendered


def _variant_allowed_intervals(
    variant: Mapping[str, Any],
    windows: list[dict[str, str]],
) -> list[tuple[float, float]]:
    start = _clock_seconds(str(variant["civil_start"]))
    end = _clock_seconds(str(variant["civil_end_exclusive"]))
    if not windows:
        return [(start, end)]
    intersections: list[tuple[float, float]] = []
    for window in windows:
        window_start = _minutes(window["start"]) * 60
        window_end = _minutes(window["end"]) * 60
        intervals = (
            ((window_start, window_end),)
            if window_start < window_end
            else ((window_start, 86400), (0, window_end))
        )
        for left, right in intervals:
            overlap_start = max(start, left)
            overlap_end = min(end, right)
            if overlap_start < overlap_end:
                intersections.append((overlap_start, overlap_end))
    merged: list[tuple[float, float]] = []
    for left, right in sorted(set(intersections)):
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    return merged


def _effective_interval_identity(
    variant: Mapping[str, Any],
    start_seconds: float,
) -> tuple[str, str]:
    anchor = datetime.fromisoformat(str(variant["civil_datetime"]))
    local_midnight = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
    effective = local_midnight + timedelta(seconds=start_seconds)
    return effective.isoformat(), effective.astimezone(timezone.utc).isoformat()


def _date_time_candidates(
    candidates: list[dict[str, Any]],
    constraints: Mapping[str, Any],
    runtime_context: RuntimeContext | None = None,
) -> list[dict[str, Any]]:
    windows = list(constraints.get("time_windows") or ())
    result: list[dict[str, Any]] = []
    for day in candidates:
        for hour in day["hour_facts"]:
            for variant_index, variant in enumerate(hour["calendar_variants"]):
                event_rules = variant["official_event_rules"]
                variant_runtime = _aligned_runtime(
                    datetime.fromisoformat(str(variant["civil_datetime"])).replace(
                        tzinfo=None
                    ),
                    variant,
                    runtime_context,
                )
                variant_event_facts = _event_specific_facts(
                    str(event_rules["profile"]),
                    requested_actions=list(event_rules["requested_actions"]),
                    runtime=variant_runtime,
                    yi_matches=list(event_rules["yi_matches"]),
                    ji_matches=list(event_rules["ji_matches"]),
                    universal_avoidance=bool(event_rules["universal_avoidance"]),
                    day_path=variant["day_path"],
                    hours=day["hour_facts"],
                    participant_hits=day["participant_clashes"],
                    directional_facts=variant["directional_facts"],
                    record_values={
                        "calendar": {
                            "lunar_date": copy.deepcopy(variant["lunar_date"]),
                            "ganzhi": copy.deepcopy(variant["ganzhi"]),
                        },
                        "jianchu": {"value": variant["jianchu"]},
                        "annual_gods": variant["annual_gods"],
                        "monthly_gods": variant["monthly_gods"],
                        "day_path": variant["day_path"],
                    },
                    include_folk_comparison="folk_comparison" in day,
                )
                participant_fact = variant_event_facts.get("participant_clashes")
                if isinstance(participant_fact, dict):
                    participant_fact["evidence_applicable"] = day[
                        "participant_scope"
                    ]["participant_specific"]
                    participant_fact["applicability_scope"] = day[
                        "participant_scope"
                    ]["status"]
                variant_event_reasons, variant_favorable_fields = (
                    _event_fact_rank_adjustments(variant_event_facts)
                )
                variant_active_rule_ids = _active_source_rule_ids(
                    variant_event_facts, event_rules
                )
                allowed_intervals = _variant_allowed_intervals(variant, windows)
                emitted_intervals = allowed_intervals or [
                    (
                        _clock_seconds(str(variant["civil_start"])),
                        _clock_seconds(str(variant["civil_end_exclusive"])),
                    )
                ]
                for interval_index, (effective_start, effective_end) in enumerate(
                    emitted_intervals
                ):
                    civil_start = _format_clock_seconds(effective_start)
                    civil_end = _format_clock_seconds(effective_end)
                    time_reasons = list(hour.get("constraint_reasons") or ())
                    if not allowed_intervals:
                        time_reasons = list(
                            dict.fromkeys((*time_reasons, "outside_time_windows"))
                        )
                    reasons = copy.deepcopy(day["mechanical_rejection_reasons"])
                    reasons.extend(
                        {
                            "code": code,
                            "hour_branch": hour["branch"],
                            "civil_start": civil_start,
                            "civil_end_exclusive": civil_end,
                        }
                        for code in time_reasons
                    )
                    if event_rules["universal_avoidance"]:
                        reasons.append(
                            {
                                "code": "official_universal_avoidance",
                                "profile": event_rules["profile"],
                                "matched_action": UNIVERSAL_AVOIDANCE,
                            }
                        )
                    if event_rules["ji_matches"]:
                        reasons.append(
                            {
                                "code": "official_event_avoidance",
                                "profile": event_rules["profile"],
                                "matched_actions": copy.deepcopy(event_rules["ji_matches"]),
                            }
                        )
                    reasons.extend(copy.deepcopy(variant_event_reasons))
                    effective_civil, effective_utc = _effective_interval_identity(
                        variant, effective_start
                    )
                    identifier = canonical_digest(
                        {
                            "date": day["candidate_id"],
                            "branch": hour["branch"],
                            "variant": variant_index,
                            "interval": interval_index,
                            "instant_utc": effective_utc,
                            "start": civil_start,
                            "end": civil_end,
                        }
                    )[:16]
                    result.append(
                        {
                            "candidate_time_id": f"{day['candidate_id']}:{hour['branch']}:{identifier}",
                            "candidate_id": day["candidate_id"],
                            "date_candidate_id": day["candidate_id"],
                            "hour_branch": hour["branch"],
                            "civil_start": civil_start,
                            "civil_end_exclusive": civil_end,
                            "effective_allowed_intervals": [
                                {
                                    "start": _format_clock_seconds(left),
                                    "end_exclusive": _format_clock_seconds(right),
                                }
                                for left, right in allowed_intervals
                            ],
                            "calculation_variant_interval": {
                                "start": variant["civil_start"],
                                "end_exclusive": variant["civil_end_exclusive"],
                            },
                            "instant_utc": effective_utc,
                            "civil_datetime": effective_civil,
                            "utc_offset_seconds": variant["utc_offset_seconds"],
                            "fold": variant["fold"],
                            "lunar_date": copy.deepcopy(variant["lunar_date"]),
                            "ganzhi": copy.deepcopy(variant["ganzhi"]),
                            "jianchu": variant["jianchu"],
                            "twelve_path_god": hour["twelve_path_god"],
                            "class": hour["class"],
                            "calendar_digest": variant["calendar_digest"],
                            "official_yiji": copy.deepcopy(variant["official_yiji"]),
                            "daily_shensha": copy.deepcopy(variant["daily_shensha"]),
                            "day_path": copy.deepcopy(variant["day_path"]),
                            "annual_gods": copy.deepcopy(variant["annual_gods"]),
                            "monthly_gods": copy.deepcopy(variant["monthly_gods"]),
                            "directional_facts": copy.deepcopy(variant["directional_facts"]),
                            "official_event_rules": copy.deepcopy(event_rules),
                            "event_specific_facts": copy.deepcopy(variant_event_facts),
                            "active_source_rule_ids": variant_active_rule_ids,
                            "eligibility": {"eligible": not reasons},
                            "rejection_reasons": reasons,
                            "ranking_components": {
                                **copy.deepcopy(day["ranking_components"]),
                                "eligible": not reasons,
                                "official_event_avoid_count": len(event_rules["ji_matches"])
                                + int(bool(event_rules["universal_avoidance"])),
                                "official_event_recommend_count": len(event_rules["yi_matches"]),
                                "event_favorable_count": len(
                                    variant_favorable_fields
                                ),
                                "event_favorable_fields": copy.deepcopy(
                                    variant_favorable_fields
                                ),
                                "official_huang_day": variant["day_path"]["class"] == "huang",
                                "official_huang_hour": hour["class"] == "huang",
                                "civil_start": civil_start,
                                "fold": variant["fold"],
                            },
                            "source_dependency_id": "selection.hour-facts.ganzhi-and-twelve-gods",
                        }
                    )
    return result


def _rank_time_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    components = candidate["ranking_components"]
    return (
        0 if components["eligible"] else 1,
        int(components["official_event_avoid_count"]),
        -int(components["official_event_recommend_count"]),
        -int(components["event_favorable_count"]),
        0 if components["official_huang_day"] else 1,
        0 if components["official_huang_hour"] else 1,
        int(components["participant_clash_count"]),
        str(components["civil_date"]),
        _clock_seconds(str(components["civil_start"])),
        int(components["fold"]),
    )


def _time_candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    rules = candidate["official_event_rules"]
    return {
        "candidate_time_id": candidate["candidate_time_id"],
        "candidate_id": candidate["candidate_id"],
        "hour_branch": candidate["hour_branch"],
        "civil_start": candidate["civil_start"],
        "civil_end_exclusive": candidate["civil_end_exclusive"],
        "effective_allowed_intervals": copy.deepcopy(
            candidate["effective_allowed_intervals"]
        ),
        "instant_utc": candidate["instant_utc"],
        "fold": candidate["fold"],
        "ganzhi": copy.deepcopy(candidate["ganzhi"]),
        "jianchu": candidate["jianchu"],
        "eligibility": copy.deepcopy(candidate["eligibility"]),
        "rejection_reasons": copy.deepcopy(candidate["rejection_reasons"]),
        "ranking_components": copy.deepcopy(candidate["ranking_components"]),
        "official_event_rules": {
            "profile": rules["profile"],
            "requested_actions": list(rules["requested_actions"]),
            "action_assessments": copy.deepcopy(rules["action_assessments"]),
            "yi_matches": list(rules["yi_matches"]),
            "ji_matches": list(rules["ji_matches"]),
            "universal_avoidance": bool(rules["universal_avoidance"]),
            "assessment_digest": rules["assessment_digest"],
        },
        "active_source_rule_ids": list(candidate["active_source_rule_ids"]),
    }


def _date_candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "civil_date": candidate["civil_date"],
        "best_candidate_time_id": candidate["best_date_time_basis"][
            "candidate_time_id"
        ],
        "eligibility": copy.deepcopy(candidate["eligibility"]),
        "rejection_reasons": copy.deepcopy(candidate["rejection_reasons"]),
        "ranking_components": copy.deepcopy(candidate["ranking_components"]),
        "active_source_rule_ids": list(candidate["active_source_rule_ids"]),
    }


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build the same stable paths used by the Runtime fact index."""

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


def _fact_leaves_at_suffixes(
    value: Any,
    path_suffixes: tuple[str, ...],
) -> Iterator[tuple[str, Any]]:
    """Index only subtrees addressable by the supplied predicates.

    The search visits the fact containers once, follows each JSON-pointer-like
    suffix exactly, and iteratively collects the matched subtree. Its yielded
    paths and values are therefore identical to the relevant subset of a
    complete Runtime fact index without paying for recursion or irrelevant
    leaves.
    """

    suffixes_by_first_token: dict[str, list[tuple[str, ...]]] = {}
    for suffix in path_suffixes:
        segments = tuple(item for item in suffix.split("/") if item)
        if not segments:
            yield from _fact_leaves(value)
            return
        suffixes_by_first_token.setdefault(segments[0], []).append(segments[1:])

    relevant: dict[str, Any] = {}

    def token_for(key: Any) -> str:
        rendered = str(key)
        return (
            _escape_fact_token(rendered)
            if "/" in rendered or "~" in rendered
            else rendered
        )

    def collect(current: Any, path: str) -> None:
        stack: list[tuple[str, Any]] = [(path, current)]
        while stack:
            current_path, current_value = stack.pop()
            if isinstance(current_value, Mapping) and current_value:
                children = [
                    (f"{current_path}/{token_for(key)}", child)
                    for key in sorted(current_value, key=str)
                    for child in (current_value[key],)
                ]
                stack.extend(reversed(children))
                continue
            if isinstance(current_value, (list, tuple)) and current_value:
                stack.extend(
                    (f"{current_path}/{index}", child)
                    for index, child in reversed(tuple(enumerate(current_value)))
                )
                continue
            relevant.setdefault(current_path or "/", current_value)

    def follow(
        current: Any,
        path: str,
        remaining: tuple[str, ...],
    ) -> None:
        current_value = current
        current_path = path
        for expected in remaining:
            if not isinstance(current_value, Mapping):
                return
            match = next(
                (
                    (key, child)
                    for key, child in current_value.items()
                    if token_for(key) == expected
                ),
                None,
            )
            if match is None:
                return
            key, current_value = match
            current_path = f"{current_path}/{token_for(key)}"
        collect(current_value, current_path)

    stack: list[tuple[str, Any]] = [("", value)]
    while stack:
        path, current = stack.pop()
        if isinstance(current, Mapping):
            children: list[tuple[str, Any]] = []
            for key in sorted(current, key=str):
                child = current[key]
                token = token_for(key)
                child_path = f"{path}/{token}"
                for remaining in suffixes_by_first_token.get(token, ()):
                    follow(child, child_path, remaining)
                if isinstance(child, Mapping) or (
                    isinstance(child, (list, tuple))
                    and any(
                        isinstance(item, (Mapping, list, tuple))
                        for item in child
                    )
                ):
                    children.append((child_path, child))
            stack.extend(reversed(children))
        elif isinstance(current, (list, tuple)):
            stack.extend(
                (f"{path}/{index}", child)
                for index, child in reversed(tuple(enumerate(current)))
                if isinstance(child, (Mapping, list, tuple))
            )

    yield from relevant.items()


def _source_conditioned_patterns(
    facts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose verified selection predicates without making a day verdict."""

    indexed = {"chart_facts": dict(facts)}
    active_rules = tuple(
        rule
        for rule in evidence_rules.production_evidence_rules()
        if rule.system == "selection" and rule.runtime_active
    )
    predicate_suffixes = tuple(
        dict.fromkeys(
            predicate.path_suffix
            for rule in active_rules
            for predicate in (
                *rule.required_fact_predicates,
                *rule.excluded_fact_predicates,
            )
        )
    )
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.selection.v1",
            provider_version=ADAPTER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves_at_suffixes(indexed, predicate_suffixes)
    )
    matches: list[dict[str, Any]] = []
    for rule in active_rules:
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
                "source_dependency_id": "selection.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def fact_digest(facts: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(facts))
    payload.pop("fact_digest", None)
    payload.pop("validation", None)
    return canonical_digest(payload)


def build_fact_layer(
    spec: Mapping[str, Any],
    *,
    timezone_name: str,
    location: str,
    longitude: Any = None,
    latitude: Any = None,
    coordinate_source: Any = None,
) -> dict[str, Any]:
    if not str(timezone_name or "").strip() or not str(location or "").strip():
        raise ValueError("Selection requires timezone and location")
    normalized = normalize_spec(spec)
    start = date.fromisoformat(normalized["date_range"]["start"])
    end = date.fromisoformat(normalized["date_range"]["end"])
    candidates: list[dict[str, Any]] = []
    runtime_context: RuntimeContext = {}
    current = start
    while current <= end:
        candidates.append(
            build_day_record(
                current.isoformat(),
                timezone_name=str(timezone_name),
                location=str(location),
                event_profile=normalized["event_profile"],
                requested_actions=normalized["requested_actions"],
                hard_constraints=normalized["hard_constraints"],
                participant_facts=normalized["participant_facts"],
                requested_scopes=normalized["requested_scopes"],
                directional_context=normalized["directional_context"],
                include_folk_comparison=normalized["include_folk_comparison"],
                longitude=longitude,
                latitude=latitude,
                coordinate_source=coordinate_source,
                _runtime_context=runtime_context,
            )
        )
        current += timedelta(days=1)
    date_times = _date_time_candidates(
        candidates,
        normalized["hard_constraints"],
        runtime_context,
    )
    ranked_date_times = sorted(date_times, key=_rank_time_key)
    ordered_ids = list(
        dict.fromkeys(row["candidate_id"] for row in ranked_date_times)
    )
    eligible_date_time_ids = [
        row["candidate_time_id"]
        for row in ranked_date_times
        if row["eligibility"]["eligible"]
    ]
    eligible_ids = list(
        dict.fromkeys(
            row["candidate_id"]
            for row in ranked_date_times
            if row["eligibility"]["eligible"]
        )
    )
    eligible_id_set = set(eligible_ids)
    candidate_by_id = {row["candidate_id"]: row for row in candidates}
    best_time_by_date: dict[str, dict[str, Any]] = {}
    for item in ranked_date_times:
        best_time_by_date.setdefault(str(item["candidate_id"]), item)
    for row in candidates:
        best_time = best_time_by_date[row["candidate_id"]]
        row["representative_assessment"] = {
            "civil_time": "12:00",
            "calendar_digest": row["calendar"]["calendar_digest"],
            "ganzhi": copy.deepcopy(row["calendar"]["ganzhi"]),
            "jianchu": row["jianchu"]["value"],
            "official_assessment_digest": row["official_event_rules"][
                "assessment_digest"
            ],
            "yi_matches": list(row["official_event_rules"]["yi_matches"]),
            "ji_matches": list(row["official_event_rules"]["ji_matches"]),
            "eligibility": copy.deepcopy(row["eligibility"]),
            "rejection_reasons": copy.deepcopy(row["rejection_reasons"]),
            "ranking_components": copy.deepcopy(row["ranking_components"]),
        }
        row["best_date_time_basis"] = _time_candidate_summary(best_time)
        row["calendar"]["lunar_date"] = copy.deepcopy(best_time["lunar_date"])
        row["calendar"]["ganzhi"] = copy.deepcopy(best_time["ganzhi"])
        row["calendar"]["calendar_digest"] = best_time["calendar_digest"]
        row["calendar"]["ranking_basis_candidate_time_id"] = best_time[
            "candidate_time_id"
        ]
        row["jianchu"] = {
            "value": best_time["jianchu"],
            "month_branch": str(best_time["ganzhi"]["month"])[1],
            "day_branch": str(best_time["ganzhi"]["day"])[1],
            "source_dependency_id": "selection.day-facts.jianchu-mansions-gods",
        }
        row["day_path"] = copy.deepcopy(best_time["day_path"])
        row["annual_gods"] = {
            **copy.deepcopy(best_time["annual_gods"]),
            "variants": copy.deepcopy(row["annual_gods"].get("variants") or []),
        }
        row["monthly_gods"] = {
            **copy.deepcopy(best_time["monthly_gods"]),
            "variants": copy.deepcopy(row["monthly_gods"].get("variants") or []),
        }
        row["daily_shensha"] = copy.deepcopy(best_time["daily_shensha"])
        row["official_yiji"] = copy.deepcopy(best_time["official_yiji"])
        row["official_event_rules"] = copy.deepcopy(best_time["official_event_rules"])
        row["event_specific_facts"] = copy.deepcopy(best_time["event_specific_facts"])
        row["directional_facts"] = copy.deepcopy(best_time["directional_facts"])
        if normalized["include_folk_comparison"]:
            final_lunar = row["calendar"]["lunar_date"]
            row["folk_comparison"] = _build_folk_comparison(
                lunar_month=abs(int(final_lunar["month"])),
                lunar_day=int(final_lunar["day"]),
                day_ganzhi=str(row["calendar"]["ganzhi"]["day"]),
                month_branch=str(row["calendar"]["ganzhi"]["month"])[1],
                jianchu=str(row["jianchu"]["value"]),
                event_profile=str(normalized["event_profile"]),
                official_eligible=bool(best_time["eligibility"]["eligible"]),
            )
        active_rule_ids = set(best_time["active_source_rule_ids"])
        if normalized["include_folk_comparison"]:
            active_rule_ids.update(("DR-01", "DR-02", "DR-03", "DR-07", "DR-08", "JR-04"))
            comparison = row.get("folk_comparison") or {}
            if comparison.get("disagreement") is True:
                active_rule_ids.add("DR-09")
            folk_hits = {
                str(item.get("id"))
                for item in comparison.get("yuqia_rule_hits") or ()
                if isinstance(item, Mapping)
            }
            for folk_id, rule_id in {
                "folk.pengzu": "JR-05",
                "folk.yang-gong-thirteen": "JR-06",
                "folk.month-taboo": "JR-07",
                "folk.shi-eda-bai": "JR-08",
                "folk.fuduan": "JR-09",
            }.items():
                if folk_id in folk_hits:
                    active_rule_ids.add(rule_id)
            if folk_hits:
                active_rule_ids.add("JR-20")
            event_facts = row["event_specific_facts"]
            if event_facts.get("renshen_location", {}).get("active") is True:
                active_rule_ids.add("JR-11")
            if event_facts.get("visit_sick_taboo_days", {}).get("active") is True:
                active_rule_ids.add("JR-12")
            if event_facts.get("jinshen_qisha", {}).get("active") is True:
                active_rule_ids.add("DR-05")
        row["active_source_rule_ids"] = sorted(active_rule_ids)
        row["eligibility"] = {
            "eligible": bool(best_time["eligibility"]["eligible"]),
            "basis": "best_exact_date_time_candidate",
            "candidate_time_id": best_time["candidate_time_id"],
        }
        row["ranking_components"] = {
            **copy.deepcopy(best_time["ranking_components"]),
            "basis_candidate_time_id": best_time["candidate_time_id"],
        }
        row["rejection_reasons"] = copy.deepcopy(best_time["rejection_reasons"])
        row["official_assessment_digest"] = best_time["official_event_rules"][
            "assessment_digest"
        ]
        compact_variant_keys = {
            "civil_datetime",
            "instant_utc",
            "utc_offset_seconds",
            "fold",
            "lunar_date",
            "ganzhi",
            "calendar_digest",
            "civil_start",
            "civil_end_exclusive",
            "segment_start",
            "segment_end_exclusive",
            "jianchu",
            "hard_constraint_eligible",
            "constraint_reasons",
            "window_overlap",
        }
        for hour in row["hour_facts"]:
            hour["calendar_variants"] = [
                {
                    key: copy.deepcopy(value)
                    for key, value in variant.items()
                    if key in compact_variant_keys
                }
                for variant in hour["calendar_variants"]
            ]
    ranked = [candidate_by_id[identifier] for identifier in ordered_ids]
    eliminations = [
        {
            "candidate_id": row["candidate_id"],
            "rejection_reasons": copy.deepcopy(row["rejection_reasons"]),
        }
        for row in candidates
        if row["candidate_id"] not in eligible_id_set
    ]
    output = {
        "event_profile": normalized["event_profile"],
        "calendar_candidates": candidates,
        "date_time_candidates": date_times,
        "eligible_candidates": [
            _date_candidate_summary(candidate_by_id[identifier])
            for identifier in eligible_ids
        ],
        "eligible_date_time_candidates": [
            _time_candidate_summary(row)
            for row in ranked_date_times
            if row["eligibility"]["eligible"]
        ],
        "eliminations": eliminations,
        "no_valid_candidate": not eligible_date_time_ids,
        "ranking": {
            "method": "explainable_lexicographic_v1",
            "opaque_numeric_score": False,
            "component_order": list(source_table()["ranking"]["component_order"]),
            "ordered_candidate_ids": ordered_ids,
            "eligible_candidate_ids": eligible_ids,
            "ordered_date_time_candidate_ids": [
                row["candidate_time_id"] for row in ranked_date_times
            ],
            "eligible_date_time_candidate_ids": eligible_date_time_ids,
            "folk_affects_rank": False,
        },
        "lineage_policy": {
            "official": "xieji-xingli-official-v1",
            "folk": "donggong-yuqia-folk-v1",
            "official_priority": "primary",
            "folk_priority": "comparison_only",
            "preserve_disagreement": True,
            "merge_verdicts": False,
        },
        "source_trace": [
            {"dependency_id": dependency, "profile": TABLE_PROFILE}
            for dependency in SOURCE_DEPENDENCIES
        ],
    }
    output["source_conditioned_patterns"] = _source_conditioned_patterns(
        {"fact_layer_status": FACT_LAYER_STATUS, "output": output}
    )
    facts: dict[str, Any] = {
        "schema_version": "mingli-selection-fact-layer-v1",
        "system": "selection",
        "fact_layer_status": FACT_LAYER_STATUS,
        "fact_layer_scope": FACT_LAYER_SCOPE,
        "adapter": {
            "name": ADAPTER_NAME,
            "version": ADAPTER_VERSION,
            "rule_profile": TABLE_PROFILE,
            "license_status": "runtime_and_sources_declared",
            "dependency": {
                "name": "cnlunar",
                "version": "0.2.4",
                "license": "MIT",
            },
            "generated_at": "deterministic-selection-identity",
        },
        "input": {
            "selection_spec": normalized,
            "timezone": str(timezone_name),
            "location": str(location),
            "longitude": longitude,
            "latitude": latitude,
            "coordinate_source": coordinate_source,
            "input_digest": canonical_digest(
                {
                    "selection_spec": normalized,
                    "timezone": str(timezone_name),
                    "location": str(location),
                    "longitude": longitude,
                    "latitude": latitude,
                    "coordinate_source": coordinate_source,
                }
            ),
        },
        "calendar_normalization": {
            "status": "calculated",
            "timezone": str(timezone_name),
            "location": str(location),
            "date_range": copy.deepcopy(normalized["date_range"]),
            "calendar_digests": [
                row["calendar"]["calendar_digest"] for row in candidates
            ],
            "calendar_profile": calendar_core.ALGORITHM_VERSION,
        },
        "output": output,
        "warnings": [
            {
                "code": "traditional_reference_not_event_guarantee",
                "status": "safety_boundary",
            },
            *(
                [
                    {
                        "code": "professional_medical_care_controls",
                        "status": "safety_boundary",
                    }
                ]
                if normalized["event_profile"] == "medical"
                else []
            ),
        ],
    }
    # This freshly built payload does not yet contain either excluded digest
    # field. Avoid a full defensive deepcopy here; ``fact_digest`` keeps that
    # behavior for validating or re-signing caller-owned payloads.
    facts["fact_digest"] = canonical_digest(facts)
    facts["validation"] = {
        "ok": True,
        "validator": "mingli-master.selection.validate_fact_layer",
    }
    return facts


def validate_fact_layer(facts: Mapping[str, Any]) -> dict[str, Any]:
    codes: list[str] = []
    if not isinstance(facts, Mapping):
        return {"ok": False, "codes": ["selection_payload_not_object"]}
    if facts.get("schema_version") != "mingli-selection-fact-layer-v1":
        codes.append("selection_schema_mismatch")
    if facts.get("system") != "selection" or facts.get("fact_layer_status") != FACT_LAYER_STATUS:
        codes.append("selection_status_mismatch")
    adapter = facts.get("adapter") if isinstance(facts.get("adapter"), Mapping) else {}
    if adapter.get("name") != ADAPTER_NAME or adapter.get("version") != ADAPTER_VERSION:
        codes.append("selection_adapter_identity_mismatch")
    profile = yaml.safe_load(FACT_PROFILE_PATH.read_text(encoding="utf-8"))
    required = profile.get("base_required_fields") or {}
    schema_scopes: tuple[tuple[str, Mapping[str, Any]], ...] = (
        ("adapter", adapter),
        (
            "input",
            facts.get("input") if isinstance(facts.get("input"), Mapping) else {},
        ),
        (
            "calendar_normalization",
            facts.get("calendar_normalization")
            if isinstance(facts.get("calendar_normalization"), Mapping)
            else {},
        ),
    )
    for scope, value in schema_scopes:
        for field in required.get(scope) or ():
            if field not in value:
                codes.append(f"selection_schema_missing:{scope}.{field}")
    output = facts.get("output") if isinstance(facts.get("output"), Mapping) else {}
    for scope, rows in (
        ("candidate_record", output.get("calendar_candidates")),
        ("date_time_candidate_record", output.get("date_time_candidates")),
    ):
        if not isinstance(rows, list) or not rows:
            codes.append(f"selection_schema_missing:{scope}")
            continue
        for field in required.get(scope) or ():
            if any(not isinstance(row, Mapping) or field not in row for row in rows):
                codes.append(f"selection_schema_missing:{scope}.{field}")
    if facts.get("fact_digest") != fact_digest(facts):
        codes.append("selection_fact_digest_mismatch")
    source_input = facts.get("input") if isinstance(facts.get("input"), Mapping) else {}
    try:
        rebuilt = build_fact_layer(
            source_input["selection_spec"],
            timezone_name=str(source_input["timezone"]),
            location=str(source_input["location"]),
            longitude=source_input.get("longitude"),
            latitude=source_input.get("latitude"),
            coordinate_source=source_input.get("coordinate_source"),
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        codes.append("selection_input_rebuild_failed")
    else:
        if facts.get("calendar_normalization") != rebuilt["calendar_normalization"]:
            codes.append("selection_calendar_facts_mismatch")
        if facts.get("output") != rebuilt["output"]:
            codes.append("selection_candidate_facts_mismatch")
        if facts.get("warnings") != rebuilt["warnings"]:
            codes.append("selection_warning_contract_mismatch")
    return {"ok": not codes, "codes": list(dict.fromkeys(codes))}


__all__ = [
    "ADAPTER_NAME",
    "ADAPTER_VERSION",
    "BRANCHES",
    "FACT_LAYER_STATUS",
    "OPPOSITE_BRANCHES",
    "SOURCE_DEPENDENCIES",
    "TABLE_PROFILE",
    "build_day_record",
    "build_fact_layer",
    "fact_digest",
    "folk_rule_hits",
    "normalize_spec",
    "source_table",
    "validate_fact_layer",
]
