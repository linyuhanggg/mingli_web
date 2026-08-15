from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.readings.capability_policy import ProductRoute, route_for_action
from app.readings.runtime_contracts import Prepare

_BAZI_DIMENSION_IDS = frozenset({"overview", "career"})
_BAZI_YEAR_MIN = 1800
_BAZI_YEAR_MAX = 2199
_FIVE_ELEMENTS_FACTS_DIMENSION_IDS = frozenset({"state"})
_CHART_SIMILARITY_DIMENSION_IDS = frozenset({"state"})
_FORTUNE_DIMENSION_IDS = frozenset({"career"})
_LIUYAO_DIMENSION_IDS = frozenset({"career", "outcome", "timing"})
_WENSHI_DIMENSION_IDS = frozenset({"outcome", "timing"})
_NATAL_ART_DIMENSION_IDS = frozenset(
    {"career", "health", "location", "outcome", "relationship", "state", "timing"}
)
_MEIHUA_DIMENSION_IDS = frozenset({"outcome", "state"})
_TAIYI_DIMENSION_IDS = frozenset({"location", "outcome", "state", "timing"})
_SELECTION_DIMENSION_IDS = frozenset({"location", "state", "timing"})
_FENGSHUI_DIMENSION_IDS = frozenset(
    {"current_state", "direction", "location", "state"}
)
_PHYSIOGNOMY_DIMENSION_IDS = frozenset({"state", "source_comparison"})
_TIME_CHECK_DIMENSION_IDS = frozenset({"time_options"})
_EVENT_ART_DIMENSION_IDS = frozenset(
    {"career", "location", "money", "outcome", "relationship", "state", "timing", "work"}
)
_RELATIONSHIP_DIMENSION_IDS = frozenset({"relationship"})
_CANWEN_ART_TO_RUNTIME = {
    "bazi": "bazi",
    "ziwei": "ziwei",
    "qizheng": "xingming",
}
_MEIHUA_CASTING_METHODS = frozenset(
    {"time", "supplied_number", "sound_count", "observation", "supplied_hexagram"}
)
_MEIHUA_TRIGRAMS = frozenset({"乾", "兑", "离", "震", "巽", "坎", "艮", "坤"})
_LIUYAO_CAST_VALUES = frozenset({6, 7, 8, 9})


class RequestCompilationError(ValueError):
    """A product request cannot be compiled into a lawful Prepare command."""


_RUNTIME_TIME_BASIS_POLICIES = frozenset(
    {
        "civil",
        "longitude_mean_solar-v1",
        "local_apparent_solar-v1",
    }
)

_RUNTIME_ZI_HOUR_POLICIES = frozenset({"midnight", "late-zi-next-day"})
_CLOCK_TEXT = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


def _runtime_time_basis_policy(value: str) -> str:
    """Translate the product label into the Runtime's exact policy ID.

    The profile API keeps the short product-facing ``solar`` value for now,
    while Runtime requires an explicit algorithm policy.  The product's true
    solar option means local apparent solar time; it must not be passed through
    as an opaque alias or silently fall back to civil time.
    """

    if value == "solar":
        return "local_apparent_solar-v1"
    if value == "lunar":
        raise RequestCompilationError(
            "lunar birth input requires lunar date fields and is not supported by this request"
        )
    if value not in _RUNTIME_TIME_BASIS_POLICIES:
        raise RequestCompilationError(
            f"unsupported Runtime time-basis policy: {value!r}"
        )
    return value


def _runtime_zi_hour_policy(value: str) -> str:
    """Translate the product's 子时 labels into Runtime policy IDs.

    True-solar time is handled by ``time_basis_policy`` before the calendar
    day boundary is applied.  The product's ``solar`` label therefore keeps
    the midnight boundary, while ``substitute`` is the product's alternate
    late-Zi-next-day convention.  Runtime never receives either UI alias.
    """

    if value == "solar":
        return "midnight"
    if value == "substitute":
        return "late-zi-next-day"
    if value not in _RUNTIME_ZI_HOUR_POLICIES:
        raise RequestCompilationError(
            f"unsupported Runtime Zi-hour policy: {value!r}"
        )
    return value


def _meihua_positive_integer(value: int | None, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RequestCompilationError(f"Meihua {field} must be a positive integer")
    return value


def _meihua_trigram(value: str | None, *, field: str) -> str:
    if value not in _MEIHUA_TRIGRAMS:
        raise RequestCompilationError(
            f"Meihua {field} must be one of {sorted(_MEIHUA_TRIGRAMS)!r}"
        )
    return value


def _meihua_source(
    value: Mapping[str, object] | None,
    *,
    field: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping) or not value:
        raise RequestCompilationError(f"Meihua {field} must be a non-empty object")
    return {str(key): item for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class ConfirmedProfileVersion:
    subject_ref: str
    birth_datetime: str
    birth_datetime_or_four_pillars: str
    timezone: str
    location: str
    gender: str
    time_basis_policy: str
    zi_hour_policy: str
    longitude: float | None
    latitude: float | None
    coordinate_source: str | None


RelationshipArt = Literal["bazi", "ziwei", "qizheng"]
RelationshipType = Literal[
    "romantic",
    "married",
    "parent_child",
    "business",
    "work",
    "friend",
]


def _route_for_compiler(
    action: str,
    *,
    expected_capability_id: str,
) -> ProductRoute:
    route = route_for_action(action)
    if route.capability_id != expected_capability_id:
        raise RequestCompilationError(
            f"product action {action!r} does not use {expected_capability_id!r}"
        )
    return route


def _validate_dimensions(
    dimension_ids: tuple[str, ...],
    *,
    allowed: frozenset[str],
) -> None:
    if len(set(dimension_ids)) != len(dimension_ids):
        raise RequestCompilationError("dimension IDs must be unique")
    unknown = set(dimension_ids) - allowed
    if unknown:
        raise RequestCompilationError(
            f"dimension IDs are outside the product allowlist: {sorted(unknown)!r}"
        )


def _normalize_datetime(value: datetime, timezone_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RequestCompilationError("server datetime must be timezone-aware")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise RequestCompilationError(
            f"confirmed timezone is invalid: {timezone_name!r}"
        ) from error
    return value.astimezone(timezone)


def _intent(
    *,
    subject_ref: str,
    route: ProductRoute,
    dimension_ids: tuple[str, ...],
    start: str | None,
    end: str | None,
    comparisons: tuple[dict[str, str], ...] = (),
) -> dict[str, object]:
    return {
        "subject_refs": [subject_ref],
        "object_id": route.object_id,
        "dimension_ids": list(dimension_ids),
        "horizon": {
            "kind_id": route.horizon_id,
            "start": start,
            "end": end,
        },
        "capability_id": route.capability_id,
        "comparisons": [dict(item) for item in comparisons],
    }


def _relationship_intent(
    *,
    subject_refs: tuple[str, str],
    route: ProductRoute,
    dimension_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "subject_refs": list(subject_refs),
        "object_id": route.object_id,
        "dimension_ids": list(dimension_ids),
        "horizon": {
            "kind_id": route.horizon_id,
            "start": None,
            "end": None,
        },
        "capability_id": route.capability_id,
        "comparisons": [],
    }


def compile_bazi_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="bazi")
    _validate_dimensions(dimension_ids, allowed=_BAZI_DIMENSION_IDS)
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": (profile.birth_datetime_or_four_pillars),
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={profile.subject_ref: facts},
    )


def compile_bazi_year_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    year: int,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    """Compile one exact Runtime-owned civil-year Bazi layer request."""

    route = _route_for_compiler(action, expected_capability_id="bazi")
    _validate_dimensions(dimension_ids, allowed=_BAZI_DIMENSION_IDS)
    if isinstance(year, bool) or not isinstance(year, int):
        raise RequestCompilationError("Bazi target year must be an integer")
    if not _BAZI_YEAR_MIN <= year <= _BAZI_YEAR_MAX:
        raise RequestCompilationError(
            f"Bazi target year must be within {_BAZI_YEAR_MIN}-{_BAZI_YEAR_MAX}"
        )
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": profile.birth_datetime_or_four_pillars,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=str(year),
            end=str(year),
        ),
        facts={profile.subject_ref: facts},
    )


def _validated_target_month(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", value):
        raise RequestCompilationError(f"{label} must use YYYY-MM")
    year = int(value[:4])
    if not _BAZI_YEAR_MIN <= year <= _BAZI_YEAR_MAX:
        raise RequestCompilationError(
            f"{label} must be within {_BAZI_YEAR_MIN}-01 and {_BAZI_YEAR_MAX}-12"
        )
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as error:
        raise RequestCompilationError(f"{label} is not a valid calendar month") from error
    return value


def _validated_target_date(value: date, *, label: str) -> str:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise RequestCompilationError(f"{label} must be a calendar date")
    if not _BAZI_YEAR_MIN <= value.year <= _BAZI_YEAR_MAX:
        raise RequestCompilationError(
            f"{label} must be within {_BAZI_YEAR_MIN}-01-01 and {_BAZI_YEAR_MAX}-12-31"
        )
    return value.isoformat()


def compile_bazi_month_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    month: str,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="bazi")
    _validate_dimensions(dimension_ids, allowed=_BAZI_DIMENSION_IDS)
    target_month = _validated_target_month(month, label="Bazi target month")
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": profile.birth_datetime_or_four_pillars,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=target_month,
            end=target_month,
        ),
        facts={profile.subject_ref: facts},
    )


def compile_bazi_day_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    target_date: date,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="bazi")
    _validate_dimensions(dimension_ids, allowed=_BAZI_DIMENSION_IDS)
    day = _validated_target_date(target_date, label="Bazi target date")
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": profile.birth_datetime_or_four_pillars,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=day,
            end=day,
        ),
        facts={profile.subject_ref: facts},
    )


def compile_five_elements_facts_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    """Compile the bounded five-elements facts product from a confirmed profile.

    This product deliberately shares Bazi's Runtime inputs but has its own
    action and dimension contract.  It exposes inventory and seasonal facts;
    it does not authorize a 旺衰、喜忌 or 用神 conclusion.
    """

    route = _route_for_compiler(action, expected_capability_id="bazi")
    _validate_dimensions(dimension_ids, allowed=_FIVE_ELEMENTS_FACTS_DIMENSION_IDS)
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": profile.birth_datetime_or_four_pillars,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={profile.subject_ref: facts},
    )


def compile_time_check_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    time_range_start: str,
    time_range_end: str,
    known_events: tuple[str, ...],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    """Compile the bounded twelve-hour candidate fact request.

    The profile supplies the date, location, gender, and time-basis policy;
    the tool supplies only the known clock range and optional event labels.
    Runtime owns candidate calculation and explicitly does not rank events.
    """

    route = _route_for_compiler(action, expected_capability_id="time-check")
    _validate_dimensions(dimension_ids, allowed=_TIME_CHECK_DIMENSION_IDS)
    if not dimension_ids:
        raise RequestCompilationError("time-check requires a dimension")
    if not _CLOCK_TEXT.fullmatch(time_range_start) or not _CLOCK_TEXT.fullmatch(
        time_range_end
    ):
        raise RequestCompilationError("time-check time range must use HH:MM")
    try:
        birth_date = datetime.fromisoformat(profile.birth_datetime).date().isoformat()
    except ValueError as error:
        raise RequestCompilationError("profile birth datetime is invalid") from error
    facts: dict[str, object] = {
        "time_check_date": birth_date,
        "time_range_start": time_range_start,
        "time_range_end": time_range_end,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
        "known_events": list(known_events),
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={profile.subject_ref: facts},
    )


def compile_fortune_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    server_reference_datetime: datetime,
    dimension_ids: tuple[str, ...],
    requested_timezone: str | None = None,
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="fortune")
    _validate_dimensions(dimension_ids, allowed=_FORTUNE_DIMENSION_IDS)
    if requested_timezone is not None and requested_timezone != profile.timezone:
        raise RequestCompilationError(
            "requested timezone cannot override the confirmed profile timezone"
        )
    reference_datetime = _normalize_datetime(
        server_reference_datetime,
        profile.timezone,
    )
    start_date = reference_datetime.date()
    end_date = start_date if route.horizon_id == "day" else start_date + timedelta(days=6)
    facts: dict[str, object] = {
        "birth_datetime": profile.birth_datetime,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "reference_datetime": reference_datetime.isoformat(),
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
    }
    if facts["time_basis_policy"] != "civil":
        facts.update(
            {
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        )
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        ),
        facts={profile.subject_ref: facts},
    )


def compile_ziwei_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="ziwei")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_ziwei_year_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    year: int,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="ziwei")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    if isinstance(year, bool) or not isinstance(year, int) or not 1800 <= year <= 2199:
        raise RequestCompilationError("Ziwei target year must be an integer within 1800-2199")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=str(year),
            end=str(year),
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_ziwei_month_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    month: str,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="ziwei")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    target_month = _validated_target_month(month, label="Ziwei target month")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=target_month,
            end=target_month,
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_qizheng_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="xingming")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    if profile.longitude is None or profile.latitude is None or not profile.coordinate_source:
        raise RequestCompilationError(
            "qizheng requires longitude, latitude, and coordinate_source"
        )
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_qizheng_year_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    year: int,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="xingming")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    if profile.longitude is None or profile.latitude is None or not profile.coordinate_source:
        raise RequestCompilationError(
            "qizheng requires longitude, latitude, and coordinate_source"
        )
    if isinstance(year, bool) or not isinstance(year, int) or not 1800 <= year <= 2199:
        raise RequestCompilationError("Qizheng target year must be an integer within 1800-2199")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=str(year),
            end=str(year),
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_qizheng_month_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    month: str,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="xingming")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    if profile.longitude is None or profile.latitude is None or not profile.coordinate_source:
        raise RequestCompilationError(
            "qizheng requires longitude, latitude, and coordinate_source"
        )
    target_month = _validated_target_month(month, label="Qizheng target month")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=target_month,
            end=target_month,
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_qizheng_day_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    target_date: date,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="xingming")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    if profile.longitude is None or profile.latitude is None or not profile.coordinate_source:
        raise RequestCompilationError(
            "qizheng requires longitude, latitude, and coordinate_source"
        )
    day = _validated_target_date(target_date, label="Qizheng target date")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=day,
            end=day,
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def _compile_natal_cross_art_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    selected_art_ids: tuple[str, ...],
    dimension_ids: tuple[str, ...],
    product_label: str,
) -> Prepare:
    """Compile a deterministic natal cross-art brief slice.

    八字 is the current primary provider.  The selected 紫微/七政 providers
    are required Runtime comparisons, so a missing comparison cannot silently
    degrade into a one-chart answer.  Product-facing ``qizheng`` is translated
    explicitly to the Runtime's ``xingming`` capability.  The product label is
    kept separate from the Runtime intent because the same comparison contract
    feeds both Canwen and Hecan ViewModels.
    """

    route = _route_for_compiler(action, expected_capability_id="bazi")
    if len(selected_art_ids) not in {2, 3}:
        raise RequestCompilationError(
            f"{product_label} requires exactly two or three arts"
        )
    if len(set(selected_art_ids)) != len(selected_art_ids):
        raise RequestCompilationError(f"{product_label} art IDs must be unique")
    unknown = set(selected_art_ids) - set(_CANWEN_ART_TO_RUNTIME)
    if unknown:
        raise RequestCompilationError(
            f"{product_label} art IDs are unsupported: {sorted(unknown)!r}"
        )
    if selected_art_ids[0] != "bazi":
        raise RequestCompilationError(
            f"{product_label} preview currently requires bazi as the primary art"
        )
    if (
        "qizheng" in selected_art_ids
        and (
            profile.longitude is None
            or profile.latitude is None
            or not profile.coordinate_source
        )
    ):
        raise RequestCompilationError(
            f"{product_label} with qizheng requires longitude, latitude, and coordinate_source"
        )
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    comparisons = tuple(
        {
            "capability_id": _CANWEN_ART_TO_RUNTIME[art_id],
            "requirement": "required",
        }
        for art_id in selected_art_ids[1:]
    )
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": profile.birth_datetime_or_four_pillars,
        "birth_datetime": profile.birth_datetime,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
            comparisons=comparisons,
        ),
        facts={profile.subject_ref: facts},
    )


def compile_canwen_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    selected_art_ids: tuple[str, ...],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    return _compile_natal_cross_art_prepare(
        action=action,
        query=query,
        profile=profile,
        selected_art_ids=selected_art_ids,
        dimension_ids=dimension_ids,
        product_label="canwen",
    )


def compile_hecan_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    selected_art_ids: tuple[str, ...],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    return _compile_natal_cross_art_prepare(
        action=action,
        query=query,
        profile=profile,
        selected_art_ids=selected_art_ids,
        dimension_ids=dimension_ids,
        product_label="hecan",
    )


def _relationship_profile_facts(profile: ConfirmedProfileVersion) -> dict[str, object]:
    return {
        "birth_datetime_or_four_pillars": profile.birth_datetime_or_four_pillars,
        "birth_datetime": profile.birth_datetime,
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": _runtime_time_basis_policy(profile.time_basis_policy),
        "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
        "longitude": profile.longitude,
        "latitude": profile.latitude,
        "coordinate_source": profile.coordinate_source,
    }


def compile_relationship_prepare(
    *,
    action: str,
    query: str,
    art_id: RelationshipArt,
    relationship_type: RelationshipType,
    profiles: tuple[ConfirmedProfileVersion, ConfirmedProfileVersion],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    expected_capability = {
        "bazi": "bazi",
        "ziwei": "ziwei",
        "qizheng": "xingming",
    }[art_id]
    route = _route_for_compiler(action, expected_capability_id=expected_capability)
    if profiles[0].subject_ref == profiles[1].subject_ref:
        raise RequestCompilationError("relationship requires two distinct profiles")
    _validate_dimensions(dimension_ids, allowed=_RELATIONSHIP_DIMENSION_IDS)
    if len(dimension_ids) != 1 or dimension_ids[0] != "relationship":
        raise RequestCompilationError("relationship requires the relationship dimension")
    if art_id == "qizheng" and any(
        profile.longitude is None
        or profile.latitude is None
        or not profile.coordinate_source
        for profile in profiles
    ):
        raise RequestCompilationError(
            "qizheng relationship requires longitude, latitude, and "
            "coordinate_source for both profiles"
        )
    del relationship_type  # Stored on ReadingVersion; Runtime intent stays schema-compatible.
    subject_refs = (profiles[0].subject_ref, profiles[1].subject_ref)
    return Prepare(
        query=query,
        intent=_relationship_intent(
            subject_refs=subject_refs,
            route=route,
            dimension_ids=dimension_ids,
        ),
        facts={
            profiles[0].subject_ref: _relationship_profile_facts(profiles[0]),
            profiles[1].subject_ref: _relationship_profile_facts(profiles[1]),
        },
    )


def compile_chart_similarity_prepare(
    *,
    action: str,
    query: str,
    profiles: tuple[ConfirmedProfileVersion, ConfirmedProfileVersion],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    """Compile the exact Bazi four-pillar comparison input.

    Both subjects are sent through the same Bazi Runtime Provider.  The
    product projector compares only the resulting calculated facts.
    """

    route = _route_for_compiler(action, expected_capability_id="bazi")
    if profiles[0].subject_ref == profiles[1].subject_ref:
        raise RequestCompilationError("chart similarity requires two distinct profiles")
    _validate_dimensions(dimension_ids, allowed=_CHART_SIMILARITY_DIMENSION_IDS)
    if len(dimension_ids) != 1 or dimension_ids[0] != "state":
        raise RequestCompilationError("chart similarity requires the state dimension")
    subject_refs = (profiles[0].subject_ref, profiles[1].subject_ref)
    return Prepare(
        query=query,
        intent=_relationship_intent(
            subject_refs=subject_refs,
            route=route,
            dimension_ids=dimension_ids,
        ),
        facts={
            profiles[0].subject_ref: _relationship_profile_facts(profiles[0]),
            profiles[1].subject_ref: _relationship_profile_facts(profiles[1]),
        },
    )


def compile_meihua_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    casting_method: str,
    event_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    time_basis_policy: str = "civil",
    zi_hour_policy: str = "midnight",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    number: int | None = None,
    count: int | None = None,
    upper_trigram: str | None = None,
    lower_trigram: str | None = None,
    moving_line: int | None = None,
    provenance: Mapping[str, object] | None = None,
    observation_source: Mapping[str, object] | None = None,
) -> Prepare:
    """Compile one of the Runtime's five explicit Meihua casting methods."""

    route = _route_for_compiler(action, expected_capability_id="meihua")
    if casting_method not in _MEIHUA_CASTING_METHODS:
        raise RequestCompilationError(
            f"unsupported Meihua casting method: {casting_method!r}"
        )
    _validate_dimensions(dimension_ids, allowed=_MEIHUA_DIMENSION_IDS)
    normalized_datetime = _normalize_datetime(event_datetime, confirmed_timezone)
    method_facts: dict[str, object] = {"casting_method": casting_method}
    if casting_method == "supplied_number":
        method_facts.update(
            {
                "number": _meihua_positive_integer(number, field="number"),
                "provenance": _meihua_source(provenance, field="provenance"),
            }
        )
    elif casting_method == "sound_count":
        method_facts.update(
            {
                "count": _meihua_positive_integer(count, field="count"),
                "observation_source": _meihua_source(
                    observation_source,
                    field="observation_source",
                ),
            }
        )
    elif casting_method == "observation":
        method_facts.update(
            {
                "upper_trigram": _meihua_trigram(upper_trigram, field="upper_trigram"),
                "lower_trigram": _meihua_trigram(lower_trigram, field="lower_trigram"),
                "observation_source": _meihua_source(
                    observation_source,
                    field="observation_source",
                ),
            }
        )
    elif casting_method == "supplied_hexagram":
        line = _meihua_positive_integer(moving_line, field="moving_line")
        if line > 6:
            raise RequestCompilationError("Meihua moving_line must be within 1..6")
        method_facts.update(
            {
                "upper_trigram": _meihua_trigram(upper_trigram, field="upper_trigram"),
                "lower_trigram": _meihua_trigram(lower_trigram, field="lower_trigram"),
                "moving_line": line,
                "provenance": _meihua_source(provenance, field="provenance"),
            }
        )
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            subject_ref: {
                **method_facts,
                "event_datetime": normalized_datetime.isoformat(),
                "timezone": confirmed_timezone,
                "location": location,
                "time_basis_policy": _runtime_time_basis_policy(time_basis_policy),
                "zi_hour_policy": _runtime_zi_hour_policy(zi_hour_policy),
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            }
        },
    )


def compile_luming_nayin_prepare(
    *,
    action: str,
    query: str,
    profile: ConfirmedProfileVersion,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="luming-nayin")
    _validate_dimensions(dimension_ids, allowed=_NATAL_ART_DIMENSION_IDS)
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime_or_four_pillars": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "time_basis_policy": _runtime_time_basis_policy(
                    profile.time_basis_policy
                ),
                "zi_hour_policy": _runtime_zi_hour_policy(profile.zi_hour_policy),
                "longitude": profile.longitude,
                "latitude": profile.latitude,
                "coordinate_source": profile.coordinate_source,
            }
        },
    )


def compile_taiyi_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    reference_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    time_basis_policy: str = "civil",
    zi_hour_policy: str = "midnight",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="taiyi")
    _validate_dimensions(dimension_ids, allowed=_TAIYI_DIMENSION_IDS)
    normalized_datetime = _normalize_datetime(reference_datetime, confirmed_timezone)
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            subject_ref: {
                "reference_datetime": normalized_datetime.isoformat(),
                "timezone": confirmed_timezone,
                "location": location,
                "time_basis_policy": _runtime_time_basis_policy(time_basis_policy),
                "zi_hour_policy": _runtime_zi_hour_policy(zi_hour_policy),
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            }
        },
    )


def _strict_selection_date(value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise RequestCompilationError(f"{label} must be an ISO civil date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise RequestCompilationError(f"{label} must be an ISO civil date") from error
    if parsed.isoformat() != value:
        raise RequestCompilationError(f"{label} must use YYYY-MM-DD")
    return parsed.isoformat()


def compile_selection_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    event_profile: str,
    requested_actions: tuple[str, ...],
    date_range_start: str,
    date_range_end: str,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    requested_scopes: tuple[str, ...] = (),
    hard_constraints: Mapping[str, object] | None = None,
    participant_facts: tuple[Mapping[str, object], ...] = (),
    directional_context: Mapping[str, str] | None = None,
    include_folk_comparison: bool = False,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="selection")
    _validate_dimensions(dimension_ids, allowed=_SELECTION_DIMENSION_IDS)
    start = _strict_selection_date(date_range_start, label="date_range.start")
    end = _strict_selection_date(date_range_end, label="date_range.end")
    if end < start:
        raise RequestCompilationError("date_range.end precedes date_range.start")
    if any(
        item not in {"directional_judgment"} for item in requested_scopes
    ):
        raise RequestCompilationError("selection requested_scopes is unsupported")
    if not isinstance(event_profile, str) or not event_profile.strip():
        raise RequestCompilationError("selection event_profile is required")
    if not requested_actions and event_profile != "generic_selection":
        raise RequestCompilationError(
            "selection requested_actions is required for this event profile"
        )
    if not isinstance(include_folk_comparison, bool):
        raise RequestCompilationError("selection include_folk_comparison must be boolean")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            subject_ref: {
                "event_profile": event_profile,
                "requested_actions": list(requested_actions),
                "date_range": {"start": start, "end": end},
                "requested_scopes": list(requested_scopes),
                "hard_constraints": dict(hard_constraints or {}),
                "participant_facts": [dict(item) for item in participant_facts],
                "directional_context": (
                    dict(directional_context) if directional_context is not None else None
                ),
                "include_folk_comparison": include_folk_comparison,
                "timezone": confirmed_timezone,
                "location": location,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            }
        },
    )


def compile_fengshui_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    fengshui_spec: Mapping[str, object],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="fengshui")
    _validate_dimensions(dimension_ids, allowed=_FENGSHUI_DIMENSION_IDS)
    if not isinstance(fengshui_spec, Mapping) or not fengshui_spec:
        raise RequestCompilationError("fengshui_spec must be a non-empty object")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={subject_ref: {"fengshui_spec": dict(fengshui_spec)}},
    )


def compile_physiognomy_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    physiognomy_spec: Mapping[str, object],
    dimension_ids: tuple[str, ...],
) -> Prepare:
    """Compile caller-normalized visible observations for the Runtime.

    Image capture, quality checks, authorization, and any vision-capable
    transcription happen before this boundary.  The Provider receives only
    the structured observation contract and must not decode or fetch media.
    """

    route = _route_for_compiler(action, expected_capability_id="physiognomy")
    _validate_dimensions(dimension_ids, allowed=_PHYSIOGNOMY_DIMENSION_IDS)
    if not isinstance(physiognomy_spec, Mapping) or not physiognomy_spec:
        raise RequestCompilationError("physiognomy_spec must be a non-empty object")
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={subject_ref: {"physiognomy_spec": dict(physiognomy_spec)}},
    )


def _normalize_liuyao_cast(cast: tuple[int | bool, ...] | str) -> object:
    if cast == "digital_coin":
        return cast
    if not isinstance(cast, tuple) or len(cast) != 6:
        raise RequestCompilationError("liuyao cast must be six bottom-up tosses or digital_coin")
    if any(type(value) is not int or value not in _LIUYAO_CAST_VALUES for value in cast):
        raise RequestCompilationError("liuyao toss values must be integers in 6..9")
    return list(cast)


def compile_liuyao_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    cast: tuple[int | bool, ...] | str,
    event_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
) -> Prepare:
    route = _route_for_compiler(action, expected_capability_id="liuyao")
    _validate_dimensions(dimension_ids, allowed=_LIUYAO_DIMENSION_IDS)
    normalized_datetime = _normalize_datetime(event_datetime, confirmed_timezone)
    normalized_cast = _normalize_liuyao_cast(cast)
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            subject_ref: {
                "cast": normalized_cast,
                "event_datetime": normalized_datetime.isoformat(),
                "timezone": confirmed_timezone,
                "location": location,
            }
        },
    )


def compile_wenshi_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    cast: tuple[int | bool, ...] | str,
    event_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    time_basis_policy: str = "civil",
    zi_hour_policy: str = "midnight",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> Prepare:
    """Compile one event into Runtime's native three-art comparison contract."""

    route = _route_for_compiler(action, expected_capability_id="liuyao")
    _validate_dimensions(dimension_ids, allowed=_WENSHI_DIMENSION_IDS)
    normalized_datetime = _normalize_datetime(event_datetime, confirmed_timezone)
    normalized_cast = _normalize_liuyao_cast(cast)
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
            comparisons=(
                {"capability_id": "qimen", "requirement": "required"},
                {"capability_id": "liuren", "requirement": "required"},
            ),
        ),
        facts={
            subject_ref: {
                "cast": normalized_cast,
                "event_datetime": normalized_datetime.isoformat(),
                # Wenshi dispatches the same event to Qimen and Liuren.
                # Liuren's v51 manifest names this slot
                # ``event_datetime_or_reference_datetime``; keep both
                # manifest-facing keys at this cross-art boundary so the
                # comparison Provider cannot silently fall back to now.
                "event_datetime_or_reference_datetime": normalized_datetime.isoformat(),
                "timezone": confirmed_timezone,
                "location": location,
                "time_basis_policy": _runtime_time_basis_policy(time_basis_policy),
                "zi_hour_policy": _runtime_zi_hour_policy(zi_hour_policy),
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            }
        },
    )


def _compile_event_art_prepare(
    *,
    action: str,
    expected_capability_id: str,
    query: str,
    subject_ref: str,
    event_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    time_basis_policy: str = "civil",
    zi_hour_policy: str = "midnight",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> Prepare:
    route = _route_for_compiler(
        action,
        expected_capability_id=expected_capability_id,
    )
    _validate_dimensions(dimension_ids, allowed=_EVENT_ART_DIMENSION_IDS)
    normalized_datetime = _normalize_datetime(event_datetime, confirmed_timezone)
    event_datetime_fact_id = (
        "event_datetime_or_reference_datetime"
        if expected_capability_id == "liuren"
        else "event_datetime"
    )
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=None,
            end=None,
        ),
        facts={
            subject_ref: {
                event_datetime_fact_id: normalized_datetime.isoformat(),
                "timezone": confirmed_timezone,
                "location": location,
                "time_basis_policy": _runtime_time_basis_policy(time_basis_policy),
                "zi_hour_policy": _runtime_zi_hour_policy(zi_hour_policy),
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            }
        },
    )


def compile_qimen_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    event_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    time_basis_policy: str = "civil",
    zi_hour_policy: str = "midnight",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> Prepare:
    return _compile_event_art_prepare(
        action=action,
        expected_capability_id="qimen",
        query=query,
        subject_ref=subject_ref,
        event_datetime=event_datetime,
        confirmed_timezone=confirmed_timezone,
        location=location,
        dimension_ids=dimension_ids,
        time_basis_policy=time_basis_policy,
        zi_hour_policy=zi_hour_policy,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
    )


def compile_liuren_prepare(
    *,
    action: str,
    query: str,
    subject_ref: str,
    event_datetime: datetime,
    confirmed_timezone: str,
    location: str,
    dimension_ids: tuple[str, ...],
    time_basis_policy: str = "civil",
    zi_hour_policy: str = "midnight",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> Prepare:
    return _compile_event_art_prepare(
        action=action,
        expected_capability_id="liuren",
        query=query,
        subject_ref=subject_ref,
        event_datetime=event_datetime,
        confirmed_timezone=confirmed_timezone,
        location=location,
        dimension_ids=dimension_ids,
        time_basis_policy=time_basis_policy,
        zi_hour_policy=zi_hour_policy,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
    )
