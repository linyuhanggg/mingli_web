#!/usr/bin/env python3
"""Read-only: P10-008 大六壬黄金样例 — signed V53 vs core."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
CORE = ROOT / "core/mingli-master"

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def claim_ids(path: Path) -> list[str]:
    return re.findall(r'"claim_unit_id":\s*"([^"]+)"', path.read_text(encoding="utf-8"))

def main() -> int:
    man = SIGNED / ".mingli-release-manifest.json"
    inspector = hashlib.sha256(man.read_bytes()).hexdigest()
    nfiles = len(json.loads(man.read_bytes()).get("files") or {})
    signed_cu = claim_ids(SIGNED / "scripts/reading_engine/providers.py")
    core_cu = claim_ids(CORE / "scripts/reading_engine/providers.py")
    impl = [
        "scripts/liuren_fact_adapter.py",
        "scripts/liuren_calc.py",
        "resources/runtime/providers/liuren.json",
        "references/matrices/liuren-source-tables-v1.yaml",
    ]
    same = all(sha(SIGNED / r) == sha(CORE / r) for r in impl)
    packs: dict[str, dict[str, int]] = {}
    active: list[str] = []
    for line in (SIGNED / "references/index/evidence-rules.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pack = str(row.get("source_pack") or "")
        if not any(k in pack for k in ("liuren", "daliuren")):
            continue
        packs.setdefault(pack, {"n": 0, "active": 0})
        packs[pack]["n"] += 1
        if row.get("runtime_active"):
            packs[pack]["active"] += 1
            active.append(str(row.get("rule_id")))
    fx_signed = (SIGNED / "references/fixtures/liuren-v51.yaml").exists()
    print(f"inspector={inspector}")
    print(f"files={nfiles}")
    print(f"liuren_cu_signed={[x for x in signed_cu if x.startswith(('liuren.','daliuren.'))]}")
    print(f"liuren_cu_core={[x for x in core_cu if x.startswith(('liuren.','daliuren.'))]}")
    print(f"impl_files_identical={same}")
    print(f"liuren_packs={packs}")
    print(f"runtime_active_count={len(active)}")
    print(f"runtime_active_rules={active}")
    print(f"golden_fixture_in_signed={fx_signed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
