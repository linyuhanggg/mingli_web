#!/usr/bin/env python3
"""Inspect and search Mingli reference packs bundled with the skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CATALOG = SKILL_ROOT / "references" / "catalog" / "catalog.json"


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def iter_packs(system: str | None = None):
    for item in load_catalog()["ready_reference_packs"]:
        if system and item["system"] != system:
            continue
        yield item


def rel(path: Path) -> str:
    return str(path.relative_to(SKILL_ROOT))


def catalog_fulltext_path(item: dict) -> Path | None:
    relative = item.get("local_fulltext_path")
    if not relative:
        return None
    candidate = (SKILL_ROOT / str(relative)).resolve()
    if not candidate.is_relative_to(SKILL_ROOT):
        raise ValueError("catalog fulltext path escapes the skill root")
    return candidate


def cmd_list(args: argparse.Namespace) -> int:
    for item in iter_packs(args.system):
        print(f"{item['system']}/{item['slug']}\t{item['title']}\t{item['skill_index_path']}")
    return 0


def cmd_blocked(_: argparse.Namespace) -> int:
    for item in load_catalog()["blocked_or_excluded"]:
        print(
            f"{item['system']}/{item['slug']}\t{item['title']}\t"
            f"raw={item['raw_source_status']}\tnorm={item['normalized_status']}\t{item.get('reason','')}"
        )
    return 0


def find_pack(slug_or_path: str) -> dict | None:
    key = slug_or_path.strip()
    for item in iter_packs():
        full = f"{item['system']}/{item['slug']}"
        if key in {item["slug"], full}:
            return item
    return None


def cmd_locate(args: argparse.Namespace) -> int:
    item = find_pack(args.pack)
    if not item:
        raise SystemExit(f"Unknown ready pack: {args.pack}")
    print(f"title: {item['title']}")
    print(f"index: {item['skill_index_path']}")
    fulltext = catalog_fulltext_path(item)
    print(f"fulltext: {rel(fulltext) if fulltext else ''}")
    print("pack_files:")
    pack_dir = SKILL_ROOT / item["skill_index_path"]
    pack_dir = pack_dir.parent
    for path in sorted(pack_dir.glob("*.md")):
        print(f"- {rel(path)}")
    return 0


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def search_file(path: Path, pattern: re.Pattern[str], context: int) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    hits: list[str] = []
    for idx, line in enumerate(lines, start=1):
        if pattern.search(line):
            start = max(1, idx - context)
            end = min(len(lines), idx + context)
            snippet = " / ".join(compact(lines[i - 1]) for i in range(start, end + 1) if lines[i - 1].strip())
            hits.append(f"{rel(path)}:L{idx}: {snippet}")
    return hits


def cmd_search(args: argparse.Namespace) -> int:
    flags = 0 if args.case_sensitive else re.IGNORECASE
    pattern = re.compile(args.query, flags)
    files: list[Path] = []
    packs = [find_pack(args.pack)] if args.pack else list(iter_packs(args.system))
    packs = [p for p in packs if p]
    layers = args.layer or ["index", "terms", "rules", "procedures", "quote-index", "chapter-map"]
    for item in packs:
        pack_dir = (SKILL_ROOT / item["skill_index_path"]).parent
        for layer in layers:
            if layer == "fulltext":
                fulltext = catalog_fulltext_path(item)
                if fulltext:
                    files.append(fulltext)
            else:
                name = "index.md" if layer == "index" else f"{layer}.md"
                files.append(pack_dir / name)

    count = 0
    for path in files:
        for hit in search_file(path, pattern, args.context):
            print(hit)
            count += 1
            if count >= args.limit:
                return 0
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("list", help="List ready reference packs")
    p.add_argument("--system")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("blocked", help="List blocked or excluded manifests")
    p.set_defaults(func=cmd_blocked)

    p = sub.add_parser("locate", help="Show paths for a ready pack")
    p.add_argument("pack", help="slug or system/slug")
    p.set_defaults(func=cmd_locate)

    p = sub.add_parser("search", help="Regex search bundled pack files")
    p.add_argument("query")
    p.add_argument("--system")
    p.add_argument("--pack")
    p.add_argument("--layer", action="append", help="index, terms, rules, procedures, quote-index, chapter-map, fulltext")
    p.add_argument("--context", type=int, default=0)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--case-sensitive", action="store_true")
    p.set_defaults(func=cmd_search)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
