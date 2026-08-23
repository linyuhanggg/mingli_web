#!/usr/bin/env python3
"""Audit Daliuren structural-pattern source bindings against checked packs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULE_CATALOG = ROOT / "references/inference/liuren-rules-v1.json"
EXPECTED_PATTERNS = ("伏吟", "反吟", "八专日", "四课不备")
EXPECTED_SOURCE_PACK = "san-shi/daliuren-daquan"
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
    manifest_text = (pack_root / "source-manifest.yaml").read_text(encoding="utf-8")
    span_match = re.search(r'line_span: "L(\d+)-L(\d+)"', manifest_text)
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

        rule_id = str(raw.get("rule_id") or "")
        quote_id = str(raw.get("quote_id") or "")
        source_anchor = str(raw.get("source_anchor") or "")
        rule_section = _section(rules_text, rule_id, 2)
        quote_section = _section(quotes_text, quote_id, 3)
        if rule_section is None:
            findings.append(f"{title}: rule card {rule_id} missing")
        elif f"`{quote_id}`" not in rule_section:
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
        anchor_line_match = re.search(r"#?L(\d+)$", source_anchor)
        if manifest_span is None or anchor_line_match is None:
            findings.append(f"{title}: source manifest coverage is not auditable")
        elif not manifest_span[0] <= int(anchor_line_match.group(1)) <= manifest_span[1]:
            findings.append(f"{title}: source manifest does not cover anchor")

        audited.append(
            {
                "title": title,
                "rule_id": rule_id,
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
