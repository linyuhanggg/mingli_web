#!/usr/bin/env python3
"""Data-driven vocabulary locality audit for the portable core.

The audit dynamically collects every capability ID and localized display
term from the bundled provider manifests, then scans the forbidden generic
surfaces for those exact string literals using ``tokenize``. It maintains
no hand-written domain word list of its own; deleting or renaming a
manifest automatically changes what is enforced. Source scanning is a
release lint, not a behavior test.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

FORBIDDEN_PYTHON = (
    "scripts/reading_engine/interface.py",
    "scripts/reading_engine/interface_contracts.py",
    "scripts/reading_engine/turns.py",
    "scripts/reading_engine/brief.py",
    "scripts/adapters/__init__.py",
    "scripts/adapters/json_cli.py",
)
FORBIDDEN_MARKDOWN = ("SKILL.md",)

# SKILL.md frontmatter carries exactly one high-level discovery sentence.
FRONTMATTER_EXEMPT_LINE_LIMIT = 4


def _display_labels(display: object) -> set[str]:
    """Every localized label a display block can project.

    A localized value is either the label itself or an object carrying a
    ``name`` plus an optional caller-facing ``description``, exactly as the
    runtime projection reads it. Both spellings must contribute, or moving one
    term to the richer form would quietly drop it from what this audit
    enforces.
    """

    labels: set[str] = set()
    if not isinstance(display, dict):
        return labels
    for localized in display.values():
        if isinstance(localized, str) and localized.strip():
            labels.add(localized.strip())
        elif isinstance(localized, dict):
            name = localized.get("name")
            if isinstance(name, str) and name.strip():
                labels.add(name.strip())
    return labels


def collect_domain_terms() -> set[str]:
    from reading_engine.catalog import CatalogLoader

    catalog = CatalogLoader(ROOT / "resources/runtime").load()
    terms: set[str] = set()
    for descriptor in catalog.descriptors:
        terms.add(descriptor.id)
        payload = descriptor.canonical_payload
        display = payload.get("display") or {}
        for localized in display.values():
            if isinstance(localized, dict):
                for value in localized.values():
                    if isinstance(value, str) and value.strip():
                        terms.add(value.strip())
        for group in ("terms", "input_fields"):
            specs = payload.get(group) or {}
            if not isinstance(specs, dict):
                continue
            for spec in specs.values():
                if isinstance(spec, dict):
                    terms |= _display_labels(spec.get("display"))
    return terms


def _python_string_literals(path: Path) -> list[tuple[int, str]]:
    literals: list[tuple[int, str]] = []
    source = path.read_text(encoding="utf-8")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.STRING:
            continue
        raw = token.string
        try:
            value = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            # f-strings and other non-literals are inspected as raw text
            value = raw
        if isinstance(value, str):
            literals.append((token.start[0], value))
    return literals


def audit() -> list[str]:
    terms = collect_domain_terms()
    if not terms:
        return ["no domain terms collected from provider manifests"]
    findings: list[str] = []
    for relative in FORBIDDEN_PYTHON:
        path = ROOT / relative
        if not path.is_file():
            findings.append(f"missing forbidden-surface file: {relative}")
            continue
        for line_number, value in _python_string_literals(path):
            for term in terms:
                if term and term in value:
                    findings.append(
                        f"{relative}:{line_number}: literal leaks domain term"
                        f" {term!r}"
                    )
    for relative in FORBIDDEN_MARKDOWN:
        path = ROOT / relative
        if not path.is_file():
            findings.append(f"missing forbidden-surface file: {relative}")
            continue
        in_frontmatter = False
        frontmatter_lines = 0
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.strip() == "---" and line_number <= 8:
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                frontmatter_lines += 1
                if frontmatter_lines <= FRONTMATTER_EXEMPT_LINE_LIMIT:
                    # one high-level discovery description is allowed
                    continue
            for term in terms:
                if term and term in line:
                    findings.append(
                        f"{relative}:{line_number}: markdown leaks domain term"
                        f" {term!r}"
                    )
    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    findings = audit()
    payload = {
        "schema_version": "mingli-vocabulary-locality-audit-v1",
        "forbidden_python": list(FORBIDDEN_PYTHON),
        "forbidden_markdown": list(FORBIDDEN_MARKDOWN),
        "findings": findings,
        "ok": not findings,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
