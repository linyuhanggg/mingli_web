#!/usr/bin/env python3
"""Independent verifier for Mac mini local profile SLA envelopes."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

import prepared_inputs

NATIVE_SUMMARY_RE = re.compile(
    r"^summary: targets=(\d+) modules=(\d+) tests=(\d+) "
    r"failed_modules=(\d+) elapsed=(\d+(?:\.\d+)?)s$"
)


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


def _artifact_bytes(
    parent: Path,
    value: object,
    *,
    label: str,
    expected_name: str,
) -> bytes:
    if not isinstance(value, dict) or set(value) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        _fail(f"{label} artifact metadata is not exact")
    if value.get("path") != expected_name:
        _fail(f"{label} artifact path mismatch")
    path = parent / expected_name
    if path.is_symlink() or not path.is_file() or path.parent != parent:
        _fail(f"{label} artifact is absent or unsafe")
    raw = path.read_bytes()
    if value.get("size_bytes") != len(raw):
        _fail(f"{label} artifact size mismatch")
    if not hmac.compare_digest(
        str(value.get("sha256", "")), hashlib.sha256(raw).hexdigest()
    ):
        _fail(f"{label} artifact SHA-256 mismatch")
    return raw


def _native_summary(stdout: bytes) -> dict[str, object]:
    try:
        lines = stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise LocalVerificationError("native stdout is not UTF-8") from exc
    matches = [match for line in lines if (match := NATIVE_SUMMARY_RE.fullmatch(line))]
    if len(matches) != 1:
        _fail("native stdout lacks one authoritative summary")
    match = matches[0]
    return {
        "targets": int(match.group(1)),
        "modules": int(match.group(2)),
        "tests": int(match.group(3)),
        "failed_modules": int(match.group(4)),
        "elapsed_seconds": float(match.group(5)),
    }


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
    if report.get("prepared_inputs_path") != "prepared-inputs.json":
        _fail("prepared inputs path mismatch")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
        "prepared_inputs",
        "stdout",
        "stderr",
    }:
        _fail("native raw artifacts are incomplete")
    prepared_raw = _artifact_bytes(
        profile_report_path.parent,
        artifacts["prepared_inputs"],
        label="prepared inputs",
        expected_name="prepared-inputs.json",
    )
    if not hmac.compare_digest(
        hashlib.sha256(prepared_raw).hexdigest(),
        expected_prepared_inputs_sha256,
    ):
        _fail("prepared inputs artifact binding mismatch")
    try:
        inputs = prepared_inputs.load(
            profile_report_path.parent / "prepared-inputs.json",
            expected_prepared_inputs_sha256,
        )
    except prepared_inputs.PreparedInputsError as exc:
        raise LocalVerificationError(f"prepared inputs are invalid: {exc}") from exc

    stdout = _artifact_bytes(
        profile_report_path.parent,
        artifacts["stdout"],
        label="stdout",
        expected_name="native-release-regression.stdout",
    )
    stderr = _artifact_bytes(
        profile_report_path.parent,
        artifacts["stderr"],
        label="stderr",
        expected_name="native-release-regression.stderr",
    )
    raw_summary = _native_summary(stdout)
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
        if summary.get(key) != expected or raw_summary.get(key) != expected:
            _fail(f"native summary {key} mismatch")
    suite_elapsed = _number(summary.get("elapsed_seconds"), "suite elapsed")
    if suite_elapsed != raw_summary["elapsed_seconds"]:
        _fail("native summary does not match raw stdout")
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
    expected_argv = [
        str(inputs.native_python),
        "-B",
        str(inputs.runner_path),
        "--jobs",
        str(slots),
        "--research-root",
        str(inputs.research_root),
    ]
    timeout_seconds = _number(command.get("timeout_seconds"), "command timeout")
    if (
        command.get("argv") != expected_argv
        or command.get("cwd") != str(inputs.source_root)
        or command.get("slots") != slots
        or command.get("shell") is not False
        or not 0 < timeout_seconds <= limit
    ):
        _fail("native command contract mismatch")
    if command.get("stdout_sha256") != artifacts["stdout"]["sha256"]:
        _fail("native command stdout binding mismatch")
    if command.get("stderr_sha256") != artifacts["stderr"]["sha256"]:
        _fail("native command stderr binding mismatch")
    if hashlib.sha256(stdout).hexdigest() != command.get("stdout_sha256"):
        _fail("native stdout digest mismatch")
    if hashlib.sha256(stderr).hexdigest() != command.get("stderr_sha256"):
        _fail("native stderr digest mismatch")
    if "profile_elapsed_seconds" in report or "elapsed_seconds" in envelope:
        _fail("native evidence must not label pre-seal time as total profile elapsed")
    evidence_seal_elapsed = _number(
        envelope.get("evidence_seal_elapsed_seconds"),
        "evidence seal elapsed",
    )
    if not command_elapsed <= evidence_seal_elapsed <= limit:
        _fail("native evidence seal exceeded its wall-clock limit")
    if envelope.get("measurement_boundary") != (
        "post-semantic-verification-pre-evidence-seal"
    ):
        _fail("native evidence measurement boundary mismatch")
    if envelope.get("deadline_enforced_through_atomic_publication") is not True:
        _fail("native atomic publication deadline was not enforced")
    if (
        _number(envelope.get("command_elapsed_seconds"), "local command elapsed")
        != command_elapsed
    ):
        _fail("native local command elapsed mismatch")
    actual_report_sha256 = hashlib.sha256(report_raw).hexdigest()
    if not hmac.compare_digest(
        str(envelope.get("profile_report_sha256", "")),
        actual_report_sha256,
    ):
        _fail("native profile report SHA-256 mismatch")
    return {
        "profile": "native-full",
        "evidence_seal_elapsed_seconds": evidence_seal_elapsed,
        "prepared_inputs_sha256": expected_prepared_inputs_sha256,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-report", type=Path, required=True)
    parser.add_argument("--local-summary", type=Path, required=True)
    parser.add_argument("--prepared-inputs-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        verified = validate_native_run(
            args.profile_report.expanduser().absolute(),
            args.local_summary.expanduser().absolute(),
            expected_prepared_inputs_sha256=args.prepared_inputs_sha256,
        )
    except LocalVerificationError as exc:
        print(f"local verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(verified, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
