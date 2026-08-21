#!/usr/bin/env python3
"""Compare core/mingli-master vs signed V53 file hashes. Read-only."""
import hashlib, json, os
from pathlib import Path
SIGNED = Path("/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release")
CORE = Path("/Volumes/Lexar/code/mingli_web/core/mingli-master")
SKIP = {".git", "__pycache__", ".pytest_cache", "node_modules", ".mypy_cache"}

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def rel_files(root: Path):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            fp = Path(dirpath) / fn
            rel = fp.relative_to(root).as_posix()
            if rel.startswith("."):
                continue
            out[rel] = fp
    return out

def main() -> int:
    man_path = SIGNED / ".mingli-release-manifest.json"
    man_sha = hashlib.sha256(man_path.read_bytes()).hexdigest()
    man = json.loads(man_path.read_bytes())
    signed = rel_files(SIGNED)
    core = rel_files(CORE)
    both = sorted(set(signed) & set(core))
    only_signed = sorted(set(signed) - set(core))
    prefixes = ("scripts/", "references/", "adapters/")
    only_core_rl = sorted(k for k in core if k.startswith(prefixes) and k not in signed)
    same = diff = 0
    print("manifest_sha256", man_sha)
    print("source_commit", man.get("source_commit"))
    print("signed_walk", len(signed))
    print("core_walk", len(core))
    print("both", len(both))
    print("=== DIFF_HASH ===")
    for rel in both:
        hs, hc = sha256(signed[rel]), sha256(core[rel])
        if hs == hc:
            same += 1
        else:
            diff += 1
            print(f"{rel}\tsigned={hs}\tcore={hc}")
    print("same_hash", same)
    print("diff_hash", diff)
    print("only_signed", len(only_signed))
    print("only_core_release_like", len(only_core_rl))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
