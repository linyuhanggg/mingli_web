#!/usr/bin/env python3
"""Read-only: 问事 / wenshi / canwen / 参问 — signed V53 vs core.

Admission pin first. V52 relationship-release (bef3df25) is contrast only.
Do not mix 合盘/hepan, 合参/hecan/convergence, or 寻时/time-check.
Bare 问事 in 所问事项/问事时间/问事分类 is generic, not the product.
Single-art liuyao/qimen/liuren providers are not the 问事 product.
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
HOST_ADAPTER = ROOT / "backend/tests/test_runtime_process_adapter.py"
HOST_COMPILER = ROOT / "backend/tests/test_request_compiler.py"

TRUE_TOKENS = [
    "wenshi",
    "canwen",
    "问事合参",
    "参问",
    "WenshiProvider",
    "CanwenProvider",
    "wenshi_one_question",
    "compile_wenshi_prepare",
    "project_wenshi_view_model",
    "compile_canwen_prepare",
    "project_canwen_view_model",
    "canwen_preview",
]
PATH_KEYS = ("wenshi", "canwen", "问事合参", "参问")
PROVIDER_STEMS = ("wenshi", "canwen")
CU_NEEDLES = ("wenshi", "canwen", "问事", "参问")
GENERIC_PHRASES = (
    "所问事项",
    "问事时间",
    "问事分类",
    "问事类",
    "当前问事",
    "六壬问事",
    "按问事",
)
TRAP_TOKENS = (
    "合盘",
    "hepan",
    "合参",
    "hecan",
    "寻时",
    "time-check",
    "time_check",
    "convergence",
    "relationship_signals",
)
FIXTURE_NAME_RE = re.compile(r"(wenshi|canwen|问事合参|参问)", re.I)
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
GOLD_NEEDLES = [
    "wenshi:golden-rule-evidence",
    "wenshi:synthetic-runtime",
    "fact:wenshi:golden-rule-evidence/calculated/liuren/dimension_facts",
    "canwen-synthetic",
    "profile-version:canwen-synthetic",
    "wenshi-v51",
    "canwen-v51",
    "mingli-wenshi-fixtures",
    "mingli-canwen-fixtures",
    "不形成问事合参结论",
]


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


def path_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            low = rel.lower()
            if any(k in low or k in rel for k in PATH_KEYS):
                hits.append(rel)
    return sorted(hits)


def claim_ids(text: str) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', text)


def count_hits(text: str, needles: list[str]) -> dict[str, int]:
    return {n: text.count(n) for n in needles}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def residual_wenshi(text: str) -> tuple[int, int]:
    covered = [False] * (len(text) + 1)
    for phrase in sorted(GENERIC_PHRASES, key=len, reverse=True):
        start = 0
        while True:
            k = text.find(phrase, start)
            if k < 0:
                break
            for x in range(k, k + len(phrase)):
                covered[x] = True
            start = k + 1
    raw = 0
    residual = 0
    i = 0
    while True:
        j = text.find("问事", i)
        if j < 0:
            break
        raw += 1
        if not covered[j]:
            residual += 1
        i = j + 2
    return raw, residual


def classify_core_only(rel: str) -> str:
    if "/fixtures/" in rel or re.search(r"-v51\.ya?ml$", rel):
        return "fixture_oracle"
    if (
        rel.startswith("scripts/test_")
        or rel.startswith("scripts/audit_")
        or rel.startswith("test-")
        or rel.endswith("_fixture_reference.py")
        or "/regression/" in rel
    ):
        return "test_or_audit"
    if rel.startswith("references/") and rel.endswith((".md", ".yaml", ".yml")):
        return "book_notes"
    if rel.endswith(".py") and "/reading_engine/" in rel:
        return "engine_impl"
    return "other"


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


def content_scan(root: Path) -> tuple[dict[str, dict[str, int]], dict[str, int], list[tuple[str, int, int]], dict[str, int]]:
    per_file: dict[str, dict[str, int]] = {}
    trap_totals: dict[str, int] = {t: 0 for t in TRAP_TOKENS}
    generic_files: list[tuple[str, int, int]] = []
    generic_phrase_sum: dict[str, int] = {t: 0 for t in GENERIC_PHRASES}
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
            raw, residual = residual_wenshi(text)
            if raw:
                generic_files.append((rel, raw, residual))
            for tok in GENERIC_PHRASES:
                generic_phrase_sum[tok] += text.count(tok)
            for tok in TRAP_TOKENS:
                trap_totals[tok] += text.count(tok)
    return per_file, trap_totals, sorted(generic_files), generic_phrase_sum


def host_gold_ids() -> list[str]:
    found: list[str] = []
    for path in (HOST_ADAPTER, HOST_COMPILER):
        if not path.exists():
            continue
        text = read_text(path)
        found.extend(re.findall(r"wenshi:[A-Za-z0-9_\-]+", text))
        found.extend(re.findall(r"canwen-[A-Za-z0-9_\-]+", text))
        found.extend(re.findall(r"profile-version:canwen-[A-Za-z0-9_\-]+", text))
        found.extend(re.findall(r"fact:wenshi:[^\"\s]+", text))
    return sorted(set(found + GOLD_NEEDLES))


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

    signed_path_hits = path_hits(SIGNED)
    core_path_hits = path_hits(CORE)
    signed_provs = provider_ids(SIGNED)
    core_provs = provider_ids(CORE)
    wenshi_provs_signed = [p for p in signed_provs if p in PROVIDER_STEMS]
    wenshi_provs_core = [p for p in core_provs if p in PROVIDER_STEMS]
    extra_core_provs = sorted(set(core_provs) - set(signed_provs))
    single_arts = [p for p in signed_provs if p in ("liuyao", "qimen", "liuren")]

    signed_prov_py = read_text(SIGNED / "scripts/reading_engine/providers.py")
    core_prov_py = read_text(CORE / "scripts/reading_engine/providers.py")
    providers_hash_same = sha(SIGNED / "scripts/reading_engine/providers.py") == sha(
        CORE / "scripts/reading_engine/providers.py"
    )
    signed_cu = claim_ids(signed_prov_py)
    core_cu = claim_ids(core_prov_py)
    extra_core_cu = [x for x in core_cu if x not in signed_cu]
    wenshi_cu_signed = [x for x in signed_cu if any(k in x.lower() or k in x for k in CU_NEEDLES)]
    wenshi_cu_core = [x for x in core_cu if any(k in x.lower() or k in x for k in CU_NEEDLES)]
    class_names = (
        "WenshiProvider",
        "CanwenProvider",
        "WenShiProvider",
        "CanWenProvider",
    )
    provider_class_signed = {n: bool(re.search(rf"class\s+{n}\b", signed_prov_py)) for n in class_names}
    provider_class_core = {n: bool(re.search(rf"class\s+{n}\b", core_prov_py)) for n in class_names}
    providers_true_signed = count_hits(signed_prov_py, TRUE_TOKENS)
    providers_true_core = count_hits(core_prov_py, TRUE_TOKENS)

    evidence_all = read_text(SIGNED / "references/index/evidence-rules.jsonl")
    n_rules = sum(1 for line in evidence_all.splitlines() if line.strip())
    packs: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    mention_rows: list[str] = []
    trap_hecan_rows = 0
    trap_hepan_rows = 0
    trap_timecheck_rows = 0
    trap_hecan_line_rows = 0
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
        if "合参" in line or "hecan" in line:
            trap_hecan_line_rows += 1
        if any(k in blob.lower() or k in blob for k in ("hepan", "合盘")):
            trap_hepan_rows += 1
        if any(k in blob.lower() for k in ("time-check", "time_check", "寻时")):
            trap_timecheck_rows += 1
        is_pack = any(pref in pack.lower() or pref in pack for pref in PATH_KEYS)
        is_mention = any(k in blob.lower() or k in blob for k in PATH_KEYS) or ("问事" in blob)
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

    scope_text = read_text(SIGNED / SCOPE_PATH) if (SIGNED / SCOPE_PATH).exists() else ""
    scope_wenshi = parse_scope_routes(scope_text, "wenshi")
    scope_canwen = parse_scope_routes(scope_text, "canwen")
    scope_hash_same = False
    if (SIGNED / SCOPE_PATH).exists() and (CORE / SCOPE_PATH).exists():
        scope_hash_same = sha(SIGNED / SCOPE_PATH) == sha(CORE / SCOPE_PATH)

    signed_content, signed_traps_tok, signed_generic, signed_generic_sum = content_scan(SIGNED)
    core_content, core_traps_tok, core_generic, core_generic_sum = content_scan(CORE)
    signed_content_files = sorted(signed_content)
    core_content_files = sorted(core_content)
    core_only_content = sorted(set(core_content_files) - set(signed_content_files))
    signed_only_content = sorted(set(signed_content_files) - set(core_content_files))
    signed_generic_files = [r for r, _raw, _res in signed_generic]
    core_generic_files = [r for r, _raw, _res in core_generic]
    core_only_generic = sorted(set(core_generic_files) - set(signed_generic_files))
    both_generic = sorted(set(signed_generic_files) & set(core_generic_files))
    generic_hash_same = {
        rel: sha(SIGNED / rel) == sha(CORE / rel)
        for rel in both_generic
        if (SIGNED / rel).exists() and (CORE / rel).exists()
    }
    core_only_kind = {rel: classify_core_only(rel) for rel in core_only_generic}
    kind_counts = dict(Counter(core_only_kind.values()))
    impl_unsigned = [rel for rel, k in core_only_kind.items() if k == "engine_impl"]
    impl_unsigned += [
        rel
        for rel in sorted(set(core_content_files) & set(signed_content_files))
        if (SIGNED / rel).exists()
        and (CORE / rel).exists()
        and sha(SIGNED / rel) != sha(CORE / rel)
        and rel.endswith((".py", ".json"))
        and "fixtures" not in rel
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
    brief_same = sha(SIGNED / "scripts/reading_engine/brief.py") == sha(
        CORE / "scripts/reading_engine/brief.py"
    )
    evid_py_same = sha(SIGNED / "scripts/reading_engine/evidence_rules.py") == sha(
        CORE / "scripts/reading_engine/evidence_rules.py"
    )

    signed_fx = fixture_names(SIGNED)
    core_fx = fixture_names(CORE)
    v52_fx = fixture_names(V52) if V52.exists() else []
    gold_ids = host_gold_ids()

    brief = read_text(SIGNED / "scripts/reading_engine/brief.py")
    evid_py = read_text(SIGNED / "scripts/reading_engine/evidence_rules.py")
    needles = list(dict.fromkeys(TRUE_TOKENS + gold_ids + GOLD_NEEDLES + ["references/fixtures"]))
    brief_hits = count_hits(brief, needles)
    evid_py_hits = count_hits(evid_py, needles)
    evid_jsonl_hits = count_hits(evidence_all, needles)
    signed_residual = sum(res for _r, _raw, res in signed_generic)
    core_residual = sum(res for _r, _raw, res in core_generic)
    signed_raw_wenshi = sum(raw for _r, raw, _res in signed_generic)
    core_raw_wenshi = sum(raw for _r, raw, _res in core_generic)

    v52_true = {t: 0 for t in TRUE_TOKENS}
    if V52.exists():
        v52_content, _v52_traps, _v52_gen, _v52_gs = content_scan(V52)
        v52_true = {tok: sum(d.get(tok, 0) for d in v52_content.values()) for tok in TRUE_TOKENS}

    prepare_hits: dict[str, dict[str, int]] = {}
    for p in PREPARE_PATHS:
        if not p.exists():
            prepare_hits[str(p)] = {"exists": 0}
            continue
        t = read_text(p)
        prepare_hits[str(p)] = {
            "exists": 1,
            **count_hits(t, TRUE_TOKENS + gold_ids),
        }

    catalog_hits: dict[str, dict[str, int] | None] = {}
    for label, root in (("signed", SIGNED), ("core", CORE), ("v52_contrast", V52)):
        p = root / "resources/runtime/catalog-v1.json"
        if not p.exists():
            catalog_hits[label] = None
            continue
        catalog_hits[label] = count_hits(read_text(p), list(TRUE_TOKENS) + ["问事"])

    signed_true_sum = {tok: sum(d.get(tok, 0) for d in signed_content.values()) for tok in TRUE_TOKENS}
    core_true_sum = {tok: sum(d.get(tok, 0) for d in core_content.values()) for tok in TRUE_TOKENS}
    signed_true_total = sum(signed_true_sum.values())
    core_true_total = sum(core_true_sum.values())
    gold_in_brief = sum(brief_hits.get(g, 0) for g in gold_ids)
    gold_in_evid_py = sum(evid_py_hits.get(g, 0) for g in gold_ids)
    gold_in_jsonl = sum(evid_jsonl_hits.get(g, 0) for g in gold_ids)
    true_in_brief = sum(brief_hits.get(t, 0) for t in TRUE_TOKENS)
    true_in_evid_py = sum(evid_py_hits.get(t, 0) for t in TRUE_TOKENS)
    true_in_jsonl = sum(evid_jsonl_hits.get(t, 0) for t in TRUE_TOKENS)
    prepare_true = sum(
        v.get(t, 0) for v in prepare_hits.values() for t in TRUE_TOKENS if isinstance(v.get(t), int)
    )
    prepare_gold = sum(
        v.get(g, 0) for v in prepare_hits.values() for g in gold_ids if isinstance(v.get(g), int)
    )

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
    print(f"v52_contrast_true_token_sum={sum(v52_true.values())}")
    print(f"signed_providers={signed_provs}")
    print(f"core_providers={core_provs}")
    print(f"signed_provider_n={len(signed_provs)}")
    print(f"wenshi_providers_signed={wenshi_provs_signed}")
    print(f"wenshi_providers_core={wenshi_provs_core}")
    print(f"extra_core_providers={extra_core_provs}")
    print(f"single_art_providers_not_mixed={single_arts}")
    print(f"provider_class_signed={provider_class_signed}")
    print(f"provider_class_core={provider_class_core}")
    print(f"providers_hash_same={providers_hash_same}")
    print(f"providers_true_signed_sum={sum(providers_true_signed.values())}")
    print(f"providers_true_core_sum={sum(providers_true_core.values())}")
    print(f"signed_cu={signed_cu}")
    print(f"core_cu={core_cu}")
    print(f"extra_core_cu={extra_core_cu}")
    print(f"wenshi_cu_signed={wenshi_cu_signed}")
    print(f"wenshi_cu_core={wenshi_cu_core}")
    print(f"signed_path_hits_n={len(signed_path_hits)}")
    print(f"signed_path_hits={signed_path_hits}")
    print(f"core_path_hits_n={len(core_path_hits)}")
    print(f"core_path_hits={core_path_hits}")
    print(f"signed_content_files_n={len(signed_content_files)}")
    print(f"signed_content_files={signed_content_files}")
    print(f"signed_true_token_sum={signed_true_sum}")
    print(f"signed_true_token_total={signed_true_total}")
    print(f"core_content_files_n={len(core_content_files)}")
    print(f"core_content_files={core_content_files}")
    print(f"core_true_token_sum={core_true_sum}")
    print(f"core_true_token_total={core_true_total}")
    print(f"core_only_true_content={core_only_content}")
    print(f"signed_only_true_content={signed_only_content}")
    print(f"signed_generic_wenshi_files={signed_generic}")
    print(f"core_generic_wenshi_files={core_generic}")
    print(f"signed_问事_raw={signed_raw_wenshi}")
    print(f"signed_问事_residual={signed_residual}")
    print(f"core_问事_raw={core_raw_wenshi}")
    print(f"core_问事_residual={core_residual}")
    print(f"signed_generic_phrase_sum={signed_generic_sum}")
    print(f"core_generic_phrase_sum={core_generic_sum}")
    print(f"core_only_generic_n={len(core_only_generic)}")
    print(f"core_only_generic={core_only_generic}")
    print(f"core_only_kind={core_only_kind}")
    print(f"core_only_kind_counts={kind_counts}")
    print(f"generic_both_hash_same={generic_hash_same}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")
    print(f"content_engine_wenshi_files={content_engine}")
    print(f"content_engine_wenshi_diff={content_engine_diff}")
    print(f"turns_hash_same={turns_same}")
    print(f"brief_hash_same={brief_same}")
    print(f"evidence_py_hash_same={evid_py_same}")
    print(f"evidence_rules_total={n_rules}")
    print(f"wenshi_packs={packs}")
    print(f"wenshi_pack_n={len(packs)}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"verified_n={len(verified_ids)}")
    print(f"wenshi_mention_not_pack={mention_rows}")
    print(f"wenshi_mention_not_pack_n={len(mention_rows)}")
    print(f"trap_hecan_packpath_rows={trap_hecan_rows}")
    print(f"trap_hecan_line_rows={trap_hecan_line_rows}")
    print(f"trap_hepan_rows={trap_hepan_rows}")
    print(f"trap_timecheck_rows={trap_timecheck_rows}")
    print(f"signed_trap_token_totals={signed_traps_tok}")
    print(f"core_trap_token_totals={core_traps_tok}")
    print(f"scope_route_wenshi={scope_wenshi}")
    print(f"scope_route_canwen={scope_canwen}")
    print(f"scope_hash_same={scope_hash_same}")
    print(f"evidence_rules_hash_same={evidence_hash_same}")
    print(f"golden_fixture_in_signed={signed_fx}")
    print(f"golden_fixture_in_core={core_fx}")
    print(f"golden_fixture_in_v52_contrast={v52_fx}")
    print(f"golden_id_n={len(gold_ids)}")
    print(f"golden_ids={gold_ids}")
    print(f"brief_true_token_hits={true_in_brief}")
    print(f"brief_golden_id_hits={gold_in_brief}")
    print(f"brief_loads_fixtures={'references/fixtures' in brief}")
    print(f"brief_needle_hits={ {k: v for k, v in brief_hits.items() if v} }")
    print(f"evidence_py_true_token_hits={true_in_evid_py}")
    print(f"evidence_py_golden_id_hits={gold_in_evid_py}")
    print(f"evidence_py_loads_fixtures={'references/fixtures' in evid_py}")
    print(f"evidence_py_needle_hits={ {k: v for k, v in evid_py_hits.items() if v} }")
    print(f"evidence_jsonl_true_token_hits={true_in_jsonl}")
    print(f"evidence_jsonl_golden_id_hits={gold_in_jsonl}")
    print(f"evidence_jsonl_needle_hits={ {k: v for k, v in evid_jsonl_hits.items() if v} }")
    print(f"prepare_hits={prepare_hits}")
    print(f"prepare_true_sum={prepare_true}")
    print(f"prepare_gold_sum={prepare_gold}")
    print(f"catalog_hits={catalog_hits}")
    print(
        "CONCLUSION_1 "
        f"pin_ok={pin_ok} v52_mix={v52_mix} "
        f"provider={wenshi_provs_signed} class={provider_class_signed} "
        f"CU={wenshi_cu_signed} packs={packs} pack_n={len(packs)} "
        f"active={len(active_ids)} verified={len(verified_ids)} "
        f"path_hits={len(signed_path_hits)} "
        f"signed_true_total={signed_true_total} "
        f"signed_问事_raw={signed_raw_wenshi} signed_问事_residual={signed_residual} "
        f"scope_wenshi={len(scope_wenshi)} scope_canwen={len(scope_canwen)} "
        f"golden_in_signed={signed_fx} "
        f"providers_n={len(signed_provs)} single_arts={single_arts} "
        f"excluded_hecan_line_rows={trap_hecan_line_rows} "
        f"excluded_hepan_rows={trap_hepan_rows} "
        f"excluded_timecheck_rows={trap_timecheck_rows} "
        f"v52_is_other={v52_is_other} v52_true_sum={sum(v52_true.values())}"
    )
    print(
        "CONCLUSION_2 "
        f"wenshi_providers_core={wenshi_provs_core} wenshi_cu_core={wenshi_cu_core} "
        f"providers_hash_same={providers_hash_same} "
        f"providers_true_core={sum(providers_true_core.values())} "
        f"extra_core_cu={extra_core_cu} "
        f"turns_hash_same={turns_same} "
        f"core_path_hits={len(core_path_hits)} "
        f"core_true_total={core_true_total} "
        f"core_问事_raw={core_raw_wenshi} core_问事_residual={core_residual} "
        f"core_only_generic_n={len(core_only_generic)} kind={kind_counts} "
        f"unsigned_impl_n={len(impl_unsigned)} "
        f"content_engine_diff={content_engine_diff} "
        f"core_fx={core_fx}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_true={true_in_brief} brief_golden_ids={gold_in_brief} "
        f"brief_loads_fixtures={'references/fixtures' in brief} "
        f"evidence_py_true={true_in_evid_py} evidence_py_golden_ids={gold_in_evid_py} "
        f"evidence_jsonl_true={true_in_jsonl} evidence_jsonl_golden_ids={gold_in_jsonl} "
        f"prepare_true={prepare_true} prepare_gold={prepare_gold} "
        f"golden_id_n={len(gold_ids)} "
        f"signed_fx={signed_fx} core_fx={core_fx} "
        f"v52_not_mixed_into_v53={v52_is_other and not v52_mix}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
