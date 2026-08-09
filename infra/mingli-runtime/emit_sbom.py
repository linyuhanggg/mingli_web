#!/usr/bin/env python3
"""Emit a CycloneDX SBOM from the installed production image bytes."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

import verify_release

RUNTIME_ROOT = Path("/opt/mingli-runtime")
RELEASE_ROOT = Path("/opt/mingli-master")
RUNTIME_PYTHON = Path("/opt/mingli-runtime/venv/bin/python")
RUNTIME_INTEGRITY = Path("/opt/mingli-runtime/venv/runtime-integrity.json")
NODE = Path("/opt/node/bin/node")
GIT = Path("/opt/git/bin/git")
PROVENANCE = RUNTIME_ROOT / "dependency-provenance.json"
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")


class SbomError(RuntimeError):
    """The installed image does not match its frozen dependency provenance."""


def _fail(message: str) -> NoReturn:
    raise SbomError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing or unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise SbomError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _distribution_tree_sha256(name: str) -> str:
    distribution = importlib.metadata.distribution(name)
    files = distribution.files
    if not files:
        _fail(f"installed distribution has no file inventory: {name}")
    root = RUNTIME_PYTHON.parent.parent.resolve(strict=True)
    digest = hashlib.sha256()
    observed = 0
    for entry in sorted(files, key=lambda item: str(item)):
        path = Path(distribution.locate_file(entry))
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise SbomError(f"installed distribution file is missing: {entry}") from exc
        if not resolved.is_relative_to(root) or path.is_symlink() or not path.is_file():
            _fail(f"installed distribution file is unsafe: {entry}")
        relative = resolved.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        file_digest = bytes.fromhex(sha256_file(resolved))
        digest.update(file_digest)
        observed += 1
    if observed == 0:
        _fail(f"installed distribution is empty: {name}")
    return digest.hexdigest()


def _hash(value: str) -> list[dict[str, str]]:
    return [{"alg": "SHA-256", "content": value}]


def _properties(values: Mapping[str, object]) -> list[dict[str, str]]:
    return [
        {"name": name, "value": str(value)} for name, value in sorted(values.items())
    ]


def _component(
    *,
    name: str,
    version: str,
    component_type: str,
    digest: str,
    license_id: str | None = None,
    license_expression: str | None = None,
    properties: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    if license_id is not None and license_expression is not None:
        _fail("SBOM component cannot use both a license ID and expression")
    value: dict[str, Any] = {
        "bom-ref": f"mingli:{name}@{version}",
        "hashes": _hash(digest),
        "name": name,
        "type": component_type,
        "version": version,
    }
    if license_id is not None:
        value["licenses"] = [{"license": {"id": license_id}}]
    if license_expression is not None:
        value["licenses"] = [{"expression": license_expression}]
    if properties:
        value["properties"] = _properties(properties)
    return value


def build_sbom(image_id: str) -> dict[str, Any]:
    if IMAGE_ID_RE.fullmatch(image_id) is None:
        _fail("production image ID must be an OCI index digest")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        _fail("SBOM must be generated inside Linux x86_64 production")
    if platform.python_version() != "3.14.6" or Path(sys.executable) != RUNTIME_PYTHON:
        _fail("SBOM must use the admitted CPython 3.14.6 executable")
    node = subprocess.run(
        [str(NODE), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if node.returncode != 0 or node.stdout.strip() != "v26.3.0":
        _fail("installed Node runtime identity mismatch")
    native_linkage = verify_release.inspect_native_linkage(RUNTIME_PYTHON, NODE, GIT)

    provenance = _load_json(PROVENANCE, "dependency provenance")
    runtime_integrity = _load_json(RUNTIME_INTEGRITY, "runtime integrity")
    if runtime_integrity.get("distributions") != verify_release.EXPECTED_DISTRIBUTIONS:
        _fail("runtime integrity distribution identity mismatch")
    python_provenance = provenance.get("python_distributions")
    if not isinstance(python_provenance, dict):
        _fail("Python dependency provenance is missing")

    components: list[dict[str, Any]] = [
        _component(
            name="cpython",
            version="3.14.6",
            component_type="application",
            digest=sha256_file(RUNTIME_PYTHON),
            properties={"mingli:installed-path": str(RUNTIME_PYTHON)},
        ),
        _component(
            name="python-base-image",
            version="3.14.6-slim-bookworm",
            component_type="container",
            digest=str(
                provenance["base_image"]["linux_amd64_manifest_digest"]
            ).removeprefix("sha256:"),
            properties={
                "mingli:image-name": provenance["base_image"]["name"],
                "mingli:multi-platform-index-digest": provenance["base_image"][
                    "multi_platform_index_digest"
                ],
            },
        ),
    ]
    distribution_names = {
        "PyYAML": "PyYAML",
        "astronomy-engine": "astronomy-engine",
        "cnlunar": "cnlunar",
        "sxtwl": "sxtwl",
    }
    for provenance_name, distribution_name in distribution_names.items():
        record = python_provenance.get(provenance_name)
        if not isinstance(record, dict):
            _fail(f"dependency provenance is missing: {provenance_name}")
        installed_version = importlib.metadata.version(distribution_name)
        if installed_version != record.get("version"):
            _fail(f"installed dependency version mismatch: {provenance_name}")
        artifact_sha256 = record.get("wheel_sha256", record.get("sha256"))
        if not isinstance(artifact_sha256, str):
            _fail(f"dependency artifact hash is missing: {provenance_name}")
        properties: dict[str, object] = {
            "mingli:artifact-filename": record.get(
                "wheel_filename", record.get("filename")
            ),
            "mingli:installed-files-sha256": _distribution_tree_sha256(
                distribution_name
            ),
        }
        if provenance_name == "sxtwl":
            properties.update(
                {
                    "mingli:source-sdist-filename": record["sdist_filename"],
                    "mingli:source-sdist-sha256": record["sdist_sha256"],
                }
            )
        components.append(
            _component(
                name=provenance_name,
                version=str(record["version"]),
                component_type="library",
                digest=artifact_sha256,
                license_id=str(record["license"]),
                properties=properties,
            )
        )

    git_provenance = provenance.get("git")
    if git_provenance != verify_release.EXPECTED_GIT:
        _fail("Git dependency provenance mismatch")
    components.append(
        _component(
            name="git",
            version=str(git_provenance["version"]),
            component_type="application",
            digest=str(git_provenance["source_sha256"]),
            license_id=str(git_provenance["license"]),
            properties={
                "mingli:artifact-filename": git_provenance["source_filename"],
                "mingli:build-config-json": json.dumps(
                    git_provenance["build_config"],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "mingli:build-config-path": git_provenance["build_config_path"],
                "mingli:build-config-sha256": git_provenance["build_config_sha256"],
                "mingli:installed-binary-sha256": git_provenance[
                    "installed_binary_sha256"
                ],
                "mingli:installed-path": git_provenance["installed_binary_path"],
                "mingli:installed-tree-content-bytes": git_provenance[
                    "installed_tree_content_bytes"
                ],
                "mingli:installed-tree-entry-count": git_provenance[
                    "installed_tree_entry_count"
                ],
                "mingli:installed-tree-regular-file-count": git_provenance[
                    "installed_tree_regular_file_count"
                ],
                "mingli:installed-tree-sha256": git_provenance["installed_tree_sha256"],
                "mingli:installed-tree-symlink-count": git_provenance[
                    "installed_tree_symlink_count"
                ],
                "mingli:license-path": git_provenance["license_path"],
                "mingli:license-sha256": git_provenance["license_sha256"],
                "mingli:source-url": git_provenance["source_url"],
            },
        )
    )

    node_provenance = provenance.get("node")
    if node_provenance != verify_release.EXPECTED_NODE | {
        "license": "MIT",
        "source_url": "https://nodejs.org/dist/v26.3.0/node-v26.3.0-linux-x64.tar.gz",
    }:
        _fail("Node dependency provenance mismatch")
    components.append(
        _component(
            name="node",
            version="26.3.0",
            component_type="application",
            digest=str(node_provenance["sha256"]),
            license_id="MIT",
            properties={
                "mingli:artifact-filename": node_provenance["filename"],
                "mingli:installed-binary-sha256": sha256_file(NODE),
                "mingli:source-url": node_provenance["source_url"],
            },
        )
    )
    system_runtime = provenance.get("system_runtime")
    if system_runtime != {"libatomic1": verify_release.EXPECTED_LIBATOMIC}:
        _fail("libatomic1 system-runtime provenance mismatch")
    libatomic = system_runtime["libatomic1"]
    components.append(
        _component(
            name="libatomic1",
            version=str(libatomic["version"]),
            component_type="library",
            digest=str(libatomic["sha256"]),
            license_expression=str(libatomic["license"]),
            properties={
                "mingli:architecture": libatomic["architecture"],
                "mingli:artifact-filename": libatomic["filename"],
                "mingli:fetch-url": libatomic["fetch_url"],
                "mingli:installed-path": libatomic["installed_path"],
                "mingli:installed-sha256": libatomic["installed_sha256"],
                "mingli:origin-url": libatomic["origin_url"],
                "mingli:snapshot-timestamp": libatomic["snapshot_timestamp"],
                "mingli:soname-path": libatomic["soname_path"],
                "mingli:soname-target": libatomic["soname_target"],
            },
        )
    )
    iztro_provenance = provenance.get("vendored", {}).get("iztro")
    if not isinstance(iztro_provenance, dict):
        _fail("iztro dependency provenance is missing")
    iztro_path = RELEASE_ROOT / str(iztro_provenance["release_path"])
    if sha256_file(iztro_path) != iztro_provenance.get("sha256"):
        _fail("installed iztro bytes differ from provenance")
    components.append(
        _component(
            name="iztro",
            version=str(iztro_provenance["version"]),
            component_type="library",
            digest=str(iztro_provenance["sha256"]),
            license_id=str(iztro_provenance["license"]),
            properties={
                "mingli:npm-tarball-sha256": iztro_provenance["npm_tarball_sha256"],
                "mingli:release-path": iztro_provenance["release_path"],
            },
        )
    )

    runtime_integrity_sha256 = sha256_file(RUNTIME_INTEGRITY)
    release_manifest_sha256 = sha256_file(RELEASE_ROOT / verify_release.MANIFEST_NAME)
    root_ref = f"mingli:runtime-image@{image_id}"
    return {
        "$schema": "https://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "components": sorted(components, key=lambda item: str(item["bom-ref"])),
        "dependencies": [
            {
                "dependsOn": sorted(str(item["bom-ref"]) for item in components),
                "ref": root_ref,
            }
        ],
        "metadata": {
            "component": {
                "bom-ref": root_ref,
                "name": "mingli-v51-runtime",
                "properties": _properties(
                    {
                        "mingli:base-image-manifest-digest": provenance["base_image"][
                            "linux_amd64_manifest_digest"
                        ],
                        verify_release.IMAGE_DIGEST_PROPERTY: image_id,
                        "mingli:release-manifest-sha256": release_manifest_sha256,
                        "mingli:runtime-integrity-sha256": runtime_integrity_sha256,
                        "mingli:native-linkage-sha256": verify_release.canonical_sha256(
                            native_linkage
                        ),
                    }
                ),
                "type": "container",
                "version": "5.1",
            },
            "tools": {
                "components": [
                    {
                        "name": "mingli-emit-sbom",
                        "type": "application",
                        "version": "1",
                    }
                ]
            },
        },
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, root_ref)}",
        "specVersion": "1.6",
        "version": 1,
    }


def main() -> int:
    image_id = os.environ.get("MINGLI_PRODUCTION_IMAGE_ID", "")
    try:
        value = build_sbom(image_id)
    except (KeyError, OSError, SbomError) as exc:
        print(f"SBOM generation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
