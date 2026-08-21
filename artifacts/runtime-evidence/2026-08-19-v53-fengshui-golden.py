#!/usr/bin/env python3
"""Read-only: 风水 / fengshui — signed V53 vs core. Admission pin first."""
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
PATH_KEYS = ("fengshui", "feng-shui")
SCOPE_PATH = Path("references/matrices/evidence-scope-bindings-v1.yaml")
IMPL_RELS = [
    "scripts/reading_engine/fengshui.py",
    "resources/runtime/providers/fengshui.json",
    "references/matrices/fengshui-source-tables-v1.yaml",
]
# 八字《神峰通考》路径含 feng，不是风水。
SHENFENG_TRAP = "shenfeng"


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
            if SHENFENG_TRAP in low:
                continue
            if any(k in low for k in PATH_KEYS) or "风水" in rel:
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
    if (
        rel.startswith("scripts/test_")
        or rel.startswith("scripts/audit_")
        or rel.endswith("_fixture_reference.py")
    ):
        return "test_or_audit"
    if rel.startswith("references/books/") or rel.startswith("references/system-cards/"):
        return "book_notes"
    if rel.endswith(".py") and "/reading_engine/" in rel:
        return "engine_impl"
    return "other"


def parse_scope_fengshui(text: str) -> list[str]:
    ids: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        m = re.match(r"^  ([^:\s][^:]*):", raw)
        if m:
            current = m.group(1)
            continue
        if current and re.match(r"^    route:\s*fengshui\s*$", raw):
            ids.append(current)
    return ids


def is_fengshui_pack(pack: str) -> bool:
    p = pack.lower()
    if SHENFENG_TRAP in p:
        return False
    return p.startswith("fengshui/") or "fengshui" in p or "风水" in pack


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

    book_rules = sorted(
        r for r in both if r.startswith("references/books/fengshui/") and r.endswith("/rules.md")
    )
    book_quotes = sorted(
        r
        for r in both
        if r.startswith("references/books/fengshui/") and r.endswith("/quote-index.md")
    )
    impl_rels = IMPL_RELS + book_rules + book_quotes
    impl_same = {r: hash_cmp.get(r, False) for r in impl_rels}

    signed_prov = (SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    core_prov = (CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    signed_cu = claim_ids(signed_prov)
    core_cu = claim_ids(core_prov)
    fengshui_cu_signed = [x for x in signed_cu if "fengshui" in x.lower()]
    fengshui_cu_core = [x for x in core_cu if "fengshui" in x.lower()]
    signed_cls = extract_class(signed_prov, "class FengshuiProvider")
    core_cls = extract_class(core_prov, "class FengshuiProvider")
    providers_py_identical = sha(SIGNED / "scripts/reading_engine/providers.py") == sha(
        CORE / "scripts/reading_engine/providers.py"
    )

    j = json.loads((SIGNED / "resources/runtime/providers/fengshui.json").read_text(encoding="utf-8"))
    rc = j.get("runtime_capability") or {}
    outs = list(rc.get("outputs") or [])
    out_bind = [b.get("name") for b in (rc.get("output_bindings") or [])]
    ext_outs = list(rc.get("extension_outputs") or [])
    ext_bind = [b.get("name") for b in (rc.get("extension_output_bindings") or [])]
    find_ids = [b.get("id") for b in (rc.get("finding_bindings") or [])]
    fengshui_src = (SIGNED / "scripts/reading_engine/fengshui.py").read_text(encoding="utf-8")
    adapter = re.search(r'ADAPTER_VERSION\s*=\s*"([^"]+)"', fengshui_src) or re.search(
        r'PROVIDER_VERSION\s*=\s*"([^"]+)"', fengshui_src
    )
    provider_id_py = re.search(r'provider_id\s*=\s*"([^"]+)"', signed_cls)
    src_route = re.search(r"SOURCE_ROUTE\s*=\s*\{(.*?)\n    \}", signed_cls, re.S)
    static_packs = re.findall(r'"packs":\s*\[(.*?)\]', src_route.group(1) if src_route else "", re.S)
    source_route_static_packs = re.findall(r'"([^"]+)"', static_packs[0]) if static_packs and static_packs[0].strip() else []
    planning_packs = re.findall(
        r'"fengshui/[^"]+"',
        signed_cls,
    )
    planning_packs = list(dict.fromkeys(planning_packs))

    packs: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    status_counter: Counter[str] = Counter()
    n_rules = 0
    fengshui_rule_rows = 0
    trap_shenfeng_rows = 0
    evidence_all = (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8")
    for line in evidence_all.splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        rid = str(row.get("rule_id") or "")
        path = str(row.get("source_path") or "")
        if SHENFENG_TRAP in pack.lower() or SHENFENG_TRAP in rid.lower() or SHENFENG_TRAP in path.lower():
            trap_shenfeng_rows += 1
            continue
        is_row = (
            is_fengshui_pack(pack)
            or "fengshui" in rid.lower()
            or "fengshui" in path.lower()
            or "风水" in pack
        )
        if not is_row:
            continue
        fengshui_rule_rows += 1
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

    scope_text = (SIGNED / SCOPE_PATH).read_text(encoding="utf-8") if (SIGNED / SCOPE_PATH).exists() else ""
    scope_ids = parse_scope_fengshui(scope_text)
    core_scope = CORE / SCOPE_PATH
    scope_hash_same = False
    if (SIGNED / SCOPE_PATH).exists() and core_scope.exists():
        scope_hash_same = sha(SIGNED / SCOPE_PATH) == sha(core_scope)

    fx_signed = (SIGNED / "references/fixtures/fengshui-v51.yaml").exists()
    fx_core = CORE / "references/fixtures/fengshui-v51.yaml"
    fx_text = fx_core.read_text(encoding="utf-8") if fx_core.exists() else ""
    manifest_ids = re.findall(r"(?m)^\s+-\s+manifest_id:\s+(FS-\S+)", fx_text)
    inline_ids = re.findall(r"\{id:\s*(FS-[A-Za-z0-9_\-]+)", fx_text)
    block_ids = re.findall(r"(?m)^\s+- id:\s+(FS-\S+)", fx_text)
    fx_all_ids = list(dict.fromkeys(manifest_ids + inline_ids + block_ids))
    compass_ids = re.findall(
        r"\{id:\s*(FS-M\d+)",
        fx_text.split("bazhai_source_examples:", 1)[0] if "bazhai_source_examples:" in fx_text else "",
    )
    obs_chunk = ""
    if "complete_observation_fixtures:" in fx_text:
        obs_chunk = fx_text.split("complete_observation_fixtures:", 1)[1]
        obs_chunk = obs_chunk.split("special_observation_fixtures:", 1)[0]
    obs_ids = re.findall(r"(?m)^\s+- id:\s+(FS-\S+)", obs_chunk)
    spec_chunk = ""
    if "special_observation_fixtures:" in fx_text:
        spec_chunk = fx_text.split("special_observation_fixtures:", 1)[1]
        spec_chunk = spec_chunk.split("hashseed_spec:", 1)[0]
    spec_ids = re.findall(r"(?m)^\s+- id:\s+(FS-\S+)", spec_chunk)
    cats = re.findall(r"(?m)^\s+category:\s*([A-Za-z0-9_]+)", fx_text)
    cat_counter = dict(Counter(cats))
    bazhai_n = len(re.findall(r"house_gua:", fx_text))
    asset_svgs = sorted(
        r
        for r in core_only
        if r.startswith("references/fixtures/assets/fengshui/") and r.endswith(".svg")
    )

    scope_fixture_hits = 0
    for nid in fx_all_ids:
        if nid in scope_text:
            scope_fixture_hits += 1

    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    evid_py = (SIGNED / "scripts/reading_engine/evidence_rules.py").read_text(encoding="utf-8")
    needles = [
        "fengshui-v51",
        "mingli-fengshui-fixtures-v51",
        "classical_case",
        "FS-PARTIAL-01",
        "FS-CONFLICT-01",
        "FS-LOW-LIGHT",
        "FS-LOW-SCALE",
        "FS-LOW-VIEW",
        "FS-SCHOOL-01",
        "FS-SCOPE-01",
    ] + fx_all_ids
    needles = list(dict.fromkeys(needles))
    brief_hits = count_hits(brief, needles)
    evid_py_hits = count_hits(evid_py, needles)
    fengshui_py_fixture_hits = count_hits(fengshui_src, needles)
    evidence_fixture_hits = count_hits(evidence_all, needles)
    brief_fengshui_hits = len(re.findall(r"fengshui|风水", brief, re.I))
    evid_py_fengshui_hits = len(re.findall(r"fengshui|风水", evid_py, re.I))
    fengshui_py_claim = fengshui_src.count("claim_unit")
    cls_claim = signed_cls.count("claim_unit")
    brief_loads_fixtures = "references/fixtures" in brief or "fengshui-v51" in brief
    evid_loads_fixtures = "references/fixtures" in evid_py or "fengshui-v51" in evid_py

    core_only_kind = {rel: classify_core_only(rel) for rel in core_only}
    kind_counts = dict(Counter(core_only_kind.values()))
    impl_unsigned = [rel for rel in core_only if core_only_kind.get(rel) == "engine_impl"]
    impl_unsigned += [
        rel
        for rel in both
        if rel.endswith((".py", ".json", ".yaml"))
        and not hash_cmp.get(rel, True)
        and "fixtures" not in rel
        and not rel.endswith("providers.py")
    ]

    content_engine: list[str] = []
    content_engine_diff: list[str] = []
    engine_dir = CORE / "scripts/reading_engine"
    for p in sorted(engine_dir.glob("*.py")):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"fengshui|风水", txt, re.I):
            continue
        rel = p.relative_to(CORE).as_posix()
        content_engine.append(rel)
        sp = SIGNED / rel
        if not sp.exists():
            content_engine_diff.append(rel + ":core_only")
        elif sha(sp) != sha(p) and rel.endswith("providers.py"):
            if signed_cls != core_cls:
                content_engine_diff.append(rel + ":FengshuiProvider_diff")
        elif sha(sp) != sha(p) and rel != "scripts/reading_engine/providers.py":
            content_engine_diff.append(rel + ":hash_diff")

    evidence_hash_same = False
    core_evid = CORE / "references/index/evidence-rules.jsonl"
    if core_evid.exists():
        evidence_hash_same = sha(SIGNED / "references/index/evidence-rules.jsonl") == sha(core_evid)

    hash_mismatch = [rel for rel, ok in hash_cmp.items() if not ok]
    impl_mismatch = [rel for rel, ok in impl_same.items() if not ok]

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
    print(f"core_only_n={len(core_only)}")
    print(f"core_only={core_only}")
    print(f"core_only_kind={core_only_kind}")
    print(f"core_only_kind_counts={kind_counts}")
    print(f"signed_only={signed_only}")
    print(f"both_n={len(both)}")
    print(f"hash_mismatch={hash_mismatch}")
    print(f"hash_mismatch_n={len(hash_mismatch)}")
    print(f"impl_files_identical={impl_same}")
    print(f"impl_all_identical={all(impl_same.values())}")
    print(f"impl_mismatch={impl_mismatch}")
    print(f"book_rules_n={len(book_rules)}")
    print(f"book_quotes_n={len(book_quotes)}")
    print(f"FengshuiProvider_identical={signed_cls == core_cls and bool(signed_cls)}")
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
    print(f"extension_outputs={ext_outs}")
    print(f"extension_output_bindings={ext_bind}")
    print(f"extension_output_count={len(ext_outs)}")
    print(f"source_route_static_packs={source_route_static_packs}")
    print(f"planning_pack_literals={planning_packs}")
    print(f"fengshui_cu_signed={fengshui_cu_signed}")
    print(f"fengshui_cu_core={fengshui_cu_core}")
    print(f"all_cu_signed={signed_cu}")
    print(f"all_cu_core={core_cu}")
    print(f"FengshuiProvider_claim_unit={cls_claim}")
    print(f"fengshui_py_claim_unit={fengshui_py_claim}")
    print(f"evidence_rules_total={n_rules}")
    print(f"fengshui_rule_rows={fengshui_rule_rows}")
    print(f"fengshui_packs={packs}")
    print(f"fengshui_pack_n={len(packs)}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"runtime_active_rules={active_ids}")
    print(f"verified_n={len(verified_ids)}")
    print(f"verified_rules={verified_ids}")
    print(f"binding_status={dict(status_counter)}")
    print(f"trap_shenfeng_rows={trap_shenfeng_rows}")
    print(f"scope_binding_path={SCOPE_PATH.as_posix()}")
    print(f"scope_route_fengshui_n={len(scope_ids)}")
    print(f"scope_route_fengshui_ids={scope_ids}")
    print(f"scope_hash_same={scope_hash_same}")
    print(f"scope_fixture_id_hits={scope_fixture_hits}")
    print(f"golden_fixture_in_signed={fx_signed}")
    print(f"golden_fixture_in_core={fx_core.exists()}")
    print(f"fixture_manifest_ids={manifest_ids}")
    print(f"fixture_manifest_n={len(manifest_ids)}")
    print(f"fixture_compass_ids={compass_ids}")
    print(f"fixture_compass_n={len(compass_ids)}")
    print(f"fixture_obs_ids={obs_ids}")
    print(f"fixture_obs_n={len(obs_ids)}")
    print(f"fixture_special_ids={spec_ids}")
    print(f"fixture_special_n={len(spec_ids)}")
    print(f"fixture_all_ids={fx_all_ids}")
    print(f"fixture_all_n={len(fx_all_ids)}")
    print(f"fixture_category_counts={cat_counter}")
    print(f"bazhai_source_examples_n={bazhai_n}")
    print(f"core_asset_svgs={asset_svgs}")
    print(f"core_asset_svg_n={len(asset_svgs)}")
    print(f"brief_fengshui_token_hits={brief_fengshui_hits}")
    print(f"brief_loads_fixtures={brief_loads_fixtures}")
    print(f"evidence_rules_py_fengshui_hits={evid_py_fengshui_hits}")
    print(f"evidence_rules_py_loads_fixtures={evid_loads_fixtures}")
    print(f"brief_fixture_needle_hits={brief_hits}")
    print(f"evidence_rules_py_fixture_needle_hits={evid_py_hits}")
    print(f"fengshui_py_fixture_needle_hits={fengshui_py_fixture_hits}")
    print(f"evidence_rules_fixture_needle_hits={evidence_fixture_hits}")
    print(f"brief_fixture_hits_sum={sum(brief_hits.values())}")
    print(f"evidence_py_fixture_hits_sum={sum(evid_py_hits.values())}")
    print(f"fengshui_py_fixture_hits_sum={sum(fengshui_py_fixture_hits.values())}")
    print(f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")
    print(f"content_engine_fengshui_files={content_engine}")
    print(f"content_engine_fengshui_diff={content_engine_diff}")
    print(f"evidence_rules_hash_same={evidence_hash_same}")

    packs_s = {k: f"n={v['n']}/active={v['active']}/verified={v['verified']}" for k, v in packs.items()}
    print(
        "CONCLUSION_1 "
        f"provider={j.get('id')}/{provider_id_py.group(1) if provider_id_py else None} "
        f"outputs={len(outs)} extension_outputs={len(ext_outs)} finding_bindings={len(find_ids)} "
        f"CU={fengshui_cu_signed} dedicated_packs={packs_s} pack_n={len(packs)} "
        f"runtime_active={len(active_ids)} verified={len(verified_ids)} "
        f"SOURCE_ROUTE_static={source_route_static_packs} "
        f"planning_literals={planning_packs} "
        f"scope_route_fengshui={len(scope_ids)} golden_in_signed={fx_signed} "
        f"shenfeng_trap_rows={trap_shenfeng_rows}"
    )
    print(
        "CONCLUSION_2 "
        f"impl_all_identical={all(impl_same.values())} "
        f"FengshuiProvider_identical={signed_cls == core_cls and bool(signed_cls)} "
        f"core_only={len(core_only)} kind={kind_counts} unsigned_impl_n={len(impl_unsigned)} "
        f"content_engine_diff={content_engine_diff} hash_mismatch_n={len(hash_mismatch)} "
        f"core_fixture_all={len(fx_all_ids)} manifest={len(manifest_ids)} "
        f"compass={len(compass_ids)} obs={len(obs_ids)} special={len(spec_ids)} "
        f"bazhai_examples={bazhai_n} assets={len(asset_svgs)} cats={cat_counter}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_fengshui_hits={brief_fengshui_hits} "
        f"brief_loads_fixtures={brief_loads_fixtures} "
        f"brief_fixture_hits_sum={sum(brief_hits.values())} "
        f"fengshui_py_fixture_hits_sum={sum(fengshui_py_fixture_hits.values())} "
        f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())} "
        f"evidence_py_fixture_hits_sum={sum(evid_py_hits.values())} "
        f"scope_fixture_id_hits={scope_fixture_hits} "
        f"finding_bindings_are_cu={bool(fengshui_cu_signed)}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
