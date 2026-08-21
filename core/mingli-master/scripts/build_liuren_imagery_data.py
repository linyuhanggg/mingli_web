#!/usr/bin/env python3
"""Build the compact runtime imagery table from a local-only full transcription."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from liuren_current_state import (
    GENERAL_ALIASES,
    GENERAL_FALLBACKS,
    SOURCE_GENERAL_NAMES,
    _activity_candidates,
    _line_number,
    _simplify,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references" / "fulltext" / "san-shi" / "liuren-miben" / "fulltext.md"
OUTPUT = ROOT / "scripts" / "data" / "liuren-miben-general-imagery.json"


def build() -> dict[str, object]:
    raw = SOURCE.read_bytes()
    fulltext = raw.decode("utf-8")
    start_marker = "## 卷之二　十二天將所主"
    end_marker = "## 卷之三"
    if start_marker not in fulltext or end_marker not in fulltext:
        raise ValueError("《大六壬秘本》卷二天将表边界缺失")
    start = fulltext.index(start_marker)
    end = fulltext.index(end_marker, start)
    section = fulltext[start:end]
    heading_re = re.compile(
        r"^(" + "|".join(SOURCE_GENERAL_NAMES) + r")者",
        re.MULTILINE,
    )
    headings = list(heading_re.finditer(section))
    if len(headings) != 12:
        raise ValueError("《大六壬秘本》卷二天将条目不足十二将")

    generals: dict[str, dict[str, object]] = {}
    branch_re = re.compile(
        r"加([子丑寅卯辰巳午未申酉戌亥醜])(.*?)(?=，?\s*加[子丑寅卯辰巳午未申酉戌亥醜]|。|\n\n|$)",
        re.DOTALL,
    )
    for index, heading in enumerate(headings):
        block_end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        block = section[heading.start():block_end]
        general = GENERAL_ALIASES[heading.group(1)]
        base_match = re.search(r"其將主(.*?)(?:等事|。)", block, re.DOTALL)
        base_text = re.sub(r"\s+", "", base_match.group(1)) if base_match else ""
        entries: dict[str, dict[str, object]] = {}
        for match in branch_re.finditer(block):
            branch = _simplify(match.group(1))
            source_text = re.sub(r"\s+", "", match.group(2)).strip("，。")
            absolute_offset = start + heading.start() + match.start()
            entries[branch] = {
                "source_text": source_text,
                "activity_candidates": _activity_candidates(source_text, general),
                "source_anchor": (
                    "references/fulltext/san-shi/liuren-miben/fulltext.md:"
                    f"L{_line_number(fulltext, absolute_offset)}"
                ),
            }
        if len(entries) < 9:
            raise ValueError(f"《大六壬秘本》{general}所临条目异常不足")
        generals[general] = {
            "base_text": base_text,
            "base_activity": GENERAL_FALLBACKS[general],
            "by_branch": entries,
        }

    return {
        "schema_version": "liuren-miben-general-imagery-v1",
        "source": {
            "path": "references/fulltext/san-shi/liuren-miben/fulltext.md",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "pack": "san-shi/liuren-miben",
            "rule_id": "LM-R01",
            "distribution": "structured_short_excerpts_only",
        },
        "generals": generals,
    }


def main() -> int:
    payload = build()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
