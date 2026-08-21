"""Ephemeral, run-scoped sharing for duplicate live audit assertions.

The cache exists only while ``run_test_suite.py`` is alive.  It is never a
release artifact and never survives into a later run.  Missing or failed
entries fall back to a fresh audit, so standalone tests keep their strength.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping


SESSION_ENV = "MINGLI_TEST_SESSION_DIR"
MATRIX_EXPECTED_ENV = "MINGLI_MATRIX_SESSION_EXPECTED"


def _root() -> Path | None:
    configured = os.environ.get(SESSION_ENV)
    if not configured:
        return None
    root = Path(configured).resolve()
    return root if root.is_dir() else None


def _safe_system(system: str) -> str:
    return system.replace("/", "_")


def _path(system: str, suffix: str) -> Path | None:
    root = _root()
    if root is None:
        return None
    return root / f"provider-{_safe_system(system)}.{suffix}"


def mark_started(system: str) -> None:
    path = _path(system, "started")
    if path is not None:
        path.touch(exist_ok=True)


def mark_failed(system: str, detail: str) -> None:
    path = _path(system, "failed")
    if path is not None:
        path.write_text(detail, encoding="utf-8")


def publish_report(system: str, report: Mapping[str, Any]) -> None:
    destination = _path(system, "json")
    if destination is None:
        return
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, default=str)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def load_report(system: str) -> dict[str, Any] | None:
    if os.environ.get(MATRIX_EXPECTED_ENV) != "1":
        return None
    report_path = _path(system, "json")
    failed_path = _path(system, "failed")
    if report_path is None or failed_path is None:
        return None
    deadline = time.monotonic() + 600.0
    while time.monotonic() < deadline:
        if report_path.is_file():
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        if failed_path.exists():
            return None
        time.sleep(0.05)
    return None
