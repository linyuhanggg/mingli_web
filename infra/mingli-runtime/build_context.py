#!/usr/bin/env python3
"""Create an exact Docker build context from the signed V5.1 release.

The installed Skill directory may contain local-only research files.  This
projector copies only the 217 files named by the signed release manifest, then
re-verifies hashes, committed modes, and the absence of every extra file.  It
never edits the source tree and refuses to replace an existing destination.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_NAME = ".mingli-release-manifest.json"
EXPECTED_MANIFEST_SHA256 = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)
EXPECTED_SOURCE_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
EXPECTED_RELEASE_NAME = "mingli-master-portable-core"
EXPECTED_FILE_COUNT = 217
CONTEXT_FILES = (
    "Dockerfile",
    "audit_runtime.py",
    "dependency-provenance.json",
    "requirements-linux-x86_64.lock",
    "verify_release.py",
)


class ProjectionError(RuntimeError):
    """The source or projected release does not match its manifest."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(raw: object) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ProjectionError(f"unsafe release path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProjectionError(f"unsafe release path: {raw!r}")
    if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
        raise ProjectionError(f"release cache artifact is forbidden: {raw}")
    return path.as_posix()


def load_manifest(
    release_root: Path,
    *,
    expected_manifest_sha256: str,
    expected_source_commit: str,
    expected_file_count: int,
) -> dict[str, Any]:
    manifest_path = release_root / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProjectionError("signed release manifest is missing or unsafe")
    actual_manifest_sha256 = sha256_file(manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise ProjectionError("signed release manifest SHA-256 mismatch")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ProjectionError("signed release manifest is invalid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "files",
        "modes",
        "release",
        "schema_version",
        "source_commit",
    }:
        raise ProjectionError("signed release manifest schema is invalid")
    if payload.get("schema_version") != 3:
        raise ProjectionError("signed release manifest schema version mismatch")
    if payload.get("release") != EXPECTED_RELEASE_NAME:
        raise ProjectionError("signed release name mismatch")
    if payload.get("source_commit") != expected_source_commit:
        raise ProjectionError("signed release source commit mismatch")
    files = payload.get("files")
    modes = payload.get("modes")
    if not isinstance(files, dict) or not isinstance(modes, dict):
        raise ProjectionError("signed release files and modes must be objects")
    if len(files) != expected_file_count or set(files) != set(modes):
        raise ProjectionError(
            f"signed release must contain exactly {expected_file_count} file records"
        )
    safe_paths = {_safe_relative(path) for path in files}
    if safe_paths != set(files):
        raise ProjectionError("signed release paths are not canonical")
    for relative, digest in files.items():
        if not isinstance(digest, str) or len(digest) != 64:
            raise ProjectionError(f"invalid release digest: {relative}")
        mode = modes[relative]
        if mode not in {0o644, 0o755}:
            raise ProjectionError(f"invalid release mode: {relative}")
    return payload


def verify_release_tree(
    release_root: Path,
    *,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_source_commit: str = EXPECTED_SOURCE_COMMIT,
    expected_file_count: int = EXPECTED_FILE_COUNT,
    reject_extras: bool,
) -> dict[str, Any]:
    manifest = load_manifest(
        release_root,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_source_commit=expected_source_commit,
        expected_file_count=expected_file_count,
    )
    files: Mapping[str, str] = manifest["files"]
    modes: Mapping[str, int] = manifest["modes"]
    observed: set[str] = set()
    for path in release_root.rglob("*"):
        relative = path.relative_to(release_root).as_posix()
        if path.is_symlink():
            raise ProjectionError(f"release symlink is forbidden: {relative}")
        if path.is_file():
            _safe_relative(relative)
            observed.add(relative)
    expected = set(files) | {MANIFEST_NAME}
    if reject_extras and observed != expected:
        extras = sorted(observed - expected)
        missing = sorted(expected - observed)
        raise ProjectionError(
            f"projected release inventory mismatch; extras={extras}, missing={missing}"
        )
    missing = sorted(set(files) - observed)
    if missing:
        raise ProjectionError(f"release files are missing: {missing}")
    for relative, expected_digest in files.items():
        path = release_root / relative
        if not path.is_file() or path.is_symlink():
            raise ProjectionError(f"release file is missing or unsafe: {relative}")
        if sha256_file(path) != expected_digest:
            raise ProjectionError(f"release file SHA-256 mismatch: {relative}")
        actual_mode = stat.S_IMODE(path.stat().st_mode)
        if actual_mode != modes[relative]:
            raise ProjectionError(
                f"release file mode mismatch: {relative} ({actual_mode:o} != {modes[relative]:o})"
            )
    return manifest


def build_context(
    source_root: Path,
    destination: Path,
    *,
    infra_root: Path | None = None,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_source_commit: str = EXPECTED_SOURCE_COMMIT,
    expected_file_count: int = EXPECTED_FILE_COUNT,
) -> Path:
    source_root = source_root.resolve(strict=True)
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ProjectionError("build-context destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    infra_root = (infra_root or Path(__file__).resolve().parent).resolve(strict=True)
    manifest = verify_release_tree(
        source_root,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_source_commit=expected_source_commit,
        expected_file_count=expected_file_count,
        reject_extras=False,
    )
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        projected = temporary / "release"
        projected.mkdir(mode=0o755)
        for relative, mode in sorted(manifest["modes"].items()):
            source = source_root / relative
            target = projected / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            shutil.copyfile(source, target, follow_symlinks=False)
            target.chmod(mode)
        shutil.copyfile(
            source_root / MANIFEST_NAME,
            projected / MANIFEST_NAME,
            follow_symlinks=False,
        )
        (projected / MANIFEST_NAME).chmod(0o444)
        verify_release_tree(
            projected,
            expected_manifest_sha256=expected_manifest_sha256,
            expected_source_commit=expected_source_commit,
            expected_file_count=expected_file_count,
            reject_extras=True,
        )
        for filename in CONTEXT_FILES:
            source = infra_root / filename
            if source.is_symlink() or not source.is_file():
                raise ProjectionError(
                    f"build-context input is missing or unsafe: {filename}"
                )
            shutil.copyfile(source, temporary / filename, follow_symlinks=False)
            (temporary / filename).chmod(0o644)
        provenance = {
            "schema_version": "mingli-build-context-v1",
            "release_file_count": expected_file_count,
            "release_manifest_sha256": expected_manifest_sha256,
            "source_commit": expected_source_commit,
        }
        (temporary / "context-provenance.json").write_text(
            json.dumps(provenance, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    build_context(args.source_root, args.destination)
    print(args.destination.absolute())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
