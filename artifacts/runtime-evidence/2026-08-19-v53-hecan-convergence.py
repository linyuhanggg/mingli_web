#!/usr/bin/env python3
"""Read-only: P10-005/P10-010 合参 — signed V53 vs core for convergence/disagreements."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
CORE = ROOT / "core/mingli-master"

def count_token(root: Path, token: str) -> tuple[int, int, list[str]]:
    files: list[str] = []
    hits = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if not fn.endswith((".py", ".json")):
                continue
            p = Path(dirpath) / fn
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            n = text.count(token)
            if n:
                files.append(str(p.relative_to(root)))
                hits += n
    return len(files), hits, files

def main() -> int:
    man = SIGNED / ".mingli-release-manifest.json"
    inspector = hashlib.sha256(man.read_bytes()).hexdigest()
    nfiles = len(json.loads(man.read_bytes()).get("files") or {})
    s_conv = count_token(SIGNED, "convergence")
    c_conv = count_token(CORE, "convergence")
    s_dis = count_token(SIGNED, "disagreements")
    c_dis = count_token(CORE, "disagreements")
    brief = (SIGNED / "scripts/reading_engine/brief.py").read_text(encoding="utf-8")
    print(f"inspector={inspector}")
    print(f"files={nfiles}")
    print(f"signed_convergence_files={s_conv[0]} hits={s_conv[1]} paths={s_conv[2]}")
    print(f"core_convergence_files={c_conv[0]} hits={c_conv[1]} paths={c_conv[2]}")
    print(f"signed_disagreements_files={s_dis[2]}")
    print(f"core_disagreements_extra={[p for p in c_dis[2] if p not in s_dis[2]]}")
    print(f"brief_convergence={brief.count('convergence')} brief_disagreements={brief.count('disagreements')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
