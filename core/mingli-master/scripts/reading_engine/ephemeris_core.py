"""Versioned Astronomy Engine service for deterministic Xingming facts."""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from .calendar_core import validate_calendar_digest


SCHEMA_VERSION = "mingli-ephemeris-v1"
ENGINE_VERSION = "2.1.19"
ENGINE = {
    "name": "astronomy-engine",
    "version": ENGINE_VERSION,
    "license": "MIT",
    "provenance": "vendor/astronomy-engine-2.1.19/PROVENANCE.json",
    "distribution_sha256": "95b797b87b659adc0602a6a205143ce5a10451664e80650bb7cd8ba3c8f1f02b",
    "license_sha256": "b4d9dd0fd80fce3879c4cd9e3754364f74fc5ec046f33276475ba3876785c8b7",
    "data_files": [],
    "data_model": "versioned_coefficients_embedded_in_distribution",
}
BODY_NAMES = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _load_astronomy() -> Any:
    try:
        import astronomy  # type: ignore
    except Exception as exc:  # pragma: no cover - platform-specific import failure
        raise RuntimeError(
            f"astronomy-engine missing: {exc}. Install the pinned runtime requirements."
        ) from exc
    actual = importlib.metadata.version("astronomy-engine")
    if actual != ENGINE_VERSION:
        raise RuntimeError(
            f"astronomy-engine version mismatch: expected {ENGINE_VERSION}, got {actual}"
        )
    return astronomy


def _parse_instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("ephemeris instant must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("ephemeris instant must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def calculate_ephemeris(
    calendar_or_instant: Mapping[str, Any] | str | None = None,
    *,
    instant: str | None = None,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> dict[str, Any]:
    """Calculate true ecliptic-of-date longitudes with a pinned engine."""

    if calendar_or_instant is None:
        calendar_or_instant = instant
    if calendar_or_instant is None:
        raise ValueError("ephemeris requires a calendar result or instant")
    calendar_binding: str | None = None
    if isinstance(calendar_or_instant, Mapping):
        calendar = dict(calendar_or_instant)
        calendar_binding = validate_calendar_digest(calendar)
        instant_utc = _parse_instant(str(calendar["instant_utc"]))
        observer = dict(calendar.get("location") or {})
        longitude = observer.get("longitude")
        latitude = observer.get("latitude")
        coordinate_source = observer.get("coordinate_source")
    else:
        instant_utc = _parse_instant(str(calendar_or_instant))
        observer = {
            "longitude": longitude,
            "latitude": latitude,
            "coordinate_source": coordinate_source or "not_supplied",
        }
    if longitude is not None and not -180 <= float(longitude) <= 180:
        raise ValueError("longitude must be within -180..180")
    if latitude is not None and not -90 <= float(latitude) <= 90:
        raise ValueError("latitude must be within -90..90")

    astronomy = _load_astronomy()
    time_value = astronomy.Time(
        instant_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    positions: dict[str, dict[str, float | str]] = {}
    for name in BODY_NAMES:
        vector = astronomy.GeoVector(getattr(astronomy.Body, name), time_value, True)
        ecliptic = astronomy.Ecliptic(vector)
        positions[name] = {
            "body": name,
            "longitude_degrees": float(ecliptic.elon),
            "latitude_degrees": float(ecliptic.elat),
        }
    convention = {
        "frame": "geocentric_true_ecliptic_of_date",
        "zodiac": "tropical",
        "aberration": True,
        "precession": "equinox_of_date_by_astronomy_engine",
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "instant_utc": instant_utc.isoformat(timespec="seconds"),
        "calendar_digest": calendar_binding,
        "observer": {
            "longitude": float(longitude) if longitude is not None else None,
            "latitude": float(latitude) if latitude is not None else None,
            "coordinate_source": str(coordinate_source or "not_supplied"),
        },
        "engine": copy.deepcopy(ENGINE),
        "coordinate_convention": convention,
        "convention": convention,
        "positions": positions,
    }
    digest = _digest(payload)
    payload["ephemeris_digest"] = digest
    payload["digest"] = digest
    return payload
