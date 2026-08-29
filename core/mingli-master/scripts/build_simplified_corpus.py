#!/usr/bin/env python3
"""Rebuild the local simplified corpus derivative and citation verdict audit.

The 54 research fulltexts remain read-only inputs.  Complete simplified
fulltexts and the 101,701-passage search index are written only to the explicit
output root; the repository carries the builder, provenance, distilled quote
indexes, and migration Golden rather than redistributing the research corpus.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from simplified_canonical import (
    canonical_metadata,
    canonicalize,
    passage_is_accepted,
)


ROOT = Path(__file__).resolve().parents[1]
BOOKS_ROOT = ROOT / "references/books"
EVIDENCE_INDEX = ROOT / "references/index/evidence-rules.jsonl"
LEGACY_GOLDEN = (
    ROOT
    / "references/regression/ming66-legacy-citation-verdicts-v1.jsonl"
)
MIGRATION_GOLDEN = (
    ROOT
    / "references/regression/ming66-citation-verdict-migration-v1.jsonl"
)

EXPECTED_FULLTEXTS = 54
EXPECTED_PASSAGES = 101_701
EXPECTED_QUOTE_INDEXES = 55
EXPECTED_QUOTE_CITATIONS = 18_940
EXPECTED_EVIDENCE_CITATIONS = 478
NGRAM = 3
PARTIAL_THRESHOLD = 0.55

_PUNCT = re.compile(r"[\s，。、；：！？「」『』（）()《》〈〉…—·,.;:!?\"'\[\]【】]+")
_LINE_RE = re.compile(r"fulltext\.md\s*[:#]?\s*L([1-9][0-9]*)(?:\s*-\s*L?([1-9][0-9]*))?")
_BLOCK_RE = re.compile(r"^###\s+([A-Z][A-Z0-9~-]*(?:-Q?[A-Z0-9~]+)+)\s*$", re.M)
_FIELD_QUOTE_RE = re.compile(
    r"^-\s+(?:\*\*)?exact_quote(?:\*\*)?\s*:\s*`([^`]+)`\s*$",
    re.M,
)


@dataclass(frozen=True)
class Passage:
    pack: str
    path: str
    line: int
    text: str
    norm: str


@dataclass(frozen=True)
class RegisteredCitation:
    registry: str
    pack: str
    local_id: str
    quote: str
    source_path: str
    line_start: int | None
    line_end: int | None
    source_location: str

    @property
    def citation_id(self) -> str:
        return f"{self.registry}:{self.pack}:{self.local_id}"


@dataclass(frozen=True)
class CitationVerdict:
    citation_id: str
    status: str
    anchor: str | None
    containment: float


def normalize(text: str, converter: Callable[[str], str] = canonicalize) -> str:
    return _PUNCT.sub("", converter(text))


def ngrams(text: str, n: int = NGRAM) -> set[str]:
    if len(text) < n:
        return {text} if text else set()
    return {text[index : index + n] for index in range(len(text) - n + 1)}


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _quote_column(headers: list[str]) -> int | None:
    for index, raw in enumerate(headers):
        header = raw.casefold().replace(" `", "").replace("`", "")
        if "quote" in header or "excerpt" in header or "短引" in header:
            return index
    return None


def _line_range(value: str) -> tuple[int | None, int | None]:
    match = _LINE_RE.search(value)
    if match is None:
        return None, None
    start = int(match.group(1))
    return start, int(match.group(2) or start)


def parse_quote_index(text: str, *, pack: str) -> list[RegisteredCitation]:
    """Parse every registered quote from the three repository index shapes."""

    found: dict[str, RegisteredCitation] = {}
    headers: list[str] | None = None
    quote_column: int | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if not cells:
            continue
        first = cells[0].casefold()
        if first in {"id", "qid", "quote_id"}:
            headers = cells
            quote_column = _quote_column(cells)
            continue
        if headers is None or quote_column is None or len(cells) <= quote_column:
            continue
        if all(cell and set(cell) <= {"-", ":"} for cell in cells):
            continue
        local_id = cells[0].strip("`")
        if not re.fullmatch(r"[A-Z][A-Z0-9~-]*(?:-[A-Z0-9~]+)+", local_id):
            continue
        quote = cells[quote_column].strip()
        if quote.startswith("`") and quote.endswith("`") and len(quote) >= 2:
            quote = quote[1:-1]
        start, end = _line_range(" ".join(cells))
        found[local_id] = RegisteredCitation(
            registry="quote-index",
            pack=pack,
            local_id=local_id,
            quote=quote,
            source_path=f"references/fulltext/{pack}/fulltext.md",
            line_start=start,
            line_end=end,
            source_location="research_tree",
        )

    blocks = list(_BLOCK_RE.finditer(text))
    for index, match in enumerate(blocks):
        end_offset = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
        block = text[match.end() : end_offset]
        quote_match = _FIELD_QUOTE_RE.search(block)
        if quote_match is None:
            continue
        start, end = _line_range(block)
        local_id = match.group(1)
        found[local_id] = RegisteredCitation(
            registry="quote-index",
            pack=pack,
            local_id=local_id,
            quote=quote_match.group(1),
            source_path=f"references/fulltext/{pack}/fulltext.md",
            line_start=start,
            line_end=end,
            source_location="research_tree",
        )

    return [found[key] for key in sorted(found)]


def collect_quote_citations(
    books_root: Path = BOOKS_ROOT,
) -> tuple[list[RegisteredCitation], int]:
    citations: list[RegisteredCitation] = []
    paths = sorted(books_root.glob("*/*/quote-index.md"))
    for path in paths:
        pack = f"{path.parent.parent.name}/{path.parent.name}"
        text = path.read_text(encoding="utf-8")
        if text != canonicalize(text):
            raise ValueError(f"quote index is not simplified canonical: {path}")
        citations.extend(parse_quote_index(text, pack=pack))
    ids = [item.citation_id for item in citations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate registered quote citation id")
    return citations, len(paths)


def collect_evidence_citations(
    path: Path = EVIDENCE_INDEX,
) -> list[RegisteredCitation]:
    citations: list[RegisteredCitation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for field in ("source_title", "chapter", "title", "quote"):
            value = str(record.get(field) or "")
            if value != canonicalize(value):
                raise ValueError(
                    f"evidence index is not simplified canonical: "
                    f"{record.get('rule_id')} {field}"
                )
        if any(
            str(topic) != canonicalize(str(topic))
            for topic in record.get("topics") or ()
        ):
            raise ValueError(
                f"evidence index topics are not simplified canonical: "
                f"{record.get('rule_id')}"
            )
        pack = str(record["source_pack"])
        for index, source in enumerate(record.get("classical_sources") or (), start=1):
            source_quote = str(source["verbatim_quote"])
            if source_quote != canonicalize(source_quote):
                raise ValueError(
                    "classical evidence quote is not simplified canonical: "
                    f"{record.get('rule_id')}"
                )
            raw_anchor = str(source.get("anchor") or "")
            start, end = _line_range(raw_anchor)
            citations.append(
                RegisteredCitation(
                    registry="evidence-rule",
                    pack=pack,
                    local_id=f"{record['rule_id']}@{index:03d}",
                    quote=source_quote,
                    source_path=str(source["path"]),
                    line_start=start,
                    line_end=end,
                    source_location=str(source.get("location") or "research_tree"),
                )
            )
    ids = [item.citation_id for item in citations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate registered evidence citation id")
    return citations


def _fulltext_paths(root: Path) -> list[Path]:
    fulltext_root = root / "references/fulltext"
    if not fulltext_root.is_dir():
        raise ValueError(f"missing research fulltext root: {fulltext_root}")
    return sorted(fulltext_root.rglob("fulltext.md"))


def collect_passages(
    root: Path,
    converter: Callable[[str], str] = canonicalize,
) -> list[Passage]:
    passages: list[Passage] = []
    for path in _fulltext_paths(root):
        pack = f"{path.parent.parent.name}/{path.parent.name}"
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="strict").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if not stripped or stripped.startswith(("- source_url:", "```")):
                continue
            text = converter(stripped)
            norm = normalize(stripped.lstrip("#>- "), converter)
            if not passage_is_accepted(stripped, norm):
                continue
            passages.append(
                Passage(
                    pack=pack,
                    path=relative,
                    line=number,
                    text=text,
                    norm=norm,
                )
            )
    return passages


def render_passage_index(passages: Iterable[Passage]) -> str:
    return "".join(
        json.dumps(
            asdict(passage),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for passage in passages
    )


def _source_text(
    citation: RegisteredCitation,
    *,
    research_root: Path,
    release_root: Path,
) -> tuple[str, str] | None:
    base = release_root if citation.source_location == "release_tree" else research_root
    path = base / citation.source_path
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if citation.line_start is None:
        return "\n".join(lines), citation.source_path
    end = citation.line_end or citation.line_start
    if citation.line_start < 1 or end > len(lines):
        return None
    anchor = f"{citation.source_path}#L{citation.line_start}"
    if end != citation.line_start:
        anchor += f"-L{end}"
    return "\n".join(lines[citation.line_start - 1 : end]), anchor


def verify_citation(
    citation: RegisteredCitation,
    *,
    passages_by_pack: dict[str, list[Passage]],
    research_root: Path,
    release_root: Path = ROOT,
    converter: Callable[[str], str] = canonicalize,
) -> CitationVerdict:
    target = normalize(citation.quote, converter)
    if len(target) < NGRAM:
        return CitationVerdict(citation.citation_id, "not_found", None, 0.0)

    source = _source_text(
        citation,
        research_root=research_root,
        release_root=release_root,
    )
    candidates: list[tuple[str, str]] = []
    if source is not None and citation.line_start is not None:
        text, anchor = source
        candidates.append((normalize(text, converter), anchor))
    elif citation.source_location == "release_tree" and source is not None:
        text, anchor = source
        candidates.append((normalize(text, converter), anchor))
    else:
        candidates.extend(
            (passage.norm, f"{passage.path}#L{passage.line}")
            for passage in passages_by_pack.get(citation.pack, ())
        )

    exact = [(norm, anchor) for norm, anchor in candidates if target in norm]
    if exact:
        return CitationVerdict(citation.citation_id, "verified_exact", exact[0][1], 1.0)

    target_grams = ngrams(target)
    scored = [
        (len(target_grams & ngrams(norm)) / len(target_grams), anchor)
        for norm, anchor in candidates
        if target_grams & ngrams(norm)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    best, anchor = scored[0] if scored else (0.0, None)
    return CitationVerdict(
        citation.citation_id,
        "partial_match" if best >= PARTIAL_THRESHOLD else "not_found",
        anchor,
        round(best, 3),
    )


def verify_registered_citations(
    citations: Iterable[RegisteredCitation],
    *,
    passages: Iterable[Passage],
    research_root: Path,
    release_root: Path = ROOT,
    converter: Callable[[str], str] = canonicalize,
) -> list[CitationVerdict]:
    by_pack: dict[str, list[Passage]] = defaultdict(list)
    for passage in passages:
        by_pack[passage.pack].append(passage)
    return [
        verify_citation(
            citation,
            passages_by_pack=by_pack,
            research_root=research_root,
            release_root=release_root,
            converter=converter,
        )
        for citation in citations
    ]


def canonicalize_quote_indexes(books_root: Path = BOOKS_ROOT) -> int:
    paths = sorted(books_root.glob("*/*/quote-index.md"))
    for path in paths:
        before = path.read_text(encoding="utf-8")
        after = canonicalize(before)
        if after != before:
            path.write_text(after, encoding="utf-8")
    return len(paths)


def _load_legacy(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    metadata: dict[str, Any] | None = None
    verdicts: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("record_type") == "metadata":
            metadata = record
            continue
        citation_id = str(record.get("citation_id") or "")
        if not citation_id or citation_id in verdicts:
            raise ValueError("invalid legacy citation verdict Golden")
        verdicts[citation_id] = record
    if metadata is None or metadata.get("schema_version") != "mingli-legacy-citation-verdicts-v1":
        raise ValueError("legacy citation verdict metadata is missing")
    return metadata, verdicts


def render_migration_audit(
    citations: list[RegisteredCitation],
    verdicts: list[CitationVerdict],
    *,
    legacy_path: Path,
) -> tuple[str, dict[str, Any]]:
    legacy_meta, legacy = _load_legacy(legacy_path)
    current = {item.citation_id: item for item in verdicts}
    ids = [item.citation_id for item in citations]
    if set(ids) != set(legacy) or set(ids) != set(current):
        raise ValueError("registered citation set drifted from the legacy Golden")

    rows: list[dict[str, Any]] = []
    downgrades: list[str] = []
    changes = 0
    for citation in sorted(citations, key=lambda item: item.citation_id):
        old = legacy[citation.citation_id]
        new = current[citation.citation_id]
        changed = old["status"] != new.status
        if changed:
            changes += 1
        if old["status"] == "verified_exact" and new.status != "verified_exact":
            downgrades.append(citation.citation_id)
        rows.append(
            {
                "citation_id": citation.citation_id,
                "registry": citation.registry,
                "pack": citation.pack,
                "old_status": old["status"],
                "new_status": new.status,
                "status_changed": changed,
                "old_anchor": old.get("anchor"),
                "new_anchor": new.anchor,
            }
        )
    metadata = {
        "record_type": "metadata",
        "schema_version": "mingli-citation-verdict-migration-v1",
        "canonical": canonical_metadata(),
        "legacy_comparator": legacy_meta["comparator"],
        "citation_count": len(rows),
        "status_changes": changes,
        "exact_downgrades": downgrades,
    }
    rendered = json.dumps(
        metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n"
    rendered += "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    )
    return rendered, metadata


def _write_fulltext_derivatives(research_root: Path, output_root: Path) -> None:
    for source in _fulltext_paths(research_root):
        relative = source.relative_to(research_root)
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            canonicalize(source.read_text(encoding="utf-8", errors="strict")),
            encoding="utf-8",
        )


def _validate_output_root(research_root: Path, output_root: Path) -> None:
    research_root = research_root.resolve()
    output_root = output_root.resolve()
    if output_root.is_relative_to(research_root):
        raise ValueError("output root must not overwrite the read-only research tree")
    if output_root.exists() and (
        not output_root.is_dir() or any(output_root.iterdir())
    ):
        raise ValueError("output root must be absent or empty")


def rebuild(
    *,
    research_root: Path,
    output_root: Path,
    legacy_path: Path = LEGACY_GOLDEN,
    write_quote_indexes: bool = False,
    migration_golden: Path | None = None,
    enforce_release_counts: bool = True,
) -> dict[str, Any]:
    _validate_output_root(research_root, output_root)
    if write_quote_indexes:
        canonicalize_quote_indexes()

    fulltexts = _fulltext_paths(research_root)
    passages = collect_passages(research_root)
    quote_citations, quote_indexes = collect_quote_citations()
    evidence_citations = collect_evidence_citations()
    citations = [*quote_citations, *evidence_citations]

    if enforce_release_counts:
        actual = {
            "fulltexts": len(fulltexts),
            "passages": len(passages),
            "quote_indexes": quote_indexes,
            "quote_citations": len(quote_citations),
            "evidence_citations": len(evidence_citations),
        }
        expected = {
            "fulltexts": EXPECTED_FULLTEXTS,
            "passages": EXPECTED_PASSAGES,
            "quote_indexes": EXPECTED_QUOTE_INDEXES,
            "quote_citations": EXPECTED_QUOTE_CITATIONS,
            "evidence_citations": EXPECTED_EVIDENCE_CITATIONS,
        }
        if actual != expected:
            raise ValueError(f"release 5.1 corpus count drift: {actual} != {expected}")

    verdicts = verify_registered_citations(
        citations,
        passages=passages,
        research_root=research_root,
    )
    migration, migration_meta = render_migration_audit(
        citations,
        verdicts,
        legacy_path=legacy_path,
    )
    if migration_meta["exact_downgrades"]:
        raise ValueError(
            "registered citation exact downgrade requires a project decision: "
            + migration_meta["exact_downgrades"][0]
        )

    _write_fulltext_derivatives(research_root, output_root)
    index_root = output_root / "references/index"
    index_root.mkdir(parents=True, exist_ok=True)
    (index_root / "classical-passages-simplified-v1.jsonl").write_text(
        render_passage_index(passages),
        encoding="utf-8",
    )
    (index_root / "citation-verdict-migration-v1.jsonl").write_text(
        migration,
        encoding="utf-8",
    )
    summary = {
        "schema_version": "mingli-simplified-corpus-build-v1",
        "canonical": canonical_metadata(),
        "counts": {
            "fulltexts": len(fulltexts),
            "accepted_passages": len(passages),
            "quote_indexes": quote_indexes,
            "quote_index_citations": len(quote_citations),
            "evidence_index_citations": len(evidence_citations),
            "registered_citations": len(citations),
            "verdict_changes": migration_meta["status_changes"],
            "exact_downgrades": len(migration_meta["exact_downgrades"]),
        },
        "raw_policy": "read_only_local_evidence",
        "derived_policy": "explicit_output_root_not_release_payload",
    }
    (index_root / "simplified-build-manifest-v1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if migration_golden is not None:
        migration_golden.parent.mkdir(parents=True, exist_ok=True)
        migration_golden.write_text(migration, encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--legacy-verdicts", type=Path, default=LEGACY_GOLDEN)
    parser.add_argument("--write-quote-indexes", action="store_true")
    parser.add_argument("--write-migration-golden", action="store_true")
    args = parser.parse_args(argv)

    summary = rebuild(
        research_root=args.research_root.resolve(),
        output_root=args.output_root.resolve(),
        legacy_path=args.legacy_verdicts.resolve(),
        write_quote_indexes=args.write_quote_indexes,
        migration_golden=MIGRATION_GOLDEN if args.write_migration_golden else None,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
