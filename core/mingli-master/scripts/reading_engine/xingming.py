"""Deterministic Xingming/Qizheng Siyu facts over the shared ephemeris.

The module calculates astronomy and source-declared assignments only.  It does
not turn a position, transformation, or limit into a personal verdict.
"""

from __future__ import annotations

import copy
import calendar as civil_calendar
from datetime import date, datetime, timedelta, timezone
import math
from typing import Any, Iterator, Mapping

from . import calendar_core, ephemeris_core, evidence_rules
from .contracts import FactRef, canonical_digest


SCHEMA_VERSION = "mingli-xingming-facts-v1"
PROVIDER_VERSION = "1.1.0"
ADAPTER_VERSION = PROVIDER_VERSION
CONVENTION_PROFILE = "guolao-tropical-equal-house-v1"
HOUSE_PROFILE = "topocentric-equal-house-mingshen-opposition-v1"
PSEUDO_POINT_PROFILE = "guolao-explicit-separated-residual-points-v1"
TRANSFORMATION_PROFILE = "xingxue-ten-stem-transformations-v1"
LIMIT_PROFILE = "dongwei-bailiu-100y6m-v1"
STEMS = tuple("甲乙丙丁戊己庚辛壬癸")

HOUSE_NAMES = (
    "命宫",
    "财帛",
    "兄弟",
    "田宅",
    "男女",
    "奴仆",
    "妻妾",
    "疾厄",
    "迁移",
    "官禄",
    "福德",
    "相貌",
)
CLASSICAL_POINT_NAMES = (
    "太阳",
    "太阴",
    "金星",
    "木星",
    "水星",
    "火星",
    "土星",
    "计都",
    "罗睺",
    "紫炁",
    "月孛",
)
CLASSICAL_BODY_NAMES = CLASSICAL_POINT_NAMES
TRANSFORMATION_NAMES = (
    "天禄",
    "天暗",
    "天福",
    "天耗",
    "天荫",
    "天贵",
    "天刑",
    "天印",
    "天囚",
    "天权",
)
TRANSFORMATION_LABELS = TRANSFORMATION_NAMES
TRANSFORMATION_BODIES = (
    "火星",
    "月孛",
    "木星",
    "金星",
    "土星",
    "太阴",
    "水星",
    "紫炁",
    "计都",
    "罗睺",
)
ENGLISH_TO_CLASSICAL = {
    "Sun": "太阳",
    "Moon": "太阴",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
}
CLASSICAL_TO_ENGLISH = {value: key for key, value in ENGLISH_TO_CLASSICAL.items()}

# 《果老星宗》定行限度法 gives 100 years and 6 months in total.  "百六"
# is therefore not normalized to 106 years.
BAILIU_DURATIONS = {
    "命宫": 15.0,
    "财帛": 5.0,
    "兄弟": 5.0,
    "田宅": 4.5,
    "男女": 4.5,
    "奴仆": 4.5,
    "妻妾": 11.0,
    "疾厄": 7.0,
    "迁移": 8.0,
    "官禄": 15.0,
    "福德": 11.0,
    "相貌": 10.0,
}
BAILIU_TOTAL_YEARS = sum(BAILIU_DURATIONS.values())
BAILIU_SEQUENCE = (
    "命宫", "相貌", "福德", "官禄", "迁移", "疾厄",
    "妻妾", "奴仆", "男女", "田宅", "兄弟", "财帛",
)

ZI_QI_PROFILE = {
    "id": "xingxue-dated-mean-ziqi-v1",
    "period_days": 10228.0,
    "anchor_julian_day": 2280289.5,
    "anchor_longitude_degrees": 284.58,
    "source_anchor": "星学大成 fulltext L4753; 钮卫星 2015 p.417 引《大明嘉靖十年辛卯岁四余躔度》",
    "calibration_path": "references/matrices/xingming-ziqi-calibration-v1.yaml",
    "calibration_sha256": "6c1be027b753684907b7ac941bb48889efe0209b832770d9fc830f08967e56cc",
    "reconstruction_status": "source_formula_with_historical_dated_calibration",
    "precision_degrees": 0.01,
    "direction": "direct",
    "observed_body": False,
}


def _normalize_degree(value: float) -> float:
    result = float(value) % 360.0
    return 0.0 if result == 360.0 else result


def _signed_delta(after: float, before: float) -> float:
    return ((float(after) - float(before) + 180.0) % 360.0) - 180.0


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Xingming instant must carry an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def _astronomy() -> Any:
    return ephemeris_core._load_astronomy()


def _moon_longitude(astronomy: Any, time_value: Any) -> float:
    vector = astronomy.GeoVector(astronomy.Body.Moon, time_value, True)
    return _normalize_degree(float(astronomy.Ecliptic(vector).elon))


def _interpolate_longitude(
    start_longitude: float,
    end_longitude: float,
    fraction: float,
    *,
    direction: str,
) -> float:
    if direction == "retrograde":
        travel = -((float(start_longitude) - float(end_longitude)) % 360.0)
    else:
        travel = (float(end_longitude) - float(start_longitude)) % 360.0
    # Both lunar-node and apsidal events move only a few degrees per cycle;
    # reject a wrong-cycle wrap instead of silently accepting it.
    if abs(travel) > 30.0:
        travel = _signed_delta(end_longitude, start_longitude)
    return _normalize_degree(float(start_longitude) + travel * float(fraction))


def _surrounding_event_longitude(
    instant: datetime,
    *,
    kind: str,
) -> tuple[float, dict[str, Any]]:
    astronomy = _astronomy()
    target = astronomy.Time(instant.isoformat().replace("+00:00", "Z"))
    if kind == "descending_node":
        event = astronomy.SearchMoonNode(astronomy.Time(target.ut - 40.0))
        wanted = astronomy.NodeEventKind.Descending
        events = []
        while event.time.ut <= target.ut + 40.0:
            if event.kind == wanted:
                events.append(event)
            event = astronomy.NextMoonNode(event)
        direction = "retrograde"
        event_profile = "astronomy-engine-interpolated-descending-node-v1"
    elif kind == "lunar_apogee":
        event = astronomy.SearchLunarApsis(astronomy.Time(target.ut - 40.0))
        wanted = astronomy.ApsisKind.Apocenter
        events = []
        while event.time.ut <= target.ut + 40.0:
            if event.kind == wanted:
                events.append(event)
            event = astronomy.NextLunarApsis(event)
        direction = "direct"
        event_profile = "astronomy-engine-interpolated-lunar-apogee-v1"
    else:  # pragma: no cover - internal contract
        raise ValueError(f"unsupported lunar event: {kind}")
    previous = [event for event in events if event.time.ut <= target.ut]
    following = [event for event in events if event.time.ut > target.ut]
    if not previous or not following:
        raise RuntimeError(f"could not bracket {kind} around target instant")
    before = previous[-1]
    after = following[0]
    fraction = (target.ut - before.time.ut) / (after.time.ut - before.time.ut)
    before_longitude = _moon_longitude(astronomy, before.time)
    after_longitude = _moon_longitude(astronomy, after.time)
    value = _interpolate_longitude(
        before_longitude,
        after_longitude,
        fraction,
        direction=direction,
    )
    return value, {
        "profile": event_profile,
        "engine": "astronomy-engine",
        "engine_version": ephemeris_core.ENGINE_VERSION,
        "before_event_utc": str(before.time),
        "after_event_utc": str(after.time),
        "interpolation_fraction": round(float(fraction), 12),
        "direction": direction,
    }


def _ziqi_longitude(instant: datetime) -> float:
    unix_epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    julian_day = (
        (instant - unix_epoch).total_seconds() / 86400.0 + 2440587.5
    )
    elapsed_days = julian_day - float(ZI_QI_PROFILE["anchor_julian_day"])
    return _normalize_degree(
        float(ZI_QI_PROFILE["anchor_longitude_degrees"])
        + elapsed_days * 360.0 / float(ZI_QI_PROFILE["period_days"])
    )


def calculate_four_residuals(instant_utc: str) -> dict[str, dict[str, Any]]:
    """Calculate four residual points under separately named conventions."""

    instant = _parse_utc(instant_utc)
    luohou, node_trace = _surrounding_event_longitude(
        instant, kind="descending_node"
    )
    yuebo, apogee_trace = _surrounding_event_longitude(
        instant, kind="lunar_apogee"
    )
    return {
        "罗睺": {
            "longitude_degrees": luohou,
            "profile": node_trace["profile"],
            "point_kind": "calculated_lunar_node",
            "kind": "calculated_pseudo_point",
            "observed_body": False,
            "direction": "retrograde",
            "trace": node_trace,
        },
        "计都": {
            "longitude_degrees": _normalize_degree(luohou + 180.0),
            "profile": "ascending-node-opposed-to-luohou-v1",
            "point_kind": "calculated_lunar_node_opposition",
            "kind": "calculated_pseudo_point",
            "observed_body": False,
            "direction": "retrograde",
            "trace": {
                "operation": "exact opposition",
                "source_point": "罗睺",
                "separation_degrees": 180.0,
            },
        },
        "紫炁": {
            "longitude_degrees": _ziqi_longitude(instant),
            "profile": str(ZI_QI_PROFILE["id"]),
            "point_kind": "classical_mean_pseudo_point",
            "kind": "calculated_pseudo_point",
            "observed_body": False,
            "direction": "direct",
            "trace": copy.deepcopy(ZI_QI_PROFILE),
        },
        "月孛": {
            "longitude_degrees": yuebo,
            "profile": apogee_trace["profile"],
            "point_kind": "classical_mean_pseudo_point",
            "kind": "calculated_pseudo_point",
            "observed_body": False,
            "direction": "direct",
            "trace": apogee_trace,
        },
    }


def _mean_obliquity_degrees(time_value: Any) -> float:
    centuries = float(time_value.ut) / 36525.0
    arcseconds = (
        84381.448
        - 46.8150 * centuries
        - 0.00059 * centuries**2
        + 0.001813 * centuries**3
    )
    return arcseconds / 3600.0


def calculate_ming_degree(
    instant_utc: str,
    *,
    longitude: float,
    latitude: float,
) -> dict[str, Any]:
    """Return the eastern ecliptic/horizon intersection (ascendant)."""

    if not -180.0 <= float(longitude) <= 180.0:
        raise ValueError("longitude must be within -180..180")
    if not -90.0 < float(latitude) < 90.0:
        raise ValueError("latitude must be strictly within -90..90")
    astronomy = _astronomy()
    time_value = astronomy.Time(_parse_utc(instant_utc).isoformat().replace("+00:00", "Z"))
    local_sidereal = _normalize_degree(
        float(astronomy.SiderealTime(time_value)) * 15.0 + float(longitude)
    )
    obliquity = _mean_obliquity_degrees(time_value)
    theta = math.radians(local_sidereal)
    epsilon = math.radians(obliquity)
    phi = math.radians(float(latitude))
    western = math.degrees(
        math.atan2(
            -math.cos(theta),
            math.sin(theta) * math.cos(epsilon)
            + math.tan(phi) * math.sin(epsilon),
        )
    )
    ming = _normalize_degree(western + 180.0)
    return {
        "ming_degree": ming,
        "shen_degree": _normalize_degree(ming + 180.0),
        "separation_degrees": 180.0,
        "local_apparent_sidereal_degrees": local_sidereal,
        "mean_obliquity_of_date_degrees": obliquity,
        "longitude_degrees": float(longitude),
        "latitude_degrees": float(latitude),
        "profile": HOUSE_PROFILE,
        "source_dependency_id": "xingming.houses.topocentric-ming-degree",
        "fact_status": "calculated_not_interpreted",
    }


def calculate_houses(ming_degree: float) -> list[dict[str, Any]]:
    return [
        {
            "sequence": index + 1,
            "name": name,
            "start_degree": _normalize_degree(float(ming_degree) + index * 30.0),
            "end_degree": _normalize_degree(float(ming_degree) + (index + 1) * 30.0),
            "width_degrees": 30.0,
            "profile": HOUSE_PROFILE,
            "source_dependency_id": "xingming.houses.ming-shen-degrees",
            "fact_status": "calculated_not_interpreted",
        }
        for index, name in enumerate(HOUSE_NAMES)
    ]


def _house_for_longitude(longitude: float, ming_degree: float) -> tuple[str, int, float]:
    offset = _normalize_degree(float(longitude) - float(ming_degree))
    index = min(int(offset // 30.0), 11)
    return HOUSE_NAMES[index], index + 1, offset - index * 30.0


def calculate_transformations(year_stem: str) -> list[dict[str, Any]]:
    if year_stem not in STEMS:
        raise ValueError("Xingming transformations require one heavenly stem")
    offset = STEMS.index(year_stem)
    return [
        {
            "sequence": index + 1,
            "transformation": transformation,
            "label": transformation,
            "classical_body": TRANSFORMATION_BODIES[(offset + index) % 10],
            "body": TRANSFORMATION_BODIES[(offset + index) % 10],
            "year_stem": year_stem,
            "profile": TRANSFORMATION_PROFILE,
            "status": "calculated_assignment_not_verdict",
            "source_dependency_id": "xingming.transformations.ten-stem-table",
        }
        for index, transformation in enumerate(TRANSFORMATION_NAMES)
    ]


def calculate_bailiu_limits(ming_degree: float) -> list[dict[str, Any]]:
    age = 0.0
    rows: list[dict[str, Any]] = []
    house_index = {house: index for index, house in enumerate(HOUSE_NAMES)}
    for index, house in enumerate(BAILIU_SEQUENCE):
        duration = float(BAILIU_DURATIONS[house])
        zodiac_index = house_index[house]
        row = {
            "sequence": index + 1,
            "house": house,
            "age_start_years": age,
            "age_end_years": age + duration,
            "duration_years": duration,
            "start_degree": _normalize_degree(float(ming_degree) + zodiac_index * 30.0),
            "end_degree": _normalize_degree(float(ming_degree) + (zodiac_index + 1) * 30.0),
            "profile": LIMIT_PROFILE,
            "status": "calculated_limit_span_not_verdict",
            "source_dependency_id": "xingming.limits.dongwei-bailiu-table",
        }
        rows.append(row)
        age += duration
    if age != 100.5:  # pragma: no cover - guarded by fixed data and tests
        raise RuntimeError("Dongwei Bailiu durations do not total 100 years 6 months")
    return rows


def build_limit_layer(
    ming_degree: float,
    *,
    target_age_years: float | None = None,
) -> dict[str, Any]:
    limits = calculate_bailiu_limits(ming_degree)
    target: dict[str, Any] | None = None
    if target_age_years is not None:
        age = float(target_age_years)
        if age < 0.0:
            target = {
                "age_years": age,
                "house": None,
                "segment_index": None,
                "segment": None,
                "status": "not_applicable_before_birth",
            }
        elif age >= BAILIU_TOTAL_YEARS:
            target = {
                "age_years": age,
                "house": None,
                "segment_index": None,
                "segment": None,
                "status": "outside_source_table",
            }
        else:
            segment = next(
                row
                for row in limits
                if row["age_start_years"] <= age < row["age_end_years"]
            )
            target = {
                "age_years": age,
                "house": segment["house"],
                "segment_index": int(segment["sequence"]) - 1,
                "segment": copy.deepcopy(segment),
                "status": "calculated_limit_location_not_verdict",
            }
    return {
        "profile": LIMIT_PROFILE,
        "total_years": BAILIU_TOTAL_YEARS,
        "total_label": "100 years 6 months",
        "segments": limits,
        "target": target,
        "source_dependency_id": "xingming.limits.dongwei-bailiu-table",
    }


def _daily_motion(ephemeris: Mapping[str, Any]) -> dict[str, float]:
    instant = _parse_utc(str(ephemeris["instant_utc"]))
    later = ephemeris_core.calculate_ephemeris(
        (instant + timedelta(hours=6)).isoformat()
    )
    return {
        body: _signed_delta(
            float(later["positions"][body]["longitude_degrees"]),
            float(row["longitude_degrees"]),
        )
        * 4.0
        for body, row in dict(ephemeris["positions"]).items()
    }


def _motion_state(body: str, speed: float) -> str:
    if body in {"Sun", "Moon"}:
        return "direct"
    if abs(float(speed)) < 0.005:
        return "stationary"
    return "direct" if speed > 0 else "retrograde"


def _conventions() -> dict[str, Any]:
    return {
        "profile": CONVENTION_PROFILE,
        "version": "1.0.0",
        "zodiac": "tropical",
        "zodiac_frame": "tropical",
        "coordinate_frame": "geocentric_true_ecliptic_of_date",
        "body_coordinates": "geocentric_true_ecliptic_of_date",
        "observer_coordinates": "WGS84 longitude/latitude required for horizon facts",
        "precession": "equinox_of_date_by_astronomy_engine",
        "house_profile": HOUSE_PROFILE,
        "house_system": "equal_30_degrees_from_ascendant",
        "ming_degree": "astronomical_ascendant",
        "shen_degree": "exact_opposition_to_ming",
        "lunar_nodes": "descending_node_luohou_with_exact_opposing_ascending_jidu",
        "luoji_identity": "guolao-luohou-descending-jidu-ascending-v1",
        "pseudo_point_profile": PSEUDO_POINT_PROFILE,
        "ziqi": str(ZI_QI_PROFILE["id"]),
        "yuebo": "ephemeris_interpolated_lunar_apogee_v1",
        "mansion_mapping": {
            "status": "not_applied",
            "reason": "no source-verified fixed_star_boundary_catalog is selected; ancient fixed longitudes are not reused silently",
        },
        "limit_profile": LIMIT_PROFILE,
        "bailiu_total": "100 years 6 months",
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


def _source_conditioned_patterns(
    facts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose verified source predicates without turning them into verdicts."""

    indexed = {"chart_facts": dict(facts)}
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.xingming.v1",
            provider_version=PROVIDER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "xingming":
            continue
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
                "source_dependency_id": "xingming.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def _natal_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload["schema_version"],
        "system": payload["system"],
        "calendar_digest": payload["calendar_normalization"]["calendar_digest"],
        "ephemeris_digest": payload["ephemeris"]["ephemeris_digest"],
        "conventions": payload["conventions"],
        "output": payload["output"],
    }


def build_from_birth(
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
    convention_profile: str = CONVENTION_PROFILE,
    house_profile: str = HOUSE_PROFILE,
    pseudo_point_profile: str = PSEUDO_POINT_PROFILE,
) -> dict[str, Any]:
    if longitude is None or latitude is None:
        raise ValueError("Xingming requires longitude and latitude for a real house chart")
    if not str(coordinate_source or "").strip():
        raise ValueError("Xingming requires coordinate_source with longitude and latitude")
    if convention_profile != CONVENTION_PROFILE:
        raise ValueError(f"unsupported Xingming convention profile: {convention_profile}")
    if house_profile != HOUSE_PROFILE:
        raise ValueError(f"unsupported Xingming house profile: {house_profile}")
    if pseudo_point_profile != PSEUDO_POINT_PROFILE:
        raise ValueError(
            f"unsupported Xingming pseudo-point profile: {pseudo_point_profile}"
        )
    calendar = calendar_core.normalize_calendar(
        civil_datetime,
        timezone_name=timezone_name,
        location=location,
        longitude=float(longitude),
        latitude=float(latitude),
        coordinate_source=str(coordinate_source),
        coordinate_accuracy_meters=coordinate_accuracy_meters,
        zi_hour_policy=zi_hour_policy,
        time_basis_policy=time_basis_policy,
    )
    ephemeris = ephemeris_core.calculate_ephemeris(calendar)
    ming_shen = calculate_ming_degree(
        str(calendar["instant_utc"]),
        longitude=float(longitude),
        latitude=float(latitude),
    )
    houses = calculate_houses(float(ming_shen["ming_degree"]))
    residuals = calculate_four_residuals(str(calendar["instant_utc"]))
    motions = _daily_motion(ephemeris)
    positions: list[dict[str, Any]] = []
    for classical_name in CLASSICAL_POINT_NAMES:
        english_name = CLASSICAL_TO_ENGLISH.get(classical_name)
        if english_name:
            source = dict(ephemeris["positions"][english_name])
            longitude_value = float(source["longitude_degrees"])
            point_kind = "observed_ephemeris_body"
            observed = True
            kind = "observed_body"
            speed = float(motions[english_name])
            trace = {
                "ephemeris_digest": ephemeris["ephemeris_digest"],
                "engine": ephemeris["engine"],
            }
            source_dependency_id = "xingming.ephemeris.seven-luminaries"
        else:
            source = residuals[classical_name]
            longitude_value = float(source["longitude_degrees"])
            point_kind = str(source["point_kind"])
            observed = False
            kind = "calculated_pseudo_point"
            speed = 0.0
            trace = copy.deepcopy(source["trace"])
            source_dependency_id = "xingming.four-residuals.numeric-profiles"
        house, house_sequence, degree_in_house = _house_for_longitude(
            longitude_value, float(ming_shen["ming_degree"])
        )
        row = {
            "body": english_name or classical_name,
            "classical_name": classical_name,
            "longitude": longitude_value,
            "longitude_degrees": longitude_value,
            "degree_in_zodiac_sign": longitude_value % 30.0,
            "latitude_degrees": (
                float(source.get("latitude_degrees") or 0.0)
                if english_name
                else 0.0
            ),
            "house": house,
            "house_sequence": house_sequence,
            "degree_in_house": degree_in_house,
            "point_kind": point_kind,
            "kind": kind,
            "observed_body": observed,
            "daily_motion_degrees": speed,
            "motion_state": (
                _motion_state(english_name, speed)
                if english_name
                else str(source.get("direction") or "declared_mean_motion")
            ),
            "fact_status": "calculated_not_interpreted",
            "source_dependency_id": source_dependency_id,
            "trace": trace,
        }
        positions.append(row)
    year_stem = str(calendar["ganzhi"]["year"])[0]
    conventions = _conventions()
    output: dict[str, Any] = {
        "ephemeris": copy.deepcopy(ephemeris),
        "positions": positions,
        "classical_bodies": copy.deepcopy(positions),
        "houses": houses,
        "ming_shen": ming_shen,
        "ming_shen_degrees": copy.deepcopy(ming_shen),
        "transformations": calculate_transformations(year_stem),
        "major_limits": calculate_bailiu_limits(float(ming_shen["ming_degree"])),
        "conventions": copy.deepcopy(conventions),
        "interpretation_status": "facts_only",
    }
    output["source_conditioned_patterns"] = _source_conditioned_patterns(
        {
            "calendar_normalization": calendar,
            "output": output,
        }
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": "xingming",
        "fact_layer_status": "calculated_xingming_facts",
        "adapter": {
            "name": "mingli-master.xingming",
            "version": ADAPTER_VERSION,
            "rule_profile": CONVENTION_PROFILE,
        },
        "input": {
            "civil_datetime": str(civil_datetime),
            "timezone": str(timezone_name),
            "location": str(location),
            "longitude": float(longitude),
            "latitude": float(latitude),
            "coordinate_source": str(coordinate_source),
            "zi_hour_policy": str(zi_hour_policy),
            "time_basis_policy": str(time_basis_policy),
            "convention_profile": str(convention_profile),
            "house_profile": str(house_profile),
            "pseudo_point_profile": str(pseudo_point_profile),
        },
        "calendar_normalization": calendar,
        "ephemeris": ephemeris,
        "conventions": conventions,
        "output": output,
        "source_lineage": {
            "calculation": [
                {
                    "pack": "xingming/guotian-jing",
                    "role": "classical points, transformations, and Bailiu limit table",
                },
                {
                    "pack": "xingming/xingxue-dacheng",
                    "role": "twelve-house ordering, body/degree requirements, and house meanings",
                },
            ],
            "interpretation": [
                {
                    "pack": "xingming/xingming-suyuan",
                    "role": "cross-book adjudication only after deterministic facts",
                }
            ],
            "blocked": [
                "xingming/qizheng-siyu-tianjing",
                "xingming/qizheng-quanshu-dacheng",
                "xingming/minghai-quanbian",
            ],
        },
    }
    payload["natal_fact_digest"] = canonical_digest(_natal_identity(payload))
    report = validate_fact_layer(payload)
    if not report["ok"]:
        raise RuntimeError("Xingming fact validation failed: " + ", ".join(report["codes"]))
    return payload


def validate_fact_layer(payload: Mapping[str, Any]) -> dict[str, Any]:
    codes: list[str] = []
    try:
        expected_conventions = _conventions()
        if (
            dict(payload["conventions"]) != expected_conventions
            or dict(payload["output"]["conventions"]) != expected_conventions
        ):
            codes.append("xingming_convention_mismatch")
    except (KeyError, TypeError, ValueError):
        codes.append("xingming_convention_mismatch")
    try:
        calendar_core.validate_calendar_digest(dict(payload["calendar_normalization"]))
    except (KeyError, TypeError, ValueError):
        codes.append("xingming_calendar_digest_mismatch")
    try:
        ephemeris = dict(payload["ephemeris"])
        expected_ephemeris = ephemeris_core.calculate_ephemeris(
            dict(payload["calendar_normalization"])
        )
        if ephemeris != expected_ephemeris:
            codes.append("xingming_ephemeris_digest_mismatch")
        expected = build_from_components(
            dict(payload["calendar_normalization"]),
            expected_ephemeris,
        )
        actual_positions = list(payload["output"]["positions"])
        if actual_positions != expected["positions"]:
            codes.append("xingming_ephemeris_position_mismatch")
        if list(payload["output"]["houses"]) != expected["houses"]:
            codes.append("xingming_house_mismatch")
        if dict(payload["output"]["ming_shen"]) != expected["ming_shen"]:
            codes.append("xingming_ming_shen_opposition_mismatch")
        if list(payload["output"]["transformations"]) != expected["transformations"]:
            codes.append("xingming_transformation_mismatch")
        if list(payload["output"]["major_limits"]) != expected["major_limits"]:
            codes.append("xingming_bailiu_limit_mismatch")
        if (
            list(payload["output"].get("source_conditioned_patterns") or ())
            != expected["source_conditioned_patterns"]
        ):
            codes.append("xingming_source_pattern_mismatch")
    except (KeyError, TypeError, ValueError, RuntimeError):
        codes.append("xingming_fact_shape_invalid")
    try:
        supplied = str(payload["natal_fact_digest"])
        actual = canonical_digest(_natal_identity(payload))
        if supplied != actual:
            codes.append("xingming_natal_digest_mismatch")
    except (KeyError, TypeError):
        codes.append("xingming_natal_digest_missing")
    return {"ok": not codes, "codes": sorted(set(codes))}


def build_from_components(
    calendar: Mapping[str, Any],
    ephemeris: Mapping[str, Any],
) -> dict[str, Any]:
    """Independently rebuild validation-sensitive output rows."""

    observer = dict(calendar["location"])
    ming_shen = calculate_ming_degree(
        str(calendar["instant_utc"]),
        longitude=float(observer["longitude"]),
        latitude=float(observer["latitude"]),
    )
    houses = calculate_houses(float(ming_shen["ming_degree"]))
    residuals = calculate_four_residuals(str(calendar["instant_utc"]))
    motions = _daily_motion(ephemeris)
    positions: list[dict[str, Any]] = []
    for classical_name in CLASSICAL_POINT_NAMES:
        english_name = CLASSICAL_TO_ENGLISH.get(classical_name)
        if english_name:
            source = dict(ephemeris["positions"][english_name])
            longitude_value = float(source["longitude_degrees"])
            observed = True
            kind = "observed_body"
            point_kind = "observed_ephemeris_body"
            speed = float(motions[english_name])
            trace = {
                "ephemeris_digest": ephemeris["ephemeris_digest"],
                "engine": ephemeris["engine"],
            }
            source_dependency_id = "xingming.ephemeris.seven-luminaries"
        else:
            source = residuals[classical_name]
            longitude_value = float(source["longitude_degrees"])
            observed = False
            kind = "calculated_pseudo_point"
            point_kind = str(source["point_kind"])
            speed = 0.0
            trace = copy.deepcopy(source["trace"])
            source_dependency_id = "xingming.four-residuals.numeric-profiles"
        house, house_sequence, degree_in_house = _house_for_longitude(
            longitude_value, float(ming_shen["ming_degree"])
        )
        positions.append(
            {
                "body": english_name or classical_name,
                "classical_name": classical_name,
                "longitude": longitude_value,
                "longitude_degrees": longitude_value,
                "degree_in_zodiac_sign": longitude_value % 30.0,
                "latitude_degrees": (
                    float(source.get("latitude_degrees") or 0.0)
                    if english_name
                    else 0.0
                ),
                "house": house,
                "house_sequence": house_sequence,
                "degree_in_house": degree_in_house,
                "point_kind": point_kind,
                "kind": kind,
                "observed_body": observed,
                "daily_motion_degrees": speed,
                "motion_state": (
                    _motion_state(english_name, speed)
                    if english_name
                    else str(source.get("direction") or "declared_mean_motion")
                ),
                "fact_status": "calculated_not_interpreted",
                "source_dependency_id": source_dependency_id,
                "trace": trace,
            }
        )
    output = {
        "positions": positions,
        "houses": houses,
        "ming_shen": ming_shen,
        "transformations": calculate_transformations(str(calendar["ganzhi"]["year"])[0]),
        "major_limits": calculate_bailiu_limits(float(ming_shen["ming_degree"])),
    }
    output["source_conditioned_patterns"] = _source_conditioned_patterns(
        {
            "calendar_normalization": calendar,
            "output": output,
        }
    )
    return output


def _age_years(birth_date: date, target_date: date) -> float:
    return (target_date - birth_date).days / 365.2425


def _requested_years(horizon: Mapping[str, Any]) -> tuple[int, ...]:
    years = []
    for key in ("start", "end"):
        value = horizon.get(key)
        if value:
            years.append(int(str(value)[:4]))
    if not years:
        return ()
    first, last = min(years), max(years)
    if last - first > 120:
        raise ValueError("Xingming requested horizon exceeds the Bailiu table")
    return tuple(range(first, last + 1))


def _annual_transformations(
    facts: Mapping[str, Any],
    *,
    horizon: Mapping[str, Any],
) -> list[dict[str, Any]]:
    source_input = dict(facts["input"])
    rows: list[dict[str, Any]] = []
    for year in _requested_years(horizon):
        # July is unambiguously inside the post-Lichun Ganzhi year.  The shared
        # calendar remains the authority instead of duplicating a year formula.
        annual_calendar = calendar_core.normalize_calendar(
            f"{year:04d}-07-01T12:00:00",
            timezone_name=str(source_input["timezone"]),
            location=str(source_input["location"]),
            longitude=float(source_input["longitude"]),
            latitude=float(source_input["latitude"]),
            coordinate_source=str(source_input["coordinate_source"]),
            zi_hour_policy=str(source_input.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(source_input.get("time_basis_policy") or "civil"),
        )
        year_ganzhi = str(annual_calendar["ganzhi"]["year"])
        rows.append(
            {
                "year": year,
                "year_ganzhi": year_ganzhi,
                "transformations": calculate_transformations(year_ganzhi[0]),
                "calendar_digest": annual_calendar["calendar_digest"],
                "fact_status": "calculated_annual_assignments_not_verdict",
            }
        )
    return rows


def build_requested_limit_layers(
    facts: Mapping[str, Any],
    *,
    horizon: Mapping[str, Any],
) -> dict[str, Any]:
    ming = float(facts["output"]["ming_shen"]["ming_degree"])
    birth = date.fromisoformat(str(facts["calendar_normalization"]["solar_date"]))
    points: list[date] = []
    for key in ("start", "end"):
        raw = horizon.get(key)
        if raw:
            text = str(raw)
            if len(text) == 4:
                text += "-01-01" if key == "start" else "-12-31"
            elif len(text) == 7:
                if key == "start":
                    text += "-01"
                else:
                    year, month = (int(item) for item in text.split("-"))
                    text += f"-{civil_calendar.monthrange(year, month)[1]:02d}"
            points.append(date.fromisoformat(text))
    if not points:
        return build_limit_layer(ming)
    rows = []
    for point in sorted(set(points)):
        age = _age_years(birth, point)
        layer = build_limit_layer(ming, target_age_years=age)
        rows.append({"date": point.isoformat(), **dict(layer["target"] or {})})
    return {
        "profile": LIMIT_PROFILE,
        "total_years": BAILIU_TOTAL_YEARS,
        "requested_limit_layers": rows,
        "segments": calculate_bailiu_limits(ming),
    }


def build_horizon_fact_extension(
    facts: Mapping[str, Any],
    *,
    horizon: Mapping[str, Any],
) -> dict[str, Any]:
    """Map requested dates to Bailiu limits without mutating natal facts."""

    layer = build_requested_limit_layers(facts, horizon=horizon)
    return {
        "limit_profile": LIMIT_PROFILE,
        "requested_limit_layers": copy.deepcopy(
            layer.get("requested_limit_layers") or []
        ),
        "annual_transformations": _annual_transformations(
            facts,
            horizon=horizon,
        ),
        "major_limits": copy.deepcopy(
            layer.get("segments") or facts["output"]["major_limits"]
        ),
        "requested_horizon": copy.deepcopy(dict(horizon)),
        "fact_status": "calculated_limit_location_not_verdict",
        "rule_trace": [
            {
                "rule_id": "xingming.dongwei-bailiu-requested-horizon-v1",
                "source_dependency_id": "xingming.limits.dongwei-bailiu-table",
                "operation": "map requested dates to the source-verified 100-year-6-month Bailiu table",
            },
            {
                "rule_id": "xingming.requested-year-transformations-v1",
                "source_dependency_id": "xingming.transformations.ten-stem-table",
                "operation": "derive each requested year's Ganzhi through the shared calendar and bind its ten transformations",
            },
        ],
    }


__all__ = [
    "ADAPTER_VERSION",
    "BAILIU_TOTAL_YEARS",
    "CLASSICAL_BODY_NAMES",
    "CLASSICAL_POINT_NAMES",
    "HOUSE_NAMES",
    "LIMIT_PROFILE",
    "PSEUDO_POINT_PROFILE",
    "PROVIDER_VERSION",
    "TRANSFORMATION_LABELS",
    "build_from_birth",
    "build_horizon_fact_extension",
    "build_limit_layer",
    "build_requested_limit_layers",
    "calculate_bailiu_limits",
    "calculate_four_residuals",
    "calculate_transformations",
    "validate_fact_layer",
]
