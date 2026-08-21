"""One deterministic calendar normalization service for all timed providers."""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import math
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEMA_VERSION = "mingli-calendar-normalization-v2"
ENGINE_VERSION = "2.0.7"
ALGORITHM_VERSION = "sxtwl-2.0.7/exact-jie-boundary-v1.2"
CONVENTION_ID = "east-asian-civil-jieqi-v1"
CONVENTION_VERSION = "1.0.2"
ASTRONOMY_ENGINE_VERSION = "2.1.19"
EOT_ALGORITHM_ID = "astronomy-engine-apparent-solar-eot-v1"
EOT_ALGORITHM_VERSION = f"astronomy-engine-{ASTRONOMY_ENGINE_VERSION}"
EOT_ALGORITHM_SOURCE = (
    "astronomy-engine apparent solar hour angle; "
    "equation_of_time = apparent_solar_time - mean_solar_time"
)
EOT_SUPPORTED_RANGE = "1900-01-01..2100-12-31"
EOT_UNCERTAINTY_SECONDS = 30
EOT_MIN_YEAR = 1900
EOT_MAX_YEAR = 2100
DOUBLE_HOUR_BOUNDARY_HOURS = (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
JIEQI_NAMES = (
    "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明",
    "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋",
    "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
)
MONTH_BOUNDARY_JIE = frozenset({1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23})
ZI_HOUR_POLICIES = frozenset({"midnight", "late-zi-next-day"})
TIME_BASIS_POLICIES = frozenset({
    "civil",
    "longitude_mean_solar-v1",
    "local_apparent_solar-v1",
})
ENGINE_TIMEZONE = timezone(timedelta(hours=8), name="sxtwl-UTC+08")


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def calendar_digest(payload: Mapping[str, Any]) -> str:
    """Recalculate a normalized calendar digest, excluding digest aliases."""

    identity = copy.deepcopy(dict(payload))
    identity.pop("calendar_digest", None)
    identity.pop("digest", None)
    return _digest(identity)


def validate_calendar_digest(payload: Mapping[str, Any]) -> str:
    supplied = str(payload.get("calendar_digest") or payload.get("digest") or "")
    actual = calendar_digest(payload)
    if not supplied or supplied != actual:
        raise ValueError("calendar digest does not match normalized calendar facts")
    return actual


@lru_cache(maxsize=1)
def load_sxtwl() -> Any:
    try:
        import sxtwl  # type: ignore
    except Exception as exc:  # pragma: no cover - platform-specific import failure
        raise RuntimeError(
            f"sxtwl missing: {exc}. Install the pinned requirements in the "
            "current interpreter or configure MINGLI_PYTHON."
        ) from exc
    actual = importlib.metadata.version("sxtwl")
    if actual != ENGINE_VERSION:
        raise RuntimeError(
            f"sxtwl version mismatch: expected {ENGINE_VERSION}, got {actual}"
        )
    return sxtwl


@lru_cache(maxsize=1)
def load_astronomy() -> Any:
    try:
        import astronomy  # type: ignore
    except Exception as exc:  # pragma: no cover - platform-specific import failure
        raise RuntimeError(
            f"astronomy-engine missing: {exc}. Install the pinned "
            "requirements in the current interpreter or configure MINGLI_PYTHON."
        ) from exc
    actual = importlib.metadata.version("astronomy-engine")
    if actual != ASTRONOMY_ENGINE_VERSION:
        raise RuntimeError(
            f"astronomy-engine version mismatch: expected "
            f"{ASTRONOMY_ENGINE_VERSION}, got {actual}"
        )
    return astronomy


def equation_of_time_seconds(instant_utc: datetime) -> int:
    """Equation of time = apparent solar time - mean solar time, in seconds.

    Composed from astronomy-engine's apparent solar hour angle at Greenwich,
    which embeds aberration, nutation and delta-T. The quantity is independent
    of observer longitude: at any instant the local apparent solar time and
    local mean solar time differ by exactly this value, so a Greenwich observer
    is sufficient and keeps the oracle separable from the production path.
    """

    astronomy = load_astronomy()
    if not EOT_MIN_YEAR <= instant_utc.year <= EOT_MAX_YEAR:
        raise ValueError(
            f"equation of time is unsupported outside "
            f"{EOT_MIN_YEAR}..{EOT_MAX_YEAR}: {instant_utc.year}"
        )
    time = astronomy.Time.Make(
        instant_utc.year,
        instant_utc.month,
        instant_utc.day,
        instant_utc.hour,
        instant_utc.minute,
        instant_utc.second,
    )
    observer = astronomy.Observer(0.0, 0.0, 0.0)
    hour_angle = float(astronomy.HourAngle(astronomy.Body.Sun, time, observer))
    apparent_solar_hours = (hour_angle + 12.0) % 24.0
    mean_solar_hours = (
        instant_utc.hour
        + instant_utc.minute / 60.0
        + instant_utc.second / 3600.0
        + instant_utc.microsecond / 3_600_000_000.0
    ) % 24.0
    eot_hours = (apparent_solar_hours - mean_solar_hours + 12.0) % 24.0 - 12.0
    return int(round(eot_hours * 3600.0))


def _hour_branch_index(hour: int) -> int:
    """Map a wall-clock hour to its Chinese double-hour branch index (0=子)."""

    return ((hour + 1) // 2) % 12


def _nearest_double_hour_boundary(effective: datetime) -> tuple[datetime, int]:
    """Nearest Chinese double-hour boundary and signed distance in seconds.

    Boundaries fall on every odd local hour (01, 03, ..., 23). The candidate
    window spans the surrounding three days so the late-Zi boundary at 23:00 of
    the previous day and the 01:00 boundary of the next day are both reachable
    across midnight. The signed distance is positive when the effective instant
    is after the boundary.
    """

    zone = effective.tzinfo
    base = effective.date()
    nearest: datetime | None = None
    nearest_abs: float | None = None
    for delta_days in (-1, 0, 1):
        day = base + timedelta(days=delta_days)
        for hour in DOUBLE_HOUR_BOUNDARY_HOURS:
            boundary = datetime(
                day.year, day.month, day.day, hour, 0, 0, tzinfo=zone
            )
            distance = (effective - boundary).total_seconds()
            magnitude = abs(distance)
            if nearest_abs is None or magnitude < nearest_abs:
                nearest = boundary
                nearest_abs = magnitude
                nearest_signed = int(round(distance))
    assert nearest is not None
    return nearest, nearest_signed


def ganzhi(value: Any) -> str:
    return STEMS[int(value.tg)] + BRANCHES[int(value.dz)]


def hour_pillar(day_ganzhi: str, hour_branch: str) -> str:
    """Apply the five-rat rule to the final selected day and hour branch."""

    stem_index = (
        (STEMS.index(day_ganzhi[0]) % 5) * 2 + BRANCHES.index(hour_branch)
    ) % 10
    return STEMS[stem_index] + hour_branch


def _localize_civil(value: str, timezone_name: str) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {timezone_name}") from exc
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("civil datetime must be ISO-8601") from exc
    if parsed.tzinfo is not None:
        return parsed.astimezone(zone)

    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = parsed.replace(tzinfo=zone, fold=fold)
        roundtrip = candidate.astimezone(timezone.utc).astimezone(zone)
        if roundtrip.replace(tzinfo=None) == parsed:
            candidates.append(candidate)
    offsets = {candidate.utcoffset() for candidate in candidates}
    if not candidates:
        raise ValueError(
            f"nonexistent local time in {timezone_name}; supply an offset-aware instant"
        )
    if len(offsets) > 1:
        raise ValueError(
            f"ambiguous local time in {timezone_name}; supply an offset-aware instant"
        )
    return candidates[0]


def term_datetime(term: Any, target_timezone: ZoneInfo | timezone) -> datetime:
    """Convert sxtwl's fixed UTC+08 term clock to a timezone-aware instant."""

    sxtwl = load_sxtwl()
    value = sxtwl.JD2DD(term.jd)
    base = datetime(
        int(value.Y),
        int(value.M),
        int(value.D),
        int(value.h),
        int(value.m),
        tzinfo=ENGINE_TIMEZONE,
    )
    return (base + timedelta(seconds=float(value.s))).astimezone(target_timezone)


def solar_terms(civil: datetime, *, years_each_side: int = 1) -> list[dict[str, Any]]:
    sxtwl = load_sxtwl()
    terms: list[dict[str, Any]] = []
    for year in range(civil.year - years_each_side, civil.year + years_each_side + 1):
        for term in sxtwl.getJieQiByYear(year):
            index = int(term.jqIndex)
            point = term_datetime(term, civil.tzinfo)
            terms.append(
                {
                    "name": JIEQI_NAMES[index],
                    "index": index,
                    "is_month_boundary_jie": index in MONTH_BOUNDARY_JIE,
                    "datetime": point.isoformat(timespec="microseconds"),
                    "instant_utc": point.astimezone(timezone.utc).isoformat(
                        timespec="microseconds"
                    ),
                }
            )
    unique = {(item["index"], item["instant_utc"]): item for item in terms}
    return sorted(unique.values(), key=lambda item: item["instant_utc"])


def surrounding_terms(
    terms: list[dict[str, Any]],
    point: datetime,
    *,
    jie_only: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = [
        item for item in terms if not jie_only or item["is_month_boundary_jie"]
    ]
    before = [
        item for item in candidates if datetime.fromisoformat(item["datetime"]) <= point
    ]
    after = [
        item for item in candidates if datetime.fromisoformat(item["datetime"]) > point
    ]
    if not before or not after:
        raise RuntimeError("could not resolve surrounding solar terms")
    return before[-1], after[0]


def _pillar_source_day(term: Mapping[str, Any]) -> Any:
    engine_datetime = datetime.fromisoformat(str(term["instant_utc"])).astimezone(
        ENGINE_TIMEZONE
    )
    return load_sxtwl().fromSolar(
        engine_datetime.year,
        engine_datetime.month,
        engine_datetime.day,
    )


def _number(value: float | int | None, *, label: str, minimum: float, maximum: float) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be within {minimum}..{maximum}")
    return number


def _pillar_facts_at(
    point: datetime,
    *,
    zi_hour_policy: str,
    terms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculate the four pillars at one already-normalized local instant.

    This is deliberately the one Runtime path used for both the civil
    no-correction baseline and the final effective instant.  Keeping the
    comparison inside this module prevents callers from deriving pillar
    changes from formatted timestamps or branch-name heuristics.
    """

    term_facts = solar_terms(point) if terms is None else terms
    previous_term, next_term = surrounding_terms(term_facts, point)
    previous_jie, next_jie = surrounding_terms(
        term_facts, point, jie_only=True
    )
    recent_li_chun = next(
        item
        for item in reversed(term_facts)
        if item["index"] == 3
        and datetime.fromisoformat(item["datetime"]) <= point
    )
    next_li_chun = next(
        item
        for item in term_facts
        if item["index"] == 3
        and datetime.fromisoformat(item["datetime"]) > point
    )

    pillar_date = point
    if point.hour == 23 and zi_hour_policy == "late-zi-next-day":
        pillar_date = point + timedelta(days=1)
    pillar_day = load_sxtwl().fromSolar(
        pillar_date.year,
        pillar_date.month,
        pillar_date.day,
    )
    active_jie_day = _pillar_source_day(previous_jie)
    active_year_day = _pillar_source_day(recent_li_chun)
    day = ganzhi(pillar_day.getDayGZ())
    hour_branch = ganzhi(pillar_day.getHourGZ(point.hour))[1]
    pillars = {
        "year": ganzhi(active_year_day.getYearGZ()),
        "month": ganzhi(active_jie_day.getMonthGZ()),
        "day": day,
        "hour": hour_pillar(day, hour_branch),
    }
    return {
        "pillars": pillars,
        "pillar_date": pillar_date,
        "previous_term": previous_term,
        "next_term": next_term,
        "previous_jie": previous_jie,
        "next_jie": next_jie,
        "recent_li_chun": recent_li_chun,
        "next_li_chun": next_li_chun,
        "exact_boundary": (
            previous_term
            if datetime.fromisoformat(previous_term["datetime"]) == point
            else None
        ),
    }


def normalize_calendar(
    civil_datetime: str,
    *,
    timezone_name: str,
    location: str,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    coordinate_accuracy_meters: float | None = None,
    zi_hour_policy: str = "midnight",
    time_basis_policy: str = "civil",
) -> dict[str, Any]:
    """Normalize one civil instant into a complete, digest-bound calendar fact."""

    if not str(location or "").strip():
        raise ValueError("location is required")
    if zi_hour_policy not in ZI_HOUR_POLICIES:
        raise ValueError(f"unsupported Zi-hour policy: {zi_hour_policy!r}")
    if time_basis_policy not in TIME_BASIS_POLICIES:
        raise ValueError(f"unsupported time-basis policy: {time_basis_policy!r}")
    longitude_value = _number(
        longitude,
        label="longitude",
        minimum=-180.0,
        maximum=180.0,
    )
    latitude_value = _number(
        latitude,
        label="latitude",
        minimum=-90.0,
        maximum=90.0,
    )
    if (longitude_value is None) != (latitude_value is None):
        raise ValueError("longitude and latitude must be supplied together")
    if longitude_value is not None and not str(coordinate_source or "").strip():
        raise ValueError("coordinate_source is required with longitude/latitude")
    accuracy_meters: float | None = None
    if coordinate_accuracy_meters is not None:
        accuracy_meters = float(coordinate_accuracy_meters)
        if not math.isfinite(accuracy_meters) or accuracy_meters < 0:
            raise ValueError(
                "coordinate_accuracy_meters must be a finite, non-negative number"
            )

    civil = _localize_civil(civil_datetime, timezone_name)
    utc_offset = civil.utcoffset() or timedelta(0)
    dst_offset = civil.dst() or timedelta(0)
    standard_offset = utc_offset - dst_offset
    standard_meridian = standard_offset.total_seconds() / 3600 * 15
    longitude_offset = (
        longitude_value - standard_meridian
        if longitude_value is not None
        else None
    )
    raw_longitude_correction = (
        int(round(longitude_offset * 240))
        if longitude_offset is not None
        else 0
    )
    requires_coordinates = time_basis_policy in {
        "longitude_mean_solar-v1",
        "local_apparent_solar-v1",
    }
    if requires_coordinates and longitude_value is None:
        raise ValueError(f"{time_basis_policy} requires measured coordinates")
    apparent = time_basis_policy == "local_apparent_solar-v1"
    applies_longitude = requires_coordinates
    longitude_correction_seconds = (
        raw_longitude_correction if applies_longitude else 0
    )
    eot_seconds = (
        equation_of_time_seconds(civil.astimezone(timezone.utc))
        if apparent
        else 0
    )
    if time_basis_policy == "civil":
        total_correction_seconds = 0
    elif apparent:
        total_correction_seconds = longitude_correction_seconds + eot_seconds
    else:
        total_correction_seconds = longitude_correction_seconds
    effective = (
        civil + timedelta(seconds=total_correction_seconds)
        if total_correction_seconds
        else civil
    )
    local_mean_solar = (
        civil + timedelta(seconds=raw_longitude_correction)
        if applies_longitude
        else None
    )
    local_apparent_solar = (
        civil + timedelta(seconds=total_correction_seconds)
        if apparent
        else None
    )

    sxtwl = load_sxtwl()
    lunar_day = sxtwl.fromSolar(civil.year, civil.month, civil.day)
    effective_lunar_day = sxtwl.fromSolar(
        effective.year, effective.month, effective.day
    )
    terms = solar_terms(effective)
    civil_pillar_facts = _pillar_facts_at(
        civil,
        zi_hour_policy=zi_hour_policy,
        terms=terms,
    )
    effective_pillar_facts = _pillar_facts_at(
        effective,
        zi_hour_policy=zi_hour_policy,
        terms=terms,
    )
    pillar_date = effective_pillar_facts["pillar_date"]
    previous_term = effective_pillar_facts["previous_term"]
    next_term = effective_pillar_facts["next_term"]
    previous_jie = effective_pillar_facts["previous_jie"]
    next_jie = effective_pillar_facts["next_jie"]
    recent_li_chun = effective_pillar_facts["recent_li_chun"]
    next_li_chun = effective_pillar_facts["next_li_chun"]
    exact_boundary = effective_pillar_facts["exact_boundary"]
    pillars = dict(effective_pillar_facts["pillars"])
    civil_pillars = civil_pillar_facts["pillars"]
    changed_pillars = [
        position
        for position in ("year", "month", "day", "hour")
        if civil_pillars[position] != pillars[position]
    ]
    day_boundary = {
        "correction_crossed_date": effective.date() != civil.date(),
        "zi_policy_advanced_day_pillar": pillar_date.date() != effective.date(),
    }
    civil_hour_branch = _hour_branch_index(civil.hour)
    effective_hour_branch = _hour_branch_index(effective.hour)
    nearest_boundary, boundary_distance = _nearest_double_hour_boundary(effective)
    correction_changes_hour_branch = civil_hour_branch != effective_hour_branch
    coord_accuracy_seconds = 0.0
    if apparent and accuracy_meters is not None and latitude_value is not None:
        meters_per_second = 463.8 * math.cos(math.radians(latitude_value))
        if meters_per_second > 0:
            coord_accuracy_seconds = accuracy_meters / meters_per_second
        else:
            coord_accuracy_seconds = float("inf")
    uncertainty_budget = EOT_UNCERTAINTY_SECONDS + coord_accuracy_seconds
    within_uncertainty = (
        apparent and abs(boundary_distance) <= uncertainty_budget
    )
    if apparent:
        true_solar_status = "apparent_solar_applied"
    elif time_basis_policy == "longitude_mean_solar-v1":
        true_solar_status = "longitude_mean_solar_applied"
    else:
        true_solar_status = "not_applied"
    true_solar_time = {
        "status": true_solar_status,
        "policy": time_basis_policy,
        "longitude_correction_seconds": longitude_correction_seconds,
        "equation_of_time_seconds": eot_seconds,
        "total_correction_seconds": total_correction_seconds,
    }
    time_basis_algorithm = (
        {
            "id": EOT_ALGORITHM_ID,
            "version": EOT_ALGORITHM_VERSION,
            "source": EOT_ALGORITHM_SOURCE,
            "supported_range": EOT_SUPPORTED_RANGE,
            "uncertainty_seconds": EOT_UNCERTAINTY_SECONDS,
        }
        if apparent
        else None
    )
    time_basis_block = {
        "policy": time_basis_policy,
        "standard_meridian_degrees": round(standard_meridian, 9),
        "longitude_correction_seconds": longitude_correction_seconds,
        "equation_of_time_seconds": eot_seconds,
        "total_correction_seconds": total_correction_seconds,
        "local_mean_solar_datetime": (
            local_mean_solar.isoformat() if local_mean_solar is not None else None
        ),
        "local_apparent_solar_datetime": (
            local_apparent_solar.isoformat()
            if local_apparent_solar is not None
            else None
        ),
        "algorithm": time_basis_algorithm,
        "boundary": {
            "nearest_double_hour_boundary": nearest_boundary.isoformat(),
            "distance_seconds": boundary_distance,
            "correction_changes_hour_branch": correction_changes_hour_branch,
            "within_uncertainty": within_uncertainty,
        },
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "status": "calculated",
        "civil_datetime": civil.isoformat(),
        "solar_date": civil.date().isoformat(),
        "effective_datetime": effective.isoformat(),
        "effective_solar_date": effective.date().isoformat(),
        "day_boundary": day_boundary,
        "changed_pillars": changed_pillars,
        "instant_utc": civil.astimezone(timezone.utc).isoformat(),
        "utc_datetime": civil.astimezone(timezone.utc).isoformat(),
        "timezone": timezone_name,
        "timezone_details": {
            "name": timezone_name,
            "utc_offset_seconds": int(utc_offset.total_seconds()),
            "dst_offset_seconds": int(dst_offset.total_seconds()),
            "standard_offset_seconds": int(standard_offset.total_seconds()),
            "standard_meridian_degrees": round(standard_meridian, 9),
            "fold": civil.fold,
        },
        "timezone_offset_seconds": int(utc_offset.total_seconds()),
        "dst_offset_seconds": int(dst_offset.total_seconds()),
        "location": {
            "name": str(location),
            "longitude": longitude_value,
            "latitude": latitude_value,
            "coordinate_source": (
                str(coordinate_source)
                if coordinate_source
                else "not_supplied"
            ),
            "coordinate_accuracy_meters": (
                float(coordinate_accuracy_meters)
                if coordinate_accuracy_meters is not None
                else None
            ),
            "longitude_offset_degrees": (
                round(longitude_offset, 9)
                if longitude_offset is not None
                else None
            ),
        },
        "calendar_convention": {
            "id": CONVENTION_ID,
            "version": CONVENTION_VERSION,
            "engine": "sxtwl",
            "engine_version": ENGINE_VERSION,
            "source_dependency_id": "bazi.calendar.sxtwl-jieqi-four-pillars",
            "year_boundary": "exact Li Chun instant",
            "month_boundary": "exact Jie instant",
            "day_rollover": (
                "late_zi_advances_day_pillar"
                if zi_hour_policy == "late-zi-next-day"
                else "civil_midnight"
            ),
            "hour_basis": time_basis_policy,
            "zi_hour_policy": zi_hour_policy,
        },
        "time_basis": time_basis_block,
        "lunar_date": {
            "year": int(lunar_day.getLunarYear()),
            "month": int(lunar_day.getLunarMonth()),
            "day": int(lunar_day.getLunarDay()),
            "is_leap_month": bool(lunar_day.isLunarLeap()),
        },
        "effective_lunar_date": {
            "year": int(effective_lunar_day.getLunarYear()),
            "month": int(effective_lunar_day.getLunarMonth()),
            "day": int(effective_lunar_day.getLunarDay()),
            "is_leap_month": bool(effective_lunar_day.isLunarLeap()),
        },
        "ganzhi": pillars,
        "solar_terms": {
            "previous": previous_term,
            "next": next_term,
            "previous_month_boundary_jie": previous_jie,
            "next_month_boundary_jie": next_jie,
            "active_month_boundary_jie": previous_jie,
            "active_year_boundary_li_chun": recent_li_chun,
            "next_year_boundary_li_chun": next_li_chun,
            "exact_boundary": exact_boundary,
            "month_switch_policy": "exact Jie instant",
        },
        "zi_hour_policy": zi_hour_policy,
        "true_solar_time": true_solar_time,
    }
    digest = calendar_digest(payload)
    payload["calendar_digest"] = digest
    payload["digest"] = digest
    return payload


def li_chun_boundary(year: int, timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    term = next(
        item
        for item in load_sxtwl().getJieQiByYear(year)
        if int(item.jqIndex) == 3
    )
    return term_datetime(term, zone)


def month_boundary_terms(year: int, month: int, timezone_name: str) -> list[dict[str, Any]]:
    zone = ZoneInfo(timezone_name)
    point = datetime(year, month, 15, 12, tzinfo=zone)
    return [
        item
        for item in solar_terms(point)
        if item["is_month_boundary_jie"]
        and (datetime.fromisoformat(item["datetime"]).year, datetime.fromisoformat(item["datetime"]).month)
        == (year, month)
    ]


def month_ganzhi_at(point: datetime) -> str:
    terms = solar_terms(point)
    previous_jie, _ = surrounding_terms(terms, point, jie_only=True)
    return ganzhi(_pillar_source_day(previous_jie).getMonthGZ())


def year_ganzhi_after_li_chun(year: int) -> str:
    return ganzhi(load_sxtwl().fromSolar(year, 7, 1).getYearGZ())
