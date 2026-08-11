#!/usr/bin/env python3
"""Verify a release root matches the frozen mingli-master 5.1 portable core.

Always use the signed 217-file release root + .mingli-release-manifest.json.
Never treat a dirty skill worktree as the production source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

FROZEN_SOURCE_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
FROZEN_RELEASE_NAME = "mingli-master-portable-core"
FROZEN_MANIFEST_SHA256 = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)
EXPECTED_FILE_COUNT = 217
EXPECTED_REFERENCE_PACKS = 55
EXPECTED_EVIDENCE = 1328
EXPECTED_PROVIDERS = 13


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.release_root.resolve()
    manifest_path = root / ".mingli-release-manifest.json"
    if not manifest_path.is_file():
        print(f"missing manifest: {manifest_path}", file=sys.stderr)
        return 1
    manifest_sha = _sha256_file(manifest_path)
    if manifest_sha != FROZEN_MANIFEST_SHA256:
        print(
            "manifest sha mismatch: "
            f"got {manifest_sha} expected {FROZEN_MANIFEST_SHA256}",
            file=sys.stderr,
        )
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_commit") != FROZEN_SOURCE_COMMIT:
        print("source_commit mismatch", file=sys.stderr)
        return 1
    if manifest.get("release") != FROZEN_RELEASE_NAME:
        print("release name mismatch", file=sys.stderr)
        return 1
    files = manifest.get("files")
    if not isinstance(files, dict) or len(files) != EXPECTED_FILE_COUNT:
        print("file count mismatch", file=sys.stderr)
        return 1
    mismatches: list[str] = []
    for relative, expected in files.items():
        path = root / relative
        if not path.is_file():
            mismatches.append(f"missing {relative}")
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatches.append(f"digest drift {relative}")
    if mismatches:
        for item in mismatches[:20]:
            print(item, file=sys.stderr)
        print(f"{len(mismatches)} file mismatches", file=sys.stderr)
        return 1
    providers = sorted((root / "resources/runtime/providers").glob("*.json"))
    packs = list((root / "references/books").rglob("rules.md"))
    evidence = root / "references/index/evidence-rules.jsonl"
    evidence_count = sum(1 for _ in evidence.open(encoding="utf-8")) if evidence.is_file() else -1
    if len(providers) != EXPECTED_PROVIDERS:
        print(f"provider count {len(providers)} != {EXPECTED_PROVIDERS}", file=sys.stderr)
        return 1
    if len(packs) != EXPECTED_REFERENCE_PACKS:
        print(f"reference packs {len(packs)} != {EXPECTED_REFERENCE_PACKS}", file=sys.stderr)
        return 1
    if evidence_count != EXPECTED_EVIDENCE:
        print(f"evidence count {evidence_count} != {EXPECTED_EVIDENCE}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "release_root": str(root),
                "source_commit": FROZEN_SOURCE_COMMIT,
                "manifest_sha256": manifest_sha,
                "files": EXPECTED_FILE_COUNT,
                "providers": EXPECTED_PROVIDERS,
                "reference_packs": EXPECTED_REFERENCE_PACKS,
                "evidence_records": EXPECTED_EVIDENCE,
                "note": "Use this signed release only; ignore dirty skill worktrees.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
