#!/usr/bin/env python3
"""Audit the exact runtime closure intended for portable distribution.

This intentionally audits the same allow-list that deployment copies.  A
repository archive is not a release artifact: it contains history, tests and
host notes which are useful to developers but must never become an installed
Skill instruction surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

import release_deploy


TEXT_SUFFIXES = {
    ".json",
    ".js",
    ".lock",
    ".md",
    ".py",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_PREFIXES = (
    ".git",
    "agents",
    "docs",
    "references/fulltext",
    "tests",
)
RETIRED_PREFIXES = ("scripts/legacy_v3",)
RETIRED_PATHS = {
    "scripts/accepted_index_migrate.py",
    "scripts/audit_v4_runtime_boundary.py",
    "scripts/fortune_public_brief.py",
    "scripts/gate_check.py",
    "scripts/inference_contract.py",
    "scripts/liuren_public_brief.py",
    "scripts/live_replay_runner.py",
    "scripts/public_answer_contract.py",
    "scripts/public_answer_finalize.py",
    "scripts/query_intent.py",
    "scripts/reading_engine/answer_contract.py",
    "scripts/reading_engine/capability_resolver.py",
    "scripts/reading_engine/cross_check.py",
    "scripts/reading_engine/drafting.py",
    "scripts/reading_engine/fortune.py",
    "scripts/reading_engine/legacy.py",
    "scripts/reading_engine/routing.py",
    "scripts/reading_engine/transaction.py",
    "scripts/reading_engine/ziwei.py",
    "scripts/reading_followup.py",
    "scripts/reading_public_brief.py",
    "scripts/route_capabilities.py",
    "scripts/test_atomic_pipeline_publish.py",
    "scripts/test_v51_capability_resolver.py",
}
FORBIDDEN_PATHS = {
    "CHANGELOG.md",
    "README.md",
    "agents/openai.yaml",
    "references/bazi-couple-future-six-year-pattern-2026-2031.md",
    "references/bazi-couple-marriage-probability.md",
    "references/bazi-male-marriage-timing-cherry.md",
    "references/bazi-marriage-year-review.md",
    "references/bazi-material-level-comparison-notes.md",
    "references/bazi-relationship-career-followups.md",
    "references/bazi-relationship-infidelity-risk.md",
    "references/bazi-relationship-year-followup-notes.md",
    "references/bazi-screenshot-qiyun-and-exam-review.md",
    "references/bazi-under23-family-material-comparison.md",
    "references/fortune-cron-reminders.md",
    "references/production-pipelines.md",
    "references/tool-adapters.md",
    "scripts/reading_transaction.py",
    "test-prompts.json",
}
FORBIDDEN_FRAGMENTS = (
    "2000-10-18" + "T05:10:00",
    "2000-10-18" + "T05:30:00",
    "2001-01-" + "25",
    "福建" + "莆田",
    "a11479d1" + "95d2493cb69cb2fc5e927b17",
    "062d7811" + "8ac64ac1ad2d2031ea6b86aa",
    "source_" + "session",
    "source_" + "message_ids",
    "/Users/" + "yuhanglin",
    "HERMES_" + "HOME",
    "." + "hermes",
)
PUBLIC_PROJECTION_POINTER_PREFIXES = (
    "/facts/chart_facts/output/",
    "/fact_extension/facts/",
)


def _matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for prefix in prefixes
    )


def _matches_retired_prefix(path: str) -> bool:
    return _matches_prefix(path, RETIRED_PREFIXES)


def _is_text_path(path: PurePosixPath) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _is_public_projection_pointer(value: object) -> bool:
    return isinstance(value, str) and value.startswith(
        PUBLIC_PROJECTION_POINTER_PREFIXES
    )


def _valid_string_list(value: object, *, non_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (bool(value) or not non_empty)
        and all(isinstance(item, str) and item for item in value)
    )


def _audit_public_projection_manifest(
    relative: str,
    resolved: Path,
    errors: list[str],
) -> None:
    """Validate optional caller-view bindings before they can be released.

    The runtime treats these projections as optional so a bad display binding
    cannot suppress a valid calculation. The release audit makes malformed or
    private declarations a build failure instead.
    """

    if not (
        relative.startswith("resources/runtime/providers/")
        and relative.endswith(".json")
    ):
        return
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        errors.append(f"invalid provider manifest: {relative}: {exc}")
        return
    if not isinstance(payload, dict):
        errors.append(f"invalid provider manifest: {relative}")
        return
    terms = payload.get("terms")
    runtime = payload.get("runtime_capability")
    if not isinstance(terms, dict) or not isinstance(runtime, dict):
        errors.append(f"invalid provider manifest: {relative}")
        return
    bindings = runtime.get("finding_bindings", [])
    if not isinstance(bindings, list):
        errors.append(f"invalid public finding bindings: {relative}")
        return
    for index, binding in enumerate(bindings):
        label = f"{relative}:finding_bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"invalid public finding binding: {label}")
            continue
        if not isinstance(binding.get("id"), str) or not binding["id"]:
            errors.append(f"missing public finding id: {label}")
        kind_id = binding.get("kind_id")
        if not isinstance(kind_id, str) or not kind_id or kind_id not in terms:
            errors.append(f"unknown public finding term: {label}")
        pointers = binding.get("json_pointers")
        if not _valid_string_list(pointers, non_empty=True) or not all(
            _is_public_projection_pointer(pointer) for pointer in pointers
        ):
            errors.append(f"unsafe public finding pointer: {label}")
        for key in ("horizons", "dimension_ids", "support_fact_ids"):
            if key in binding and not _valid_string_list(binding[key]):
                errors.append(f"invalid public finding {key}: {label}")

    limits = runtime.get("limit_bindings", [])
    if not isinstance(limits, list):
        errors.append(f"invalid public limit bindings: {relative}")
        return
    for index, binding in enumerate(limits):
        label = f"{relative}:limit_bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"invalid public limit binding: {label}")
            continue
        kind_id = binding.get("kind_id")
        if not isinstance(kind_id, str) or not kind_id or kind_id not in terms:
            errors.append(f"unknown public limit term: {label}")
        if not _is_public_projection_pointer(binding.get("json_pointer")):
            errors.append(f"unsafe public limit pointer: {label}")
        if "equals" not in binding:
            errors.append(f"missing public limit comparator: {label}")
        for key in ("scope_refs", "detail_ids"):
            if key in binding and not _valid_string_list(binding[key]):
                errors.append(f"invalid public limit {key}: {label}")

    horizon_binding = runtime.get("request_view_horizon_binding")
    if horizon_binding is not None and (
        not isinstance(horizon_binding, dict)
        or not _is_public_projection_pointer(horizon_binding.get("json_pointer"))
    ):
        errors.append(f"unsafe request-view horizon binding: {relative}")


def _audit_path(relative: str, source: Path, errors: list[str]) -> None:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"unsafe release path: {relative}")
        return
    if (
        _matches_prefix(relative, FORBIDDEN_PREFIXES)
        or relative in FORBIDDEN_PATHS
    ):
        errors.append(f"forbidden release path: {relative}")
    if relative.startswith("scripts/test_"):
        errors.append(f"test release path: {relative}")
    if _matches_retired_prefix(relative) or relative in RETIRED_PATHS:
        errors.append(f"retired release path: {relative}")

    resolved = source / relative
    if resolved.is_symlink():
        errors.append(f"release symlink is not allowed: {relative}")
        return
    if not resolved.is_file():
        errors.append(f"release file is not regular: {relative}")
        return
    _audit_public_projection_manifest(relative, resolved, errors)
    if not _is_text_path(path):
        return
    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    except OSError as exc:
        errors.append(f"cannot read release file {relative}: {exc}")
        return
    for fragment in FORBIDDEN_FRAGMENTS:
        if fragment in text:
            errors.append(f"private fragment in {relative}: {fragment!r}")


def audit_release_surface(source: Path) -> dict[str, object]:
    """Audit only the files that deployment would install from ``source``."""

    selected = release_deploy.tracked_release_files(source)
    errors: list[str] = []
    for relative in selected:
        _audit_path(relative, source, errors)
    return {
        "ok": not errors,
        "surface": release_deploy.RUNTIME_CLOSURE_SCHEMA,
        "file_count": len(selected),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args(argv)
    result = audit_release_surface(args.source.expanduser().resolve())
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"release surface audit failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
