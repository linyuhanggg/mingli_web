#!/usr/bin/env python3
"""BM25-ish search over bundled Mingli reference packs.

This helper is dependency-free on purpose. It is not a replacement for a
production Chinese segmenter, but it gives agents a better first-pass recall
tool than exact regex search when the user only remembers approximate wording.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from simplified_canonical import canonicalize


SKILL_ROOT = Path(__file__).resolve().parents[1]
CATALOG = SKILL_ROOT / "references" / "catalog" / "catalog.json"
DEFAULT_LAYERS = ["index", "terms", "rules", "procedures", "quote-index", "chapter-map"]


@dataclass
class Document:
    path: Path
    line_no: int
    text: str
    tokens: list[str]


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def iter_packs(system: str | None, pack: str | None):
    for item in load_catalog()["ready_reference_packs"]:
        full = f"{item['system']}/{item['slug']}"
        if system and item["system"] != system:
            continue
        if pack and pack not in {item["slug"], full}:
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


def tokenize(text: str) -> list[str]:
    text = canonicalize(text).lower()
    ascii_terms = re.findall(r"[a-z0-9_][a-z0-9_\-]*", text)
    cjk_chars = re.findall(r"[\u3400-\u9fff]", text)
    cjk_bigrams = [cjk_chars[i] + cjk_chars[i + 1] for i in range(len(cjk_chars) - 1)]
    return ascii_terms + cjk_chars + cjk_bigrams


def layer_paths(item: dict, layers: list[str], include_fulltext: bool) -> list[Path]:
    paths: list[Path] = []
    pack_dir = (SKILL_ROOT / item["skill_index_path"]).parent
    for layer in layers:
        name = "index.md" if layer == "index" else f"{layer}.md"
        path = pack_dir / name
        if path.exists():
            paths.append(path)
    if include_fulltext:
        path = catalog_fulltext_path(item)
        if path is None:
            return paths
        if path.exists():
            paths.append(path)
    return paths


def build_docs(args: argparse.Namespace) -> list[Document]:
    docs: list[Document] = []
    layers = args.layer or DEFAULT_LAYERS
    for item in iter_packs(args.system, args.pack):
        for path in layer_paths(item, layers, args.fulltext):
            for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                text = canonicalize(re.sub(r"\s+", " ", line).strip())
                if len(text) < args.min_chars:
                    continue
                tokens = tokenize(text)
                if tokens:
                    docs.append(Document(path=path, line_no=line_no, text=text, tokens=tokens))
    return docs


def bm25(query_tokens: list[str], docs: list[Document], k1: float = 1.5, b: float = 0.75) -> list[tuple[float, Document]]:
    if not docs:
        return []
    doc_count = len(docs)
    avgdl = sum(len(doc.tokens) for doc in docs) / doc_count
    df: dict[str, int] = defaultdict(int)
    for doc in docs:
        for token in set(doc.tokens):
            df[token] += 1

    scored: list[tuple[float, Document]] = []
    query_counts = Counter(query_tokens)
    for doc in docs:
        counts = Counter(doc.tokens)
        doc_len = len(doc.tokens)
        score = 0.0
        for token, query_weight in query_counts.items():
            freq = counts.get(token, 0)
            if not freq:
                continue
            idf = math.log(1 + (doc_count - df[token] + 0.5) / (df[token] + 0.5))
            denom = freq + k1 * (1 - b + b * doc_len / avgdl)
            score += query_weight * idf * ((freq * (k1 + 1)) / denom)
        if score > 0:
            scored.append((score, doc))
    return sorted(
        scored,
        key=lambda item: (
            -item[0],
            str(item[1].path),
            item[1].line_no,
            item[1].text,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--system")
    parser.add_argument("--pack")
    parser.add_argument("--layer", action="append", help="index, terms, rules, procedures, quote-index, chapter-map, validation")
    parser.add_argument("--fulltext", action="store_true", help="Include normalized fulltext lines")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-chars", type=int, default=8)
    args = parser.parse_args()

    query_tokens = tokenize(args.query)
    if not query_tokens:
        raise SystemExit("Query produced no searchable tokens")
    docs = build_docs(args)
    results = bm25(query_tokens, docs)
    for score, doc in results[: args.limit]:
        print(f"{rel(doc.path)}:L{doc.line_no}: score={score:.3f}: {doc.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
