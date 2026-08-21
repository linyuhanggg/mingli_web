#!/usr/bin/env python3
"""Record one authenticated outcome from a private JSON report."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Sequence

from reading_engine.outcome_store import OutcomeStore
from reading_engine.storage import AtomicReadingStore


def _secure_bytes(path: Path, *, label: str, maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"{label} must be a private regular file") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"{label} must be a private regular file")
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ValueError(f"{label} must be owned by the current user with mode 0600")
        content = os.read(descriptor, maximum + 1)
    finally:
        os.close(descriptor)
    if not content or len(content) > maximum:
        raise ValueError(f"{label} has an invalid size")
    return content


def _report(source: str) -> dict[str, Any]:
    if source == "-":
        content = sys.stdin.buffer.read(16385)
        if not content or len(content) > 16384:
            raise ValueError("stdin report has an invalid size")
    else:
        content = _secure_bytes(Path(source), label="report file", maximum=16384)
    payload = json.loads(content)
    required = {
        "reading_id", "prepared_digest", "claim_id", "status", "evidence", "reported_at"
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("report file fields do not match the outcome schema")
    return payload


def _inside(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    resolved_root = root.resolve()
    return resolved == resolved_root or resolved_root in resolved.parents


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reading-store", type=Path, required=True)
    parser.add_argument("--outcome-store", type=Path, required=True)
    parser.add_argument("--integrity-key-file", type=Path, required=True)
    parser.add_argument("--integrity-checkpoint", type=Path, required=True)
    parser.add_argument("--report-file", required=True, help="private 0600 JSON path, or - for stdin")
    args = parser.parse_args(argv)
    if _inside(args.integrity_key_file, args.reading_store) or _inside(
        args.integrity_key_file, args.outcome_store
    ):
        raise ValueError("integrity key file must be outside reading and outcome stores")
    integrity_key = _secure_bytes(
        args.integrity_key_file,
        label="integrity key file",
        maximum=1024,
    )
    if len(integrity_key) < 32:
        raise ValueError("integrity key file must contain at least 32 bytes")
    report = _report(args.report_file)
    store = OutcomeStore(
        args.outcome_store,
        reading_store=AtomicReadingStore(args.reading_store),
        integrity_key=integrity_key,
        checkpoint_path=args.integrity_checkpoint,
    )
    outcome = store.record(**report)
    print(
        json.dumps(
            {
                "schema_version": outcome.schema_version,
                "claim_id": outcome.claim_id,
                "record_digest": outcome.record_digest,
                "status": outcome.status,
                "stored": True,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
