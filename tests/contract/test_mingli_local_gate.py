#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import importlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "infra" / "mingli-runtime"
EXPECTED_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)
VZ_PROFILE_PATH = RUNTIME_DIR / "lima-vz-rosetta.yaml"
PREPARE_LINUX_INPUTS_PATH = RUNTIME_DIR / "prepare_linux_inputs.py"
EXPECTED_LINUX_IMAGE_ID = (
    "sha256:608401536f5c0a84efbbaf17e9e6e5c76ef3e2991562ae38a01b79a0232df0fd"
)
EXPECTED_LINUX_PLATFORM_MANIFEST = (
    "sha256:7678978220e07bf84514c6d15dbbdb4f289ca601302c38985b94292c135ed32f"
)
EXPECTED_LINUX_CONFIG = (
    "sha256:e89014940e10ebeab2352ecbaae6de58b5b7c3df8851f9c873223f1e9b064e27"
)
EXPECTED_LINUX_ATTESTATION = (
    "sha256:0bbf16052a906a714789109ae3947454059f40a5c902d5a0595177d9a1051e04"
)
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_local_gate() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("local_gate", None)
        sys.modules.pop("prepared_inputs", None)
        sys.modules.pop("verify_local_full", None)
        return importlib.import_module("local_gate")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def load_local_verifier() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("verify_local_full", None)
        return importlib.import_module("verify_local_full")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def load_linux_identity() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("linux_identity", None)
        return importlib.import_module("linux_identity")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def load_linux_preparer() -> ModuleType:
    assert PREPARE_LINUX_INPUTS_PATH.is_file(), (
        "Linux PreparedInputs producer is absent; formal certification stays RED"
    )
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("prepare_linux_inputs", None)
        return importlib.import_module("prepare_linux_inputs")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def load_lima_controller() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("run_lima_gate", None)
        return importlib.import_module("run_lima_gate")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def write_prepared_inputs(tmp_path: Path) -> tuple[Path, str, dict[str, Any]]:
    source_root = tmp_path / "source"
    scripts = source_root / "scripts"
    scripts.mkdir(parents=True)
    runner = scripts / "run_test_suite.py"
    runner.write_text(
        "raise SystemExit('scripted test must not execute')\n", encoding="utf-8"
    )
    lock = source_root / "requirements-runtime.lock"
    lock.write_text("locked\n", encoding="utf-8")
    release_manifest = source_root / ".mingli-release-manifest.json"
    release_manifest.write_text('{"fixture":"release"}\n', encoding="utf-8")
    research_root = tmp_path / "research"
    research_root.mkdir()
    (research_root / "book.txt").write_text("fixture research\n", encoding="utf-8")
    runtime_root = tmp_path / "native-runtime"
    runtime_bin = runtime_root / "bin"
    runtime_bin.mkdir(parents=True)
    python = runtime_bin / "python"
    shutil.copy2(Path(sys.executable).resolve(strict=True), python)
    runtime_integrity = runtime_root / "runtime-integrity.json"
    runtime_integrity.write_text('{"schema_version":1}\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(source_root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(source_root), "add", "--all"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    source_commit = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
    ).strip()
    source_tree_sha256 = tree_sha256(source_root)
    research_tree_sha256 = tree_sha256(research_root)
    runtime_tree_sha256 = tree_sha256(runtime_root)
    prepared_module = sys.modules.get("prepared_inputs")
    if prepared_module is not None:
        prepared_module.EXPECTED_RELEASE_MANIFEST_SHA256 = sha256_file(release_manifest)
        prepared_module.EXPECTED_COMMIT = source_commit
    payload = {
        "schema": "mingli-prepared-inputs-v1",
        "source": {
            "root": str(source_root),
            "commit": source_commit,
            "release_manifest": str(release_manifest),
            "release_manifest_sha256": sha256_file(release_manifest),
            "tree_sha256": source_tree_sha256,
        },
        "research": {
            "root": str(research_root),
            "commit": source_commit,
            "tree_sha256": research_tree_sha256,
        },
        "native_runtime": {
            "root": str(runtime_root),
            "tree_sha256": runtime_tree_sha256,
            "python": str(python),
            "python_sha256": sha256_file(python),
            "runtime_integrity": str(runtime_integrity),
            "runtime_integrity_sha256": sha256_file(runtime_integrity),
            "requirements_lock": str(lock),
            "requirements_lock_sha256": sha256_file(lock),
        },
        "bindings": [
            {
                "path": str(runner),
                "kind": "file",
                "sha256": sha256_file(runner),
            },
            {
                "path": str(lock),
                "kind": "file",
                "sha256": sha256_file(lock),
            },
            {
                "path": str(release_manifest),
                "kind": "file",
                "sha256": sha256_file(release_manifest),
            },
            {
                "path": str(runtime_integrity),
                "kind": "file",
                "sha256": sha256_file(runtime_integrity),
            },
        ],
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path = tmp_path / "prepared-inputs.json"
    path.write_bytes(raw)
    return path, sha256_bytes(raw), payload


def tree_sha256(root: Path) -> str:
    """Test-side canonical digest for a closed regular-file/symlink tree."""

    digest = hashlib.sha256()
    for path in sorted(
        (
            path
            for path in root.rglob("*")
            if ".git" not in path.relative_to(root).parts
        ),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix().encode()
        if path.is_symlink():
            record = b"L\0" + relative + b"\0" + os.readlink(path).encode() + b"\0"
        elif path.is_file():
            mode = path.stat().st_mode & 0o777
            record = (
                b"F\0"
                + relative
                + b"\0"
                + f"{mode:o}".encode()
                + b"\0"
                + sha256_file(path).encode()
                + b"\0"
            )
        elif path.is_dir():
            continue
        else:
            raise AssertionError(f"unsupported fixture entry: {path}")
        digest.update(record)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest_ref(raw: bytes) -> str:
    return f"sha256:{sha256_bytes(raw)}"


def write_oci_archive(
    path: Path,
    image_ref: str,
    *,
    build_context_sha256: str = "f" * 64,
) -> dict[str, Any]:
    layer_uncompressed = b"fixture-linux-amd64-layer"
    layer = gzip.compress(layer_uncompressed, mtime=0)
    layer_digest = digest_ref(layer)
    diff_id = digest_ref(layer_uncompressed)
    runtime_config = {
        "User": "10001:10001",
        "Env": ["PATH=/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE=1"],
        "Entrypoint": ["/opt/mingli-master/scripts/run_reading_transaction.sh"],
        "WorkingDir": "/opt/mingli-master",
    }
    config_raw = canonical_json_bytes(
        {
            "architecture": "amd64",
            "config": runtime_config,
            "os": "linux",
            "rootfs": {"type": "layers", "diff_ids": [diff_id]},
        }
    )
    config_digest = digest_ref(config_raw)
    platform_raw = canonical_json_bytes(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": config_digest,
                "size": len(config_raw),
            },
            "layers": [
                {
                    "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": layer_digest,
                    "size": len(layer),
                }
            ],
        }
    )
    platform_digest = digest_ref(platform_raw)
    empty_raw = b"{}"
    context_uri = "http://buildkit-session/fixture"
    statement_raw = canonical_json_bytes(
        {
            "_type": "https://in-toto.io/Statement/v1",
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [
                {
                    "name": f"pkg:docker/{image_ref}?platform=linux%2Famd64",
                    "digest": {"sha256": platform_digest.removeprefix("sha256:")},
                }
            ],
            "predicate": {
                "buildDefinition": {
                    "resolvedDependencies": [
                        {
                            "uri": context_uri,
                            "digest": {"sha256": build_context_sha256},
                        }
                    ],
                    "externalParameters": {
                        "configSource": {
                            "uri": context_uri,
                            "digest": {"sha256": build_context_sha256},
                            "path": "Dockerfile",
                        },
                        "request": {
                            "frontend": "gateway.v0",
                            "args": {"target": "final"},
                        },
                    },
                }
            },
        }
    )
    statement_digest = digest_ref(statement_raw)
    attestation_raw = canonical_json_bytes(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "artifactType": "application/vnd.docker.attestation.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.oci.empty.v1+json",
                "digest": digest_ref(empty_raw),
                "size": len(empty_raw),
            },
            "layers": [
                {
                    "mediaType": "application/vnd.in-toto+json",
                    "digest": statement_digest,
                    "size": len(statement_raw),
                    "annotations": {
                        "in-toto.io/predicate-type": ("https://slsa.dev/provenance/v1")
                    },
                }
            ],
            "subject": {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": platform_digest,
                "size": len(platform_raw),
            },
        }
    )
    attestation_digest = digest_ref(attestation_raw)
    index_raw = canonical_json_bytes(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": platform_digest,
                    "size": len(platform_raw),
                    "platform": {"architecture": "amd64", "os": "linux"},
                },
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": attestation_digest,
                    "size": len(attestation_raw),
                    "annotations": {
                        "vnd.docker.reference.digest": platform_digest,
                        "vnd.docker.reference.type": "attestation-manifest",
                    },
                    "platform": {"architecture": "unknown", "os": "unknown"},
                },
            ],
        }
    )
    index_digest = digest_ref(index_raw)
    outer_index = canonical_json_bytes(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.index.v1+json",
                    "digest": index_digest,
                    "size": len(index_raw),
                    "annotations": {
                        "io.containerd.image.name": f"docker.io/library/{image_ref}",
                        "org.opencontainers.image.ref.name": image_ref.rsplit(":", 1)[
                            -1
                        ],
                    },
                }
            ],
        }
    )
    docker_manifest = canonical_json_bytes(
        [
            {
                "Config": f"blobs/sha256/{config_digest.removeprefix('sha256:')}",
                "RepoTags": [image_ref],
                "Layers": [f"blobs/sha256/{layer_digest.removeprefix('sha256:')}"],
            }
        ]
    )
    blobs = {
        index_digest: index_raw,
        platform_digest: platform_raw,
        config_digest: config_raw,
        attestation_digest: attestation_raw,
        digest_ref(empty_raw): empty_raw,
        statement_digest: statement_raw,
        layer_digest: layer,
    }
    members = {
        "oci-layout": canonical_json_bytes({"imageLayoutVersion": "1.0.0"}),
        "index.json": outer_index,
        "manifest.json": docker_manifest,
        **{
            f"blobs/sha256/{digest.removeprefix('sha256:')}": raw
            for digest, raw in blobs.items()
        },
    }
    with tarfile.open(path, "w") as archive:
        for name, raw in sorted(members.items()):
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.mode = 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(raw))
    return {
        "index_digest": index_digest,
        "platform_manifest_digest": platform_digest,
        "config_digest": config_digest,
        "attestation_manifest_digest": attestation_digest,
        "layer_digests": [layer_digest],
        "rootfs_diff_ids": [diff_id],
        "runtime_config": runtime_config,
    }


def write_linux_prepared_inputs(tmp_path: Path) -> tuple[Path, str, dict[str, Any]]:
    path, _, payload = write_prepared_inputs(tmp_path)
    effective_config = tmp_path / "effective-vz.yaml"
    effective_config.write_text("vmType: vz\narch: aarch64\n", encoding="utf-8")
    oci_archive = tmp_path / "mingli-runtime.oci"
    image_ref = "mingli-runtime:task8-final"
    oci = write_oci_archive(oci_archive, image_ref)
    payload["linux_runtime"] = {
        "instance": "mingli-linux-gate-vz",
        "lima_version": "2.2.0",
        "effective_config": str(effective_config),
        "effective_config_sha256": sha256_file(effective_config),
        "image_ref": image_ref,
        "image_repository": "mingli-runtime",
        "immutable_image_ref": f"mingli-runtime@{oci['index_digest']}",
        "oci": {key: value for key, value in oci.items() if key != "runtime_config"},
        "oci_archive": str(oci_archive),
        "oci_archive_sha256": sha256_file(oci_archive),
        "docker": {
            "client_version": "29.7.2",
            "server_version": "29.7.2",
            "server_arch": "arm64",
            "containerd_version": "v2.3.3",
            "rootlesskit_version": "3.0.2",
        },
    }
    payload["bindings"].extend(
        [
            {
                "path": str(effective_config),
                "kind": "file",
                "sha256": sha256_file(effective_config),
            },
            {
                "path": str(oci_archive),
                "kind": "file",
                "sha256": sha256_file(oci_archive),
            },
        ]
    )
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    return path, sha256_bytes(raw), payload


def write_controller_repository(
    tmp_path: Path, preparer: ModuleType
) -> tuple[Path, str]:
    controller_root = tmp_path / "controller"
    for relative in preparer.CONTROLLER_INPUT_PATHS:
        target = controller_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"fixture controller input: {relative}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(controller_root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(controller_root), "add", "--all"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(controller_root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "controller fixture",
        ],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        },
    )
    controller_commit = subprocess.check_output(
        ["git", "-C", str(controller_root), "rev-parse", "HEAD"], text=True
    ).strip()
    return controller_root, controller_commit


def write_formal_linux_prepared_inputs(
    tmp_path: Path,
    gate_module: ModuleType,
) -> tuple[Path, str, dict[str, Any]]:
    preparer = load_linux_preparer()
    path, _, payload = write_linux_prepared_inputs(tmp_path)
    controller_root, controller_commit = write_controller_repository(tmp_path, preparer)
    context_root = tmp_path / "build-context"
    context_root.mkdir()
    release_fixture = context_root / "release" / "fixture.txt"
    release_fixture.parent.mkdir()
    release_fixture.write_text("signed projection fixture\n", encoding="utf-8")
    for name in preparer.BUILD_CONTEXT_INPUT_NAMES:
        source = controller_root / "infra" / "mingli-runtime" / name
        shutil.copy2(source, context_root / name)
    provenance = context_root / "context-provenance.json"
    provenance.write_text('{"schema":"fixture"}\n', encoding="utf-8")
    context_tree_sha256 = tree_sha256(context_root)
    context_archive = tmp_path / preparer.BUILD_CONTEXT_ARCHIVE_NAME
    with tarfile.open(context_archive, "w", format=tarfile.PAX_FORMAT) as archive:
        for candidate in sorted(
            context_root.rglob("*"),
            key=lambda item: item.relative_to(context_root).as_posix(),
        ):
            relative = candidate.relative_to(context_root).as_posix()
            info = archive.gettarinfo(str(candidate), arcname=relative)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            if candidate.is_dir():
                archive.addfile(info)
            else:
                with candidate.open("rb") as stream:
                    archive.addfile(info, stream)
    linux = payload["linux_runtime"]
    oci_archive = Path(linux["oci_archive"])
    oci = write_oci_archive(
        oci_archive,
        linux["image_ref"],
        build_context_sha256=sha256_file(context_archive),
    )
    linux["oci"] = {key: value for key, value in oci.items() if key != "runtime_config"}
    linux["oci_archive_sha256"] = sha256_file(oci_archive)
    linux["immutable_image_ref"] = f"{linux['image_repository']}@{oci['index_digest']}"
    for binding in payload["bindings"]:
        if binding["path"] == str(oci_archive):
            binding["sha256"] = sha256_file(oci_archive)
    preparation_record = tmp_path / preparer.PREPARATION_RECORD_NAME
    controller_sha256 = {
        relative: sha256_file(controller_root / relative)
        for relative in preparer.CONTROLLER_INPUT_PATHS
    }
    infra_sha256 = {
        name: sha256_file(context_root / name)
        for name in preparer.BUILD_CONTEXT_INPUT_NAMES
    }
    record = {
        "schema": preparer.PREPARATION_SCHEMA,
        "controller": {
            "repository_root": str(controller_root),
            "commit": controller_commit,
            "input_sha256": controller_sha256,
        },
        "build_context": {
            "archive": str(context_archive),
            "archive_sha256": sha256_file(context_archive),
            "tree_sha256": context_tree_sha256,
            "infra_sha256": infra_sha256,
        },
        "runtime": {
            "instance": linux["instance"],
            "lima_version": linux["lima_version"],
            "effective_config_sha256": linux["effective_config_sha256"],
            "docker": linux["docker"],
        },
        "image": {
            "image_ref": linux["image_ref"],
            "image_repository": linux["image_repository"],
            "immutable_image_ref": linux["immutable_image_ref"],
            "oci_archive": linux["oci_archive"],
            "oci_archive_sha256": linux["oci_archive_sha256"],
            "oci": linux["oci"],
        },
        "commands": {
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
                linux["image_ref"],
                "-",
            ],
            "export": ["docker", "image", "save", linux["image_ref"]],
        },
    }
    preparation_record.write_bytes(canonical_json_bytes(record) + b"\n")
    linux["preparation"] = {
        "record": str(preparation_record),
        "record_sha256": sha256_file(preparation_record),
        "controller_commit": controller_commit,
        "build_context_archive": str(context_archive),
        "build_context_archive_sha256": sha256_file(context_archive),
        "build_context_tree_sha256": context_tree_sha256,
    }
    payload["bindings"].extend(
        [
            {
                "path": str(preparation_record),
                "kind": "file",
                "sha256": sha256_file(preparation_record),
            },
            {
                "path": str(context_archive),
                "kind": "file",
                "sha256": sha256_file(context_archive),
            },
            *[
                {
                    "path": str(controller_root / relative),
                    "kind": "file",
                    "sha256": controller_sha256[relative],
                }
                for relative in preparer.CONTROLLER_INPUT_PATHS
            ],
        ]
    )
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    loaded = gate_module.prepared_inputs.load(path, sha256_bytes(raw))
    gate_module.prepared_inputs.require_certifiable_linux(loaded)
    return path, sha256_bytes(raw), payload


def reseal_linux_preparation(
    manifest_path: Path,
    payload: dict[str, Any],
    record: dict[str, Any],
) -> str:
    preparation = payload["linux_runtime"]["preparation"]
    record_path = Path(preparation["record"])
    record_path.write_bytes(canonical_json_bytes(record) + b"\n")
    preparation["record_sha256"] = sha256_file(record_path)
    for binding in payload["bindings"]:
        if binding["path"] == str(record_path):
            binding["sha256"] = sha256_file(record_path)
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)
    return sha256_bytes(raw)


def docker_image_payload(payload: dict[str, Any]) -> dict[str, Any]:
    linux = payload["linux_runtime"]
    oci = linux["oci"]
    archive_path = Path(linux["oci_archive"])
    with tarfile.open(archive_path, "r") as archive:
        config_member = archive.extractfile(
            f"blobs/sha256/{oci['config_digest'].removeprefix('sha256:')}"
        )
        assert config_member is not None
        runtime_config = json.loads(config_member.read())["config"]
    return {
        "id": oci["index_digest"],
        "repo_digests": [linux["immutable_image_ref"]],
        "descriptor": {
            "digest": oci["index_digest"],
            "mediaType": "application/vnd.oci.image.index.v1+json",
        },
        "os": "linux",
        "architecture": "amd64",
        "rootfs": {"Type": "layers", "Layers": oci["rootfs_diff_ids"]},
        "config": runtime_config,
    }


def complete_linux_identity(payload: dict[str, Any]) -> dict[str, Any]:
    linux = payload["linux_runtime"]
    oci = linux["oci"]
    return {
        "schema": "mingli-vz-amd64-identity-v1",
        "lima_version": payload["linux_runtime"]["lima_version"],
        "instance": {
            "vm_type": "vz",
            "guest_arch": "aarch64",
            "rosetta_enabled": True,
            "rosetta_binfmt": True,
        },
        "docker": {
            "client_version": "29.7.2",
            "server_version": "29.7.2",
            "server_arch": "arm64",
            "containerd_version": "v2.3.3",
            "rootlesskit_version": "3.0.2",
        },
        "image": {
            "archive_sha256": linux["oci_archive_sha256"],
            "index_digest": oci["index_digest"],
            "platform_manifest_digest": oci["platform_manifest_digest"],
            "config_digest": oci["config_digest"],
            "attestation_manifest_digest": oci["attestation_manifest_digest"],
            "layer_digests": oci["layer_digests"],
            "rootfs_diff_ids": oci["rootfs_diff_ids"],
            "docker": {
                "id": oci["index_digest"],
                "descriptor_digest": oci["index_digest"],
                "descriptor_media_type": "application/vnd.oci.image.index.v1+json",
                "immutable_ref": linux["immutable_image_ref"],
                "os": "linux",
                "architecture": "amd64",
                "rootfs_diff_ids": oci["rootfs_diff_ids"],
            },
        },
        "container": {
            "platform_system": "Linux",
            "platform_machine": "x86_64",
            "uname_machine": "x86_64",
            "python_version": [3, 14, 6],
            "node_version": "v26.3.0",
            "git_version": "git version 2.39.5",
            "sxtwl_smoke": [2024, 1, 1],
            "elf_machine": {
                "python": 62,
                "node": 62,
                "git": 62,
                "sxtwl": 62,
                "yaml": 62,
            },
            "node_ldd_libraries": ["libatomic.so.1", "libc.so.6"],
            "sxtwl_ldd_libraries": ["libstdc++.so.6", "libc.so.6"],
        },
    }


def complete_lima_instance() -> dict[str, Any]:
    return {
        "name": "mingli-linux-gate-vz",
        "status": "Running",
        "vmType": "vz",
        "arch": "aarch64",
        "cpus": 10,
        "memory": 10 * 1024**3,
        "disk": 60 * 1024**3,
        "config": {
            "minimumLimaVersion": "2.2.0",
            "vmType": "vz",
            "arch": "aarch64",
            "cpus": 10,
            "memory": "10GiB",
            "disk": "60GiB",
            "mounts": [],
            "propagateProxyEnv": False,
            "images": [EXPECTED_VZ_IMAGE],
            "vmOpts": {"vz": {"rosetta": {"enabled": True, "binfmt": True}}},
        },
    }


class ScriptedExecution:
    def __init__(
        self,
        module: ModuleType,
        *,
        stdout: str,
        elapsed_seconds: float,
        returncode: int = 0,
        on_run: Callable[[], None] | None = None,
    ) -> None:
        self.module = module
        self.stdout = stdout
        self.elapsed_seconds = elapsed_seconds
        self.returncode = returncode
        self.on_run = on_run
        self.commands: list[Any] = []

    def run(self, command: Any) -> Any:
        self.commands.append(command)
        if self.on_run is not None:
            self.on_run()
        return self.module.CommandResult(
            stdout=self.stdout.encode(),
            stderr=b"",
            returncode=self.returncode,
            started_monotonic=100.0,
            finished_monotonic=100.0 + self.elapsed_seconds,
        )


def native_request(
    gate_module: ModuleType,
    tmp_path: Path,
    *,
    deadline_seconds: int = 600,
    slots: int = 10,
) -> tuple[Any, dict[str, Any]]:
    manifest_path, manifest_sha256, payload = write_prepared_inputs(tmp_path)
    request = gate_module.LocalFullRequest(
        profile="native-full",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=manifest_sha256,
        ),
        output_parent=tmp_path / "output",
        deadline_seconds=deadline_seconds,
        slots=slots,
    )
    return request, payload


def complete_summary(*, elapsed_seconds: float = 434.62) -> str:
    return (
        "test plan: targets=126 modules=93 workers=10 parallel=100 serial=26\n"
        "summary: targets=126 modules=93 tests=1584 "
        f"failed_modules=0 elapsed={elapsed_seconds:.2f}s\n"
    )


def assert_nothing_published(output_parent: Path) -> None:
    assert not output_parent.exists() or list(output_parent.iterdir()) == []


def test_profile_clock_starts_after_initial_prepared_input_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    events: list[str] = []
    original_load = gate_module.prepared_inputs.load

    def observed_load(path: Path, expected_sha256: str) -> Any:
        events.append("load")
        return original_load(path, expected_sha256)

    def observed_monotonic() -> float:
        events.append("clock")
        return 0.0

    monkeypatch.setattr(gate_module.prepared_inputs, "load", observed_load)

    gate_module.LocalFullGate(
        ScriptedExecution(
            gate_module,
            stdout=complete_summary(elapsed_seconds=1.0),
            elapsed_seconds=1.0,
        ),
        monotonic=observed_monotonic,
    ).run(request)

    assert events[:2] == ["load", "clock"]


def test_native_full_accepts_only_complete_suite_under_budget(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=434.62,
    )

    result = gate_module.LocalFullGate(execution).run(request)

    assert result.profile == "native-full"
    assert result.elapsed_seconds == 434.62
    assert len(result.timeline) == 1
    assert result.timeline[0].command_id == "native-release-regression"
    assert result.profile_report.name == "native-full-5.1.json"
    assert result.profile_report.is_file()
    assert len(execution.commands) == 1
    command = execution.commands[0]
    source_root = Path(payload["source"]["root"])
    assert command.argv == (
        payload["native_runtime"]["python"],
        "-B",
        str(source_root / "scripts" / "run_test_suite.py"),
        "--jobs",
        "10",
        "--research-root",
        payload["research"]["root"],
    )
    assert command.cwd == source_root
    assert command.shell is False


@pytest.mark.parametrize(
    "summary",
    [
        "no authoritative summary\n",
        "summary: targets=125 modules=93 tests=1584 failed_modules=0 elapsed=1.00s\n",
        "summary: targets=126 modules=92 tests=1584 failed_modules=0 elapsed=1.00s\n",
        "summary: targets=126 modules=93 tests=1583 failed_modules=0 elapsed=1.00s\n",
        "summary: targets=126 modules=93 tests=1584 failed_modules=1 elapsed=1.00s\n",
    ],
)
def test_native_full_rejects_incomplete_or_missing_summary(
    tmp_path: Path,
    summary: str,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=summary,
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


@pytest.mark.parametrize(
    ("returncode", "actual_elapsed", "summary_elapsed"),
    [
        (1, 1.0, 1.0),
        (0, 600.001, 1.0),
        (0, 1.0, 600.01),
    ],
)
def test_native_full_rejects_failure_or_timeout(
    tmp_path: Path,
    returncode: int,
    actual_elapsed: float,
    summary_elapsed: float,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(elapsed_seconds=summary_elapsed),
        elapsed_seconds=actual_elapsed,
        returncode=returncode,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


@pytest.mark.parametrize(
    ("deadline_seconds", "slots"),
    [(601, 10), (600, 11), (0, 10), (600, 0)],
)
def test_native_full_cannot_relax_or_disable_resource_limits(
    tmp_path: Path,
    deadline_seconds: int,
    slots: int,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(
        gate_module,
        tmp_path,
        deadline_seconds=deadline_seconds,
        slots=slots,
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_native_full_rejects_manifest_sha_mismatch(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    request = gate_module.LocalFullRequest(
        profile=request.profile,
        prepared_inputs=gate_module.PreparedInputsRef(
            path=request.prepared_inputs.path,
            sha256="0" * 64,
        ),
        output_parent=request.output_parent,
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected, match="manifest SHA-256 mismatch"):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_native_full_rejects_input_drift_during_run(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    lock = Path(payload["native_runtime"]["requirements_lock"])
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
        on_run=lambda: lock.write_text("drifted\n", encoding="utf-8"),
    )

    with pytest.raises(gate_module.GateRejected, match="changed during run"):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


def test_subprocess_execution_runs_fixed_argv_without_shell(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    execution = gate_module.SubprocessExecution()
    command = gate_module.GateCommand(
        command_id="fixed-argv-probe",
        argv=(
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ),
        cwd=tmp_path,
        timeout_seconds=5,
        slots=1,
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
    )

    result = execution.run(command)

    assert result.returncode == 0
    assert result.stdout == b"out\n"
    assert result.stderr == b"err\n"
    assert result.finished_monotonic >= result.started_monotonic


def test_subprocess_execution_enforces_output_cap_and_kills_process_group(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    child_pid_path = tmp_path / "child.pid"
    program = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)']); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid)); "
        "sys.stdout.write('x' * 4096); sys.stdout.flush(); time.sleep(30)"
    )
    command = gate_module.GateCommand(
        command_id="output-cap-probe",
        argv=(sys.executable, "-c", program),
        cwd=tmp_path,
        timeout_seconds=2,
        slots=1,
        stdout_limit_bytes=64,
        stderr_limit_bytes=64,
    )
    started = time.monotonic()

    with pytest.raises(gate_module.ExecutionFailure, match="stdout exceeded"):
        gate_module.SubprocessExecution().run(command)

    assert time.monotonic() - started < 1.0
    child_pid = int(child_pid_path.read_text())
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        pytest.fail("output-cap child process survived process-group cleanup")


def test_subprocess_execution_converts_wait_timeout_and_reaps_group(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    parent_pid_path = tmp_path / "parent.pid"
    program = (
        "import os, pathlib, time; "
        f"pathlib.Path({str(parent_pid_path)!r}).write_text(str(os.getpid())); "
        "os.close(1); os.close(2); time.sleep(30)"
    )
    command = gate_module.GateCommand(
        command_id="wait-timeout-probe",
        argv=(sys.executable, "-c", program),
        cwd=tmp_path,
        timeout_seconds=0.1,
        slots=1,
    )

    with pytest.raises(gate_module.ExecutionFailure, match="exceeded"):
        gate_module.SubprocessExecution().run(command)

    parent_pid = int(parent_pid_path.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(parent_pid, 0)


def test_subprocess_execution_wraps_spawn_failure(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    command = gate_module.GateCommand(
        command_id="spawn-failure-probe",
        argv=(str(tmp_path / "does-not-exist"),),
        cwd=tmp_path,
        timeout_seconds=1,
        slots=1,
    )

    with pytest.raises(gate_module.ExecutionFailure, match="could not start"):
        gate_module.SubprocessExecution().run(command)


def test_subprocess_execution_reaps_group_when_selector_setup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_module = load_local_gate()
    parent_pid_path = tmp_path / "selector-parent.pid"
    program = (
        "import os, pathlib, time; "
        f"pathlib.Path({str(parent_pid_path)!r}).write_text(str(os.getpid())); "
        "time.sleep(30)"
    )
    command = gate_module.GateCommand(
        command_id="selector-setup-failure-probe",
        argv=(sys.executable, "-c", program),
        cwd=tmp_path,
        timeout_seconds=2,
        slots=1,
    )

    class BrokenSelector:
        def __init__(self) -> None:
            deadline = time.monotonic() + 1.0
            while not parent_pid_path.is_file() and time.monotonic() < deadline:
                time.sleep(0.01)
            raise OSError("scripted selector setup failure")

    monkeypatch.setattr(gate_module.selectors, "DefaultSelector", BrokenSelector)
    parent_pid: int | None = None
    try:
        with pytest.raises(
            gate_module.ExecutionFailure,
            match="execution infrastructure failed",
        ):
            gate_module.SubprocessExecution().run(command)
        parent_pid = int(parent_pid_path.read_text(encoding="utf-8"))
        with pytest.raises(ProcessLookupError):
            os.kill(parent_pid, 0)
    finally:
        if parent_pid is None and parent_pid_path.is_file():
            parent_pid = int(parent_pid_path.read_text(encoding="utf-8"))
        if parent_pid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.kill(parent_pid, signal.SIGKILL)


def test_native_full_wraps_execution_failure_and_removes_staging(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class TimedOutExecution:
        def run(self, command: Any) -> Any:
            raise gate_module.ExecutionFailure(
                f"{command.command_id} exceeded {command.timeout_seconds}s"
            )

    with pytest.raises(gate_module.GateRejected, match="native execution failed"):
        gate_module.LocalFullGate(TimedOutExecution()).run(request)

    assert_nothing_published(request.output_parent)


def test_native_full_wraps_unexpected_execution_error_and_removes_staging(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class BrokenExecution:
        def run(self, command: Any) -> Any:
            raise OSError(f"{command.command_id} transport broke")

    with pytest.raises(gate_module.GateRejected, match="native execution failed"):
        gate_module.LocalFullGate(BrokenExecution()).run(request)

    assert_nothing_published(request.output_parent)


def test_native_full_cli_is_the_standard_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate_module = load_local_gate()
    manifest_path, manifest_sha256, _ = write_prepared_inputs(tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=434.62,
    )

    exit_code = gate_module.main(
        [
            "native-full",
            "--prepared-inputs",
            str(manifest_path),
            "--prepared-inputs-sha256",
            manifest_sha256,
            "--output-parent",
            str(tmp_path / "output"),
        ],
        execution=execution,
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["profile"] == "native-full"
    assert output["elapsed_seconds"] == 434.62
    assert Path(output["profile_report"]).is_file()


def test_native_reports_are_independently_revalidated(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=434.62,
    )
    result = gate_module.LocalFullGate(execution).run(request)
    verifier = load_local_verifier()

    verified = verifier.validate_native_run(
        result.profile_report,
        result.local_summary,
        expected_prepared_inputs_sha256=request.prepared_inputs.sha256,
    )

    assert verified["profile"] == "native-full"
    assert verified["evidence_seal_elapsed_seconds"] == 434.62


def test_native_report_archives_prepared_inputs_for_later_verification(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    original_manifest = request.prepared_inputs.path.read_bytes()
    result = gate_module.LocalFullGate(
        ScriptedExecution(
            gate_module,
            stdout=complete_summary(),
            elapsed_seconds=434.62,
        )
    ).run(request)
    archived_manifest = result.profile_report.parent / "prepared-inputs.json"

    assert archived_manifest.read_bytes() == original_manifest
    request.prepared_inputs.path.write_text("{}\n", encoding="utf-8")
    verifier = load_local_verifier()

    verified = verifier.validate_native_run(
        result.profile_report,
        result.local_summary,
        expected_prepared_inputs_sha256=request.prepared_inputs.sha256,
    )

    assert verified["profile"] == "native-full"


def test_native_report_publishes_raw_bytes_and_cli_revalidates_them(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    stdout = complete_summary()
    execution = ScriptedExecution(
        gate_module,
        stdout=stdout,
        elapsed_seconds=434.62,
    )
    result = gate_module.LocalFullGate(execution).run(request)
    report = json.loads(result.profile_report.read_text(encoding="utf-8"))

    assert report["prepared_inputs_path"] == "prepared-inputs.json"
    assert report["command"]["slots"] == 10
    assert report["command"]["timeout_seconds"] <= 600
    assert report["command"]["shell"] is False
    for stream, expected in (("stdout", stdout.encode()), ("stderr", b"")):
        artifact = report["artifacts"][stream]
        artifact_path = result.profile_report.parent / artifact["path"]
        assert artifact_path.read_bytes() == expected
        assert artifact["size_bytes"] == len(expected)
        assert artifact["sha256"] == sha256_bytes(expected)

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNTIME_DIR / "verify_local_full.py"),
            "--help",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--profile-report" in completed.stdout
    verifier = load_local_verifier()
    exit_code = verifier.main(
        [
            "--profile-report",
            str(result.profile_report),
            "--local-summary",
            str(result.local_summary),
            "--prepared-inputs-sha256",
            request.prepared_inputs.sha256,
        ]
    )
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["profile"] == "native-full"


def test_native_verifier_rejects_raw_stdout_tampering(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    result = gate_module.LocalFullGate(
        ScriptedExecution(
            gate_module,
            stdout=complete_summary(),
            elapsed_seconds=434.62,
        )
    ).run(request)
    report = json.loads(result.profile_report.read_text(encoding="utf-8"))
    stdout_path = result.profile_report.parent / report["artifacts"]["stdout"]["path"]
    stdout_path.write_text("forged pass\n", encoding="utf-8")
    verifier = load_local_verifier()

    with pytest.raises(verifier.LocalVerificationError):
        verifier.validate_native_run(
            result.profile_report,
            result.local_summary,
            expected_prepared_inputs_sha256=request.prepared_inputs.sha256,
        )


def test_native_verifier_rejects_self_consistent_command_forgery(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    result = gate_module.LocalFullGate(
        ScriptedExecution(
            gate_module,
            stdout=complete_summary(),
            elapsed_seconds=434.62,
        )
    ).run(request)
    report = json.loads(result.profile_report.read_text(encoding="utf-8"))
    report["command"]["argv"][-1] = "/tmp/forged-research"
    report_raw = (
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    result.profile_report.write_bytes(report_raw)
    envelope = json.loads(result.local_summary.read_text(encoding="utf-8"))
    envelope["profile_report_sha256"] = sha256_bytes(report_raw)
    result.local_summary.write_text(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    verifier = load_local_verifier()

    with pytest.raises(verifier.LocalVerificationError, match="command"):
        verifier.validate_native_run(
            result.profile_report,
            result.local_summary,
            expected_prepared_inputs_sha256=request.prepared_inputs.sha256,
        )


def test_native_full_verifies_staging_before_atomic_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    verifier = gate_module.verify_local_full

    def reject(*args: object, **kwargs: object) -> object:
        raise verifier.LocalVerificationError("scripted verifier rejection")

    monkeypatch.setattr(verifier, "validate_native_run", reject)

    with pytest.raises(gate_module.GateRejected, match="independent verification"):
        gate_module.LocalFullGate(
            ScriptedExecution(
                gate_module,
                stdout=complete_summary(),
                elapsed_seconds=434.62,
            )
        ).run(request)

    assert_nothing_published(request.output_parent)


def test_native_full_rejects_total_profile_wall_clock_over_budget(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class FakeMonotonic:
        def __init__(self) -> None:
            self.values = [0.0, 0.0, 601.0]
            self.index = 0

        def __call__(self) -> float:
            value = self.values[min(self.index, len(self.values) - 1)]
            self.index += 1
            return value

    with pytest.raises(gate_module.GateRejected, match="profile.*deadline"):
        gate_module.LocalFullGate(
            ScriptedExecution(
                gate_module,
                stdout=complete_summary(elapsed_seconds=1.0),
                elapsed_seconds=1.0,
            ),
            monotonic=FakeMonotonic(),
        ).run(request)

    assert_nothing_published(request.output_parent)


def test_native_report_records_explicit_pre_seal_elapsed_boundary(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class FakeMonotonic:
        def __init__(self) -> None:
            self.values = [0.0, 0.0, 2.0, 5.0, 5.0, 5.0, 5.0]
            self.index = 0

        def __call__(self) -> float:
            value = self.values[min(self.index, len(self.values) - 1)]
            self.index += 1
            return value

    result = gate_module.LocalFullGate(
        ScriptedExecution(
            gate_module,
            stdout=complete_summary(elapsed_seconds=1.0),
            elapsed_seconds=1.0,
        ),
        monotonic=FakeMonotonic(),
    ).run(request)
    report = json.loads(result.profile_report.read_text(encoding="utf-8"))
    envelope = json.loads(result.local_summary.read_text(encoding="utf-8"))

    assert result.elapsed_seconds == 5.0
    assert "profile_elapsed_seconds" not in report
    assert envelope["evidence_seal_elapsed_seconds"] == 5.0
    assert envelope["measurement_boundary"] == (
        "post-semantic-verification-pre-evidence-seal"
    )
    assert envelope["deadline_enforced_through_atomic_publication"] is True
    assert "elapsed_seconds" not in envelope


def test_native_profile_elapsed_includes_final_verifier_and_publication_check(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class FakeMonotonic:
        def __init__(self) -> None:
            self.values = [0.0, 0.0, 2.0, 5.0, 8.0, 8.0, 8.0]
            self.index = 0

        def __call__(self) -> float:
            value = self.values[min(self.index, len(self.values) - 1)]
            self.index += 1
            return value

    result = gate_module.LocalFullGate(
        ScriptedExecution(
            gate_module,
            stdout=complete_summary(elapsed_seconds=1.0),
            elapsed_seconds=1.0,
        ),
        monotonic=FakeMonotonic(),
    ).run(request)
    report = json.loads(result.profile_report.read_text(encoding="utf-8"))
    envelope = json.loads(result.local_summary.read_text(encoding="utf-8"))

    assert result.elapsed_seconds == 8.0
    assert envelope["evidence_seal_elapsed_seconds"] == 5.0
    assert envelope["measurement_boundary"] == (
        "post-semantic-verification-pre-evidence-seal"
    )
    assert envelope["deadline_enforced_through_atomic_publication"] is True
    assert "profile_elapsed_seconds" not in report
    assert "elapsed_seconds" not in envelope


def test_native_publication_deadline_failure_removes_published_bundle(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class FakeMonotonic:
        def __init__(self) -> None:
            self.values = [0.0, 0.0, 2.0, 5.0, 5.0, 601.0]
            self.index = 0

        def __call__(self) -> float:
            value = self.values[min(self.index, len(self.values) - 1)]
            self.index += 1
            return value

    with pytest.raises(gate_module.GateRejected, match="profile.*deadline"):
        gate_module.LocalFullGate(
            ScriptedExecution(
                gate_module,
                stdout=complete_summary(elapsed_seconds=1.0),
                elapsed_seconds=1.0,
            ),
            monotonic=FakeMonotonic(),
        ).run(request)

    assert_nothing_published(request.output_parent)


@pytest.mark.parametrize("tree_name", ["source", "research", "native_runtime"])
def test_prepared_inputs_rejects_unbound_tree_bytes(
    tmp_path: Path,
    tree_name: str,
) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    root = Path(payload[tree_name]["root"])
    (root / "unbound.bin").write_bytes(b"not in prepared closure")
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(elapsed_seconds=1.0),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected, match="tree SHA-256 mismatch"):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_prepared_inputs_rejects_release_manifest_bytes_mismatch(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    Path(payload["source"]["release_manifest"]).write_text(
        "forged manifest\n", encoding="utf-8"
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(elapsed_seconds=1.0),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected, match="release manifest"):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_prepared_inputs_accepts_external_signed_release_manifest(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_prepared_inputs(tmp_path)
    source_manifest = Path(payload["source"]["release_manifest"])
    external_manifest = tmp_path / "external-release-manifest.json"
    shutil.copy2(source_manifest, external_manifest)
    source_root = Path(payload["source"]["root"])
    subprocess.run(
        ["git", "-C", str(source_root), "rm", "-q", str(source_manifest)],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--amend",
            "--no-edit",
            "-q",
        ],
        check=True,
    )
    source_commit = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
    ).strip()
    gate_module.prepared_inputs.EXPECTED_COMMIT = source_commit
    payload["source"]["commit"] = source_commit
    payload["research"]["commit"] = source_commit
    payload["source"]["tree_sha256"] = tree_sha256(source_root)
    payload["source"]["release_manifest"] = str(external_manifest)
    for binding in payload["bindings"]:
        if binding["path"] == str(source_manifest):
            binding["path"] = str(external_manifest)
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)

    loaded = gate_module.prepared_inputs.load(manifest_path, sha256_bytes(raw))

    assert loaded.source_root == source_root


@pytest.mark.parametrize(
    "required_path",
    [
        lambda payload: (
            Path(payload["source"]["root"]) / "scripts" / "run_test_suite.py"
        ),
        lambda payload: Path(payload["native_runtime"]["requirements_lock"]),
        lambda payload: Path(payload["source"]["release_manifest"]),
        lambda payload: Path(payload["native_runtime"]["runtime_integrity"]),
    ],
)
def test_prepared_inputs_requires_every_native_binding_once(
    tmp_path: Path,
    required_path: Callable[[dict[str, Any]], Path],
) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_prepared_inputs(tmp_path)
    missing = str(required_path(payload))
    payload["bindings"] = [
        binding for binding in payload["bindings"] if binding["path"] != missing
    ]
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)

    with pytest.raises(
        gate_module.prepared_inputs.PreparedInputsError,
        match="required binding",
    ):
        gate_module.prepared_inputs.load(manifest_path, sha256_bytes(raw))


def test_prepared_inputs_rejects_duplicate_binding_paths(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_prepared_inputs(tmp_path)
    payload["bindings"].append(copy.deepcopy(payload["bindings"][0]))
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)

    with pytest.raises(
        gate_module.prepared_inputs.PreparedInputsError,
        match="duplicate binding",
    ):
        gate_module.prepared_inputs.load(manifest_path, sha256_bytes(raw))


def test_prepared_inputs_verifies_real_source_git_head(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    source_root = payload["source"]["root"]
    subprocess.run(
        [
            "git",
            "-C",
            source_root,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "drifted head",
        ],
        check=True,
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(elapsed_seconds=1.0),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected, match="source Git HEAD mismatch"):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_native_full_rejects_unbound_research_drift_during_run(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    research_file = Path(payload["research"]["root"]) / "book.txt"
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(elapsed_seconds=1.0),
        elapsed_seconds=1.0,
        on_run=lambda: research_file.write_text("drifted\n", encoding="utf-8"),
    )

    with pytest.raises(gate_module.GateRejected, match="changed during run"):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


def test_prepared_inputs_requires_external_research_root(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_prepared_inputs(tmp_path)
    payload["research"]["root"] = payload["source"]["root"]
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)
    request = gate_module.LocalFullRequest(
        profile="native-full",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=sha256_bytes(raw),
        ),
        output_parent=tmp_path / "output",
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(
        gate_module.GateRejected, match="research root must be external"
    ):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []


def test_prepared_inputs_rejects_fulltext_inside_source_projection(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    fulltext = Path(payload["source"]["root"]) / "references" / "fulltext"
    fulltext.mkdir(parents=True)
    (fulltext / "book.md").write_text("external research bytes\n", encoding="utf-8")
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(
        gate_module.GateRejected, match="source projection contains fulltext"
    ):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []


def test_vz_profile_fills_to_pinned_mountless_rosetta_contract() -> None:
    assert VZ_PROFILE_PATH.is_file(), "VZ+Rosetta profile is absent"
    validate = subprocess.run(
        ["limactl", "template", "validate", "--fill", str(VZ_PROFILE_PATH)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert validate.returncode == 0, validate.stderr
    filled = subprocess.run(
        ["limactl", "template", "copy", "--fill", str(VZ_PROFILE_PATH), "-"],
        capture_output=True,
        check=False,
        text=True,
    )
    assert filled.returncode == 0, filled.stderr
    profile = yaml.safe_load(filled.stdout)

    assert profile["minimumLimaVersion"] == "2.2.0"
    assert profile["vmType"] == "vz"
    assert profile["arch"] == "aarch64"
    assert profile["cpus"] == 10
    assert profile["memory"] == "10GiB"
    assert profile.get("mounts", []) == []
    assert "base" not in profile
    assert profile["vmOpts"]["vz"]["rosetta"] == {
        "enabled": True,
        "binfmt": True,
    }
    assert profile["images"] == [EXPECTED_VZ_IMAGE]
    provision = "\n".join(
        str(item.get("script", "")) for item in profile.get("provision", [])
    )
    assert "get.docker.com" not in provision
    for version in (
        "docker-ce=5:29.7.2-1~ubuntu.26.04~resolute",
        "docker-ce-cli=5:29.7.2-1~ubuntu.26.04~resolute",
        "docker-ce-rootless-extras=5:29.7.2-1~ubuntu.26.04~resolute",
        "containerd.io=2.3.3-1~ubuntu.26.04~resolute",
        "docker-buildx-plugin=0.36.1-1~ubuntu.26.04~resolute",
        "docker-compose-plugin=5.4.0-1~ubuntu.26.04~resolute",
    ):
        assert version in provision


def test_formal_linux_preparation_requires_persisted_build_provenance() -> None:
    preparer = load_linux_preparer()

    assert preparer.PREPARATION_SCHEMA == "mingli-linux-preparation-v1"
    assert set(preparer.CONTROLLER_INPUT_PATHS) >= {
        "infra/mingli-runtime/Dockerfile",
        "infra/mingli-runtime/audit_runtime.py",
        "infra/mingli-runtime/local_gate.py",
        "infra/mingli-runtime/verify_release.py",
        "infra/mingli-runtime/verify_local_full.py",
        "infra/mingli-runtime/run_lima_gate.py",
        "infra/mingli-runtime/prepare_linux_inputs.py",
    }
    assert preparer.BUILD_CONTEXT_ARCHIVE_NAME == "build-context.tar"
    assert preparer.PREPARATION_RECORD_NAME == "linux-preparation.json"


def test_identity_only_linux_inputs_cannot_enter_formal_release_gate(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    manifest_path, manifest_sha256, _ = write_linux_prepared_inputs(tmp_path)
    loaded = gate_module.prepared_inputs.load(manifest_path, manifest_sha256)

    with pytest.raises(
        gate_module.prepared_inputs.PreparedInputsError,
        match="preparation provenance",
    ):
        gate_module.prepared_inputs.require_certifiable_linux(loaded)


def test_linux_runtime_inputs_require_actual_lima_version(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_linux_prepared_inputs(tmp_path)
    payload["linux_runtime"].pop("lima_version")
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)
    manifest_sha256 = sha256_bytes(raw)
    loaded = gate_module.prepared_inputs.load(manifest_path, manifest_sha256)

    with pytest.raises(
        gate_module.prepared_inputs.PreparedInputsError,
        match="Lima version",
    ):
        gate_module.prepared_inputs.require_linux(loaded)


def test_run_lima_gate_rejects_identity_only_prepared_inputs(
    tmp_path: Path,
) -> None:
    controller = load_lima_controller()
    manifest_path, manifest_sha256, _ = write_linux_prepared_inputs(tmp_path)
    args = SimpleNamespace(
        prepared_inputs=manifest_path,
        prepared_inputs_sha256=manifest_sha256,
        release_source=None,
        research_repository=None,
        instance=None,
    )

    with pytest.raises(controller.GateError, match="preparation provenance"):
        controller._resolve_gate_inputs(args)


def test_formal_linux_inputs_recompute_controller_and_build_context(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    manifest_path, manifest_sha256, payload = write_formal_linux_prepared_inputs(
        tmp_path, gate_module
    )

    loaded = gate_module.prepared_inputs.load(manifest_path, manifest_sha256)
    linux = gate_module.prepared_inputs.require_certifiable_linux(loaded)

    assert linux.index_digest == payload["linux_runtime"]["oci"]["index_digest"]
    assert (
        linux.controller_commit
        == payload["linux_runtime"]["preparation"]["controller_commit"]
    )
    assert (
        linux.build_context_tree_sha256
        == payload["linux_runtime"]["preparation"]["build_context_tree_sha256"]
    )


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("controller_commit", "controller Git HEAD mismatch"),
        ("context_tree", "build-context tree SHA-256 mismatch"),
        ("image_index", "OCI outer index digest mismatch"),
    ],
)
def test_formal_linux_inputs_reject_consistently_resealed_false_provenance(
    tmp_path: Path,
    mutation: str,
    error: str,
) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_formal_linux_prepared_inputs(
        tmp_path, gate_module
    )
    preparation = payload["linux_runtime"]["preparation"]
    record_path = Path(preparation["record"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if mutation == "controller_commit":
        record["controller"]["commit"] = "0" * 40
        preparation["controller_commit"] = "0" * 40
    elif mutation == "context_tree":
        record["build_context"]["tree_sha256"] = "0" * 64
        preparation["build_context_tree_sha256"] = "0" * 64
    elif mutation == "image_index":
        false_index = "sha256:" + "0" * 64
        payload["linux_runtime"]["oci"]["index_digest"] = false_index
        payload["linux_runtime"]["immutable_image_ref"] = (
            f"{payload['linux_runtime']['image_repository']}@{false_index}"
        )
        record["image"]["oci"]["index_digest"] = false_index
        record["image"]["immutable_image_ref"] = payload["linux_runtime"][
            "immutable_image_ref"
        ]
    else:  # pragma: no cover - exhaustive parametrization guard
        raise AssertionError(mutation)
    manifest_sha256 = reseal_linux_preparation(manifest_path, payload, record)
    loaded = gate_module.prepared_inputs.load(manifest_path, manifest_sha256)

    with pytest.raises(gate_module.prepared_inputs.PreparedInputsError, match=error):
        gate_module.prepared_inputs.require_certifiable_linux(loaded)


def test_formal_linux_inputs_reject_resealed_dirty_controller_file(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_formal_linux_prepared_inputs(
        tmp_path, gate_module
    )
    preparation = payload["linux_runtime"]["preparation"]
    record_path = Path(preparation["record"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    controller_root = Path(record["controller"]["repository_root"])
    relative = "infra/mingli-runtime/local_gate.py"
    controller_file = controller_root / relative
    controller_file.write_text("synchronized malicious rewrite\n", encoding="utf-8")
    false_sha256 = sha256_file(controller_file)
    record["controller"]["input_sha256"][relative] = false_sha256
    for binding in payload["bindings"]:
        if binding["path"] == str(controller_file):
            binding["sha256"] = false_sha256
    manifest_sha256 = reseal_linux_preparation(manifest_path, payload, record)
    loaded = gate_module.prepared_inputs.load(manifest_path, manifest_sha256)

    with pytest.raises(
        gate_module.prepared_inputs.PreparedInputsError,
        match="controller Git tracked worktree is not clean",
    ):
        gate_module.prepared_inputs.require_certifiable_linux(loaded)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("lima_command", "preparation command contract mismatch"),
        ("build", "preparation command contract mismatch"),
        ("export", "preparation command contract mismatch"),
        ("instance", "preparation runtime identity mismatch"),
        ("effective_config", "preparation runtime identity mismatch"),
        ("lima_version", "Lima version drift"),
        ("docker", "preparation runtime identity mismatch"),
    ],
)
def test_formal_linux_inputs_reject_resealed_command_and_runtime_drift(
    tmp_path: Path,
    mutation: str,
    error: str,
) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_formal_linux_prepared_inputs(
        tmp_path, gate_module
    )
    preparation = payload["linux_runtime"]["preparation"]
    record = json.loads(Path(preparation["record"]).read_text(encoding="utf-8"))
    if mutation == "lima_command":
        record["commands"]["lima_version"] = ["limactl", "version"]
    elif mutation == "build":
        record["commands"]["build"].insert(2, "--pull")
    elif mutation == "export":
        record["commands"]["export"].extend(["--platform", "linux/amd64"])
    elif mutation == "instance":
        record["runtime"]["instance"] = "drifted-instance"
    elif mutation == "effective_config":
        record["runtime"]["effective_config_sha256"] = "0" * 64
    elif mutation == "lima_version":
        payload["linux_runtime"]["lima_version"] = "2.2.1"
        record["runtime"]["lima_version"] = "2.2.1"
    elif mutation == "docker":
        record["runtime"]["docker"]["server_version"] = "0.0.0"
    else:  # pragma: no cover - exhaustive parametrization guard
        raise AssertionError(mutation)
    manifest_sha256 = reseal_linux_preparation(manifest_path, payload, record)
    loaded = gate_module.prepared_inputs.load(manifest_path, manifest_sha256)

    with pytest.raises(gate_module.prepared_inputs.PreparedInputsError, match=error):
        gate_module.prepared_inputs.require_certifiable_linux(loaded)


def make_linux_preparer_case(
    tmp_path: Path,
    preparer: ModuleType,
) -> SimpleNamespace:
    base_manifest, base_sha256, base_payload = write_prepared_inputs(tmp_path / "base")
    controller_root, controller_commit = write_controller_repository(
        tmp_path / "control", preparer
    )
    effective_config = tmp_path / "effective-vz.yaml"
    effective_config.write_text("vmType: vz\narch: aarch64\n", encoding="utf-8")

    def project_context(
        _release_source: Path,
        destination: Path,
        *,
        infra_root: Path,
    ) -> Path:
        destination.mkdir()
        release = destination / "release"
        release.mkdir()
        (release / "fixture.txt").write_text(
            "signed projection fixture\n", encoding="utf-8"
        )
        for name in preparer.BUILD_CONTEXT_INPUT_NAMES:
            shutil.copy2(infra_root / name, destination / name)
        (destination / "context-provenance.json").write_text(
            '{"schema":"fixture"}\n', encoding="utf-8"
        )
        return destination

    request = preparer.PrepareRequest(
        base_prepared_inputs=base_manifest,
        base_prepared_inputs_sha256=base_sha256,
        controller_root=controller_root,
        release_source=Path(base_payload["source"]["root"]),
        effective_config=effective_config,
        effective_config_sha256=sha256_file(effective_config),
        instance="mingli-linux-gate-vz",
        output_directory=tmp_path / "prepared-linux",
    )
    return SimpleNamespace(
        base_manifest=base_manifest,
        base_sha256=base_sha256,
        controller_commit=controller_commit,
        controller_root=controller_root,
        project_context=project_context,
        request=request,
    )


class FakeLinuxImageBuilder:
    def __init__(
        self,
        *,
        before_build: Callable[[], None] | None = None,
        failure: BaseException | None = None,
    ) -> None:
        self.before_build = before_build
        self.failure = failure
        self.observed_context_sha256: str | None = None

    def build_and_export(
        self,
        *,
        context_tar: bytes,
        image_ref: str,
        destination: Path,
    ) -> Any:
        if self.before_build is not None:
            self.before_build()
        if self.failure is not None:
            raise self.failure
        self.observed_context_sha256 = sha256_bytes(context_tar)
        oci = write_oci_archive(
            destination,
            image_ref,
            build_context_sha256=self.observed_context_sha256,
        )
        return SimpleNamespace(
            index_digest=oci["index_digest"],
            lima_version="2.2.0",
            docker={
                "client_version": "29.7.2",
                "server_version": "29.7.2",
                "server_arch": "arm64",
                "containerd_version": "v2.3.3",
                "rootlesskit_version": "3.0.2",
            },
        )


def test_linux_preparer_builds_from_the_persisted_post_commit_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_module = load_local_gate()
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    final_manifest = case.request.output_directory / preparer.PREPARED_INPUTS_NAME
    builder = FakeLinuxImageBuilder(
        before_build=lambda: assert_path_absent(final_manifest)
    )
    original_validator = preparer.prepared_inputs.require_certifiable_linux

    def validate_before_admission(inputs: Any) -> Any:
        assert not final_manifest.exists()
        assert case.request.output_directory.is_dir()
        return original_validator(inputs)

    monkeypatch.setattr(
        preparer.prepared_inputs,
        "require_certifiable_linux",
        validate_before_admission,
    )

    result = preparer.prepare(
        case.request,
        builder=builder,
        context_builder=case.project_context,
    )

    assert result.controller_commit == case.controller_commit
    assert result.prepared_inputs.is_file()
    loaded = gate_module.prepared_inputs.load(
        result.prepared_inputs, result.prepared_inputs_sha256
    )
    linux = original_validator(loaded)
    assert linux.controller_commit == case.controller_commit
    assert sha256_file(result.build_context_archive) == (
        builder.observed_context_sha256
    )
    assert result.index_digest == linux.index_digest
    assert result.lima_version == "2.2.0"
    assert not (
        result.output_directory / preparer.PENDING_PREPARED_INPUTS_NAME
    ).exists()
    assert not (result.output_directory / "release-5.1.json").exists()


def test_linux_preparer_reads_the_exact_lima_version_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparer = load_linux_preparer()
    observed: list[list[str]] = []

    def exact_version(argv: list[str], **kwargs: Any) -> Any:
        del kwargs
        observed.append(argv)
        return subprocess.CompletedProcess(
            argv,
            0,
            b"limactl version 2.2.0\n",
            b"",
        )

    monkeypatch.setattr(preparer.subprocess, "run", exact_version)

    assert preparer.LimaImageBuilder._lima_version() == "2.2.0"
    assert observed == [["limactl", "--version"]]

    def drifted_version(argv: list[str], **kwargs: Any) -> Any:
        del kwargs
        return subprocess.CompletedProcess(
            argv,
            0,
            b"limactl version 2.2.1\n",
            b"",
        )

    monkeypatch.setattr(preparer.subprocess, "run", drifted_version)
    with pytest.raises(preparer.PreparationError, match="Lima version drift"):
        preparer.LimaImageBuilder._lima_version()


def assert_path_absent(path: Path) -> None:
    assert not path.exists()


def test_linux_preparer_rejects_existing_output_before_builder(
    tmp_path: Path,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    case.request.output_directory.mkdir()
    builder = FakeLinuxImageBuilder(
        before_build=lambda: pytest.fail("builder must not run")
    )

    with pytest.raises(
        preparer.PreparationError,
        match="must not already exist",
    ):
        preparer.prepare(
            case.request,
            builder=builder,
            context_builder=case.project_context,
        )


def test_linux_preparer_builder_failure_leaves_no_output(
    tmp_path: Path,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)

    with pytest.raises(RuntimeError, match="scripted builder failure"):
        preparer.prepare(
            case.request,
            builder=FakeLinuxImageBuilder(
                failure=RuntimeError("scripted builder failure")
            ),
            context_builder=case.project_context,
        )

    assert not case.request.output_directory.exists()


def test_linux_preparer_validation_failure_never_publishes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    final_manifest = case.request.output_directory / preparer.PREPARED_INPUTS_NAME

    def reject(_inputs: Any) -> Any:
        assert not final_manifest.exists()
        raise preparer.prepared_inputs.PreparedInputsError(
            "scripted independent validation failure"
        )

    monkeypatch.setattr(
        preparer.prepared_inputs,
        "require_certifiable_linux",
        reject,
    )

    with pytest.raises(
        preparer.PreparationError,
        match="independent validation failure",
    ):
        preparer.prepare(
            case.request,
            builder=FakeLinuxImageBuilder(),
            context_builder=case.project_context,
        )

    assert not final_manifest.exists()
    assert not case.request.output_directory.exists()


def test_linux_preparer_base_exception_before_admission_removes_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    final_manifest = case.request.output_directory / preparer.PREPARED_INPUTS_NAME

    def interrupt(_inputs: Any) -> Any:
        assert case.request.output_directory.is_dir()
        assert not final_manifest.exists()
        raise KeyboardInterrupt("scripted interruption")

    monkeypatch.setattr(
        preparer.prepared_inputs,
        "require_certifiable_linux",
        interrupt,
    )

    with pytest.raises(KeyboardInterrupt, match="scripted interruption"):
        preparer.prepare(
            case.request,
            builder=FakeLinuxImageBuilder(),
            context_builder=case.project_context,
        )

    assert not final_manifest.exists()
    assert not case.request.output_directory.exists()


def test_linux_preparer_manifest_is_the_final_atomic_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    final_manifest = case.request.output_directory / preparer.PREPARED_INPUTS_NAME
    real_replace = preparer.os.replace
    manifest_publications = 0

    def observed_replace(source: Any, destination: Any) -> None:
        nonlocal manifest_publications
        destination_path = Path(destination)
        if destination_path == final_manifest:
            manifest_publications += 1
            assert case.request.output_directory.is_dir()
            assert not final_manifest.exists()
            assert Path(source).name.startswith(".")
            for name in (
                preparer.BUILD_CONTEXT_ARCHIVE_NAME,
                preparer.OCI_ARCHIVE_NAME,
                preparer.PREPARATION_RECORD_NAME,
                "lima-effective.yaml",
            ):
                assert (case.request.output_directory / name).is_file()
        real_replace(source, destination)

    monkeypatch.setattr(preparer.os, "replace", observed_replace)

    result = preparer.prepare(
        case.request,
        builder=FakeLinuxImageBuilder(),
        context_builder=case.project_context,
    )

    assert manifest_publications == 1
    assert result.prepared_inputs == final_manifest
    assert final_manifest.is_file()


def test_linux_preparer_revalidates_base_and_controller_before_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    controller_checks = 0
    real_controller_identity = preparer._controller_identity

    def observed_controller_identity(root: Path) -> tuple[str, dict[str, str]]:
        nonlocal controller_checks
        controller_checks += 1
        return real_controller_identity(root)

    monkeypatch.setattr(
        preparer,
        "_controller_identity",
        observed_controller_identity,
    )

    def mutate_base_manifest() -> None:
        case.base_manifest.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        preparer.PreparationError,
        match="PreparedInputs changed during Linux preparation",
    ):
        preparer.prepare(
            case.request,
            builder=FakeLinuxImageBuilder(before_build=mutate_base_manifest),
            context_builder=case.project_context,
        )

    assert controller_checks >= 2
    assert not case.request.output_directory.exists()


def test_linux_preparer_revalidates_effective_config_before_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preparer = load_linux_preparer()
    case = make_linux_preparer_case(tmp_path, preparer)
    real_validator = preparer.prepared_inputs.require_certifiable_linux

    def mutate_after_independent_validation(inputs: Any) -> Any:
        result = real_validator(inputs)
        case.request.effective_config.write_text(
            "vmType: qemu\narch: aarch64\n", encoding="utf-8"
        )
        return result

    monkeypatch.setattr(
        preparer.prepared_inputs,
        "require_certifiable_linux",
        mutate_after_independent_validation,
    )

    with pytest.raises(
        preparer.PreparationError,
        match="effective Lima config changed",
    ):
        preparer.prepare(
            case.request,
            builder=FakeLinuxImageBuilder(),
            context_builder=case.project_context,
        )

    assert not case.request.output_directory.exists()


def test_linux_certify_first_stage_accepts_only_exact_amd64_identity(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    manifest_path, manifest_sha256, payload = write_linux_prepared_inputs(tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=json.dumps(complete_linux_identity(payload), sort_keys=True) + "\n",
        elapsed_seconds=3.5,
    )
    request = gate_module.LocalFullRequest(
        profile="linux-certify",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=manifest_sha256,
        ),
        output_parent=tmp_path / "output",
        deadline_seconds=60,
        slots=1,
    )

    result = gate_module.LocalFullGate(execution).run(request)

    assert result.profile == "linux-certify"
    assert result.profile_report.name == "linux-identity-tracer.json"
    assert result.profile_report.is_file()
    assert not (result.profile_report.parent / "release-5.1.json").exists()
    assert result.timeline[0].command_id == "linux-amd64-identity-tracer"
    command = execution.commands[0]
    lima_version_index = command.argv.index("--lima-version")
    assert command.argv[lima_version_index + 1] == "2.2.0"


def test_linux_identity_timeout_reaps_the_whole_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity_module = load_linux_identity()
    child_pid_path = tmp_path / "identity-child.pid"
    program = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)'], stdin=subprocess.DEVNULL, "
        "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid)); "
        "time.sleep(30)"
    )
    monkeypatch.setattr(identity_module, "COMMAND_TIMEOUT_SECONDS", 0.1)
    child_pid: int | None = None

    try:
        with pytest.raises(identity_module.IdentityError, match="timed out"):
            identity_module.SubprocessRunner().run((sys.executable, "-c", program))
        child_pid = int(child_pid_path.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            pytest.fail("Linux identity child survived timeout process-group cleanup")
    finally:
        if child_pid is None and child_pid_path.is_file():
            child_pid = int(child_pid_path.read_text(encoding="utf-8"))
        if child_pid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.kill(child_pid, 9)


def test_linux_identity_input_rejection_removes_staging(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_linux_prepared_inputs(tmp_path)
    payload["linux_runtime"]["docker"]["server_version"] = "drifted"
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)
    request = gate_module.LocalFullRequest(
        profile="linux-certify",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=sha256_bytes(raw),
        ),
        output_parent=tmp_path / "output",
        deadline_seconds=60,
        slots=1,
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=json.dumps(complete_linux_identity(payload), sort_keys=True) + "\n",
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected, match="Docker identity drift"):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["instance"].__setitem__("vm_type", "qemu"),
        lambda value: value["instance"].__setitem__("rosetta_binfmt", False),
        lambda value: value.__setitem__("lima_version", "2.2.1"),
        lambda value: value["docker"].__setitem__("server_arch", "amd64"),
        lambda value: value["image"].__setitem__("index_digest", "sha256:" + "0" * 64),
        lambda value: value["image"].__setitem__(
            "platform_manifest_digest", "sha256:" + "0" * 64
        ),
        lambda value: value["image"].__setitem__("config_digest", "sha256:" + "0" * 64),
        lambda value: value["image"].__setitem__(
            "attestation_manifest_digest", "sha256:" + "0" * 64
        ),
        lambda value: value["image"].__setitem__("layer_digests", []),
        lambda value: value["image"].__setitem__("rootfs_diff_ids", []),
        lambda value: value["image"]["docker"].__setitem__("id", "sha256:" + "0" * 64),
        lambda value: value["image"]["docker"].__setitem__("architecture", "arm64"),
        lambda value: value["container"].__setitem__("platform_machine", "aarch64"),
        lambda value: value["container"].__setitem__("uname_machine", "aarch64"),
        lambda value: value["container"]["elf_machine"].__setitem__("sxtwl", 183),
        lambda value: value["container"].__setitem__("sxtwl_smoke", []),
        lambda value: value["container"].__setitem__("node_ldd_libraries", []),
        lambda value: value["container"].__setitem__("sxtwl_ldd_libraries", []),
    ],
)
def test_linux_identity_mutations_fail_closed(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    gate_module = load_local_gate()
    manifest_path, manifest_sha256, payload = write_linux_prepared_inputs(tmp_path)
    identity = copy.deepcopy(complete_linux_identity(payload))
    mutation(identity)
    execution = ScriptedExecution(
        gate_module,
        stdout=json.dumps(identity, sort_keys=True) + "\n",
        elapsed_seconds=1.0,
    )
    request = gate_module.LocalFullRequest(
        profile="linux-certify",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=manifest_sha256,
        ),
        output_parent=tmp_path / "output",
        deadline_seconds=60,
        slots=1,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


def test_linux_identity_collector_uses_exact_rosetta_container_boundary(
    tmp_path: Path,
) -> None:
    identity_module = load_linux_identity()
    _, _, payload = write_linux_prepared_inputs(tmp_path)
    effective_config = tmp_path / "effective.yaml"
    effective_config.write_text("vmType: vz\narch: aarch64\n", encoding="utf-8")
    instance_payload = complete_lima_instance()
    docker_payload = {
        "Client": {"Version": "29.7.2"},
        "Server": {
            "Version": "29.7.2",
            "Arch": "arm64",
            "Components": [
                {"Name": "containerd", "Version": "v2.3.3"},
                {"Name": "rootlesskit", "Version": "3.0.2"},
            ],
        },
    }
    container_payload = complete_linux_identity(payload)["container"]

    class ScriptedHostRunner:
        def __init__(self) -> None:
            self.commands: list[tuple[str, ...]] = []
            self.outputs = [
                b"limactl version 2.2.0\n",
                (json.dumps(instance_payload) + "\n").encode(),
                (json.dumps(docker_payload) + "\n").encode(),
                (json.dumps(docker_image_payload(payload)) + "\n").encode(),
                (json.dumps(container_payload) + "\n").encode(),
                b"limactl version 2.2.0\n",
            ]

        def run(self, argv: tuple[str, ...]) -> bytes:
            self.commands.append(argv)
            return self.outputs.pop(0)

    runner = ScriptedHostRunner()

    identity = identity_module.collect_identity(
        instance="mingli-linux-gate-vz",
        image_ref=payload["linux_runtime"]["image_ref"],
        immutable_image_ref=payload["linux_runtime"]["immutable_image_ref"],
        oci_archive=Path(payload["linux_runtime"]["oci_archive"]),
        expected_oci_archive_sha256=payload["linux_runtime"]["oci_archive_sha256"],
        expected_oci=payload["linux_runtime"]["oci"],
        effective_config=effective_config,
        expected_effective_config_sha256=sha256_file(effective_config),
        expected_lima_version="2.2.0",
        runner=runner,
    )

    assert identity == complete_linux_identity(payload)
    assert runner.outputs == []
    assert runner.commands[0] == ("limactl", "--version")
    assert runner.commands[-1] == ("limactl", "--version")
    container_argv = runner.commands[-2]
    assert "--platform=linux/amd64" in container_argv
    assert "--device=lima-vm.io/rosetta=cached" in container_argv
    assert "--network=none" in container_argv
    label_index = container_argv.index("--label")
    assert (
        container_argv[label_index + 1]
        == "io.fateradar.mingli.gate=linux-amd64-identity-tracer"
    )
    assert "--entrypoint" in container_argv
    assert "/opt/mingli-runtime/venv/bin/python" in container_argv
    assert payload["linux_runtime"]["immutable_image_ref"] in container_argv
    assert payload["linux_runtime"]["image_ref"] not in container_argv

    drifted_runner = ScriptedHostRunner()
    drifted_runner.outputs[-1] = b"limactl version 2.2.1\n"
    with pytest.raises(identity_module.IdentityError, match="Lima version"):
        identity_module.collect_identity(
            instance="mingli-linux-gate-vz",
            image_ref=payload["linux_runtime"]["image_ref"],
            immutable_image_ref=payload["linux_runtime"]["immutable_image_ref"],
            oci_archive=Path(payload["linux_runtime"]["oci_archive"]),
            expected_oci_archive_sha256=payload["linux_runtime"]["oci_archive_sha256"],
            expected_oci=payload["linux_runtime"]["oci"],
            effective_config=effective_config,
            expected_effective_config_sha256=sha256_file(effective_config),
            expected_lima_version="2.2.0",
            runner=drifted_runner,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("index_digest", "sha256:" + "0" * 64),
        lambda value: value.__setitem__(
            "platform_manifest_digest", "sha256:" + "0" * 64
        ),
        lambda value: value.__setitem__("config_digest", "sha256:" + "0" * 64),
        lambda value: value.__setitem__(
            "attestation_manifest_digest", "sha256:" + "0" * 64
        ),
        lambda value: value.__setitem__("layer_digests", ["sha256:" + "0" * 64]),
        lambda value: value.__setitem__("rootfs_diff_ids", ["sha256:" + "0" * 64]),
    ],
)
def test_oci_archive_verifier_rejects_every_identity_link_mutation(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    identity_module = load_linux_identity()
    archive = tmp_path / "runtime.oci.tar"
    image_ref = "mingli-runtime:task8-final"
    expected = write_oci_archive(archive, image_ref)
    expected.pop("runtime_config")
    mutation(expected)

    with pytest.raises(identity_module.IdentityError):
        identity_module.verify_oci_archive(
            archive,
            expected_archive_sha256=sha256_file(archive),
            image_ref=image_ref,
            expected=expected,
        )


def test_oci_archive_verifier_rejects_missing_attestation_blob(
    tmp_path: Path,
) -> None:
    identity_module = load_linux_identity()
    original = tmp_path / "runtime.oci.tar"
    image_ref = "mingli-runtime:task8-final"
    expected = write_oci_archive(original, image_ref)
    expected.pop("runtime_config")
    missing_name = "blobs/sha256/" + expected[
        "attestation_manifest_digest"
    ].removeprefix("sha256:")
    broken = tmp_path / "missing-attestation.oci.tar"
    with tarfile.open(original, "r") as source, tarfile.open(broken, "w") as target:
        for member in source.getmembers():
            if member.name == missing_name:
                continue
            stream = source.extractfile(member)
            target.addfile(member, stream)

    with pytest.raises(identity_module.IdentityError, match="attestation"):
        identity_module.verify_oci_archive(
            broken,
            expected_archive_sha256=sha256_file(broken),
            image_ref=image_ref,
            expected=expected,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("cpus", 9),
        lambda value: value.__setitem__("memory", 9 * 1024**3),
        lambda value: value.__setitem__("disk", 59 * 1024**3),
        lambda value: value["config"].__setitem__("minimumLimaVersion", "2.1.0"),
        lambda value: value["config"].__setitem__("mounts", [{"location": "/Users"}]),
        lambda value: value["config"].__setitem__("propagateProxyEnv", True),
        lambda value: value["config"].__setitem__("cpus", 9),
        lambda value: value["config"].__setitem__("memory", "9GiB"),
        lambda value: value["config"].__setitem__("disk", "59GiB"),
        lambda value: value["config"]["images"][0].__setitem__(
            "digest", "sha256:" + "0" * 64
        ),
    ],
)
def test_linux_identity_rejects_running_instance_profile_drift(
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    identity_module = load_linux_identity()
    payload = complete_lima_instance()
    mutation(payload)

    with pytest.raises(identity_module.IdentityError):
        identity_module._instance_record(
            (json.dumps(payload, sort_keys=True) + "\n").encode(),
            "mingli-linux-gate-vz",
        )
