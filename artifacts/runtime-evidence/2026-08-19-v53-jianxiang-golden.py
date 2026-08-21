#!/usr/bin/env python3
"""Read-only: 见相 / jianxiang / physiognomy — signed V53 vs core. Admission pin first."""
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
LATIN_KEYS = ("physiognomy", "jianxiang", "mianxiang")
CN_KEYS = ("见相", "面相", "相术")
# 八字 / 风水 / 择日 / 合参 不得混进见相计数。
OTHER_SYSTEM_PATH = (
    "bazi/",
    "fengshui/",
    "selection/",
    "hecan",
    "hepan",
    "/relationship",
    "合参",
    "八字",
    "风水",
    "择日",
)
OTHER_PACK_PREFIX = ("bazi/", "fengshui/", "selection/")
SCOPE_PATH = Path("references/matrices/evidence-scope-bindings-v1.yaml")
IMPL_RELS = [
    "scripts/reading_engine/physiognomy.py",
    "resources/runtime/providers/physiognomy.json",
    "references/matrices/physiognomy-source-tables-v1.yaml",
]
ALGO_SAMPLES = Path("references/fixtures/algorithm-source-samples-v51.yaml")
FIXTURE_YAML = Path("references/fixtures/physiognomy-v51.yaml")
ANNOTATION = Path("references/fixtures/assets/physiognomy/annotation-manifest-v1.yaml")


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


def is_other_system_path(rel: str) -> bool:
    low = rel.lower()
    return any(k in low or k in rel for k in OTHER_SYSTEM_PATH)


def path_is_jianxiang(rel: str) -> bool:
    low = rel.lower()
    if any(k in low for k in LATIN_KEYS) or any(k in rel for k in CN_KEYS):
        return True
    return False


def path_hits(root: Path) -> tuple[list[str], list[str]]:
    hits: list[str] = []
    traps: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            if not path_is_jianxiang(rel):
                continue
            if is_other_system_path(rel):
                traps.append(rel)
                continue
            hits.append(rel)
    return sorted(hits), sorted(traps)


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


def parse_scope_physio(text: str) -> list[str]:
    ids: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        m = re.match(r"^  ([^:\s][^:]*):", raw)
        if m:
            current = m.group(1)
            continue
        if current and re.match(r"^    route:\s*physiognomy\s*$", raw):
            ids.append(current)
    return ids


def is_physio_pack(pack: str) -> bool:
    p = pack.lower()
    if any(p.startswith(pref) for pref in OTHER_PACK_PREFIX):
        return False
    return (
        p.startswith("physiognomy/")
        or "physiognomy" in p
        or "jianxiang" in p
        or "mianxiang" in p
        or any(k in pack for k in CN_KEYS)
    )


def alias_in_text(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in LATIN_KEYS) or any(k in text for k in CN_KEYS)


def split_fixture_sections(text: str) -> dict[str, str]:
    markers = ["complete_cases:", "boundary_cases:"]
    positions: list[tuple[str, int]] = []
    for name in markers:
        i = text.find("\n" + name)
        if i < 0:
            i = 0 if text.startswith(name) else -1
        else:
            i = i + 1
        if i >= 0:
            positions.append((name[:-1], i))
    positions.sort(key=lambda x: x[1])
    chunks: dict[str, str] = {}
    for idx, (name, start) in enumerate(positions):
        end = positions[idx + 1][1] if idx + 1 < len(positions) else len(text)
        chunks[name] = text[start:end]
    return chunks


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

    signed_hits, signed_traps = path_hits(SIGNED)
    core_hits, core_traps = path_hits(CORE)
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
        r
        for r in both
        if r.startswith("references/books/physiognomy/") and r.endswith("/rules.md")
    )
    book_quotes = sorted(
        r
        for r in both
        if r.startswith("references/books/physiognomy/") and r.endswith("/quote-index.md")
    )
    impl_rels = IMPL_RELS + book_rules + book_quotes
    impl_same = {r: hash_cmp.get(r, False) for r in impl_rels}

    signed_prov = (SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    core_prov = (CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    signed_cu = claim_ids(signed_prov)
    core_cu = claim_ids(core_prov)
    physio_cu_needles = ("physiognomy", "jianxiang", "mianxiang", "见相", "面相", "相术")
    physio_cu_signed = [
        x for x in signed_cu if any(k in x.lower() or k in x for k in physio_cu_needles)
    ]
    physio_cu_core = [
        x for x in core_cu if any(k in x.lower() or k in x for k in physio_cu_needles)
    ]
    signed_cls = extract_class(signed_prov, "class PhysiognomyProvider")
    core_cls = extract_class(core_prov, "class PhysiognomyProvider")
    providers_py_identical = sha(SIGNED / "scripts/reading_engine/providers.py") == sha(
        CORE / "scripts/reading_engine/providers.py"
    )

    j = json.loads(
        (SIGNED / "resources/runtime/providers/physiognomy.json").read_text(encoding="utf-8")
    )
    rc = j.get("runtime_capability") or {}
    outs = list(rc.get("outputs") or [])
    out_bind = [b.get("name") for b in (rc.get("output_bindings") or [])]
    ext_outs = list(rc.get("extension_outputs") or [])
    ext_bind = [b.get("name") for b in (rc.get("extension_output_bindings") or [])]
    find_ids = [b.get("id") for b in (rc.get("finding_bindings") or [])]
    physio_src = (SIGNED / "scripts/reading_engine/physiognomy.py").read_text(encoding="utf-8")
    adapter = re.search(r'ADAPTER_VERSION\s*=\s*"([^"]+)"', physio_src) or re.search(
        r'PROVIDER_VERSION\s*=\s*"([^"]+)"', physio_src
    )
    provider_id_py = re.search(r'provider_id\s*=\s*"([^"]+)"', signed_cls)
    src_route = re.search(r"SOURCE_ROUTE\s*=\s*\{(.*?)\n    \}", signed_cls, re.S)
    static_packs = re.findall(r'"packs":\s*\[(.*?)\]', src_route.group(1) if src_route else "", re.S)
    source_route_static_packs = (
        re.findall(r'"([^"]+)"', static_packs[0]) if static_packs and static_packs[0].strip() else []
    )
    source_priority = re.findall(
        r'"physiognomy/[^"]+"',
        re.search(r"SOURCE_PRIORITY\s*=\s*\((.*?)\)", signed_cls, re.S).group(1)
        if re.search(r"SOURCE_PRIORITY\s*=\s*\((.*?)\)", signed_cls, re.S)
        else "",
    )
    planning_packs = list(dict.fromkeys(re.findall(r'"physiognomy/[^"]+"', signed_cls)))

    packs: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    status_counter: Counter[str] = Counter()
    n_rules = 0
    physio_rule_rows = 0
    trap_other_rows = 0
    trap_other_detail: list[str] = []
    trap_bazi = 0
    trap_fengshui = 0
    trap_selection = 0
    trap_hecan = 0
    evidence_all = (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8")
    for line in evidence_all.splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        rid = str(row.get("rule_id") or "")
        path = str(row.get("source_path") or "")
        blob = pack + " " + rid + " " + path
        other_hit = False
        if pack.startswith("bazi/") or "bazi" in rid.lower() or path.startswith("references/books/bazi/"):
            trap_bazi += 1
            other_hit = True
        if (
            pack.startswith("fengshui/")
            or "fengshui" in rid.lower()
            or path.startswith("references/books/fengshui/")
        ):
            trap_fengshui += 1
            other_hit = True
        if (
            pack.startswith("selection/")
            or "selection" in rid.lower()
            or path.startswith("references/books/selection/")
        ):
            trap_selection += 1
            other_hit = True
        if any(k in blob.lower() or k in blob for k in ("hecan", "hepan", "合参")):
            trap_hecan += 1
            other_hit = True
        if other_hit and alias_in_text(blob):
            trap_other_rows += 1
            trap_other_detail.append(rid)
            continue
        if other_hit and not is_physio_pack(pack):
            continue
        is_row = (
            is_physio_pack(pack)
            or any(k in rid.lower() for k in LATIN_KEYS)
            or any(k in path.lower() for k in LATIN_KEYS)
            or any(k in pack or k in rid or k in path for k in CN_KEYS)
        )
        if not is_row:
            continue
        physio_rule_rows += 1
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
    scope_ids = parse_scope_physio(scope_text)
    core_scope = CORE / SCOPE_PATH
    scope_hash_same = False
    if (SIGNED / SCOPE_PATH).exists() and core_scope.exists():
        scope_hash_same = sha(SIGNED / SCOPE_PATH) == sha(core_scope)

    fx_signed = (SIGNED / FIXTURE_YAML).exists()
    fx_core = CORE / FIXTURE_YAML
    fx_text = fx_core.read_text(encoding="utf-8") if fx_core.exists() else ""
    sections = split_fixture_sections(fx_text)
    complete_ids = re.findall(r"(?m)^\s+- case_id:\s+(\S+)", sections.get("complete_cases", ""))
    boundary_ids = re.findall(r"(?m)^\s+- case_id:\s+(\S+)", sections.get("boundary_cases", ""))
    all_case_ids = list(dict.fromkeys(complete_ids + boundary_ids))
    cats = re.findall(r"(?m)^\s+category:\s*([A-Za-z0-9_]+)", fx_text)
    cat_counter = dict(Counter(cats))
    oid_n = len(re.findall(r"observation_id:\s*(oid-[A-Za-z0-9]+)", fx_text))
    tid_n = len(set(re.findall(r"target_id:\s*(tid-[A-Za-z0-9]+)", fx_text)))
    aid_n = len(set(re.findall(r"asset_id:\s*(aid-[A-Za-z0-9]+)", fx_text)))
    asset_svgs = sorted(
        r
        for r in core_only
        if r.startswith("references/fixtures/assets/physiognomy/") and r.endswith(".svg")
    )
    annotation_exists = (CORE / ANNOTATION).exists()
    annotation_signed = (SIGNED / ANNOTATION).exists()

    algo_core = CORE / ALGO_SAMPLES
    algo_text = algo_core.read_text(encoding="utf-8") if algo_core.exists() else ""
    algo_keys = re.findall(r"(?m)^  (physiognomy-[A-Za-z0-9_\-]+):", algo_text)
    algo_case_ids = re.findall(r"provider_fixture_case_id:\s*([A-Za-z0-9_\-]+)", algo_text)
    algo_signed = (SIGNED / ALGO_SAMPLES).exists()
    source_table_text = (
        SIGNED / "references/matrices/physiognomy-source-tables-v1.yaml"
    ).read_text(encoding="utf-8")
    source_table_fixture_ids = re.findall(
        r"fixture_case_id:\s*([A-Za-z0-9_\-]+)", source_table_text
    )
    source_table_loads_fixtures = "references/fixtures" in source_table_text

    scope_fixture_hits = 0
    for nid in all_case_ids:
        if nid in scope_text:
            scope_fixture_hits += 1

    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    evid_py = (SIGNED / "scripts/reading_engine/evidence_rules.py").read_text(encoding="utf-8")
    needles = [
        "physiognomy-v51",
        "mingli-physiognomy-fixtures-v1",
        "mingli-physiognomy-fixtures",
        "provider_fixture_case_id",
        "algorithm-source-samples-v51",
        "complete_cases",
        "boundary_cases",
        "classical_case",
    ] + all_case_ids + algo_keys + algo_case_ids
    needles = list(dict.fromkeys(needles))
    brief_hits = count_hits(brief, needles)
    evid_py_hits = count_hits(evid_py, needles)
    physio_py_fixture_hits = count_hits(physio_src, needles)
    evidence_fixture_hits = count_hits(evidence_all, needles)
    source_table_fixture_hits = count_hits(source_table_text, needles)
    alias_re = r"physiognomy|jianxiang|mianxiang|见相|面相|相术"
    brief_alias_hits = len(re.findall(alias_re, brief, re.I))
    evid_py_alias_hits = len(re.findall(alias_re, evid_py, re.I))
    physio_py_claim = physio_src.count("claim_unit")
    cls_claim = signed_cls.count("claim_unit")
    brief_loads_fixtures = "references/fixtures" in brief or "physiognomy-v51" in brief
    evid_loads_fixtures = "references/fixtures" in evid_py or "physiognomy-v51" in evid_py
    physio_loads_fixtures = "references/fixtures" in physio_src or "physiognomy-v51" in physio_src

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
    content_re = re.compile(alias_re, re.I)
    for p in sorted(engine_dir.glob("*.py")):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if not content_re.search(txt):
            continue
        rel = p.relative_to(CORE).as_posix()
        content_engine.append(rel)
        sp = SIGNED / rel
        if not sp.exists():
            content_engine_diff.append(rel + ":core_only")
        elif sha(sp) != sha(p) and rel.endswith("providers.py"):
            if signed_cls != core_cls:
                content_engine_diff.append(rel + ":PhysiognomyProvider_diff")
        elif sha(sp) != sha(p) and rel != "scripts/reading_engine/providers.py":
            content_engine_diff.append(rel + ":hash_diff")

    evidence_hash_same = False
    core_evid = CORE / "references/index/evidence-rules.jsonl"
    if core_evid.exists():
        evidence_hash_same = sha(SIGNED / "references/index/evidence-rules.jsonl") == sha(core_evid)

    hash_mismatch = [rel for rel, ok in hash_cmp.items() if not ok]
    impl_mismatch = [rel for rel, ok in impl_same.items() if not ok]
    catalog_signed = json.loads((SIGNED / "references/catalog/catalog.json").read_text(encoding="utf-8"))
    catalog_physio = [
        item.get("id") or item.get("pack") or item.get("source_pack") or item
        for item in (catalog_signed.get("sources") or catalog_signed.get("items") or [])
        if isinstance(item, dict)
        and (
            item.get("system") == "physiognomy"
            or "physiognomy" in str(item.get("id") or "").lower()
            or "physiognomy" in str(item.get("skill_index_path") or "").lower()
        )
    ]
    if not catalog_physio:
        catalog_physio = []
        for item in catalog_signed.get("sources") or catalog_signed.get("books") or catalog_signed.get("entries") or []:
            if isinstance(item, dict) and item.get("system") == "physiognomy":
                catalog_physio.append(
                    item.get("id") or item.get("pack_id") or item.get("local_fulltext_path")
                )
        if not catalog_physio:
            blob = json.dumps(catalog_signed, ensure_ascii=False)
            catalog_physio = re.findall(r"physiognomy/([a-z0-9\-]+)", blob)
            catalog_physio = list(dict.fromkeys(catalog_physio))

    print(f"inspector={inspector}")
    print(f"source_commit={src}")
    print(f"manifest_files={n_man}")
    print(f"walk_files={n_walk}")
    print(f"pin_ok={pin_ok}")
    print(f"v52_mix_in_v53_turns={v52_mix}")
    print(f"signed_path_hits={len(signed_hits)}")
    print(f"signed_paths={signed_hits}")
    print(f"signed_other_system_traps={signed_traps}")
    print(f"core_path_hits={len(core_hits)}")
    print(f"core_paths={core_hits}")
    print(f"core_other_system_traps={core_traps}")
    print(f"core_only_n={len(core_only)}")
    print(f"core_only={core_only}")
    print(f"core_only_kind={core_only_kind}")
    print(f"core_only_kind_counts={kind_counts}")
    print(f"signed_only={signed_only}")
    print(f"both_n={len(both)}")
    print(f"hash_mismatch={hash_mismatch}")
    print(f"hash_mismatch_n={len(hash_mismatch)}")
    print(f"impl_files_identical={impl_same}")
    print(f"impl_all_identical={all(impl_same.values()) if impl_same else False}")
    print(f"impl_mismatch={impl_mismatch}")
    print(f"book_rules_n={len(book_rules)}")
    print(f"book_quotes_n={len(book_quotes)}")
    print(f"PhysiognomyProvider_identical={signed_cls == core_cls and bool(signed_cls)}")
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
    print(f"source_priority={source_priority}")
    print(f"planning_pack_literals={planning_packs}")
    print(f"catalog_physiognomy={catalog_physio}")
    print(f"catalog_physiognomy_n={len(catalog_physio)}")
    print(f"physio_cu_signed={physio_cu_signed}")
    print(f"physio_cu_core={physio_cu_core}")
    print(f"all_cu_signed={signed_cu}")
    print(f"all_cu_core={core_cu}")
    print(f"PhysiognomyProvider_claim_unit={cls_claim}")
    print(f"physiognomy_py_claim_unit={physio_py_claim}")
    print(f"evidence_rules_total={n_rules}")
    print(f"physio_rule_rows={physio_rule_rows}")
    print(f"physio_packs={packs}")
    print(f"physio_pack_n={len(packs)}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"runtime_active_rules={active_ids}")
    print(f"verified_n={len(verified_ids)}")
    print(f"verified_rules={verified_ids}")
    print(f"binding_status={dict(status_counter)}")
    print(f"trap_other_alias_in_other_packs={trap_other_rows}")
    print(f"trap_other_detail={trap_other_detail}")
    print(f"trap_bazi_rows_seen={trap_bazi}")
    print(f"trap_fengshui_rows_seen={trap_fengshui}")
    print(f"trap_selection_rows_seen={trap_selection}")
    print(f"trap_hecan_rows_seen={trap_hecan}")
    print(f"scope_binding_path={SCOPE_PATH.as_posix()}")
    print(f"scope_route_physiognomy_n={len(scope_ids)}")
    print(f"scope_route_physiognomy_ids={scope_ids}")
    print(f"scope_hash_same={scope_hash_same}")
    print(f"scope_fixture_id_hits={scope_fixture_hits}")
    print(f"golden_fixture_in_signed={fx_signed}")
    print(f"golden_fixture_in_core={fx_core.exists()}")
    print(f"fixture_complete_ids={complete_ids}")
    print(f"fixture_complete_n={len(complete_ids)}")
    print(f"fixture_boundary_ids={boundary_ids}")
    print(f"fixture_boundary_n={len(boundary_ids)}")
    print(f"fixture_all_case_ids={all_case_ids}")
    print(f"fixture_all_case_n={len(all_case_ids)}")
    print(f"fixture_category_counts={cat_counter}")
    print(f"fixture_observation_id_n={oid_n}")
    print(f"fixture_target_id_unique_n={tid_n}")
    print(f"fixture_asset_id_unique_n={aid_n}")
    print(f"core_asset_svgs={asset_svgs}")
    print(f"core_asset_svg_n={len(asset_svgs)}")
    print(f"annotation_manifest_in_core={annotation_exists}")
    print(f"annotation_manifest_in_signed={annotation_signed}")
    print(f"algo_samples_in_signed={algo_signed}")
    print(f"algo_samples_in_core={algo_core.exists()}")
    print(f"algo_physiognomy_keys={algo_keys}")
    print(f"algo_physiognomy_key_n={len(algo_keys)}")
    print(f"algo_fixture_case_ids={algo_case_ids}")
    print(f"source_table_fixture_case_ids={source_table_fixture_ids}")
    print(f"source_table_loads_fixtures_path={source_table_loads_fixtures}")
    print(f"brief_alias_hits={brief_alias_hits}")
    print(f"brief_loads_fixtures={brief_loads_fixtures}")
    print(f"evidence_rules_py_alias_hits={evid_py_alias_hits}")
    print(f"evidence_rules_py_loads_fixtures={evid_loads_fixtures}")
    print(f"physiognomy_py_loads_fixtures={physio_loads_fixtures}")
    print(f"brief_fixture_needle_hits={brief_hits}")
    print(f"evidence_rules_py_fixture_needle_hits={evid_py_hits}")
    print(f"physiognomy_py_fixture_needle_hits={physio_py_fixture_hits}")
    print(f"evidence_rules_fixture_needle_hits={evidence_fixture_hits}")
    print(f"source_table_fixture_needle_hits={source_table_fixture_hits}")
    print(f"brief_fixture_hits_sum={sum(brief_hits.values())}")
    print(f"evidence_py_fixture_hits_sum={sum(evid_py_hits.values())}")
    print(f"physiognomy_py_fixture_hits_sum={sum(physio_py_fixture_hits.values())}")
    print(f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())}")
    print(f"source_table_fixture_hits_sum={sum(source_table_fixture_hits.values())}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")
    print(f"content_engine_physio_files={content_engine}")
    print(f"content_engine_physio_diff={content_engine_diff}")
    print(f"evidence_rules_hash_same={evidence_hash_same}")

    packs_s = {k: f"n={v['n']}/active={v['active']}/verified={v['verified']}" for k, v in packs.items()}
    print(
        "CONCLUSION_1 "
        f"provider={j.get('id')}/{provider_id_py.group(1) if provider_id_py else None} "
        f"outputs={len(outs)} extension_outputs={len(ext_outs)} finding_bindings={len(find_ids)} "
        f"CU={physio_cu_signed} dedicated_packs={packs_s} pack_n={len(packs)} "
        f"runtime_active={len(active_ids)} verified={len(verified_ids)} "
        f"SOURCE_ROUTE_static={source_route_static_packs} "
        f"SOURCE_PRIORITY={source_priority} "
        f"scope_route_physiognomy={len(scope_ids)} golden_in_signed={fx_signed} "
        f"trap_other_alias={trap_other_rows} "
        f"excluded_bazi={trap_bazi} excluded_fengshui={trap_fengshui} "
        f"excluded_selection={trap_selection} excluded_hecan={trap_hecan}"
    )
    print(
        "CONCLUSION_2 "
        f"impl_all_identical={all(impl_same.values()) if impl_same else False} "
        f"PhysiognomyProvider_identical={signed_cls == core_cls and bool(signed_cls)} "
        f"core_only={len(core_only)} kind={kind_counts} unsigned_impl_n={len(impl_unsigned)} "
        f"content_engine_diff={content_engine_diff} hash_mismatch_n={len(hash_mismatch)} "
        f"core_fixture_cases={len(all_case_ids)} complete={len(complete_ids)} "
        f"boundary={len(boundary_ids)} assets={len(asset_svgs)} cats={cat_counter} "
        f"algo_keys={len(algo_keys)}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_alias_hits={brief_alias_hits} "
        f"brief_loads_fixtures={brief_loads_fixtures} "
        f"brief_fixture_hits_sum={sum(brief_hits.values())} "
        f"physiognomy_py_fixture_hits_sum={sum(physio_py_fixture_hits.values())} "
        f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())} "
        f"evidence_py_fixture_hits_sum={sum(evid_py_hits.values())} "
        f"scope_fixture_id_hits={scope_fixture_hits} "
        f"source_table_fixture_hits_sum={sum(source_table_fixture_hits.values())} "
        f"finding_bindings_are_cu={bool(physio_cu_signed)}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
