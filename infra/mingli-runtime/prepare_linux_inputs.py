#!/usr/bin/env python3
"""Prepare one immutable Linux OCI artifact outside the timed release Gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Protocol

import build_context
import linux_identity
import prepared_inputs
import run_lima_gate

BUILD_CONTEXT_ARCHIVE_NAME = "build-context.tar"
OCI_ARCHIVE_NAME = "mingli-v51.oci.tar"
PREPARATION_RECORD_NAME = "linux-preparation.json"
PREPARED_INPUTS_NAME = "prepared-inputs.json"
PENDING_PREPARED_INPUTS_NAME = ".prepared-inputs.pending"
PREPARATION_SCHEMA = prepared_inputs.PREPARATION_SCHEMA
BUILD_CONTEXT_INPUT_NAMES = prepared_inputs.BUILD_CONTEXT_INPUT_NAMES
CONTROLLER_INPUT_PATHS = prepared_inputs.CONTROLLER_INPUT_PATHS
IMAGE_REPOSITORY = "mingli-v51-production"
VZ_INSTANCE = "mingli-linux-gate-vz"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class PreparationError(RuntimeError):
    """The immutable Linux build cannot be sealed for a formal Gate."""


def _fail(message: str) -> NoReturn:
    raise PreparationError(message)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class PrepareRequest:
    base_prepared_inputs: Path
    base_prepared_inputs_sha256: str
    controller_root: Path
    release_source: Path
    effective_config: Path
    effective_config_sha256: str
    instance: str
    output_directory: Path


@dataclass(frozen=True)
class ImageBuildResult:
    index_digest: str
    lima_version: str
    docker: dict[str, Any]


@dataclass(frozen=True)
class PreparedBundle:
    output_directory: Path
    prepared_inputs: Path
    prepared_inputs_sha256: str
    preparation_record: Path
    build_context_archive: Path
    oci_archive: Path
    controller_commit: str
    index_digest: str
    lima_version: str


class ImageBuilder(Protocol):
    def build_and_export(
        self,
        *,
        context_tar: bytes,
        image_ref: str,
        destination: Path,
    ) -> ImageBuildResult: ...


ContextBuilder = Callable[..., Path]


def _run_git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            [
                "/usr/bin/git",
                "--no-replace-objects",
                "-C",
                str(root),
                *args,
            ],
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
        raise PreparationError("controller Git identity command failed") from exc
    if (
        completed.returncode != 0
        or len(completed.stdout) > 1024 * 1024
        or len(completed.stderr) > 1024 * 1024
    ):
        _fail("controller Git identity command failed")
    return completed.stdout


def _controller_identity(root: Path) -> tuple[str, dict[str, str]]:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        _fail("controller root must be an absolute non-symlink directory")
    root = root.resolve(strict=True)
    try:
        commit = (
            _run_git(root, "rev-parse", "--verify", "HEAD^{commit}")
            .decode("ascii")
            .strip()
        )
    except UnicodeDecodeError as exc:
        raise PreparationError("controller Git HEAD is not ASCII") from exc
    if COMMIT_RE.fullmatch(commit) is None:
        _fail("controller Git HEAD is malformed")
    if _run_git(root, "status", "--porcelain=v1", "--untracked-files=no"):
        _fail("controller Git tracked worktree is not clean")
    tracked = set(
        _run_git(root, "ls-files", "--", *CONTROLLER_INPUT_PATHS)
        .decode("utf-8")
        .splitlines()
    )
    if tracked != set(CONTROLLER_INPUT_PATHS):
        _fail("controller input is not fully tracked")
    inputs: dict[str, str] = {}
    for relative in CONTROLLER_INPUT_PATHS:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            _fail(f"controller input is missing or unsafe: {relative}")
        inputs[relative] = prepared_inputs.sha256_file(path)
    return commit, inputs


def _read_oci_json(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    name: str,
    label: str,
) -> dict[str, Any]:
    member = members.get(name)
    if member is None or not member.isfile() or member.size > 16 * 1024 * 1024:
        _fail(f"{label} is absent or too large")
    stream = archive.extractfile(member)
    if stream is None:
        _fail(f"{label} cannot be read")
    raw = stream.read()
    if name.startswith("blobs/sha256/"):
        expected = name.removeprefix("blobs/sha256/")
        if hashlib.sha256(raw).hexdigest() != expected:
            _fail(f"{label} blob digest mismatch")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreparationError(f"{label} is invalid JSON") from exc
    if not isinstance(payload, dict):
        _fail(f"{label} must be an object")
    return payload


def _derive_oci_identity(
    path: Path,
    *,
    image_ref: str,
    build_context_sha256: str,
) -> dict[str, Any]:
    try:
        archive = tarfile.open(path, "r:*")  # noqa: SIM115 - normalize errors
    except (OSError, tarfile.TarError) as exc:
        raise PreparationError("OCI archive cannot be opened") from exc
    with archive:
        members = {
            member.name.removeprefix("./"): member for member in archive.getmembers()
        }
        outer = _read_oci_json(archive, members, "index.json", "OCI outer index")
        outer_descriptors = outer.get("manifests")
        if not isinstance(outer_descriptors, list) or len(outer_descriptors) != 1:
            _fail("OCI outer index is not singular")
        outer_descriptor = outer_descriptors[0]
        if not isinstance(outer_descriptor, dict):
            _fail("OCI outer descriptor is malformed")
        index_digest = outer_descriptor.get("digest")
        if not isinstance(index_digest, str):
            _fail("OCI index digest is absent")
        index = _read_oci_json(
            archive,
            members,
            f"blobs/sha256/{index_digest.removeprefix('sha256:')}",
            "OCI index",
        )
        descriptors = index.get("manifests")
        if not isinstance(descriptors, list):
            _fail("OCI child descriptors are absent")
        platforms = [
            item
            for item in descriptors
            if isinstance(item, dict)
            and item.get("platform") == {"architecture": "amd64", "os": "linux"}
        ]
        attestations = [
            item
            for item in descriptors
            if isinstance(item, dict)
            and item.get("annotations", {}).get("vnd.docker.reference.type")
            == "attestation-manifest"
        ]
        if len(platforms) != 1 or len(attestations) != 1:
            _fail("OCI platform or attestation descriptor is absent")
        platform_digest = platforms[0].get("digest")
        attestation_digest = attestations[0].get("digest")
        if not isinstance(platform_digest, str) or not isinstance(
            attestation_digest, str
        ):
            _fail("OCI child digest is absent")
        platform = _read_oci_json(
            archive,
            members,
            f"blobs/sha256/{platform_digest.removeprefix('sha256:')}",
            "OCI platform manifest",
        )
        config_descriptor = platform.get("config")
        layers = platform.get("layers")
        if not isinstance(config_descriptor, dict) or not isinstance(layers, list):
            _fail("OCI platform closure is malformed")
        config_digest = config_descriptor.get("digest")
        layer_digests = [
            item.get("digest") if isinstance(item, dict) else None for item in layers
        ]
        if not isinstance(config_digest, str) or not all(
            isinstance(item, str) for item in layer_digests
        ):
            _fail("OCI config or layer digest is absent")
        config = _read_oci_json(
            archive,
            members,
            f"blobs/sha256/{config_digest.removeprefix('sha256:')}",
            "OCI config",
        )
        rootfs = config.get("rootfs")
        if not isinstance(rootfs, dict) or not isinstance(rootfs.get("diff_ids"), list):
            _fail("OCI RootFS identity is absent")
        expected = {
            "index_digest": index_digest,
            "platform_manifest_digest": platform_digest,
            "config_digest": config_digest,
            "attestation_manifest_digest": attestation_digest,
            "layer_digests": layer_digests,
            "rootfs_diff_ids": rootfs["diff_ids"],
        }
    archive_sha256 = prepared_inputs.sha256_file(path)
    try:
        linux_identity.verify_oci_archive(
            path,
            expected_archive_sha256=archive_sha256,
            image_ref=image_ref,
            expected=expected,
            expected_build_context_sha256=build_context_sha256,
        )
    except linux_identity.IdentityError as exc:
        raise PreparationError(f"OCI archive verification failed: {exc}") from exc
    return expected


def prepare(
    request: PrepareRequest,
    *,
    builder: ImageBuilder,
    context_builder: ContextBuilder = build_context.build_context,
) -> PreparedBundle:
    output = request.output_directory.absolute()
    if output.exists() or output.is_symlink():
        _fail("prepared Linux output directory must not already exist")
    if request.instance != VZ_INSTANCE:
        _fail("formal local Linux preparation requires the pinned VZ instance")
    base = prepared_inputs.load(
        request.base_prepared_inputs.absolute(),
        request.base_prepared_inputs_sha256,
    )
    if "linux_runtime" in base.payload:
        _fail("base PreparedInputs already contains a Linux artifact")
    effective_config = request.effective_config.absolute()
    if (
        effective_config.is_symlink()
        or not effective_config.is_file()
        or prepared_inputs.sha256_file(effective_config)
        != request.effective_config_sha256
    ):
        _fail("effective Lima config SHA-256 mismatch")
    controller_root = request.controller_root.absolute()
    controller_commit, controller_inputs = _controller_identity(controller_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    directory_published = False
    admitted = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="mingli-linux-build-context-"
        ) as context_text:
            context = context_builder(
                request.release_source,
                Path(context_text) / "context",
                infra_root=controller_root / "infra" / "mingli-runtime",
            )
            context_tree_sha256 = prepared_inputs.sha256_tree(context)
            context_tar = run_lima_gate._tar_tree(context)
            context_archive_staging = staging / BUILD_CONTEXT_ARCHIVE_NAME
            context_archive_staging.write_bytes(context_tar)
            context_archive_staging.chmod(0o600)
            context_archive_sha256 = _sha256_bytes(context_tar)
            infra_sha256 = {
                name: prepared_inputs.sha256_file(context / name)
                for name in BUILD_CONTEXT_INPUT_NAMES
            }

            image_ref = (
                f"{IMAGE_REPOSITORY}:prepared-{controller_commit[:12]}-"
                f"{secrets.token_hex(4)}"
            )
            oci_archive_staging = staging / OCI_ARCHIVE_NAME
            build_result = builder.build_and_export(
                context_tar=context_tar,
                image_ref=image_ref,
                destination=oci_archive_staging,
            )
            oci = _derive_oci_identity(
                oci_archive_staging,
                image_ref=image_ref,
                build_context_sha256=context_archive_sha256,
            )
            if build_result.index_digest != oci["index_digest"]:
                _fail("built Docker index and exported OCI index differ")

        effective_staging = staging / "lima-effective.yaml"
        shutil.copyfile(effective_config, effective_staging, follow_symlinks=False)
        effective_staging.chmod(0o600)
        final_context_archive = output / BUILD_CONTEXT_ARCHIVE_NAME
        final_oci_archive = output / OCI_ARCHIVE_NAME
        final_effective_config = output / effective_staging.name
        final_record = output / PREPARATION_RECORD_NAME
        final_manifest = output / PREPARED_INPUTS_NAME
        pending_manifest = output / PENDING_PREPARED_INPUTS_NAME
        immutable_image_ref = f"{IMAGE_REPOSITORY}@{oci['index_digest']}"
        build_argv = [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "--progress=plain",
            "--target",
            "final",
            "--tag",
            image_ref,
            "-",
        ]
        export_argv = ["docker", "image", "save", image_ref]
        oci_archive_sha256 = prepared_inputs.sha256_file(oci_archive_staging)
        record = {
            "schema": PREPARATION_SCHEMA,
            "controller": {
                "repository_root": str(controller_root),
                "commit": controller_commit,
                "input_sha256": controller_inputs,
            },
            "build_context": {
                "archive": str(final_context_archive),
                "archive_sha256": context_archive_sha256,
                "tree_sha256": context_tree_sha256,
                "infra_sha256": infra_sha256,
            },
            "runtime": {
                "instance": request.instance,
                "lima_version": build_result.lima_version,
                "effective_config_sha256": request.effective_config_sha256,
                "docker": build_result.docker,
            },
            "image": {
                "image_ref": image_ref,
                "image_repository": IMAGE_REPOSITORY,
                "immutable_image_ref": immutable_image_ref,
                "oci_archive": str(final_oci_archive),
                "oci_archive_sha256": oci_archive_sha256,
                "oci": oci,
            },
            "commands": {
                "lima_version": ["limactl", "--version"],
                "build": build_argv,
                "export": export_argv,
            },
        }
        record_staging = staging / PREPARATION_RECORD_NAME
        record_staging.write_bytes(_json_bytes(record))
        record_staging.chmod(0o600)
        payload = copy.deepcopy(base.payload)
        payload["linux_runtime"] = {
            "instance": request.instance,
            "lima_version": build_result.lima_version,
            "effective_config": str(final_effective_config),
            "effective_config_sha256": request.effective_config_sha256,
            "image_ref": image_ref,
            "image_repository": IMAGE_REPOSITORY,
            "immutable_image_ref": immutable_image_ref,
            "oci": oci,
            "oci_archive": str(final_oci_archive),
            "oci_archive_sha256": oci_archive_sha256,
            "docker": build_result.docker,
            "preparation": {
                "record": str(final_record),
                "record_sha256": prepared_inputs.sha256_file(record_staging),
                "controller_commit": controller_commit,
                "build_context_archive": str(final_context_archive),
                "build_context_archive_sha256": context_archive_sha256,
                "build_context_tree_sha256": context_tree_sha256,
            },
        }
        final_bindings = [
            {
                "kind": "file",
                "path": str(final_effective_config),
                "sha256": request.effective_config_sha256,
            },
            {
                "kind": "file",
                "path": str(final_oci_archive),
                "sha256": oci_archive_sha256,
            },
            {
                "kind": "file",
                "path": str(final_context_archive),
                "sha256": context_archive_sha256,
            },
            {
                "kind": "file",
                "path": str(final_record),
                "sha256": prepared_inputs.sha256_file(record_staging),
            },
            *[
                {
                    "kind": "file",
                    "path": str(controller_root / relative),
                    "sha256": digest,
                }
                for relative, digest in controller_inputs.items()
            ],
        ]
        payload["bindings"] = [*payload["bindings"], *final_bindings]
        manifest_staging = staging / PENDING_PREPARED_INPUTS_NAME
        manifest_staging.write_bytes(_json_bytes(payload))
        manifest_staging.chmod(0o600)
        if output.exists() or output.is_symlink():
            _fail("prepared Linux output directory appeared during preparation")
        os.replace(staging, output)
        directory_published = True
        manifest_sha256 = prepared_inputs.sha256_file(pending_manifest)
        try:
            loaded = prepared_inputs.load(pending_manifest, manifest_sha256)
            certified = prepared_inputs.require_certifiable_linux(loaded)
        except (OSError, prepared_inputs.PreparedInputsError) as exc:
            raise PreparationError(
                f"pending PreparedInputs failed independent validation: {exc}"
            ) from exc
        if certified.index_digest != build_result.index_digest:
            _fail("pending PreparedInputs changed the OCI index")

        final_controller_commit, final_controller_inputs = _controller_identity(
            controller_root
        )
        if (
            final_controller_commit != controller_commit
            or final_controller_inputs != controller_inputs
        ):
            _fail("controller inputs changed during Linux preparation")
        try:
            final_base = prepared_inputs.load(
                request.base_prepared_inputs.absolute(),
                request.base_prepared_inputs_sha256,
            )
        except (OSError, prepared_inputs.PreparedInputsError) as exc:
            raise PreparationError(
                f"base PreparedInputs changed during Linux preparation: {exc}"
            ) from exc
        if final_base.payload != base.payload:
            _fail("base PreparedInputs changed during Linux preparation")
        if (
            effective_config.is_symlink()
            or not effective_config.is_file()
            or prepared_inputs.sha256_file(effective_config)
            != request.effective_config_sha256
        ):
            _fail("effective Lima config changed during Linux preparation")

        os.replace(pending_manifest, final_manifest)
        admitted = True
        return PreparedBundle(
            output_directory=output,
            prepared_inputs=final_manifest,
            prepared_inputs_sha256=manifest_sha256,
            preparation_record=final_record,
            build_context_archive=final_context_archive,
            oci_archive=final_oci_archive,
            controller_commit=controller_commit,
            index_digest=certified.index_digest,
            lima_version=certified.lima_version,
        )
    finally:
        if not admitted:
            if directory_published:
                shutil.rmtree(output, ignore_errors=True)
            shutil.rmtree(staging, ignore_errors=True)


class LimaImageBuilder:
    def __init__(self, instance: str) -> None:
        self.instance = instance
        self.vm = run_lima_gate.LimaDocker(instance)

    def _docker_identity(self) -> dict[str, str]:
        version = (
            self.vm.docker(
                [
                    "version",
                    "--format",
                    "{{.Client.Version}} {{.Server.Version}} {{.Server.Arch}}",
                ]
            )
            .stdout.decode("ascii")
            .strip()
            .split()
        )
        containerd = self.vm.run(["containerd", "--version"]).stdout.decode("ascii")
        rootlesskit = self.vm.run(["rootlesskit", "--version"]).stdout.decode("ascii")
        if len(version) != 3:
            _fail("Docker version identity is malformed")
        result = {
            "client_version": version[0],
            "server_version": version[1],
            "server_arch": version[2],
            "containerd_version": "v2.3.3",
            "rootlesskit_version": "3.0.2",
        }
        if " v2.3.3 " not in f" {containerd.strip()} " or (
            "rootlesskit version 3.0.2" not in rootlesskit
        ):
            _fail("Docker dependency identity drift")
        return result

    @staticmethod
    def _lima_version() -> str:
        try:
            completed = subprocess.run(
                ["limactl", "--version"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
                shell=False,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PreparationError("Lima version command failed") from exc
        if (
            completed.returncode != 0
            or completed.stderr
            or len(completed.stdout) > 1024
        ):
            _fail("Lima version command failed")
        try:
            output = completed.stdout.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise PreparationError("Lima version output is not ASCII") from exc
        expected = f"limactl version {prepared_inputs.EXPECTED_LIMA_VERSION}"
        if output != expected:
            _fail("Lima version drift")
        return prepared_inputs.EXPECTED_LIMA_VERSION

    def _export(self, image_ref: str, destination: Path) -> None:
        command = [
            "limactl",
            "shell",
            self.instance,
            "--",
            "docker",
            "image",
            "save",
            image_ref,
        ]
        try:
            with destination.open("xb") as output:
                completed = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.PIPE,
                    check=False,
                    shell=False,
                    timeout=1800,
                )
        except (OSError, subprocess.SubprocessError) as exc:
            destination.unlink(missing_ok=True)
            raise PreparationError("OCI export command failed") from exc
        if completed.returncode != 0 or len(completed.stderr) > 4 * 1024 * 1024:
            destination.unlink(missing_ok=True)
            _fail("OCI export command failed")

    def build_and_export(
        self,
        *,
        context_tar: bytes,
        image_ref: str,
        destination: Path,
    ) -> ImageBuildResult:
        starting_lima_version = self._lima_version()
        self.vm.docker(
            [
                "build",
                "--platform",
                "linux/amd64",
                "--progress=plain",
                "--target",
                "final",
                "--tag",
                image_ref,
                "-",
            ],
            input_bytes=context_tar,
            capture=False,
        )
        index_digest = run_lima_gate._docker_image_id(self.vm, image_ref)
        self._export(image_ref, destination)
        if run_lima_gate._docker_image_id(self.vm, image_ref) != index_digest:
            destination.unlink(missing_ok=True)
            _fail("Docker image identity changed during OCI export")
        if self._lima_version() != starting_lima_version:
            destination.unlink(missing_ok=True)
            _fail("Lima version changed during image preparation")
        return ImageBuildResult(
            index_digest=index_digest,
            lima_version=starting_lima_version,
            docker=self._docker_identity(),
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-prepared-inputs", type=Path, required=True)
    parser.add_argument("--base-prepared-inputs-sha256", required=True)
    parser.add_argument("--controller-root", type=Path, required=True)
    parser.add_argument("--release-source", type=Path, required=True)
    parser.add_argument("--effective-config", type=Path, required=True)
    parser.add_argument("--effective-config-sha256", required=True)
    parser.add_argument("--instance", default=VZ_INSTANCE)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    request = PrepareRequest(
        base_prepared_inputs=args.base_prepared_inputs,
        base_prepared_inputs_sha256=args.base_prepared_inputs_sha256,
        controller_root=args.controller_root,
        release_source=args.release_source,
        effective_config=args.effective_config,
        effective_config_sha256=args.effective_config_sha256,
        instance=args.instance,
        output_directory=args.output_directory,
    )
    try:
        result = prepare(request, builder=LimaImageBuilder(request.instance))
    except (
        PreparationError,
        build_context.ProjectionError,
        prepared_inputs.PreparedInputsError,
        run_lima_gate.GateError,
    ) as exc:
        print(f"Linux preparation failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "build_context_archive": str(result.build_context_archive),
                "controller_commit": result.controller_commit,
                "index_digest": result.index_digest,
                "lima_version": result.lima_version,
                "oci_archive": str(result.oci_archive),
                "output_directory": str(result.output_directory),
                "prepared_inputs": str(result.prepared_inputs),
                "prepared_inputs_sha256": result.prepared_inputs_sha256,
                "status": "prepared-not-certified",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
