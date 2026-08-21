#!/usr/bin/env python3
"""Career-prepare predicate_matched vs brief.evidence[] on signed V53.

Read-only. Does not write the signed tree.
Row set = on-disk career prepare source_conditioned_patterns with
predicate_matched* AND signed runtime_active — not all 24 active rules.
Scores use signed reading_evidence_bundle._rule_text + search_bm25.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CORE = Path("/Volumes/Lexar/code/mingli_web/core/mingli-master")
SIGNED = Path("/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release")
MANIFEST = SIGNED / ".mingli-release-manifest.json"
SIGNED_JSONL = SIGNED / "references" / "index" / "evidence-rules.jsonl"

QUERY = "验证八字核心盘面"
DIMENSION = "career"
QUERY_JOINED = f"{QUERY} {DIMENSION}"

PREPARES = {
    "1994_career": {
        "path": Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json"),
        "label": "1994 career",
        "kind": "career",
    },
    "1992_career": {
        "path": Path("/tmp/mingli-oneshot-v53-fixture2-20260819/out/prepare.stdout.json"),
        "label": "1992 career",
        "kind": "career",
    },
    "yiyou_overview": {
        "path": Path("/Volumes/Lexar/code/mingli_web/.runtime/oneshot-20260819-claim-unit/prepare-out.json"),
        "label": "乙酉 overview",
        "kind": "overview",
    },
}

CLAIM_UNITS = [
    "bazi.month-order-state-v1",
    "bazi.ziping-pattern-entry-v1",
    "bazi.tiaohou-priority-v1",
    "bazi.day-master-root-support-v1",
]

sys.path.insert(0, str(SIGNED / "scripts"))
import search_bm25  # noqa: E402
from reading_engine.evidence_rules import load_evidence_rules  # noqa: E402
from reading_evidence_bundle import _rule_text  # noqa: E402


def _claim_units_emitted(providers_path: Path) -> list[str]:
    tree = ast.parse(providers_path.read_text(encoding="utf-8"))
    ids: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "_bazi_public_claim_findings":
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Dict):
                continue
            for key, value in zip(sub.keys, sub.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "claim_unit_id"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    ids.append(value.value)
    return list(dict.fromkeys(ids))


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(CORE), *args], text=True).rstrip()


def _load_prepare(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_claim_units(obj) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        value = obj.get("claim_unit_id")
        if isinstance(value, str) and value:
            found.append(value)
        for item in obj.values():
            found.extend(_walk_claim_units(item))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk_claim_units(item))
    return list(dict.fromkeys(found))


def _scp_entries(brief: dict) -> list[dict]:
    for fact in brief.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        ref = str(fact.get("ref") or "")
        if ref.endswith("/calculated/bazi/source_conditioned_patterns") or (
            "source_conditioned_patterns" in ref
        ):
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


def _status_predicate_matched(status: object) -> bool:
    return "predicate_matched" in str(status or "")


def _fmt_tokens(tokens: list[str]) -> str:
    return ",".join(tokens) if tokens else "(none)"


def _bm25_scores(query_tokens: list[str], rules: list) -> dict[str, float]:
    documents = [
        search_bm25.Document(
            path=SIGNED / rule.source_path,
            line_no=index,
            text=_rule_text(rule),
            tokens=search_bm25.tokenize(_rule_text(rule)),
        )
        for index, rule in enumerate(rules, start=1)
    ]
    by_line = {doc.line_no: rule for doc, rule in zip(documents, rules)}
    ranked = search_bm25.bm25(query_tokens, documents)
    scores = {rule.rule_id: 0.0 for rule in rules}
    for score, doc in ranked:
        scores[by_line[doc.line_no].rule_id] = float(score)
    return scores


def main() -> int:
    core_head = _git(["rev-parse", "HEAD"])
    core_subject = _git(["log", "-1", "--format=%s"])
    dirty = [line for line in _git(["status", "--short"]).splitlines() if line]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_sha = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    rules = load_evidence_rules(SIGNED_JSONL, root=SIGNED)
    by_id = {rule.rule_id: rule for rule in rules}
    active_ids = {
        rule.rule_id
        for rule in rules
        if rule.system == "bazi" and rule.runtime_active is True
    }
    active_rules = [by_id[rule_id] for rule_id in sorted(active_ids)]

    query_tokens = search_bm25.tokenize(QUERY_JOINED)
    query_token_set = set(query_tokens)

    core_claims = _claim_units_emitted(CORE / "scripts" / "reading_engine" / "providers.py")
    signed_claims = _claim_units_emitted(
        SIGNED / "scripts" / "reading_engine" / "providers.py"
    )

    loaded = {}
    for key, spec in PREPARES.items():
        payload = _load_prepare(spec["path"])
        brief = payload["brief"]
        scp = _scp_entries(brief)
        evidence_ids = _evidence_ids(brief)
        matched = []
        skipped = []
        for entry in scp:
            rule_id = str(entry.get("rule_id") or "")
            status = entry.get("status")
            runtime_ok = rule_id in active_ids
            pred_ok = _status_predicate_matched(status)
            row = {
                "rule_id": rule_id,
                "local_rule_id": entry.get("local_rule_id"),
                "pack": entry.get("source_pack")
                or (by_id[rule_id].source_pack if rule_id in by_id else ""),
                "status": status,
                "runtime_active": runtime_ok,
                "predicate_matched": pred_ok,
            }
            if pred_ok and runtime_ok:
                matched.append(row)
            else:
                skipped.append(row)
        loaded[key] = {
            **spec,
            "question": brief.get("question"),
            "dimension_ids": (brief.get("request_view") or {}).get("dimension_ids"),
            "scp_n": len(scp),
            "evidence_ids": evidence_ids,
            "claim_units": _walk_claim_units(brief.get("findings")),
            "matched": matched,
            "skipped": skipped,
        }

    career_keys = ["1994_career", "1992_career"]
    union_ids = []
    for key in career_keys:
        for row in loaded[key]["matched"]:
            if row["rule_id"] not in union_ids:
                union_ids.append(row["rule_id"])
    union_rules = [by_id[rule_id] for rule_id in union_ids]
    scores_union = _bm25_scores(query_tokens, union_rules)
    scores_active = _bm25_scores(query_tokens, active_rules)
    per_prepare_scores = {
        key: _bm25_scores(
            query_tokens,
            [by_id[row["rule_id"]] for row in loaded[key]["matched"]],
        )
        for key in career_keys
    }

    both_matched = (
        {row["rule_id"] for row in loaded["1994_career"]["matched"]}
        & {row["rule_id"] for row in loaded["1992_career"]["matched"]}
    )
    ev_1994 = set(loaded["1994_career"]["evidence_ids"])
    ev_1992 = set(loaded["1992_career"]["evidence_ids"])
    ev_overview = set(loaded["yiyou_overview"]["evidence_ids"])
    never_enters = sorted(
        rule_id
        for rule_id in both_matched
        if rule_id not in ev_1994 and rule_id not in ev_1992
    )

    print("=== IDENTITY ===")
    print(f"core_head={core_head}")
    print(f"core_subject={core_subject}")
    print(f"core_dirty_count={len(dirty)}")
    for line in dirty:
        print(f"core_dirty={line}")
    print(f"signed_manifest_sha256={manifest_sha}")
    print(f"signed_source_commit={manifest.get('source_commit')}")
    print(f"signed_n_files={len(manifest.get('files') or {})}")
    print(f"runtime_active_bazi={len(active_ids)}")
    print(f"query={QUERY!r}")
    print(f"dimension={DIMENSION!r}")
    print(f"query_joined={QUERY_JOINED!r}")
    print(f"query_tokens={query_tokens}")

    print("=== PREPARE_LOAD ===")
    for key in ("1994_career", "1992_career", "yiyou_overview"):
        item = loaded[key]
        print(f"prepare={key}")
        print(f"  path={item['path']}")
        print(f"  question={item['question']!r}")
        print(f"  dimension_ids={item['dimension_ids']}")
        print(f"  scp_n={item['scp_n']}")
        print(f"  matched_n={len(item['matched'])}")
        print(f"  skipped_n={len(item['skipped'])}")
        print(f"  evidence_n={len(item['evidence_ids'])}")
        print(f"  evidence_ids={item['evidence_ids']}")
        print(f"  claim_units={item['claim_units']}")
        if item["skipped"]:
            print(f"  skipped={[(row['rule_id'], row['status'], row['runtime_active']) for row in item['skipped']]}")

    print("=== MAIN_TABLE ===")
    print(
        "rule_id\tpack\ttoken_intersection\tbm25_union\tbm25_active_corpus\t"
        "bm25_1994\tbm25_1992\tmatched_1994\tmatched_1992\t"
        "in_1994_evidence\tin_1992_evidence\tin_overview_evidence"
    )
    for rule_id in union_ids:
        rule = by_id[rule_id]
        rule_tokens = set(search_bm25.tokenize(_rule_text(rule)))
        overlap = sorted(query_token_set & rule_tokens)
        m1994 = any(row["rule_id"] == rule_id for row in loaded["1994_career"]["matched"])
        m1992 = any(row["rule_id"] == rule_id for row in loaded["1992_career"]["matched"])
        s1994 = per_prepare_scores["1994_career"].get(rule_id)
        s1992 = per_prepare_scores["1992_career"].get(rule_id)
        print(
            f"{rule_id}\t{rule.source_pack}\t{_fmt_tokens(overlap)}\t"
            f"{scores_union.get(rule_id, 0.0):.10f}\t"
            f"{scores_active.get(rule_id, 0.0):.10f}\t"
            f"{'n/a' if s1994 is None else format(s1994, '.10f')}\t"
            f"{'n/a' if s1992 is None else format(s1992, '.10f')}\t"
            f"{'YES' if m1994 else 'NO'}\t"
            f"{'YES' if m1992 else 'NO'}\t"
            f"{'YES' if rule_id in ev_1994 else 'NO'}\t"
            f"{'YES' if rule_id in ev_1992 else 'NO'}\t"
            f"{'YES' if rule_id in ev_overview else 'NO'}"
        )

    print("=== TOTALS ===")
    print(f"union_matched_runtime_active={len(union_ids)}")
    print(f"matched_1994={len(loaded['1994_career']['matched'])}")
    print(f"matched_1992={len(loaded['1992_career']['matched'])}")
    print(f"both_matched={len(both_matched)}")
    print(f"both_matched_ids={sorted(both_matched)}")
    print(f"evidence_1994_n={len(ev_1994)}")
    print(f"evidence_1992_n={len(ev_1992)}")
    print(f"evidence_overview_n={len(ev_overview)}")
    print(f"never_enters_n={len(never_enters)}")
    print(f"never_enters_ids={never_enters}")
    five_1994 = [
        "bazi/qiongtong-baojian#QR-02-01",
        "bazi/sanming-tonghui#R-01-02",
        "bazi/sanming-tonghui#R-02-04",
        "bazi/ziping-zhenquan#ZPR-01",
        "bazi/qiongtong-baojian#QTB-M01",
    ]
    print(f"dr_01_01_in_never_enters={'YES' if 'bazi/ditiansui-chanwei#DR-01-01' in never_enters else 'NO'}")
    leaked = [rule_id for rule_id in five_1994 if rule_id in never_enters]
    print(f"five_1994_evidence_ids={five_1994}")
    print(f"five_1994_in_never_enters={leaked if leaked else 'NONE'}")
    print(f"five_1994_in_1994_evidence={all(rule_id in ev_1994 for rule_id in five_1994)}")

    print("=== ATTACHMENT_CLAIM_UNITS ===")
    print("claim_unit_id\tsource_has\tartifact_has\tbrief_1994\tbrief_1992\tbrief_overview")
    for claim_id in CLAIM_UNITS:
        print(
            f"{claim_id}\t"
            f"{'YES' if claim_id in core_claims else 'NO'}\t"
            f"{'YES' if claim_id in signed_claims else 'NO'}\t"
            f"{'YES' if claim_id in loaded['1994_career']['claim_units'] else 'NO'}\t"
            f"{'YES' if claim_id in loaded['1992_career']['claim_units'] else 'NO'}\t"
            f"{'YES' if claim_id in loaded['yiyou_overview']['claim_units'] else 'NO'}"
        )
    print(f"source_claims={core_claims}")
    print(f"artifact_claims={signed_claims}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
