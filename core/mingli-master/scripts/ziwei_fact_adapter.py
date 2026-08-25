#!/usr/bin/env python3
"""Calculate a versioned Zi Wei Dou Shu fact layer with vendored iztro."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reading_engine import calendar_core, evidence_rules
from reading_engine.contracts import FactRef


ADAPTER_NAME = "mingli-master.ziwei_fact_adapter"
ADAPTER_VERSION = "1.2.0"
IZTRO_VERSION = "2.5.8"
RUNTIME = Path(__file__).with_name("ziwei_runtime.js")
NODE_RUNTIME_FLAGS = ("--jitless",)
IZTRO_SINGLE_TIMEOUT_SECONDS = 30
IZTRO_LARGE_HORIZON_THRESHOLD_DAYS = 31
IZTRO_HORIZON_BATCH_DAYS = 64
IZTRO_HORIZON_BATCH_WORKERS = 4
IZTRO_HORIZON_BATCH_TIMEOUT_SECONDS = 90
VENDOR = Path(__file__).resolve().parents[1] / "vendor" / f"iztro-{IZTRO_VERSION}"
YANG_STEMS = frozenset("甲丙戊庚壬")
TRANSFORMATION_EFFECTS = ("禄", "权", "科", "忌")
TRANSFORMATION_TABLE = {
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
SOURCE_LINEAGE = {
    "calculation": [
        {
            "pack": "ziwei/ziwei-doushu-quanshu",
            "role": "classical placement and temporal-rule source",
            "source_dependency_ids": [
                "ziwei.iztro.natal-palaces-stars-transformations",
                "ziwei.iztro.decadal-year-month-horoscope",
                "ziwei.iztro.leap-hour-major-limit-conventions",
            ],
        }
    ],
    "interpretation": [
        {
            "pack": "ziwei/taiwei-fu",
            "role": "applicable early classical adjudication after calculation",
            "calculation_authority": False,
        }
    ],
    "commentary_only": [
        {
            "pack": "ziwei/feixing-ziwei-doushu-yuanzhi",
            "role": "late observational commentary; never placement authority",
            "calculation_authority": False,
        }
    ],
}
SOURCE_ROLES = {
    "calculation_primary": ["ziwei/ziwei-doushu-quanshu"],
    "classical_adjudication": ["ziwei/taiwei-fu"],
    "late_observational_commentary": ["ziwei/feixing-ziwei-doushu-yuanzhi"],
}


def _source_lineage() -> dict[str, list[dict[str, Any]]]:
    return json.loads(json.dumps(SOURCE_LINEAGE, ensure_ascii=False))


def _vendor_provenance() -> dict[str, Any]:
    try:
        payload = json.loads((VENDOR / "PROVENANCE.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("invalid vendored iztro provenance") from exc
    if payload.get("version") != IZTRO_VERSION:
        raise RuntimeError("vendored iztro provenance version mismatch")
    return payload


def _normalize_gender(value: str) -> tuple[str, str]:
    normalized = str(value or "").strip().lower()
    if normalized in {"男", "male", "m"}:
        return "male", "男"
    if normalized in {"女", "female", "f"}:
        return "female", "女"
    raise ValueError("gender must be male/female or 男/女")


def _local_datetime(value: str, timezone_name: str) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {timezone_name}") from exc
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("civil datetime must be ISO-8601") from exc
    return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed.astimezone(zone)


def _run_iztro_payload(
    payload: Mapping[str, Any],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    completed = subprocess.run(
        ["node", *NODE_RUNTIME_FLAGS, str(RUNTIME)],
        input=json.dumps(payload, ensure_ascii=False),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "iztro runtime failed")
    chart = json.loads(completed.stdout)
    if not isinstance(chart, dict) or len(chart.get("palaces") or []) != 12:
        raise RuntimeError("iztro returned an incomplete chart")
    return chart


def _run_iztro(
    local: datetime,
    gender_zh: str,
    *,
    target_date: date | None = None,
    target_dates: list[date] | None = None,
    zi_hour_policy: str = "midnight",
) -> dict[str, Any]:
    if zi_hour_policy not in calendar_core.ZI_HOUR_POLICIES:
        raise ValueError(f"unsupported Zi-hour policy: {zi_hour_policy!r}")
    payload: dict[str, Any] = {
        "year": local.year,
        "month": local.month,
        "day": local.day,
        "hour": local.hour,
        "gender": gender_zh,
        "ziHourPolicy": zi_hour_policy,
    }
    if target_dates is not None:
        if target_date is not None:
            raise ValueError("use target_date or target_dates, not both")
        payload["targetDates"] = [item.isoformat() for item in target_dates]
    elif target_date is not None:
        payload["targetDate"] = (
            f"{target_date.year}-{target_date.month}-{target_date.day}"
        )
    target_values = list(payload.get("targetDates") or ())
    if len(target_values) <= IZTRO_LARGE_HORIZON_THRESHOLD_DAYS:
        return _run_iztro_payload(
            payload,
            timeout_seconds=IZTRO_SINGLE_TIMEOUT_SECONDS,
        )

    # A one-year exact horizon asks iztro to calculate every civil day. One
    # --jitless process exceeded even 90 seconds under admitted x86_64 QEMU.
    # Keep every target and every independent provider replay, but distribute
    # bounded 64-day shards over the four admitted vCPUs. Each child remains
    # fail-closed at 90 seconds; a 366-day horizon has at most two waves.
    batches = [
        target_values[index : index + IZTRO_HORIZON_BATCH_DAYS]
        for index in range(0, len(target_values), IZTRO_HORIZON_BATCH_DAYS)
    ]

    def run_batch(batch: list[str]) -> dict[str, Any]:
        batch_payload = dict(payload)
        batch_payload["targetDates"] = batch
        return _run_iztro_payload(
            batch_payload,
            timeout_seconds=IZTRO_HORIZON_BATCH_TIMEOUT_SECONDS,
        )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(IZTRO_HORIZON_BATCH_WORKERS, len(batches))
    ) as executor:
        charts = list(executor.map(run_batch, batches))

    requested: dict[str, Any] = {}
    for batch, chart in zip(batches, charts):
        snapshots = chart.get("requestedHoroscopes")
        if not isinstance(snapshots, dict) or set(snapshots) != set(batch):
            raise RuntimeError("iztro returned an incomplete requested horoscope shard")
        requested.update(snapshots)
    if set(requested) != set(target_values):
        raise RuntimeError("iztro returned an incomplete requested horoscope range")

    result = dict(charts[0])
    result["requestedHoroscopes"] = {
        target: requested[target] for target in target_values
    }
    return result


def _parse_horizon_month(value: str) -> tuple[int, int]:
    try:
        year_text, month_text = value.split("-", 1)
        year, month = int(year_text), int(month_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Ziwei month horizon must use YYYY-MM") from exc
    if not 1800 <= year <= 2199 or not 1 <= month <= 12:
        raise ValueError("Ziwei month horizon must be within 1800-01..2199-12")
    return year, month


def _iter_months(start: str, end: str) -> list[tuple[int, int]]:
    start_year, start_month = _parse_horizon_month(start)
    end_year, end_month = _parse_horizon_month(end)
    first = start_year * 12 + start_month - 1
    final = end_year * 12 + end_month - 1
    if first > final:
        raise ValueError("Ziwei month horizon start must not follow end")
    if final - first > 599:
        raise ValueError("Ziwei month horizon cannot exceed 600 months")
    return [(index // 12, index % 12 + 1) for index in range(first, final + 1)]


def _compact_horoscope_layer(layer: dict[str, Any] | None) -> dict[str, Any]:
    source = layer or {}
    return {
        key: source.get(key)
        for key in (
            "index",
            "name",
            "heavenlyStem",
            "earthlyBranch",
            "palaceNames",
            "mutagen",
            "stars",
            "yearlyDecStar",
        )
        if key in source
    }


def _major_limit_direction(year_stem: str, gender: str) -> str:
    is_yang = year_stem in YANG_STEMS
    return (
        "forward"
        if (is_yang and gender == "male") or (not is_yang and gender == "female")
        else "reverse"
    )


def _transformation_rows(
    heavenly_stem: str,
    *,
    natal_stars: list[dict[str, Any]],
    scope: str,
    source_dependency_id: str,
) -> list[dict[str, Any]]:
    star_names = TRANSFORMATION_TABLE.get(heavenly_stem)
    if star_names is None:
        raise RuntimeError(f"unsupported Ziwei transformation stem: {heavenly_stem!r}")
    locations: dict[str, list[dict[str, Any]]] = {}
    for star in natal_stars:
        name = str(star.get("name") or "")
        palace = str(star.get("palace") or "")
        if not name or not palace:
            continue
        row = {
            "palace": palace,
            "palace_branch": star.get("palace_branch"),
        }
        if row not in locations.setdefault(name, []):
            locations[name].append(row)
    rows: list[dict[str, Any]] = []
    for transformation, star_name in zip(TRANSFORMATION_EFFECTS, star_names):
        star_locations = locations.get(star_name) or []
        if len(star_locations) != 1:
            raise RuntimeError(
                f"Ziwei transformation star {star_name!r} has "
                f"{len(star_locations)} deterministic locations"
            )
        location = star_locations[0]
        rows.append(
            {
                "star": star_name,
                "transformation": transformation,
                "palace": location["palace"],
                "palace_branch": location["palace_branch"],
                "scope": scope,
                "source_dependency_id": source_dependency_id,
            }
        )
    return rows


def _runtime_natal_facts(
    chart: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    palaces = [
        {
            "index": palace.get("index"),
            "name": palace.get("name"),
            "earthlyBranch": palace.get("earthlyBranch"),
        }
        for palace in chart.get("palaces") or ()
        if isinstance(palace, dict)
    ]
    stars = [
        {
            **star,
            "palace": palace.get("name"),
            "palace_branch": palace.get("earthlyBranch"),
            "palace_index": palace.get("index"),
        }
        for palace in chart.get("palaces") or ()
        if isinstance(palace, dict)
        for field in ("majorStars", "minorStars", "adjectiveStars")
        for star in palace.get(field) or ()
        if isinstance(star, dict)
    ]
    if len(palaces) != 12 or not stars:
        raise RuntimeError("iztro runtime did not expose complete natal placement facts")
    return palaces, stars


def _enrich_temporal_layer(
    layer: dict[str, Any],
    *,
    natal_palaces: list[dict[str, Any]],
    natal_stars: list[dict[str, Any]],
) -> dict[str, Any]:
    stem = str(layer.get("heavenlyStem") or "")
    stars = tuple(str(item) for item in layer.get("mutagen") or ())
    expected = TRANSFORMATION_TABLE.get(stem)
    if expected is None or stars != expected:
        raise RuntimeError(
            f"iztro transformation table mismatch for heavenly stem {stem!r}"
        )
    palace_names = list(layer.get("palaceNames") or ())
    dynamic_stars = list(layer.get("stars") or ())
    if len(palace_names) != 12 or len(dynamic_stars) != 12:
        raise RuntimeError("iztro temporal layer must expose twelve palace slots")
    natal_by_index = {
        item.get("index"): item for item in natal_palaces if isinstance(item, dict)
    }
    palace_facts: list[dict[str, Any]] = []
    star_facts: list[dict[str, Any]] = []
    for index in range(12):
        natal = natal_by_index.get(index, {})
        slot_stars = [
            dict(item) for item in dynamic_stars[index] if isinstance(item, dict)
        ]
        palace_facts.append(
            {
                "index": index,
                "natal_palace": natal.get("name"),
                "natal_branch": natal.get("earthlyBranch"),
                "temporal_palace": palace_names[index],
                "dynamic_stars": slot_stars,
            }
        )
        star_facts.extend(
            {
                **item,
                "palace_index": index,
                "natal_palace": natal.get("name"),
                "natal_branch": natal.get("earthlyBranch"),
                "temporal_palace": palace_names[index],
                "palace": natal.get("name"),
                "palace_branch": natal.get("earthlyBranch"),
            }
            for item in slot_stars
        )
    transformation_rows = _transformation_rows(
        stem,
        natal_stars=natal_stars,
        scope=str(layer.get("name") or ""),
        source_dependency_id="ziwei.iztro.decadal-year-month-horoscope",
    )
    return {
        **layer,
        "palace_facts": palace_facts,
        "palace_assignments": [
            {
                **item,
                "chart_palace": {
                    "name": item["natal_palace"],
                    "branch": item["natal_branch"],
                },
            }
            for item in palace_facts
        ],
        "star_facts": star_facts,
        "transformation_facts": [
            {
                **item,
                "effect": item["transformation"],
                "natal_palaces": [item["palace"]] if item["palace"] else [],
            }
            for item in transformation_rows
        ],
        "fact_layer": "calculated_temporal_placement",
    }


def natal_fact_digest(chart_facts: dict[str, Any]) -> str:
    """Return the deterministic Ziwei birth-chart identity."""

    identity = {
        "schema_version": chart_facts.get("schema_version"),
        "system": chart_facts.get("system"),
        "input": (chart_facts.get("input") or {}).get("normalized_input"),
        "calendar_normalization": chart_facts.get("calendar_normalization"),
        "output": chart_facts.get("output"),
        "rule_profile": (chart_facts.get("adapter") or {}).get("rule_profile"),
        "dependency": (chart_facts.get("adapter") or {}).get("dependency"),
        "engine_contract": (chart_facts.get("adapter") or {}).get("engine_contract"),
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_target_fact_snapshot(
    chart_facts: dict[str, Any], target_date: str
) -> dict[str, Any]:
    """Calculate one exact Da-Xian/Liu-Nian/Liu-Yue snapshot."""

    if chart_facts.get("fact_layer_status") != "calculated_ziwei_chart_from_birth_datetime":
        raise ValueError("Ziwei target snapshot requires a calculated birth chart")
    try:
        target = date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError("Ziwei target date must use YYYY-MM-DD") from exc
    if not 1800 <= target.year <= 2199:
        raise ValueError("Ziwei target date must be within 1800-2199")
    raw = ((chart_facts.get("input") or {}).get("raw_user_input") or {})
    required = ("civil_datetime", "timezone", "location", "gender")
    if any(not raw.get(field) for field in required):
        raise ValueError("Ziwei target snapshot requires original birth inputs")
    local = _local_datetime(str(raw["civil_datetime"]), str(raw["timezone"]))
    _, gender_zh = _normalize_gender(str(raw["gender"]))
    zi_hour_policy = str(raw.get("zi_hour_policy") or "midnight")
    chart = _run_iztro(
        local,
        gender_zh,
        target_date=target,
        zi_hour_policy=zi_hour_policy,
    )
    snapshot = chart.get("requestedHoroscope")
    if not isinstance(snapshot, dict):
        raise RuntimeError("iztro did not return the requested horoscope snapshot")
    natal_palaces, natal_stars = _runtime_natal_facts(chart)
    layers = {
        "major_limit": _enrich_temporal_layer(
            _compact_horoscope_layer(snapshot.get("decadal")),
            natal_palaces=natal_palaces,
            natal_stars=natal_stars,
        ),
        "annual": _enrich_temporal_layer(
            _compact_horoscope_layer(snapshot.get("yearly")),
            natal_palaces=natal_palaces,
            natal_stars=natal_stars,
        ),
        "monthly": _enrich_temporal_layer(
            _compact_horoscope_layer(snapshot.get("monthly")),
            natal_palaces=natal_palaces,
            natal_stars=natal_stars,
        ),
    }
    palace_by_index = {
        item.get("index"): item for item in natal_palaces if isinstance(item, dict)
    }
    active_palace = palace_by_index.get(layers["major_limit"].get("index"), {})
    layers["major_limit"]["active_natal_palace"] = {
        "index": active_palace.get("index"),
        "name": active_palace.get("name"),
        "branch": active_palace.get("earthlyBranch"),
    }
    return {
        "schema_version": "mingli-ziwei-target-fact-v1",
        "target_date": target.isoformat(),
        "natal_fact_digest": natal_fact_digest(chart_facts),
        "major_limit": layers["major_limit"],
        "annual": layers["annual"],
        "monthly": layers["monthly"],
        "transformation_layers": {
            key: list(value["transformation_facts"])
            for key, value in layers.items()
        },
        "boundary_profile": {
            "horoscope_divide": "normal/lunar-new-year",
            "age_divide": "normal/nominal-age",
            "day_divide": "forward/late-Zi next-day only when requested",
        },
        "source_roles": dict(SOURCE_ROLES),
        "source_lineage": _source_lineage(),
        "interpretation_status": "facts_only",
    }


def _date_sequence(start: date, end_exclusive: date) -> list[date]:
    count = (end_exclusive - start).days
    if count <= 0:
        raise ValueError("Ziwei horizon start must precede end")
    if count > 366 * 120:
        raise ValueError("Ziwei horizon cannot exceed 120 civil years")
    return [start + timedelta(days=offset) for offset in range(count)]


def _layer_segments(
    targets: list[date],
    snapshots: dict[str, dict[str, Any]],
    *,
    source_key: str,
    output_key: str,
    natal_palaces: list[dict[str, Any]],
    natal_stars: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for target in targets:
        compact = _enrich_temporal_layer(
            _compact_horoscope_layer(
                (snapshots[target.isoformat()] or {}).get(source_key)
            ),
            natal_palaces=natal_palaces,
            natal_stars=natal_stars,
        )
        signature = json.dumps(
            compact,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if segments and segments[-1]["_signature"] == signature:
            segments[-1]["end_exclusive"] = (
                target + timedelta(days=1)
            ).isoformat()
            continue
        segments.append(
            {
                "start_inclusive": target.isoformat(),
                "end_exclusive": (target + timedelta(days=1)).isoformat(),
                output_key: compact,
                "transformations": list(compact.get("mutagen") or ()),
                "transformation_facts": list(
                    compact.get("transformation_facts") or ()
                ),
                "_signature": signature,
            }
        )
    for segment in segments:
        segment.pop("_signature")
    return segments


def build_horizon_fact_extensions(
    chart_facts: dict[str, Any],
    *,
    horizon: dict[str, Any],
) -> dict[str, Any]:
    """Calculate requested Ziwei Da-Xian/Liu-Nian/Liu-Yue layers with iztro."""

    if chart_facts.get("fact_layer_status") != "calculated_ziwei_chart_from_birth_datetime":
        raise ValueError("Ziwei horizon extension requires a calculated birth chart")
    raw = ((chart_facts.get("input") or {}).get("raw_user_input") or {})
    required = ("civil_datetime", "timezone", "location", "gender")
    if any(not raw.get(field) for field in required):
        raise ValueError("Ziwei horizon extension requires original birth inputs")
    local = _local_datetime(str(raw["civil_datetime"]), str(raw["timezone"]))
    _, gender_zh = _normalize_gender(str(raw["gender"]))
    zi_hour_policy = str(raw.get("zi_hour_policy") or "midnight")
    kind = str(horizon.get("kind") or "")
    requested_months: list[tuple[int, int]] = []
    if kind == "month":
        start = str(horizon.get("start") or "")
        end = str(horizon.get("end") or start)
        requested_months = _iter_months(start, end)
        first_year, first_month = requested_months[0]
        last_year, last_month = requested_months[-1]
        range_start = date(first_year, first_month, 1)
        range_end = (
            date(last_year + 1, 1, 1)
            if last_month == 12
            else date(last_year, last_month + 1, 1)
        )
        requested_target_date = str(horizon.get("target_date") or "")
        if requested_target_date:
            try:
                parsed_target_date = date.fromisoformat(requested_target_date)
            except ValueError as exc:
                raise ValueError(
                    "Ziwei month target_date must use YYYY-MM-DD"
                ) from exc
            if not range_start <= parsed_target_date < range_end:
                raise ValueError(
                    "Ziwei month target_date must fall inside the requested range"
                )
    elif kind == "year":
        try:
            start_year = int(str(horizon.get("start") or ""))
            end_year = int(str(horizon.get("end") or start_year))
        except ValueError as exc:
            raise ValueError("Ziwei year horizon must use YYYY") from exc
        if not 1800 <= start_year <= end_year <= 2199:
            raise ValueError("Ziwei year horizon must be an inclusive 1800-2199 range")
        range_start = date(start_year, 1, 1)
        range_end = date(end_year + 1, 1, 1)
    else:
        raise ValueError("Ziwei extension supports explicit year or month horizons")

    targets = _date_sequence(range_start, range_end)
    chart = _run_iztro(
        local,
        gender_zh,
        target_dates=targets,
        zi_hour_policy=zi_hour_policy,
    )
    snapshots = chart.get("requestedHoroscopes")
    if not isinstance(snapshots, dict) or set(snapshots) != {
        item.isoformat() for item in targets
    }:
        raise RuntimeError("iztro did not return the complete requested horoscope range")
    natal_palaces, natal_stars = _runtime_natal_facts(chart)

    annual_layers: dict[str, dict[str, Any]] = {}
    for year in range(range_start.year, range_end.year + 1):
        year_targets = [item for item in targets if item.year == year]
        if not year_targets:
            continue
        segments = _layer_segments(
            year_targets,
            snapshots,
            source_key="yearly",
            output_key="liu_nian",
            natal_palaces=natal_palaces,
            natal_stars=natal_stars,
        )
        first_layer = segments[0]["liu_nian"]
        annual_layers[str(year)] = {
            "year": year,
            "coverage_start": year_targets[0].isoformat(),
            "coverage_end_exclusive": (
                year_targets[-1] + timedelta(days=1)
            ).isoformat(),
            "segments": segments,
            "liu_nian": first_layer,
            "transformations": list(first_layer.get("mutagen") or ()),
            "representative_scope": "first exact segment; use segments for all dates",
        }
    monthly_layers: dict[str, dict[str, Any]] = {}
    for year, month in requested_months:
        key = f"{year:04d}-{month:02d}"
        month_targets = [
            item for item in targets if (item.year, item.month) == (year, month)
        ]
        segments = _layer_segments(
            month_targets,
            snapshots,
            source_key="monthly",
            output_key="liu_yue",
            natal_palaces=natal_palaces,
            natal_stars=natal_stars,
        )
        first_layer = segments[0]["liu_yue"]
        monthly_layers[key] = {
            "year": year,
            "month": month,
            "segments": segments,
            "liu_yue": first_layer,
            "transformations": list(first_layer.get("mutagen") or ()),
            "representative_scope": "first exact segment; use segments for all dates",
        }
    major_limit_segments = _layer_segments(
        targets,
        snapshots,
        source_key="decadal",
        output_key="major_limit",
        natal_palaces=natal_palaces,
        natal_stars=natal_stars,
    )
    first_major_limit = major_limit_segments[0]["major_limit"]
    return {
        "schema_version": "mingli-ziwei-temporal-fact-v1",
        "natal_fact_digest": natal_fact_digest(chart_facts),
        "active_major_limit": first_major_limit,
        "active_major_limit_segments": major_limit_segments,
        "annual_layers": annual_layers,
        "monthly_layers": monthly_layers,
        "calendar_coverage": {
            "status": "exact_daily_boundary_detection",
            "start_inclusive": range_start.isoformat(),
            "end_exclusive": range_end.isoformat(),
            "horoscope_divide": "normal/lunar-new-year",
            "age_divide": "normal/nominal-age",
            "requested_target_date": (
                requested_target_date if kind == "month" else ""
            ),
        },
        "source_roles": dict(SOURCE_ROLES),
        "source_lineage": _source_lineage(),
        "interpretation_status": "facts_only",
        "fact_layer_separation": {
            "calculation": "palace, star, and transformation placement only",
            "classical_interpretation": "current model adjudicates only from retrieved applicable evidence",
            "late_observation": "commentary only; never a calculation source",
        },
        "rule_trace": [
            {
                "rule_id": "ziwei.iztro-horoscope-v2.5.8",
                "source_dependency_id": "ziwei.iztro.decadal-year-month-horoscope",
                "operation": "vendored iztro horoscope API calculated every civil day and grouped exact Da Xian, Liu Nian, and Liu Yue boundary segments",
                "dependency": {"name": "iztro", "version": IZTRO_VERSION},
            }
        ],
    }


def _compact_palace(palace: dict[str, Any]) -> dict[str, Any]:
    return {
        key: palace.get(key)
        for key in (
            "index",
            "name",
            "isBodyPalace",
            "isOriginalPalace",
            "heavenlyStem",
            "earthlyBranch",
            "majorStars",
            "minorStars",
            "adjectiveStars",
            "changsheng12",
            "boshi12",
            "jiangqian12",
            "suiqian12",
            "decadal",
            "ages",
        )
    }


_ZIWEI_INTERPRETIVE_RULES = (
    ("TR-02", "入庙为奇 / 失度为虚", "star_brightness_present"),
    ("TR-04", "马遇空亡", "horse_with_void_marker"),
    ("TR-06", "日月反背 / 禄马交驰", "lu_ma_same_triangular_scope"),
    ("TR-07", "紫府辅弼", "emperor_with_assistants"),
    ("TR-08", "七杀破军 / 杀破狼", "sha_po_lang_major_stars"),
    ("TR-10", "魁钺同行", "kui_yue_same_triangular_scope"),
    ("TR-11", "太阳居午", "sun_in_noon_branch"),
    ("TR-12", "太阴居子", "moon_in_rat_branch"),
    ("TR-13", "太阳会文昌于官禄", "sun_wenchang_in_career_palace"),
    ("TR-14", "太阴会文曲于妻宫", "moon_wenqu_in_spouse_palace"),
)


def _ziwei_palace_name(value: object) -> str:
    return str(value or "").strip().removesuffix("宫")


def _ziwei_star_names(palace: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    for field in ("majorStars", "minorStars", "adjectiveStars"):
        for item in palace.get(field) or ():
            if isinstance(item, Mapping) and str(item.get("name") or ""):
                names.append(str(item["name"]))
    return names


def _ziwei_candidate_rule(
    rule_id: str,
    name: str,
    predicate: str,
    matched: bool,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "name": name,
        "predicate": predicate,
        "matched": matched,
        "status": (
            "predicate_matched_not_verdict"
            if matched
            else "predicate_not_matched"
        ),
        "hard_verdict": None,
        "verification_status": "unverified",
        "source_pack": "ziwei/taiwei-fu",
        "source_anchor": (
            "references/books/ziwei/taiwei-fu/rules.md#" + rule_id
        ),
        "source_dependency_id": (
            "ziwei.classical-adjudication.taiwei-fu-predicate"
        ),
        "details": dict(details),
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
            provider_id="mingli-master.ziwei.iztro",
            provider_version=ADAPTER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "ziwei":
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
                "source_dependency_id": "ziwei.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def _ziwei_interpretive_candidates(
    palaces: list[dict[str, Any]],
    transformations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Expose source-bound Ziwei predicates without interpreting them."""

    by_name = {
        _ziwei_palace_name(item.get("name")): item
        for item in palaces
        if isinstance(item, Mapping)
    }
    triad_roles = (
        ("life", "命"),
        ("opposite", "迁移"),
        ("wealth", "财帛"),
        ("career", "官禄"),
    )
    triad: list[dict[str, Any]] = []
    for role, palace_name in triad_roles:
        palace = by_name.get(palace_name)
        if palace is None:
            continue
        triad.append(
            {
                "role": role,
                "palace": palace.get("name"),
                "index": palace.get("index"),
                "branch": palace.get("earthlyBranch"),
                "major_stars": [
                    str(item.get("name"))
                    for item in palace.get("majorStars") or ()
                    if isinstance(item, Mapping) and item.get("name")
                ],
                "minor_stars": [
                    str(item.get("name"))
                    for item in palace.get("minorStars") or ()
                    if isinstance(item, Mapping) and item.get("name")
                ],
                "adjective_stars": [
                    str(item.get("name"))
                    for item in palace.get("adjectiveStars") or ()
                    if isinstance(item, Mapping) and item.get("name")
                ],
                "brightness": [
                    {
                        "star": str(item.get("name")),
                        "brightness": item.get("brightness"),
                    }
                    for field in ("majorStars", "minorStars", "adjectiveStars")
                    for item in palace.get(field) or ()
                    if isinstance(item, Mapping)
                    and item.get("name")
                    and item.get("brightness")
                ],
            }
        )
    triad_names = {
        _ziwei_palace_name(item.get("palace")) for item in triad
    }
    triad_stars = {
        star
        for item in triad
        for field in ("major_stars", "minor_stars", "adjective_stars")
        for star in item.get(field) or ()
    }
    career = by_name.get("官禄", {})
    spouse = by_name.get("夫妻", {})
    noon_sun = any(
        "太阳" in _ziwei_star_names(item)
        and str(item.get("earthlyBranch") or "") == "午"
        for item in palaces
    )
    rat_moon = any(
        "太阴" in _ziwei_star_names(item)
        and str(item.get("earthlyBranch") or "") == "子"
        for item in palaces
    )
    horse_void = [
        item.get("name")
        for item in palaces
        if "天马" in _ziwei_star_names(item)
        and ({"旬空", "空亡"} & set(_ziwei_star_names(item)))
    ]
    evaluated = [
        _ziwei_candidate_rule(
            "TR-02",
            "入庙为奇 / 失度为虚",
            "star_brightness_present",
            any(item.get("brightness") for item in triad),
            {
                "scope": "命宫三方四正",
                "triad_palaces": sorted(triad_names),
            },
        ),
        _ziwei_candidate_rule(
            "TR-04",
            "马遇空亡",
            "horse_with_void_marker",
            bool(horse_void),
            {"matched_palaces": horse_void},
        ),
        _ziwei_candidate_rule(
            "TR-06",
            "日月反背 / 禄马交驰",
            "lu_ma_same_triangular_scope",
            {"禄存", "天马"} <= triad_stars,
            {
                "required_stars": ["禄存", "天马"],
                "matched_stars": sorted({"禄存", "天马"} & triad_stars),
                "scope": "命宫三方四正",
            },
        ),
        _ziwei_candidate_rule(
            "TR-07",
            "紫府辅弼",
            "emperor_with_assistants",
            bool({"紫微", "天府"} & triad_stars)
            and bool({"左辅", "右弼"} & triad_stars),
            {
                "emperor_stars": sorted({"紫微", "天府"} & triad_stars),
                "assistant_stars": sorted({"左辅", "右弼"} & triad_stars),
                "scope": "命宫三方四正",
            },
        ),
        _ziwei_candidate_rule(
            "TR-08",
            "七杀破军 / 杀破狼",
            "sha_po_lang_major_stars",
            {"七杀", "破军", "贪狼"} <= triad_stars,
            {
                "required_stars": ["七杀", "破军", "贪狼"],
                "matched_stars": sorted({"七杀", "破军", "贪狼"} & triad_stars),
                "scope": "命宫三方四正",
            },
        ),
        _ziwei_candidate_rule(
            "TR-10",
            "魁钺同行",
            "kui_yue_same_triangular_scope",
            {"天魁", "天钺"} <= triad_stars,
            {
                "required_stars": ["天魁", "天钺"],
                "matched_stars": sorted({"天魁", "天钺"} & triad_stars),
                "scope": "命宫三方四正",
            },
        ),
        _ziwei_candidate_rule(
            "TR-11",
            "太阳居午",
            "sun_in_noon_branch",
            noon_sun,
            {"matched": noon_sun},
        ),
        _ziwei_candidate_rule(
            "TR-12",
            "太阴居子",
            "moon_in_rat_branch",
            rat_moon,
            {"matched": rat_moon},
        ),
        _ziwei_candidate_rule(
            "TR-13",
            "太阳会文昌于官禄",
            "sun_wenchang_in_career_palace",
            {"太阳", "文昌"} <= set(_ziwei_star_names(career)),
            {"palace": career.get("name")},
        ),
        _ziwei_candidate_rule(
            "TR-14",
            "太阴会文曲于妻宫",
            "moon_wenqu_in_spouse_palace",
            {"太阴", "文曲"} <= set(_ziwei_star_names(spouse)),
            {"palace": spouse.get("name")},
        ),
    ]
    triad_transformations = [
        dict(item)
        for item in transformations
        if _ziwei_palace_name(item.get("palace")) in triad_names
    ]
    return {
        "schema_version": "mingli-ziwei-interpretive-candidates-v1",
        "status": "candidate_only",
        "hard_verdict": None,
        "life_palace": next(
            (item for item in triad if item.get("role") == "life"),
            None,
        ),
        "san_fang_si_zheng": triad,
        "transformation_facts": triad_transformations,
        "evaluated_rules": evaluated,
        "matched_rules": [item for item in evaluated if item["matched"]],
        "source_rules": [
            {
                "pack": "ziwei/ziwei-doushu-quanshu",
                "procedure_id": "P-ZW-02",
                "role": "palace_and_san_fang_si_zheng_candidate",
                "verification_status": "procedure_dependency_unverified",
            },
            {
                "pack": "ziwei/taiwei-fu",
                "rule_ids": [item[0] for item in _ZIWEI_INTERPRETIVE_RULES],
                "role": "classical_predicate_candidates",
                "verification_status": "unverified",
            },
        ],
        "source_dependency_ids": [
            "ziwei.iztro.natal-palaces-stars-transformations",
            "ziwei.classical-adjudication.taiwei-fu-predicate",
        ],
        "requires_classical_adjudication": True,
        "boundary": (
            "命宫三方四正、亮度、四化和古籍谓词只表示盘面候选；"
            "不生成富贵、疾病、婚姻、职业、寿命或具体年份硬断"
        ),
    }


_SCHOOL_NOTE = "Ziwei schools may differ in star brightness, transformations, and late-Zi policy"


def _ziwei_missing_or_ambiguous(time_basis_policy: str, longitude: float | None) -> list[str]:
    if time_basis_policy == "civil":
        base = (
            ["true solar time not applied"]
            if longitude is None
            else ["equation-of-time apparent-solar correction not applied"]
        )
    elif time_basis_policy == "longitude_mean_solar-v1":
        base = ["equation-of-time apparent-solar correction not applied"]
    else:  # local_apparent_solar-v1
        base = []
    return [*base, _SCHOOL_NOTE]


def _ziwei_blocked_capabilities(time_basis_policy: str) -> list[str]:
    # true_solar_time_verified_hour is only blocked when apparent-solar was NOT applied.
    blocked = ["school_independent_consensus"]
    if time_basis_policy != "local_apparent_solar-v1":
        blocked.append("true_solar_time_verified_hour")
    return blocked


def _ziwei_time_warning(time_basis_policy: str) -> str:
    if time_basis_policy == "civil":
        return "True solar time was not applied."
    if time_basis_policy == "longitude_mean_solar-v1":
        return (
            "Longitude mean-solar correction was applied; equation-of-time "
            "apparent-solar correction remains unapplied."
        )
    return (
        "Longitude and equation-of-time apparent-solar (true solar time) "
        "correction was applied."
    )


def build_from_birth(
    civil_datetime: str,
    *,
    timezone_name: str,
    location: str,
    gender: str,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    coordinate_accuracy_meters: float | None = None,
    zi_hour_policy: str = "midnight",
    time_basis_policy: str = "civil",
) -> dict[str, Any]:
    if not str(location or "").strip():
        raise ValueError("location is required")
    calendar = calendar_core.normalize_calendar(
        civil_datetime,
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        coordinate_accuracy_meters=coordinate_accuracy_meters,
        zi_hour_policy=zi_hour_policy,
        time_basis_policy=time_basis_policy,
    )
    local = datetime.fromisoformat(calendar["civil_datetime"])
    effective = datetime.fromisoformat(calendar["effective_datetime"])
    gender_en, gender_zh = _normalize_gender(gender)
    # The chart is cast for the policy-corrected effective instant (apparent
    # solar time when requested); the civil input is retained for display.
    chart = _run_iztro(effective, gender_zh, zi_hour_policy=zi_hour_policy)
    palaces = [_compact_palace(palace) for palace in chart["palaces"]]
    stars = [
        {
            **star,
            "palace": palace["name"],
            "palace_branch": palace["earthlyBranch"],
            "palace_index": palace["index"],
        }
        for palace in palaces
        for field in ("majorStars", "minorStars", "adjectiveStars")
        for star in palace.get(field) or []
    ]
    sihua = [
        {
            "star": star["name"],
            "mutagen": star["mutagen"],
            "palace": star["palace"],
        }
        for star in stars
        if star.get("mutagen")
    ]
    ganzhi_values = str(chart.get("chineseDate") or "").split()
    if len(ganzhi_values) != 4:
        raise RuntimeError("iztro did not return four Chinese-date pillars")
    pillars = dict(zip(("year", "month", "day", "hour"), ganzhi_values))
    year_stem = pillars["year"][0]
    direction = _major_limit_direction(year_stem, gender_en)
    major_limits = [
        {
            "palace": palace["name"],
            "palace_index": palace["index"],
            "palace_branch": palace["earthlyBranch"],
            **(palace.get("decadal") or {}),
        }
        for palace in palaces
    ]
    major_limit_sequence = sorted(
        major_limits,
        key=lambda item: (item.get("range") or [10**9])[0],
    )
    for sequence, item in enumerate(major_limit_sequence, start=1):
        age_range = item.get("range") or [None, None]
        item.update(
            {
                "sequence": sequence,
                "age_start": age_range[0],
                "age_end": age_range[1],
                "direction": direction,
                "source_dependency_id": "ziwei.iztro.leap-hour-major-limit-conventions",
            }
        )
    runtime_convention = chart.get("runtimeConvention") or {}
    provenance = _vendor_provenance()
    natal_transformations = _transformation_rows(
        year_stem,
        natal_stars=stars,
        scope="natal",
        source_dependency_id="ziwei.iztro.natal-palaces-stars-transformations",
    )
    if {
        (item["star"], item["mutagen"], item["palace"])
        for item in sihua
    } != {
        (item["star"], item["transformation"], item["palace"])
        for item in natal_transformations
    }:
        raise RuntimeError("iztro natal transformations disagree with the stem table")
    engine_contract = {
        "name": "iztro",
        "version": IZTRO_VERSION,
        "license": provenance.get("license"),
        "config": {
            "algorithm": runtime_convention.get("algorithm"),
            "yearDivide": runtime_convention.get("yearDivide"),
            "ageDivide": runtime_convention.get("ageDivide"),
            "dayDivide": runtime_convention.get("dayDivide"),
            "horoscopeDivide": runtime_convention.get("horoscopeDivide"),
        },
        "fix_leap": runtime_convention.get("fixLeap"),
        "artifact_sha256": provenance.get("vendored_sha256"),
        "license_sha256": provenance.get("license_sha256"),
        "source_dependency_ids": [
            "ziwei.iztro.natal-palaces-stars-transformations",
            "ziwei.iztro.leap-hour-major-limit-conventions",
            "ziwei.iztro.decadal-year-month-horoscope",
        ],
    }
    payload = {
        "schema_version": "mingli-ziwei-fact-v1",
        "system": "ziwei",
        "fact_layer_status": "calculated_ziwei_chart_from_birth_datetime",
        "fact_layer_scope": "natal_timing",
        "adapter": {
            "name": ADAPTER_NAME,
            "version": ADAPTER_VERSION,
            "license_status": "MIT_vendored",
            "rule_profile": "iztro-default-v2.5.8/fix-leap/zh-CN",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runtime": "node",
            "dependency": {
                "name": "iztro",
                "version": IZTRO_VERSION,
                "provenance": f"vendor/iztro-{IZTRO_VERSION}/PROVENANCE.json",
            },
            "engine_contract": engine_contract,
        },
        "input": {
            "raw_user_input": {
                "civil_datetime": civil_datetime,
                "timezone": timezone_name,
                "location": location,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
                "gender": gender,
                "zi_hour_policy": zi_hour_policy,
                "time_basis_policy": time_basis_policy,
            },
            "normalized_input": {
                "civil_datetime": local.isoformat(timespec="seconds"),
                "timezone": timezone_name,
                "location": location,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source or "not_supplied",
                "gender": gender_en,
                "zi_hour_policy": zi_hour_policy,
                "time_basis_policy": time_basis_policy,
                "effective_datetime": effective.isoformat(timespec="seconds"),
                "hour_branch_policy": "iztro early-rat=0 late-rat=12",
                "ziwei_engine_input": {
                    "solar_date": f"{effective.year}-{effective.month}-{effective.day}",
                    "time_index": runtime_convention.get("timeIndex"),
                    "fix_leap": True,
                    "day_divide": runtime_convention.get("dayDivide"),
                },
            },
            "missing_or_ambiguous": _ziwei_missing_or_ambiguous(time_basis_policy, longitude),
        },
        "calendar_normalization": calendar,
        "output": {
            "palaces": palaces,
            "palace_facts": palaces,
            "ming_shen": {
                "ming_branch": chart.get("earthlyBranchOfSoulPalace"),
                "shen_branch": chart.get("earthlyBranchOfBodyPalace"),
                "soul_star": chart.get("soul"),
                "body_star": chart.get("body"),
            },
            "stars": stars,
            "star_facts": stars,
            "sihua": sihua,
            "natal_transformation_facts": natal_transformations,
            "transformation_layers": {"natal": natal_transformations},
            "interpretive_candidates": _ziwei_interpretive_candidates(
                palaces,
                natal_transformations,
            ),
            "source_conditioned_patterns": [],
            "major_limits": major_limits,
            "major_limit_sequence": major_limit_sequence,
            "major_limit_direction": {
                "year_stem": year_stem,
                "year_polarity": "yang" if year_stem in YANG_STEMS else "yin",
                "gender": gender_en,
                "direction": direction,
                "source_dependency_id": "ziwei.iztro.leap-hour-major-limit-conventions",
            },
            "major_limit_starting_age": (
                major_limit_sequence[0]["range"][0] if major_limit_sequence else None
            ),
            "five_elements_class": chart.get("fiveElementsClass"),
            "solar_date": chart.get("solarDate"),
            "lunar_date_display": chart.get("lunarDate"),
            "chinese_date": chart.get("chineseDate"),
            "time": chart.get("time"),
            "time_range": chart.get("timeRange"),
            "chart_convention": {
                "engine": {"name": "iztro", "version": IZTRO_VERSION},
                "algorithm": runtime_convention.get("algorithm"),
                "fix_leap": runtime_convention.get("fixLeap"),
                "year_divide": runtime_convention.get("yearDivide"),
                "horoscope_divide": runtime_convention.get("horoscopeDivide"),
                "age_divide": runtime_convention.get("ageDivide"),
                "day_divide": runtime_convention.get("dayDivide"),
                "time_index": runtime_convention.get("timeIndex"),
                "major_limit_direction_rule": "yang-male/yin-female forward; yin-male/yang-female reverse",
                "source_dependency_ids": [
                    "ziwei.iztro.natal-palaces-stars-transformations",
                    "ziwei.iztro.leap-hour-major-limit-conventions",
                ],
            },
            "source_roles": dict(SOURCE_ROLES),
            "source_lineage": _source_lineage(),
            "fact_layer_separation": {
                "calculation": "natal palace, star, brightness, transformation, and major-limit placement",
                "interpretation": "not emitted by the adapter",
            },
            "interpretation_status": "facts_only",
        },
        "source_lineage": _source_lineage(),
        "capabilities": {
            "allowed": ["natal_palace_interpretation", "major_limit_context"],
            "blocked": _ziwei_blocked_capabilities(time_basis_policy),
        },
        "warnings": [
            "This chart uses the pinned iztro default profile; another Ziwei school may differ.",
            _ziwei_time_warning(time_basis_policy),
        ],
        "trace": [
            "normalized the civil datetime in the declared timezone",
            "cast the twelve-palace chart on the policy-corrected effective instant with vendored iztro 2.5.8",
            "flattened palace stars, four transformations, and major limits",
        ],
    }
    payload["output"]["source_conditioned_patterns"] = _source_conditioned_patterns(
        {
            "calendar_normalization": calendar,
            "output": payload["output"],
        }
    )
    payload["natal_fact_digest"] = natal_fact_digest(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datetime", required=True, dest="civil_datetime")
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--coordinate-source")
    parser.add_argument("--coordinate-accuracy-meters", type=float)
    parser.add_argument(
        "--zi-hour-policy",
        choices=("midnight", "late-zi-next-day"),
        default="midnight",
    )
    parser.add_argument("--time-basis-policy", default="civil")
    parser.add_argument("--gender", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        payload = build_from_birth(
            args.civil_datetime,
            timezone_name=args.timezone,
            location=args.location,
            gender=args.gender,
            longitude=args.longitude,
            latitude=args.latitude,
            coordinate_source=args.coordinate_source,
            coordinate_accuracy_meters=args.coordinate_accuracy_meters,
            zi_hour_policy=args.zi_hour_policy,
            time_basis_policy=args.time_basis_policy,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
