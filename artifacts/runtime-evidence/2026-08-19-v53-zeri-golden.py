#!/usr/bin/env python3
"""Read-only: 择日 / zeri / selection — signed V53 vs core. Admission pin first."""
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
PATH_KEYS = ("zeri", "selection", "date-selection", "date_selection")
# 寻时 / 运势 / 太乙 / 风水 / 模型选型 不是择日。
OTHER_ART_TRAPS = (
    "time-check",
    "time_check",
    "timecheck",
    "fortune",
    "taiyi",
    "fengshui",
    "feng-shui",
)
MODEL_SELECTION_TRAPS = ("model-selection", "model_selection")
SCOPE_PATH = Path("references/matrices/evidence-scope-bindings-v1.yaml")
IMPL_RELS = [
    "scripts/reading_engine/selection.py",
    "resources/runtime/providers/selection.json",
    "references/matrices/selection-source-tables-v1.yaml",
    "references/matrices/selection-fact-layer-profile.yaml",
]
FX_NAME = "selection-v51.yaml"
SECTION_KEYS = (
    "published_calendar_cases",
    "event_fact_formula_cases",
    "external_reference_cases",
    "completion_cases",
    "boundary_cases",
    "event_profile_cases",
    "event_rule_cases",
    "no_candidate_cases",
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


def is_model_selection_trap(rel: str) -> bool:
    low = rel.lower()
    return any(t in low for t in MODEL_SELECTION_TRAPS)


def is_other_art_trap(rel: str) -> bool:
    low = rel.lower()
    if "selection" in low or "zeri" in low or "择日" in rel:
        return False
    return any(t in low for t in OTHER_ART_TRAPS)


def is_zeri_path(rel: str) -> bool:
    if is_model_selection_trap(rel) or is_other_art_trap(rel):
        return False
    low = rel.lower()
    return any(k in low for k in PATH_KEYS) or "择日" in rel


def path_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            if is_zeri_path(rel):
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
    if is_model_selection_trap(rel):
        return "trap_model_selection"
    if rel.endswith("-v51.yaml") or rel.startswith("references/fixtures/"):
        return "fixture_oracle"
    if (
        rel.startswith("scripts/test_")
        or rel.startswith("scripts/audit_")
        or rel.startswith("scripts/build_selection")
        or rel.endswith("_fixture_generator.py")
        or rel.endswith("selection_formula_reference.py")
    ):
        return "test_or_audit"
    if (
        rel.startswith("references/books/")
        or rel.startswith("references/system-cards/")
        or rel.startswith("vendor/selection-sources/")
        or rel.startswith("references/matrices/")
    ):
        return "book_notes"
    if rel.endswith(".py") and "/reading_engine/" in rel:
        return "engine_impl"
    return "other"


def parse_scope_selection(text: str) -> list[str]:
    ids: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        m = re.match(r"^  ([^:\s][^:]*):", raw)
        if m:
            current = m.group(1)
            continue
        if current and re.match(r"^    route:\s*selection\s*$", raw):
            ids.append(current)
    return ids


def is_selection_pack(pack: str) -> bool:
    p = pack.lower()
    if any(t in p for t in ("time-check", "fortune", "taiyi", "fengshui")):
        return False
    return p.startswith("selection/") or "择日" in pack


def top_level_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    keys: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z0-9_]+):", line)
        if m:
            keys.append((i, m.group(1)))
    out: list[tuple[str, str]] = []
    for idx, (start, key) in enumerate(keys):
        end = keys[idx + 1][0] if idx + 1 < len(keys) else len(lines)
        out.append((key, "\n".join(lines[start:end])))
    return out


def section_ids(chunk: str) -> list[str]:
    dash = re.findall(r"(?m)^- id:\s+(\S+)", chunk)
    inline = re.findall(r"\{id:\s*([A-Za-z0-9_.\-]{4,})", chunk)
    quoted = re.findall(r'"id"\s*:\s*"([^"]+)"', chunk)
    return [x for x in dict.fromkeys(dash + inline + quoted) if len(x) >= 4]


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
        r for r in both if r.startswith("references/books/selection/") and r.endswith("/rules.md")
    )
    book_quotes = sorted(
        r
        for r in both
        if r.startswith("references/books/selection/") and r.endswith("/quote-index.md")
    )
    book_tables = sorted(
        r
        for r in both
        if r.startswith("references/books/selection/") and r.endswith("/monthly-day-table.md")
    )
    impl_rels = IMPL_RELS + book_rules + book_quotes + book_tables
    impl_same = {r: hash_cmp.get(r, False) for r in impl_rels}

    signed_prov = (SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    core_prov = (CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    signed_cu = claim_ids(signed_prov)
    core_cu = claim_ids(core_prov)
    selection_cu_signed = [
        x
        for x in signed_cu
        if any(k in x.lower() for k in ("selection", "zeri", "date-selection"))
    ]
    selection_cu_core = [
        x
        for x in core_cu
        if any(k in x.lower() for k in ("selection", "zeri", "date-selection"))
    ]
    signed_cls = extract_class(signed_prov, "class SelectionProvider")
    core_cls = extract_class(core_prov, "class SelectionProvider")
    signed_tc_cls = extract_class(signed_prov, "class TimeCheckProvider")
    providers_py_identical = sha(SIGNED / "scripts/reading_engine/providers.py") == sha(
        CORE / "scripts/reading_engine/providers.py"
    )

    j = json.loads((SIGNED / "resources/runtime/providers/selection.json").read_text(encoding="utf-8"))
    rc = j.get("runtime_capability") or {}
    outs = list(rc.get("outputs") or [])
    out_bind = [b.get("name") for b in (rc.get("output_bindings") or [])]
    ext_outs = list(rc.get("extension_outputs") or [])
    ext_bind = [b.get("name") for b in (rc.get("extension_output_bindings") or [])]
    find_ids = [b.get("id") for b in (rc.get("finding_bindings") or [])]
    selection_src = (SIGNED / "scripts/reading_engine/selection.py").read_text(encoding="utf-8")
    adapter = re.search(r'ADAPTER_VERSION\s*=\s*"([^"]+)"', selection_src) or re.search(
        r'PROVIDER_VERSION\s*=\s*"([^"]+)"', selection_src
    )
    provider_id_py = re.search(r'provider_id\s*=\s*"([^"]+)"', signed_cls)
    src_route = re.search(r"SOURCE_ROUTE\s*=\s*\{(.*?)\n    \}", signed_cls, re.S)
    src_body = src_route.group(1) if src_route else ""
    packs_m = re.search(r'"packs":\s*\[(.*?)\]', src_body, re.S)
    cmp_m = re.search(r'"default_comparison_packs":\s*\[(.*?)\]', src_body, re.S)
    source_route_packs = re.findall(r'"([^"]+)"', packs_m.group(1)) if packs_m else []
    source_route_cmp_packs = re.findall(r'"([^"]+)"', cmp_m.group(1)) if cmp_m else []

    tc_json_path = SIGNED / "resources/runtime/providers/time-check.json"
    fortune_json_path = SIGNED / "resources/runtime/providers/fortune.json"
    taiyi_json_path = SIGNED / "resources/runtime/providers/taiyi.json"
    fengshui_json_path = SIGNED / "resources/runtime/providers/fengshui.json"
    other_provider_ids = {
        "time-check": json.loads(tc_json_path.read_text(encoding="utf-8")).get("id")
        if tc_json_path.exists()
        else None,
        "fortune": json.loads(fortune_json_path.read_text(encoding="utf-8")).get("id")
        if fortune_json_path.exists()
        else None,
        "taiyi": json.loads(taiyi_json_path.read_text(encoding="utf-8")).get("id")
        if taiyi_json_path.exists()
        else None,
        "fengshui": json.loads(fengshui_json_path.read_text(encoding="utf-8")).get("id")
        if fengshui_json_path.exists()
        else None,
    }

    packs: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    status_counter: Counter[str] = Counter()
    n_rules = 0
    selection_rule_rows = 0
    trap_other_art_rows = 0
    trap_model_selection_rows = 0
    trap_fengshui_xuanze_rows = 0
    evidence_all = (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8")
    for line in evidence_all.splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        rid = str(row.get("rule_id") or "")
        path = str(row.get("source_path") or "")
        blob = f"{pack}\n{rid}\n{path}"
        low = blob.lower()
        if any(t in low for t in MODEL_SELECTION_TRAPS):
            trap_model_selection_rows += 1
        if any(t in low for t in ("time-check", "fortune/", "taiyi", "fengshui/")) and not is_selection_pack(pack):
            trap_other_art_rows += 1
        if pack.startswith("fengshui/") and ("选择" in json.dumps(row, ensure_ascii=False) or "择日" in json.dumps(row, ensure_ascii=False)):
            trap_fengshui_xuanze_rows += 1
        if not (
            is_selection_pack(pack)
            or rid.startswith("selection/")
            or "/selection/" in path
            or "择日" in pack
        ):
            continue
        selection_rule_rows += 1
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
    scope_ids = parse_scope_selection(scope_text)
    core_scope = CORE / SCOPE_PATH
    scope_hash_same = False
    if (SIGNED / SCOPE_PATH).exists() and core_scope.exists():
        scope_hash_same = sha(SIGNED / SCOPE_PATH) == sha(core_scope)

    fx_signed = (SIGNED / "references/fixtures" / FX_NAME).exists()
    fx_core = CORE / "references/fixtures" / FX_NAME
    fx_text = fx_core.read_text(encoding="utf-8") if fx_core.exists() else ""
    section_id_map: dict[str, list[str]] = {k: [] for k in SECTION_KEYS}
    for key, chunk in top_level_sections(fx_text):
        ids = section_ids(chunk)
        if key in section_id_map:
            section_id_map[key] = ids
        elif ids:
            section_id_map[key] = ids
    fx_all_ids = list(dict.fromkeys(id_ for ids in section_id_map.values() for id_ in ids))
    fx_schema = ""
    sm = re.search(r"(?m)^schema_version:\s+(\S+)", fx_text)
    if sm:
        fx_schema = sm.group(1)
    fx_profile = ""
    pm = re.search(r"(?m)^profile_id:\s+(\S+)", fx_text)
    if pm:
        fx_profile = pm.group(1)
    table_profile_hits = selection_src.count("xieji-official-cnlunar-v1")
    table_profile_loads_fixture = (
        "references/fixtures" in selection_src or "selection-v51" in selection_src
    )

    scope_fixture_hits = 0
    for nid in fx_all_ids:
        if nid in scope_text:
            scope_fixture_hits += 1

    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    evid_py = (SIGNED / "scripts/reading_engine/evidence_rules.py").read_text(encoding="utf-8")
    needles = [
        "selection-v51",
        "mingli-selection-fixtures-v51",
        "xieji-official-cnlunar-v1",
        "classical_case",
        "event_fact_formula_cases",
        "published_calendar_cases",
    ] + fx_all_ids
    needles = list(dict.fromkeys(needles))
    brief_hits = count_hits(brief, needles)
    evid_py_hits = count_hits(evid_py, needles)
    selection_py_fixture_hits = count_hits(selection_src, needles)
    evidence_fixture_hits = count_hits(evidence_all, needles)
    brief_selection_hits = len(re.findall(r"selection|zeri|择日", brief, re.I))
    evid_py_selection_hits = len(re.findall(r"selection|zeri|择日", evid_py, re.I))
    selection_py_claim = selection_src.count("claim_unit")
    cls_claim = signed_cls.count("claim_unit")
    brief_loads_fixtures = "references/fixtures" in brief or "selection-v51" in brief
    evid_loads_fixtures = "references/fixtures" in evid_py or "selection-v51" in evid_py

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
        if not re.search(r"\bselection\b|zeri|择日", txt, re.I):
            continue
        rel = p.relative_to(CORE).as_posix()
        content_engine.append(rel)
        sp = SIGNED / rel
        if not sp.exists():
            content_engine_diff.append(rel + ":core_only")
        elif sha(sp) != sha(p) and rel.endswith("providers.py"):
            if signed_cls != core_cls:
                content_engine_diff.append(rel + ":SelectionProvider_diff")
        elif sha(sp) != sha(p) and rel != "scripts/reading_engine/providers.py":
            content_engine_diff.append(rel + ":hash_diff")

    evidence_hash_same = False
    core_evid = CORE / "references/index/evidence-rules.jsonl"
    if core_evid.exists():
        evidence_hash_same = sha(SIGNED / "references/index/evidence-rules.jsonl") == sha(core_evid)

    hash_mismatch = [rel for rel, ok in hash_cmp.items() if not ok]
    impl_mismatch = [rel for rel, ok in impl_same.items() if not ok]
    tc_overlap = [
        r
        for r in signed_hits
        if "time-check" in r.lower() or "time_check" in r.lower() or "寻时" in r
    ]
    fortune_overlap = [r for r in signed_hits if "fortune" in r.lower() or "运势" in r]
    taiyi_overlap = [r for r in signed_hits if "taiyi" in r.lower() or "太乙" in r]
    fengshui_overlap = [r for r in signed_hits if "fengshui" in r.lower() or "风水" in r]

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
    print(f"impl_all_identical={all(impl_same.values()) if impl_same else False}")
    print(f"impl_mismatch={impl_mismatch}")
    print(f"book_rules_n={len(book_rules)}")
    print(f"book_quotes_n={len(book_quotes)}")
    print(f"book_tables_n={len(book_tables)}")
    print(f"SelectionProvider_identical={signed_cls == core_cls and bool(signed_cls)}")
    print(f"providers_py_identical={providers_py_identical}")
    print(f"TimeCheckProvider_present={bool(signed_tc_cls)}")
    print(f"other_art_provider_ids={other_provider_ids}")
    print(f"signed_overlap_time_check={tc_overlap}")
    print(f"signed_overlap_fortune={fortune_overlap}")
    print(f"signed_overlap_taiyi={taiyi_overlap}")
    print(f"signed_overlap_fengshui={fengshui_overlap}")
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
    print(f"source_route_packs={source_route_packs}")
    print(f"source_route_default_comparison_packs={source_route_cmp_packs}")
    print(f"selection_cu_signed={selection_cu_signed}")
    print(f"selection_cu_core={selection_cu_core}")
    print(f"all_cu_signed={signed_cu}")
    print(f"all_cu_core={core_cu}")
    print(f"SelectionProvider_claim_unit={cls_claim}")
    print(f"selection_py_claim_unit={selection_py_claim}")
    print(f"evidence_rules_total={n_rules}")
    print(f"selection_rule_rows={selection_rule_rows}")
    print(f"selection_packs={packs}")
    print(f"selection_pack_n={len(packs)}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"runtime_active_rules={active_ids}")
    print(f"verified_n={len(verified_ids)}")
    print(f"verified_rules={verified_ids}")
    print(f"binding_status={dict(status_counter)}")
    print(f"trap_other_art_rows={trap_other_art_rows}")
    print(f"trap_model_selection_rows={trap_model_selection_rows}")
    print(f"trap_fengshui_xuanze_rows={trap_fengshui_xuanze_rows}")
    print(f"scope_binding_path={SCOPE_PATH.as_posix()}")
    print(f"scope_route_selection_n={len(scope_ids)}")
    print(f"scope_route_selection_ids={scope_ids}")
    print(f"scope_hash_same={scope_hash_same}")
    print(f"scope_fixture_id_hits={scope_fixture_hits}")
    print(f"golden_fixture_in_signed={fx_signed}")
    print(f"golden_fixture_in_core={fx_core.exists()}")
    print(f"fixture_schema_version={fx_schema}")
    print(f"fixture_profile_id={fx_profile}")
    for key in SECTION_KEYS:
        print(f"fixture_{key}_n={len(section_id_map[key])}")
        print(f"fixture_{key}_ids={section_id_map[key]}")
    print(f"fixture_all_ids_n={len(fx_all_ids)}")
    print(f"fixture_section_sum={sum(len(section_id_map[k]) for k in SECTION_KEYS)}")
    print(f"fixture_all_ids={fx_all_ids}")
    print(f"table_profile_hits_in_selection_py={table_profile_hits}")
    print(f"table_profile_loads_fixture={table_profile_loads_fixture}")
    print(f"brief_selection_token_hits={brief_selection_hits}")
    print(f"brief_loads_fixtures={brief_loads_fixtures}")
    print(f"evidence_rules_py_selection_hits={evid_py_selection_hits}")
    print(f"evidence_rules_py_loads_fixtures={evid_loads_fixtures}")
    print(f"brief_fixture_needle_hits={brief_hits}")
    print(f"evidence_rules_py_fixture_needle_hits={evid_py_hits}")
    print(f"selection_py_fixture_needle_hits={selection_py_fixture_hits}")
    print(f"evidence_rules_fixture_needle_hits={evidence_fixture_hits}")
    named_needles = {
        "selection-v51",
        "mingli-selection-fixtures-v51",
        "xieji-official-cnlunar-v1",
        "classical_case",
        "event_fact_formula_cases",
        "published_calendar_cases",
    }
    brief_id_hits_sum = sum(v for k, v in brief_hits.items() if k in fx_all_ids)
    evid_py_id_hits_sum = sum(v for k, v in evid_py_hits.items() if k in fx_all_ids)
    selection_py_id_hits_sum = sum(v for k, v in selection_py_fixture_hits.items() if k in fx_all_ids)
    evidence_id_hits_sum = sum(v for k, v in evidence_fixture_hits.items() if k in fx_all_ids)
    named_only = {k: brief_hits.get(k, 0) for k in named_needles}
    print(f"brief_fixture_hits_sum={sum(brief_hits.values())}")
    print(f"evidence_py_fixture_hits_sum={sum(evid_py_hits.values())}")
    print(f"selection_py_fixture_hits_sum={sum(selection_py_fixture_hits.values())}")
    print(f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())}")
    print(f"brief_fixture_id_hits_sum={brief_id_hits_sum}")
    print(f"evidence_py_fixture_id_hits_sum={evid_py_id_hits_sum}")
    print(f"selection_py_fixture_id_hits_sum={selection_py_id_hits_sum}")
    print(f"evidence_fixture_id_hits_sum={evidence_id_hits_sum}")
    print(f"named_needle_hits_in_brief={named_only}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")
    print(f"content_engine_selection_files={content_engine}")
    print(f"content_engine_selection_diff={content_engine_diff}")
    print(f"evidence_rules_hash_same={evidence_hash_same}")

    packs_s = {k: f"n={v['n']}/active={v['active']}/verified={v['verified']}" for k, v in packs.items()}
    section_ns = {k: len(v) for k, v in section_id_map.items()}
    print(
        "CONCLUSION_1 "
        f"provider={j.get('id')}/{provider_id_py.group(1) if provider_id_py else None} "
        f"outputs={len(outs)} extension_outputs={len(ext_outs)} finding_bindings={len(find_ids)} "
        f"CU={selection_cu_signed} dedicated_packs={packs_s} pack_n={len(packs)} "
        f"runtime_active={len(active_ids)} verified={len(verified_ids)} "
        f"SOURCE_ROUTE_packs={source_route_packs} "
        f"SOURCE_ROUTE_cmp={source_route_cmp_packs} "
        f"scope_route_selection={len(scope_ids)} golden_in_signed={fx_signed} "
        f"not_time_check_fortune_taiyi_fengshui=True"
    )
    print(
        "CONCLUSION_2 "
        f"impl_all_identical={all(impl_same.values()) if impl_same else False} "
        f"SelectionProvider_identical={signed_cls == core_cls and bool(signed_cls)} "
        f"core_only={len(core_only)} kind={kind_counts} unsigned_impl_n={len(impl_unsigned)} "
        f"content_engine_diff={content_engine_diff} hash_mismatch_n={len(hash_mismatch)} "
        f"core_fixture_all={len(fx_all_ids)} section_sum={sum(len(section_id_map[k]) for k in SECTION_KEYS)} "
        f"sections={section_ns}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_selection_hits={brief_selection_hits} "
        f"brief_loads_fixtures={brief_loads_fixtures} "
        f"brief_fixture_id_hits_sum={brief_id_hits_sum} "
        f"selection_py_fixture_id_hits_sum={selection_py_id_hits_sum} "
        f"evidence_fixture_id_hits_sum={evidence_id_hits_sum} "
        f"evidence_py_fixture_id_hits_sum={evid_py_id_hits_sum} "
        f"scope_fixture_id_hits={scope_fixture_hits} "
        f"table_profile_hits={table_profile_hits} "
        f"table_profile_loads_fixture={table_profile_loads_fixture} "
        f"finding_bindings_are_cu={bool(selection_cu_signed)}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
