#!/usr/bin/env python3
"""Collect exact VZ, Rosetta, Docker, image, and amd64 container identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
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
    '{"id":{{json .Id}},"os":{{json .Os}},"architecture":{{json .Architecture}}}'
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


class Runner(Protocol):
    def run(self, argv: tuple[str, ...]) -> bytes: ...


class SubprocessRunner:
    def run(self, argv: tuple[str, ...]) -> bytes:
        completed = subprocess.run(
            list(argv),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            shell=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if len(completed.stdout) > MAX_OUTPUT_BYTES:
            _fail("identity command stdout exceeded its byte limit")
        if len(completed.stderr) > MAX_OUTPUT_BYTES:
            _fail("identity command stderr exceeded its byte limit")
        if completed.returncode != 0:
            diagnostic = completed.stderr.decode("utf-8", errors="replace")[-4000:]
            _fail(f"identity command failed ({argv[0]}): {diagnostic}")
        return completed.stdout


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
    expected_image_id: str,
    effective_config: Path,
    expected_effective_config_sha256: str,
    runner: Runner,
) -> dict[str, object]:
    if IMAGE_ID_RE.fullmatch(expected_image_id) is None:
        _fail("expected image ID is malformed")
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
                    image_ref,
                )
            ),
            "Docker image inspect",
        ),
        "Docker image inspect",
    )
    if image != {
        "id": expected_image_id,
        "os": "linux",
        "architecture": "amd64",
    }:
        _fail("Docker image identity mismatch")
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
                    image_ref,
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
        "image": image,
        "container": container,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--effective-config", type=Path, required=True)
    parser.add_argument("--effective-config-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        identity = collect_identity(
            instance=args.instance,
            image_ref=args.image_ref,
            expected_image_id=args.expected_image_id,
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
