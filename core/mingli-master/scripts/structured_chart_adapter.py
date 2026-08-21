#!/usr/bin/env python3
"""Normalize complete user-provided charts without claiming recalculation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import adapter_validate


ADAPTER_NAME = "mingli-master.structured_chart_adapter"
ADAPTER_VERSION = "1.0.0"
FACT_STATUS = "validated_user_provided_chart"
FACT_SCOPE = "supplied_facts_only"
RULE_PROFILE = "user-provided-no-recalculation"

DEDICATED_ADAPTER_SYSTEMS = {
    "bazi", "fengshui", "liuren", "fortune", "physiognomy", "qimen", "san-shi/qimen", "selection",
}
ROUTE_ALIASES = {
    "liuyao": ("divination", "liuyao"),
    "meihua": ("divination", "meihua"),
    "divination/liuyao": ("divination", "liuyao"),
    "divination/meihua": ("divination", "meihua"),
    "san-shi/taiyi": ("taiyi", None),
}
SUPPORTED_SYSTEMS = {
    "ziwei", "xingming", "divination", "taiyi",
}
SOURCE_TYPES = {"user_text", "image_transcription", "user_file"}


def _canonical_route(route: str, raw: dict[str, Any]) -> tuple[str, str | None]:
    if route in DEDICATED_ADAPTER_SYSTEMS:
        raise ValueError(f"{route} must use its dedicated deterministic adapter")
    if route in ROUTE_ALIASES:
        return ROUTE_ALIASES[route]
    if route == "divination":
        subsystem = raw.get("subsystem")
        if subsystem not in {"liuyao", "meihua"}:
            raise ValueError("divination requires subsystem liuyao or meihua")
        return route, subsystem
    if route not in SUPPORTED_SYSTEMS:
        raise ValueError(f"unsupported system: {route}")
    return route, None


def _validate_provenance(raw: dict[str, Any]) -> dict[str, Any]:
    provenance = raw.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("missing provenance")
    if provenance.get("source_type") not in SOURCE_TYPES:
        raise ValueError("provenance source_type must be user_text, image_transcription, or user_file")
    if provenance.get("calculation_status") != "not_recalculated":
        raise ValueError("provenance calculation_status must be not_recalculated")
    if not str(provenance.get("raw_excerpt") or "").strip():
        raise ValueError("provenance raw_excerpt is required")
    uncertainties = provenance.get("uncertainties")
    if not isinstance(uncertainties, list):
        raise ValueError("provenance uncertainties must be a list")
    return provenance


def build_payload(route: str, raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("chart input must be a JSON object")
    system, subsystem = _canonical_route(route, raw)
    provenance = _validate_provenance(raw)
    calendar = raw.get("calendar_normalization")
    output = raw.get("output")
    if not isinstance(calendar, dict):
        raise ValueError("calendar_normalization must be an object")
    if not isinstance(output, dict):
        raise ValueError("output must be an object")

    payload: dict[str, Any] = {
        "schema_version": "mingli-structured-user-chart-v1",
        "system": system,
        "subsystem": subsystem,
        "fact_layer_status": FACT_STATUS,
        "fact_layer_scope": FACT_SCOPE,
        "adapter": {
            "name": ADAPTER_NAME,
            "version": ADAPTER_VERSION,
            "license_status": "user_provided",
            "rule_profile": RULE_PROFILE,
            "generated_at": "deterministic-user-input-normalization",
        },
        "input": {
            "provenance": provenance,
            "missing_or_ambiguous": list(provenance.get("uncertainties") or []),
        },
        "calendar_normalization": calendar,
        "output": output,
        "warnings": list(provenance.get("uncertainties") or []),
        "trace": [
            "accepted complete user-provided chart fields",
            "did not recalculate calendar, chart, plate, ephemeris, or casting arithmetic",
        ],
    }
    validation = adapter_validate.validate_payload(system, payload)
    if not validation["ok"]:
        raise ValueError("invalid structured chart: " + ", ".join(validation["codes"]))
    payload["validation"] = {
        "ok": True,
        "system": system,
        "validator": "mingli-master.adapter_validate",
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True)
    parser.add_argument("--file", required=True, help="Raw user-provided chart JSON")
    parser.add_argument("--output")
    args = parser.parse_args()

    raw = json.loads(Path(args.file).read_text(encoding="utf-8"))
    try:
        payload = build_payload(args.system, raw)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
