#!/usr/bin/env python3
"""Audit source trace coverage for shensha entries.

The audit is intentionally mechanical: it reads the shensha name map and the
per-entry source profile, then scans only local D2-ready pack layers. It does
not promote acquisition-only sources and it does not treat a text hit as an
interpretation rule by itself.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml


TRACE_LAYERS = ("quote-index.md", "terms.md", "rules.md")
MAX_ANCHORS_PER_PACK = 4


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse as a YAML mapping")
    return data


def split_name_terms(value: str) -> list[str]:
    pieces = re.split(r"[/／、,，\s]+", value)
    return [piece.strip() for piece in pieces if piece.strip()]


def search_tokens(entry: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    tokens.extend(split_name_terms(str(entry.get("name", ""))))
    for alias in entry.get("aliases", []) or []:
        tokens.extend(split_name_terms(str(alias)))

    cleaned: list[str] = []
    for token in tokens:
        if not token:
            continue
        # Single-character tokens are usually too noisy. Keep 禄/祿 because the
        # dedicated entry is deliberately about this short technical term.
        if len(token) < 2 and token not in {"禄", "祿"}:
            continue
        if token not in cleaned:
            cleaned.append(token)
    cleaned.sort(key=lambda item: (-len(item), item))
    return cleaned


def parse_quote_id(line: str) -> str | None:
    if not line.lstrip().startswith("|"):
        return None
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) < 2:
        return None
    candidate = cells[0]
    if re.match(r"^[A-Z][A-Z0-9-]*Q\d+", candidate):
        return candidate
    if re.match(r"^[A-Z]+-\d+", candidate):
        return candidate
    return None


def scan_pack(skill_root: Path, pack: str, tokens: list[str]) -> list[dict[str, Any]]:
    pack_dir = skill_root / "references" / "books" / pack
    anchors: list[dict[str, Any]] = []
    if not pack_dir.exists():
        return anchors

    for layer in TRACE_LAYERS:
        path = pack_dir / layer
        if not path.exists():
            continue
        rel = path.relative_to(skill_root)
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                matched = next((token for token in tokens if token in line), None)
                if matched is None:
                    continue
                anchor = {
                    "pack": pack,
                    "layer": layer.removesuffix(".md"),
                    "line_ref": f"{rel}:L{line_no}",
                    "matched_token": matched,
                }
                quote_id = parse_quote_id(line)
                if quote_id:
                    anchor["quote_id"] = quote_id
                anchors.append(anchor)
                if len([a for a in anchors if a["pack"] == pack and a["layer"] == layer.removesuffix(".md")]) >= MAX_ANCHORS_PER_PACK:
                    break
    return anchors


def role_pack_map(profile_doc: dict[str, Any]) -> dict[str, str]:
    roles = profile_doc.get("book_roles", {})
    result: dict[str, str] = {}
    for role_id, role in roles.items():
        pack = role.get("pack") if isinstance(role, dict) else None
        if pack:
            result[role_id] = str(pack)
    return result


def audit(skill_root: Path) -> dict[str, Any]:
    matrices = skill_root / "references" / "matrices"
    name_doc = load_yaml(matrices / "shensha-name-disambiguation.yaml")
    profile_doc = load_yaml(matrices / "shensha-entry-source-profile.yaml")

    entries_by_id = {entry["id"]: entry for entry in name_doc.get("entries", [])}
    profiles = profile_doc.get("entry_source_profiles", {})
    role_packs = role_pack_map(profile_doc)

    if set(entries_by_id) != set(profiles):
        missing_profiles = sorted(set(entries_by_id) - set(profiles))
        orphan_profiles = sorted(set(profiles) - set(entries_by_id))
        raise ValueError(f"profile/name mismatch missing={missing_profiles} orphan={orphan_profiles}")

    output_entries: list[dict[str, Any]] = []
    system_status_counts: Counter[str] = Counter()
    entry_status_counts: Counter[str] = Counter()

    for entry_id in sorted(entries_by_id):
        entry = entries_by_id[entry_id]
        profile = profiles[entry_id]
        tokens = search_tokens(entry)
        systems_out: dict[str, Any] = {}
        entry_system_statuses: list[str] = []

        for system, sys_profile in sorted((profile.get("profiles") or {}).items()):
            first_roles = sys_profile.get("first_line") or []
            support_roles = sys_profile.get("support") or []
            first_packs = [role_packs[role] for role in first_roles if role in role_packs]
            support_packs = [role_packs[role] for role in support_roles if role in role_packs]

            first_anchors: list[dict[str, Any]] = []
            support_anchors: list[dict[str, Any]] = []
            for pack in first_packs:
                first_anchors.extend(scan_pack(skill_root, pack, tokens))
            for pack in support_packs:
                support_anchors.extend(scan_pack(skill_root, pack, tokens))

            has_first_quote = any(anchor["layer"] == "quote-index" for anchor in first_anchors)
            has_any_first = bool(first_anchors)
            has_support_quote = any(anchor["layer"] == "quote-index" for anchor in support_anchors)
            if has_first_quote:
                status = "first_line_quote_index_hit"
            elif has_any_first:
                status = "first_line_layer_hit"
            elif has_support_quote:
                status = "support_quote_index_hit"
            elif support_anchors:
                status = "support_layer_hit"
            else:
                status = "needs_second_pass"

            systems_out[system] = {
                "trace_status": status,
                "first_line_packs": first_packs,
                "support_packs": support_packs,
                "first_line_anchors": first_anchors[:8],
                "support_anchors": support_anchors[:6],
            }
            system_status_counts[status] += 1
            entry_system_statuses.append(status)

        if all(status == "first_line_quote_index_hit" for status in entry_system_statuses):
            entry_status = "all_systems_first_line_quote_index_hit"
        elif any(status == "needs_second_pass" for status in entry_system_statuses):
            entry_status = "has_second_pass_gap"
        elif any(status.endswith("layer_hit") for status in entry_system_statuses):
            entry_status = "has_layer_only_trace"
        else:
            entry_status = "has_quote_trace"
        entry_status_counts[entry_status] += 1

        output_entries.append(
            {
                "id": entry_id,
                "name": entry.get("name"),
                "search_tokens": tokens,
                "entry_trace_status": entry_status,
                "systems": systems_out,
                "acquisition_only": profile.get("acquisition_only") or [],
            }
        )

    return {
        "generated_at": str(date.today()),
        "version": "v0.1",
        "source_status": "generated_from_local_ready_pack_layers",
        "purpose": "Mechanical trace audit for shensha entries. Anchors prove local source availability, not final interpretation.",
        "inputs": [
            "references/matrices/shensha-name-disambiguation.yaml",
            "references/matrices/shensha-entry-source-profile.yaml",
            "references/books/*/*/{quote-index,terms,rules}.md",
        ],
        "policy": {
            "use_ready_pack_layers_only": True,
            "do_not_use_acquisition_only_sources": True,
            "quote_index_hit_preferred": True,
            "layer_hit_requires_human_second_pass_before_rule_promotion": True,
        },
        "coverage_summary": {
            "entry_count": len(output_entries),
            "entry_status_counts": dict(entry_status_counts),
            "system_status_counts": dict(system_status_counts),
        },
        "entries": output_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--write-yaml", type=Path, help="Optional output YAML path, relative to skill root if not absolute.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of YAML.")
    args = parser.parse_args()

    result = audit(args.skill_root)
    if args.write_yaml:
        output_path = args.write_yaml
        if not output_path.is_absolute():
            output_path = args.skill_root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(result, handle, allow_unicode=True, sort_keys=False, width=120)

    if args.json:
        print(json.dumps(result["coverage_summary"], ensure_ascii=False, indent=2))
    else:
        print(yaml.safe_dump(result["coverage_summary"], allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
