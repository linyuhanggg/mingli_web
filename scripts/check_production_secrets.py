#!/usr/bin/env python3
"""Fail-closed checks that production secrets are injected and non-local.

Never prints secret values. Does not claim a cloud Secret Manager is wired.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import os
import sys


def _present(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return f"{name} missing"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-real-traffic-ready",
        action="store_true",
        help="Also require alert sink and real-traffic env readiness.",
    )
    args = parser.parse_args()
    errors: list[str] = []
    for name in (
        "MINGLI_IDENTITY_HASH_KEY",
        "MINGLI_CONTENT_ENCRYPTION_KEY_B64",
        "MINGLI_CONTENT_ENCRYPTION_KEY_ID",
        "DEEPSEEK_API_KEY",
    ):
        err = _present(name)
        if err:
            errors.append(err)
    identity = os.environ.get("MINGLI_IDENTITY_HASH_KEY", "")
    if identity.startswith("local-only-"):
        errors.append("MINGLI_IDENTITY_HASH_KEY is local-only")
    key_id = os.environ.get("MINGLI_CONTENT_ENCRYPTION_KEY_ID", "")
    if key_id.startswith("local-only-"):
        errors.append("MINGLI_CONTENT_ENCRYPTION_KEY_ID is local-only")
    encoded = os.environ.get("MINGLI_CONTENT_ENCRYPTION_KEY_B64", "")
    if encoded:
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            errors.append("MINGLI_CONTENT_ENCRYPTION_KEY_B64 is not valid base64")
        else:
            if len(raw) != 32:
                errors.append("MINGLI_CONTENT_ENCRYPTION_KEY_B64 must decode to 32 bytes")
            if encoded == "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=":
                errors.append("MINGLI_CONTENT_ENCRYPTION_KEY_B64 is the local default")
    if args.require_real_traffic_ready:
        if os.environ.get("MINGLI_ALERT_SINK_ENABLED", "").lower() not in {"1", "true", "yes"}:
            errors.append("MINGLI_ALERT_SINK_ENABLED must be true for real-traffic readiness")
        if os.environ.get("MINGLI_REAL_TRAFFIC_ENABLED", "").lower() in {"1", "true", "yes"}:
            errors.append(
                "MINGLI_REAL_TRAFFIC_ENABLED is true; app still fail-closes until Phase 0 closes"
            )
    if errors:
        for item in errors:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("OK: required production secret slots look injected (values not shown)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
