#!/usr/bin/env python3
"""Fail-closed loading for immutable local Gate inputs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

import linux_identity

EXPECTED_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)
SCHEMA = "mingli-prepared-inputs-v1"
INSTANCE_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
GIT = Path("/usr/bin/git")
EXPECTED_LIMA_VERSION = "2.2.0"
PREPARATION_SCHEMA = "mingli-linux-preparation-v1"
BUILD_CONTEXT_INPUT_NAMES = (
    "Dockerfile",
    "audit_runtime.py",
    "dependency-provenance.json",
    "emit_sbom.py",
    "git-build-config.json",
    "requirements-linux-x86_64.lock",
    "verify_release.py",
)
CONTROLLER_INPUT_PATHS = (
    "infra/mingli-runtime/Dockerfile",
    "infra/mingli-runtime/audit_runtime.py",
    "infra/mingli-runtime/build_context.py",
    "infra/mingli-runtime/dependency-provenance.json",
    "infra/mingli-runtime/emit_sbom.py",
    "infra/mingli-runtime/git-build-config.json",
    "infra/mingli-runtime/linux_identity.py",
    "infra/mingli-runtime/local_gate.py",
    "infra/mingli-runtime/prepare_linux_inputs.py",
    "infra/mingli-runtime/prepared_inputs.py",
    "infra/mingli-runtime/requirements-linux-x86_64.lock",
    "infra/mingli-runtime/run_lima_gate.py",
    "infra/mingli-runtime/verify_local_full.py",
    "infra/mingli-runtime/verify_release.py",
)


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


def _sha256(value: object, label: str) -> str:
    digest = _string(value, label)
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        _fail(f"{label} must be a lowercase SHA-256")
    return digest


def sha256_tree(root: Path) -> str:
    """Hash every visible tree entry without following directory symlinks.

    Git administration bytes are not runtime input and are excluded. Every other
    regular file and symlink is bound by relative path, mode, type, and content or
    link target. Special files are rejected because their bytes are not stable.
    """

    digest = hashlib.sha256()
    candidates = sorted(
        (
            path
            for path in root.rglob("*")
            if ".git" not in path.relative_to(root).parts
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in candidates:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_symlink():
            record = b"L\0" + relative + b"\0" + os.fsencode(os.readlink(path)) + b"\0"
        elif path.is_file():
            mode = path.stat().st_mode & 0o777
            record = (
                b"F\0"
                + relative
                + b"\0"
                + f"{mode:o}".encode("ascii")
                + b"\0"
                + sha256_file(path).encode("ascii")
                + b"\0"
            )
        elif path.is_dir():
            continue
        else:
            _fail(f"tree contains unsupported entry: {path}")
        digest.update(record)
    return digest.hexdigest()


def _require_within(path: Path, root: Path, label: str) -> None:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except ValueError:
        _fail(f"{label} must be inside its declared root")


def _git(root: Path, *args: str) -> bytes:
    if not GIT.is_file():
        _fail("fixed Git executable is absent")
    try:
        completed = subprocess.run(
            [str(GIT), "--no-replace-objects", "-C", str(root), *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=30,
            env={
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
            },
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PreparedInputsError("source Git identity command failed") from exc
    if (
        completed.returncode != 0
        or len(completed.stdout) > 1024 * 1024
        or len(completed.stderr) > 1024 * 1024
    ):
        _fail("source Git identity command failed")
    return completed.stdout


def _verify_source_git(root: Path, expected_commit: str) -> None:
    if COMMIT_RE.fullmatch(expected_commit) is None:
        _fail("source commit is malformed")
    try:
        head = (
            _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        )
    except UnicodeDecodeError as exc:
        raise PreparedInputsError("source Git HEAD is not ASCII") from exc
    if head != expected_commit:
        _fail("source Git HEAD mismatch")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        _fail("source Git worktree is not clean")


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
    source_tree_sha256: str
    research_root: Path
    research_tree_sha256: str
    native_runtime_root: Path
    native_runtime_tree_sha256: str
    native_python: Path
    runner_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class LinuxRuntimeInputs:
    instance: str
    lima_version: str
    effective_config: Path
    effective_config_sha256: str
    image_ref: str
    image_repository: str
    immutable_image_ref: str
    index_digest: str
    platform_manifest_digest: str
    config_digest: str
    attestation_manifest_digest: str
    layer_digests: tuple[str, ...]
    rootfs_diff_ids: tuple[str, ...]
    oci_archive: Path
    oci_archive_sha256: str
    docker: dict[str, Any]
    controller_commit: str | None = None
    build_context_tree_sha256: str | None = None


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
    release_manifest = _absolute_path(
        source.get("release_manifest"), "source.release_manifest", directory=False
    )
    if sha256_file(release_manifest) != EXPECTED_RELEASE_MANIFEST_SHA256:
        _fail("release manifest bytes do not match the signed SHA-256")
    source_fulltext = source_root / "references" / "fulltext"
    if source_fulltext.is_symlink():
        _fail("source projection contains fulltext through a symlink")
    if source_fulltext.is_dir() and any(
        candidate.is_file() for candidate in source_fulltext.rglob("*")
    ):
        _fail("source projection contains fulltext generator drift")
    source_tree_sha256 = _sha256(source.get("tree_sha256"), "source.tree_sha256")
    if sha256_tree(source_root) != source_tree_sha256:
        _fail("source tree SHA-256 mismatch")
    research_tree_sha256 = _sha256(research.get("tree_sha256"), "research.tree_sha256")
    if sha256_tree(research_root) != research_tree_sha256:
        _fail("research tree SHA-256 mismatch")
    _verify_source_git(source_root, EXPECTED_COMMIT)
    native_runtime_root = _absolute_path(
        native_runtime.get("root"), "native_runtime.root", directory=True
    )
    native_runtime_tree_sha256 = _sha256(
        native_runtime.get("tree_sha256"), "native_runtime.tree_sha256"
    )
    if sha256_tree(native_runtime_root) != native_runtime_tree_sha256:
        _fail("native_runtime tree SHA-256 mismatch")
    native_python = _absolute_path(
        native_runtime.get("python"), "native_runtime.python", directory=False
    )
    _require_within(native_python, native_runtime_root, "native_runtime.python")
    if sha256_file(native_python) != native_runtime.get("python_sha256"):
        _fail("native Python SHA-256 mismatch")
    runtime_integrity = _absolute_path(
        native_runtime.get("runtime_integrity"),
        "native_runtime.runtime_integrity",
        directory=False,
    )
    _require_within(
        runtime_integrity,
        native_runtime_root,
        "native_runtime.runtime_integrity",
    )
    if sha256_file(runtime_integrity) != native_runtime.get("runtime_integrity_sha256"):
        _fail("native runtime integrity SHA-256 mismatch")
    lock = _absolute_path(
        native_runtime.get("requirements_lock"),
        "native_runtime.requirements_lock",
        directory=False,
    )
    if sha256_file(lock) != native_runtime.get("requirements_lock_sha256"):
        _fail("runtime lock SHA-256 mismatch")
    _require_within(lock, source_root, "native_runtime.requirements_lock")

    runner_path = source_root / "scripts" / "run_test_suite.py"
    if runner_path.is_symlink() or not runner_path.is_file():
        _fail("signed native suite runner is absent")

    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        _fail("prepared inputs bindings must be a non-empty list")
    bound_paths: set[Path] = set()
    for index, raw_binding in enumerate(bindings):
        binding = _mapping(raw_binding, f"bindings[{index}]")
        if set(binding) != {"kind", "path", "sha256"}:
            _fail(f"bindings[{index}] fields are not exact")
        if binding.get("kind") != "file":
            _fail(f"bindings[{index}].kind is unsupported")
        bound_path = _absolute_path(
            binding.get("path"), f"bindings[{index}].path", directory=False
        )
        canonical_path = bound_path.resolve(strict=True)
        if canonical_path in bound_paths:
            _fail(f"duplicate binding path: {bound_path}")
        bound_paths.add(canonical_path)
        binding_sha256 = _sha256(binding.get("sha256"), f"bindings[{index}].sha256")
        if sha256_file(bound_path) != binding_sha256:
            _fail(f"bindings[{index}] SHA-256 mismatch")
    required_bindings = {
        runner_path.resolve(strict=True),
        lock.resolve(strict=True),
        release_manifest.resolve(strict=True),
        runtime_integrity.resolve(strict=True),
    }
    if not required_bindings.issubset(bound_paths):
        _fail("prepared inputs required binding is absent")
    return PreparedInputs(
        manifest_path=path,
        manifest_sha256=actual_sha256,
        source_root=source_root,
        source_tree_sha256=source_tree_sha256,
        research_root=research_root,
        research_tree_sha256=research_tree_sha256,
        native_runtime_root=native_runtime_root,
        native_runtime_tree_sha256=native_runtime_tree_sha256,
        native_python=native_python,
        runner_path=runner_path,
        payload=payload,
    )


def require_linux(inputs: PreparedInputs) -> LinuxRuntimeInputs:
    linux = _mapping(inputs.payload.get("linux_runtime"), "linux_runtime")
    instance = _string(linux.get("instance"), "linux_runtime.instance")
    if INSTANCE_RE.fullmatch(instance) is None:
        _fail("linux runtime instance is malformed")
    lima_version = _string(linux.get("lima_version"), "Linux Lima version")
    if lima_version != EXPECTED_LIMA_VERSION:
        _fail("Linux Lima version drift")
    effective_config = _absolute_path(
        linux.get("effective_config"),
        "linux_runtime.effective_config",
        directory=False,
    )
    effective_config_sha256 = _string(
        linux.get("effective_config_sha256"),
        "linux_runtime.effective_config_sha256",
    )
    if sha256_file(effective_config) != effective_config_sha256:
        _fail("effective Lima config SHA-256 mismatch")
    image_ref = _string(linux.get("image_ref"), "linux_runtime.image_ref")
    if any(character.isspace() for character in image_ref):
        _fail("linux runtime image ref is malformed")
    image_repository = _string(
        linux.get("image_repository"), "linux_runtime.image_repository"
    )
    if any(character.isspace() for character in image_repository):
        _fail("linux runtime image repository is malformed")
    oci = _mapping(linux.get("oci"), "linux_runtime.oci")
    if set(oci) != {
        "index_digest",
        "platform_manifest_digest",
        "config_digest",
        "attestation_manifest_digest",
        "layer_digests",
        "rootfs_diff_ids",
    }:
        _fail("linux OCI identity fields are not exact")
    index_digest = _string(oci.get("index_digest"), "linux_runtime.oci.index")
    platform_manifest_digest = _string(
        oci.get("platform_manifest_digest"), "linux_runtime.oci.platform_manifest"
    )
    config_digest = _string(oci.get("config_digest"), "linux_runtime.oci.config")
    attestation_manifest_digest = _string(
        oci.get("attestation_manifest_digest"),
        "linux_runtime.oci.attestation_manifest",
    )
    for label, digest in (
        ("index", index_digest),
        ("platform manifest", platform_manifest_digest),
        ("config", config_digest),
        ("attestation manifest", attestation_manifest_digest),
    ):
        if IMAGE_ID_RE.fullmatch(digest) is None:
            _fail(f"linux runtime OCI {label} digest is malformed")
    if (
        len(
            {
                index_digest,
                platform_manifest_digest,
                config_digest,
                attestation_manifest_digest,
            }
        )
        != 4
    ):
        _fail("linux runtime OCI identities must be distinct")

    def digest_list(key: str) -> tuple[str, ...]:
        value = oci.get(key)
        if (
            not isinstance(value, list)
            or not value
            or not all(
                isinstance(item, str) and IMAGE_ID_RE.fullmatch(item) is not None
                for item in value
            )
            or len(set(value)) != len(value)
        ):
            _fail(f"linux_runtime.oci.{key} is malformed")
        return tuple(value)

    layer_digests = digest_list("layer_digests")
    rootfs_diff_ids = digest_list("rootfs_diff_ids")
    if len(layer_digests) != len(rootfs_diff_ids):
        _fail("linux OCI layer and RootFS identities differ in length")
    immutable_image_ref = _string(
        linux.get("immutable_image_ref"), "linux_runtime.immutable_image_ref"
    )
    if immutable_image_ref != f"{image_repository}@{index_digest}":
        _fail("linux immutable image ref does not bind the OCI index")
    oci_archive = _absolute_path(
        linux.get("oci_archive"),
        "linux_runtime.oci_archive",
        directory=False,
    )
    oci_archive_sha256 = _string(
        linux.get("oci_archive_sha256"), "linux_runtime.oci_archive_sha256"
    )
    if sha256_file(oci_archive) != oci_archive_sha256:
        _fail("Linux OCI archive SHA-256 mismatch")
    docker = _mapping(linux.get("docker"), "linux_runtime.docker")
    expected_docker = {
        "client_version": "29.7.2",
        "server_version": "29.7.2",
        "server_arch": "arm64",
        "containerd_version": "v2.3.3",
        "rootlesskit_version": "3.0.2",
    }
    if docker != expected_docker:
        _fail("Linux Docker identity drift")
    return LinuxRuntimeInputs(
        instance=instance,
        lima_version=lima_version,
        effective_config=effective_config,
        effective_config_sha256=effective_config_sha256,
        image_ref=image_ref,
        image_repository=image_repository,
        immutable_image_ref=immutable_image_ref,
        index_digest=index_digest,
        platform_manifest_digest=platform_manifest_digest,
        config_digest=config_digest,
        attestation_manifest_digest=attestation_manifest_digest,
        layer_digests=layer_digests,
        rootfs_diff_ids=rootfs_diff_ids,
        oci_archive=oci_archive,
        oci_archive_sha256=oci_archive_sha256,
        docker=docker,
    )


def _bound_file_digests(inputs: PreparedInputs) -> dict[Path, str]:
    bindings = inputs.payload.get("bindings")
    if not isinstance(bindings, list):
        _fail("prepared inputs bindings are absent")
    result: dict[Path, str] = {}
    for index, raw_binding in enumerate(bindings):
        binding = _mapping(raw_binding, f"bindings[{index}]")
        path = _absolute_path(
            binding.get("path"), f"bindings[{index}].path", directory=False
        ).resolve(strict=True)
        digest = _sha256(binding.get("sha256"), f"bindings[{index}].sha256")
        result[path] = digest
    return result


def _safe_tar_name(raw: str) -> str:
    if not raw or "\\" in raw:
        _fail("build-context archive path is unsafe")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _fail("build-context archive path is unsafe")
    return path.as_posix()


def _inspect_build_context_archive(path: Path) -> tuple[str, dict[str, str]]:
    try:
        archive = tarfile.open(path, "r:")  # noqa: SIM115 - normalize open errors
    except (OSError, tarfile.TarError) as exc:
        raise PreparedInputsError("build-context archive cannot be opened") from exc
    digest = hashlib.sha256()
    file_sha256: dict[str, str] = {}
    with archive:
        members = archive.getmembers()
        names = [_safe_tar_name(member.name) for member in members]
        if names != sorted(names) or len(names) != len(set(names)):
            _fail("build-context archive inventory is not canonical")
        for member, relative in zip(members, names, strict=True):
            if (
                member.uid != 0
                or member.gid != 0
                or member.uname
                or member.gname
                or member.mtime != 0
            ):
                _fail("build-context archive metadata is not canonical")
            if member.isdir():
                continue
            if not member.isfile() or member.size > 64 * 1024 * 1024:
                _fail("build-context archive contains an unsafe entry")
            stream = archive.extractfile(member)
            if stream is None:
                _fail("build-context archive file cannot be read")
            content_digest = hashlib.sha256()
            while chunk := stream.read(1024 * 1024):
                content_digest.update(chunk)
            content_sha256 = content_digest.hexdigest()
            file_sha256[relative] = content_sha256
            digest.update(
                b"F\0"
                + relative.encode("utf-8")
                + b"\0"
                + f"{member.mode & 0o777:o}".encode("ascii")
                + b"\0"
                + content_sha256.encode("ascii")
                + b"\0"
            )
    return digest.hexdigest(), file_sha256


def _read_preparation_record(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 1024 * 1024:
        _fail("Linux preparation record exceeds its byte limit")
    try:
        return _mapping(json.loads(path.read_bytes()), "Linux preparation record")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreparedInputsError("Linux preparation record is invalid JSON") from exc


def _verify_controller_git(
    root: Path,
    *,
    expected_commit: str,
    expected_inputs: dict[str, str],
) -> None:
    if COMMIT_RE.fullmatch(expected_commit) is None:
        _fail("controller commit is malformed")
    try:
        head = (
            _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        )
    except UnicodeDecodeError as exc:
        raise PreparedInputsError("controller Git HEAD is not ASCII") from exc
    if head != expected_commit:
        _fail("controller Git HEAD mismatch")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=no"):
        _fail("controller Git tracked worktree is not clean")
    tracked = set(
        _git(root, "ls-files", "--", *CONTROLLER_INPUT_PATHS)
        .decode("utf-8")
        .splitlines()
    )
    if tracked != set(CONTROLLER_INPUT_PATHS):
        _fail("controller input is not fully tracked")
    if set(expected_inputs) != set(CONTROLLER_INPUT_PATHS):
        _fail("controller input inventory is not exact")
    for relative, expected_sha256 in expected_inputs.items():
        path = root / relative
        if path.is_symlink() or not path.is_file():
            _fail(f"controller input is missing or unsafe: {relative}")
        if sha256_file(path) != _sha256(expected_sha256, relative):
            _fail(f"controller input SHA-256 mismatch: {relative}")


def require_certifiable_linux(inputs: PreparedInputs) -> LinuxRuntimeInputs:
    """Require the persisted post-commit build provenance used by a full Gate."""

    linux = require_linux(inputs)
    linux_payload = _mapping(inputs.payload.get("linux_runtime"), "linux_runtime")
    preparation = _mapping(
        linux_payload.get("preparation"), "Linux preparation provenance"
    )
    if set(preparation) != {
        "record",
        "record_sha256",
        "controller_commit",
        "build_context_archive",
        "build_context_archive_sha256",
        "build_context_tree_sha256",
    }:
        _fail("Linux preparation provenance fields are not exact")
    record_path = _absolute_path(
        preparation.get("record"), "Linux preparation record", directory=False
    )
    record_sha256 = _sha256(
        preparation.get("record_sha256"), "Linux preparation record SHA-256"
    )
    if sha256_file(record_path) != record_sha256:
        _fail("Linux preparation record SHA-256 mismatch")
    context_archive = _absolute_path(
        preparation.get("build_context_archive"),
        "build-context archive",
        directory=False,
    )
    context_archive_sha256 = _sha256(
        preparation.get("build_context_archive_sha256"),
        "build-context archive SHA-256",
    )
    if sha256_file(context_archive) != context_archive_sha256:
        _fail("build-context archive SHA-256 mismatch")
    context_tree_sha256 = _sha256(
        preparation.get("build_context_tree_sha256"),
        "build-context tree SHA-256",
    )
    actual_tree_sha256, context_files = _inspect_build_context_archive(context_archive)
    if actual_tree_sha256 != context_tree_sha256:
        _fail("build-context tree SHA-256 mismatch")
    try:
        linux_identity.verify_oci_archive(
            linux.oci_archive,
            expected_archive_sha256=linux.oci_archive_sha256,
            image_ref=linux.image_ref,
            expected=_mapping(linux_payload.get("oci"), "linux runtime OCI"),
            expected_build_context_sha256=context_archive_sha256,
        )
    except linux_identity.IdentityError as exc:
        raise PreparedInputsError(
            f"Linux OCI preparation provenance is invalid: {exc}"
        ) from exc

    bound = _bound_file_digests(inputs)
    for required in (record_path, context_archive):
        resolved = required.resolve(strict=True)
        if resolved not in bound or bound[resolved] != sha256_file(required):
            _fail("Linux preparation artifact is not bound by PreparedInputs")

    record = _read_preparation_record(record_path)
    if (
        set(record)
        != {
            "schema",
            "controller",
            "build_context",
            "runtime",
            "image",
            "commands",
        }
        or record.get("schema") != PREPARATION_SCHEMA
    ):
        _fail("Linux preparation record schema mismatch")
    controller = _mapping(record.get("controller"), "preparation controller")
    if set(controller) != {"repository_root", "commit", "input_sha256"}:
        _fail("preparation controller fields are not exact")
    controller_root = _absolute_path(
        controller.get("repository_root"),
        "preparation controller root",
        directory=True,
    )
    controller_commit = _string(controller.get("commit"), "controller commit")
    if controller_commit != preparation.get("controller_commit"):
        _fail("preparation controller commit cross-binding mismatch")
    controller_inputs = _mapping(
        controller.get("input_sha256"), "preparation controller inputs"
    )
    _verify_controller_git(
        controller_root,
        expected_commit=controller_commit,
        expected_inputs=controller_inputs,
    )
    for relative, expected_sha256 in controller_inputs.items():
        resolved = (controller_root / relative).resolve(strict=True)
        if resolved not in bound or bound[resolved] != expected_sha256:
            _fail("controller input is not bound by PreparedInputs")

    context = _mapping(record.get("build_context"), "preparation build context")
    if set(context) != {
        "archive",
        "archive_sha256",
        "tree_sha256",
        "infra_sha256",
    }:
        _fail("preparation build-context fields are not exact")
    if context != {
        "archive": str(context_archive),
        "archive_sha256": context_archive_sha256,
        "tree_sha256": context_tree_sha256,
        "infra_sha256": context.get("infra_sha256"),
    }:
        _fail("preparation build-context cross-binding mismatch")
    infra_sha256 = _mapping(
        context.get("infra_sha256"), "preparation build-context infra"
    )
    if set(infra_sha256) != set(BUILD_CONTEXT_INPUT_NAMES):
        _fail("preparation build-context infra inventory is not exact")
    for name, expected_sha256 in infra_sha256.items():
        expected = _sha256(expected_sha256, f"build-context {name}")
        if context_files.get(name) != expected:
            _fail(f"build-context input SHA-256 mismatch: {name}")
        controller_relative = f"infra/mingli-runtime/{name}"
        if controller_inputs.get(controller_relative) != expected:
            _fail(f"build-context controller binding mismatch: {name}")

    expected_runtime = {
        "instance": linux.instance,
        "lima_version": linux.lima_version,
        "effective_config_sha256": linux.effective_config_sha256,
        "docker": linux.docker,
    }
    if record.get("runtime") != expected_runtime:
        _fail("preparation runtime identity mismatch")
    expected_image = {
        "image_ref": linux.image_ref,
        "image_repository": linux.image_repository,
        "immutable_image_ref": linux.immutable_image_ref,
        "oci_archive": str(linux.oci_archive),
        "oci_archive_sha256": linux.oci_archive_sha256,
        "oci": linux_payload.get("oci"),
    }
    if record.get("image") != expected_image:
        _fail("preparation image identity mismatch")
    expected_commands = {
        "lima_version": ["limactl", "--version"],
        "build": [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "--progress=plain",
            "--target",
            "final",
            "--tag",
            linux.image_ref,
            "-",
        ],
        "export": ["docker", "image", "save", linux.image_ref],
    }
    if record.get("commands") != expected_commands:
        _fail("preparation command contract mismatch")
    return replace(
        linux,
        controller_commit=controller_commit,
        build_context_tree_sha256=context_tree_sha256,
    )
