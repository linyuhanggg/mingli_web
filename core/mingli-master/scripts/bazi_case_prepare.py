#!/usr/bin/env python3
"""Prepare answer-isolated external Bazi cases with explicit time policies."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from prediction_freeze import canonical_digest


LOCATION_TIMEZONE_PROFILES = (
    (("日本", "宫崎"), "Asia/Tokyo", "civil_japan_standard_time"),
    (("新加坡",), "Asia/Singapore", "civil_singapore_time"),
    (("馬來西亞", "马来西亚"), "Asia/Kuala_Lumpur", "civil_malaysia_time"),
    (("香港",), "Asia/Hong_Kong", "civil_hong_kong_time"),
    (("台湾", "臺灣"), "Asia/Taipei", "civil_taipei_time"),
    (("中国", "北京", "广东", "潮汕"), "Asia/Shanghai", "civil_china_standard_time"),
)
FORBIDDEN_KEYS = {
    "answer",
    "correct_option",
    "ground_truth",
    "observed_outcome",
    "outcome",
}
ADAPTER_PATH = Path(__file__).with_name("bazi_fact_adapter.py")


def _outcome_path(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).strip().lower()
            child_path = f"{path}.{raw_key}"
            if key in FORBIDDEN_KEYS:
                return child_path
            found = _outcome_path(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _outcome_path(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _base_result(case_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "prepared_schema": "mingli-prepared-bazi-case-v1",
        "case_id": case_input.get("case_id"),
        "system": "bazi",
        "source_person_id": case_input.get("source_person_id"),
        "question": case_input.get("question"),
        "options": case_input.get("options") or [],
    }


def _time_profile(place: str) -> dict[str, Any] | None:
    for tokens, timezone_name, basis in LOCATION_TIMEZONE_PROFILES:
        if any(token in place for token in tokens):
            return {
                "timezone": timezone_name,
                "basis": basis,
                "original_place": place,
            }
    return None


def _stable_facts(facts: dict[str, Any]) -> dict[str, Any]:
    stable = copy.deepcopy(facts)
    adapter = stable.get("adapter")
    if isinstance(adapter, dict):
        adapter.pop("generated_at", None)
    return stable


def _calculate_facts(
    civil_datetime: str,
    *,
    timezone_name: str,
    place: str,
    gender: str,
    zi_hour_policy: str = "midnight",
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(ADAPTER_PATH),
            "birth",
            "--datetime",
            civil_datetime,
            "--timezone",
            timezone_name,
            "--location",
            place,
            "--gender",
            gender,
            "--zi-hour-policy",
            zi_hour_policy,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode not in {0, 3}:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Bazi adapter failed: {message}")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("Bazi adapter returned a non-object payload")
    if completed.returncode == 3 or payload.get("conflicts"):
        raise ValueError("unexpected Bazi adapter conflict for benchmark birth data")
    return payload


def prepare_bazi_case(case_input: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(case_input, dict):
        raise TypeError("Bazi case input must be an object")
    leak_path = _outcome_path(case_input)
    if leak_path:
        raise ValueError(f"outcome-like field is forbidden in Bazi preparation: {leak_path}")
    if case_input.get("system") != "bazi":
        raise ValueError("Bazi case preparation requires system=bazi")
    result = _base_result(case_input)
    profile = case_input.get("birth_profile")
    if not isinstance(profile, dict):
        raise ValueError("Bazi case requires birth_profile")
    birth = profile.get("birth")
    gender = profile.get("gender")
    if not isinstance(birth, dict) or gender not in {"male", "female"}:
        raise ValueError("Bazi case birth profile is incomplete")

    place = str(birth.get("place") or "").strip()
    time_profile = _time_profile(place)
    if time_profile is None:
        result.update(
            {
                "preparation_status": "missing_timezone",
                "required_resolution": {
                    "field": "birth_timezone",
                    "original_place": place,
                    "reason": "location does not identify a supported civil timezone",
                },
            }
        )
        return result
    result["time_profile"] = time_profile

    try:
        year = int(birth["year"])
        month = int(birth["month"])
        day = int(birth["day"])
        hour = int(birth["hour"])
        minute = int(birth.get("minute") or 0)
        local_timezone = ZoneInfo(time_profile["timezone"])
        civil = datetime(
            year,
            month,
            day,
            hour,
            minute,
            tzinfo=local_timezone,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid Bazi birth fields: {exc}") from exc

    if hour == 23:
        result.update(
            {
                "preparation_status": "ambiguous_zi_hour_policy",
                "required_resolution": {
                    "field": "zi_hour_policy",
                    "candidate_policies": ["midnight", "late-zi-next-day"],
                    "reason": "the source dataset does not declare its late-Zi day-switch convention",
                },
            }
        )
        return result

    offset_datetime = civil.isoformat(timespec="seconds")
    offset = civil.strftime("%z")
    time_profile["civil_offset"] = f"{offset[:3]}:{offset[3:]}"
    facts = _calculate_facts(
        offset_datetime,
        timezone_name=time_profile["timezone"],
        place=place,
        gender=gender,
    )
    stable_facts = _stable_facts(facts)
    result.update(
        {
            "preparation_status": "calculated",
            "fact_snapshot": stable_facts,
            "facts_digest": canonical_digest(stable_facts),
            "source_birth_approximate": birth.get("approximate"),
            "prepared_at": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    return result
