#!/usr/bin/env python3
"""Sync classical-evidence-bindings-v1.json binding stubs.

For every rule that has fact predicates but no classical binding entry, create an
``inactive_unverified`` stub.  For every binding entry whose rule no longer has
fact predicates, remove it.  Then rewrite the manifest in the exact canonical
serialization and update both pinned SHA-256 constants.

This tool never creates ``verified`` / ``verified_exact`` state; those statuses
are reserved for the human audit gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TREE = Path("core/mingli-master")
DEFAULT_PY = Path.home() / ".local/share/mingli-master/venv/bin/python"

MANIFEST_REL = Path("references/matrices/classical-evidence-bindings-v1.json")
BUILD_SCRIPT_REL = Path("scripts/build_evidence_index.py")
RUNTIME_SCRIPT_REL = Path("scripts/reading_engine/evidence_rules.py")

_STUB_STATUS = "inactive_unverified"
_STUB_METHOD = "runtime_inactive_pending_semantic_source_applicability_audit"
_HASH64 = re.compile(r"[0-9a-f]{64}")


def _load_compiler(tree: Path):
    """Import the tree's build_evidence_index module (not the repo-root one)."""
    sys.path.insert(0, str((tree / "scripts").resolve()))
    import build_evidence_index  # type: ignore

    return build_evidence_index


def _canonical_rendered(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _pin_paths(tree: Path) -> list[Path]:
    return [tree / BUILD_SCRIPT_REL, tree / RUNTIME_SCRIPT_REL]


def _update_pins(tree: Path, new_hash: str) -> None:
    pattern = re.compile(
        r'(CLASSICAL_EVIDENCE_BINDINGS_SHA256 = \(\s*")' + _HASH64.pattern + r'("\s*\))'
    )
    for path in _pin_paths(tree):
        text = path.read_text(encoding="utf-8")
        new_text, count = pattern.subn(
            lambda m: m.group(1) + new_hash + m.group(2),
            text,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"could not locate hash constant in {path}")
        path.write_text(new_text, encoding="utf-8")


def _run(tree: Path, python: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [str(python), *args],
        cwd=tree,
        capture_output=True,
        text=True,
        env=env,
    )


def build_stub(record: dict, compiler) -> dict:
    """Build an inactive_unverified binding stub for a compiled rule record."""
    binding = {
        "rule_id": str(record["rule_id"]),
        "verification_status": _STUB_STATUS,
        "semantic_verification_status": _STUB_STATUS,
        "verification_method": _STUB_METHOD,
        "mechanical_location_status": "unverified",
        "applicability_signature": compiler.canonical_predicate_signature(
            record.get("required_fact_predicates") or [],
            record.get("excluded_fact_predicates") or [],
        ),
        "rule_record_digest": compiler.canonical_rule_record_digest(record),
        "classical_sources": [],
    }
    binding["binding_digest"] = compiler._classical_binding_digest(binding)
    return binding


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report changes without writing any file",
    )
    parser.add_argument(
        "--tree",
        type=Path,
        default=DEFAULT_TREE,
        help="source tree (default: core/mingli-master)",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=DEFAULT_PY,
        help="Runtime venv python (default: ~/.local/share/mingli-master/venv/bin/python)",
    )
    args = parser.parse_args(argv)

    tree = args.tree.resolve()
    python = args.python.expanduser()
    if not tree.is_dir():
        print(f"error: source tree not found: {tree}", file=sys.stderr)
        return 2
    if not python.is_file():
        print(f"error: python not found: {python}", file=sys.stderr)
        return 2

    compiler = _load_compiler(tree)

    try:
        records = compiler.compile_evidence_rules(
            root=tree,
            enforce_classical_bindings=False,
        )
    except Exception as exc:  # noqa: BLE001 - surface environment/parse failures
        print(f"error: compile_evidence_rules failed: {exc}", file=sys.stderr)
        return 2

    record_by_id = {str(r["rule_id"]): r for r in records}
    needed = {
        str(r["rule_id"])
        for r in records
        if r.get("required_fact_predicates") or r.get("excluded_fact_predicates")
    }

    manifest_path = tree / MANIFEST_REL
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:
        print(f"error: cannot read manifest: {exc}", file=sys.stderr)
        return 2
    actual_hash = hashlib.sha256(raw).hexdigest()

    try:
        manifest = compiler.load_classical_evidence_bindings(
            root=tree,
            expected_sha256=actual_hash,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error: cannot load classical evidence bindings: {exc}", file=sys.stderr)
        return 2

    current = set(manifest["bindings"].keys())
    to_add = sorted(needed - current)
    to_remove = sorted(current - needed)

    if to_add:
        for rule_id in to_add:
            record = record_by_id.get(rule_id)
            if record is None:
                print(f"error: no compiled record for {rule_id}", file=sys.stderr)
                return 2
            manifest["bindings"][rule_id] = build_stub(record, compiler)

    for rule_id in to_remove:
        del manifest["bindings"][rule_id]

    manifest["bindings"] = dict(sorted(manifest["bindings"].items()))
    rendered = _canonical_rendered(manifest)
    new_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    print(f"manifest: {manifest_path}")
    print(f"predicate-bearing rules: {len(needed)}")
    print(f"manifest binding entries: {len(current)} -> {len(manifest['bindings'])}")
    print(f"to add ({len(to_add)}): {', '.join(to_add) or '-'}")
    print(f"to remove ({len(to_remove)}): {', '.join(to_remove) or '-'}")
    if to_add or to_remove:
        print(f"new manifest sha256: {new_hash}")
    else:
        print(f"manifest sha256 unchanged: {new_hash}")

    if args.dry_run:
        return 0

    # Back up the current pre-write state so a broken sync is recoverable.
    # Only needed when the sync will actually change the manifest.
    if to_add or to_remove:
        backup_dir = Path(
            "docs/releases/evidence/2026-08-18-binding-manifest-baselines"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_manifest = backup_dir / f"auto-before-{actual_hash}.json"
        if not backup_manifest.exists():
            backup_manifest.write_bytes(raw)
            print(f"backup manifest: {backup_manifest}")

    manifest_path.write_text(rendered, encoding="utf-8")
    _update_pins(tree, new_hash)
    print(f"wrote manifest with {len(manifest['bindings'])} bindings")
    print(f"synced pins to {new_hash}: {', '.join(str(p) for p in _pin_paths(tree))}")

    # Regenerate the compiled index, then verify --check.
    build = _run(tree, python, ["scripts/build_evidence_index.py"])
    if build.returncode != 0:
        print("error: build_evidence_index.py (write) failed", file=sys.stderr)
        print(build.stdout[-2000:], file=sys.stderr)
        print(build.stderr[-3000:], file=sys.stderr)
        return 1

    check = _run(tree, python, ["scripts/build_evidence_index.py", "--check"])
    if check.returncode != 0:
        print("error: build_evidence_index.py --check failed", file=sys.stderr)
        print(check.stdout[-3000:], file=sys.stderr)
        print(check.stderr[-3000:], file=sys.stderr)
        return 1

    print("self-check: build_evidence_index.py --check pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
