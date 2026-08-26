#!/usr/bin/env python3
"""Audit Daliuren structural-pattern source bindings against checked packs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULE_CATALOG = ROOT / "references/inference/liuren-rules-v1.json"
EXPECTED_PATTERN_IDENTITIES = {
    "伏吟": ("DLR-09", "liuren.structural.fuyin"),
    "反吟": ("DLR-10", "liuren.structural.fanyin"),
    "八专日": ("DLR-08", "liuren.structural.bazhuan-day"),
    "四课不备": ("DLR-S01", "liuren.structural.incomplete-four-lessons"),
}
EXPECTED_PATTERNS = tuple(EXPECTED_PATTERN_IDENTITIES)
EXPECTED_SOURCE_PACK = "san-shi/daliuren-daquan"
BIEZHE_RULE_ID = "DLR-07"
BIEZHE_QUOTE_ID = "DLQ-012"
BIEZHE_PRECONDITION = "去重后恰为三课，且无直接克、无遥克。"
REQUIRED_FIELDS = (
    "rule_id",
    "local_rule_id",
    "title",
    "source_pack",
    "source_anchor",
    "quote_id",
    "source_excerpt_sha256",
)
OPTIONAL_FIELDS = ("required_distinct_lesson_count",)


def _section(text: str, heading: str, level: int) -> str | None:
    marker = "#" * level
    match = re.search(
        rf"^{re.escape(marker)} {re.escape(heading)}[^\n]*\n"
        rf"(?P<body>.*?)(?=^{'#' * level} |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else None


def _normalized_source(
    manifest: Any,
    *,
    root: Path,
    findings: list[str],
) -> tuple[str, str, str, list[str]]:
    """Load the manifest-declared normalized source and verify its digest."""

    if not isinstance(manifest, Mapping):
        findings.append("source manifest must be an object")
        return "", "", "", []
    local_files = manifest.get("local_files")
    if not isinstance(local_files, list):
        findings.append("source manifest local_files missing")
        return "", "", "", []
    candidates = [
        row
        for row in local_files
        if isinstance(row, Mapping) and row.get("role") == "normalized_search_text"
    ]
    if len(candidates) != 1:
        findings.append("source manifest must declare one normalized_search_text")
        return "", "", "", []

    entry = candidates[0]
    relative_path = entry.get("path")
    declared_sha256 = entry.get("sha256")
    if not isinstance(relative_path, str) or not relative_path.strip():
        findings.append("normalized source path missing")
        return "", "", "", []
    if not isinstance(declared_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", declared_sha256
    ) is None:
        findings.append("normalized source manifest digest is invalid")
        declared_sha256 = ""

    source_path = (root / relative_path).resolve()
    try:
        source_path.relative_to(root.resolve())
    except ValueError:
        findings.append("normalized source path escapes repository root")
        return relative_path, declared_sha256, "", []
    if not source_path.is_file():
        findings.append(f"normalized source file missing: {relative_path}")
        return relative_path, declared_sha256, "", []

    source_bytes = source_path.read_bytes()
    observed_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if observed_sha256 != declared_sha256:
        findings.append("normalized source digest mismatch")
    try:
        source_lines = source_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        findings.append("normalized source must be UTF-8")
        source_lines = []
    return relative_path, declared_sha256, observed_sha256, source_lines


def audit_liuren_structural_patterns() -> dict[str, Any]:
    payload = json.loads(RULE_CATALOG.read_text(encoding="utf-8"))
    catalog = payload.get("source_conditioned_patterns")
    findings: list[str] = []
    audited: list[dict[str, Any]] = []

    if payload.get("schema_version") != "mingli-liuren-executable-rules-v1":
        findings.append("unsupported Liuren rule catalog schema")
    if not isinstance(catalog, dict):
        findings.append("source_conditioned_patterns catalog missing")
        catalog = {}
    if tuple(catalog) != EXPECTED_PATTERNS:
        findings.append("structural pattern source key set/order mismatch")

    pack_root = ROOT / "references/books" / EXPECTED_SOURCE_PACK
    rules_text = (pack_root / "rules.md").read_text(encoding="utf-8")
    quotes_text = (pack_root / "quote-index.md").read_text(encoding="utf-8")
    biezhe_section = _section(rules_text, BIEZHE_RULE_ID, 2)
    if biezhe_section is None:
        findings.append(f"别责: rule card {BIEZHE_RULE_ID} missing")
    else:
        if f"`{BIEZHE_QUOTE_ID}`" not in biezhe_section:
            findings.append(
                f"别责: rule card does not cite {BIEZHE_QUOTE_ID}"
            )
        if BIEZHE_PRECONDITION not in biezhe_section:
            findings.append("别责: complete three-lesson/no-overcome predicate drift")
    manifest_path = pack_root / "source-manifest.yaml"
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        manifest = None
        findings.append("source manifest is missing or invalid")
    (
        normalized_source_path,
        declared_source_sha256,
        observed_source_sha256,
        normalized_source_lines,
    ) = _normalized_source(manifest, root=ROOT, findings=findings)
    coverage = (
        manifest.get("chapter_coverage")
        if isinstance(manifest, Mapping)
        else None
    )
    normalized_coverage = (
        coverage.get("normalized_containers")
        if isinstance(coverage, Mapping)
        else None
    )
    line_span = (
        normalized_coverage.get("line_span")
        if isinstance(normalized_coverage, Mapping)
        else None
    )
    span_match = re.fullmatch(r"L(\d+)-L(\d+)", str(line_span or ""))
    manifest_span = (
        (int(span_match.group(1)), int(span_match.group(2)))
        if span_match
        else None
    )

    for title in EXPECTED_PATTERNS:
        raw = catalog.get(title)
        if not isinstance(raw, dict):
            findings.append(f"{title}: source definition missing")
            continue
        missing = [field for field in REQUIRED_FIELDS if not raw.get(field)]
        unknown = sorted(set(raw) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
        if missing:
            findings.append(f"{title}: missing fields {','.join(missing)}")
        if unknown:
            findings.append(f"{title}: unknown fields {','.join(unknown)}")
        if raw.get("title") != title:
            findings.append(f"{title}: title mismatch")
        if raw.get("source_pack") != EXPECTED_SOURCE_PACK:
            findings.append(f"{title}: source pack mismatch")

        expected_rule_id, expected_local_rule_id = (
            EXPECTED_PATTERN_IDENTITIES[title]
        )
        if raw.get("rule_id") != expected_rule_id:
            findings.append(
                f"{title}: rule identity must be {expected_rule_id}"
            )
        if raw.get("local_rule_id") != expected_local_rule_id:
            findings.append(
                f"{title}: local rule identity must be {expected_local_rule_id}"
            )
        if title == "四课不备":
            if raw.get("rule_id") == BIEZHE_RULE_ID:
                findings.append("四课不备: must not reuse DLR-07 别责 identity")
            if raw.get("required_distinct_lesson_count") != 3:
                findings.append(
                    "四课不备: required distinct lesson count must be 3"
                )

        rule_id = str(raw.get("rule_id") or "")
        quote_id = str(raw.get("quote_id") or "")
        source_anchor = str(raw.get("source_anchor") or "")
        rule_section = (
            None if title == "四课不备" else _section(rules_text, rule_id, 2)
        )
        quote_section = _section(quotes_text, quote_id, 3)
        if title != "四课不备" and rule_section is None:
            findings.append(f"{title}: rule card {rule_id} missing")
        elif rule_section is not None and f"`{quote_id}`" not in rule_section:
            findings.append(f"{title}: rule card does not cite {quote_id}")
        if quote_section is None:
            findings.append(f"{title}: quote index {quote_id} missing")
            continue

        anchor_match = re.search(r"normalized_anchor: `([^`]+)`", quote_section)
        quote_match = re.search(r"exact_quote: `([^`]+)`", quote_section)
        observed_anchor = anchor_match.group(1) if anchor_match else ""
        observed_quote = quote_match.group(1) if quote_match else ""
        expected_anchor = source_anchor.replace("#", ":", 1)
        if observed_anchor != expected_anchor:
            findings.append(f"{title}: source anchor mismatch")
        observed_digest = hashlib.sha256(observed_quote.encode("utf-8")).hexdigest()
        if observed_digest != raw.get("source_excerpt_sha256"):
            findings.append(f"{title}: source excerpt digest mismatch")
        anchor_line_match = re.fullmatch(
            r"(?P<file>[^#/]+)#L(?P<line>[1-9]\d*)",
            source_anchor,
        )
        if manifest_span is None or anchor_line_match is None:
            findings.append(f"{title}: source manifest coverage is not auditable")
        elif not (
            manifest_span[0]
            <= int(anchor_line_match.group("line"))
            <= manifest_span[1]
        ):
            findings.append(f"{title}: source manifest does not cover anchor")
        if anchor_line_match is not None and normalized_source_path:
            if anchor_line_match.group("file") != Path(normalized_source_path).name:
                findings.append(f"{title}: source anchor file mismatch")
            else:
                anchor_line = int(anchor_line_match.group("line"))
                if not 1 <= anchor_line <= len(normalized_source_lines):
                    findings.append(f"{title}: source anchor line is unavailable")
                elif observed_quote not in normalized_source_lines[anchor_line - 1]:
                    findings.append(
                        f"{title}: exact quote missing from normalized source line"
                    )

        audited.append(
            {
                "title": title,
                "rule_id": rule_id,
                "local_rule_id": str(raw.get("local_rule_id") or ""),
                "quote_id": quote_id,
                "source_pack": str(raw.get("source_pack") or ""),
                "source_anchor": source_anchor,
                "source_excerpt_sha256": observed_digest,
            }
        )

    return {
        "schema_version": "mingli-liuren-structural-pattern-source-audit-v1",
        "catalog_schema": payload.get("schema_version"),
        "pattern_count": len(catalog),
        "anchored_pattern_count": len(audited),
        "normalized_source_path": normalized_source_path,
        "manifest_normalized_source_sha256": declared_source_sha256,
        "observed_normalized_source_sha256": observed_source_sha256,
        "normalized_source_line_count": len(normalized_source_lines),
        "biezhe_rule_identity": {
            "rule_id": BIEZHE_RULE_ID,
            "quote_id": BIEZHE_QUOTE_ID,
            "required_predicates": (
                "distinct_lesson_count_eq:3",
                "has_direct_overcome:eq:false",
                "has_remote_overcome:eq:false",
            ),
        },
        "patterns": audited,
        "findings": findings,
        "ready": not findings,
    }


def main() -> int:
    report = audit_liuren_structural_patterns()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
