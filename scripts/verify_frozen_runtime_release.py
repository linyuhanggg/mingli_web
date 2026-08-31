#!/usr/bin/env python3
"""Verify the one admitted V53 Runtime release, including its 227/228 split."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

FROZEN_SOURCE_COMMIT = "6db9dd37d8e62cd425798be2c64ad1121c1c1649"
FROZEN_RELEASE_NAME = "mingli-master-portable-core"
FROZEN_MANIFEST_SHA256 = (
    "f1deb17a9b4f39b09b2478c8942dcf0761d90bcba95dcbc44a15b8c84f79190b"
)
FROZEN_WORKER_SHA256 = (
    "e89df2c08df29e65ffc91c05e8e4e5be99f72f67e26b79c5b23a4eb2222ddc9c"
)
FROZEN_DESCRIBE_MANIFEST_DIGEST = (
    "2da3c62b250959a6f011434ee38fc3cf3851725a5fafb794ef78d978d9367b22"
)
FROZEN_CAPABILITY_SHAPE_SHA256 = (
    "9b9193285622a183c06802713fbfb62fa4c76e9190b692d9d422261a418e63af"
)
EXPECTED_SIGNED_FILE_COUNT = 227
EXPECTED_PHYSICAL_FILE_COUNT = 228
EXPECTED_REFERENCE_PACKS = 55
EXPECTED_EVIDENCE = 1328
EXPECTED_CAPABILITY_IDS = (
    "bazi",
    "fengshui",
    "fortune",
    "liuren",
    "liuyao",
    "luming-nayin",
    "meihua",
    "physiognomy",
    "qimen",
    "selection",
    "taiyi",
    "time-check",
    "xingming",
    "ziwei",
)
MANIFEST_NAME = ".mingli-release-manifest.json"
WORKER_RELATIVE = "scripts/reading_engine/runtime_worker.py"
CLOSURE_RELATIVE = "release/runtime-closure-v1.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RUNTIME_IDENTITY_PROGRAM = r"""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from reading_engine.catalog import CatalogLoader
from reading_engine.interface import _capability_view

catalog = CatalogLoader(root / "resources" / "runtime").load()
capabilities = [
    _capability_view(descriptor).to_dict()
    for descriptor in catalog.descriptors
]
shape = hashlib.sha256(
    json.dumps(
        capabilities,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
print(json.dumps({
    "manifest_digest": catalog.manifest_digest,
    "capability_shape_sha256": shape,
    "capability_ids": [item["id"] for item in capabilities],
}, ensure_ascii=True, sort_keys=True))
"""


class VerificationError(ValueError):
    """The release does not match the admitted immutable identity."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{label} path is invalid")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or value != relative.as_posix():
        raise VerificationError(f"{label} path is unsafe")
    return value


def _regular_file(root: Path, relative: object, label: str) -> Path:
    safe_relative = _safe_relative(relative, label)
    candidate = root / safe_relative
    try:
        metadata = candidate.lstat()
    except OSError as error:
        raise VerificationError(f"{label} is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise VerificationError(f"{label} must be a regular file")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise VerificationError(f"{label} escapes the release root") from error
    return candidate


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"{label} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise VerificationError(f"{label} must be a JSON object")
    return payload


def _verify_physical_inventory(root: Path, signed_paths: set[str]) -> int:
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in root.rglob("*"):
        try:
            metadata = path.lstat()
        except OSError as error:
            raise VerificationError("release inventory is unreadable") from error
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(metadata.st_mode):
            raise VerificationError("release contains an unsigned filesystem entry")
        if stat.S_ISDIR(metadata.st_mode):
            actual_directories.add(relative)
        elif stat.S_ISREG(metadata.st_mode):
            actual_files.add(relative)
        else:
            raise VerificationError("release contains an unsigned filesystem entry")

    expected_files = signed_paths | {MANIFEST_NAME}
    expected_directories: set[str] = set()
    for relative in expected_files:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if actual_files != expected_files or actual_directories != expected_directories:
        raise VerificationError("release physical inventory mismatch")
    if len(actual_files) != EXPECTED_PHYSICAL_FILE_COUNT:
        raise VerificationError("physical file count mismatch")
    return len(actual_files)


def _verify_closure(root: Path, signed_paths: set[str]) -> int:
    closure = _load_json(
        _regular_file(root, CLOSURE_RELATIVE, "Runtime closure"),
        "Runtime closure",
    )
    if closure.get("schema_version") != "mingli-runtime-closure-v1":
        raise VerificationError("Runtime closure schema mismatch")
    explicit = closure.get("files")
    patterns = closure.get("patterns")
    if not isinstance(explicit, list) or not isinstance(patterns, list):
        raise VerificationError("Runtime closure inventory is invalid")
    selected = {_safe_relative(item, "Runtime closure") for item in explicit}
    for raw_pattern in patterns:
        if not isinstance(raw_pattern, str) or not raw_pattern:
            raise VerificationError("Runtime closure pattern is invalid")
        matches = {
            relative
            for relative in signed_paths
            if PurePosixPath(relative).match(raw_pattern)
        }
        if not matches:
            raise VerificationError("Runtime closure pattern matched no signed files")
        selected.update(matches)
    if selected != signed_paths or len(selected) != EXPECTED_SIGNED_FILE_COUNT:
        raise VerificationError("Runtime closure does not match the signed inventory")
    return len(selected)


def _runtime_identity(root: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "-c",
                _RUNTIME_IDENTITY_PROGRAM,
                str(root),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        payload = json.loads(completed.stdout)
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ) as error:
        raise VerificationError("Runtime describe identity could not be recomputed") from error
    if not isinstance(payload, dict):
        raise VerificationError("Runtime describe identity is invalid")
    return payload


def verify_release(root: Path) -> dict[str, object]:
    root = root.resolve(strict=True)
    manifest_path = _regular_file(root, MANIFEST_NAME, "release manifest")
    manifest_sha256 = _sha256_file(manifest_path)
    if manifest_sha256 != FROZEN_MANIFEST_SHA256:
        raise VerificationError("manifest sha mismatch")

    manifest = _load_json(manifest_path, "release manifest")
    if (
        set(manifest) != {"schema_version", "release", "source_commit", "files", "modes"}
        or manifest.get("schema_version") != 3
        or manifest.get("release") != FROZEN_RELEASE_NAME
        or manifest.get("source_commit") != FROZEN_SOURCE_COMMIT
    ):
        raise VerificationError("release identity mismatch")
    files = manifest.get("files")
    modes = manifest.get("modes")
    if not isinstance(files, dict) or not isinstance(modes, dict):
        raise VerificationError("signed inventory is invalid")
    if len(files) != EXPECTED_SIGNED_FILE_COUNT or set(files) != set(modes):
        raise VerificationError("signed file count mismatch")

    signed_paths: set[str] = set()
    for raw_relative, expected_digest in files.items():
        relative = _safe_relative(raw_relative, "signed file")
        if not isinstance(expected_digest, str) or not _SHA256_RE.fullmatch(
            expected_digest
        ):
            raise VerificationError("signed file digest is invalid")
        path = _regular_file(root, relative, "signed file")
        if _sha256_file(path) != expected_digest:
            raise VerificationError(f"signed file digest mismatch: {relative}")
        expected_mode = modes[relative]
        if (
            not isinstance(expected_mode, int)
            or stat.S_IMODE(path.stat().st_mode) != expected_mode
        ):
            raise VerificationError(f"signed file mode mismatch: {relative}")
        signed_paths.add(relative)

    physical_file_count = _verify_physical_inventory(root, signed_paths)
    closure_file_count = _verify_closure(root, signed_paths)
    worker_path = _regular_file(root, WORKER_RELATIVE, "Runtime worker")
    worker_sha256 = _sha256_file(worker_path)
    if (
        worker_sha256 != FROZEN_WORKER_SHA256
        or files.get(WORKER_RELATIVE) != FROZEN_WORKER_SHA256
    ):
        raise VerificationError("Runtime worker digest mismatch")

    provider_ids = tuple(
        path.stem
        for path in sorted((root / "resources/runtime/providers").glob("*.json"))
    )
    if provider_ids != EXPECTED_CAPABILITY_IDS:
        raise VerificationError("Provider inventory mismatch")
    packs = list((root / "references/books").rglob("rules.md"))
    if len(packs) != EXPECTED_REFERENCE_PACKS:
        raise VerificationError("reference pack count mismatch")
    evidence = _regular_file(
        root,
        "references/index/evidence-rules.jsonl",
        "evidence index",
    )
    try:
        evidence_count = sum(1 for _ in evidence.open(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise VerificationError("evidence index is unreadable") from error
    if evidence_count != EXPECTED_EVIDENCE:
        raise VerificationError("evidence count mismatch")

    identity = _runtime_identity(root)
    if identity.get("manifest_digest") != FROZEN_DESCRIBE_MANIFEST_DIGEST:
        raise VerificationError("describe manifest digest mismatch")
    if identity.get("capability_shape_sha256") != FROZEN_CAPABILITY_SHAPE_SHA256:
        raise VerificationError("capability shape digest mismatch")
    if tuple(identity.get("capability_ids", ())) != EXPECTED_CAPABILITY_IDS:
        raise VerificationError("describe capability inventory mismatch")

    return {
        "status": "ok",
        "release_root": str(root),
        "source_commit": FROZEN_SOURCE_COMMIT,
        "manifest_sha256": manifest_sha256,
        "worker_sha256": worker_sha256,
        "signed_files": len(signed_paths),
        "physical_files": physical_file_count,
        "closure_files": closure_file_count,
        "describe_manifest_digest": identity["manifest_digest"],
        "capability_shape_sha256": identity["capability_shape_sha256"],
        "capabilities": len(EXPECTED_CAPABILITY_IDS),
        "reference_packs": len(packs),
        "evidence_records": evidence_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_release(args.release_root)
    except (OSError, VerificationError) as error:
        print(f"verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
