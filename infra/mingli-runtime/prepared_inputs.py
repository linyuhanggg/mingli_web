#!/usr/bin/env python3
"""Fail-closed loading for immutable local Gate inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

EXPECTED_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)
SCHEMA = "mingli-prepared-inputs-v1"


class PreparedInputsError(RuntimeError):
    """Prepared inputs are absent, mutable, or do not match the contract."""


def _fail(message: str) -> NoReturn:
    raise PreparedInputsError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _fail(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty string")
    return value


def _absolute_path(value: object, label: str, *, directory: bool) -> Path:
    raw = Path(_string(value, label))
    if not raw.is_absolute() or raw.is_symlink():
        _fail(f"{label} must be an absolute non-symlink path")
    if directory and not raw.is_dir():
        _fail(f"{label} must be a directory")
    if not directory and not raw.is_file():
        _fail(f"{label} must be a file")
    return raw


@dataclass(frozen=True)
class PreparedInputs:
    manifest_path: Path
    manifest_sha256: str
    source_root: Path
    research_root: Path
    native_python: Path
    runner_path: Path
    payload: dict[str, Any]


def load(path: Path, expected_sha256: str) -> PreparedInputs:
    if len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256
    ):
        _fail("prepared inputs SHA-256 is malformed")
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        _fail("prepared inputs manifest must be an absolute regular file")
    raw = path.read_bytes()
    actual_sha256 = sha256_bytes(raw)
    if actual_sha256 != expected_sha256:
        _fail("prepared inputs manifest SHA-256 mismatch")
    try:
        payload = _mapping(json.loads(raw), "prepared inputs")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreparedInputsError("prepared inputs manifest is not valid JSON") from exc
    if payload.get("schema") != SCHEMA:
        _fail("prepared inputs schema mismatch")

    source = _mapping(payload.get("source"), "source")
    research = _mapping(payload.get("research"), "research")
    native_runtime = _mapping(payload.get("native_runtime"), "native_runtime")
    if source.get("commit") != EXPECTED_COMMIT:
        _fail("source commit mismatch")
    if source.get("release_manifest_sha256") != EXPECTED_RELEASE_MANIFEST_SHA256:
        _fail("release manifest SHA-256 mismatch")
    if research.get("commit") != EXPECTED_COMMIT:
        _fail("research commit mismatch")

    source_root = _absolute_path(source.get("root"), "source.root", directory=True)
    research_root = _absolute_path(
        research.get("root"), "research.root", directory=True
    )
    source_resolved = source_root.resolve(strict=True)
    research_resolved = research_root.resolve(strict=True)
    if (
        source_resolved == research_resolved
        or source_resolved.is_relative_to(research_resolved)
        or research_resolved.is_relative_to(source_resolved)
    ):
        _fail("research root must be external to the source projection")
    source_fulltext = source_root / "references" / "fulltext"
    if source_fulltext.is_symlink():
        _fail("source projection contains fulltext through a symlink")
    if source_fulltext.is_dir() and any(
        candidate.is_file() for candidate in source_fulltext.rglob("*")
    ):
        _fail("source projection contains fulltext generator drift")
    native_python = _absolute_path(
        native_runtime.get("python"), "native_runtime.python", directory=False
    )
    if sha256_file(native_python) != native_runtime.get("python_sha256"):
        _fail("native Python SHA-256 mismatch")
    lock = _absolute_path(
        native_runtime.get("requirements_lock"),
        "native_runtime.requirements_lock",
        directory=False,
    )
    if sha256_file(lock) != native_runtime.get("requirements_lock_sha256"):
        _fail("runtime lock SHA-256 mismatch")

    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        _fail("prepared inputs bindings must be a non-empty list")
    for index, raw_binding in enumerate(bindings):
        binding = _mapping(raw_binding, f"bindings[{index}]")
        if binding.get("kind") != "file":
            _fail(f"bindings[{index}].kind is unsupported")
        bound_path = _absolute_path(
            binding.get("path"), f"bindings[{index}].path", directory=False
        )
        if sha256_file(bound_path) != binding.get("sha256"):
            _fail(f"bindings[{index}] SHA-256 mismatch")

    runner_path = source_root / "scripts" / "run_test_suite.py"
    if runner_path.is_symlink() or not runner_path.is_file():
        _fail("signed native suite runner is absent")
    return PreparedInputs(
        manifest_path=path,
        manifest_sha256=actual_sha256,
        source_root=source_root,
        research_root=research_root,
        native_python=native_python,
        runner_path=runner_path,
        payload=payload,
    )
