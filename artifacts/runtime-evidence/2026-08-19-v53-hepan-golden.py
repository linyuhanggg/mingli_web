#!/usr/bin/env python3
"""Read-only: P10-004 合盘关系 / hepan / relationship — signed V53 vs core.

Admission pin first. V52 relationship-release (bef3df25) is contrast only;
never added into V53 counts. Do not mix 三术合参 convergence or 见相 disagreements.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
CORE = ROOT / "core/mingli-master"
V52 = ROOT / ".runtime/v52-relationship-release"
ADMITTED_MANIFEST = "c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b"
ADMITTED_SOURCE = "663543e65ae037843b03dca1dec9486293affc9d"
ADMITTED_FILES = 220
V52_MANIFEST = "bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50"
V52_SOURCE = "da46e7c0d565fe781e40a115acbb2874c400a195"
SKIP = {".git", "__pycache__", ".pytest_cache", "node_modules", ".mypy_cache"}
SCOPE_PATH = Path("references/matrices/evidence-scope-bindings-v1.yaml")
SMOKE = ROOT / "scripts/smoke_local_real_relationship_runtime.py"

# 合盘关系真值。不要用裸 relationship：会撞上 source_relationships / branch_relations。
TRUE_TOKENS = [
    "relationship_signals",
    "_append_runtime_relationship",
    "_bazi_relationship_signals",
    "_ziwei_relationship_signals",
    "_qizheng_relationship_signals",
    "_runtime_relationship_signals",
    "bazi-relationship",
    "ziwei-relationship",
    "qizheng-relationship",
    "kind.bazi.relationship_signals",
    "kind.ziwei.relationship_signals",
    "kind.xingming.relationship_signals",
    "kind.qizheng.relationship_signals",
    "BaziRelationshipV1",
    "ZiweiRelationshipV1",
    "QizhengRelationshipV1",
    "合盘",
    "hepan",
]
PATH_KEYS = (
    "hepan",
    "bazi-relationship",
    "ziwei-relationship",
    "qizheng-relationship",
    "合盘",
)
TRAP_TOKENS = (
    "source_relationships",
    "branch_relations",
    "convergence",
    "disagreements",
    "合参",
    "hecan",
)
CU_NEEDLES = (
    "hepan",
    "relationship",
    "合盘",
    "bazi-relationship",
    "ziwei-relationship",
    "qizheng-relationship",
)
PROVIDER_STEMS = (
    "hepan",
    "relationship",
    "bazi-relationship",
    "ziwei-relationship",
    "qizheng-relationship",
)
FIXTURE_NAME_RE = re.compile(
    r"(hepan|relationship|bazi-relationship|合盘)", re.I
)
PREPARE_PATHS = [
    Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json"),
    Path("/Volumes/Lexar/code/mingli_web/.runtime/oneshot-20260819-claim-unit/prepare-out.json"),
]
TEXT_SUFFIXES = (
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".jsonl",
    ".txt",
    ".lock",
)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_files(root: Path) -> list[str]:
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            if rel.startswith("."):
                continue
            out.append(rel)
    return out


def is_trap_path(rel: str) -> bool:
    low = rel.lower()
    if "hecan" in low or "合参" in rel or "convergence" in low:
        return True
    if "disagreement" in low:
        return True
    if "source_relationship" in low or "branch_relation" in low:
        return True
    return False


def path_is_hepan(rel: str) -> bool:
    if is_trap_path(rel):
        return False
    low = rel.lower()
    if "hecan" in low:
        return False
    if any(k in low or k in rel for k in PATH_KEYS):
        return True
    # 文件名含 relationship，但排除证据血缘 / 地支关系。
    name = Path(rel).name.lower()
    if "relationship" in name and "source_relationship" not in name:
        if "branch_relation" in name:
            return False
        return True
    return False


def path_hits(root: Path) -> tuple[list[str], list[str]]:
    hits: list[str] = []
    traps: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            if is_trap_path(rel) and (
                any(k in rel.lower() or k in rel for k in PATH_KEYS)
                or "relationship" in Path(rel).name.lower()
            ):
                traps.append(rel)
                continue
            if path_is_hepan(rel):
                hits.append(rel)
    return sorted(hits), sorted(traps)


def claim_ids(text: str) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', text)


def count_hits(text: str, needles: list[str]) -> dict[str, int]:
    return {n: text.count(n) for n in needles}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def golden_signal_ids() -> list[str]:
    if not SMOKE.exists():
        return []
    text = read_text(SMOKE)
    return sorted(set(re.findall(r'"(?:bazi|ziwei|qizheng)\.cross_[^"]+"', text)))


def classify_core_only(rel: str) -> str:
    if "/fixtures/" in rel or re.search(r"-v51\.ya?ml$", rel):
        return "fixture_oracle"
    if (
        rel.startswith("scripts/test_")
        or rel.startswith("scripts/audit_")
        or rel.endswith("_fixture_reference.py")
    ):
        return "test_or_audit"
    if rel.startswith("references/") and rel.endswith((".md", ".yaml", ".yml")):
        return "book_notes"
    if rel.endswith(".py") and "/reading_engine/" in rel:
        return "engine_impl"
    return "other"


def content_scan(root: Path) -> tuple[dict[str, dict[str, int]], dict[str, int], list[str]]:
    """True-token hits per relative path. Trap tokens counted separately, not mixed."""
    per_file: dict[str, dict[str, int]] = {}
    trap_totals: dict[str, int] = {t: 0 for t in TRAP_TOKENS}
    trap_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(TEXT_SUFFIXES):
                continue
            p = Path(dirpath, fn)
            rel = p.relative_to(root).as_posix()
            try:
                text = read_text(p)
            except OSError:
                continue
            found = {tok: text.count(tok) for tok in TRUE_TOKENS if text.count(tok)}
            if found:
                per_file[rel] = found
            trap_here = False
            for tok in TRAP_TOKENS:
                n = text.count(tok)
                if n:
                    trap_totals[tok] += n
                    trap_here = True
            if trap_here:
                trap_files.append(rel)
    return per_file, trap_totals, sorted(set(trap_files))


def provider_ids(root: Path) -> list[str]:
    d = root / "resources/runtime/providers"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def fixture_names(root: Path) -> list[str]:
    fx = root / "references/fixtures"
    if not fx.exists():
        return []
    names: list[str] = []
    for p in fx.rglob("*"):
        if p.is_file() and FIXTURE_NAME_RE.search(p.name):
            names.append(p.relative_to(root).as_posix())
    return sorted(names)


def parse_scope_routes(text: str, route: str) -> list[str]:
    ids: list[str] = []
    current: str | None = None
    pat = re.compile(rf"^    route:\s*{re.escape(route)}\s*$")
    for raw in text.splitlines():
        m = re.match(r"^  ([^:\s][^:]*):", raw)
        if m:
            current = m.group(1)
            continue
        if current and pat.match(raw):
            ids.append(current)
    return ids


def main() -> int:
    man_path = SIGNED / ".mingli-release-manifest.json"
    inspector = sha(man_path)
    man = json.loads(man_path.read_bytes())
    src = man.get("source_commit")
    n_man = len(man.get("files") or {})
    n_walk = len(walk_files(SIGNED))
    signed_turns = read_text(SIGNED / "scripts/reading_engine/turns.py")
    core_turns = read_text(CORE / "scripts/reading_engine/turns.py")
    v52_mix = ("relationship_signals" in signed_turns) or (
        "_append_runtime_relationship" in signed_turns
    )
    pin_ok = (
        inspector == ADMITTED_MANIFEST
        and src == ADMITTED_SOURCE
        and n_man == ADMITTED_FILES
        and n_walk == ADMITTED_FILES
        and inspector != V52_MANIFEST
        and src != V52_SOURCE
        and not v52_mix
    )

    v52_inspector = sha(V52 / ".mingli-release-manifest.json") if V52.exists() else None
    v52_man = (
        json.loads((V52 / ".mingli-release-manifest.json").read_bytes()) if V52.exists() else {}
    )
    v52_src = v52_man.get("source_commit")
    v52_n = len(v52_man.get("files") or {})
    v52_is_other = (
        v52_inspector == V52_MANIFEST and v52_src == V52_SOURCE and inspector != v52_inspector
    )
    v52_turns = (
        read_text(V52 / "scripts/reading_engine/turns.py")
        if (V52 / "scripts/reading_engine/turns.py").exists()
        else ""
    )

    signed_path_hits, signed_traps = path_hits(SIGNED)
    core_path_hits, core_traps = path_hits(CORE)
    signed_set = set(signed_path_hits)
    core_set = set(core_path_hits)
    both = sorted(signed_set & core_set)
    core_only = sorted(core_set - signed_set)
    signed_only = sorted(signed_set - core_set)
    hash_cmp = {
        rel: sha(SIGNED / rel) == sha(CORE / rel)
        for rel in both
        if (SIGNED / rel).exists() and (CORE / rel).exists()
    }

    signed_provs = provider_ids(SIGNED)
    core_provs = provider_ids(CORE)
    hepan_provs_signed = [p for p in signed_provs if p in PROVIDER_STEMS or "hepan" in p]
    hepan_provs_core = [p for p in core_provs if p in PROVIDER_STEMS or "hepan" in p]
    extra_core_provs = sorted(set(core_provs) - set(signed_provs))

    signed_prov_py = read_text(SIGNED / "scripts/reading_engine/providers.py")
    core_prov_py = read_text(CORE / "scripts/reading_engine/providers.py")
    signed_cu = claim_ids(signed_prov_py)
    core_cu = claim_ids(core_prov_py)
    hepan_cu_signed = [
        x for x in signed_cu if any(k in x.lower() or k in x for k in CU_NEEDLES)
    ]
    hepan_cu_core = [x for x in core_cu if any(k in x.lower() or k in x for k in CU_NEEDLES)]
    provider_class_hits_signed = {
        name: bool(re.search(rf"class\s+{name}\b", signed_prov_py))
        for name in ("RelationshipProvider", "HepanProvider", "BaziRelationshipProvider")
    }
    provider_class_hits_core = {
        name: bool(re.search(rf"class\s+{name}\b", core_prov_py))
        for name in ("RelationshipProvider", "HepanProvider", "BaziRelationshipProvider")
    }

    evidence_all = read_text(SIGNED / "references/index/evidence-rules.jsonl")
    n_rules = sum(1 for line in evidence_all.splitlines() if line.strip())
    packs: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    mention_rows: list[str] = []
    trap_hecan_rows = 0
    trap_dis_rows = 0
    for line in evidence_all.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        rid = str(row.get("rule_id") or "")
        path = str(row.get("source_path") or "")
        blob = pack + " " + rid + " " + path
        if any(k in blob.lower() or k in blob for k in ("hecan", "合参", "convergence")):
            trap_hecan_rows += 1
        if "disagreement" in blob.lower() or "见相" in blob:
            trap_dis_rows += 1
        is_pack = any(
            pack.startswith(pref) or pref in pack.lower()
            for pref in ("hepan", "relationship", "bazi-relationship")
        ) or "合盘" in pack
        is_mention = ("合盘" in blob) or bool(
            re.search(
                r"\bhepan\b|bazi-relationship|ziwei-relationship|qizheng-relationship|relationship_signals",
                blob,
                re.I,
            )
        )
        if is_mention and not is_pack:
            mention_rows.append(rid)
            continue
        if not is_pack:
            continue
        packs.setdefault(pack, {"n": 0, "active": 0, "verified": 0})
        packs[pack]["n"] += 1
        if row.get("runtime_active"):
            packs[pack]["active"] += 1
            active_ids.append(rid)
        if str(row.get("classical_binding_status") or "") == "verified":
            packs[pack]["verified"] += 1
            verified_ids.append(rid)

    core_evidence = CORE / "references/index/evidence-rules.jsonl"
    evidence_hash_same = core_evidence.exists() and sha(
        SIGNED / "references/index/evidence-rules.jsonl"
    ) == sha(core_evidence)

    scope_text = (
        read_text(SIGNED / SCOPE_PATH) if (SIGNED / SCOPE_PATH).exists() else ""
    )
    scope_hepan = parse_scope_routes(scope_text, "hepan")
    scope_rel = parse_scope_routes(scope_text, "relationship")
    scope_bazi_rel = parse_scope_routes(scope_text, "bazi-relationship")
    scope_hash_same = False
    if (SIGNED / SCOPE_PATH).exists() and (CORE / SCOPE_PATH).exists():
        scope_hash_same = sha(SIGNED / SCOPE_PATH) == sha(CORE / SCOPE_PATH)

    signed_content, signed_traps_tok, _signed_trap_files = content_scan(SIGNED)
    core_content, core_traps_tok, _core_trap_files = content_scan(CORE)
    signed_content_files = sorted(signed_content)
    core_content_files = sorted(core_content)
    core_only_content = sorted(set(core_content_files) - set(signed_content_files))
    signed_only_content = sorted(set(signed_content_files) - set(core_content_files))
    both_content = sorted(set(signed_content_files) & set(core_content_files))
    content_hash_mismatch = [
        rel
        for rel in both_content
        if (SIGNED / rel).exists()
        and (CORE / rel).exists()
        and sha(SIGNED / rel) != sha(CORE / rel)
    ]
    core_only_kind = {rel: classify_core_only(rel) for rel in core_only_content}
    kind_counts = dict(Counter(core_only_kind.values()))
    impl_unsigned = [rel for rel, k in core_only_kind.items() if k == "engine_impl"]
    impl_unsigned += [
        rel
        for rel in content_hash_mismatch
        if rel.endswith((".py", ".json"))
        and "fixtures" not in rel
        and not rel.endswith("providers.py")
    ]

    engine_dir = CORE / "scripts/reading_engine"
    content_engine: list[str] = []
    content_engine_diff: list[str] = []
    for p in sorted(engine_dir.glob("*.py")):
        txt = read_text(p)
        if not any(tok in txt for tok in TRUE_TOKENS):
            continue
        rel = p.relative_to(CORE).as_posix()
        content_engine.append(rel)
        sp = SIGNED / rel
        if not sp.exists():
            content_engine_diff.append(rel + ":core_only")
        elif sha(sp) != sha(p) and rel != "scripts/reading_engine/providers.py":
            content_engine_diff.append(rel + ":hash_diff")

    turns_same = sha(SIGNED / "scripts/reading_engine/turns.py") == sha(
        CORE / "scripts/reading_engine/turns.py"
    )
    v52_turns_same_as_signed = bool(v52_turns) and sha(
        SIGNED / "scripts/reading_engine/turns.py"
    ) == sha(V52 / "scripts/reading_engine/turns.py")
    v52_true = count_hits(v52_turns, TRUE_TOKENS)
    signed_turns_true = count_hits(signed_turns, TRUE_TOKENS)
    core_turns_true = count_hits(core_turns, TRUE_TOKENS)

    signed_fx = fixture_names(SIGNED)
    core_fx = fixture_names(CORE)
    v52_fx = fixture_names(V52) if V52.exists() else []
    gold_ids = golden_signal_ids()

    brief = read_text(SIGNED / "scripts/reading_engine/brief.py")
    evid_py = read_text(SIGNED / "scripts/reading_engine/evidence_rules.py")
    core_brief = read_text(CORE / "scripts/reading_engine/brief.py")
    core_evid_py = read_text(CORE / "scripts/reading_engine/evidence_rules.py")
    needles = list(
        dict.fromkeys(
            TRUE_TOKENS
            + gold_ids
            + [
                "hepan-v51",
                "relationship-v51",
                "mingli-hepan-fixtures",
                "mingli-relationship-fixtures",
                "bazi-compatibility-reading",
                "v52-relationship",
                "bef3df25",
                "cross_branch",
                "cross_palace",
                "cross_aspect",
                "cross_stem",
            ]
        )
    )
    brief_hits = count_hits(brief, needles)
    evid_py_hits = count_hits(evid_py, needles)
    evid_jsonl_hits = count_hits(evidence_all, needles)
    core_brief_hits = count_hits(core_brief, needles)
    core_evid_py_hits = count_hits(core_evid_py, needles)
    brief_loads_fixtures = ("references/fixtures" in brief) or any(
        k in brief for k in ("hepan-v51", "relationship-v51")
    )
    evid_loads_fixtures = ("references/fixtures" in evid_py) or any(
        k in evid_py for k in ("hepan-v51", "relationship-v51")
    )
    brief_loads_v52_path = "v52-relationship-release" in brief or "bef3df25" in brief
    evid_loads_v52_path = "v52-relationship-release" in evid_py or "bef3df25" in evid_py

    prepare_hits: dict[str, dict[str, int]] = {}
    for p in PREPARE_PATHS:
        if not p.exists():
            prepare_hits[str(p)] = {"exists": 0}
            continue
        t = read_text(p)
        prepare_hits[str(p)] = {
            "exists": 1,
            "relationship_signals": t.count("relationship_signals"),
            "合盘": t.count("合盘"),
            "hepan": t.count("hepan"),
            "bazi-relationship": t.count("bazi-relationship"),
            "golden_id_hits": sum(t.count(g) for g in gold_ids),
        }

    catalog_hits = {}
    for label, root in (("signed", SIGNED), ("core", CORE), ("v52_contrast", V52)):
        p = root / "resources/runtime/catalog-v1.json"
        if not p.exists():
            catalog_hits[label] = None
            continue
        t = read_text(p)
        catalog_hits[label] = count_hits(t, ["hepan", "relationship", "合盘", "bazi-relationship"])

    privacy_listed = [
        "references/bazi-relationship-career-followups.md",
        "references/bazi-relationship-infidelity-risk.md",
        "references/bazi-relationship-year-followup-notes.md",
    ]
    privacy_exist = {
        rel: {
            "core": (CORE / rel).exists(),
            "signed": (SIGNED / rel).exists(),
            "v52": (V52 / rel).exists(),
        }
        for rel in privacy_listed
    }
    note_file = "references/bazi-compatibility-reading.md"
    note_in_core = (CORE / note_file).exists()
    note_in_signed = (SIGNED / note_file).exists()

    signed_true_sum = {
        tok: sum(d.get(tok, 0) for d in signed_content.values()) for tok in TRUE_TOKENS
    }
    core_true_sum = {
        tok: sum(d.get(tok, 0) for d in core_content.values()) for tok in TRUE_TOKENS
    }
    signed_true_total = sum(signed_true_sum.values())
    core_true_total = sum(core_true_sum.values())
    gold_in_brief = sum(brief_hits.get(g, 0) for g in gold_ids)
    gold_in_evid_py = sum(evid_py_hits.get(g, 0) for g in gold_ids)
    gold_in_jsonl = sum(evid_jsonl_hits.get(g, 0) for g in gold_ids)
    true_in_brief = sum(brief_hits.get(t, 0) for t in TRUE_TOKENS)
    true_in_evid_py = sum(evid_py_hits.get(t, 0) for t in TRUE_TOKENS)
    true_in_jsonl = sum(evid_jsonl_hits.get(t, 0) for t in TRUE_TOKENS)

    print(f"inspector={inspector}")
    print(f"source_commit={src}")
    print(f"manifest_files={n_man}")
    print(f"walk_files={n_walk}")
    print(f"pin_ok={pin_ok}")
    print(f"v52_mix_in_v53_turns={v52_mix}")
    print(f"v52_contrast_exists={V52.exists()}")
    print(f"v52_contrast_inspector={v52_inspector}")
    print(f"v52_contrast_source={v52_src}")
    print(f"v52_contrast_files={v52_n}")
    print(f"v52_is_other_artifact={v52_is_other}")
    print(f"v52_turns_same_as_signed={v52_turns_same_as_signed}")
    print(f"v52_contrast_true_token_hits={ {k: v for k, v in v52_true.items() if v} }")
    print(f"v52_contrast_true_token_sum={sum(v52_true.values())}")
    print(f"signed_providers={signed_provs}")
    print(f"core_providers={core_provs}")
    print(f"hepan_providers_signed={hepan_provs_signed}")
    print(f"hepan_providers_core={hepan_provs_core}")
    print(f"extra_core_providers={extra_core_provs}")
    print(f"provider_class_signed={provider_class_hits_signed}")
    print(f"provider_class_core={provider_class_hits_core}")
    print(f"signed_cu={signed_cu}")
    print(f"core_cu={core_cu}")
    print(f"hepan_cu_signed={hepan_cu_signed}")
    print(f"hepan_cu_core={hepan_cu_core}")
    print(f"signed_path_hits_n={len(signed_path_hits)}")
    print(f"signed_path_hits={signed_path_hits}")
    print(f"signed_path_traps={signed_traps}")
    print(f"core_path_hits_n={len(core_path_hits)}")
    print(f"core_path_hits={core_path_hits}")
    print(f"core_path_traps={core_traps}")
    print(f"core_only_path_n={len(core_only)}")
    print(f"core_only_paths={core_only}")
    print(f"signed_only_paths={signed_only}")
    print(f"both_path_n={len(both)}")
    print(f"path_hash_mismatch={ [r for r, ok in hash_cmp.items() if not ok] }")
    print(f"signed_content_files_n={len(signed_content_files)}")
    print(f"signed_content_files={signed_content_files}")
    print(f"signed_true_token_sum={signed_true_sum}")
    print(f"signed_true_token_total={signed_true_total}")
    print(f"core_content_files_n={len(core_content_files)}")
    print(f"core_content_files={core_content_files}")
    print(f"core_true_token_sum={core_true_sum}")
    print(f"core_true_token_total={core_true_total}")
    print(f"core_only_content_n={len(core_only_content)}")
    print(f"core_only_content={core_only_content}")
    print(f"core_only_kind={core_only_kind}")
    print(f"core_only_kind_counts={kind_counts}")
    print(f"signed_only_content={signed_only_content}")
    print(f"content_hash_mismatch={content_hash_mismatch}")
    print(f"content_hash_mismatch_n={len(content_hash_mismatch)}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")
    print(f"content_engine_hepan_files={content_engine}")
    print(f"content_engine_hepan_diff={content_engine_diff}")
    print(f"turns_hash_same={turns_same}")
    print(f"signed_turns_true={ {k: v for k, v in signed_turns_true.items() if v} }")
    print(f"core_turns_true={ {k: v for k, v in core_turns_true.items() if v} }")
    print(f"evidence_rules_total={n_rules}")
    print(f"hepan_packs={packs}")
    print(f"hepan_pack_n={len(packs)}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"runtime_active_rules={active_ids}")
    print(f"verified_n={len(verified_ids)}")
    print(f"verified_rules={verified_ids}")
    print(f"hepan_mention_not_pack={mention_rows}")
    print(f"hepan_mention_not_pack_n={len(mention_rows)}")
    print(f"trap_hecan_rows_seen={trap_hecan_rows}")
    print(f"trap_disagreement_or_jianxiang_rows_seen={trap_dis_rows}")
    print(f"signed_trap_token_totals={signed_traps_tok}")
    print(f"core_trap_token_totals={core_traps_tok}")
    print(f"scope_route_hepan={scope_hepan}")
    print(f"scope_route_relationship={scope_rel}")
    print(f"scope_route_bazi_relationship={scope_bazi_rel}")
    print(f"scope_hash_same={scope_hash_same}")
    print(f"evidence_rules_hash_same={evidence_hash_same}")
    print(f"golden_fixture_in_signed={signed_fx}")
    print(f"golden_fixture_in_core={core_fx}")
    print(f"golden_fixture_in_v52_contrast={v52_fx}")
    print(f"golden_signal_id_n={len(gold_ids)}")
    print(f"golden_signal_ids={gold_ids}")
    print(f"brief_true_token_hits={true_in_brief}")
    print(f"brief_golden_id_hits={gold_in_brief}")
    print(f"brief_loads_fixtures={brief_loads_fixtures}")
    print(f"brief_loads_v52_path={brief_loads_v52_path}")
    print(f"brief_needle_hits={ {k: v for k, v in brief_hits.items() if v} }")
    print(f"evidence_py_true_token_hits={true_in_evid_py}")
    print(f"evidence_py_golden_id_hits={gold_in_evid_py}")
    print(f"evidence_py_loads_fixtures={evid_loads_fixtures}")
    print(f"evidence_py_loads_v52_path={evid_loads_v52_path}")
    print(f"evidence_py_needle_hits={ {k: v for k, v in evid_py_hits.items() if v} }")
    print(f"evidence_jsonl_true_token_hits={true_in_jsonl}")
    print(f"evidence_jsonl_golden_id_hits={gold_in_jsonl}")
    print(f"evidence_jsonl_needle_hits={ {k: v for k, v in evid_jsonl_hits.items() if v} }")
    print(f"core_brief_true_token_hits={sum(core_brief_hits.get(t, 0) for t in TRUE_TOKENS)}")
    print(f"core_evidence_py_true_token_hits={sum(core_evid_py_hits.get(t, 0) for t in TRUE_TOKENS)}")
    print(f"prepare_hits={prepare_hits}")
    print(f"prepare_any_relationship_signals={any(v.get('relationship_signals', 0) for v in prepare_hits.values())}")
    print(f"catalog_hits={catalog_hits}")
    print(f"privacy_listed_exist={privacy_exist}")
    print(f"note_bazi_compatibility_core={note_in_core}")
    print(f"note_bazi_compatibility_signed={note_in_signed}")
    print(
        "CONCLUSION_1 "
        f"pin_ok={pin_ok} v52_mix={v52_mix} "
        f"provider={hepan_provs_signed} class={provider_class_hits_signed} "
        f"CU={hepan_cu_signed} packs={packs} pack_n={len(packs)} "
        f"active={len(active_ids)} verified={len(verified_ids)} "
        f"path_hits={len(signed_path_hits)} "
        f"turns_relationship_signals={signed_turns_true.get('relationship_signals', 0)} "
        f"signed_true_total={signed_true_total} "
        f"scope_hepan={len(scope_hepan)} scope_relationship={len(scope_rel)} "
        f"golden_in_signed={signed_fx} "
        f"excluded_hecan_rows={trap_hecan_rows} "
        f"v52_is_other={v52_is_other} v52_turns_same={v52_turns_same_as_signed}"
    )
    print(
        "CONCLUSION_2 "
        f"hepan_providers_core={hepan_provs_core} hepan_cu_core={hepan_cu_core} "
        f"turns_hash_same={turns_same} "
        f"core_path_hits={len(core_path_hits)} "
        f"core_only_content_n={len(core_only_content)} kind={kind_counts} "
        f"unsigned_impl_n={len(impl_unsigned)} "
        f"content_engine_diff={content_engine_diff} "
        f"content_hash_mismatch_n={len(content_hash_mismatch)} "
        f"note_in_core={note_in_core} note_in_signed={note_in_signed} "
        f"core_fx={core_fx}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_true={true_in_brief} brief_golden_ids={gold_in_brief} "
        f"brief_loads_fixtures={brief_loads_fixtures} "
        f"brief_loads_v52_path={brief_loads_v52_path} "
        f"evidence_py_true={true_in_evid_py} evidence_py_golden_ids={gold_in_evid_py} "
        f"evidence_jsonl_true={true_in_jsonl} evidence_jsonl_golden_ids={gold_in_jsonl} "
        f"prepare_any_relationship_signals={any(v.get('relationship_signals', 0) for v in prepare_hits.values())} "
        f"golden_signal_id_n={len(gold_ids)} "
        f"v52_contrast_true_sum={sum(v52_true.values())} "
        f"v52_not_mixed_into_v53={v52_is_other and not v52_mix}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
