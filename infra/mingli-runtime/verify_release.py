#!/usr/bin/env python3
"""Fail-closed verifier for the complete Mingli V5.1 Linux release.

There are two deliberately separate entry points:

* :func:`inspect_runtime` runs in the image and recomputes the signed release,
  runtime closure, 13-Provider catalog, 55 reference packs, 1328 evidence rows,
  installed Python tree, Node runtime, and portable ``describe`` result.
* :func:`validate_audit_report` runs in this repository and recomputes every
  digest recorded by the generated audit report.  Status strings alone are
  never admission evidence.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

MANIFEST_NAME = ".mingli-release-manifest.json"
IMAGE_DIGEST_KIND = "oci_index"
IMAGE_DIGEST_PROPERTY = "mingli:oci-index-digest"
EXPECTED_RELEASE = {
    "name": "mingli-master-portable-core",
    "version": "5.1",
    "source_commit": "494ce0bba174a77800daf9b9c38ce9c9166d9a94",
    "release_manifest_file_count": 217,
    "release_manifest_sha256": (
        "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
    ),
    "skill_sha256": (
        "ee43ae256f2a39c7bf0fde6714d5ff87af2b654cae2283ee0b6d07566502c378"
    ),
    "protocol_version": "mingli-portable-interface-v2",
    "describe_digest": (
        "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
    ),
}
EXPECTED_PROVIDERS = frozenset(
    {
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
        "xingming",
        "ziwei",
    }
)
EXPECTED_P0_PROVIDERS = frozenset({"bazi", "fortune", "liuyao"})
EXPECTED_DISTRIBUTIONS = {
    "astronomy_engine": "2.1.19",
    "cnlunar": "0.2.4",
    "pyyaml": "6.0.3",
    "sxtwl": "2.0.7",
}
EXPECTED_NODE = {
    "filename": "node-v26.3.0-linux-x64.tar.gz",
    "sha256": "a6e65cc653e40c1653b77742f9185dbce3ff1f99fa2746d211bddb53530ef206",
    "version": "26.3.0",
}
EXPECTED_LIBATOMIC = {
    "architecture": "amd64",
    "fetch_url": (
        "https://snapshot.debian.org/archive/debian/20250501T000000Z/"
        "pool/main/g/gcc-12/libatomic1_12.2.0-14+deb12u1_amd64.deb"
    ),
    "filename": "libatomic1_12.2.0-14+deb12u1_amd64.deb",
    "installed_path": "/usr/lib/x86_64-linux-gnu/libatomic.so.1.2.0",
    "installed_sha256": (
        "107ab9f7661a1c47cddfb5cd1def99ec537a50a9a537fbe38cdde1b34b8ba280"
    ),
    "license": "GPL-3.0-or-later WITH GCC-exception-3.1",
    "origin_url": (
        "https://deb.debian.org/debian/pool/main/g/gcc-12/"
        "libatomic1_12.2.0-14+deb12u1_amd64.deb"
    ),
    "package": "libatomic1",
    "sha256": "fbd4e154a6b444229ea002cc209df099209c0adc09102e5fd21239a3d2b55e2d",
    "soname_path": "/usr/lib/x86_64-linux-gnu/libatomic.so.1",
    "soname_target": "libatomic.so.1.2.0",
    "snapshot_timestamp": "20250501T000000Z",
    "version": "12.2.0-14+deb12u1",
}
EXPECTED_GIT_BUILD_CONFIG = {
    "build_jobs": 6,
    "cflags": (
        "-O2 -g0 -ffile-prefix-map=/opt/git-build/source-{lane}=. "
        "-fdebug-prefix-map=/opt/git-build/source-{lane}=."
    ),
    "compiler": "gcc",
    "features": {
        "curl": False,
        "expat": False,
        "gettext": False,
        "openssl": False,
        "perl": False,
        "python": False,
        "tcltk": False,
    },
    "install_link_strategy": "relative-symlinks",
    "ldflags": "-Wl,--build-id=none",
    "license": "GPL-2.0-only",
    "make_flags": [
        "BLK_SHA256=YesPlease",
        "NO_CURL=YesPlease",
        "NO_EXPAT=YesPlease",
        "NO_GETTEXT=YesPlease",
        "INSTALL_SYMLINKS=YesPlease",
        "NO_OPENSSL=YesPlease",
        "NO_PERL=YesPlease",
        "NO_PYTHON=YesPlease",
        "NO_TCLTK=YesPlease",
    ],
    "prefix": "/opt/git",
    "schema_version": "mingli-git-build-config-v1",
    "sha1_backend": "sha1dc-built-in",
    "sha256_backend": "block-built-in",
    "source_sha256": (
        "ca0ec03fb2696f552f37135a56a0242fa062bd350cb243dc4a15c86f1cafbc99"
    ),
    "source_url": "https://www.kernel.org/pub/software/scm/git/git-2.39.5.tar.gz",
    "version": "2.39.5",
}
EXPECTED_GIT = {
    "build_config": EXPECTED_GIT_BUILD_CONFIG,
    "build_config_path": "/opt/git/build-config.json",
    "build_config_sha256": (
        "268f9c8479e24f29c3856b077d419e4dab2b13dfa7f732351c22f4e56926f92e"
    ),
    "checksum_manifest_url": (
        "https://www.kernel.org/pub/software/scm/git/sha256sums.asc"
    ),
    "installed_binary_path": "/opt/git/bin/git",
    "installed_binary_sha256": (
        "dab43c441c45a75efaa8db3f7c69507d803a642c275efb087d3eaa96d7c0efbe"
    ),
    "installed_tree_content_bytes": 17_679_688,
    "installed_tree_entry_count": 224,
    "installed_tree_path": "/opt/git",
    "installed_tree_regular_file_bytes": 17_677_827,
    "installed_tree_regular_file_count": 70,
    "installed_tree_sha256": (
        "44c998a56d933e9e6b637cb5ca23a9938b843f2fa66a54de2e28c38fc3a59486"
    ),
    "installed_tree_symlink_count": 144,
    "installed_tree_symlink_target_bytes": 1_861,
    "license": "GPL-2.0-only",
    "license_path": "/opt/git/COPYING",
    "license_sha256": (
        "5b2198d1645f767585e8a88ac0499b04472164c0d2da22e75ecf97ef443ab32e"
    ),
    "source_filename": "git-2.39.5.tar.gz",
    "source_sha256": (
        "ca0ec03fb2696f552f37135a56a0242fa062bd350cb243dc4a15c86f1cafbc99"
    ),
    "source_url": "https://www.kernel.org/pub/software/scm/git/git-2.39.5.tar.gz",
    "version": "2.39.5",
}
GIT_SMOKE_FIXTURE_BYTES = b"Mingli V5.1 Git runtime smoke fixture.\n"
GIT_SMOKE_OPERATIONS = (
    "version",
    "init",
    "config-user-name",
    "config-user-email",
    "config-gc-auto",
    "config-maintenance-auto",
    "add",
    "commit",
    "status",
    "ls-files",
    "ls-tree",
    "rev-parse-commit",
    "rev-parse-tree",
    "archive",
    "exec-path",
)
EXPECTED_GIT_SMOKE_ARCHIVE_SHA256 = (
    "f063d200b64075f2386bfb49351ce97a124b678b550dea39e3949778c446318d"
)
EXPECTED_NODE_LINKAGE = frozenset(
    {
        "ld-linux-x86-64.so.2",
        "libatomic.so.1",
        "libc.so.6",
        "libdl.so.2",
        "libgcc_s.so.1",
        "libm.so.6",
        "libpthread.so.0",
        "libstdc++.so.6",
    }
)
EXPECTED_GIT_LINKAGE = frozenset(
    {
        "ld-linux-x86-64.so.2",
        "libc.so.6",
        "libz.so.1",
    }
)
EXPECTED_SXTWL_LINKAGE = frozenset(
    {
        "ld-linux-x86-64.so.2",
        "libc.so.6",
        "libgcc_s.so.1",
        "libm.so.6",
        "libstdc++.so.6",
    }
)
EXPECTED_SXTWL_EXTENSION_SHA256 = (
    "1619ccedd2f03cdad9dfdcc7fb39be0c65b8603a913058e5099d54c3462f9b85"
)
EXPECTED_BASE_IMAGE = {
    "linux_amd64_manifest_digest": (
        "sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4"
    ),
    "multi_platform_index_digest": (
        "sha256:4c92f39a122d9d4008cb3227dd58506d8a2a87c2df47981406b043178374f9f8"
    ),
    "name": "python:3.14.6-slim-bookworm",
}
EXPECTED_PYTHON_ARTIFACTS = {
    "PyYAML": {
        "filename": (
            "pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64."
            "manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"
        ),
        "sha256": "c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5",
        "version": "6.0.3",
    },
    "astronomy-engine": {
        "filename": "astronomy_engine-2.1.19-py3-none-any.whl",
        "sha256": "232ba7dd2bbf42225c48be6721b676e8c6c079dbd4588d2781dfa68adcb6f67f",
        "version": "2.1.19",
    },
    "cnlunar": {
        "filename": "cnlunar-0.2.4-py3-none-any.whl",
        "sha256": "19689288604e86a3ef48dba23d39d6a7efbd5efabcb3923d4d656319762af4ea",
        "version": "0.2.4",
    },
    "sxtwl": {
        "sdist_filename": "sxtwl-2.0.7.tar.gz",
        "sdist_sha256": (
            "38b24472389f7f6f3521c2c99e4b5e86c0184c7d6eb02e5409c239d21f0a6512"
        ),
        "version": "2.0.7",
        "wheel_filename": "sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl",
        "wheel_sha256": (
            "90595ae5a5e311ae019170784c56bff52c176942347836c904e7c8af8d7b5c22"
        ),
    },
}
EXPECTED_IZTRO_SHA256 = (
    "4b8eca323e5d4291471567c62255a2166471c55c77ebe8f0d2d38240e69d12b1"
)
EXPECTED_TEST_COUNT = 1584
EXPECTED_TEST_TARGETS = 126
EXPECTED_TEST_MODULES = 93
EXPECTED_PROVIDER_MATRIX_TIMEOUT_SECONDS = 10_800
EXPECTED_RELEASE_REGRESSION_TIMEOUT_SECONDS = 10_800
EXPECTED_MATRIX_BINDING_TIMEOUT_SECONDS = 300
EXPECTED_PROVIDER_MATRIX_SHA256 = (
    "b0d9f9cad40a07d245d8e8b26407aef870da2b359042ebabcab4b1d3c9a9dd0e"
)
EXPECTED_GENERATOR_INPUT_FINGERPRINT = (
    "62e4b9560b08784e0cad24366c71ea25bf0f7217c74052fae9314f86dffab6d6"
)
MATRIX_TARGET = "test_v51_provider_completeness.py::CanonicalMatrixSnapshotTests"
EXPECTED_PRODUCTION_COMMAND_IDS = frozenset(
    {
        "characterization-a",
        "characterization-b",
        "git-smoke",
        "matrix-input-after",
        "matrix-input-before",
        "p0-trajectories",
        "production-native-linkage",
        "production-tree-identity",
        "provider-matrix-b",
        "release-regression",
        "runtime-inventory",
        "runtime-probe-machine",
        "runtime-probe-unittest",
        "sbom-regeneration",
    }
)
EXPECTED_AUDIT_COMMAND_IDS = frozenset(
    {
        "audit-native-linkage",
        "audit-tree-identity",
        "source-binding",
    }
)
EXPECTED_BACKUP_FLAGS = (
    "accepted_followup_created",
    "accepted_token_replayed",
    "complete_public_copy_byte_identical",
    "followup_version_advanced",
    "prepared_replay_byte_identical",
    "prepared_restored_completed",
    "prepared_token_restored",
)
EXPECTED_CHARACTERIZATION_DIGESTS = {
    "bazi": "8414c2fed081d148fd47a7472ebe70669eae673b6510627097485dd25a5cbc4c",
    "fengshui": "f20065947fc8eaa277bdcc6ea41cc5406eab389d6132662cba30b265683453ee",
    "fortune": "1dd87a9250fd41e9054d607e3fed3b2a353e88397b7a53e836e6496e714150c0",
    "liuren": "f373fd19d94c85ef5b83dbf7b1ceac12df95501b888fae584e94b0f6b5a8bf74",
    "liuyao": "139ed261ba16ee4a44e392a5a83dfaa12ee8ae430302c73c82db236be1d71971",
    "luming-nayin": "f2aa69dfcb7f577070afb85a69693bdfc7dca1c00bbefd2a3cfce24839ad395f",
    "meihua": "25935f21960bd22d841b53929373bbfe8d8532edd7e3d8998c75f640c046db38",
    "physiognomy": "e65b6f9e1cf969189ecaf12d14939ac95dce23d6c611cda4747870d1dfc3ebe0",
    "qimen": "dfeb5f9c5eeef5f12d579e3ee4d51480ee4e02efb550027c98c818d6b2a73be9",
    "selection": "2338e42137bfc74a71206671788df0aec82e574ce0e717f8da71db2a2f36eab1",
    "taiyi": "978f8d4750a849bc8410418e11b4baea7e7f6a23be6acda2bc6531e18730c52a",
    "xingming": "45b73740914812e2625e6fff80a9d21025762b041324f0ab7482683877eaa491",
    "ziwei": "d1a42e98792445f17e7394450623cf24ce5996fccb1709a8a6c430df92ddf0f6",
}
EXPECTED_FIXTURE_DIGESTS = {
    "bazi": "f5e7e1f5460ef1faf1b2d64dcc5b97cbfca8adeca03945aa9c59f2fb25bf13a4",
    "fengshui": "e94670e3f82f03f1ef69a68fd2cb55adebced53fa0c46e55cee86da068be1935",
    "fortune": "b84f4bf9c5aa3c3ea04825e6271485cc31a8e0187f0d0b66314dd9df7d71275d",
    "liuren": "791640f102d54c857e64a33bc405135125a7a20fb1959f90f1c7c489c3d69960",
    "liuyao": "8fc4a740b0afe39ba5878285482f0ab1921cf208aec876ac0a7fc06f9bf2c9d9",
    "luming-nayin": "cd263b740cbbcb99e7268d1ae07342d5126b0dc3dd4aa29b193d204b70c6549a",
    "meihua": "4d791d72356a7b4d63d7f4e4083726611dc1b845d3bb5ce78fdb6efe74ad9a25",
    "physiognomy": "8d2a3202155d741a2e8ca528d40cf113c58f09c9d61421c56ec0d782234f62c6",
    "qimen": "14c3f8a5dba09454acafdf332bf5eb9fc72359aa82ab5eeeb11d4a49c59f07ce",
    "selection": "ec2ac7599b18b9ea8ad8762e8b7214aad0e7a402a3f9eaac1bf4f3a09bb18686",
    "taiyi": "fb736b6a4f8908bd0d4602952df347f99248ba1162cd17c93720de5b3aa3c5b7",
    "xingming": "941ef871ddc3e47a1599c4c31900d63fb2bdf30e0dfd1db4b5d53a535b75cdd0",
    "ziwei": "194dffa733a9d9edcea1a29a4b5a6386faf8afcacee564e412c86316183b554a",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
IMAGE_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
SUMMARY_RE = re.compile(
    r"^summary: targets=(?P<targets>\d+) modules=(?P<modules>\d+) "
    r"tests=(?P<tests>\d+) failed_modules=(?P<failed>\d+) "
    r"elapsed=(?P<elapsed>[0-9.]+)s$",
    re.MULTILINE,
)
MATRIX_TARGET_RE = re.compile(
    r"^\[PASS\] "
    + re.escape(MATRIX_TARGET)
    + r" tests=(?P<tests>\d+) elapsed=(?P<elapsed>\d+(?:\.\d+)?)s$",
    re.MULTILINE,
)
RUN_ID_RE = re.compile(r"\d{14}[0-9a-f]{8}")


class ReleaseVerificationError(RuntimeError):
    """Release admission evidence is missing, inconsistent, or tampered."""


def _fail(message: str) -> NoReturn:
    raise ReleaseVerificationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ReleaseVerificationError(f"cannot hash artifact: {path}") from exc
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def runtime_tree_digest(root: Path) -> dict[str, Any]:
    """Hash every byte, mode, directory, and in-root symlink deterministically."""

    raw_root = root
    if raw_root.is_symlink():
        _fail(f"runtime tree root is a symlink: {raw_root}")
    try:
        root = raw_root.resolve(strict=True)
    except OSError as exc:
        raise ReleaseVerificationError(f"runtime tree is missing: {raw_root}") from exc
    if not root.is_dir():
        _fail(f"runtime tree is missing or unsafe: {root}")
    entries: list[dict[str, object]] = []
    regular_file_bytes = 0
    regular_file_count = 0
    symlink_count = 0
    symlink_target_bytes = 0
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISDIR(info.st_mode):
            record: dict[str, object] = {
                "mode": mode,
                "path": relative,
                "type": "directory",
            }
        elif stat.S_ISREG(info.st_mode):
            regular_file_count += 1
            regular_file_bytes += info.st_size
            record = {
                "mode": mode,
                "path": relative,
                "sha256": sha256_file(path),
                "size": info.st_size,
                "type": "file",
            }
        elif stat.S_ISLNK(info.st_mode):
            symlink_count += 1
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                raise ReleaseVerificationError(
                    f"runtime tree contains a broken symlink: {path}"
                ) from exc
            if not resolved.is_relative_to(root):
                _fail(f"runtime tree symlink escapes its root: {path}")
            target = os.readlink(path)
            symlink_target_bytes += len(target.encode("utf-8"))
            record = {
                "mode": mode,
                "path": relative,
                "target": target,
                "type": "symlink",
            }
        else:
            _fail(f"runtime tree contains an unsupported object: {path}")
        entries.append(record)
    return {
        "content_bytes": regular_file_bytes + symlink_target_bytes,
        "entry_count": len(entries),
        "path": str(root),
        "regular_file_bytes": regular_file_bytes,
        "regular_file_count": regular_file_count,
        "sha256": canonical_sha256(entries),
        "symlink_count": symlink_count,
        "symlink_target_bytes": symlink_target_bytes,
    }


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing or unsafe: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ReleaseVerificationError(f"{label} is invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        _fail(f"{label} must be a JSON object")
    return value


def _safe_relative(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        _fail(f"{label} contains an unsafe path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"{label} contains an unsafe path: {raw!r}")
    if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
        _fail(f"{label} contains a forbidden cache artifact: {raw}")
    return path.as_posix()


def _regular_file(root: Path, relative: object, label: str) -> Path:
    safe = _safe_relative(relative, label)
    path = root / safe
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ReleaseVerificationError(f"{label} is missing: {safe}") from exc
    if (
        not resolved.is_relative_to(root.resolve())
        or path.is_symlink()
        or not path.is_file()
    ):
        _fail(f"{label} escapes its root or is unsafe: {safe}")
    return path


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        _fail(f"{label} must be a lowercase SHA-256")
    return value


def _require_image_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or IMAGE_DIGEST_RE.fullmatch(value) is None:
        _fail(f"{label} must be a sha256 image digest")
    return value


def _require_exact_mapping(
    actual: object, expected: Mapping[str, object], label: str
) -> None:
    if actual != expected:
        _fail(f"{label} does not match the frozen contract")


def _read_release_manifest(release_root: Path) -> dict[str, Any]:
    manifest_path = release_root / MANIFEST_NAME
    if sha256_file(manifest_path) != EXPECTED_RELEASE["release_manifest_sha256"]:
        _fail("release manifest SHA-256 mismatch")
    manifest = _load_json(manifest_path, "release manifest")
    if set(manifest) != {
        "files",
        "modes",
        "release",
        "schema_version",
        "source_commit",
    }:
        _fail("release manifest schema is not exact")
    if manifest.get("schema_version") != 3:
        _fail("release manifest schema version mismatch")
    if manifest.get("release") != EXPECTED_RELEASE["name"]:
        _fail("release manifest name mismatch")
    if manifest.get("source_commit") != EXPECTED_RELEASE["source_commit"]:
        _fail("release manifest source commit mismatch")
    files = manifest.get("files")
    modes = manifest.get("modes")
    if not isinstance(files, dict) or not isinstance(modes, dict):
        _fail("release manifest files and modes must be objects")
    if len(files) != EXPECTED_RELEASE["release_manifest_file_count"]:
        _fail("release manifest must contain exactly 217 files")
    if set(files) != set(modes):
        _fail("release manifest file/mode inventory mismatch")
    if files.get("SKILL.md") != EXPECTED_RELEASE["skill_sha256"]:
        _fail("release SKILL.md digest mismatch")
    for relative, digest in files.items():
        if _safe_relative(relative, "release manifest") != relative:
            _fail(f"release manifest path is not canonical: {relative}")
        _require_sha256(digest, f"release digest {relative}")
        if modes[relative] not in {0o644, 0o755}:
            _fail(f"release manifest mode is invalid: {relative}")
    return manifest


def _verify_release_files(
    release_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, dict[str, object]]:
    expected_files: Mapping[str, str] = manifest["files"]
    expected_modes: Mapping[str, int] = manifest["modes"]
    observed: set[str] = set()
    for path in release_root.rglob("*"):
        relative = path.relative_to(release_root).as_posix()
        if path.is_symlink():
            _fail(f"release symlink is forbidden: {relative}")
        if path.is_file():
            _safe_relative(relative, "release tree")
            observed.add(relative)
    expected = set(expected_files) | {MANIFEST_NAME}
    if observed != expected:
        _fail(
            "release tree is not the exact 217-file projection; "
            f"extras={sorted(observed - expected)}, missing={sorted(expected - observed)}"
        )
    inventory: dict[str, dict[str, object]] = {}
    for relative, expected_digest in sorted(expected_files.items()):
        path = _regular_file(release_root, relative, "release file")
        actual_digest = sha256_file(path)
        actual_mode = stat.S_IMODE(path.stat().st_mode)
        if actual_digest != expected_digest:
            _fail(f"release file digest mismatch: {relative}")
        if actual_mode != expected_modes[relative]:
            _fail(f"release file mode mismatch: {relative}")
        inventory[relative] = {"mode": actual_mode, "sha256": actual_digest}
    return inventory


def _verify_runtime_closure(
    release_root: Path,
    manifest_paths: set[str],
) -> list[str]:
    closure = _load_json(
        release_root / "release/runtime-closure-v1.json",
        "runtime closure",
    )
    if set(closure) != {"files", "patterns", "schema_version"}:
        _fail("runtime closure schema is not exact")
    if closure.get("schema_version") != "mingli-runtime-closure-v1":
        _fail("runtime closure schema version mismatch")
    raw_files = closure.get("files")
    raw_patterns = closure.get("patterns")
    if not isinstance(raw_files, list) or not isinstance(raw_patterns, list):
        _fail("runtime closure files/patterns must be lists")
    files = [_safe_relative(item, "runtime closure") for item in raw_files]
    if len(files) != len(set(files)):
        _fail("runtime closure explicit files are not unique")
    selected = set(files)
    for raw_pattern in raw_patterns:
        if not isinstance(raw_pattern, str) or not any(x in raw_pattern for x in "*?["):
            _fail("runtime closure pattern is invalid")
        _safe_relative(
            raw_pattern.replace("*", "x").replace("?", "x"), "runtime closure"
        )
        matches = {
            relative
            for relative in manifest_paths
            if PurePosixPath(relative).match(raw_pattern)
        }
        if not matches:
            _fail(f"runtime closure pattern matched no signed files: {raw_pattern}")
        selected.update(matches)
    if selected != manifest_paths:
        _fail("runtime closure does not close over all 217 signed files")
    for relative in selected:
        _regular_file(release_root, relative, "runtime closure file")
    return sorted(selected)


def _verify_provider_catalog(release_root: Path) -> tuple[list[str], dict[str, bool]]:
    catalog = _load_json(
        release_root / "resources/runtime/catalog-v1.json",
        "provider catalog",
    )
    if set(catalog) != {"providers", "schema_version"}:
        _fail("provider catalog schema is not exact")
    if catalog.get("schema_version") != "catalog-v1":
        _fail("provider catalog schema version mismatch")
    entries = catalog.get("providers")
    if not isinstance(entries, list) or len(entries) != 13:
        _fail("13 Provider catalog is incomplete")
    provider_ids: list[str] = []
    for relative in entries:
        path = _regular_file(
            release_root / "resources/runtime",
            relative,
            "provider manifest",
        )
        provider = _load_json(path, "provider manifest")
        provider_id = provider.get("id")
        if not isinstance(provider_id, str) or not provider_id:
            _fail("provider manifest id is invalid")
        if provider.get("schema_version") != "provider-manifest-v1":
            _fail(f"provider manifest schema mismatch: {provider_id}")
        runtime_capability = provider.get("runtime_capability")
        capability = provider.get("capability")
        if not isinstance(runtime_capability, dict) or not isinstance(capability, dict):
            _fail(f"provider capability declaration is incomplete: {provider_id}")
        if runtime_capability.get("system") != provider_id:
            _fail(f"provider runtime system mismatch: {provider_id}")
        provider_ids.append(provider_id)
    if (
        len(provider_ids) != len(set(provider_ids))
        or set(provider_ids) != EXPECTED_PROVIDERS
    ):
        _fail("13 Provider inventory does not match the frozen release")
    return sorted(provider_ids), {provider: True for provider in sorted(provider_ids)}


def _signed_markdown_index_ids(path: Path, label: str) -> set[str]:
    """Extract canonical local IDs only from Markdown headings or index rows."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseVerificationError(f"{label} is unreadable: {path}") from exc
    local_id_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~:-]*[-_:][A-Za-z0-9._~:-]*")
    local_ids: list[str] = []
    for line in lines:
        heading = re.match(r"^#{2,6}\s+(\S+)(?:\s|$)", line)
        index_row = re.match(r"^\|\s*([^|\s]+)\s*\|", line)
        match = heading or index_row
        if match is not None and local_id_pattern.fullmatch(match.group(1)):
            local_ids.append(match.group(1))
    if len(local_ids) != len(set(local_ids)):
        _fail(f"{label} contains a duplicated canonical local ID")
    return set(local_ids)


def _evidence_reference_is_closed(
    reference: object,
    rule_ids: set[str],
    local_index_ids_by_pack: Mapping[str, set[str]],
) -> bool:
    if not isinstance(reference, str):
        return False
    if reference in rule_ids:
        return True
    if reference.count("#") != 1:
        return False
    pack_id, local_id = reference.split("#", 1)
    return local_id in local_index_ids_by_pack.get(pack_id, set())


def _verify_reference_and_evidence(release_root: Path) -> dict[str, object]:
    catalog = _load_json(
        release_root / "references/catalog/catalog.json",
        "reference catalog",
    )
    packs = catalog.get("ready_reference_packs")
    if (
        catalog.get("ready_count") != 55
        or not isinstance(packs, list)
        or len(packs) != 55
    ):
        _fail("reference catalog must contain exactly 55/55 ready packs")
    validation = catalog.get("validation")
    if not isinstance(validation, dict) or set(validation.values()) != {"PASS 55/55"}:
        _fail("reference catalog 55/55 validation is incomplete")
    pack_ids: set[str] = set()
    local_index_ids_by_pack: dict[str, set[str]] = {}
    for item in packs:
        if not isinstance(item, dict):
            _fail("reference pack record must be an object")
        system = item.get("system")
        slug = item.get("slug")
        if not isinstance(system, str) or not isinstance(slug, str):
            _fail("reference pack identity is invalid")
        pack_id = f"{system}/{slug}"
        if pack_id in pack_ids:
            _fail(f"reference pack identity is duplicated: {pack_id}")
        pack_ids.add(pack_id)
        if item.get("d2_status") != "ready":
            _fail(f"reference pack is not ready: {pack_id}")
        pack_root = f"references/books/{pack_id}"
        rules = _regular_file(release_root, f"{pack_root}/rules.md", "reference rules")
        quote_index = _regular_file(
            release_root,
            f"{pack_root}/quote-index.md",
            "reference quote index",
        )
        local_index_ids_by_pack[pack_id] = _signed_markdown_index_ids(
            rules,
            f"reference rules for {pack_id}",
        ) | _signed_markdown_index_ids(
            quote_index,
            f"reference quote index for {pack_id}",
        )
        fulltext_required = item.get("local_fulltext_required_for_runtime")
        if fulltext_required is True:
            if item.get("local_fulltext_policy") != "verified_excerpt_distributed":
                _fail(f"distributed reference excerpt policy drift: {pack_id}")
            excerpt = _regular_file(
                release_root,
                item.get("local_fulltext_path"),
                "distributed reference excerpt",
            )
            if sha256_file(excerpt) != item.get("local_fulltext_sha256"):
                _fail(f"distributed reference excerpt digest mismatch: {pack_id}")
        elif fulltext_required is not False:
            _fail(f"reference pack runtime/fulltext policy drift: {pack_id}")
    evidence_path = release_root / "references/index/evidence-rules.jsonl"
    try:
        rows = [
            json.loads(line)
            for line in evidence_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ReleaseVerificationError("evidence index is not valid JSONL") from exc
    if len(rows) != 1328 or any(not isinstance(row, dict) for row in rows):
        _fail("evidence index must contain exactly 1328 object records")
    rule_ids = [row.get("rule_id") for row in rows]
    if any(not isinstance(rule_id, str) or not rule_id for rule_id in rule_ids):
        _fail("evidence index contains an invalid rule_id")
    if len(set(rule_ids)) != 1328:
        _fail("evidence index 1328 rule_id values are not unique")
    rule_id_set = set(rule_ids)
    source_cache: dict[str, str] = {}
    for row in rows:
        rule_id = str(row["rule_id"])
        if row.get("schema_version") != "mingli-evidence-rule-v1":
            _fail(f"evidence schema mismatch: {rule_id}")
        if row.get("record_kind") != "substantive_rule":
            _fail(f"evidence record is not substantive: {rule_id}")
        if row.get("source_pack") not in pack_ids:
            _fail(f"evidence source pack is unknown: {rule_id}")
        source_relative = _safe_relative(row.get("source_path"), "evidence source")
        source_path = _regular_file(release_root, source_relative, "evidence source")
        source_digest = source_cache.setdefault(
            source_relative, sha256_file(source_path)
        )
        if source_digest != row.get("source_sha256"):
            _fail(f"evidence source digest mismatch: {rule_id}")
        quote = row.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            _fail(f"evidence quote is empty: {rule_id}")
        if hashlib.sha256(quote.encode("utf-8")).hexdigest() != row.get("quote_hash"):
            _fail(f"evidence quote digest mismatch: {rule_id}")
        for field in ("depends_on_rule_ids", "exception_rule_ids"):
            references = row.get(field)
            if not isinstance(references, list) or any(
                not isinstance(item, str) or item not in rule_id_set
                for item in references
            ):
                _fail(f"evidence reference closure failed for {field}: {rule_id}")
        conflict_references = row.get("conflict_rule_ids")
        if not isinstance(conflict_references, list) or any(
            not _evidence_reference_is_closed(
                item,
                rule_id_set,
                local_index_ids_by_pack,
            )
            for item in conflict_references
        ):
            _fail(f"evidence reference closure failed for conflict_rule_ids: {rule_id}")
    return {
        "evidence_index_count": len(rows),
        "evidence_index_sha256": sha256_file(evidence_path),
        "evidence_rule_ids_digest": canonical_sha256(sorted(rule_id_set)),
        "evidence_rule_ids_unique": True,
        "reference_pack_count": len(pack_ids),
        "reference_pack_ids_digest": canonical_sha256(sorted(pack_ids)),
    }


def _verify_version(release_root: Path) -> None:
    version = _load_json(release_root / "release/version.json", "release version")
    if version != {"name": "mingli-master", "version": EXPECTED_RELEASE["version"]}:
        _fail("release version identity mismatch")


def _verify_iztro(release_root: Path) -> None:
    vendored = release_root / "vendor/iztro-2.5.8/iztro.min.js"
    if sha256_file(vendored) != EXPECTED_IZTRO_SHA256:
        _fail("vendored iztro digest mismatch")
    provenance = _load_json(
        release_root / "vendor/iztro-2.5.8/PROVENANCE.json",
        "iztro provenance",
    )
    if provenance.get("version") != "2.5.8":
        _fail("vendored iztro version mismatch")
    if provenance.get("vendored_sha256") != EXPECTED_IZTRO_SHA256:
        _fail("vendored iztro provenance digest mismatch")


def _verify_runtime_python(release_root: Path, executable: Path) -> dict[str, Any]:
    if (
        not executable.is_absolute()
        or executable.is_symlink()
        or not os.access(executable, os.X_OK)
    ):
        _fail("runtime Python path is missing, relative, or unsafe")
    scripts = release_root / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        import runtime_python  # type: ignore[import-not-found]

        identity = runtime_python.probe_runtime_identity(str(executable))
    except Exception as exc:
        raise ReleaseVerificationError("runtime-integrity validation failed") from exc
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(scripts))
    if not isinstance(identity, dict):
        _fail("runtime Python identity is invalid")
    completed = subprocess.run(
        [str(executable), "-I", "-S", "-B", "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    version_text = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0 or version_text != "Python 3.14.6":
        _fail("runtime Python must be exactly CPython 3.14.6")
    manifest_path = executable.parent.parent / "runtime-integrity.json"
    runtime_manifest = _load_json(manifest_path, "runtime-integrity manifest")
    if runtime_manifest.get("distributions") != EXPECTED_DISTRIBUTIONS:
        _fail("runtime-integrity distribution set mismatch")
    files = runtime_manifest.get("files")
    if not isinstance(files, dict) or not files:
        _fail("runtime-integrity contains no installed files")
    return {
        "identity": identity,
        "manifest_file_count": len(files),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }


def _verify_node(executable: Path) -> dict[str, str]:
    if (
        not executable.is_absolute()
        or executable.is_symlink()
        or not os.access(executable, os.X_OK)
    ):
        _fail("Node runtime path is missing, relative, or unsafe")
    completed = subprocess.run(
        [str(executable), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if completed.returncode != 0 or completed.stdout.strip() != "v26.3.0":
        _fail("Node runtime must be exactly 26.3.0")
    return dict(EXPECTED_NODE)


def _verify_git(executable: Path) -> dict[str, Any]:
    expected_executable = Path(EXPECTED_GIT["installed_binary_path"])
    if (
        executable != expected_executable
        or not executable.is_absolute()
        or executable.is_symlink()
        or not os.access(executable, os.X_OK)
    ):
        _fail("Git runtime path is missing, relative, symlinked, or unexpected")
    root = Path(EXPECTED_GIT["installed_tree_path"])
    tree = runtime_tree_digest(root)
    expected_tree = {
        "content_bytes": EXPECTED_GIT["installed_tree_content_bytes"],
        "entry_count": EXPECTED_GIT["installed_tree_entry_count"],
        "path": EXPECTED_GIT["installed_tree_path"],
        "regular_file_bytes": EXPECTED_GIT["installed_tree_regular_file_bytes"],
        "regular_file_count": EXPECTED_GIT["installed_tree_regular_file_count"],
        "sha256": EXPECTED_GIT["installed_tree_sha256"],
        "symlink_count": EXPECTED_GIT["installed_tree_symlink_count"],
        "symlink_target_bytes": EXPECTED_GIT["installed_tree_symlink_target_bytes"],
    }
    if tree != expected_tree:
        _fail("installed Git tree differs from the frozen deterministic build")
    if sha256_file(executable) != EXPECTED_GIT["installed_binary_sha256"]:
        _fail("installed Git executable SHA-256 mismatch")
    config_path = Path(EXPECTED_GIT["build_config_path"])
    config = _load_json(config_path, "Git build configuration")
    if config != EXPECTED_GIT_BUILD_CONFIG:
        _fail("installed Git build configuration differs from frozen flags")
    if sha256_file(config_path) != EXPECTED_GIT["build_config_sha256"]:
        _fail("installed Git build configuration SHA-256 mismatch")
    license_path = Path(EXPECTED_GIT["license_path"])
    if sha256_file(license_path) != EXPECTED_GIT["license_sha256"]:
        _fail("installed Git license bytes mismatch")
    source_path = Path("/opt/mingli-runtime/artifacts") / str(
        EXPECTED_GIT["source_filename"]
    )
    if source_path.is_symlink() or not source_path.is_file():
        _fail("Git frozen source artifact is missing or unsafe")
    if sha256_file(source_path) != EXPECTED_GIT["source_sha256"]:
        _fail("Git frozen source artifact SHA-256 mismatch")
    provenance = _load_json(
        Path("/opt/mingli-runtime/dependency-provenance.json"),
        "dependency provenance",
    )
    if provenance.get("git") != EXPECTED_GIT:
        _fail("Git dependency provenance differs from the frozen build")
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/opt/git/bin:/usr/bin:/bin",
        "TZ": "UTC",
    }
    completed = subprocess.run(
        [str(executable), "--version"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=15,
    )
    if completed.returncode != 0 or completed.stdout.strip() != "git version 2.39.5":
        _fail("Git runtime must be exactly 2.39.5")
    return {
        "binary_path": str(executable),
        "binary_sha256": EXPECTED_GIT["installed_binary_sha256"],
        "build_config_sha256": EXPECTED_GIT["build_config_sha256"],
        "license_sha256": EXPECTED_GIT["license_sha256"],
        "source_sha256": EXPECTED_GIT["source_sha256"],
        "tree": tree,
        "version": EXPECTED_GIT["version"],
    }


def validate_git_smoke_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("Git smoke output must be a JSON object")
    blob_header = f"blob {len(GIT_SMOKE_FIXTURE_BYTES)}\0".encode("ascii")
    blob_sha1 = hashlib.sha1(
        blob_header + GIT_SMOKE_FIXTURE_BYTES,
        usedforsecurity=False,
    ).hexdigest()
    tree_body = b"100644 tracked.txt\0" + bytes.fromhex(blob_sha1)
    tree_sha1 = hashlib.sha1(
        f"tree {len(tree_body)}\0".encode("ascii") + tree_body,
        usedforsecurity=False,
    ).hexdigest()
    commit_body = (
        f"tree {tree_sha1}\n"
        "author Mingli Linux Gate <gate@mingli.invalid> 946684800 +0000\n"
        "committer Mingli Linux Gate <gate@mingli.invalid> 946684800 +0000\n"
        "\n"
        "Mingli V5.1 Git smoke fixture\n"
    ).encode()
    commit_sha1 = hashlib.sha1(
        f"commit {len(commit_body)}\0".encode("ascii") + commit_body,
        usedforsecurity=False,
    ).hexdigest()
    expected = {
        "archive_sha256": EXPECTED_GIT_SMOKE_ARCHIVE_SHA256,
        "commit_sha1": commit_sha1,
        "exec_path": "/opt/git/libexec/git-core",
        "fixture": {
            "author_date": "2000-01-01T00:00:00Z",
            "author_email": "gate@mingli.invalid",
            "author_name": "Mingli Linux Gate",
            "commit_message": "Mingli V5.1 Git smoke fixture",
            "content_sha256": hashlib.sha256(GIT_SMOKE_FIXTURE_BYTES).hexdigest(),
            "filename": "tracked.txt",
        },
        "ls_files_row": f"100644 {blob_sha1} 0\ttracked.txt",
        "ls_tree_row": f"100644 blob {blob_sha1}\ttracked.txt",
        "operations": list(GIT_SMOKE_OPERATIONS),
        "schema_version": "mingli-git-smoke-v1",
        "status_porcelain": "",
        "templates_exists": True,
        "templates_path": "/opt/git/share/git-core/templates",
        "tree_sha1": tree_sha1,
        "version": "git version 2.39.5",
    }
    if value != expected:
        _fail("Git smoke output differs from the frozen fixture and golden values")
    return value


def _verify_libatomic() -> dict[str, str]:
    artifact = Path("/opt/mingli-runtime/artifacts") / EXPECTED_LIBATOMIC["filename"]
    if artifact.is_symlink() or not artifact.is_file():
        _fail("libatomic1 frozen amd64 package artifact is missing or unsafe")
    if sha256_file(artifact) != EXPECTED_LIBATOMIC["sha256"]:
        _fail("libatomic1 amd64 package artifact SHA-256 mismatch")
    for field, expected in (
        ("Package", EXPECTED_LIBATOMIC["package"]),
        ("Version", EXPECTED_LIBATOMIC["version"]),
        ("Architecture", EXPECTED_LIBATOMIC["architecture"]),
    ):
        completed = subprocess.run(
            ["/usr/bin/dpkg-deb", "--field", str(artifact), field],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if completed.returncode != 0 or completed.stdout.strip() != expected:
            _fail(f"libatomic1 package metadata mismatch: {field}")
    for field, expected in (
        ("${Version}", EXPECTED_LIBATOMIC["version"]),
        ("${Architecture}", EXPECTED_LIBATOMIC["architecture"]),
    ):
        completed = subprocess.run(
            [
                "/usr/bin/dpkg-query",
                "--show",
                f"--showformat={field}",
                "libatomic1:amd64",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if completed.returncode != 0 or completed.stdout.strip() != expected:
            _fail("installed libatomic1 package identity mismatch")
    soname = Path(EXPECTED_LIBATOMIC["soname_path"])
    if (
        not soname.is_symlink()
        or os.readlink(soname) != EXPECTED_LIBATOMIC["soname_target"]
    ):
        _fail("libatomic1 SONAME link mismatch")
    installed = Path(EXPECTED_LIBATOMIC["installed_path"])
    if installed.is_symlink() or not installed.is_file():
        _fail("libatomic1 installed shared object is missing or unsafe")
    if sha256_file(installed) != EXPECTED_LIBATOMIC["installed_sha256"]:
        _fail("libatomic1 installed shared object SHA-256 mismatch")
    if soname.resolve(strict=True) != installed.resolve(strict=True):
        _fail("libatomic1 SONAME does not resolve to the admitted shared object")
    return dict(EXPECTED_LIBATOMIC)


def _inspect_dynamic_target(executable: Path, label: str) -> dict[str, Any]:
    if executable.is_symlink() or not executable.is_file():
        _fail(f"{label} native target is missing or unsafe")
    completed = subprocess.run(
        ["/usr/bin/ldd", str(executable)],
        check=False,
        capture_output=True,
        text=True,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"},
        timeout=30,
    )
    if completed.returncode != 0 or completed.stderr.strip():
        _fail(f"{label} dynamic linkage inspection failed")
    dependencies: dict[str, dict[str, object]] = {}
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("linux-vdso.so.1 "):
            continue
        if "=>" in line:
            name, raw_target = line.split("=>", 1)
            target = raw_target.strip().split()[0]
            name = name.strip()
            if target == "not":
                _fail(f"{label} dynamic dependency is unresolved: {name}")
        else:
            target = line.split()[0]
            name = Path(target).name
        path = Path(target)
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ReleaseVerificationError(
                f"{label} dynamic dependency is missing: {name}"
            ) from exc
        if not path.is_absolute() or not resolved.is_file():
            _fail(f"{label} dynamic dependency path is unsafe: {name}")
        if name in dependencies:
            _fail(f"{label} dynamic dependency is duplicated: {name}")
        dependencies[name] = {
            "reported_path": str(path),
            "resolved_path": str(resolved),
            "sha256": sha256_file(resolved),
        }
    if not dependencies:
        _fail(f"{label} dynamic dependency inventory is empty")
    return {
        "dependencies": dependencies,
        "path": str(executable),
        "sha256": sha256_file(executable),
    }


def _runtime_extension_paths(runtime_python: Path) -> dict[str, Path]:
    script = (
        "import _sxtwl,json,sxtwl,yaml._yaml\n"
        "day=sxtwl.fromSolar(2000,1,1)\n"
        "assert (day.getSolarYear(),day.getSolarMonth(),day.getSolarDay()) == (2000,1,1)\n"
        "modules={'sxtwl':_sxtwl,'yaml_c_extension':yaml._yaml}\n"
        "result={label:module.__file__ for label,module in modules.items()}\n"
        "print(json.dumps(result,sort_keys=True,separators=(',',':')))\n"
    )
    completed = subprocess.run(
        [str(runtime_python), "-I", "-B", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"},
        timeout=30,
    )
    if completed.returncode != 0 or completed.stderr.strip():
        _fail("runtime native extension discovery failed")
    try:
        raw = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReleaseVerificationError(
            "runtime native extension discovery returned invalid JSON"
        ) from exc
    if not isinstance(raw, dict) or set(raw) != {"sxtwl", "yaml_c_extension"}:
        _fail("runtime native extension discovery is incomplete")
    runtime_root = runtime_python.parent.parent.resolve(strict=True)
    result: dict[str, Path] = {}
    for label, value in raw.items():
        if not isinstance(value, str) or not value.endswith(".so"):
            _fail(f"runtime native extension is absent: {label}")
        path = Path(value)
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ReleaseVerificationError(
                f"runtime native extension is missing: {label}"
            ) from exc
        if (
            path.is_symlink()
            or not resolved.is_file()
            or not resolved.is_relative_to(runtime_root)
        ):
            _fail(f"runtime native extension path is unsafe: {label}")
        result[label] = resolved
    return result


def inspect_native_linkage(
    runtime_python: Path,
    node: Path,
    git: Path,
) -> dict[str, Any]:
    node_record = _verify_node(node)
    git_record = _verify_git(git)
    libatomic = _verify_libatomic()
    extensions = _runtime_extension_paths(runtime_python)
    targets = {
        "git": _inspect_dynamic_target(git, "Git"),
        "node": _inspect_dynamic_target(node, "Node"),
        "python": _inspect_dynamic_target(runtime_python, "CPython"),
        "sxtwl": _inspect_dynamic_target(extensions["sxtwl"], "sxtwl"),
        "yaml_c_extension": _inspect_dynamic_target(
            extensions["yaml_c_extension"],
            "PyYAML C extension",
        ),
    }
    node_dependencies = targets["node"]["dependencies"]
    if set(node_dependencies) != EXPECTED_NODE_LINKAGE:
        _fail("Node dynamic dependency inventory is not exact")
    atomic = node_dependencies.get("libatomic.so.1")
    if not isinstance(atomic, dict) or (
        atomic.get("resolved_path") != libatomic["installed_path"]
        or atomic.get("sha256") != libatomic["installed_sha256"]
    ):
        _fail("Node linkage is not bound to the admitted libatomic1 bytes")
    git_dependencies = targets["git"]["dependencies"]
    if set(git_dependencies) != EXPECTED_GIT_LINKAGE:
        _fail("Git dynamic dependency inventory is not exact")
    if targets["git"].get("sha256") != git_record["binary_sha256"]:
        _fail("Git linkage target differs from the admitted binary")
    sxtwl_dependencies = targets["sxtwl"]["dependencies"]
    if set(sxtwl_dependencies) != EXPECTED_SXTWL_LINKAGE:
        _fail("sxtwl dynamic dependency inventory is not exact")
    if targets["sxtwl"].get("sha256") != EXPECTED_SXTWL_EXTENSION_SHA256:
        _fail("sxtwl native extension differs from the admitted wheel bytes")
    return {
        "git_version": git_record["version"],
        "libatomic1": libatomic,
        "node_version": node_record["version"],
        "schema_version": "mingli-native-linkage-v1",
        "targets": targets,
    }


def _validate_native_target(record: object, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        _fail(f"{label} must be an object")
    if set(record) != {"dependencies", "path", "sha256"}:
        _fail(f"{label} fields are not exact")
    path = record.get("path")
    if not isinstance(path, str) or not path.startswith("/"):
        _fail(f"{label} path is invalid")
    _require_sha256(record.get("sha256"), f"{label} target")
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, dict) or not dependencies:
        _fail(f"{label} dynamic dependency inventory is empty")
    for name, item in dependencies.items():
        if not isinstance(name, str) or not name or not isinstance(item, dict):
            _fail(f"{label} dynamic dependency record is invalid: {name}")
        if set(item) != {"reported_path", "resolved_path", "sha256"}:
            _fail(f"{label} dynamic dependency fields are not exact: {name}")
        reported_path = item.get("reported_path")
        resolved_path = item.get("resolved_path")
        if (
            not isinstance(reported_path, str)
            or not reported_path.startswith("/")
            or not isinstance(resolved_path, str)
            or not resolved_path.startswith("/")
        ):
            _fail(f"{label} dynamic dependency path is invalid: {name}")
        _require_sha256(item.get("sha256"), f"{label} dynamic dependency {name}")
    return record


def _validate_native_linkage_record(record: object, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        _fail(f"{label} must be an object")
    if record.get("schema_version") != "mingli-native-linkage-v1":
        _fail(f"{label} schema mismatch")
    if record.get("node_version") != EXPECTED_NODE["version"]:
        _fail(f"{label} Node version mismatch")
    if record.get("libatomic1") != EXPECTED_LIBATOMIC:
        _fail(f"{label} libatomic1 provenance mismatch")
    targets = record.get("targets")
    if record.get("git_version") != EXPECTED_GIT["version"]:
        _fail(f"{label} Git version mismatch")
    expected_targets = {"git", "node", "python", "sxtwl", "yaml_c_extension"}
    if not isinstance(targets, dict) or set(targets) != expected_targets:
        _fail(f"{label} native target inventory mismatch")
    validated = {
        name: _validate_native_target(value, f"{label} {name}")
        for name, value in targets.items()
    }
    if validated["node"].get("path") != "/opt/node/bin/node":
        _fail(f"{label} Node path mismatch")
    if validated["git"].get("path") != EXPECTED_GIT["installed_binary_path"]:
        _fail(f"{label} Git path mismatch")
    if validated["git"].get("sha256") != EXPECTED_GIT["installed_binary_sha256"]:
        _fail(f"{label} Git executable digest mismatch")
    if validated["python"].get("path") != "/opt/mingli-runtime/venv/bin/python":
        _fail(f"{label} CPython path mismatch")
    for name in ("sxtwl", "yaml_c_extension"):
        path = validated[name].get("path")
        if not isinstance(path, str) or not path.startswith(
            "/opt/mingli-runtime/venv/"
        ):
            _fail(f"{label} extension path mismatch: {name}")
    if not Path(str(validated["sxtwl"]["path"])).name.startswith("_sxtwl."):
        _fail(f"{label} sxtwl native extension identity mismatch")
    if validated["sxtwl"].get("sha256") != EXPECTED_SXTWL_EXTENSION_SHA256:
        _fail(f"{label} sxtwl native extension digest mismatch")
    if not Path(str(validated["yaml_c_extension"]["path"])).name.startswith("_yaml."):
        _fail(f"{label} PyYAML C extension identity mismatch")
    node_dependencies = validated["node"]["dependencies"]
    if set(node_dependencies) != EXPECTED_NODE_LINKAGE:
        _fail(f"{label} Node dynamic dependency inventory mismatch")
    atomic = node_dependencies["libatomic.so.1"]
    if (
        atomic.get("resolved_path") != EXPECTED_LIBATOMIC["installed_path"]
        or atomic.get("sha256") != EXPECTED_LIBATOMIC["installed_sha256"]
    ):
        _fail(f"{label} is not bound to admitted libatomic1 bytes")
    if set(validated["git"]["dependencies"]) != EXPECTED_GIT_LINKAGE:
        _fail(f"{label} Git dynamic dependency inventory mismatch")
    if set(validated["sxtwl"]["dependencies"]) != EXPECTED_SXTWL_LINKAGE:
        _fail(f"{label} sxtwl dynamic dependency inventory mismatch")
    if "libstdc++.so.6" not in validated["sxtwl"]["dependencies"]:
        _fail(f"{label} sxtwl is not linked to the C++ runtime")
    return record


def _verify_state_root(state_root: Path) -> dict[str, int]:
    if (
        not state_root.is_absolute()
        or state_root.is_symlink()
        or not state_root.is_dir()
    ):
        _fail("state root is missing, relative, or unsafe")
    info = state_root.stat()
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o077:
        _fail("state root must not be accessible by group or others")
    if info.st_uid == 0:
        _fail("state root must be owned by a fixed non-root UID")
    return {"gid": info.st_gid, "mode": mode, "uid": info.st_uid}


def _git(
    source_root: Path,
    arguments: Sequence[str],
    *,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        check=False,
        capture_output=True,
        text=text,
        timeout=60,
    )
    if completed.returncode != 0:
        _fail(f"authoritative source git command failed: {' '.join(arguments)}")
    return completed


def _verify_research_source(
    release_root: Path,
    source_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, object]:
    source_root = source_root.resolve(strict=True)
    if source_root.is_symlink() or not (source_root / ".git").exists():
        _fail("authoritative regression source is not an independent Git checkout")
    head = _git(source_root, ["rev-parse", "HEAD"]).stdout.strip()
    if head != EXPECTED_RELEASE["source_commit"]:
        _fail("authoritative regression source commit mismatch")
    status = _git(
        source_root, ["status", "--porcelain", "--untracked-files=all"]
    ).stdout
    if status.strip():
        _fail("authoritative regression source checkout is not clean")
    raw_tree = _git(
        source_root,
        ["ls-tree", "-rz", "--full-tree", "-r", head],
        text=False,
    ).stdout
    tree_modes: dict[str, int] = {}
    expected_paths = set(manifest["files"])
    for raw_record in raw_tree.split(b"\0"):
        if not raw_record:
            continue
        metadata, encoded_path = raw_record.split(b"\t", 1)
        git_mode, object_type, _object_id = metadata.split(b" ", 2)
        relative = encoded_path.decode("utf-8")
        if relative not in expected_paths:
            continue
        if object_type != b"blob" or git_mode not in {b"100644", b"100755"}:
            _fail(f"authoritative source has an unsupported release object: {relative}")
        tree_modes[relative] = 0o755 if git_mode == b"100755" else 0o644
    if set(tree_modes) != expected_paths:
        _fail("authoritative regression source omits a signed release file")
    for relative, expected_digest in manifest["files"].items():
        source_path = _regular_file(source_root, relative, "authoritative source file")
        release_path = _regular_file(release_root, relative, "image release file")
        if sha256_file(source_path) != expected_digest:
            _fail(f"authoritative source release digest mismatch: {relative}")
        if sha256_file(release_path) != expected_digest:
            _fail(f"image/source release digest mismatch: {relative}")
        if tree_modes[relative] != manifest["modes"][relative]:
            _fail(f"authoritative source release mode mismatch: {relative}")
    reference_catalog = _load_json(
        source_root / "references/catalog/catalog.json",
        "authoritative reference catalog",
    )
    packs = reference_catalog.get("ready_reference_packs")
    if not isinstance(packs, list) or len(packs) != 55:
        _fail("authoritative regression source lacks the 55 reference packs")
    fulltext_count = 0
    for pack in packs:
        if not isinstance(pack, dict):
            _fail("authoritative reference pack record is invalid")
        fulltext = _regular_file(
            source_root,
            pack.get("local_fulltext_path"),
            "authoritative reference fulltext",
        )
        if sha256_file(fulltext) != pack.get("local_fulltext_sha256"):
            _fail("authoritative reference fulltext digest mismatch")
        fulltext_count += 1
    return {
        "clean": True,
        "fulltext_count": fulltext_count,
        "source_commit": head,
        "signed_release_files_matched": len(expected_paths),
    }


def validate_describe_payload(result: object, label: str) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("kind") != "described":
        _fail(f"{label} did not return Described")
    if result.get("protocol_version") != EXPECTED_RELEASE["protocol_version"]:
        _fail(f"{label} protocol mismatch")
    if result.get("manifest_digest") != EXPECTED_RELEASE["describe_digest"]:
        _fail(f"{label} manifest digest mismatch")
    capabilities = result.get("capabilities")
    if not isinstance(capabilities, list):
        _fail(f"{label} capabilities are invalid")
    provider_ids = {item.get("id") for item in capabilities if isinstance(item, dict)}
    if len(capabilities) != 13 or provider_ids != EXPECTED_PROVIDERS:
        _fail(f"{label} does not expose all 13 Provider capabilities")
    return result


def _run_describe(
    release_root: Path,
    runtime_python: Path,
    state_root: Path,
) -> dict[str, Any]:
    command = release_root / "scripts/run_reading_transaction.sh"
    environment = {
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "MINGLI_PYTHON": str(runtime_python),
        "MINGLI_STORE_ROOT": str(state_root),
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TZ": "UTC",
    }
    completed = subprocess.run(
        [str(command)],
        input='{"kind":"describe"}\n',
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        cwd=release_root,
        timeout=60,
    )
    if completed.returncode != 0 or completed.stderr.strip():
        _fail("portable describe process failed or emitted stderr")
    lines = completed.stdout.splitlines()
    if len(lines) != 1:
        _fail("portable describe must emit exactly one JSON line")
    try:
        result = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ReleaseVerificationError(
            "portable describe output is invalid JSON"
        ) from exc
    return validate_describe_payload(result, "portable describe")


def inspect_runtime(
    *,
    release_root: Path,
    runtime_python: Path | None = None,
    node: Path | None = None,
    git: Path | None = None,
    state_root: Path | None = None,
    research_source: Path | None = None,
    release_only: bool = False,
) -> dict[str, Any]:
    release_root = release_root.resolve(strict=True)
    if release_root.is_symlink() or not release_root.is_dir():
        _fail("release root is missing or unsafe")
    root_mode = stat.S_IMODE(release_root.stat().st_mode)
    if root_mode & 0o022:
        _fail("release root is writable by group or others")
    manifest = _read_release_manifest(release_root)
    release_files = _verify_release_files(release_root, manifest)
    closure = _verify_runtime_closure(release_root, set(manifest["files"]))
    _verify_version(release_root)
    provider_ids, readiness = _verify_provider_catalog(release_root)
    reference = _verify_reference_and_evidence(release_root)
    _verify_iztro(release_root)
    inventory: dict[str, Any] = {
        "schema_version": "mingli-runtime-inventory-v1",
        "release": dict(EXPECTED_RELEASE),
        "release_files": release_files,
        "release_manifest_sha256": EXPECTED_RELEASE["release_manifest_sha256"],
        "runtime_closure_paths": closure,
        "runtime_closure_verified": True,
        "provider_count": len(provider_ids),
        "provider_ids": provider_ids,
        "readiness": readiness,
        **reference,
    }
    if research_source is not None:
        inventory["authoritative_source"] = _verify_research_source(
            release_root,
            research_source,
            manifest,
        )
    if release_only:
        return inventory
    if runtime_python is None or node is None or git is None or state_root is None:
        _fail("full runtime inspection requires Python, Node, Git, and state root")
    runtime = _verify_runtime_python(release_root, runtime_python)
    node_record = _verify_node(node)
    git_record = _verify_git(git)
    native_linkage = inspect_native_linkage(runtime_python, node, git)
    state = _verify_state_root(state_root)
    first_describe = _run_describe(release_root, runtime_python, state_root)
    second_describe = _run_describe(release_root, runtime_python, state_root)
    if first_describe != second_describe:
        _fail("portable describe is not repeatable")
    inventory.update(
        {
            "describe": first_describe,
            "describe_output_sha256": canonical_sha256(first_describe),
            "git": git_record,
            "node": node_record,
            "native_linkage": native_linkage,
            "runtime_integrity": runtime,
            "state_root": state,
        }
    )
    return inventory


def _artifact_path(root: Path, relative: object, label: str) -> Path:
    return _regular_file(root, relative, label)


def _verify_artifact_digest(
    root: Path,
    relative: object,
    expected_digest: object,
    label: str,
) -> Path:
    path = _artifact_path(root, relative, label)
    digest = _require_sha256(expected_digest, f"{label} digest")
    if sha256_file(path) != digest:
        _fail(f"{label} digest does not match its bytes")
    return path


def _verify_inventory_artifact(
    report_inventory: object,
    inventory_path: Path,
    release_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    inventory = _load_json(inventory_path, "runtime inventory evidence")
    if inventory.get("schema_version") != "mingli-runtime-inventory-v1":
        _fail("runtime inventory evidence schema mismatch")
    release_files = inventory.get("release_files")
    closure = inventory.get("runtime_closure_paths")
    if not isinstance(release_files, dict) or len(release_files) != 217:
        _fail("runtime inventory evidence does not contain all 217 files")
    if not isinstance(closure, list) or set(closure) != set(release_files):
        _fail("runtime inventory evidence does not prove the 217-file closure")
    manifest_files = release_manifest.get("files")
    manifest_modes = release_manifest.get("modes")
    if not isinstance(manifest_files, dict) or not isinstance(manifest_modes, dict):
        _fail("release manifest evidence files/modes are invalid")
    if set(release_files) != set(manifest_files) or set(release_files) != set(
        manifest_modes
    ):
        _fail("runtime inventory does not match the signed 217-file manifest")
    for relative, item in release_files.items():
        _safe_relative(relative, "runtime inventory evidence")
        if not isinstance(item, dict):
            _fail("runtime inventory file record is invalid")
        _require_sha256(item.get("sha256"), f"runtime inventory {relative}")
        if item.get("mode") not in {0o644, 0o755}:
            _fail(f"runtime inventory mode is invalid: {relative}")
        if item.get("sha256") != manifest_files[relative]:
            _fail(f"runtime inventory digest differs from signed manifest: {relative}")
        if item.get("mode") != manifest_modes[relative]:
            _fail(f"runtime inventory mode differs from signed manifest: {relative}")
    if (
        release_files.get("SKILL.md", {}).get("sha256")
        != EXPECTED_RELEASE["skill_sha256"]
    ):
        _fail("runtime inventory SKILL.md digest mismatch")
    provider_ids = inventory.get("provider_ids")
    readiness = inventory.get("readiness")
    if (
        set(provider_ids or ()) != EXPECTED_PROVIDERS
        or inventory.get("provider_count") != 13
    ):
        _fail("runtime inventory does not prove the exact 13 Provider set")
    if not isinstance(readiness, dict) or set(readiness) != EXPECTED_PROVIDERS:
        _fail("runtime inventory 13 Provider readiness is incomplete")
    if not all(value is True for value in readiness.values()):
        _fail("runtime inventory does not prove 13/13 readiness")
    if inventory.get("reference_pack_count") != 55:
        _fail("runtime inventory does not prove 55/55 reference packs")
    if inventory.get("evidence_index_count") != 1328:
        _fail("runtime inventory does not prove all 1328 evidence rows")
    if inventory.get("evidence_rule_ids_unique") is not True:
        _fail("runtime inventory 1328 evidence rule IDs are not unique")
    if inventory.get("runtime_closure_verified") is not True:
        _fail("runtime inventory closure is not verified")
    describe = inventory.get("describe")
    if not isinstance(describe, dict):
        _fail("runtime inventory does not contain portable describe evidence")
    if describe.get("kind") != "described":
        _fail("runtime inventory portable describe kind mismatch")
    if describe.get("protocol_version") != EXPECTED_RELEASE["protocol_version"]:
        _fail("runtime inventory portable describe protocol mismatch")
    if describe.get("manifest_digest") != EXPECTED_RELEASE["describe_digest"]:
        _fail("runtime inventory portable describe digest mismatch")
    capabilities = describe.get("capabilities")
    if (
        not isinstance(capabilities, list)
        or {item.get("id") for item in capabilities if isinstance(item, dict)}
        != EXPECTED_PROVIDERS
    ):
        _fail("runtime inventory portable describe lacks the exact 13 Provider set")
    if inventory.get("describe_output_sha256") != canonical_sha256(describe):
        _fail("runtime inventory portable describe output digest mismatch")
    _validate_native_linkage_record(
        inventory.get("native_linkage"),
        "runtime inventory native linkage",
    )
    if not isinstance(report_inventory, dict):
        _fail("release report inventory must be an object")
    expected_projection = {
        "evidence_index_count": inventory["evidence_index_count"],
        "evidence_rule_ids_unique": inventory["evidence_rule_ids_unique"],
        "provider_count": inventory["provider_count"],
        "provider_ids": inventory["provider_ids"],
        "readiness": inventory["readiness"],
        "reference_pack_count": inventory["reference_pack_count"],
        "runtime_closure_verified": inventory["runtime_closure_verified"],
    }
    if report_inventory != expected_projection:
        if report_inventory.get("evidence_index_count") != 1328:
            _fail("release report does not match the recomputed 1328 evidence rows")
        if (
            report_inventory.get("provider_count") != 13
            or set(report_inventory.get("provider_ids", ())) != EXPECTED_PROVIDERS
            or set(report_inventory.get("readiness", {})) != EXPECTED_PROVIDERS
        ):
            _fail("release report does not match the exact 13 Provider inventory")
        _fail("release report inventory differs from the recomputed runtime inventory")
    return inventory


def _verify_source_binding_artifact(
    inventory_path: Path,
    release_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    inventory = _load_json(inventory_path, "authoritative source binding evidence")
    if inventory.get("schema_version") != "mingli-runtime-inventory-v1":
        _fail("authoritative source binding schema mismatch")
    if inventory.get("release") != EXPECTED_RELEASE:
        _fail("authoritative source binding release identity mismatch")
    if (
        inventory.get("release_manifest_sha256")
        != EXPECTED_RELEASE["release_manifest_sha256"]
    ):
        _fail("authoritative source binding manifest digest mismatch")
    files = inventory.get("release_files")
    manifest_files = release_manifest.get("files")
    manifest_modes = release_manifest.get("modes")
    if (
        not isinstance(files, dict)
        or not isinstance(manifest_files, dict)
        or not isinstance(manifest_modes, dict)
        or set(files) != set(manifest_files)
        or set(files) != set(manifest_modes)
        or len(files) != 217
    ):
        _fail("authoritative source binding does not cover the signed 217 files")
    for relative, record in files.items():
        _safe_relative(relative, "authoritative source binding")
        if not isinstance(record, dict) or record != {
            "mode": manifest_modes[relative],
            "sha256": manifest_files[relative],
        }:
            _fail(f"authoritative source binding file mismatch: {relative}")
    closure = inventory.get("runtime_closure_paths")
    if not isinstance(closure, list) or set(closure) != set(files):
        _fail("authoritative source binding runtime closure mismatch")
    if inventory.get("runtime_closure_verified") is not True:
        _fail("authoritative source binding runtime closure is unverified")
    if (
        inventory.get("provider_count") != 13
        or set(inventory.get("provider_ids") or ()) != EXPECTED_PROVIDERS
        or inventory.get("readiness")
        != {provider: True for provider in sorted(EXPECTED_PROVIDERS)}
    ):
        _fail("authoritative source binding does not prove all 13 Providers")
    if (
        inventory.get("reference_pack_count") != 55
        or inventory.get("evidence_index_count") != 1328
        or inventory.get("evidence_rule_ids_unique") is not True
    ):
        _fail("authoritative source binding does not close 55/1328 assets")
    expected_source = {
        "clean": True,
        "fulltext_count": 55,
        "signed_release_files_matched": 217,
        "source_commit": EXPECTED_RELEASE["source_commit"],
    }
    if inventory.get("authoritative_source") != expected_source:
        _fail("authoritative source binding is not a clean exact commit")
    forbidden_runtime_fields = {
        "describe",
        "native_linkage",
        "git",
        "node",
        "runtime_integrity",
        "state_root",
    }
    if forbidden_runtime_fields & set(inventory):
        _fail("source binding must remain a release-only audit artifact")
    return inventory


def _verify_sbom(path: Path, report: Mapping[str, Any]) -> None:
    sbom = _load_json(path, "SBOM")
    if (
        sbom.get("bomFormat") != "CycloneDX"
        or sbom.get("specVersion") != "1.6"
        or sbom.get("version") != 1
    ):
        _fail("SBOM is not CycloneDX")
    components = sbom.get("components")
    if not isinstance(components, list):
        _fail("SBOM components are missing")
    component_refs = [
        item.get("bom-ref") for item in components if isinstance(item, dict)
    ]
    if len(component_refs) != len(components) or len(set(component_refs)) != len(
        component_refs
    ):
        _fail("SBOM component references are missing or duplicated")
    identities = [
        (item.get("name"), item.get("version"))
        for item in components
        if isinstance(item, dict)
    ]
    if len(set(identities)) != len(identities):
        _fail("SBOM component identities are duplicated")
    by_identity = {
        (item.get("name"), item.get("version")): item
        for item in components
        if isinstance(item, dict)
    }
    required = {
        ("cpython", "3.14.6"),
        ("python-base-image", "3.14.6-slim-bookworm"),
        ("git", EXPECTED_GIT["version"]),
        ("node", EXPECTED_NODE["version"]),
        ("iztro", "2.5.8"),
        ("PyYAML", "6.0.3"),
        ("sxtwl", "2.0.7"),
        ("astronomy-engine", "2.1.19"),
        ("cnlunar", "0.2.4"),
        ("libatomic1", EXPECTED_LIBATOMIC["version"]),
    }
    if not required <= set(by_identity):
        _fail("SBOM omits a required Python, Git, Node, or vendored component")

    artifact = report.get("artifact")
    if not isinstance(artifact, dict):
        _fail("release report artifact is missing for SBOM binding")
    metadata = sbom.get("metadata")
    if not isinstance(metadata, dict):
        _fail("SBOM metadata is missing")
    root_component = metadata.get("component")
    if not isinstance(root_component, dict) or {
        "name": root_component.get("name"),
        "type": root_component.get("type"),
        "version": root_component.get("version"),
    } != {"name": "mingli-v51-runtime", "type": "container", "version": "5.1"}:
        _fail("SBOM root component identity mismatch")
    expected_root_ref = f"mingli:runtime-image@{artifact.get('image_digest')}"
    if root_component.get("bom-ref") != expected_root_ref:
        _fail("SBOM root component is not bound to the production image")
    root_properties = {
        item.get("name"): item.get("value")
        for item in root_component.get("properties") or ()
        if isinstance(item, dict)
    }
    if root_properties != {
        "mingli:base-image-manifest-digest": EXPECTED_BASE_IMAGE[
            "linux_amd64_manifest_digest"
        ],
        IMAGE_DIGEST_PROPERTY: artifact.get("image_digest"),
        "mingli:native-linkage-sha256": report.get(
            "runtime_native_linkage_identity", {}
        ).get("payload_sha256"),
        "mingli:release-manifest-sha256": EXPECTED_RELEASE["release_manifest_sha256"],
        "mingli:runtime-integrity-sha256": artifact.get("runtime_integrity_sha256"),
    }:
        _fail("SBOM root properties are not bound to admitted image artifacts")
    tools = metadata.get("tools")
    if tools != {
        "components": [
            {
                "name": "mingli-emit-sbom",
                "type": "application",
                "version": "1",
            }
        ]
    }:
        _fail("SBOM generator identity mismatch")
    if sbom.get("dependencies") != [
        {"dependsOn": sorted(component_refs), "ref": expected_root_ref}
    ]:
        _fail("SBOM dependency graph is not bound to every component")

    def component_hashes(identity: tuple[str, str]) -> set[object]:
        hashes = by_identity[identity].get("hashes")
        if not isinstance(hashes, list):
            _fail(f"SBOM component has no hashes: {identity[0]}")
        return {
            item.get("content")
            for item in hashes
            if isinstance(item, dict) and item.get("alg") == "SHA-256"
        }

    base_digest = EXPECTED_BASE_IMAGE["linux_amd64_manifest_digest"]
    if component_hashes(("python-base-image", "3.14.6-slim-bookworm")) != {
        str(base_digest).removeprefix("sha256:")
    }:
        _fail("SBOM base image amd64 digest mismatch")
    cpython_hashes = component_hashes(("cpython", "3.14.6"))
    if len(cpython_hashes) != 1:
        _fail("SBOM CPython installed binary digest is not exact")
    _require_sha256(next(iter(cpython_hashes)), "SBOM CPython installed binary")
    cpython_properties = {
        item.get("name"): item.get("value")
        for item in by_identity[("cpython", "3.14.6")].get("properties") or ()
        if isinstance(item, dict)
    }
    if cpython_properties != {
        "mingli:installed-path": "/opt/mingli-runtime/venv/bin/python"
    }:
        _fail("SBOM CPython installed path mismatch")
    for component_name, expected in EXPECTED_PYTHON_ARTIFACTS.items():
        version = str(expected["version"])
        expected_hash = expected.get("wheel_sha256", expected.get("sha256"))
        if component_hashes((component_name, version)) != {expected_hash}:
            _fail(f"SBOM Python artifact SHA-256 mismatch: {component_name}")
        properties = by_identity[(component_name, version)].get("properties")
        property_map = {
            item.get("name"): item.get("value")
            for item in properties or ()
            if isinstance(item, dict)
        }
        _require_sha256(
            property_map.get("mingli:installed-files-sha256"),
            f"SBOM {component_name} installed tree",
        )
        expected_filename = expected.get("wheel_filename", expected.get("filename"))
        if property_map.get("mingli:artifact-filename") != expected_filename:
            _fail(f"SBOM Python artifact filename mismatch: {component_name}")
    git_identity = ("git", EXPECTED_GIT["version"])
    if component_hashes(git_identity) != {EXPECTED_GIT["source_sha256"]}:
        _fail("SBOM Git source archive SHA-256 mismatch")
    git_component = by_identity[git_identity]
    if git_component.get("licenses") != [{"license": {"id": EXPECTED_GIT["license"]}}]:
        _fail("SBOM Git license identity mismatch")
    git_properties = {
        item.get("name"): item.get("value")
        for item in git_component.get("properties") or ()
        if isinstance(item, dict)
    }
    expected_git_properties = {
        "mingli:artifact-filename": str(EXPECTED_GIT["source_filename"]),
        "mingli:build-config-json": json.dumps(
            EXPECTED_GIT_BUILD_CONFIG,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "mingli:build-config-path": str(EXPECTED_GIT["build_config_path"]),
        "mingli:build-config-sha256": str(EXPECTED_GIT["build_config_sha256"]),
        "mingli:installed-binary-sha256": str(EXPECTED_GIT["installed_binary_sha256"]),
        "mingli:installed-path": str(EXPECTED_GIT["installed_binary_path"]),
        "mingli:installed-tree-content-bytes": str(
            EXPECTED_GIT["installed_tree_content_bytes"]
        ),
        "mingli:installed-tree-entry-count": str(
            EXPECTED_GIT["installed_tree_entry_count"]
        ),
        "mingli:installed-tree-regular-file-count": str(
            EXPECTED_GIT["installed_tree_regular_file_count"]
        ),
        "mingli:installed-tree-sha256": str(EXPECTED_GIT["installed_tree_sha256"]),
        "mingli:installed-tree-symlink-count": str(
            EXPECTED_GIT["installed_tree_symlink_count"]
        ),
        "mingli:license-path": str(EXPECTED_GIT["license_path"]),
        "mingli:license-sha256": str(EXPECTED_GIT["license_sha256"]),
        "mingli:source-url": str(EXPECTED_GIT["source_url"]),
    }
    if git_properties != expected_git_properties:
        _fail("SBOM Git build/provenance properties mismatch")
    node_hashes = by_identity[("node", EXPECTED_NODE["version"])].get("hashes")
    if not isinstance(node_hashes, list) or {
        item.get("content")
        for item in node_hashes
        if isinstance(item, dict) and item.get("alg") == "SHA-256"
    } != {EXPECTED_NODE["sha256"]}:
        _fail("SBOM Node tarball SHA-256 provenance mismatch")
    node_properties = {
        item.get("name"): item.get("value")
        for item in by_identity[("node", EXPECTED_NODE["version"])].get("properties")
        or ()
        if isinstance(item, dict)
    }
    _require_sha256(
        node_properties.get("mingli:installed-binary-sha256"),
        "SBOM Node installed binary",
    )
    if {
        key: value
        for key, value in node_properties.items()
        if key != "mingli:installed-binary-sha256"
    } != {
        "mingli:artifact-filename": EXPECTED_NODE["filename"],
        "mingli:source-url": "https://nodejs.org/dist/v26.3.0/node-v26.3.0-linux-x64.tar.gz",
    }:
        _fail("SBOM Node provenance properties mismatch")
    iztro_hashes = by_identity[("iztro", "2.5.8")].get("hashes")
    if EXPECTED_IZTRO_SHA256 not in {
        item.get("content") for item in iztro_hashes or () if isinstance(item, dict)
    }:
        _fail("SBOM vendored iztro SHA-256 provenance mismatch")
    iztro_properties = {
        item.get("name"): item.get("value")
        for item in by_identity[("iztro", "2.5.8")].get("properties") or ()
        if isinstance(item, dict)
    }
    if iztro_properties != {
        "mingli:npm-tarball-sha256": (
            "8293c6a587de521b0713e45826745ba4b7482fc507bd2da43fc820cadf06deca"
        ),
        "mingli:release-path": "vendor/iztro-2.5.8/iztro.min.js",
    }:
        _fail("SBOM iztro provenance properties mismatch")
    sxtwl_properties = by_identity[("sxtwl", "2.0.7")].get("properties")
    property_map = {
        item.get("name"): item.get("value")
        for item in sxtwl_properties or ()
        if isinstance(item, dict)
    }
    if (
        property_map.get("mingli:source-sdist-sha256")
        != EXPECTED_PYTHON_ARTIFACTS["sxtwl"]["sdist_sha256"]
    ):
        _fail("SBOM sxtwl source sdist SHA-256 provenance mismatch")
    libatomic_identity = ("libatomic1", EXPECTED_LIBATOMIC["version"])
    if component_hashes(libatomic_identity) != {EXPECTED_LIBATOMIC["sha256"]}:
        _fail("SBOM libatomic1 amd64 package SHA-256 mismatch")
    libatomic_component = by_identity[libatomic_identity]
    if libatomic_component.get("licenses") != [
        {"expression": EXPECTED_LIBATOMIC["license"]}
    ]:
        _fail("SBOM libatomic1 license expression mismatch")
    libatomic_properties = {
        item.get("name"): item.get("value")
        for item in libatomic_component.get("properties") or ()
        if isinstance(item, dict)
    }
    if libatomic_properties != {
        "mingli:architecture": EXPECTED_LIBATOMIC["architecture"],
        "mingli:artifact-filename": EXPECTED_LIBATOMIC["filename"],
        "mingli:installed-path": EXPECTED_LIBATOMIC["installed_path"],
        "mingli:installed-sha256": EXPECTED_LIBATOMIC["installed_sha256"],
        "mingli:soname-path": EXPECTED_LIBATOMIC["soname_path"],
        "mingli:soname-target": EXPECTED_LIBATOMIC["soname_target"],
        "mingli:fetch-url": EXPECTED_LIBATOMIC["fetch_url"],
        "mingli:origin-url": EXPECTED_LIBATOMIC["origin_url"],
        "mingli:snapshot-timestamp": EXPECTED_LIBATOMIC["snapshot_timestamp"],
    }:
        _fail("SBOM libatomic1 installed/provenance properties mismatch")
    if report.get("target", {}).get("node_version") != EXPECTED_NODE["version"]:
        _fail("release report Node version differs from SBOM provenance")


def _command_map(
    commands: object,
    *,
    artifacts_root: Path,
    image_id: str,
    audit_image_id: str,
) -> dict[str, dict[str, Any]]:
    if audit_image_id != image_id:
        _fail("audit command map spans different OCI image identities")
    if not isinstance(commands, list) or not commands:
        _fail("audit contains no executed commands")
    indexed: dict[str, dict[str, Any]] = {}
    for command in commands:
        if not isinstance(command, dict):
            _fail("audit command evidence must be an object")
        command_id = command.get("id")
        if not isinstance(command_id, str) or not command_id or command_id in indexed:
            _fail("audit command id is missing or duplicated")
        argv = command.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(item, str) or not item for item in argv)
        ):
            _fail(f"audit command argv is invalid: {command_id}")
        cwd = command.get("cwd")
        if not isinstance(cwd, str) or not cwd.startswith("/"):
            _fail(f"audit command cwd is invalid: {command_id}")
        if command.get("exit_code") != 0:
            _fail(f"audit command did not exit zero: {command_id}")
        executed_in = command.get("executed_in_image_id")
        if executed_in != image_id:
            _fail(f"audit command image identity mismatch: {command_id}")
        _require_command_budget(command, label=f"audit command {command_id}")
        stdout = _verify_artifact_digest(
            artifacts_root,
            command.get("stdout_path"),
            command.get("stdout_sha256"),
            f"command {command_id} stdout",
        )
        stderr = _verify_artifact_digest(
            artifacts_root,
            command.get("stderr_path"),
            command.get("stderr_sha256"),
            f"command {command_id} stderr",
        )
        indexed[command_id] = {**command, "stdout_file": stdout, "stderr_file": stderr}
    return indexed


def _require_command_budget(
    command: Mapping[str, Any],
    *,
    expected_timeout_seconds: int | None = None,
    label: str,
) -> None:
    timeout = command.get("timeout_seconds")
    elapsed = command.get("elapsed_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        _fail(f"{label} timeout budget is invalid")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or elapsed < 0
        or elapsed > timeout
    ):
        _fail(f"{label} elapsed time is outside its timeout budget")
    if expected_timeout_seconds is not None and timeout != expected_timeout_seconds:
        _fail(f"{label} timeout budget differs from the frozen Gate budget")


def _require_command(
    commands: Mapping[str, Mapping[str, Any]],
    command_id: str,
    *,
    argv: Sequence[str],
    cwd: str,
    image_id: str,
) -> Mapping[str, Any]:
    command = commands.get(command_id)
    if command is None:
        _fail(f"required audit command is missing: {command_id}")
    if command.get("argv") != list(argv):
        _fail(f"audit command argv drift: {command_id}")
    if command.get("cwd") != cwd:
        _fail(f"audit command cwd drift: {command_id}")
    if command.get("executed_in_image_id") != image_id:
        _fail(f"audit command ran in the wrong image: {command_id}")
    return command


def _require_successful_command_ids(
    section: object,
    commands: Mapping[str, Mapping[str, Any]],
    label: str,
) -> None:
    if not isinstance(section, dict) or section.get("status") != "passed":
        _fail(f"{label} did not pass")
    command_ids = section.get("command_ids")
    if not isinstance(command_ids, list) or not command_ids:
        _fail(f"{label} has no command evidence")
    if any(command_id not in commands for command_id in command_ids):
        _fail(f"{label} references unknown command evidence")


def _command_stdout_text(command: Mapping[str, Any], label: str) -> str:
    path = command.get("stdout_file")
    if not isinstance(path, Path):
        _fail(f"{label} stdout artifact is not resolved")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseVerificationError(f"{label} stdout is unreadable") from exc


def _verify_matrix_input_binding(
    command: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    path = command.get("stdout_file")
    if not isinstance(path, Path):
        _fail(f"{label} stdout artifact is not resolved")
    payload = _load_json(path, label)
    expected = {
        "generator_input_fingerprint": EXPECTED_GENERATOR_INPUT_FINGERPRINT,
        "matrix_path": ("/audit-source/references/matrices/provider-completeness.yaml"),
        "matrix_sha256": EXPECTED_PROVIDER_MATRIX_SHA256,
        "provider_count": 13,
        "schema_version": "mingli-matrix-input-binding-v1",
        "signed_generator_input_fingerprint": (EXPECTED_GENERATOR_INPUT_FINGERPRINT),
        "source_filesystem_read_only": True,
        "source_root": "/audit-source",
    }
    if payload != expected:
        _fail(f"{label} does not bind the frozen read-only matrix inputs")
    return payload


def _verify_provider_matrix(
    section: object,
    evidence: Mapping[str, Any],
    commands: Mapping[str, Mapping[str, Any]],
    *,
    artifacts_root: Path,
    image_id: str,
    run_id: str,
) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise ReleaseVerificationError(
            "PyYAML is unavailable for Provider matrix verification"
        ) from exc
    matrix_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("provider_matrix_path"),
        evidence.get("provider_matrix_sha256"),
        "frozen Provider matrix",
    )
    if (
        evidence.get("provider_matrix_path") != "evidence/provider-completeness.yaml"
        or evidence.get("provider_matrix_sha256") != EXPECTED_PROVIDER_MATRIX_SHA256
    ):
        _fail("Provider matrix artifact is not the frozen source-commit byte stream")
    try:
        matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ReleaseVerificationError(
            "frozen Provider matrix is invalid YAML"
        ) from exc
    if not isinstance(matrix, dict):
        _fail("frozen Provider matrix must be an object")
    inputs = matrix.get("inputs")
    providers = matrix.get("providers")
    if (
        matrix.get("schema_version") != "mingli-provider-completeness-v1"
        or not isinstance(inputs, dict)
        or inputs.get("generator_input_fingerprint")
        != EXPECTED_GENERATOR_INPUT_FINGERPRINT
        or not isinstance(providers, dict)
        or set(providers) != EXPECTED_PROVIDERS
    ):
        _fail("frozen Provider matrix semantics are incomplete")

    before = _verify_matrix_input_binding(
        commands["matrix-input-before"],
        "matrix input binding before Matrix A/B",
    )
    after = _verify_matrix_input_binding(
        commands["matrix-input-after"],
        "matrix input binding after Matrix A/B",
    )
    if before != after:
        _fail("matrix inputs changed between Matrix A and Matrix B")

    regression = commands["release-regression"]
    matrix_a_matches = list(
        MATRIX_TARGET_RE.finditer(
            _command_stdout_text(regression, "release regression")
        )
    )
    if len(matrix_a_matches) != 1:
        _fail("Canonical Matrix A target is missing, failed, or duplicated")
    matrix_a = matrix_a_matches[0]
    matrix_a_tests = int(matrix_a.group("tests"))
    matrix_a_elapsed = float(matrix_a.group("elapsed"))
    if (
        matrix_a_tests != 2
        or matrix_a_elapsed < 0
        or matrix_a_elapsed > regression["timeout_seconds"]
    ):
        _fail("Canonical Matrix A target evidence is outside the frozen contract")

    try:
        matrix_b_payload = yaml.safe_load(
            _command_stdout_text(commands["provider-matrix-b"], "Matrix B")
        )
    except yaml.YAMLError as exc:
        raise ReleaseVerificationError("Matrix B stdout is invalid YAML") from exc
    expected_matrix_b = {
        "findings": [],
        "provider_count": 13,
        "provider_ready": True,
        "schema_version": "mingli-provider-completeness-audit-v1",
    }
    if matrix_b_payload != expected_matrix_b:
        _fail("Matrix B machine output is not exactly 13/13 ready")

    expected_section = {
        "executed_in_image_id": image_id,
        "generator_input_fingerprint": EXPECTED_GENERATOR_INPUT_FINGERPRINT,
        "input_binding_command_ids": [
            "matrix-input-before",
            "matrix-input-after",
        ],
        "matrix_path": "evidence/provider-completeness.yaml",
        "matrix_sha256": EXPECTED_PROVIDER_MATRIX_SHA256,
        "run_id": run_id,
        "runs": [
            {
                "command_id": "release-regression",
                "elapsed_seconds": matrix_a_elapsed,
                "target": MATRIX_TARGET,
                "test_count": 2,
                "timeout_seconds": EXPECTED_RELEASE_REGRESSION_TIMEOUT_SECONDS,
            },
            {
                "command_id": "provider-matrix-b",
                "elapsed_seconds": commands["provider-matrix-b"]["elapsed_seconds"],
                "provider_count": 13,
                "timeout_seconds": EXPECTED_PROVIDER_MATRIX_TIMEOUT_SECONDS,
            },
        ],
        "source_commit": EXPECTED_RELEASE["source_commit"],
        "status": "passed",
    }
    if section != expected_section:
        _fail("Provider Matrix A/B report binding is not exact")


def _verify_production_evidence(
    evidence_path: Path,
    *,
    artifacts_root: Path,
    image_id: str,
    run_id: str,
    commands: Mapping[str, Mapping[str, Any]],
    report: Mapping[str, Any],
) -> None:
    production = _load_json(evidence_path, "production image evidence")
    if production.get("schema_version") != "mingli-production-evidence-v1":
        _fail("production image evidence schema mismatch")
    if production.get("generated_by") != "/opt/mingli-runtime/audit_runtime.py":
        _fail("production image evidence generator mismatch")
    if production.get("image_id") != image_id:
        _fail("production image evidence image identity mismatch")
    if production.get("run_id") != run_id:
        _fail("production image evidence run identity mismatch")
    raw_commands = production.get("commands")
    if not isinstance(raw_commands, list):
        _fail("production image evidence command list is missing")
    indexed: dict[str, dict[str, Any]] = {}
    for record in raw_commands:
        if not isinstance(record, dict):
            _fail("production image command record is invalid")
        command_id = record.get("id")
        if not isinstance(command_id, str) or command_id in indexed:
            _fail("production image command identity is invalid")
        indexed[command_id] = record
    if set(indexed) != EXPECTED_PRODUCTION_COMMAND_IDS:
        _fail("production image command inventory is not exact")
    for command_id, production_record in indexed.items():
        final_record = commands.get(command_id)
        if final_record is None:
            _fail(f"production image command absent from final report: {command_id}")
        normalized = {
            key: value
            for key, value in final_record.items()
            if key not in {"stdout_file", "stderr_file"}
        }
        if production_record != normalized:
            _fail(f"production command changed during audit finalization: {command_id}")
        if production_record.get("executed_in_image_id") != image_id:
            _fail(f"core Gate did not execute in production: {command_id}")
    files = production.get("files")
    if not isinstance(files, dict):
        _fail("production image evidence file inventory is missing")
    expected_files = {
        "evidence/dependency-provenance.json",
        "evidence/provider-completeness.yaml",
        "evidence/release-manifest.json",
        "evidence/runtime-integrity.json",
        "evidence/runtime-inventory.json",
        "sbom.cdx.json",
    }
    for command in indexed.values():
        expected_files.add(_safe_relative(command.get("stdout_path"), "production"))
        expected_files.add(_safe_relative(command.get("stderr_path"), "production"))
    if set(files) != expected_files:
        _fail("production image evidence file inventory is not exact")
    for relative, digest in files.items():
        _verify_artifact_digest(
            artifacts_root,
            relative,
            digest,
            f"production image evidence {relative}",
        )
    for field in (
        "characterization",
        "git_smoke",
        "inventory",
        "p0_trajectories",
        "probes",
        "provider_matrix",
        "release_regression",
        "target",
    ):
        if production.get(field) != report.get(field):
            _fail(f"final report changed production image evidence: {field}")


def _verify_tree_identity(
    section: object,
    commands: Mapping[str, Mapping[str, Any]],
) -> None:
    if not isinstance(section, dict) or section.get("status") != "passed":
        _fail("production/audit runtime tree identity did not pass")
    production_id = section.get("production_command_id")
    audit_id = section.get("audit_command_id")
    if (production_id, audit_id) != (
        "production-tree-identity",
        "audit-tree-identity",
    ):
        _fail("runtime tree identity command binding mismatch")
    production = commands["production-tree-identity"]
    audit = commands["audit-tree-identity"]
    digest = _require_sha256(section.get("sha256"), "runtime tree identity")
    if (
        production.get("stdout_sha256") != digest
        or audit.get("stdout_sha256") != digest
    ):
        _fail("production and audit runtime tree stdout digests differ")
    first = _load_json(production["stdout_file"], "production runtime tree identity")
    second = _load_json(audit["stdout_file"], "audit runtime tree identity")
    if first != second:
        _fail("derived audit stage changed the admitted runtime trees")
    if first.get("schema_version") != "mingli-runtime-tree-identity-v1":
        _fail("runtime tree identity schema mismatch")
    trees = first.get("trees")
    expected_paths = {
        "git": "/opt/git",
        "node": "/opt/node",
        "release": "/opt/mingli-master",
        "runtime_venv": "/opt/mingli-runtime/venv",
    }
    if not isinstance(trees, dict) or set(trees) != set(expected_paths):
        _fail("runtime tree identity does not cover the four admitted trees")
    for name, expected_path in expected_paths.items():
        record = trees[name]
        if (
            not isinstance(record, dict)
            or record.get("path") != expected_path
            or not isinstance(record.get("content_bytes"), int)
            or record["content_bytes"] <= 0
            or not isinstance(record.get("entry_count"), int)
            or record["entry_count"] <= 0
            or not isinstance(record.get("regular_file_count"), int)
            or record["regular_file_count"] <= 0
            or not isinstance(record.get("regular_file_bytes"), int)
            or record["regular_file_bytes"] <= 0
            or not isinstance(record.get("symlink_count"), int)
            or record["symlink_count"] < 0
            or not isinstance(record.get("symlink_target_bytes"), int)
            or record["symlink_target_bytes"] < 0
        ):
            _fail(f"runtime tree identity record is invalid: {name}")
        _require_sha256(record.get("sha256"), f"runtime tree identity {name}")
    expected_git_tree = {
        "content_bytes": EXPECTED_GIT["installed_tree_content_bytes"],
        "entry_count": EXPECTED_GIT["installed_tree_entry_count"],
        "path": EXPECTED_GIT["installed_tree_path"],
        "regular_file_bytes": EXPECTED_GIT["installed_tree_regular_file_bytes"],
        "regular_file_count": EXPECTED_GIT["installed_tree_regular_file_count"],
        "sha256": EXPECTED_GIT["installed_tree_sha256"],
        "symlink_count": EXPECTED_GIT["installed_tree_symlink_count"],
        "symlink_target_bytes": EXPECTED_GIT["installed_tree_symlink_target_bytes"],
    }
    if trees["git"] != expected_git_tree:
        _fail("Git runtime tree does not match the admitted deterministic install")


def _verify_git_smoke(
    section: object,
    commands: Mapping[str, Mapping[str, Any]],
) -> None:
    if section != {
        "command_id": "git-smoke",
        "output_sha256": commands["git-smoke"].get("stdout_sha256"),
        "status": "passed",
    }:
        _fail("Git smoke report binding mismatch")
    command = commands["git-smoke"]
    if command.get("stderr_sha256") != hashlib.sha256(b"").hexdigest():
        _fail("Git smoke emitted stderr")
    payload = _load_json(command["stdout_file"], "Git smoke machine output")
    validate_git_smoke_payload(payload)


def _verify_native_linkage_identity(
    section: object,
    commands: Mapping[str, Mapping[str, Any]],
    runtime_inventory: Mapping[str, Any],
) -> None:
    if not isinstance(section, dict) or section.get("status") != "passed":
        _fail("production/audit native linkage identity did not pass")
    if (
        section.get("production_command_id"),
        section.get("audit_command_id"),
    ) != ("production-native-linkage", "audit-native-linkage"):
        _fail("native linkage identity command binding mismatch")
    if section.get("targets") != [
        "git",
        "node",
        "python",
        "sxtwl",
        "yaml_c_extension",
    ]:
        _fail("native linkage identity target inventory mismatch")
    digest = _require_sha256(section.get("sha256"), "native linkage identity")
    production = commands["production-native-linkage"]
    audit = commands["audit-native-linkage"]
    if (
        production.get("stdout_sha256") != digest
        or audit.get("stdout_sha256") != digest
    ):
        _fail("production and audit native linkage stdout digests differ")
    first = _load_json(production["stdout_file"], "production native linkage")
    second = _load_json(audit["stdout_file"], "audit native linkage")
    if first != second:
        _fail("derived audit stage changed native runtime linkage")
    _validate_native_linkage_record(first, "production/audit native linkage")
    if section.get("payload_sha256") != canonical_sha256(first):
        _fail("native linkage canonical payload digest mismatch")
    if runtime_inventory.get("native_linkage") != first:
        _fail("runtime inventory and native linkage command evidence differ")


def _backup_docker_run_boundary(
    commands: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    command = commands.get("source-describe")
    argv = command.get("argv") if isinstance(command, Mapping) else None
    allowed = (
        ["--platform=linux/amd64"],
        [
            "--platform=linux/amd64",
            "--device=lima-vm.io/rosetta=cached",
        ],
    )
    if isinstance(argv, list) and argv[:2] == ["docker", "run"]:
        for boundary in allowed:
            end = 2 + len(boundary)
            if argv[2:end] == boundary and argv[end : end + 1] == ["--rm"]:
                return list(boundary)
    _fail("backup/restore container boundary is missing or unsafe")


def _verify_backup_restore(
    section: object,
    evidence_path: Path,
    image_digest: str,
    artifacts_root: Path,
) -> None:
    evidence = _load_json(evidence_path, "backup/restore evidence")
    if evidence.get("schema_version") != "mingli-backup-restore-v1":
        _fail("backup/restore evidence schema mismatch")
    if evidence.get("image_digest") != image_digest:
        _fail("backup/restore evidence used a different production image")
    volume_ids = evidence.get("volume_ids")
    if not isinstance(volume_ids, dict) or set(volume_ids) != {
        "accepted_restore_blank",
        "prepared_restore_blank",
        "source",
    }:
        _fail("backup/restore evidence does not name three volume roles")
    if len(set(volume_ids.values())) != 3 or any(
        not value for value in volume_ids.values()
    ):
        _fail("backup/restore did not use distinct blank destination volumes")
    if evidence.get("blank_volume_checks") != {
        "accepted_restore_blank": True,
        "prepared_restore_blank": True,
    }:
        _fail("backup/restore did not prove both restore volumes started blank")
    snapshots = evidence.get("snapshots")
    if not isinstance(snapshots, dict) or set(snapshots) != {"accepted", "prepared"}:
        _fail("backup/restore snapshot artifacts are incomplete")
    snapshot_command_ids = {
        "accepted": ("accepted-snapshot-capture", "accepted-snapshot-seal"),
        "prepared": ("prepared-snapshot-capture", "prepared-snapshot-seal"),
    }
    for name, snapshot in snapshots.items():
        if not isinstance(snapshot, dict):
            _fail(f"backup/restore snapshot record is invalid: {name}")
        if snapshot.get("encryption") != "xor-one-time-pad-key-destroyed":
            _fail(f"backup/restore snapshot is not safely sealed: {name}")
        capture_id, seal_id = snapshot_command_ids[name]
        if snapshot.get("capture_command_id") != capture_id:
            _fail(f"backup/restore snapshot capture binding failed: {name}")
        if snapshot.get("seal_command_id") != seal_id:
            _fail(f"backup/restore snapshot seal binding failed: {name}")
        ciphertext = _verify_artifact_digest(
            artifacts_root,
            snapshot.get("ciphertext_path"),
            snapshot.get("ciphertext_sha256"),
            f"backup/restore {name} snapshot ciphertext",
        )
        _require_sha256(
            snapshot.get("plaintext_sha256"),
            f"backup/restore {name} snapshot plaintext",
        )
        if (
            snapshot.get("byte_count") != ciphertext.stat().st_size
            or ciphertext.stat().st_size <= 0
        ):
            _fail(f"backup/restore snapshot byte count mismatch: {name}")

    expected_command_ids = {
        "accepted-complete-replay",
        "accepted-followup-complete",
        "accepted-followup-prepare",
        "accepted-followup-token-record",
        "accepted-restore",
        "accepted-restore-describe",
        "accepted-restore-state-root-identity",
        "accepted-restore-volume-empty",
        "accepted-snapshot-capture",
        "accepted-snapshot-seal",
        "prepared-restore",
        "prepared-restore-describe",
        "prepared-restore-state-root-identity",
        "prepared-restore-volume-empty",
        "prepared-restored-complete",
        "prepared-snapshot-capture",
        "prepared-snapshot-seal",
        "prepared-token-replay",
        "source-complete",
        "source-describe",
        "source-pending-prepare",
        "source-prepare",
        "source-prepared-token-record",
        "source-state-root-identity",
    }
    command_records = evidence.get("commands")
    if not isinstance(command_records, list):
        _fail("backup/restore command evidence is missing")
    commands: dict[str, dict[str, Any]] = {}
    runtime_command_ids = {
        "accepted-complete-replay",
        "accepted-followup-complete",
        "accepted-followup-prepare",
        "accepted-restore-describe",
        "prepared-restore-describe",
        "prepared-restored-complete",
        "prepared-token-replay",
        "source-complete",
        "source-describe",
        "source-pending-prepare",
        "source-prepare",
    }
    for command in command_records:
        if not isinstance(command, dict):
            _fail("backup/restore command record is invalid")
        command_id = command.get("id")
        if not isinstance(command_id, str) or command_id in commands:
            _fail("backup/restore command id is missing or duplicated")
        if command.get("exit_code") != 0:
            _fail(f"backup/restore command did not exit zero: {command_id}")
        argv = command.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(item, str) or not item for item in argv)
        ):
            _fail(f"backup/restore command argv is invalid: {command_id}")
        if any("state_token" in item for item in argv):
            _fail(f"backup/restore command argv leaked a state token: {command_id}")
        if command_id in runtime_command_ids and image_digest not in argv:
            _fail(
                f"backup/restore runtime command used a different image: {command_id}"
            )
        stdout_file = _verify_artifact_digest(
            artifacts_root,
            command.get("stdout_path"),
            command.get("stdout_sha256"),
            f"backup/restore command {command_id} stdout",
        )
        stderr_file = _verify_artifact_digest(
            artifacts_root,
            command.get("stderr_path"),
            command.get("stderr_sha256"),
            f"backup/restore command {command_id} stderr",
        )
        commands[command_id] = {
            **command,
            "stderr_file": stderr_file,
            "stdout_file": stdout_file,
        }
    if set(commands) != expected_command_ids:
        _fail("backup/restore command inventory is not exact")
    docker_run_boundary = _backup_docker_run_boundary(commands)
    runtime_tmpfs = "/tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777"
    command_volume_roles = {
        "accepted-complete-replay": "accepted_restore_blank",
        "accepted-followup-complete": "prepared_restore_blank",
        "accepted-followup-prepare": "prepared_restore_blank",
        "accepted-restore-describe": "accepted_restore_blank",
        "prepared-restore-describe": "prepared_restore_blank",
        "prepared-restored-complete": "prepared_restore_blank",
        "prepared-token-replay": "prepared_restore_blank",
        "source-complete": "source",
        "source-describe": "source",
        "source-pending-prepare": "source",
        "source-prepare": "source",
    }
    describe_command_ids = {
        "accepted-restore-describe",
        "prepared-restore-describe",
        "source-describe",
    }
    for command_id, role in command_volume_roles.items():
        expected_argv = [
            "docker",
            "run",
            *docker_run_boundary,
            "--rm",
            "-i",
            "--network=none",
            "--tmpfs",
            runtime_tmpfs,
            "--mount",
            f"source={volume_ids[role]},target=/var/lib/mingli",
            image_digest,
        ]
        if commands[command_id].get("argv") != expected_argv:
            _fail(f"backup runtime command argv drift: {command_id}")
        expected_capture = (
            "describe-result-v1"
            if command_id in describe_command_ids
            else "sanitized-runtime-result-v1"
        )
        if commands[command_id].get("stdout_capture") != expected_capture:
            _fail(f"backup runtime command capture drift: {command_id}")
    token_record_roles = {
        "accepted-followup-token-record": "prepared_restore_blank",
        "source-prepared-token-record": "source",
    }
    for command_id, role in token_record_roles.items():
        expected_argv = [
            "docker",
            "run",
            *docker_run_boundary,
            "--rm",
            "-i",
            "--network=none",
            "--read-only",
            "--tmpfs",
            runtime_tmpfs,
            "--mount",
            f"source={volume_ids[role]},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/opt/mingli-runtime/venv/bin/python",
            image_digest,
            "-B",
            "/opt/mingli-runtime/audit_runtime.py",
            "--emit-token-record",
            "--state-root",
            "/var/lib/mingli",
        ]
        if commands[command_id].get("argv") != expected_argv:
            _fail(f"backup token-record command argv drift: {command_id}")
        if commands[command_id].get("stdout_capture") != "token-record-audit-v1":
            _fail(f"backup token-record command capture drift: {command_id}")
    state_root_roles = {
        "accepted-restore-state-root-identity": "accepted_restore_blank",
        "prepared-restore-state-root-identity": "prepared_restore_blank",
        "source-state-root-identity": "source",
    }
    for command_id, role in state_root_roles.items():
        expected_argv = [
            "docker",
            "run",
            *docker_run_boundary,
            "--rm",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume_ids[role]},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/opt/mingli-runtime/venv/bin/python",
            image_digest,
            "-B",
            "/opt/mingli-runtime/audit_runtime.py",
            "--emit-state-root-identity",
            "--state-root",
            "/var/lib/mingli",
        ]
        if commands[command_id].get("argv") != expected_argv:
            _fail(f"backup state-root identity command argv drift: {command_id}")
        if commands[command_id].get("stdout_capture") != "state-root-identity-v1":
            _fail(f"backup state-root identity capture drift: {command_id}")
    empty_roles = {
        "accepted-restore-volume-empty": "accepted_restore_blank",
        "prepared-restore-volume-empty": "prepared_restore_blank",
    }
    for command_id, role in empty_roles.items():
        expected_argv = [
            "docker",
            "run",
            *docker_run_boundary,
            "--rm",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume_ids[role]},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/usr/bin/find",
            image_digest,
            "/var/lib/mingli",
            "-mindepth",
            "1",
            "-print",
            "-quit",
        ]
        if commands[command_id].get("argv") != expected_argv:
            _fail(f"blank volume command argv drift: {command_id}")
    snapshot_roles = {
        "accepted": ("source", "accepted_restore_blank"),
        "prepared": ("source", "prepared_restore_blank"),
    }
    for name, (capture_role, restore_role) in snapshot_roles.items():
        capture_id = f"{name}-snapshot-capture"
        capture_argv = [
            "docker",
            "run",
            *docker_run_boundary,
            "--rm",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume_ids[capture_role]},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/bin/tar",
            image_digest,
            "-C",
            "/var/lib/mingli",
            "-cf",
            "-",
            ".",
        ]
        if commands[capture_id].get("argv") != capture_argv:
            _fail(f"snapshot capture command argv drift: {name}")
        restore_id = f"{name}-restore"
        restore_argv = [
            "docker",
            "run",
            *docker_run_boundary,
            "--rm",
            "-i",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume_ids[restore_role]},target=/var/lib/mingli",
            "--entrypoint",
            "/bin/tar",
            image_digest,
            "-C",
            "/var/lib/mingli",
            "-xf",
            "-",
        ]
        if commands[restore_id].get("argv") != restore_argv:
            _fail(f"snapshot restore command argv drift: {name}")
        seal_id = f"{name}-snapshot-seal"
        ciphertext_path = snapshots[name]["ciphertext_path"]
        if commands[seal_id].get("argv") != [
            "in-process:xor-one-time-pad",
            name,
            ciphertext_path,
        ]:
            _fail(f"snapshot seal command argv drift: {name}")
        capture_receipt = _load_json(
            commands[capture_id]["stdout_file"],
            f"{name} snapshot capture receipt",
        )
        seal_receipt = _load_json(
            commands[seal_id]["stdout_file"],
            f"{name} snapshot seal receipt",
        )
        restore_receipt = _load_json(
            commands[restore_id]["stdout_file"],
            f"{name} snapshot restore receipt",
        )
        expected_capture = {
            "byte_count": snapshots[name]["byte_count"],
            "plaintext_sha256": snapshots[name]["plaintext_sha256"],
            "schema_version": "mingli-snapshot-capture-v1",
        }
        if capture_receipt != expected_capture:
            _fail(f"snapshot capture receipt binding failed: {name}")
        expected_seal = {
            "byte_count": snapshots[name]["byte_count"],
            "ciphertext_sha256": snapshots[name]["ciphertext_sha256"],
            "plaintext_sha256": snapshots[name]["plaintext_sha256"],
            "schema_version": "mingli-snapshot-seal-v1",
        }
        if seal_receipt != expected_seal:
            _fail(f"snapshot seal receipt binding failed: {name}")
        if restore_receipt != {
            "key_destroyed": True,
            "plaintext_buffer_destroyed": True,
            "schema_version": "mingli-snapshot-restore-v1",
        }:
            _fail(f"snapshot restore receipt binding failed: {name}")

    restore_environment = evidence.get("restore_environment")
    if not isinstance(restore_environment, dict):
        _fail("backup/restore environment evidence is missing")
    expected_roles = {"accepted_restore", "prepared_restore", "source"}

    def load_bound_output(
        bindings: object,
        role: str,
        command_id: str,
        label: str,
    ) -> dict[str, Any]:
        if not isinstance(bindings, dict) or set(bindings) != expected_roles:
            _fail(f"backup/restore {label} bindings are incomplete")
        binding = bindings[role]
        command = commands[command_id]
        if (
            not isinstance(binding, dict)
            or binding.get("command_id") != command_id
            or binding.get("path") != command.get("stdout_path")
            or binding.get("sha256") != command.get("stdout_sha256")
        ):
            _fail(f"backup/restore {label} binding failed: {role}")
        return _load_json(command["stdout_file"], f"backup/restore {label} {role}")

    describe_ids = {
        "accepted_restore": "accepted-restore-describe",
        "prepared_restore": "prepared-restore-describe",
        "source": "source-describe",
    }
    describes = {
        role: validate_describe_payload(
            load_bound_output(
                restore_environment.get("describes"),
                role,
                command_id,
                "describe",
            ),
            f"backup/restore {role} describe",
        )
        for role, command_id in describe_ids.items()
    }
    describe_hashes = {
        commands[command_id].get("stdout_sha256")
        for command_id in describe_ids.values()
    }
    if (
        restore_environment.get("describe_byte_identical") is not True
        or len(describe_hashes) != 1
        or len({canonical_sha256(item) for item in describes.values()}) != 1
    ):
        _fail("backup/restore describe results are not byte-identical")

    state_root_ids = {
        "accepted_restore": "accepted-restore-state-root-identity",
        "prepared_restore": "prepared-restore-state-root-identity",
        "source": "source-state-root-identity",
    }
    state_roots = {
        role: load_bound_output(
            restore_environment.get("state_roots"),
            role,
            command_id,
            "state-root identity",
        )
        for role, command_id in state_root_ids.items()
    }
    identity_pairs: set[tuple[int, int]] = set()
    for role, item in state_roots.items():
        if item.get("schema_version") != "mingli-state-root-identity-v1":
            _fail(f"backup/restore state-root identity schema mismatch: {role}")
        if {
            "gid": item.get("gid"),
            "mode": item.get("mode"),
            "path": item.get("path"),
            "uid": item.get("uid"),
        } != {
            "gid": 10001,
            "mode": 0o700,
            "path": "/var/lib/mingli",
            "uid": 10001,
        }:
            _fail(f"backup/restore state-root invariant mismatch: {role}")
        st_dev = item.get("st_dev")
        st_ino = item.get("st_ino")
        if (
            not isinstance(st_dev, int)
            or st_dev <= 0
            or not isinstance(st_ino, int)
            or st_ino <= 0
        ):
            _fail(f"backup/restore device/inode evidence is invalid: {role}")
        identity_pairs.add((st_dev, st_ino))
    expected_constraints = {
        "device_inode_values_may_change": True,
        "must_match": {
            "gid": 10001,
            "mode": 0o700,
            "path": "/var/lib/mingli",
            "uid": 10001,
        },
        "root_identity_pairs_distinct": True,
    }
    if (
        restore_environment.get("constraints") != expected_constraints
        or len(identity_pairs) != 3
    ):
        _fail("backup/restore filesystem identity constraints are unproven")

    transcript_ids = {
        "accepted-replay": "accepted-complete-replay",
        "accepted-followup-accepted": "accepted-followup-complete",
        "accepted-followup-prepared": "accepted-followup-prepare",
        "prepared-replay": "prepared-token-replay",
        "prepared-restored-accepted": "prepared-restored-complete",
        "source-accepted": "source-complete",
        "source-pending": "source-pending-prepare",
        "source-prepared": "source-prepare",
    }
    transcript_records = evidence.get("transcripts")
    if not isinstance(transcript_records, dict) or set(transcript_records) != set(
        transcript_ids
    ):
        _fail("backup/restore sanitized transcripts are incomplete")
    transcripts: dict[str, dict[str, Any]] = {}
    for transcript_id, command_id in transcript_ids.items():
        record = transcript_records[transcript_id]
        if not isinstance(record, dict) or record.get("command_id") != command_id:
            _fail(f"backup/restore transcript command binding failed: {transcript_id}")
        if record.get("path") != commands[command_id].get("stdout_path"):
            _fail(f"backup/restore transcript is not command stdout: {transcript_id}")
        if record.get("sha256") != commands[command_id].get("stdout_sha256"):
            _fail(
                f"backup/restore transcript digest is not command stdout: {transcript_id}"
            )
        transcript_path = _verify_artifact_digest(
            artifacts_root,
            record.get("path"),
            record.get("sha256"),
            f"backup/restore transcript {transcript_id}",
        )
        transcript = _load_json(
            transcript_path,
            f"backup/restore transcript {transcript_id}",
        )
        if transcript.get("schema_version") != "mingli-sanitized-runtime-result-v1":
            _fail(f"backup/restore transcript schema mismatch: {transcript_id}")
        if transcript.get("redaction") != "state-token-sha256-fingerprint":
            _fail(f"backup/restore transcript redaction mismatch: {transcript_id}")
        for field in (
            "command_sha256",
            "result_bytes_sha256",
            "token_fingerprint",
        ):
            _require_sha256(transcript.get(field), f"{transcript_id} {field}")
        if transcript.get("input_token_fingerprint") is not None:
            _require_sha256(
                transcript.get("input_token_fingerprint"),
                f"{transcript_id} input token fingerprint",
            )
        if transcript.get("kind") == "accepted":
            _require_sha256(
                transcript.get("public_copy_sha256"),
                f"{transcript_id} public copy",
            )
        elif transcript.get("kind") == "prepared":
            for field in ("brief_sha256", "question_sha256"):
                _require_sha256(transcript.get(field), f"{transcript_id} {field}")
            if transcript.get("prior_answer_sha256") is not None:
                _require_sha256(
                    transcript.get("prior_answer_sha256"),
                    f"{transcript_id} prior answer",
                )
        elif transcript.get("kind") == "stopped":
            if transcript.get("reason") != "need_input":
                _fail(f"backup/restore Stopped reason mismatch: {transcript_id}")
            _require_sha256(
                transcript.get("public_copy_sha256"),
                f"{transcript_id} public copy",
            )
        else:
            _fail(f"backup/restore transcript kind mismatch: {transcript_id}")
        transcripts[transcript_id] = transcript

    token_record_ids = {
        "accepted-followup": "accepted-followup-token-record",
        "source-prepared": "source-prepared-token-record",
    }
    raw_token_records = evidence.get("token_records")
    if not isinstance(raw_token_records, dict) or set(raw_token_records) != set(
        token_record_ids
    ):
        _fail("backup/restore token-record evidence is incomplete")
    token_records: dict[str, dict[str, Any]] = {}
    for record_id, command_id in token_record_ids.items():
        binding = raw_token_records[record_id]
        if not isinstance(binding, dict) or binding.get("command_id") != command_id:
            _fail(f"backup token-record command binding failed: {record_id}")
        if binding.get("path") != commands[command_id].get("stdout_path"):
            _fail(f"backup token-record is not command stdout: {record_id}")
        if binding.get("sha256") != commands[command_id].get("stdout_sha256"):
            _fail(f"backup token-record digest is not command stdout: {record_id}")
        token_record_path = _verify_artifact_digest(
            artifacts_root,
            binding.get("path"),
            binding.get("sha256"),
            f"backup token-record {record_id}",
        )
        token_record = _load_json(token_record_path, f"backup token-record {record_id}")
        if token_record.get("schema_version") != "mingli-token-record-audit-v1":
            _fail(f"backup token-record schema mismatch: {record_id}")
        for field in (
            "reading_id_sha256",
            "token_fingerprint",
        ):
            _require_sha256(token_record.get(field), f"{record_id} {field}")
        if token_record.get("parent_token_fingerprint") is not None:
            _require_sha256(
                token_record.get("parent_token_fingerprint"),
                f"{record_id} parent token",
            )
        if not isinstance(token_record.get("version"), int):
            _fail(f"backup token-record version is invalid: {record_id}")
        token_records[record_id] = token_record

    source_pending = transcripts["source-pending"]
    source_prepared = transcripts["source-prepared"]
    prepared_replay = transcripts["prepared-replay"]
    prepared_restored_accepted = transcripts["prepared-restored-accepted"]
    followup = transcripts["accepted-followup-prepared"]
    followup_accepted = transcripts["accepted-followup-accepted"]
    source_accepted = transcripts["source-accepted"]
    accepted_replay = transcripts["accepted-replay"]
    source_fingerprint = source_prepared.get("token_fingerprint")
    if (
        source_pending.get("kind") != "stopped"
        or source_pending.get("reason") != "need_input"
        or source_pending.get("input_token_fingerprint") is not None
        or source_prepared.get("input_token_fingerprint")
        != source_pending.get("token_fingerprint")
        or source_fingerprint != source_pending.get("token_fingerprint")
    ):
        _fail("pending token did not promote atomically into Prepared")
    if (
        source_prepared.get("kind") != "prepared"
        or prepared_replay.get("kind") != "prepared"
    ):
        _fail("Prepared backup did not restore into a Prepared replay")
    if prepared_replay.get("input_token_fingerprint") != source_fingerprint:
        _fail("Prepared replay did not use the restored source token")
    if prepared_replay.get("token_fingerprint") != source_fingerprint:
        _fail("Prepared replay did not preserve the state token")
    for field in ("brief_sha256", "result_bytes_sha256"):
        if prepared_replay.get(field) != source_prepared.get(field):
            _fail(f"Prepared replay was not byte-identical: {field}")
    if prepared_restored_accepted.get("kind") != "accepted" or (
        prepared_restored_accepted.get("input_token_fingerprint") != source_fingerprint
    ):
        _fail("restored Prepared token was not completed")
    if followup.get("kind") != "prepared":
        _fail("Accepted parent did not create a real follow-up Prepared")
    if followup.get("input_token_fingerprint") != source_fingerprint:
        _fail("Accepted follow-up did not use the restored accepted token")
    if followup.get("token_fingerprint") == source_fingerprint:
        _fail("Accepted follow-up did not create a child token")
    if followup.get("prior_answer_sha256") != source_accepted.get("public_copy_sha256"):
        _fail("Accepted follow-up prior_answer is not bound to the original copy")
    if followup.get("question_sha256") == source_prepared.get("question_sha256"):
        _fail("Accepted follow-up did not use a new query")
    if followup_accepted.get("input_token_fingerprint") != followup.get(
        "token_fingerprint"
    ):
        _fail("Prepared follow-up completion did not use the restored child token")
    if source_accepted.get("kind") != "accepted" or accepted_replay.get("kind") != (
        "accepted"
    ):
        _fail("Accepted backup replay did not return Accepted")
    if accepted_replay.get("input_token_fingerprint") != source_fingerprint:
        _fail("Accepted replay did not use the original Prepared token")
    if accepted_replay.get("token_fingerprint") != source_accepted.get(
        "token_fingerprint"
    ):
        _fail("Accepted replay did not return the original Accepted token")
    original_completions = (
        source_accepted,
        prepared_restored_accepted,
        accepted_replay,
    )
    if len({item.get("command_sha256") for item in original_completions}) != 1:
        _fail("restored Accepted paths did not use the byte-identical Complete command")
    if len({item.get("result_bytes_sha256") for item in original_completions}) != 1:
        _fail("restored Accepted paths did not return byte-identical Accepted")
    copy_digests = {item.get("public_copy_sha256") for item in original_completions}
    if len(copy_digests) != 1 or None in copy_digests:
        _fail("backup/restore public_copy bytes were not identical")
    source_token_record = token_records["source-prepared"]
    child_token_record = token_records["accepted-followup"]
    if source_token_record != {
        "parent_token_fingerprint": None,
        "phase": "prepared",
        "reading_id_sha256": source_token_record.get("reading_id_sha256"),
        "schema_version": "mingli-token-record-audit-v1",
        "token_fingerprint": source_fingerprint,
        "version": 1,
    }:
        _fail("source Prepared token record does not prove version 1")
    if (
        child_token_record.get("phase") != "prepared"
        or child_token_record.get("version") != 2
        or child_token_record.get("token_fingerprint")
        != followup.get("token_fingerprint")
        or child_token_record.get("parent_token_fingerprint") != source_fingerprint
        or child_token_record.get("reading_id_sha256")
        == source_token_record.get("reading_id_sha256")
    ):
        _fail("Accepted follow-up token record does not prove child version 2")
    if any(evidence.get(field) is not True for field in EXPECTED_BACKUP_FLAGS):
        _fail("backup/restore semantic evidence flags are incomplete")
    if "state_token" in json.dumps(evidence, sort_keys=True):
        _fail("backup/restore evidence must not contain a plaintext state token")
    if not isinstance(section, dict) or section.get("status") != "passed":
        _fail("backup/restore report section did not pass")
    for field in EXPECTED_BACKUP_FLAGS:
        if section.get(field) is not evidence.get(field):
            _fail(f"backup/restore report differs from evidence: {field}")
    if section.get("command_ids") != sorted(expected_command_ids):
        _fail("backup/restore report command inventory is not exact")


def validate_audit_report(
    report: Mapping[str, Any],
    *,
    artifacts_root: Path,
) -> None:
    """Validate a generated report and recompute every referenced digest."""

    artifacts_root = artifacts_root.resolve(strict=True)
    if not isinstance(report, Mapping):
        _fail("release report must be an object")
    if report.get("schema_version") != "mingli-linux-runtime-audit-v1":
        _fail("release report schema mismatch")
    _require_exact_mapping(report.get("release"), EXPECTED_RELEASE, "release identity")
    target = report.get("target")
    if not isinstance(target, dict) or target.get("os") != "linux":
        _fail("release target must be Linux")
    expected_target = {
        "architecture": "x86_64",
        "base_image_digest": EXPECTED_BASE_IMAGE["linux_amd64_manifest_digest"],
        "os": "linux",
        "python_path": "/opt/mingli-runtime/venv/bin/python",
        "python_version": "3.14.6",
        "release_root": "/opt/mingli-master",
        "state_root": "/var/lib/mingli",
    }
    for key, value in expected_target.items():
        if target.get(key) != value:
            _fail(f"release target mismatch: {key}")
    if not isinstance(target.get("uid"), int) or target["uid"] <= 0:
        _fail("release target UID must be non-root")
    if target.get("node_version") != EXPECTED_NODE["version"]:
        _fail("release target Node version mismatch")
    if target.get("git_version") != EXPECTED_GIT["version"]:
        _fail("release target Git version mismatch")

    artifact = report.get("artifact")
    evidence = report.get("evidence")
    audit = report.get("audit")
    if (
        not isinstance(artifact, dict)
        or not isinstance(evidence, dict)
        or not isinstance(audit, dict)
    ):
        _fail("release artifact/evidence sections are missing")
    image_digest = _require_image_digest(artifact.get("image_digest"), "image digest")
    image_id = _require_image_digest(audit.get("image_id"), "image ID")
    audit_image_id = _require_image_digest(
        audit.get("audit_image_id"),
        "audit image ID",
    )
    if artifact.get("image_digest_kind") != IMAGE_DIGEST_KIND:
        _fail("production image digest kind must be the OCI index digest")
    if not (image_digest == image_id == audit_image_id):
        _fail(
            "artifact, production, and audit image IDs must be the same OCI index digest"
        )
    if (
        artifact.get("base_image_digest")
        != EXPECTED_BASE_IMAGE["linux_amd64_manifest_digest"]
    ):
        _fail("production artifact base image amd64 digest mismatch")
    sbom_path = _verify_artifact_digest(
        artifacts_root,
        artifact.get("sbom_path"),
        artifact.get("sbom_sha256"),
        "SBOM",
    )
    runtime_integrity_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("runtime_integrity_path"),
        artifact.get("runtime_integrity_sha256"),
        "runtime-integrity",
    )
    runtime_integrity = _load_json(runtime_integrity_path, "runtime-integrity evidence")
    if runtime_integrity.get("distributions") != EXPECTED_DISTRIBUTIONS:
        _fail("runtime-integrity evidence distribution set mismatch")
    manifest_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("release_manifest_path"),
        EXPECTED_RELEASE["release_manifest_sha256"],
        "release manifest evidence",
    )
    manifest = _load_json(manifest_path, "release manifest evidence")
    if len(manifest.get("files", {})) != 217:
        _fail("release manifest evidence does not contain exactly 217 files")
    production_evidence_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("production_evidence_path"),
        evidence.get("production_evidence_sha256"),
        "production image evidence",
    )
    source_binding_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("source_binding_path"),
        evidence.get("source_binding_sha256"),
        "authoritative source binding",
    )
    _verify_source_binding_artifact(source_binding_path, manifest)
    inventory_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("runtime_inventory_path"),
        evidence.get("runtime_inventory_sha256"),
        "runtime inventory evidence",
    )
    runtime_inventory = _verify_inventory_artifact(
        report.get("inventory"),
        inventory_path,
        manifest,
    )
    provenance_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("dependency_provenance_path"),
        evidence.get("dependency_provenance_sha256"),
        "dependency provenance",
    )
    provenance = _load_json(provenance_path, "dependency provenance")
    if provenance.get("base_image") != EXPECTED_BASE_IMAGE:
        _fail("base image provenance differs from the frozen amd64 digest")
    if provenance.get("node") != {
        **EXPECTED_NODE,
        "license": "MIT",
        "source_url": ("https://nodejs.org/dist/v26.3.0/node-v26.3.0-linux-x64.tar.gz"),
    }:
        _fail("Node 26.3.0 tarball provenance mismatch")
    if provenance.get("system_runtime") != {"libatomic1": EXPECTED_LIBATOMIC}:
        _fail("libatomic1 frozen system-runtime provenance mismatch")
    if provenance.get("git") != EXPECTED_GIT:
        _fail("Git frozen dependency provenance mismatch")
    dependencies = report.get("dependencies")
    if not isinstance(dependencies, dict):
        _fail("release dependency projection is missing")
    if dependencies.get("node") != provenance.get("node"):
        _fail("release dependency Node provenance differs from audited bytes")
    python_distributions = provenance.get("python_distributions")
    if not isinstance(python_distributions, dict):
        _fail("Python dependency provenance is missing")
    if set(python_distributions) != set(EXPECTED_PYTHON_ARTIFACTS):
        _fail("Python dependency provenance set mismatch")
    for name, expected in EXPECTED_PYTHON_ARTIFACTS.items():
        actual = python_distributions.get(name)
        if not isinstance(actual, dict):
            _fail(f"Python dependency provenance is missing: {name}")
        for key, value in expected.items():
            if actual.get(key) != value:
                _fail(f"Python dependency frozen provenance mismatch: {name}/{key}")
    expected_dependency_projection = {
        "astronomy-engine": python_distributions.get("astronomy-engine"),
        "cnlunar": python_distributions.get("cnlunar"),
        "git": provenance.get("git"),
        "node": provenance.get("node"),
        "pyyaml": python_distributions.get("PyYAML"),
        "sxtwl": python_distributions.get("sxtwl"),
        "iztro": provenance.get("vendored", {}).get("iztro"),
        "libatomic1": provenance.get("system_runtime", {}).get("libatomic1"),
    }
    if dependencies != expected_dependency_projection:
        _fail("release dependencies differ from recomputed provenance")
    runtime_binding = runtime_inventory.get("runtime_integrity")
    if not isinstance(runtime_binding, dict):
        _fail("runtime inventory lacks runtime-integrity binding")
    if runtime_binding.get("manifest_sha256") != artifact.get(
        "runtime_integrity_sha256"
    ):
        _fail("runtime inventory and report runtime-integrity digest differ")
    if runtime_inventory.get("node") != EXPECTED_NODE:
        _fail("runtime inventory Node record differs from frozen provenance")
    git_inventory = runtime_inventory.get("git")
    if (
        not isinstance(git_inventory, dict)
        or git_inventory.get("binary_sha256") != EXPECTED_GIT["installed_binary_sha256"]
        or git_inventory.get("build_config_sha256")
        != EXPECTED_GIT["build_config_sha256"]
        or git_inventory.get("tree", {}).get("sha256")
        != EXPECTED_GIT["installed_tree_sha256"]
    ):
        _fail("runtime inventory Git record differs from frozen provenance")
    state_root_record = runtime_inventory.get("state_root")
    if (
        not isinstance(state_root_record, dict)
        or state_root_record.get("uid") != target["uid"]
    ):
        _fail("runtime inventory state UID differs from the release target")
    if runtime_inventory.get("release") != EXPECTED_RELEASE:
        _fail("runtime inventory release identity mismatch")
    _verify_sbom(sbom_path, report)

    product_policy = report.get("product_policy")
    if not isinstance(product_policy, dict) or set(
        product_policy.get("p0_provider_ids", ())
    ) != (EXPECTED_P0_PROVIDERS):
        _fail("P0 Product Capability Policy is not the frozen three-entry allowlist")
    if audit.get("generator") != "/opt/mingli-runtime/audit_runtime.py":
        _fail("audit report was not generated by the image entry point")
    completed_at = audit.get("completed_at")
    if (
        not isinstance(completed_at, str)
        or re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            completed_at,
        )
        is None
    ):
        _fail("audit completion timestamp is invalid")
    run_id = audit.get("run_id")
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        _fail("audit run identity is malformed or absent")
    commands = _command_map(
        audit.get("commands"),
        artifacts_root=artifacts_root,
        image_id=image_id,
        audit_image_id=audit_image_id,
    )
    expected_command_ids = EXPECTED_PRODUCTION_COMMAND_IDS | EXPECTED_AUDIT_COMMAND_IDS
    if set(commands) != expected_command_ids:
        _fail("audit command inventory differs from the frozen Linux Gate")
    runtime_path = "/opt/mingli-runtime/venv/bin/python"
    audit_script = "/opt/mingli-runtime/audit_runtime.py"
    source_root = "/audit-source"
    research_root = "/audit-research"
    output_root = "/audit-output"
    production_output_root = "/production-output"
    matrix_path = "/audit-source/references/matrices/provider-completeness.yaml"
    sbom_command = _require_command(
        commands,
        "sbom-regeneration",
        argv=(runtime_path, "-B", "/opt/mingli-runtime/emit_sbom.py"),
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    if artifact.get("sbom_command_id") != "sbom-regeneration":
        _fail("SBOM artifact is not bound to its in-image generator command")
    if sbom_command.get("stdout_sha256") != artifact.get("sbom_sha256"):
        _fail("SBOM bytes differ from the in-image generator stdout")
    inventory_command = _require_command(
        commands,
        "runtime-inventory",
        argv=(
            runtime_path,
            "-B",
            "/opt/mingli-runtime/verify_release.py",
            "--release-root",
            "/opt/mingli-master",
            "--runtime-python",
            runtime_path,
            "--node",
            "/opt/node/bin/node",
            "--git",
            "/opt/git/bin/git",
            "--state-root",
            "/var/lib/mingli",
            "--inventory-output",
            f"{production_output_root}/evidence/runtime-inventory.json",
        ),
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    if inventory_command.get("stdout_sha256") != hashlib.sha256(b"").hexdigest():
        _fail("runtime inventory command emitted unexpected stdout")
    source_binding_command = _require_command(
        commands,
        "source-binding",
        argv=(
            runtime_path,
            "-B",
            "/opt/mingli-runtime/verify_release.py",
            "--release-root",
            "/opt/mingli-master",
            "--research-source",
            research_root,
            "--release-only",
            "--inventory-output",
            f"{output_root}/evidence/source-binding.json",
        ),
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    if source_binding_command.get("stdout_sha256") != hashlib.sha256(b"").hexdigest():
        _fail("authoritative source binding command emitted unexpected stdout")
    source_binding_section = report.get("source_binding")
    if source_binding_section != {
        "command_id": "source-binding",
        "status": "passed",
    }:
        _fail("authoritative source binding report section mismatch")
    _require_command(
        commands,
        "git-smoke",
        argv=(runtime_path, "-B", audit_script, "--emit-git-smoke"),
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    _verify_git_smoke(report.get("git_smoke"), commands)
    tree_argv = (runtime_path, "-B", audit_script, "--emit-tree-identity")
    _require_command(
        commands,
        "production-tree-identity",
        argv=tree_argv,
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    _require_command(
        commands,
        "audit-tree-identity",
        argv=tree_argv,
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    _verify_tree_identity(report.get("runtime_tree_identity"), commands)
    native_linkage_argv = (
        runtime_path,
        "-B",
        audit_script,
        "--emit-native-linkage",
    )
    _require_command(
        commands,
        "production-native-linkage",
        argv=native_linkage_argv,
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    _require_command(
        commands,
        "audit-native-linkage",
        argv=native_linkage_argv,
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    _verify_native_linkage_identity(
        report.get("runtime_native_linkage_identity"),
        commands,
        runtime_inventory,
    )
    _verify_production_evidence(
        production_evidence_path,
        artifacts_root=artifacts_root,
        image_id=image_id,
        run_id=run_id,
        commands=commands,
        report=report,
    )
    matrix_binding_argv = (
        runtime_path,
        "-B",
        audit_script,
        "--emit-matrix-input-binding",
        "--source-root",
        source_root,
    )
    for command_id in ("matrix-input-before", "matrix-input-after"):
        _require_command(
            commands,
            command_id,
            argv=matrix_binding_argv,
            cwd=source_root,
            image_id=image_id,
        )
        _require_command_budget(
            commands[command_id],
            expected_timeout_seconds=EXPECTED_MATRIX_BINDING_TIMEOUT_SECONDS,
            label=command_id,
        )
    matrix_argv = (
        runtime_path,
        "-B",
        "/audit-source/scripts/audit_provider_completeness.py",
        "--check",
        "--matrix",
        matrix_path,
    )
    _require_command(
        commands,
        "provider-matrix-b",
        argv=matrix_argv,
        cwd=source_root,
        image_id=image_id,
    )
    _require_command_budget(
        commands["provider-matrix-b"],
        expected_timeout_seconds=EXPECTED_PROVIDER_MATRIX_TIMEOUT_SECONDS,
        label="provider-matrix-b",
    )
    _verify_provider_matrix(
        report.get("provider_matrix"),
        evidence,
        commands,
        artifacts_root=artifacts_root,
        image_id=image_id,
        run_id=run_id,
    )
    characterization_argv = (
        runtime_path,
        "-B",
        audit_script,
        "--emit-characterization",
        "--source-root",
        source_root,
    )
    for command_id in ("characterization-a", "characterization-b"):
        _require_command(
            commands,
            command_id,
            argv=characterization_argv,
            cwd=source_root,
            image_id=image_id,
        )
    if (
        commands["characterization-a"]["stdout_sha256"]
        != commands["characterization-b"]["stdout_sha256"]
    ):
        _fail("13 Provider characterization output changed across two runs")
    characterization_a = _load_json(
        commands["characterization-a"]["stdout_file"],
        "first characterization command output",
    )
    characterization_b = _load_json(
        commands["characterization-b"]["stdout_file"],
        "second characterization command output",
    )
    if characterization_a != characterization_b:
        _fail("13 Provider characterization JSON changed across two runs")
    if characterization_a.get("schema_version") != "mingli-characterization-v1":
        _fail("characterization machine output schema mismatch")
    characterization_outputs = characterization_a.get("providers")
    if not isinstance(characterization_outputs, dict) or set(
        characterization_outputs
    ) != (EXPECTED_PROVIDERS):
        _fail("characterization machine output lacks the exact 13 Provider set")

    characterization = report.get("characterization")
    if (
        not isinstance(characterization, dict)
        or set(characterization) != EXPECTED_PROVIDERS
    ):
        _fail("characterization must cover the exact 13 Provider set")
    for provider_id, item in characterization.items():
        if not isinstance(item, dict) or item.get("status") != "passed":
            _fail(f"characterization did not pass: {provider_id}")
        if item.get("command_ids") != [
            "release-regression",
            "provider-matrix-b",
            "characterization-a",
            "characterization-b",
        ]:
            _fail(f"characterization lacks the frozen command evidence: {provider_id}")
        if item.get("output_path") != commands["characterization-a"].get("stdout_path"):
            _fail(
                f"characterization is not bound to first command stdout: {provider_id}"
            )
        if item.get("repeat_output_path") != commands["characterization-b"].get(
            "stdout_path"
        ):
            _fail(
                f"characterization is not bound to second command stdout: {provider_id}"
            )
        output_path = _verify_artifact_digest(
            artifacts_root,
            item.get("output_path"),
            item.get("output_sha256"),
            f"{provider_id} output digest",
        )
        repeat_path = _verify_artifact_digest(
            artifacts_root,
            item.get("repeat_output_path"),
            item.get("repeat_output_sha256"),
            f"{provider_id} repeat output digest",
        )
        if output_path != commands["characterization-a"]["stdout_file"]:
            _fail(f"{provider_id} characterization output path drift")
        if repeat_path != commands["characterization-b"]["stdout_file"]:
            _fail(f"{provider_id} repeat characterization output path drift")
        if item.get("output_sha256") != commands["characterization-a"]["stdout_sha256"]:
            _fail(f"{provider_id} output digest is not bound to command stdout")
        if (
            item.get("repeat_output_sha256")
            != commands["characterization-b"]["stdout_sha256"]
        ):
            _fail(f"{provider_id} repeat output digest is not bound to command stdout")
        output = characterization_outputs.get(provider_id)
        if not isinstance(output, dict) or output.get("provider_id") != provider_id:
            _fail(f"{provider_id} characterization machine record is invalid")
        if output.get("ready") is not True or item.get("status") != "passed":
            _fail(f"{provider_id} characterization output is not ready")
        if (
            output.get("provider_output_sha256")
            != EXPECTED_CHARACTERIZATION_DIGESTS[provider_id]
        ):
            _fail(f"{provider_id} characterization golden digest mismatch")
        if item.get("provider_output_sha256") != output.get("provider_output_sha256"):
            _fail(f"{provider_id} report/provider output digest mismatch")
        if output.get("fixture_input_sha256") != EXPECTED_FIXTURE_DIGESTS[provider_id]:
            _fail(f"{provider_id} fixed fixture input digest mismatch")
        if item.get("fixture_input_sha256") != output.get("fixture_input_sha256"):
            _fail(f"{provider_id} report/fixture input digest mismatch")
        for digest_field in ("deterministic_facts_sha256", "evidence_mapping_sha256"):
            _require_sha256(output.get(digest_field), f"{provider_id} {digest_field}")
            if item.get(digest_field) != output.get(digest_field):
                _fail(f"{provider_id} report machine digest mismatch: {digest_field}")
        expected_assertions = {
            "deterministic_facts": True,
            "evidence_mapping": True,
            "fixture_bound": True,
        }
        if output.get("assertions") != expected_assertions:
            _fail(f"{provider_id} characterization machine assertions failed")
        if item.get("assertions") != expected_assertions:
            _fail(f"{provider_id} characterization report assertions failed")

    regression = report.get("release_regression")
    if not isinstance(regression, dict) or regression.get("status") != "passed":
        _fail("release regression did not pass")
    if regression.get("test_count") != EXPECTED_TEST_COUNT:
        _fail("release regression must contain exactly 1584 tests")
    if regression.get("executed_in_image_id") != image_digest:
        _fail("release regression did not execute in the final production image")
    regression_command = commands.get(regression.get("command_id"))
    if regression_command is None:
        _fail("release regression command evidence is missing")
    _require_command(
        commands,
        "release-regression",
        argv=(
            runtime_path,
            "-B",
            "/audit-source/scripts/run_test_suite.py",
            "--jobs",
            "10",
            "--research-root",
            research_root,
        ),
        cwd=source_root,
        image_id=image_id,
    )
    _require_command_budget(
        regression_command,
        expected_timeout_seconds=EXPECTED_RELEASE_REGRESSION_TIMEOUT_SECONDS,
        label="release regression",
    )
    if (
        regression.get("elapsed_seconds") != regression_command.get("elapsed_seconds")
        or regression.get("timeout_seconds")
        != EXPECTED_RELEASE_REGRESSION_TIMEOUT_SECONDS
        or regression.get("timeout_seconds")
        != regression_command.get("timeout_seconds")
    ):
        _fail("release regression elapsed/budget evidence is not exact")
    if regression_command.get("executed_in_image_id") != regression.get(
        "executed_in_image_id"
    ):
        _fail("release regression report and command image identity differ")
    regression_stdout = regression_command["stdout_file"].read_text(encoding="utf-8")
    summaries = list(SUMMARY_RE.finditer(regression_stdout))
    if len(summaries) != 1:
        _fail("release regression stdout has no unique authoritative summary")
    summary = summaries[0]
    if int(summary.group("tests")) != EXPECTED_TEST_COUNT:
        _fail("release regression stdout does not report exactly 1584 tests")
    if int(summary.group("failed")) != 0:
        _fail("release regression stdout reports failed modules")
    if int(summary.group("targets")) != EXPECTED_TEST_TARGETS:
        _fail("release regression stdout target count mismatch")
    if int(summary.group("modules")) != EXPECTED_TEST_MODULES:
        _fail("release regression stdout module count mismatch")

    p0 = report.get("p0_trajectories")
    _require_successful_command_ids(p0, commands, "P0 trajectories")
    if not isinstance(p0, dict) or p0.get("command_ids") != ["p0-trajectories"]:
        _fail("P0 trajectories command inventory is not exact")
    p0_command = _require_command(
        commands,
        "p0-trajectories",
        argv=(
            runtime_path,
            "-B",
            "-m",
            "unittest",
            "-v",
            "test_v51_bazi_fortune_completion",
            "test_v51_liuyao_completion",
            "test_v51_portable_interface",
        ),
        cwd="/audit-source/scripts",
        image_id=image_id,
    )
    p0_output = p0_command["stdout_file"].read_text(encoding="utf-8") + p0_command[
        "stderr_file"
    ].read_text(encoding="utf-8")
    p0_sentinels = {
        "bazi": "test_full_structured_chart_prepares_with_clean_brief",
        "fortune_day": "test_fortune_is_one_day_view_over_the_same_natal_fact_identity",
        "fortune_week": "test_broad_weekly_question_prepares_with_default_dimensions",
        "liuyao_digital": "test_seeded_digital_cast_is_reproducible_and_records_coin_faces",
        "liuyao_manual": "test_provider_calculates_supplied_cast_and_binds_shared_calendar",
    }
    if p0.get("assertions") != {name: True for name in p0_sentinels}:
        _fail("P0 trajectories machine assertions are incomplete")
    for label, sentinel in p0_sentinels.items():
        if sentinel not in p0_output:
            _fail(f"P0 trajectory evidence is missing: {label}")

    probes = report.get("probes")
    _require_successful_command_ids(probes, commands, "runtime probes")
    if not isinstance(probes, dict) or probes.get("command_ids") != [
        "runtime-probe-machine",
        "runtime-probe-unittest",
    ]:
        _fail("runtime probes command inventory is not exact")
    machine_probe = _require_command(
        commands,
        "runtime-probe-machine",
        argv=(
            runtime_path,
            "-B",
            audit_script,
            "--emit-runtime-probes",
            "--state-root",
            "/var/lib/mingli",
        ),
        cwd="/opt/mingli-master",
        image_id=image_id,
    )
    machine_output = _load_json(
        machine_probe["stdout_file"],
        "runtime probe machine output",
    )
    expected_probe_assertions = {
        "describe_repeatable": True,
        "describe_within_60_seconds": True,
        "launcher_timeout_killed_without_residual_process": True,
        "malformed_input_stopped": True,
        "tampered_release_rejected": True,
    }
    if machine_output != {
        "assertions": expected_probe_assertions,
        "schema_version": "mingli-runtime-probes-v1",
    }:
        _fail("runtime probe machine assertions failed")
    if probes.get("assertions") != {
        **expected_probe_assertions,
        "concurrency_fenced": True,
        "token_replay_byte_stable": True,
    }:
        _fail("runtime probe report assertions are incomplete")
    unittest_probe = _require_command(
        commands,
        "runtime-probe-unittest",
        argv=(
            runtime_path,
            "-B",
            "-m",
            "unittest",
            "-v",
            "test_v51_pending_atomicity",
            "test_v51_state_token",
            "test_runtime_launcher",
        ),
        cwd="/audit-source/scripts",
        image_id=image_id,
    )
    probe_output = unittest_probe["stdout_file"].read_text(
        encoding="utf-8"
    ) + unittest_probe["stderr_file"].read_text(encoding="utf-8")
    for sentinel in (
        "test_concurrent_children_yield_exactly_one_winner",
        "test_one_prepared_token_completes_and_replay_is_idempotent",
        "test_accept_commit_is_first_write_wins_and_byte_stable",
    ):
        if sentinel not in probe_output:
            _fail(f"runtime probe unittest evidence is missing: {sentinel}")
    backup_path = _verify_artifact_digest(
        artifacts_root,
        evidence.get("backup_restore_path"),
        evidence.get("backup_restore_sha256"),
        "backup/restore evidence",
    )
    _verify_backup_restore(
        report.get("backup_restore"),
        backup_path,
        image_digest,
        artifacts_root,
    )


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--runtime-python", type=Path)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--git", type=Path)
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--research-source", type=Path)
    parser.add_argument("--release-only", action="store_true")
    parser.add_argument("--inventory-output", type=Path)
    parser.add_argument("--audit-report", type=Path)
    parser.add_argument("--artifacts-root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.audit_report is not None:
            if args.artifacts_root is None:
                parser.error("--audit-report requires --artifacts-root")
            report = _load_json(args.audit_report, "release audit report")
            validate_audit_report(report, artifacts_root=args.artifacts_root)
            return 0
        if args.release_root is None:
            parser.error("runtime inspection requires --release-root")
        inventory = inspect_runtime(
            release_root=args.release_root,
            runtime_python=args.runtime_python,
            node=args.node,
            git=args.git,
            state_root=args.state_root,
            research_source=args.research_source,
            release_only=args.release_only,
        )
        if args.inventory_output is not None:
            _write_json(args.inventory_output, inventory)
        else:
            print(json.dumps(inventory, ensure_ascii=False, sort_keys=True))
        return 0
    except ReleaseVerificationError as exc:
        print(f"release verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
