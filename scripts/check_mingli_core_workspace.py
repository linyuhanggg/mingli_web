#!/usr/bin/env python3
"""Check the visible core checkout and its installed local Runtime Release."""

from __future__ import annotations

import filecmp
import hashlib
import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = Path(
    os.environ.get(
        "MINGLI_CORE_SOURCE_ROOT",
        str(PROJECT_ROOT / "core" / "mingli-master"),
    )
).expanduser()
RUNTIME_ROOT = Path(
    os.environ.get(
        "MINGLI_RUNTIME_TEST_RELEASE_ROOT",
        str(PROJECT_ROOT / ".runtime" / "v53-time-check-release"),
    )
).expanduser()


def _git_branch(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "detached"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not (CORE_ROOT / ".git").exists():
        print(f"core_source=missing_or_not_git:{CORE_ROOT}")
        return 1

    print(f"core_source={CORE_ROOT}")
    print(f"core_branch={_git_branch(CORE_ROOT)}")

    manifest_path = RUNTIME_ROOT / ".mingli-release-manifest.json"
    if not manifest_path.is_file():
        print(f"runtime_release=missing:{RUNTIME_ROOT}")
        print("source_sync_ready=yes")
        return 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    managed = manifest.get("files")
    if not isinstance(managed, dict):
        print("runtime_manifest=invalid")
        return 1

    missing: list[str] = []
    drifted: list[str] = []
    unsigned: list[str] = []
    for relative, expected_digest in sorted(managed.items()):
        source = CORE_ROOT / relative
        installed = RUNTIME_ROOT / relative
        if not source.is_file() or not installed.is_file():
            missing.append(relative)
            continue
        if not filecmp.cmp(source, installed, shallow=False):
            drifted.append(relative)
        if not isinstance(expected_digest, str) or _sha256(installed) != expected_digest:
            unsigned.append(relative)

    print(f"runtime_release={RUNTIME_ROOT}")
    print(f"managed_files={len(managed)}")
    print(f"missing_files={len(missing)}")
    print(f"drifted_files={len(drifted)}")
    print(f"unsigned_files={len(unsigned)}")
    for relative in (*missing, *drifted, *unsigned):
        print(f"needs_release={relative}")
    print("source_sync_ready=yes")
    return 1 if missing or drifted or unsigned else 0


if __name__ == "__main__":
    raise SystemExit(main())
