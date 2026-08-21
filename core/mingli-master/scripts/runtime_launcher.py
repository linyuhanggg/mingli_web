#!/usr/bin/env python3
"""Site-hook-free bootstrap: validate the pinned runtime, run the codec once.

The launcher keeps the existing pinned dependency identity check, then
invokes the fixed JSON codec entrypoint exactly once. There is no probe
mode, no run mode and no caller-supplied transaction path. Bootstrap
failures still write one minimal, parsable ``Stopped`` Result to stdout so
hosts never receive empty output from a started process.
"""

from __future__ import annotations

import importlib.util
import json
import runpy
import sys
from pathlib import Path


sys.dont_write_bytecode = True
sys.pycache_prefix = "/dev/null"


SCRIPTS = Path(__file__).resolve().parent
CODEC = SCRIPTS / "adapters" / "json_cli.py"
FALLBACK_ERROR_TEXT = "本次处理未完成，请稍后重试。"


def _load_guard():
    helper = SCRIPTS / "runtime_python.py"
    spec = importlib.util.spec_from_file_location("_mingli_runtime_guard", helper)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime guard could not be loaded")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return guard


def _validated_identity(guard) -> dict[str, object]:
    site_roots = guard.validate_installed_runtime(sys.executable)
    for site_root in site_roots:
        sys.path.append(str(site_root))
    identity = guard.current_runtime_identity()
    guard.validate_runtime_identity(identity)
    return identity


def _emit_bootstrap_stop(reason: str) -> None:
    payload = {
        "kind": "stopped",
        "reason": "error",
        "public_copy": FALLBACK_ERROR_TEXT,
        "state_token": None,
    }
    print(json.dumps(payload, ensure_ascii=False))
    print(f"Mingli runtime bootstrap failed: {reason}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    # The codec surface is fixed. Reject retired shell subcommands explicitly
    # instead of silently discarding them and accidentally running a reading.
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        _emit_bootstrap_stop("unexpected adapter arguments")
        return 0
    try:
        guard = _load_guard()
        runtime_root = guard.runtime_root_for_executable(sys.executable)
        with guard.runtime_lock(runtime_root, exclusive=False):
            _validated_identity(guard)
            sys.path.append(str(SCRIPTS))
            sys.argv = [str(CODEC)]
            runpy.run_path(str(CODEC), run_name="__main__")
        return 0
    except SystemExit:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        _emit_bootstrap_stop(str(exc))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
