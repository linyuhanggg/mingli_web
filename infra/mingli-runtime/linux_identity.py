#!/usr/bin/env python3
"""Collect exact VZ, Rosetta, Docker, image, and amd64 container identity."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tarfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn, Protocol

IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
COMMAND_TIMEOUT_SECONDS = 120
EXPECTED_VZ_IMAGE = {
    "location": (
        "https://cloud-images.ubuntu.com/releases/resolute/"
        "release-20260720/ubuntu-26.04-server-cloudimg-arm64.img"
    ),
    "arch": "aarch64",
    "digest": (
        "sha256:7bcf159e29ad0000bfed9c57875908c39268f5ed1257f4958fa6a9f5f60edd54"
    ),
    "variant": "server",
}
IMAGE_INSPECT_FORMAT = (
    '{"id":{{json .Id}},"repo_digests":{{json .RepoDigests}},'
    '"descriptor":{{json .Descriptor}},"os":{{json .Os}},'
    '"architecture":{{json .Architecture}},"rootfs":{{json .RootFS}},'
    '"config":{{json .Config}}}'
)
CONTAINER_PROBE = r"""
import json
import os
import platform
import subprocess
import sys

import _sxtwl
import sxtwl
import yaml._yaml as yaml_extension


def elf_machine(path):
    with open(path, "rb") as stream:
        header = stream.read(20)
    if len(header) != 20 or header[:4] != b"\x7fELF":
        raise RuntimeError(f"not an ELF binary: {path}")
    byteorder = "little" if header[5] == 1 else "big"
    return int.from_bytes(header[18:20], byteorder)


def ldd_libraries(path):
    completed = subprocess.run(
        ["/usr/bin/ldd", path],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0 or "not found" in completed.stdout:
        raise RuntimeError(f"ldd failed for {path}: {completed.stdout} {completed.stderr}")
    names = []
    for raw in completed.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        names.append(line.split("=>", 1)[0].strip().split()[0])
    return sorted(set(names))


python = sys.executable
node = "/opt/node/bin/node"
git = "/opt/git/bin/git"
sxtwl_extension = _sxtwl.__file__
yaml_c_extension = yaml_extension.__file__
if not sxtwl_extension or not yaml_c_extension:
    raise RuntimeError("native extension path is absent")
day = sxtwl.fromSolar(2024, 1, 1)
payload = {
    "platform_system": platform.system(),
    "platform_machine": platform.machine(),
    "uname_machine": os.uname().machine,
    "python_version": list(sys.version_info[:3]),
    "node_version": subprocess.check_output([node, "--version"], text=True).strip(),
    "git_version": subprocess.check_output([git, "--version"], text=True).strip(),
    "sxtwl_smoke": [day.getSolarYear(), day.getSolarMonth(), day.getSolarDay()],
    "elf_machine": {
        "python": elf_machine(python),
        "node": elf_machine(node),
        "git": elf_machine(git),
        "sxtwl": elf_machine(sxtwl_extension),
        "yaml": elf_machine(yaml_c_extension),
    },
    "node_ldd_libraries": ldd_libraries(node),
    "sxtwl_ldd_libraries": ldd_libraries(sxtwl_extension),
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
""".strip()


class IdentityError(RuntimeError):
    """The machine or artifact does not satisfy the tracer boundary."""


def _fail(message: str) -> NoReturn:
    raise IdentityError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or IMAGE_ID_RE.fullmatch(value) is None:
        _fail(f"{label} is not a SHA-256 digest")
    return value


def _descriptor_blob(
    members: dict[str, tarfile.TarInfo],
    archive: tarfile.TarFile,
    descriptor: dict[str, Any],
    *,
    label: str,
) -> bytes:
    digest = _digest(descriptor.get("digest"), f"{label} digest")
    name = f"blobs/sha256/{digest.removeprefix('sha256:')}"
    member = members.get(name)
    if member is None:
        _fail(f"{label} blob is absent")
    if descriptor.get("size") != member.size:
        _fail(f"{label} descriptor size mismatch")
    stream = archive.extractfile(member)
    if stream is None:
        _fail(f"{label} blob cannot be read")
    raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != digest.removeprefix("sha256:"):
        _fail(f"{label} blob digest mismatch")
    return raw


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    return _object(_json(raw, label), label)


def verify_oci_archive(
    path: Path,
    *,
    expected_archive_sha256: str,
    image_ref: str,
    expected: dict[str, Any],
) -> dict[str, object]:
    """Verify the complete OCI index, amd64 child, attestation, and layers."""

    if (
        path.is_symlink()
        or not path.is_file()
        or sha256_file(path) != expected_archive_sha256
    ):
        _fail("OCI archive SHA-256 mismatch")
    required_keys = {
        "index_digest",
        "platform_manifest_digest",
        "config_digest",
        "attestation_manifest_digest",
        "layer_digests",
        "rootfs_diff_ids",
    }
    if set(expected) != required_keys:
        _fail("expected OCI identity fields are not exact")
    index_digest = _digest(expected["index_digest"], "OCI index")
    platform_digest = _digest(
        expected["platform_manifest_digest"], "OCI platform manifest"
    )
    config_digest = _digest(expected["config_digest"], "OCI config")
    attestation_digest = _digest(
        expected["attestation_manifest_digest"], "OCI attestation manifest"
    )
    layer_digests = expected["layer_digests"]
    rootfs_diff_ids = expected["rootfs_diff_ids"]
    if (
        not isinstance(layer_digests, list)
        or not layer_digests
        or not isinstance(rootfs_diff_ids, list)
        or len(rootfs_diff_ids) != len(layer_digests)
    ):
        _fail("OCI layer identity lists are malformed")
    for digest in [*layer_digests, *rootfs_diff_ids]:
        _digest(digest, "OCI layer")

    try:
        archive = tarfile.open(path, "r:*")  # noqa: SIM115 - normalize open errors
    except (OSError, tarfile.TarError) as exc:
        raise IdentityError("OCI archive cannot be opened") from exc
    with archive:
        members: dict[str, tarfile.TarInfo] = {}
        for member in archive.getmembers():
            name = member.name.removeprefix("./")
            parts = name.split("/")
            if (
                not name
                or name.startswith("/")
                or ".." in parts
                or name in members
                or member.issym()
                or member.islnk()
                or not (member.isdir() or member.isfile())
            ):
                _fail("OCI archive contains an unsafe or duplicate member")
            if member.isfile() and member.size > 512 * 1024 * 1024:
                _fail("OCI archive member exceeds its byte limit")
            members[name] = member

        file_members = {
            name: member for name, member in members.items() if member.isfile()
        }
        for name, member in file_members.items():
            if not name.startswith("blobs/sha256/"):
                continue
            suffix = name.removeprefix("blobs/sha256/")
            if len(suffix) != 64 or any(
                char not in "0123456789abcdef" for char in suffix
            ):
                _fail("OCI blob path is malformed")
            stream = archive.extractfile(member)
            if stream is None:
                _fail("OCI blob cannot be read")
            digest = hashlib.sha256()
            for chunk in iter(lambda stream=stream: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            if digest.hexdigest() != suffix:
                _fail("OCI blob path does not match its bytes")

        def read_named(name: str, label: str) -> bytes:
            member = file_members.get(name)
            if member is None or member.size > 16 * 1024 * 1024:
                _fail(f"{label} is absent or too large")
            stream = archive.extractfile(member)
            if stream is None:
                _fail(f"{label} cannot be read")
            return stream.read()

        layout = _json_object(read_named("oci-layout", "OCI layout"), "OCI layout")
        if layout != {"imageLayoutVersion": "1.0.0"}:
            _fail("OCI layout version mismatch")
        outer = _json_object(
            read_named("index.json", "OCI outer index"), "OCI outer index"
        )
        outer_manifests = outer.get("manifests")
        if (
            outer.get("schemaVersion") != 2
            or outer.get("mediaType") != "application/vnd.oci.image.index.v1+json"
            or not isinstance(outer_manifests, list)
            or len(outer_manifests) != 1
        ):
            _fail("OCI outer index is not exact")
        outer_descriptor = _object(outer_manifests[0], "OCI outer descriptor")
        if (
            outer_descriptor.get("digest") != index_digest
            or outer_descriptor.get("mediaType")
            != "application/vnd.oci.image.index.v1+json"
        ):
            _fail("OCI outer index digest mismatch")
        index_raw = _descriptor_blob(
            members, archive, outer_descriptor, label="OCI index"
        )
        index = _json_object(index_raw, "OCI index")
        descriptors = index.get("manifests")
        if (
            index.get("schemaVersion") != 2
            or index.get("mediaType") != "application/vnd.oci.image.index.v1+json"
            or not isinstance(descriptors, list)
            or len(descriptors) != 2
        ):
            _fail("OCI index must contain one platform and one attestation")
        descriptor_objects = [
            _object(item, "OCI child descriptor") for item in descriptors
        ]
        platform_matches = [
            item
            for item in descriptor_objects
            if item.get("platform") == {"architecture": "amd64", "os": "linux"}
        ]
        attestation_matches = [
            item
            for item in descriptor_objects
            if item.get("annotations", {}).get("vnd.docker.reference.type")
            == "attestation-manifest"
        ]
        if len(platform_matches) != 1 or len(attestation_matches) != 1:
            _fail("OCI platform or attestation descriptor is absent")
        platform_descriptor = platform_matches[0]
        attestation_descriptor = attestation_matches[0]
        if platform_descriptor.get("digest") != platform_digest:
            _fail("OCI amd64 platform manifest digest mismatch")
        if (
            attestation_descriptor.get("digest") != attestation_digest
            or attestation_descriptor.get("platform")
            != {"architecture": "unknown", "os": "unknown"}
            or attestation_descriptor.get("annotations", {}).get(
                "vnd.docker.reference.digest"
            )
            != platform_digest
        ):
            _fail("OCI attestation descriptor mismatch")
        platform_raw = _descriptor_blob(
            members, archive, platform_descriptor, label="OCI platform manifest"
        )
        attestation_raw = _descriptor_blob(
            members, archive, attestation_descriptor, label="OCI attestation manifest"
        )
        platform = _json_object(platform_raw, "OCI platform manifest")
        config_descriptor = _object(platform.get("config"), "OCI config descriptor")
        if config_descriptor.get("digest") != config_digest:
            _fail("OCI config digest mismatch")
        config_raw = _descriptor_blob(
            members, archive, config_descriptor, label="OCI config"
        )
        config = _json_object(config_raw, "OCI config")
        platform_layers = platform.get("layers")
        if not isinstance(platform_layers, list):
            _fail("OCI platform layers are absent")
        layer_descriptors = [
            _object(item, "OCI layer descriptor") for item in platform_layers
        ]
        if [item.get("digest") for item in layer_descriptors] != layer_digests:
            _fail("OCI compressed layer digests mismatch")
        rootfs = _object(config.get("rootfs"), "OCI config rootfs")
        if (
            config.get("architecture") != "amd64"
            or config.get("os") != "linux"
            or rootfs.get("type") != "layers"
            or rootfs.get("diff_ids") != rootfs_diff_ids
        ):
            _fail("OCI config platform or RootFS identity mismatch")
        runtime_config = _object(config.get("config"), "OCI runtime config")

        for descriptor, expected_diff_id in zip(
            layer_descriptors, rootfs_diff_ids, strict=True
        ):
            if (
                descriptor.get("mediaType")
                != "application/vnd.oci.image.layer.v1.tar+gzip"
            ):
                _fail("OCI layer media type mismatch")
            layer_digest = _digest(descriptor.get("digest"), "OCI layer digest")
            member = members.get(f"blobs/sha256/{layer_digest.removeprefix('sha256:')}")
            if member is None or descriptor.get("size") != member.size:
                _fail("OCI layer blob is absent or has the wrong size")
            stream = archive.extractfile(member)
            if stream is None:
                _fail("OCI layer blob cannot be read")
            uncompressed_digest = hashlib.sha256()
            try:
                with gzip.GzipFile(fileobj=stream, mode="rb") as uncompressed:
                    for chunk in iter(lambda: uncompressed.read(1024 * 1024), b""):
                        uncompressed_digest.update(chunk)
            except OSError as exc:
                raise IdentityError("OCI layer is not valid gzip") from exc
            if f"sha256:{uncompressed_digest.hexdigest()}" != expected_diff_id:
                _fail("OCI layer does not match its RootFS diff ID")

        attestation = _json_object(attestation_raw, "OCI attestation manifest")
        subject = _object(attestation.get("subject"), "OCI attestation subject")
        if (
            attestation.get("artifactType")
            != "application/vnd.docker.attestation.manifest.v1+json"
            or subject.get("digest") != platform_digest
            or subject.get("size") != len(platform_raw)
        ):
            _fail("OCI attestation subject mismatch")
        attestation_config = _object(
            attestation.get("config"), "OCI attestation config"
        )
        _descriptor_blob(
            members, archive, attestation_config, label="OCI attestation config"
        )
        attestation_layers_raw = attestation.get("layers")
        if not isinstance(attestation_layers_raw, list) or not attestation_layers_raw:
            _fail("OCI attestation payload is absent")
        attestation_layers = [
            _object(item, "OCI attestation layer") for item in attestation_layers_raw
        ]
        for descriptor in attestation_layers:
            _descriptor_blob(
                members, archive, descriptor, label="OCI attestation payload"
            )

        reachable = {
            index_digest,
            platform_digest,
            config_digest,
            attestation_digest,
            *layer_digests,
            _digest(attestation_config.get("digest"), "OCI attestation config"),
            *[
                _digest(item.get("digest"), "OCI attestation payload")
                for item in attestation_layers
            ],
        }
        actual_blobs = {
            f"sha256:{name.removeprefix('blobs/sha256/')}"
            for name in file_members
            if name.startswith("blobs/sha256/")
        }
        if actual_blobs != reachable:
            _fail("OCI archive contains unreachable or missing blobs")

        docker_manifest = _json(
            read_named("manifest.json", "Docker compatibility manifest"),
            "Docker compatibility manifest",
        )
        expected_config_path = f"blobs/sha256/{config_digest.removeprefix('sha256:')}"
        expected_layer_paths = [
            f"blobs/sha256/{digest.removeprefix('sha256:')}" for digest in layer_digests
        ]
        if docker_manifest != [
            {
                "Config": expected_config_path,
                "RepoTags": [image_ref],
                "Layers": expected_layer_paths,
            }
        ]:
            _fail("Docker compatibility manifest does not bind the exact tag")

    return {
        "archive_sha256": expected_archive_sha256,
        "index_digest": index_digest,
        "platform_manifest_digest": platform_digest,
        "config_digest": config_digest,
        "attestation_manifest_digest": attestation_digest,
        "layer_digests": list(layer_digests),
        "rootfs_diff_ids": list(rootfs_diff_ids),
        "runtime_config": runtime_config,
    }


class Runner(Protocol):
    def run(self, argv: tuple[str, ...]) -> bytes: ...


class SubprocessRunner:
    @staticmethod
    def _terminate_group(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate(timeout=2)

    def run(self, argv: tuple[str, ...]) -> bytes:
        try:
            process = subprocess.Popen(
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=True,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise IdentityError(f"identity command could not start: {argv[0]}") from exc
        try:
            stdout, stderr = process.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            self._terminate_group(process)
            raise IdentityError(f"identity command timed out: {argv[0]}") from exc
        except BaseException:
            self._terminate_group(process)
            raise
        if len(stdout) > MAX_OUTPUT_BYTES:
            _fail("identity command stdout exceeded its byte limit")
        if len(stderr) > MAX_OUTPUT_BYTES:
            _fail("identity command stderr exceeded its byte limit")
        if process.returncode != 0:
            diagnostic = stderr.decode("utf-8", errors="replace")[-4000:]
            _fail(f"identity command failed ({argv[0]}): {diagnostic}")
        return stdout


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _fail(f"{label} must be an object")
    return value


def _json(raw: bytes, label: str) -> object:
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityError(f"{label} is not valid JSON") from exc


def _instance_record(raw: bytes, instance: str) -> dict[str, Any]:
    records = []
    for line in raw.splitlines():
        if line.strip():
            records.append(
                _object(_json(line, "Lima instance record"), "Lima instance")
            )
    matches = [record for record in records if record.get("name") == instance]
    if len(matches) != 1:
        _fail("exact Lima instance is absent or duplicated")
    record = matches[0]
    config = _object(record.get("config"), "Lima effective config")
    vm_opts = _object(config.get("vmOpts"), "Lima vmOpts")
    vz = _object(vm_opts.get("vz"), "Lima VZ options")
    rosetta = _object(vz.get("rosetta"), "Lima Rosetta options")
    if (
        record.get("status") != "Running"
        or record.get("vmType") != "vz"
        or record.get("arch") != "aarch64"
        or record.get("cpus") != 10
        or record.get("memory") != 10 * 1024**3
        or record.get("disk") != 60 * 1024**3
        or config.get("minimumLimaVersion") != "2.2.0"
        or config.get("vmType") != "vz"
        or config.get("arch") != "aarch64"
        or config.get("cpus") != 10
        or config.get("memory") != "10GiB"
        or config.get("disk") != "60GiB"
        or config.get("mounts", []) != []
        or config.get("propagateProxyEnv") is not False
        or config.get("images") != [EXPECTED_VZ_IMAGE]
        or rosetta != {"enabled": True, "binfmt": True}
    ):
        _fail("Lima instance drifted from the mountless VZ Rosetta profile")
    return record


def _docker_identity(raw: bytes) -> dict[str, str]:
    payload = _object(_json(raw, "Docker version"), "Docker version")
    client = _object(payload.get("Client"), "Docker client")
    server = _object(payload.get("Server"), "Docker server")
    components = server.get("Components")
    if not isinstance(components, list):
        _fail("Docker components are absent")
    component_versions = {
        str(component.get("Name")): str(component.get("Version"))
        for component in components
        if isinstance(component, dict)
    }
    return {
        "client_version": str(client.get("Version")),
        "server_version": str(server.get("Version")),
        "server_arch": str(server.get("Arch")),
        "containerd_version": component_versions.get("containerd", ""),
        "rootlesskit_version": component_versions.get("rootlesskit", ""),
    }


def collect_identity(
    *,
    instance: str,
    image_ref: str,
    immutable_image_ref: str,
    oci_archive: Path,
    expected_oci_archive_sha256: str,
    expected_oci: dict[str, Any],
    effective_config: Path,
    expected_effective_config_sha256: str,
    runner: Runner,
) -> dict[str, object]:
    index_digest = _digest(expected_oci.get("index_digest"), "expected OCI index")
    repository, separator, digest = immutable_image_ref.rpartition("@")
    if not separator or not repository or digest != index_digest:
        _fail("immutable image ref does not bind the expected OCI index")
    archive_identity = verify_oci_archive(
        oci_archive,
        expected_archive_sha256=expected_oci_archive_sha256,
        image_ref=image_ref,
        expected=expected_oci,
    )
    if (
        effective_config.is_symlink()
        or not effective_config.is_file()
        or sha256_file(effective_config) != expected_effective_config_sha256
    ):
        _fail("effective Lima config SHA-256 mismatch")
    instance_record = _instance_record(
        runner.run(("limactl", "list", "--json")), instance
    )
    docker = _docker_identity(
        runner.run(
            (
                "limactl",
                "shell",
                instance,
                "--",
                "docker",
                "version",
                "--format",
                "{{json .}}",
            )
        )
    )
    image = _object(
        _json(
            runner.run(
                (
                    "limactl",
                    "shell",
                    instance,
                    "--",
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    IMAGE_INSPECT_FORMAT,
                    immutable_image_ref,
                )
            ),
            "Docker image inspect",
        ),
        "Docker image inspect",
    )
    descriptor = _object(image.get("descriptor"), "Docker image descriptor")
    rootfs = _object(image.get("rootfs"), "Docker image RootFS")
    image_config = _object(image.get("config"), "Docker image config")
    repo_digests = image.get("repo_digests")
    if (
        image.get("id") != index_digest
        or image.get("os") != "linux"
        or image.get("architecture") != "amd64"
        or repo_digests != [immutable_image_ref]
        or descriptor.get("digest") != index_digest
        or descriptor.get("mediaType") != "application/vnd.oci.image.index.v1+json"
        or rootfs != {"Type": "layers", "Layers": expected_oci["rootfs_diff_ids"]}
        or image_config != archive_identity["runtime_config"]
    ):
        _fail("Docker image identity mismatch")
    docker_image = {
        "id": image["id"],
        "descriptor_digest": descriptor["digest"],
        "descriptor_media_type": descriptor["mediaType"],
        "immutable_ref": immutable_image_ref,
        "os": image["os"],
        "architecture": image["architecture"],
        "rootfs_diff_ids": rootfs["Layers"],
    }
    container = _object(
        _json(
            runner.run(
                (
                    "limactl",
                    "shell",
                    instance,
                    "--",
                    "docker",
                    "run",
                    "--label",
                    "io.fateradar.mingli.gate=linux-amd64-identity-tracer",
                    "--rm",
                    "--read-only",
                    "--network=none",
                    "--platform=linux/amd64",
                    "--device=lima-vm.io/rosetta=cached",
                    "--security-opt=no-new-privileges",
                    "--cap-drop=ALL",
                    "--pids-limit=64",
                    "--memory=512m",
                    "--tmpfs",
                    "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
                    "--entrypoint",
                    "/opt/mingli-runtime/venv/bin/python",
                    immutable_image_ref,
                    "-I",
                    "-B",
                    "-c",
                    CONTAINER_PROBE,
                )
            ),
            "amd64 container identity",
        ),
        "amd64 container identity",
    )
    if sha256_file(effective_config) != expected_effective_config_sha256:
        _fail("effective Lima config changed during identity trace")
    ending_archive_identity = verify_oci_archive(
        oci_archive,
        expected_archive_sha256=expected_oci_archive_sha256,
        image_ref=image_ref,
        expected=expected_oci,
    )
    if ending_archive_identity != archive_identity:
        _fail("OCI archive identity changed during trace")
    config = _object(instance_record.get("config"), "Lima effective config")
    rosetta = _object(
        _object(
            _object(config.get("vmOpts"), "Lima vmOpts").get("vz"),
            "Lima VZ options",
        ).get("rosetta"),
        "Lima Rosetta options",
    )
    return {
        "schema": "mingli-vz-amd64-identity-v1",
        "instance": {
            "vm_type": instance_record["vmType"],
            "guest_arch": instance_record["arch"],
            "rosetta_enabled": rosetta["enabled"],
            "rosetta_binfmt": rosetta["binfmt"],
        },
        "docker": docker,
        "image": {
            key: value
            for key, value in archive_identity.items()
            if key != "runtime_config"
        }
        | {"docker": docker_image},
        "container": container,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--immutable-image-ref", required=True)
    parser.add_argument("--oci-archive", type=Path, required=True)
    parser.add_argument("--oci-archive-sha256", required=True)
    parser.add_argument("--oci-index-digest", required=True)
    parser.add_argument("--oci-platform-manifest-digest", required=True)
    parser.add_argument("--oci-config-digest", required=True)
    parser.add_argument("--oci-attestation-manifest-digest", required=True)
    parser.add_argument("--oci-layer-digest", action="append", required=True)
    parser.add_argument("--oci-rootfs-diff-id", action="append", required=True)
    parser.add_argument("--effective-config", type=Path, required=True)
    parser.add_argument("--effective-config-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        identity = collect_identity(
            instance=args.instance,
            image_ref=args.image_ref,
            immutable_image_ref=args.immutable_image_ref,
            oci_archive=args.oci_archive.expanduser().resolve(),
            expected_oci_archive_sha256=args.oci_archive_sha256,
            expected_oci={
                "index_digest": args.oci_index_digest,
                "platform_manifest_digest": args.oci_platform_manifest_digest,
                "config_digest": args.oci_config_digest,
                "attestation_manifest_digest": args.oci_attestation_manifest_digest,
                "layer_digests": args.oci_layer_digest,
                "rootfs_diff_ids": args.oci_rootfs_diff_id,
            },
            effective_config=args.effective_config.expanduser().resolve(),
            expected_effective_config_sha256=args.effective_config_sha256,
            runner=SubprocessRunner(),
        )
    except IdentityError as exc:
        print(f"Linux identity tracer failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(identity, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
