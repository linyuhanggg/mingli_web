#!/usr/bin/env python3
"""Validate and regenerate the repository-local reference-pack catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "references" / "catalog"
YAML_PATH = CATALOG_DIR / "D2_READY_REFERENCE_PACKS.yaml"
JSON_PATH = CATALOG_DIR / "catalog.json"
MARKDOWN_PATH = CATALOG_DIR / "D2_READY_REFERENCE_PACKS.md"
REQUIRED_PACK_FILES = (
    "index.md",
    "chapter-map.md",
    "terms.md",
    "rules.md",
    "procedures.md",
    "quote-index.md",
    "validation.md",
)
VERIFIED_RELEASE_EXCERPTS = {
    ("san-shi", "qimen-faqiao"): {
        "path": "references/source-excerpts/qimen-faqiao-chaibu-v1.md",
        "policy": "verified_excerpt_distributed",
        "required_for_runtime": True,
        "redistribution_status": (
            "ancient_text_public_domain_with_mit_transcription_provenance"
        ),
        "source_provenance_status": "fixed_commit_hash_and_scan_crosscheck",
        "load_policy": (
            "load index.md first; load rules.md only for calculated QM-P26 or QM-P36"
        ),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_seed() -> dict[str, Any]:
    for path in (YAML_PATH, JSON_PATH):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("ready_reference_packs"), list):
            return payload
    raise ValueError("reference catalog seed is missing or malformed")


def build_catalog(*, require_local_fulltext: bool) -> tuple[dict[str, Any], list[str]]:
    seed = _load_seed()
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for old in seed["ready_reference_packs"]:
        system = str(old.get("system") or "").strip()
        slug = str(old.get("slug") or "").strip()
        title = str(old.get("title") or "").strip()
        key = (system, slug)
        if not system or not slug or not title:
            errors.append(f"catalog entry is missing system/slug/title: {old!r}")
            continue
        if key in seen:
            errors.append(f"duplicate catalog entry: {system}/{slug}")
            continue
        seen.add(key)

        pack_dir = ROOT / "references" / "books" / system / slug
        missing = [name for name in REQUIRED_PACK_FILES if not (pack_dir / name).is_file()]
        if missing:
            errors.append(f"{system}/{slug}: missing pack files: {', '.join(missing)}")

        index_path = pack_dir / "index.md"
        release_excerpt = VERIFIED_RELEASE_EXCERPTS.get(key)
        if release_excerpt:
            fulltext_path = ROOT / str(release_excerpt["path"])
        else:
            fulltext_path = ROOT / "references" / "fulltext" / system / slug / "fulltext.md"
        source_manifest_path = pack_dir / "source-manifest.yaml"
        source_anchor = str(old.get("source_anchor_url") or "").strip()
        if not source_anchor.startswith(("https://", "http://")):
            errors.append(f"{system}/{slug}: missing stable source anchor URL")

        recorded_fulltext_sha = str(old.get("local_fulltext_sha256") or "").strip()
        if fulltext_path.is_file():
            actual_fulltext_sha = _sha256(fulltext_path)
            if recorded_fulltext_sha and recorded_fulltext_sha != actual_fulltext_sha:
                errors.append(f"{system}/{slug}: local fulltext SHA-256 mismatch")
            recorded_fulltext_sha = actual_fulltext_sha
        elif release_excerpt:
            errors.append(f"{system}/{slug}: verified release excerpt is unavailable")
        elif require_local_fulltext:
            errors.append(f"{system}/{slug}: local-only fulltext is unavailable")
        elif not recorded_fulltext_sha:
            errors.append(f"{system}/{slug}: no recorded local fulltext SHA-256")

        if release_excerpt and old.get("local_fulltext_policy") != release_excerpt["policy"]:
            errors.append(
                f"{system}/{slug}: verified release excerpt policy is not explicitly declared"
            )

        entries.append(
            {
                "system": system,
                "slug": slug,
                "title": title,
                "d2_status": str(old.get("d2_status") or "ready"),
                "source_layer": str(
                    old.get("source_layer") or "primary_or_commentary_see_pack_index"
                ),
                "source_anchor_url": source_anchor,
                "source_risk": str(old.get("source_risk") or "see pack validation"),
                "skill_index_path": _relative(index_path),
                "skill_index_sha256": _sha256(index_path) if index_path.is_file() else "",
                "local_fulltext_path": _relative(fulltext_path),
                "local_fulltext_sha256": recorded_fulltext_sha,
                "local_fulltext_policy": (
                    release_excerpt["policy"]
                    if release_excerpt
                    else "local_only_not_distributed"
                ),
                "local_fulltext_required_for_runtime": (
                    release_excerpt["required_for_runtime"]
                    if release_excerpt
                    else False
                ),
                "redistribution_status": (
                    release_excerpt["redistribution_status"]
                    if release_excerpt
                    else "distilled_pack_only_source_licence_review_pending"
                ),
                "source_provenance_status": (
                    release_excerpt["source_provenance_status"]
                    if release_excerpt
                    else (
                        "pack_manifest_and_catalog"
                        if source_manifest_path.is_file()
                        else "consolidated_catalog"
                    )
                ),
                "source_manifest_path": (
                    _relative(source_manifest_path) if source_manifest_path.is_file() else None
                ),
                "load_policy": (
                    release_excerpt["load_policy"]
                    if release_excerpt
                    else (
                        "load index.md first; load chapter-map/terms/rules/procedures/"
                        "quote-index/validation only as needed"
                    )
                ),
            }
        )

    entries.sort(key=lambda item: (item["system"], item["slug"]))
    blocked = list(seed.get("blocked_or_excluded") or [])
    catalog = {
        "schema_version": "mingli-reference-catalog-v2",
        "generated_at": str(seed.get("generated_at") or date.today().isoformat()),
        "purpose": (
            "Authoritative loader and consolidated provenance manifest for the "
            "reference packs distributed with mingli-master."
        ),
        "distribution_policy": {
            "runtime_payload": "distilled_reference_packs_plus_declared_verified_excerpts",
            "fulltext_payload": "local_only_except_narrow_verified_release_excerpts",
            "reason": (
                "source-page and transcription licences are not uniformly cleared; "
                "record anchors and hashes without redistributing complete transcriptions, "
                "except explicitly allowlisted public-domain excerpts with fixed provenance"
            ),
        },
        "validation": {
            "reference_pack_files": f"PASS {len(entries)}/{len(entries)}" if not errors else "FAIL",
            "source_provenance_entries": f"PASS {len(entries)}/{len(entries)}",
            "fulltext_checksums_recorded": (
                f"PASS {sum(bool(item['local_fulltext_sha256']) for item in entries)}/{len(entries)}"
            ),
        },
        "ready_count": len(entries),
        "ready_reference_packs": entries,
        "blocked_or_excluded_count": len(blocked),
        "blocked_or_excluded": blocked,
    }
    return catalog, errors


def _markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# D2 Ready Reference Packs",
        "",
        "> Generated from the repository's actual `references/books/` layout. This is both",
        "> the loader manifest and the consolidated source-provenance manifest.",
        "",
        "## Distribution Boundary",
        "",
        "- Releases contain distilled reference packs, source anchors, and SHA-256 records.",
        "- Complete transcriptions under `references/fulltext/` stay local and are not committed.",
        "- Narrow verified release excerpts are allowlisted individually with fixed provenance and hashes.",
        "- A `ready` pack means its distilled evidence structure passed local checks; it does not",
        "  claim that every source webpage grants redistribution rights.",
        "",
        "## Validation",
        "",
    ]
    for key, value in catalog["validation"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Load Policy",
            "",
            "- Load `index.md` first for the selected pack.",
            "- Load detailed pack files only when the answer needs that evidence layer.",
            "- Never load blocked entries as first-line references.",
            "",
        ]
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in catalog["ready_reference_packs"]:
        grouped[entry["system"]].append(entry)
    for system in sorted(grouped):
        lines.extend(
            [
                f"## {system}",
                "",
                "| slug | title | index | local fulltext SHA-256 | source anchor |",
                "|---|---|---|---|---|",
            ]
        )
        for entry in grouped[system]:
            lines.append(
                "| `{slug}` | {title} | `{index}` | `{sha}` | {anchor} |".format(
                    slug=entry["slug"],
                    title=str(entry["title"]).replace("|", "\\|"),
                    index=entry["skill_index_path"],
                    sha=entry["local_fulltext_sha256"],
                    anchor=entry["source_anchor_url"],
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Blocked Or Excluded",
            "",
            "| slug | title | raw | normalized | reason |",
            "|---|---|---|---|---|",
        ]
    )
    for entry in catalog["blocked_or_excluded"]:
        lines.append(
            "| `{slug}` | {title} | {raw} | {normalized} | {reason} |".format(
                slug=entry.get("slug", ""),
                title=str(entry.get("title", "")).replace("|", "\\|"),
                raw=entry.get(
                    "raw_source_status",
                    entry.get("raw_status", entry.get("raw", "")),
                ),
                normalized=entry.get("normalized_status", entry.get("normalized", "")),
                reason=str(entry.get("reason", "")).replace("|", "\\|"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _rendered_outputs(catalog: dict[str, Any]) -> dict[Path, str]:
    return {
        YAML_PATH: yaml.safe_dump(
            catalog,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        ),
        JSON_PATH: json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        MARKDOWN_PATH: _markdown(catalog),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="regenerate JSON/YAML/Markdown outputs")
    parser.add_argument(
        "--require-local-fulltext",
        action="store_true",
        help="fail when a local-only fulltext is absent",
    )
    args = parser.parse_args()

    catalog, errors = build_catalog(require_local_fulltext=args.require_local_fulltext)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    rendered = _rendered_outputs(catalog)
    if args.write:
        for path, content in rendered.items():
            path.write_text(content, encoding="utf-8")
    else:
        drifted = [
            _relative(path)
            for path, content in rendered.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        if drifted:
            for path in drifted:
                print(f"ERROR: generated catalog drift: {path}")
            return 1
    print(
        f"PASS packs={catalog['ready_count']} provenance={catalog['ready_count']} "
        f"blocked={catalog['blocked_or_excluded_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
