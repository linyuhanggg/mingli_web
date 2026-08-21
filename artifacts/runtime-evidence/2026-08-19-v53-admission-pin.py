#!/usr/bin/env python3
"""Pin check: admitted V53 must stay c451de5e / 663543e / 220 files. Detect overwrite or V52 mix-in. Read-only."""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path

ADMITTED_MANIFEST = "c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b"
ADMITTED_SOURCE = "663543e65ae037843b03dca1dec9486293affc9d"
ADMITTED_FILES = 220
ADMITTED_DESCRIBE = "3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc"
V52_MANIFEST = "bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50"
V52_SOURCE = "da46e7c0d565fe781e40a115acbb2874c400a195"
V52_DESCRIBE = "6118c5f525c87b9cbde95b4d51c945be18bfd18fff8e03306da9fa748b87d917"

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime" / "v53-time-check-release"
V52 = ROOT / ".runtime" / "v52-relationship-release"
SKIP = {".git", "__pycache__", ".pytest_cache", "node_modules", ".mypy_cache"}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def walk_count(root: Path) -> int:
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            rel = Path(dirpath, fn).relative_to(root).as_posix()
            if rel.startswith("."):
                continue
            n += 1
    return n

def main() -> int:
    fails = []
    man_path = SIGNED / ".mingli-release-manifest.json"
    print("signed_root", SIGNED)
    print("exists", man_path.exists())
    if not man_path.exists():
        print("FAIL missing manifest")
        return 2
    man_sha = sha256_file(man_path)
    man = json.loads(man_path.read_bytes())
    src = man.get("source_commit")
    n_man = len(man.get("files") or {})
    n_walk = walk_count(SIGNED)
    turns = (SIGNED / "scripts" / "reading_engine" / "turns.py").read_text(encoding="utf-8")
    has_rel = "relationship_signals" in turns or "_append_runtime_relationship" in turns
    providers = (SIGNED / "scripts" / "reading_engine" / "providers.py").read_text(encoding="utf-8")
    has_root = "bazi.day-master-root-support-v1" in providers
    print("inspector_manifest_sha256", man_sha)
    print("source_commit", src)
    print("manifest_files", n_man)
    print("walk_files", n_walk)
    print("turns_has_relationship_signals", has_rel)
    print("providers_has_day_master_root", has_root)
    if man_sha != ADMITTED_MANIFEST:
        fails.append("manifest_sha256 != c451de5e (overwrite or wrong tree)")
    if src != ADMITTED_SOURCE:
        fails.append("source_commit != 663543e")
    if n_man != ADMITTED_FILES or n_walk != ADMITTED_FILES:
        fails.append("file count != 220")
    if man_sha == V52_MANIFEST or src == V52_SOURCE:
        fails.append("this tree IS V52 (bef3df25 / da46e7c0) mixed into v53 path")
    if has_rel:
        fails.append("v53 turns.py now has relationship_signals (V52 mix-in)")
    if has_root:
        fails.append("signed providers now has day-master-root (unsigned source leaked / resign happened)")

    v52_ok = False
    if V52.exists():
        v52_sha = sha256_file(V52 / ".mingli-release-manifest.json")
        v52_man = json.loads((V52 / ".mingli-release-manifest.json").read_bytes())
        print("v52_separate_exists", True)
        print("v52_manifest_sha256", v52_sha)
        print("v52_source_commit", v52_man.get("source_commit"))
        v52_ok = v52_sha == V52_MANIFEST and v52_man.get("source_commit") == V52_SOURCE
        print("v52_is_other_artifact", v52_ok)
        if v52_sha == ADMITTED_MANIFEST:
            fails.append("v52 path unexpectedly equals admitted V53 hash")
    else:
        print("v52_separate_exists", False)

    print("admitted_manifest", ADMITTED_MANIFEST)
    print("admitted_source", ADMITTED_SOURCE)
    print("admitted_files", ADMITTED_FILES)
    print("pin_ok", not fails)
    for f in fails:
        print("FAIL", f)
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
