#!/usr/bin/env python3
"""Read-only: P10-006/P10-009 六爻旺衰救应 — signed V53 vs core."""
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
    liuyao_cu_signed = [x for x in signed_cu if x.startswith("liuyao.")]
    liuyao_cu_core = [x for x in core_cu if x.startswith("liuyao.")]
    same_py = sha(SIGNED / "scripts/reading_engine/liuyao.py") == sha(CORE / "scripts/reading_engine/liuyao.py")
    same_json = sha(SIGNED / "resources/runtime/providers/liuyao.json") == sha(CORE / "resources/runtime/providers/liuyao.json")
    prov = json.loads((SIGNED / "resources/runtime/providers/liuyao.json").read_text())
    fb = [b.get("id") for b in prov["runtime_capability"]["finding_bindings"]]
    print(f"inspector={inspector}")
    print(f"files={nfiles}")
    print(f"signed_claim_units={signed_cu}")
    print(f"core_claim_units={core_cu}")
    print(f"liuyao_cu_signed={liuyao_cu_signed}")
    print(f"liuyao_cu_core={liuyao_cu_core}")
    print(f"liuyao.py_identical={same_py}")
    print(f"liuyao.json_identical={same_json}")
    print(f"liuyao_finding_bindings={fb}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
