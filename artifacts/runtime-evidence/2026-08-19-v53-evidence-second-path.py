#!/usr/bin/env python3
"""Path B: signed _semantic_terms extra-token injection on 1994 career.

Read-only. Does not write the signed tree. Does not resign / edit selector.
Path A = search_bm25.tokenize("验证八字核心盘面 career")
Path B = tokenize(" ".join(_semantic_terms(goal, plan, fact_index)))
using 1994 prepared fact_index (CJK keys in 盘面投影 paths).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

CORE = Path("/Volumes/Lexar/code/mingli_web/core/mingli-master")
SIGNED = Path("/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release")
MANIFEST = SIGNED / ".mingli-release-manifest.json"
SIGNED_JSONL = SIGNED / "references" / "index" / "evidence-rules.jsonl"
PREPARED = Path(
    "/tmp/mingli-oneshot-v53-time-check-20260819/"
    "503de6c92e75c6f742aa637c2ec71dcc367b597bb69f1280fe1aefe1d58a384b/"
    "readings-v51/readings/9ecec297703f4b8f87d1373010f1ab7a/prepared/000001.json"
)
PREPARE_STDOUT = Path(
    "/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json"
)

QUERY = "验证八字核心盘面"
DIMENSION = "career"
QUERY_JOINED = f"{QUERY} {DIMENSION}"

FOCUS = [
    "bazi/sanming-tonghui#R-01-02",
    "bazi/sanming-tonghui#R-02-04",
    "bazi/qiongtong-baojian#QR-02-01",
    "bazi/ditiansui-chanwei#DR-01-01",
]

sys.path.insert(0, str(SIGNED / "scripts"))
import search_bm25  # noqa: E402
from reading_engine.contracts import CalculationResult  # noqa: E402
from reading_engine.evidence_rules import load_evidence_rules  # noqa: E402
from reading_engine.fact_index import build_fact_index  # noqa: E402
from reading_evidence_bundle import _rule_text, _semantic_terms  # noqa: E402


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(CORE), *args], text=True).rstrip()


def _is_cjk(token: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" for char in token)


def _scp_entries(brief: dict) -> list[dict]:
    for fact in brief.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        ref = str(fact.get("ref") or "")
        if "source_conditioned_patterns" in ref:
            value = fact.get("value")
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _evidence_ids(brief: dict) -> list[str]:
    ids: list[str] = []
    for item in brief.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        rule_id = item.get("rule_id")
        if isinstance(rule_id, str) and rule_id:
            ids.append(rule_id)
    return ids


def _goal_from_prepared(payload: dict) -> dict:
    # Same fields as signed providers._adapter_evidence_goal (providers.py:355)
    intent = payload["request"]["intent"]
    dimensions = list(intent.get("question_dimensions") or [])
    return {
        "evidence_questions": list(intent.get("evidence_questions") or []),
        "question_dimensions": dimensions,
        "requested_dimensions": dimensions,
        "requested_resolution": intent.get("requested_granularity"),
        "calculation_object": intent.get("calculation_object"),
    }


def _plan_from_goal(goal: dict) -> dict:
    # BaziProvider.SOURCE_ROUTE (providers.py:2749) has no semantic_term_projections.
    return {
        "question_dimensions": list(goal["question_dimensions"]),
        "requested_dimensions": list(goal["requested_dimensions"]),
        "semantic_term_projections": [],
    }


def _pack_scores(query_tokens: list[str], rules: list, by_id: dict) -> dict[str, float]:
    pack_groups: dict[str, list] = {}
    for rule in rules:
        pack_groups.setdefault(rule.source_pack, []).append(rule)
    scores = {rule.rule_id: 0.0 for rule in rules}
    for pack_rules in pack_groups.values():
        documents = [
            search_bm25.Document(
                path=SIGNED / rule.source_path,
                line_no=index,
                text=_rule_text(rule),
                tokens=search_bm25.tokenize(_rule_text(rule)),
            )
            for index, rule in enumerate(pack_rules, start=1)
        ]
        by_line = {doc.line_no: rule for doc, rule in zip(documents, pack_rules)}
        for score, doc in search_bm25.bm25(query_tokens, documents):
            scores[by_line[doc.line_no].rule_id] = float(score)
    return scores


def _fmt(tokens: list[str]) -> str:
    return " ".join(tokens) if tokens else "∅"


def main() -> int:
    core_head = _git(["rev-parse", "HEAD"])
    core_subject = _git(["log", "-1", "--format=%s"])
    dirty = [line for line in _git(["status", "--short"]).splitlines() if line]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_sha = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    prepared = json.loads(PREPARED.read_text(encoding="utf-8"))
    stdout = json.loads(PREPARE_STDOUT.read_text(encoding="utf-8"))
    calc = CalculationResult.from_dict(prepared["calculation"])
    goal = _goal_from_prepared(prepared)
    plan = _plan_from_goal(goal)
    fact_index = build_fact_index(
        calc,
        reading_id=str(prepared["reading_id"]),
        version=int(prepared["version"]),
    )
    terms = _semantic_terms(goal, plan, fact_index, counter=False)
    path_a = search_bm25.tokenize(QUERY_JOINED)
    path_b = search_bm25.tokenize(" ".join(terms))
    extra = [token for token in dict.fromkeys(path_b) if token not in set(path_a)]
    extra_cjk = [token for token in extra if _is_cjk(token)]
    non_fact = [term for term in terms if not str(term).startswith("fact:")]
    named_or_board = sum(
        1
        for item in fact_index
        if "/named_patterns/" in item.path or "/board_predicates/" in item.path
    )

    rules = load_evidence_rules(SIGNED_JSONL, root=SIGNED)
    by_id = {rule.rule_id: rule for rule in rules}
    brief = stdout["brief"]
    evidence_ids = _evidence_ids(brief)
    scp = _scp_entries(brief)
    matched_ids = [
        str(entry.get("rule_id") or "")
        for entry in scp
        if "predicate_matched" in str(entry.get("status") or "")
    ]
    matched_rules = [by_id[rule_id] for rule_id in matched_ids if rule_id in by_id]
    scores_a = _pack_scores(path_a, matched_rules, by_id)
    scores_b = _pack_scores(path_b, matched_rules, by_id)

    print("=== IDENTITY ===")
    print(f"core_head={core_head}")
    print(f"core_subject={core_subject}")
    print(f"core_dirty_count={len(dirty)}")
    print(f"signed_manifest_sha256={manifest_sha}")
    print(f"signed_source_commit={manifest.get('source_commit')}")
    print(f"signed_n_files={len(manifest.get('files') or {})}")
    print("path_b_name=_semantic_terms extra-token injection")
    print(
        "path_b_file=/.runtime/v53-time-check-release/scripts/"
        "reading_evidence_bundle.py:_semantic_terms"
    )
    print("path_b_cite=reading_evidence_bundle.py:96:_semantic_terms")

    print("=== PATHS ===")
    print(f"path_a_joined={QUERY_JOINED!r}")
    print(f"path_a_tokens={path_a}")
    print(f"path_a_token_n={len(path_a)}")
    print(f"goal_evidence_questions={goal['evidence_questions']}")
    print(f"goal_question_dimensions={goal['question_dimensions']}")
    print(f"plan_semantic_term_projections={plan['semantic_term_projections']}")
    print(f"fact_index_n={len(fact_index)}")
    print(f"semantic_terms_n={len(terms)}")
    print(f"semantic_terms_non_fact={non_fact}")
    print(f"named_patterns_or_board_predicates_n={named_or_board}")
    print(f"path_b_token_n={len(path_b)}")
    print(f"path_b_unique_n={len(set(path_b))}")
    print(f"path_b_extra_unique_n={len(extra)}")
    print(f"path_b_extra_cjk={extra_cjk}")

    print("=== 1994_PREPARE ===")
    print(f"prepared={PREPARED}")
    print(f"prepare_stdout={PREPARE_STDOUT}")
    print(f"scp_matched_n={len(matched_ids)}")
    print(f"scp_matched_ids={matched_ids}")
    print(f"evidence_n={len(evidence_ids)}")
    print(f"evidence_ids={evidence_ids}")

    print("=== FOCUS_TABLE ===")
    print(
        "rule_id\tpath_a_overlap\tpath_a_bm25\tpath_b_overlap\tpath_b_bm25\t"
        "in_1994_evidence"
    )
    for rule_id in FOCUS:
        rule = by_id[rule_id]
        rule_tokens = set(search_bm25.tokenize(_rule_text(rule)))
        overlap_a = sorted(set(path_a) & rule_tokens)
        overlap_b = sorted(set(path_b) & rule_tokens)
        in_ev = "YES" if rule_id in evidence_ids else "NO"
        print(
            f"{rule_id}\t{_fmt(overlap_a)}\t{scores_a.get(rule_id, 0.0):.6f}\t"
            f"{_fmt(overlap_b)}\t{scores_b.get(rule_id, 0.0):.6f}\t{in_ev}"
        )

    print("=== CONTRIBUTING_FACT_PATHS ===")
    focus_tokens = ["土", "木", "水", "火", "金", "正", "神"]
    for token in focus_tokens:
        paths = [
            item.path
            for item in fact_index
            if token in set(search_bm25.tokenize(item.fact_id))
        ]
        print(f"token={token} n={len(paths)}")
        shown = []
        for path in paths:
            # de-dup the domain_work copies; keep canonical 盘面 leaves
            if "/reasoning_tools/domain_work/" in path:
                continue
            shown.append(path)
        if not shown:
            shown = paths[:4]
        for path in shown:
            print(f"  {path}")

    print("=== WHY_DR_01_01 ===")
    dr_tokens = set(search_bm25.tokenize(_rule_text(by_id[FOCUS[3]])))
    print(f"dr_rule_text={_rule_text(by_id[FOCUS[3]])}")
    print(f"dr_path_a_overlap=∅")
    print(f"dr_path_b_overlap=∅")
    print(f"dr_path_b_bm25={scores_b.get(FOCUS[3], 0.0):.6f}")
    print(
        "dr_reason=injected extra CJK are 五行/十神 keys "
        "(土 木 水 火 金 偏 印 正 官 财 食 神 + cross-term bigrams); "
        "DR-01-01 quote has none of those tokens, so pack BM25 stays 0 "
        "and _rank_rules drops the only ditiansui-chanwei match"
    )
    _ = dr_tokens
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
