#!/usr/bin/env python3
"""Read-only: 太乙 / taiyi — signed V53 vs core. Admission pin first."""
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
PATH_KEYS = ("taiyi", "tai-yi")
# 六壬十二神「太乙」(巳) 不是太乙神数；路径过滤只用 latin token，正文另计 trap。
LIUREN_TRAP_PATHS = (
    "scripts/reading_engine/liuren.py",
    "scripts/liuren_fact_adapter.py",
    "scripts/liuren_calc.py",
    "resources/runtime/providers/liuren.json",
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


def path_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            low = rel.lower()
            if any(k in low for k in PATH_KEYS) or "太乙" in rel:
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


def is_taiyi_pack(pack: str) -> bool:
    p = pack.lower()
    return "taiyi" in p or "太乙" in pack


def count_hits(text: str, needles: list[str]) -> dict[str, int]:
    return {n: text.count(n) for n in needles}


def yaml_ids(text: str) -> tuple[list[str], list[str], list[str]]:
    block = re.findall(r"(?m)^\s+- id:\s+(\S+)", text)
    inline = re.findall(r"\{id:\s*([A-Za-z0-9_\-]+)", text)
    # kintaiyi raw_cases use "- id:" without extra indent marker beyond yaml list
    raw = re.findall(r"(?m)^- id:\s+(\S+)", text)
    all_ids = list(dict.fromkeys(block + inline + raw))
    return block, inline, all_ids


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

    impl_rels = [
        "scripts/reading_engine/taiyi.py",
        "resources/runtime/providers/taiyi.json",
        "references/matrices/taiyi-source-tables-v1.yaml",
        "references/books/san-shi/taiyi-shenshu/rules.md",
        "references/books/san-shi/taiyi-shenshu/quote-index.md",
    ]
    impl_same = {r: hash_cmp.get(r, False) for r in impl_rels}

    signed_prov = (SIGNED / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    core_prov = (CORE / "scripts/reading_engine/providers.py").read_text(encoding="utf-8")
    signed_cu = claim_ids(signed_prov)
    core_cu = claim_ids(core_prov)
    taiyi_cu_signed = [x for x in signed_cu if "taiyi" in x.lower()]
    taiyi_cu_core = [x for x in core_cu if "taiyi" in x.lower()]
    signed_cls = extract_class(signed_prov, "class TaiyiProvider")
    core_cls = extract_class(core_prov, "class TaiyiProvider")

    j = json.loads((SIGNED / "resources/runtime/providers/taiyi.json").read_text(encoding="utf-8"))
    rc = j.get("runtime_capability") or {}
    outs = list(rc.get("outputs") or [])
    out_bind = [b.get("name") for b in (rc.get("output_bindings") or [])]
    ext_outs = list(rc.get("extension_outputs") or [])
    find_bind = rc.get("finding_bindings") or j.get("finding_bindings") or []
    find_ids = [b.get("id") if isinstance(b, dict) else b for b in (find_bind or [])]
    taiyi_src = (SIGNED / "scripts/reading_engine/taiyi.py").read_text(encoding="utf-8")
    adapter = re.search(r'ADAPTER_VERSION\s*=\s*"([^"]+)"', taiyi_src)
    provider_id_py = re.search(r'provider_id\s*=\s*"([^"]+)"', signed_cls)
    deps = re.findall(r'"taiyi\.[^"]+"', taiyi_src)
    pred_ids = re.findall(r'"(TY-P\d+)"', taiyi_src)

    packs: dict[str, dict[str, int]] = {}
    active_ids: list[str] = []
    verified_ids: list[str] = []
    status_counter: Counter[str] = Counter()
    local_ids: list[str] = []
    n_rules = 0
    taiyi_rule_rows = 0
    trap_liuren_pack_rows = 0
    for line in (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n_rules += 1
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        rid = str(row.get("rule_id") or "")
        path = str(row.get("source_path") or "")
        if "liuren" in pack.lower() or "daliuren" in pack.lower():
            trap_liuren_pack_rows += 1
        if not (is_taiyi_pack(pack) or "taiyi" in rid.lower() or "taiyi" in path.lower()):
            continue
        taiyi_rule_rows += 1
        packs.setdefault(pack, {"n": 0, "active": 0, "verified": 0})
        packs[pack]["n"] += 1
        st = str(row.get("classical_binding_status") or "")
        status_counter[st] += 1
        local_ids.append(str(row.get("local_rule_id") or ""))
        if row.get("runtime_active"):
            packs[pack]["active"] += 1
            active_ids.append(rid)
        if st == "verified":
            packs[pack]["verified"] += 1
            verified_ids.append(rid)

    src_packs = re.findall(r'"packs":\s*\[(.*?)\]', signed_cls, re.S)
    source_route_packs: list[str] = []
    if src_packs:
        source_route_packs = re.findall(r'"([^"]+)"', src_packs[0])

    scope_path = SIGNED / "references/index/evidence-scope-bindings-v1.yaml"
    scope_hits = 0
    if scope_path.exists():
        scope_text = scope_path.read_text(encoding="utf-8")
        scope_hits = len(re.findall(r"taiyi|太乙", scope_text, re.I))

    fx_names = ["taiyi-v51.yaml", "kintaiyi-taiyi-v51.yaml"]
    fx_signed = {n: (SIGNED / "references/fixtures" / n).exists() for n in fx_names}
    fx_core_exists = {n: (CORE / "references/fixtures" / n).exists() for n in fx_names}

    fx_text = ""
    kintaiyi_text = ""
    fx_core = CORE / "references/fixtures/taiyi-v51.yaml"
    kintaiyi_core = CORE / "references/fixtures/kintaiyi-taiyi-v51.yaml"
    if fx_core.exists():
        fx_text = fx_core.read_text(encoding="utf-8")
    if kintaiyi_core.exists():
        kintaiyi_text = kintaiyi_core.read_text(encoding="utf-8")
    fx_block, fx_inline, fx_all = yaml_ids(fx_text)
    kt_block, kt_inline, kt_all = yaml_ids(kintaiyi_text)
    combined_ids = list(dict.fromkeys(fx_all + kt_all))

    epoch_ids = re.findall(r"(?m)^epoch_cases:\n(?:  - \{id: ([A-Za-z0-9_\-]+).+\n)+", fx_text)
    epoch_ids = re.findall(r"(?m)^  - \{id: ([A-Za-z0-9_\-]+)", fx_text.split("external_reference:")[0] if "external_reference:" in fx_text else fx_text)
    ext_ids = []
    if "external_reference_cases:" in fx_text:
        chunk = fx_text.split("external_reference_cases:", 1)[1]
        chunk = chunk.split("known_comparator_difference_cases:", 1)[0]
        ext_ids = re.findall(r"\{id:\s*([A-Za-z0-9_\-]+)", chunk)
    cal_ids = []
    if "calendar_boundary_cases:" in fx_text:
        chunk = fx_text.split("calendar_boundary_cases:", 1)[1]
        cal_ids = re.findall(r"\{id:\s*([A-Za-z0-9_\-]+)", chunk)
    diff_bureaus = re.findall(r"(?m)^  - \{bureau:\s*(\d+)", fx_text)
    kt_raw_ids = re.findall(r"(?m)^- id:\s+(\S+)", kintaiyi_text)

    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    evidence_all = (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8")
    needles = [
        "taiyi-v51",
        "kintaiyi-taiyi-v51",
        "mingli-taiyi-fixtures-v1",
        "kintaiyi-taiyi-raw-v1",
        "classical_case",
    ] + combined_ids
    brief_hits = count_hits(brief, needles)
    taiyi_py_fixture_hits = count_hits(taiyi_src, needles)
    evidence_fixture_hits = count_hits(evidence_all, needles)
    brief_taiyi_hits = len(re.findall(r"taiyi|太乙", brief, re.I))
    taiyi_py_claim = taiyi_src.count("claim_unit")
    cls_claim = signed_cls.count("claim_unit")

    trap_liuren_taiyi = 0
    for rel in LIUREN_TRAP_PATHS:
        p = SIGNED / rel
        if p.exists():
            trap_liuren_taiyi += p.read_text(encoding="utf-8").count("太乙")

    core_only_kind: dict[str, str] = {}
    for rel in core_only:
        if "/fixtures/" in rel or "fixture" in rel:
            core_only_kind[rel] = "fixture_oracle"
        elif rel.startswith("scripts/test_") or rel.startswith("scripts/audit_"):
            core_only_kind[rel] = "test_or_audit"
        elif rel.startswith("references/books/"):
            core_only_kind[rel] = "book_notes"
        else:
            core_only_kind[rel] = "other"

    impl_unsigned = [
        rel
        for rel in core_only
        if rel.endswith(".py") and "/reading_engine/" in rel
    ]
    impl_unsigned += [
        rel
        for rel in both
        if rel.endswith((".py", ".json", ".yaml"))
        and not hash_cmp.get(rel, True)
        and "fixtures" not in rel
    ]

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
    print(f"TaiyiProvider_identical={signed_cls == core_cls and bool(signed_cls)}")
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
    print(f"source_route_packs={source_route_packs}")
    print(f"source_dependency_ids={deps}")
    print(f"source_dependency_n={len(deps)}")
    print(f"board_predicate_ids={pred_ids}")
    print(f"board_predicate_n={len(pred_ids)}")
    print(f"taiyi_cu_signed={taiyi_cu_signed}")
    print(f"taiyi_cu_core={taiyi_cu_core}")
    print(f"all_cu_signed={signed_cu}")
    print(f"all_cu_core={core_cu}")
    print(f"TaiyiProvider_claim_unit={cls_claim}")
    print(f"taiyi_py_claim_unit={taiyi_py_claim}")
    print(f"evidence_rules_total={n_rules}")
    print(f"taiyi_rule_rows={taiyi_rule_rows}")
    print(f"taiyi_packs={packs}")
    print(f"runtime_active_n={len(active_ids)}")
    print(f"runtime_active_rules={active_ids}")
    print(f"verified_n={len(verified_ids)}")
    print(f"verified_rules={verified_ids}")
    print(f"local_rule_ids={local_ids}")
    print(f"binding_status={dict(status_counter)}")
    print(f"scope_binding_file_exists={scope_path.exists()}")
    print(f"scope_binding_taiyi_hits={scope_hits}")
    print(f"golden_fixture_in_signed={fx_signed}")
    print(f"golden_fixture_in_core={fx_core_exists}")
    print(f"taiyi_v51_block_ids={fx_block}")
    print(f"taiyi_v51_block_n={len(fx_block)}")
    print(f"taiyi_v51_inline_ids={fx_inline}")
    print(f"taiyi_v51_inline_n={len(fx_inline)}")
    print(f"taiyi_v51_all_ids={fx_all}")
    print(f"taiyi_v51_all_n={len(fx_all)}")
    print(f"epoch_case_ids={epoch_ids}")
    print(f"epoch_case_n={len(epoch_ids)}")
    print(f"external_reference_case_ids={ext_ids}")
    print(f"external_reference_case_n={len(ext_ids)}")
    print(f"calendar_boundary_case_ids={cal_ids}")
    print(f"calendar_boundary_case_n={len(cal_ids)}")
    print(f"comparator_difference_bureaus={diff_bureaus}")
    print(f"comparator_difference_n={len(diff_bureaus)}")
    print(f"kintaiyi_block_ids={kt_block}")
    print(f"kintaiyi_raw_ids={kt_raw_ids}")
    print(f"kintaiyi_raw_n={len(kt_raw_ids)}")
    print(f"kintaiyi_all_n={len(kt_all)}")
    print(f"fixture_all_ids={combined_ids}")
    print(f"fixture_all_n={len(combined_ids)}")
    print(f"brief_taiyi_token_hits={brief_taiyi_hits}")
    print(f"brief_fixture_needle_hits={brief_hits}")
    print(f"taiyi_py_fixture_needle_hits={taiyi_py_fixture_hits}")
    print(f"evidence_rules_fixture_needle_hits={evidence_fixture_hits}")
    print(f"liuren_trap_taiyi_char_hits={trap_liuren_taiyi}")
    print(f"liuren_pack_rows_not_counted_as_taiyi={trap_liuren_pack_rows}")
    print(f"unsigned_impl_candidates={impl_unsigned}")
    print(f"unsigned_impl_n={len(impl_unsigned)}")

    packs_s = {k: f"n={v['n']}/active={v['active']}/verified={v['verified']}" for k, v in packs.items()}
    print(
        "CONCLUSION_1 "
        f"provider={j.get('id')}/{provider_id_py.group(1) if provider_id_py else None} "
        f"outputs={len(outs)} extension_outputs={len(ext_outs)} finding_bindings={len(find_ids)} "
        f"CU={taiyi_cu_signed} packs={packs_s} "
        f"runtime_active={len(active_ids)} verified={len(verified_ids)} "
        f"golden_in_signed={fx_signed}"
    )
    print(
        "CONCLUSION_2 "
        f"impl_all_identical={all(impl_same.values())} "
        f"TaiyiProvider_identical={signed_cls == core_cls and bool(signed_cls)} "
        f"core_only={len(core_only)} unsigned_impl_n={len(impl_unsigned)} "
        f"taiyi_v51_all={len(fx_all)} kintaiyi_raw={len(kt_raw_ids)} "
        f"fixture_all={len(combined_ids)}"
    )
    print(
        "CONCLUSION_3 "
        f"brief_taiyi_hits={brief_taiyi_hits} "
        f"brief_fixture_hits_sum={sum(brief_hits.values())} "
        f"taiyi_py_fixture_hits_sum={sum(taiyi_py_fixture_hits.values())} "
        f"evidence_fixture_hits_sum={sum(evidence_fixture_hits.values())} "
        f"finding_bindings_are_cu={bool(taiyi_cu_signed)} "
        f"liuren_trap_太乙={trap_liuren_taiyi}"
    )
    return 0 if pin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
