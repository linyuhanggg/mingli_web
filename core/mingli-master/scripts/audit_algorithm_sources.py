#!/usr/bin/env python3
"""Audit versioned algorithm sources before deterministic provider work.

The complete research transcriptions intentionally remain outside release artifacts.
This audit verifies those local files when requested and always verifies the release-
tracked provenance, conventions, engineering artifacts, and independent samples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = (
    ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER_RE = re.compile(
    r"(?:\bTODO\b|\bTBD\b|placeholder|unavailable|missing[-_ ]source)",
    re.IGNORECASE,
)
DEFERRED_VERIFICATION_RE = re.compile(
    r"(?:\bwill\b|\blater\b|\bto be\b|\bTask\s*\d+\b|以后|稍后|待核|"
    r"将在|将(?:在|于)|待(?:实现|验证|补充)|后续(?:实现|验证|补充))",
    re.IGNORECASE,
)
INDEPENDENT_SAMPLE_SCHEMA = "mingli-algorithm-source-samples-v1"
REQUIRED_PROVIDER_SYSTEMS = (
    "bazi",
    "time-check",
    "fortune",
    "ziwei",
    "luming-nayin",
    "xingming",
    "liuyao",
    "meihua",
    "liuren",
    "qimen",
    "taiyi",
    "selection",
    "fengshui",
    "physiognomy",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)


def _required(
    mapping: dict[str, Any],
    fields: Iterable[str],
    *,
    label: str,
    findings: list[str],
) -> None:
    for field in fields:
        if field not in mapping or mapping[field] in (None, "", [], {}):
            findings.append(f"{label}: missing {field}")


def _research_root(
    payload: dict[str, Any],
    root: Path,
    explicit: Path | None = None,
) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    environment_root = os.environ.get("MINGLI_RESEARCH_ROOT")
    if environment_root:
        return Path(environment_root).resolve()
    configured = str(
        (payload.get("audit_policy") or {}).get("research_source_root") or ""
    )
    if not configured or configured == "external":
        return None
    return (root / configured).resolve()


def _audit_engineering_reference(
    reference: dict[str, Any],
    *,
    root: Path,
    label: str,
    findings: list[str],
) -> None:
    _required(
        reference,
        ("name", "role", "version", "license", "upstream"),
        label=label,
        findings=findings,
    )
    reviewed_hash_fields = (
        "distribution_sha256",
        "npm_tarball_sha256",
        "artifact_sha256",
    )
    if not any(reference.get(field) for field in reviewed_hash_fields):
        findings.append(f"{label}: missing reviewed hash")
    lockfile = reference.get("lockfile")
    lock_entry = reference.get("lock_entry")
    if lockfile or lock_entry:
        if not lockfile or not lock_entry:
            findings.append(f"{label}: lockfile and lock_entry must be paired")
        else:
            path = root / str(lockfile)
            if not path.is_file():
                findings.append(f"{label}: missing lockfile {lockfile}")
            elif str(lock_entry) not in path.read_text(encoding="utf-8"):
                findings.append(f"{label}: lock entry not found: {lock_entry}")
    for hash_field in (
        "distribution_sha256",
        "npm_tarball_sha256",
        "artifact_sha256",
        "license_sha256",
    ):
        if hash_field in reference and not SHA256_RE.fullmatch(
            str(reference[hash_field])
        ):
            findings.append(f"{label}: invalid {hash_field}")
    for path_field, hash_field in (
        ("artifact_path", "artifact_sha256"),
        ("license_path", "license_sha256"),
    ):
        if path_field not in reference:
            continue
        if hash_field not in reference:
            findings.append(f"{label}: {path_field} requires {hash_field}")
            continue
        path = root / str(reference[path_field])
        if not path.is_file():
            findings.append(f"{label}: missing {path_field} {reference[path_field]}")
            continue
        actual = _sha256(path)
        if actual != reference[hash_field]:
            findings.append(
                f"{label}: {path_field} sha256 mismatch "
                f"(expected {reference[hash_field]}, got {actual})"
            )
    provenance_path = reference.get("provenance_path")
    if provenance_path:
        path = root / str(provenance_path)
        if not path.is_file():
            findings.append(f"{label}: missing provenance_path {provenance_path}")
            return
        try:
            provenance = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(f"{label}: invalid provenance document ({exc})")
            return
        if not isinstance(provenance, dict):
            findings.append(f"{label}: invalid provenance document")
            return
        compared_fields = {
            "version": "version",
            "license": "license",
            "upstream": "upstream",
            "upstream_tag_commit": "reviewed_upstream_commit",
            "distribution_sha256": "distribution_sha256",
            "npm_tarball_sha256": "npm_tarball_sha256",
            "npm_integrity": "npm_integrity",
            "artifact_sha256": "vendored_sha256",
            "license_sha256": "license_sha256",
        }
        for reference_field, provenance_field in compared_fields.items():
            if reference_field not in reference:
                continue
            if str(reference[reference_field]) != str(
                provenance.get(provenance_field) or ""
            ):
                findings.append(
                    f"{label}: provenance {provenance_field} does not match "
                    f"audited {reference_field}"
                )


def _excerpt_is_within_line_anchor(text: str, excerpt: str, anchor: str) -> bool:
    ranges = list(re.finditer(r"L(\d+)(?:-L?(\d+))?", anchor))
    if not ranges:
        return True
    lines = text.splitlines()
    selected: list[str] = []
    for match in ranges:
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if 1 <= start <= end <= len(lines):
            selected.extend(lines[start - 1 : end])
    return bool(selected) and excerpt in "\n".join(selected)


def _audit_primary_source(
    source: dict[str, Any],
    *,
    root: Path,
    research_root: Path,
    verify_research_sources: bool,
    label: str,
    findings: list[str],
) -> None:
    _required(
        source,
        (
            "title",
            "edition_or_recension",
            "normalized_path",
            "sha256",
            "anchor",
            "exact_excerpt",
            "material",
            "license_status",
        ),
        label=label,
        findings=findings,
    )
    expected = str(source.get("sha256") or "")
    if not SHA256_RE.fullmatch(expected):
        findings.append(f"{label}: invalid sha256")
        return
    if not verify_research_sources:
        return
    source_root = (
        root
        if source.get("source_location") == "release"
        else research_root
    )
    path = source_root / str(source.get("normalized_path") or "")
    if not path.is_file():
        findings.append(f"{label}: missing research source {path}")
        return
    actual = _sha256(path)
    if actual != expected:
        findings.append(
            f"{label}: research source sha256 mismatch "
            f"(expected {expected}, got {actual})"
        )
    excerpt = str(source.get("exact_excerpt") or "")
    source_text = path.read_text(encoding="utf-8")
    if excerpt and excerpt not in source_text:
        findings.append(f"{label}: exact_excerpt not found in normalized source")
    elif excerpt and not _excerpt_is_within_line_anchor(
        source_text,
        excerpt,
        str(source.get("anchor") or ""),
    ):
        findings.append(f"{label}: exact_excerpt is outside declared anchor")


def _anchor_tokens(anchor: str) -> tuple[str, ...]:
    """Return stable identifiers when an anchor names several sections."""

    identifiers = re.findall(
        r"(?:[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+|[a-z][a-z0-9_]{3,})",
        anchor,
    )
    ignored = {"and", "through", "rules", "source"}
    return tuple(token for token in identifiers if token not in ignored)


def _audit_anchored_file(
    reference: dict[str, Any],
    *,
    root: Path,
    label: str,
    path_field: str,
    anchor_field: str,
    findings: list[str],
) -> None:
    _required(
        reference,
        (path_field, anchor_field),
        label=label,
        findings=findings,
    )
    relative = str(reference.get(path_field) or "")
    anchor = str(reference.get(anchor_field) or "")
    path = root / relative
    if not path.is_file():
        findings.append(f"{label}: missing {path_field} {relative}")
        return
    text = path.read_text(encoding="utf-8")
    if anchor in text:
        return
    tokens = _anchor_tokens(anchor)
    if not tokens or any(token not in text for token in tokens):
        findings.append(f"{label}: {anchor_field} not found: {anchor}")


def _audit_independent_sample(
    sample: dict[str, Any],
    *,
    root: Path,
    label: str,
    findings: list[str],
) -> None:
    _required(
        sample,
        (
            "id",
            "source",
            "source_path",
            "source_anchor",
            "input",
            "expected",
            "independence",
        ),
        label=label,
        findings=findings,
    )
    if DEFERRED_VERIFICATION_RE.search(str(sample.get("independence") or "")):
        findings.append(f"{label}: deferred verification is not allowed")
    _audit_anchored_file(
        sample,
        root=root,
        label=f"{label} independent sample",
        path_field="source_path",
        anchor_field="source_anchor",
        findings=findings,
    )
    relative = str(sample.get("source_path") or "")
    path = Path(relative)
    if not path.is_absolute():
        path = root / path
    if path.suffix.lower() not in {".yaml", ".yml"} or not path.is_file():
        return
    try:
        fixture = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        findings.append(f"{label}: invalid structured fixture ({exc})")
        return
    if not isinstance(fixture, dict) or fixture.get("schema_version") != (
        INDEPENDENT_SAMPLE_SCHEMA
    ):
        findings.append(f"{label}: unsupported structured fixture schema")
        return
    sample_id = str(sample.get("id") or "")
    anchor = str(sample.get("source_anchor") or "")
    if anchor != sample_id:
        findings.append(f"{label}: source_anchor must equal sample id {sample_id}")
        return
    cases = fixture.get("cases")
    case = cases.get(sample_id) if isinstance(cases, dict) else None
    if not isinstance(case, dict):
        findings.append(f"{label}: fixture case {sample_id} not found")
        return
    _required(
        case,
        ("source_reference", "input", "expected", "verification"),
        label=f"{label} fixture case {sample_id}",
        findings=findings,
    )
    verification = str(case.get("verification") or "")
    if DEFERRED_VERIFICATION_RE.search(verification):
        findings.append(f"{label}: deferred verification is not allowed")


def _audit_source_artifact(
    artifact: dict[str, Any],
    *,
    root: Path,
    label: str,
    findings: list[str],
) -> None:
    _required(
        artifact,
        ("path", "schema_version", "sha256"),
        label=label,
        findings=findings,
    )
    expected_hash = str(artifact.get("sha256") or "")
    if not SHA256_RE.fullmatch(expected_hash):
        findings.append(f"{label}: invalid sha256")
        return
    path = root / str(artifact.get("path") or "")
    if not path.is_file():
        findings.append(f"{label}: missing path {artifact.get('path')}")
        return
    actual_hash = _sha256(path)
    if actual_hash != expected_hash:
        findings.append(
            f"{label}: sha256 mismatch (expected {expected_hash}, got {actual_hash})"
        )
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        findings.append(f"{label}: invalid YAML ({exc})")
        return
    if not isinstance(payload, dict) or str(payload.get("schema_version") or "") != str(
        artifact.get("schema_version") or ""
    ):
        findings.append(f"{label}: schema_version mismatch")


def audit_matrix(
    payload: dict[str, Any],
    *,
    root: Path = ROOT,
    systems: Iterable[str] | None = None,
    verify_research_sources: bool | None = None,
    research_root: Path | None = None,
) -> dict[str, Any]:
    findings: list[str] = []
    resolved_research_root = _research_root(payload, root, research_root)
    verify_sources = (
        resolved_research_root is not None
        if verify_research_sources is None
        else verify_research_sources
    )
    if payload.get("schema_version") != "mingli-algorithm-source-dependencies-v1":
        findings.append("matrix: unsupported schema_version")
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        return {
            "ok": False,
            "audited_systems": [],
            "dependency_count": 0,
            "research_sources_verified": verify_sources,
            "findings": ["matrix: providers must be a mapping"],
        }
    for required_system in REQUIRED_PROVIDER_SYSTEMS:
        if required_system not in providers:
            findings.append(f"matrix: missing provider {required_system}")

    selected = tuple(systems) if systems is not None else REQUIRED_PROVIDER_SYSTEMS
    unknown = [system for system in selected if system not in providers]
    findings.extend(f"matrix: unknown requested system {system}" for system in unknown)
    if verify_sources and resolved_research_root is None:
        findings.append(
            "matrix: explicit research source root is required for fulltext verification"
        )
    dependency_count = 0
    seen_sample_ids: set[str] = set()

    for system in selected:
        provider = providers.get(system)
        if not isinstance(provider, dict):
            continue
        provider_label = f"provider {system}"
        if provider.get("source_audit_status") != "source_verified":
            findings.append(
                f"{provider_label}: source_audit_status is "
                f"{provider.get('source_audit_status')!r}, expected 'source_verified'"
            )
            continue
        dependencies = provider.get("dependencies")
        if not isinstance(dependencies, list) or not dependencies:
            findings.append(f"{provider_label}: dependencies must be non-empty")
            continue
        seen: set[str] = set()
        for index, dependency in enumerate(dependencies):
            dependency_count += 1
            if not isinstance(dependency, dict):
                findings.append(f"{provider_label}: dependency {index} is not a mapping")
                continue
            dep_id = str(dependency.get("id") or f"index-{index}")
            label = f"{provider_label} dependency {dep_id}"
            _required(
                dependency,
                (
                    "id",
                    "category",
                    "version",
                    "status",
                    "convention",
                    "primary_sources",
                    "independent_test_sample",
                ),
                label=label,
                findings=findings,
            )
            if dep_id in seen:
                findings.append(f"{label}: duplicate dependency id")
            seen.add(dep_id)
            if dependency.get("status") != "verified":
                findings.append(f"{label}: status must be verified")
            if any(PLACEHOLDER_RE.search(value) for value in _walk_strings(dependency)):
                findings.append(f"{label}: contains placeholder vocabulary")
            convention = dependency.get("convention")
            if isinstance(convention, dict):
                _required(
                    convention,
                    ("id", "version", "disputed", "boundary_rules"),
                    label=f"{label} convention",
                    findings=findings,
                )
                if not isinstance(convention.get("disputed"), bool):
                    findings.append(f"{label} convention: disputed must be boolean")
            sources = dependency.get("primary_sources")
            if isinstance(sources, list):
                for source_index, source in enumerate(sources):
                    if not isinstance(source, dict):
                        findings.append(f"{label}: primary source {source_index} invalid")
                        continue
                    _audit_primary_source(
                        source,
                        root=root,
                        research_root=(resolved_research_root or root),
                        verify_research_sources=verify_sources,
                        label=f"{label} source {source_index}",
                        findings=findings,
                    )
            commentary_dependencies = dependency.get("commentary_dependencies") or []
            if not isinstance(commentary_dependencies, list):
                findings.append(f"{label}: commentary_dependencies must be a list")
            else:
                for commentary_index, commentary in enumerate(
                    commentary_dependencies
                ):
                    commentary_label = (
                        f"{label} commentary dependency {commentary_index}"
                    )
                    if not isinstance(commentary, dict):
                        findings.append(f"{commentary_label}: invalid mapping")
                        continue
                    _required(
                        commentary,
                        ("path", "anchor", "role"),
                        label=commentary_label,
                        findings=findings,
                    )
                    _audit_anchored_file(
                        commentary,
                        root=root,
                        label=commentary_label,
                        path_field="path",
                        anchor_field="anchor",
                        findings=findings,
                    )
            source_artifact = dependency.get("source_artifact")
            if source_artifact is not None:
                if not isinstance(source_artifact, dict):
                    findings.append(f"{label}: source_artifact must be a mapping")
                else:
                    _audit_source_artifact(
                        source_artifact,
                        root=root,
                        label=f"{label} source artifact",
                        findings=findings,
                    )
            sample = dependency.get("independent_test_sample")
            if isinstance(sample, dict):
                sample_label = f"{label} independent_test_sample"
                sample_id = str(sample.get("id") or "")
                if sample_id in seen_sample_ids:
                    findings.append(f"{sample_label}: duplicate sample id")
                elif sample_id:
                    seen_sample_ids.add(sample_id)
                _audit_independent_sample(
                    sample,
                    root=root,
                    label=sample_label,
                    findings=findings,
                )
            references = dependency.get("engineering_references") or []
            if not isinstance(references, list):
                findings.append(f"{label}: engineering_references must be a list")
            else:
                for reference_index, reference in enumerate(references):
                    if not isinstance(reference, dict):
                        findings.append(
                            f"{label}: engineering reference {reference_index} invalid"
                        )
                        continue
                    _audit_engineering_reference(
                        reference,
                        root=root,
                        label=f"{label} engineering reference {reference_index}",
                        findings=findings,
                    )

    return {
        "ok": not findings,
        "audited_systems": list(selected),
        "dependency_count": dependency_count,
        "research_sources_verified": verify_sources,
        "research_source_root": (
            str(resolved_research_root) if resolved_research_root is not None else None
        ),
        "findings": findings,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument(
        "--systems",
        help="comma-separated provider systems; omitted means the full 14-route audit",
    )
    parser.add_argument(
        "--verify-research-sources",
        action="store_true",
        help="verify local normalized fulltext hashes and exact excerpts",
    )
    parser.add_argument(
        "--research-root",
        type=Path,
        help="explicit root containing references/fulltext for strict source verification",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = yaml.safe_load(args.matrix.read_text(encoding="utf-8"))
    systems = tuple(item.strip() for item in args.systems.split(",") if item.strip()) if args.systems else None
    report = audit_matrix(
        payload,
        root=ROOT,
        systems=systems,
        verify_research_sources=args.verify_research_sources,
        research_root=args.research_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
