#!/usr/bin/env python3
"""Read-only: P10 short table — 制品已有 / 仅源码 / 必须 resign."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
CORE = ROOT / "core/mingli-master"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def claim_ids(path: Path) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', path.read_text(encoding="utf-8"))


def pack_active(prefix: str) -> tuple[dict[str, dict[str, int]], list[str]]:
    packs: dict[str, dict[str, int]] = {}
    active: list[str] = []
    for line in (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        if not pack.startswith(prefix):
            continue
        packs.setdefault(pack, {"n": 0, "active": 0})
        packs[pack]["n"] += 1
        if row.get("runtime_active"):
            packs[pack]["active"] += 1
            active.append(str(row.get("rule_id")))
    return packs, active


def main() -> int:
    man = json.loads((SIGNED / ".mingli-release-manifest.json").read_bytes())
    inspector = hashlib.sha256((SIGNED / ".mingli-release-manifest.json").read_bytes()).hexdigest()
    signed_cu = claim_ids(SIGNED / "scripts/reading_engine/providers.py")
    core_cu = claim_ids(CORE / "scripts/reading_engine/providers.py")
    signed_provs = sorted(p.stem for p in (SIGNED / "resources/runtime/providers").glob("*.json"))
    core_provs = sorted(p.stem for p in (CORE / "resources/runtime/providers").glob("*.json"))

    rules_text = (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8")
    n_rules = sum(1 for line in rules_text.splitlines() if line.strip())
    dr = None
    for line in rules_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("rule_id")) == "DR-01-01" or str(row.get("rule_id", "")).endswith("#DR-01-01"):
            dr = {
                "rule_id": row.get("rule_id"),
                "pack": row.get("source_pack"),
                "runtime_active": bool(row.get("runtime_active")),
            }
            break
    if dr is None:
        for line in rules_text.splitlines():
            if "DR-01-01" in line:
                row = json.loads(line)
                dr = {
                    "rule_id": row.get("rule_id"),
                    "pack": row.get("source_pack"),
                    "runtime_active": bool(row.get("runtime_active")),
                }
                break

    p1994 = Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json")
    ev1994 = []
    if p1994.exists():
        prep = json.loads(p1994.read_text(encoding="utf-8"))
        brief = prep.get("brief") or {}
        ev1994 = [e.get("rule_id") or e.get("id") for e in (brief.get("evidence") or [])]

    turns = (SIGNED / "scripts/reading_engine/turns.py").read_text(encoding="utf-8")
    rel_signed = "relationship_signals" in turns
    conv_signed = 0
    for p in list(SIGNED.rglob("*.py")) + list(SIGNED.rglob("*.json")):
        if "__pycache__" in str(p):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        conv_signed += t.count("convergence")

    zw_packs, zw_active = pack_active("ziwei/")
    xm_packs, xm_active = pack_active("xingming/")
    qm_packs, qm_active = pack_active("san-shi/qimen")
    lr_packs, lr_active = pack_active("san-shi/")
    lr_packs = {k: v for k, v in lr_packs.items() if "liuren" in k or "daliuren" in k}
    lr_active = [x for x in lr_active if "liuren" in x or "daliuren" in x or x.startswith("DLR-") or x.startswith("LR-") or x.startswith("LM-")]

    print(f"inspector={inspector}")
    print(f"source_commit={man.get('source_commit')}")
    print(f"files={len(man.get('files') or {})}")
    print(f"signed_cu={signed_cu}")
    print(f"core_cu={core_cu}")
    print(f"core_only_cu={sorted(set(core_cu) - set(signed_cu))}")
    print(f"signed_providers={signed_provs}")
    print(f"extra_core_providers={sorted(set(core_provs) - set(signed_provs))}")
    print(f"evidence_rules_total={n_rules}")
    print(f"dr0101={dr}")
    print(f"career_1994_evidence={ev1994}")
    print(f"career_1994_has_DR-01-01={any(x and 'DR-01-01' in str(x) for x in ev1994)}")
    print(f"signed_turns_has_relationship_signals={rel_signed}")
    print(f"signed_convergence_hits={conv_signed}")
    print(f"ziwei_packs={zw_packs}")
    print(f"ziwei_active={zw_active}")
    print(f"xingming_packs={xm_packs}")
    print(f"xingming_active={xm_active}")
    print(f"qimen_packs={qm_packs}")
    print(f"qimen_active_n={len(qm_active)}")
    print(f"liuren_packs={lr_packs}")
    print(f"liuren_active_n={len(lr_active)}")
    print(f"has_dream_name_provider={any(x in signed_provs for x in ('dream', 'name', 'jiemeng'))}")
    print(f"ziwei_fixture_signed={(SIGNED / 'references/fixtures/ziwei-v51.yaml').exists()}")
    print(f"xingming_fixture_signed={(SIGNED / 'references/fixtures/xingming-v51.yaml').exists()}")
    print(f"qimen_fixture_signed={(SIGNED / 'references/fixtures/qimen-v51.yaml').exists()}")
    print(f"liuren_fixture_signed={(SIGNED / 'references/fixtures/liuren-v51.yaml').exists()}")
    print(f"ziwei_fixture_core={(CORE / 'references/fixtures/ziwei-v51.yaml').exists()}")
    print(f"day_master_in_signed={'bazi.day-master-root-support-v1' in signed_cu}")
    print(f"day_master_in_core={'bazi.day-master-root-support-v1' in core_cu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
