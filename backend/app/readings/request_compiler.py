from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.readings.capability_policy import ProductRoute, route_for_action
from app.readings.runtime_contracts import Prepare

_BAZI_DIMENSION_IDS = frozenset(
    {"overview", "state", "career", "relationship", "timing"}
)
_BAZI_PREVIEW_DIMENSION_IDS = frozenset({"overview", "state"})
_FORTUNE_DIMENSION_IDS = frozenset({"career"})
_LIUYAO_DIMENSION_IDS = frozenset({"career", "outcome", "timing"})
_LIUYAO_CAST_VALUES = frozenset({6, 7, 8, 9})


class RequestCompilationError(ValueError):
    """A product request cannot be compiled into a lawful Prepare command."""


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
    allowed = (
        _BAZI_PREVIEW_DIMENSION_IDS
        if action == "profile_preview"
        else _BAZI_DIMENSION_IDS
    )
    _validate_dimensions(dimension_ids, allowed=allowed)
    facts: dict[str, object] = {
        "birth_datetime_or_four_pillars": (profile.birth_datetime_or_four_pillars),
        "timezone": profile.timezone,
        "location": profile.location,
        "gender": profile.gender,
        "time_basis_policy": profile.time_basis_policy,
        "zi_hour_policy": profile.zi_hour_policy,
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
    return Prepare(
        query=query,
        intent=_intent(
            subject_ref=profile.subject_ref,
            route=route,
            dimension_ids=dimension_ids,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        ),
        facts={
            profile.subject_ref: {
                "birth_datetime": profile.birth_datetime,
                "timezone": profile.timezone,
                "location": profile.location,
                "gender": profile.gender,
                "reference_datetime": reference_datetime.isoformat(),
                "time_basis_policy": profile.time_basis_policy,
                "zi_hour_policy": profile.zi_hour_policy,
            }
        },
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
