#!/usr/bin/env python3
"""Read-only: 梅花 / meihua — signed V53 vs core. Admission pin first."""
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
ADMITTED_MANIFEST = "c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b"
ADMITTED_SOURCE = "663543e65ae037843b03dca1dec9486293affc9d"
ADMITTED_FILES = 220
SKIP = {".git", "__pycache__", ".pytest_cache", "node_modules", ".mypy_cache"}
PATH_KEYS = ("meihua", "mei-hua", "梅花")
SCOPE_PATH = Path("references/matrices/evidence-scope-bindings-v1.yaml")
IMPL_RELS = [
    "scripts/reading_engine/meihua.py",
    "resources/runtime/providers/meihua.json",
    "references/matrices/meihua-source-tables-v1.yaml",
    "references/books/divination/meihua-yishu/rules.md",
    "references/books/divination/meihua-yishu/quote-index.md",
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
            if any(k in low for k in PATH_KEYS) or "梅花" in rel:
                hits.append(rel)
    return sorted(hits)


def claim_ids(text: str) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', text)


def extract_class(text: str, name: str) -> str:
    i = text.find(name)
    if i < 0:
        return ""
    rest = text[i:]
    m = re.search(r"\nclass ", rest[1:])
    return rest if not m else rest[: m.start() + 1]


def count_hits(text: str, needles: list[str]) -> dict[str, int]:
    return {n: text.count(n) for n in needles}


def classify_core_only(rel: str) -> str:
    if "/fixtures/" in rel or rel.endswith("-v51.yaml"):
        return "fixture_oracle"
    if rel.startswith("scripts/test_") or rel.startswith("scripts/audit_"):
        return "test_or_audit"
    if rel.startswith("references/books/"):
        return "book_notes"
    if rel.endswith(".py") and "/reading_engine/" in rel:
        return "engine_impl"
    return "other"


def parse_scope_meihua(text: str) -> list[str]:
    """Rule ids whose binding block has `route: meihua`."""
    ids: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        m = re.match(r"^  ([^:\s][^:]*):", raw)
        if m:
            current = m.group(1)
            continue
        if current and re.match(r"^    route:\s*meihua\s*$", raw):
            ids.append(current)
    return ids


def main() -> int:
    man_path = SIGNED / ".mingli-release-manifest.json"
    inspector = sha(man_path)
    man = json.loads(man_path.read_bytes())
    src = man.get("source_commit")
    n_man = len(man.get("files") or {})
    n_walk = len(walk_files(SIGNED))
    pin_ok = (
        inspector == ADMITTED_MANIFEST
        and src == ADMITTED_SOURCE
        and n_man == ADMITTED_FILES
        and n_walk == ADMITTED_FILES
    )
    turns = (SIGNED / "scripts/reading_engine/turns.py").read_text(encoding="utf-8")
    v52_mix = ("relationship_signals" in turns) or ("_append_runtime_relationship" in turns)

    signed_hits = path_hits(SIGNED)
    core_hits = path_hits(CORE)
    signed_set = set(signed_hits)
    core_set = set(core_hits)
    both = sorted(signed_set & core_set)
    core_only = sorted(core_set - signed_set)
    signed_only = sorted(signed_set - core_set)
    hash_cmp: dict[str, bool] = {}
    for rel in both:
        sp, cp = SIGNED / rel, CORE / rel
        hash_cmp[rel] = sp.exists() and cp.exists() and sha(sp) == sha(cp)
    impl_same = {r: hash_cmp.get(r, False) for r in IMPL_RELS}

    signed_prov = (SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    core_prov = (CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    signed_cu = claim_ids(signed_prov)
    core_cu = claim_ids(core_prov)
    meihua_cu_signed = [x for x in signed_cu if "meihua" in x.lower()]
    meihua_cu_core = [x for x in core_cu if "meihua" in x.lower()]
    signed_cls = extract_class(signed_prov, "class MeihuaProvider")
    core_cls = extract_class(core_prov, "class MeihuaProvider")
    providers_py_identical = sha(SIGNED / "scripts/reading_engine/providers.py") == sha(
        CORE / "scripts/reading_engine/providers.py"
    )

    j = json.loads((SIGNED / "resources/runtime/providers/meihua.json").read_text(encoding="utf-8"))
    rc = j.get("runtime_capability") or {}
    outs = list(rc.get("outputs") or [])
    out_bind = [b.get("name") for b in (rc.get("output_bindings") or [])]
    find_ids = [b.get("id") for b in (rc.get("finding_bindings") or [])]
    meihua_src = (SIGNED / "scripts/reading_engine/meihua.py").read_text(encoding="utf-8")
    adapter = re.search(r'PROVIDER_VERSION\s*=\s*"([^"]+)"', meihua_src) or re.search(
        r'ADAPTER_VERSION\s*=\s*"([^"]+)"', meihua_src
    )
    provider_id_py = re.search(r'provider_id\s*=\s*"([^"]+)"', signed_cls)
    src_route = re.search(r"SOURCE_ROUTE\s*=\s*\{(.*?)\n    \}", signed_cls, re.S)
    source_route_packs = re.findall(r'"((?:divination|san-shi)/[^"]+)"', src_route.group(1) if src_route else "")

    packs: dict[str, dict[str, int]] = {}
    route_pack_stats: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    status_counter: Counter[str] = Counter()
    n_rules = 0
    meihua_rule_rows = 0
    shared_route_rows: list[str] = []
    evidence_all = (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8")
    for line in evidence_all.splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        rid = str(row.get("rule_id") or "")
        path = str(row.get("source_path") or "")
        if pack in source_route_packs:
            route_pack_stats.setdefault(pack, {"n": 0, "active": 0, "verified": 0})
            route_pack_stats[pack]["n"] += 1
            if row.get("runtime_active"):
                route_pack_stats[pack]["active"] += 1
            if str(row.get("classical_binding_status") or "") == "verified":
                route_pack_stats[pack]["verified"] += 1
        is_meihua_row = (
            "meihua" in pack.lower()
            or "梅花" in pack
            or "meihua" in rid.lower()
            or "meihua" in path.lower()
        )
        if not is_meihua_row:
            continue
        meihua_rule_rows += 1
        packs.setdefault(pack, {"n": 0, "active": 0, "verified": 0})
        packs[pack]["n"] += 1
        st = str(row.get("classical_binding_status") or "")
        status_counter[st] += 1
        if row.get("runtime_active"):
            packs[pack]["active"] += 1
            active_ids.append(rid)
        if st == "verified":
            packs[pack]["verified"] += 1
            verified_ids.append(rid)

    # HR-04-01 / ZZR-M001 status (SOURCE_ROUTE shared, scoped to meihua)
    shared_ids = ("divination/huangji-jingshi#HR-04-01", "divination/zhouyi-zhezhong#ZZR-M001")
    shared_status: dict[str, dict[str, object]] = {}
    for line in evidence_all.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rid = str(row.get("rule_id") or "")
        if rid in shared_ids:
            shared_status[rid] = {
                "runtime_active": bool(row.get("runtime_active")),
                "classical_binding_status": row.get("classical_binding_status"),
                "source_pack": row.get("source_pack"),
            }
            shared_route_rows.append(rid)

    scope_text = (SIGNED / SCOPE_PATH).read_text(encoding="utf-8") if (SIGNED / SCOPE_PATH).exists() else ""
    scope_ids = parse_scope_meihua(scope_text)
    scope_fixture_hits = 0
    core_scope = CORE / SCOPE_PATH
    scope_hash_same = False
    if (SIGNED / SCOPE_PATH).exists() and core_scope.exists():
        scope_hash_same = sha(SIGNED / SCOPE_PATH) == sha(core_scope)

    fx_signed = (SIGNED / "references/fixtures/meihua-v51.yaml").exists()
    fx_core = CORE / "references/fixtures/meihua-v51.yaml"
    fx_text = fx_core.read_text(encoding="utf-8") if fx_core.exists() else ""
    fx_block_ids = re.findall(r"(?m)^\s+- id:\s+(\S+)", fx_text)
    fx_inline_ids = re.findall(r"\{id:\s*([A-Za-z0-9_\-]+)", fx_text)
    fx_all_ids = list(dict.fromkeys(fx_block_ids + fx_inline_ids))
    cats = re.findall(r"category:\s*([A-Za-z0-9_]+)", fx_text)
    cat_counter = dict(Counter(cats))
    replay_block = re.search(r"exact_method_cases:\n((?:    .+\n)+)", fx_text)
    replay_ids = re.findall(r"(?m)^    ([A-Za-z0-9_\-]+):", replay_block.group(1)) if replay_block else []
    cal_block = re.search(r"calendar_boundaries:\n((?:  .+\n)+)", fx_text)
    cal_ids = re.findall(r"\{id:\s*([A-Za-z0-9_\-]+)", cal_block.group(1) if cal_block else "")

    for nid in fx_all_ids:
        if nid in scope_text:
            scope_fixture_hits += 1

    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    evid_py = (SIGNED / "scripts/reading_engine/evidence_rules.py").read_text(encoding="utf-8")
    needles = ["meihua-v51", "classical_case", "mingli-meihua-fixtures-v51"] + fx_all_ids
    brief_hits = count_hits(brief, needles)
    evid_py_hits = count_hits(evid_py, needles)
    meihua_py_fixture_hits = count_hits(meihua_src, needles)
    evidence_fixture_hits = count_hits(evidence_all, needles)
    brief_meihua_hits = len(re.findall(r"meihua|梅花", brief, re.I))
    evid_py_meihua_hits = len(re.findall(r"meihua|梅花", evid_py, re.I))
    meihua_py_claim = meihua_src.count("claim_unit")
    cls_claim = signed_cls.count("claim_unit")
    brief_loads_fixtures = "references/fixtures" in brief or "meihua-v51" in brief
    evid_loads_fixtures = "references/fixtures" in evid_py or "meihua-v51" in evid_py

    core_only_kind = {rel: classify_core_only(rel) for rel in core_only}
    impl_unsigned = [
        rel for rel in core_only if core_only_kind.get(rel) == "engine_impl"
    ]
    impl_unsigned += [
        rel
        for rel in both
        if rel.endswith((".py", ".json", ".yaml"))
        and not hash_cmp.get(rel, True)
        and "fixtures" not in rel
        and not rel.endswith("providers.py")
    ]

    # content-scan: core reading_engine py mentioning meihua vs signed counterpart
    content_engine: list[str] = []
    content_engine_diff: list[str] = []
    engine_dir = CORE / "scripts/reading_engine"
    for p in sorted(engine_dir.glob("*.py")):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"meihua|梅花", txt, re.I):
            continue
        rel = p.relative_to(CORE).as_posix()
        content_engine.append(rel)
        sp = SIGNED / rel
        if not sp.exists():
            content_engine_diff.append(rel + ":core_only")
        elif sha(sp) != sha(p) and rel.endswith("providers.py"):
            # whole file may differ (bazi CU); class compare is the meihua seam
            if signed_cls != core_cls:
                content_engine_diff.append(rel + ":MeihuaProvider_diff")
        elif sha(sp) != sha(p) and rel != "scripts/reading_engine/providers.py":
            content_engine_diff.append(rel + ":hash_diff")

    liuyao_signed = (SIGNED / "scripts/reading_engine/liuyao.py").read_text(encoding="utf-8")
    liuyao_block = "time_based_meihua_casting" in liuyao_signed
    liuyao_hash_same = sha(SIGNED / "scripts/reading_engine/liuyao.py") == sha(
        CORE / "scripts/reading_engine/liuyao.py"
    )

    evidence_hash_same = False
    core_evid = CORE / "references/index/evidence-rules.jsonl"
    if core_evid.exists():
        evidence_hash_same = sha(SIGNED / "references/index/evidence-rules.jsonl") == sha(core_evid)

    print(f"inspector={inspector}")
    print(f"source_commit={src}")
    print(f"manifest_files={n_man}")
    print(f"walk_files={n_walk}")
    print(f"pin_ok={pin_ok}")
    print(f"v52_mix_in_v53_turns={v52_mix}")
    print(f"signed_path_hits={len(signed_hits)}")
    print(f"signed_paths={signed_hits}")
    print(f"core_path_hits={len(core_hits)}")
    print(f"core_paths={core_hits}")
    print(f"core_only={core_only}")
    print(f"core_only_kind={core_only_kind}")
    print(f"signed_only={signed_only}")
    print(f"hash_identical={hash_cmp}")
    print(f"impl_files_identical={impl_same}")
    print(f"impl_all_identical={all(impl_same.values())}")
    print(f"MeihuaProvider_identical={signed_cls == core_cls and bool(signed_cls)}")
    print(f"providers_py_identical={providers_py_identical}")
    print(f"provider_json_id={j.get('id')}")
    print(f"entrypoint={j.get('entrypoint')}")
    print(f"provider_id_py={provider_id_py.group(1) if provider_id_py else None}")
    print(f"adapter_version={adapter.group(1) if adapter else None}")
    print(f"evidence_profile_id={j.get('evidence_profile_id')}")
    print(f"finding_bindings={find_ids}")
    print(f"finding_bindings_count={len(find_ids)}")
    print(f"outputs={outs}")
    print(f"output_bindings={out_bind}")
    print(f"output_count={len(outs)}")
    print(f"source_route_packs={source_route_packs}")
    print(f"source_route_pack_stats={route_pack_stats}")
    print(f"meihua_cu_signed={meihua_cu_signed}")
    print(f"meihua_cu_core={meihua_cu_core}")
    print(f"all_cu_signed={signed_cu}")
    print(f"all_cu_core={core_cu}")
    print(f"MeihuaProvider_claim_unit={cls_claim}")
    print(f"meihua_py_claim_unit={meihua_py_claim}")
    print(f"evidence_rules_total={n_rules}")
    print(f"meihua_rule_rows={meihua_rule_rows}")
    print(f"meihua_packs={packs}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"runtime_active_rules={active_ids}")
    print(f"verified_n={len(verified_ids)}")
    print(f"verified_rules={verified_ids}")
    print(f"binding_status={dict(status_counter)}")
    print(f"scope_binding_path={SCOPE_PATH.as_posix()}")
    print(f"scope_route_meihua_n={len(scope_ids)}")
    print(f"scope_route_meihua_ids={scope_ids}")
    print(f"scope_hash_same={scope_hash_same}")
    print(f"scope_fixture_id_hits={scope_fixture_hits}")
    print(f"shared_route_rule_status={shared_status}")
    print(f"golden_fixture_in_signed={fx_signed}")
    print(f"golden_fixture_in_core={fx_core.exists()}")
    print(f"fixture_yaml_block_ids={fx_block_ids}")
    print(f"fixture_yaml_block_n={len(fx_block_ids)}")
    print(f"fixture_inline_ids={fx_inline_ids}")
    print(f"fixture_inline_n={len(fx_inline_ids)}")
    print(f"fixture_all_ids={fx_all_ids}")
    print(f"fixture_all_n={len(fx_all_ids)}")
    print(f"fixture_category_counts={cat_counter}")
    print(f"fixture_replay_case_ids={replay_ids}")
    print(f"fixture_replay_case_n={len(replay_ids)}")
    print(f"fixture_calendar_ids={cal_ids}")
    print(f"fixture_calendar_n={len(cal_ids)}")
    print(f"brief_meihua_token_hits={brief_meihua_hits}")
    print(f"brief_loads_fixtures={brief_loads_fixtures}")
    print(f"evidence_rules_py_meihua_hits={evid_py_meihua_hits}")
    print(f"evidence_rules_py_loads_fixtures={evid_loads_fixtures}")
    print(f"brief_fixture_needle_hits={brief_hits}")
    print(f"evidence_rules_py_fixture_needle_hits={evid_py_hits}")
    print(f"meihua_py_fixture_needle_hits={meihua_py_fixture_hits}")
    print(f"evidence_rules_fixture_needle_hits={evidence_fixture_hits}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")
    print(f"content_engine_meihua_files={content_engine}")
    print(f"content_engine_meihua_diff={content_engine_diff}")
    print(f"liuyao_blocks_time_based_meihua={liuyao_block}")
    print(f"liuyao_hash_same={liuyao_hash_same}")
    print(f"evidence_rules_hash_same={evidence_hash_same}")

    packs_s = {k: f"n={v['n']}/active={v['active']}/verified={v['verified']}" for k, v in packs.items()}
    route_s = {
        k: f"n={v['n']}/active={v['active']}/verified={v['verified']}" for k, v in route_pack_stats.items()
    }
    print(
        "CONCLUSION_1 "
        f"provider={j.get('id')}/{provider_id_py.group(1) if provider_id_py else None} "
        f"outputs={len(outs)} finding_bindings={len(find_ids)} "
        f"CU={meihua_cu_signed} dedicated_packs={packs_s} "
        f"runtime_active={len(active_ids)} verified={len(verified_ids)} "
        f"SOURCE_ROUTE={source_route_packs} route_pack_stats={route_s} "
        f"scope_route_meihua={len(scope_ids)} golden_in_signed={fx_signed}"
    )
    print(
        "CONCLUSION_2 "
        f"impl_all_identical={all(impl_same.values())} "
        f"MeihuaProvider_identical={signed_cls == core_cls and bool(signed_cls)} "
        f"core_only={len(core_only)} unsigned_impl_n={len(impl_unsigned)} "
        f"content_engine_diff={content_engine_diff} "
        f"core_fixture_all={len(fx_all_ids)} yaml_block={len(fx_block_ids)} "
        f"inline={len(fx_inline_ids)} replay_cases={len(replay_ids)} "
        f"calendar={len(cal_ids)} cats={cat_counter}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_meihua_hits={brief_meihua_hits} "
        f"brief_loads_fixtures={brief_loads_fixtures} "
        f"brief_fixture_hits_sum={sum(brief_hits.values())} "
        f"meihua_py_fixture_hits_sum={sum(meihua_py_fixture_hits.values())} "
        f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())} "
        f"evidence_py_fixture_hits_sum={sum(evid_py_hits.values())} "
        f"scope_fixture_id_hits={scope_fixture_hits} "
        f"finding_bindings_are_cu={bool(meihua_cu_signed)}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
