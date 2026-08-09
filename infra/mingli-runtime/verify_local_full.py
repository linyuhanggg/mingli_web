#!/usr/bin/env python3
"""Independent verifier for Mac mini local profile SLA envelopes."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from pathlib import Path
from typing import Any, NoReturn


class LocalVerificationError(RuntimeError):
    """Local profile evidence does not satisfy its independent contract."""


def _fail(message: str) -> NoReturn:
    raise LocalVerificationError(message)


def _read_json(path: Path | None, label: str) -> tuple[dict[str, Any], bytes]:
    if path is None or path.is_symlink() or not path.is_file():
        _fail(f"{label} is absent or unsafe")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalVerificationError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _fail(f"{label} must be an object")
    return value, raw


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        _fail(f"{label} must be finite")
    return number


def validate_native_run(
    profile_report_path: Path,
    local_summary_path: Path | None,
    *,
    expected_prepared_inputs_sha256: str,
) -> dict[str, object]:
    report, report_raw = _read_json(profile_report_path, "native profile report")
    envelope, _ = _read_json(local_summary_path, "native local SLA envelope")
    if report.get("schema") != "mingli-native-full-report-v1":
        _fail("native profile report schema mismatch")
    if report.get("profile") != "native-full" or report.get("status") != "passed":
        _fail("native profile status mismatch")
    if not hmac.compare_digest(
        str(report.get("prepared_inputs_sha256", "")),
        expected_prepared_inputs_sha256,
    ):
        _fail("prepared inputs binding mismatch")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        _fail("native summary is absent")
    expected_counts = {
        "targets": 126,
        "modules": 93,
        "tests": 1584,
        "failed_modules": 0,
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            _fail(f"native summary {key} mismatch")
    suite_elapsed = _number(summary.get("elapsed_seconds"), "suite elapsed")
    if not 0 <= suite_elapsed <= 600:
        _fail("native suite exceeded 600 seconds")

    command = report.get("command")
    if not isinstance(command, dict):
        _fail("native command evidence is absent")
    if (
        command.get("command_id") != "native-release-regression"
        or command.get("returncode") != 0
    ):
        _fail("native command did not pass")
    command_elapsed = _number(command.get("elapsed_seconds"), "command elapsed")
    if not 0 <= command_elapsed <= 600:
        _fail("native command exceeded 600 seconds")

    if envelope.get("schema") != "mingli-local-profile-sla-v1":
        _fail("native local SLA schema mismatch")
    if envelope.get("profile") != "native-full":
        _fail("native local SLA profile mismatch")
    if envelope.get("run_id") != report.get("run_id"):
        _fail("native local SLA run_id mismatch")
    limit = envelope.get("limit_seconds")
    slots = envelope.get("max_slots")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 600:
        _fail("native local SLA limit is invalid")
    if isinstance(slots, bool) or not isinstance(slots, int) or not 1 <= slots <= 10:
        _fail("native local SLA slots are invalid")
    if _number(envelope.get("elapsed_seconds"), "local elapsed") != command_elapsed:
        _fail("native local SLA elapsed mismatch")
    actual_report_sha256 = hashlib.sha256(report_raw).hexdigest()
    if not hmac.compare_digest(
        str(envelope.get("profile_report_sha256", "")),
        actual_report_sha256,
    ):
        _fail("native profile report SHA-256 mismatch")
    return {
        "profile": "native-full",
        "elapsed_seconds": command_elapsed,
        "prepared_inputs_sha256": expected_prepared_inputs_sha256,
    }
