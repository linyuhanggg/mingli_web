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
            "bd03d0b56d81112d87ad340a3d65458059497dc33496b1938fb23056dfe8ba80"
        ),
    },
}
EXPECTED_IZTRO_SHA256 = (
    "4b8eca323e5d4291471567c62255a2166471c55c77ebe8f0d2d38240e69d12b1"
)
EXPECTED_TEST_COUNT = 1584
EXPECTED_TEST_TARGETS = 126
EXPECTED_TEST_MODULES = 93
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
    if not isinstance(result, dict) or result.get("kind") != "described":
        _fail("portable describe did not return Described")
    if result.get("protocol_version") != EXPECTED_RELEASE["protocol_version"]:
        _fail("portable describe protocol mismatch")
    if result.get("manifest_digest") != EXPECTED_RELEASE["describe_digest"]:
        _fail("portable describe manifest digest mismatch")
    capabilities = result.get("capabilities")
    if not isinstance(capabilities, list):
        _fail("portable describe capabilities are invalid")
    provider_ids = {item.get("id") for item in capabilities if isinstance(item, dict)}
    if len(capabilities) != 13 or provider_ids != EXPECTED_PROVIDERS:
        _fail("portable describe does not expose all 13 Provider capabilities")
    return result


def inspect_runtime(
    *,
    release_root: Path,
    runtime_python: Path | None = None,
    node: Path | None = None,
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
    if runtime_python is None or node is None or state_root is None:
        _fail("full runtime inspection requires Python, Node, and state root")
    runtime = _verify_runtime_python(release_root, runtime_python)
    node_record = _verify_node(node)
    state = _verify_state_root(state_root)
    first_describe = _run_describe(release_root, runtime_python, state_root)
    second_describe = _run_describe(release_root, runtime_python, state_root)
    if first_describe != second_describe:
        _fail("portable describe is not repeatable")
    inventory.update(
        {
            "describe": first_describe,
            "describe_output_sha256": canonical_sha256(first_describe),
            "node": node_record,
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


def _verify_sbom(path: Path, report: Mapping[str, Any]) -> None:
    sbom = _load_json(path, "SBOM")
    if sbom.get("bomFormat") != "CycloneDX":
        _fail("SBOM is not CycloneDX")
    components = sbom.get("components")
    if not isinstance(components, list):
        _fail("SBOM components are missing")
    by_identity = {
        (item.get("name"), item.get("version")): item
        for item in components
        if isinstance(item, dict)
    }
    required = {
        ("cpython", "3.14.6"),
        ("python-base-image", "3.14.6-slim-bookworm"),
        ("node", EXPECTED_NODE["version"]),
        ("iztro", "2.5.8"),
        ("PyYAML", "6.0.3"),
        ("sxtwl", "2.0.7"),
        ("astronomy-engine", "2.1.19"),
        ("cnlunar", "0.2.4"),
    }
    if not required <= set(by_identity):
        _fail("SBOM omits a required Python, Node, or vendored component")

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
    for component_name, expected in EXPECTED_PYTHON_ARTIFACTS.items():
        version = str(expected["version"])
        expected_hash = expected.get("wheel_sha256", expected.get("sha256"))
        if component_hashes((component_name, version)) != {expected_hash}:
            _fail(f"SBOM Python artifact SHA-256 mismatch: {component_name}")
    node_hashes = by_identity[("node", EXPECTED_NODE["version"])].get("hashes")
    if not isinstance(node_hashes, list) or {
        item.get("content")
        for item in node_hashes
        if isinstance(item, dict) and item.get("alg") == "SHA-256"
    } != {EXPECTED_NODE["sha256"]}:
        _fail("SBOM Node tarball SHA-256 provenance mismatch")
    iztro_hashes = by_identity[("iztro", "2.5.8")].get("hashes")
    if EXPECTED_IZTRO_SHA256 not in {
        item.get("content") for item in iztro_hashes or () if isinstance(item, dict)
    }:
        _fail("SBOM vendored iztro SHA-256 provenance mismatch")
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
    if report.get("target", {}).get("node_version") != EXPECTED_NODE["version"]:
        _fail("release report Node version differs from SBOM provenance")


def _command_map(
    commands: object,
    *,
    artifacts_root: Path,
    image_id: str,
    audit_image_id: str,
) -> dict[str, dict[str, Any]]:
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
        if executed_in not in {image_id, audit_image_id}:
            _fail(f"audit command image identity mismatch: {command_id}")
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
        "accepted-restore",
        "accepted-restore-volume-empty",
        "accepted-snapshot-capture",
        "accepted-snapshot-seal",
        "prepared-followup",
        "prepared-followup-complete",
        "prepared-restore",
        "prepared-restore-volume-empty",
        "prepared-snapshot-capture",
        "prepared-snapshot-seal",
        "source-complete",
        "source-prepare",
    }
    command_records = evidence.get("commands")
    if not isinstance(command_records, list):
        _fail("backup/restore command evidence is missing")
    commands: dict[str, dict[str, Any]] = {}
    runtime_command_ids = {
        "accepted-complete-replay",
        "prepared-followup",
        "prepared-followup-complete",
        "source-complete",
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
        _verify_artifact_digest(
            artifacts_root,
            command.get("stdout_path"),
            command.get("stdout_sha256"),
            f"backup/restore command {command_id} stdout",
        )
        _verify_artifact_digest(
            artifacts_root,
            command.get("stderr_path"),
            command.get("stderr_sha256"),
            f"backup/restore command {command_id} stderr",
        )
        commands[command_id] = command
    if set(commands) != expected_command_ids:
        _fail("backup/restore command inventory is not exact")

    transcript_ids = {
        "accepted-replay": "accepted-complete-replay",
        "prepared-followup": "prepared-followup",
        "prepared-followup-accepted": "prepared-followup-complete",
        "source-accepted": "source-complete",
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
        transcripts[transcript_id] = transcript

    source_prepared = transcripts["source-prepared"]
    followup = transcripts["prepared-followup"]
    followup_accepted = transcripts["prepared-followup-accepted"]
    source_accepted = transcripts["source-accepted"]
    accepted_replay = transcripts["accepted-replay"]
    if source_prepared.get("kind") != "prepared" or followup.get("kind") != "prepared":
        _fail("Prepared backup did not restore into a real tokened follow-up")
    if followup.get("input_token_fingerprint") != source_prepared.get(
        "token_fingerprint"
    ):
        _fail("Prepared follow-up did not use the restored source token")
    if followup_accepted.get("input_token_fingerprint") != followup.get(
        "token_fingerprint"
    ):
        _fail("Prepared follow-up completion did not use the restored child token")
    if source_accepted.get("kind") != "accepted" or accepted_replay.get("kind") != (
        "accepted"
    ):
        _fail("Accepted backup replay did not return Accepted")
    if accepted_replay.get("input_token_fingerprint") != source_prepared.get(
        "token_fingerprint"
    ):
        _fail("Accepted replay did not use the original Prepared token")
    if accepted_replay.get("token_fingerprint") != source_accepted.get(
        "token_fingerprint"
    ):
        _fail("Accepted replay did not return the original Accepted token")
    if accepted_replay.get("command_sha256") != source_accepted.get("command_sha256"):
        _fail("Accepted replay did not use the byte-identical Complete command")
    copy_digests = {
        followup_accepted.get("public_copy_sha256"),
        source_accepted.get("public_copy_sha256"),
        accepted_replay.get("public_copy_sha256"),
    }
    if len(copy_digests) != 1 or None in copy_digests:
        _fail("backup/restore public_copy bytes were not identical")
    if evidence.get("prepared_token_restored") is not True:
        _fail("Prepared token was not restored across a blank state volume")
    if evidence.get("accepted_token_replayed") is not True:
        _fail("Accepted token was not replayed across a blank state volume")
    if evidence.get("complete_public_copy_byte_identical") is not True:
        _fail("restored Complete did not preserve the exact public copy bytes")
    if "state_token" in json.dumps(evidence, sort_keys=True):
        _fail("backup/restore evidence must not contain a plaintext state token")
    if not isinstance(section, dict) or section.get("status") != "passed":
        _fail("backup/restore report section did not pass")
    for field in ("accepted_token_replayed", "prepared_token_restored"):
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
    if artifact.get("image_digest_kind") != "oci_config":
        _fail("production image digest kind must be the local OCI config digest")
    if image_digest != image_id:
        _fail("production image digest and image ID must be the same OCI config digest")
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
        "node": provenance.get("node"),
        "pyyaml": python_distributions.get("PyYAML"),
        "sxtwl": python_distributions.get("sxtwl"),
        "iztro": provenance.get("vendored", {}).get("iztro"),
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
    commands = _command_map(
        audit.get("commands"),
        artifacts_root=artifacts_root,
        image_id=image_id,
        audit_image_id=audit_image_id,
    )
    expected_command_ids = {
        "characterization-a",
        "characterization-b",
        "p0-trajectories",
        "provider-matrix-a",
        "provider-matrix-b",
        "release-regression",
        "runtime-inventory",
        "runtime-probe-machine",
        "runtime-probe-unittest",
    }
    if set(commands) != expected_command_ids:
        _fail("audit command inventory differs from the frozen Linux Gate")
    runtime_path = "/opt/mingli-runtime/venv/bin/python"
    audit_script = "/opt/mingli-runtime/audit_runtime.py"
    source_root = "/audit-source"
    output_root = "/audit-output"
    matrix_path = "/audit-source/references/matrices/provider-completeness.yaml"
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
            "--state-root",
            "/var/lib/mingli",
            "--research-source",
            source_root,
            "--inventory-output",
            f"{output_root}/evidence/runtime-inventory.json",
        ),
        cwd="/opt/mingli-master",
        image_id=audit_image_id,
    )
    if inventory_command.get("stdout_sha256") != hashlib.sha256(b"").hexdigest():
        _fail("runtime inventory command emitted unexpected stdout")
    matrix_argv = (
        runtime_path,
        "-B",
        "/audit-source/scripts/audit_provider_completeness.py",
        "--check",
        "--matrix",
        matrix_path,
    )
    for command_id in ("provider-matrix-a", "provider-matrix-b"):
        _require_command(
            commands,
            command_id,
            argv=matrix_argv,
            cwd=source_root,
            image_id=audit_image_id,
        )
    if (
        commands["provider-matrix-a"]["stdout_sha256"]
        != commands["provider-matrix-b"]["stdout_sha256"]
    ):
        _fail("13 Provider live matrix output changed across two runs")
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
            image_id=audit_image_id,
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
            "provider-matrix-a",
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
            "5",
            "--research-root",
            source_root,
        ),
        cwd=source_root,
        image_id=audit_image_id,
    )
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
        image_id=audit_image_id,
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
        image_id=audit_image_id,
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
        image_id=audit_image_id,
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
