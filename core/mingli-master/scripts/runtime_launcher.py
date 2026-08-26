#!/usr/bin/env python3
"""Site-hook-free bootstrap: validate the pinned runtime, run the codec once.

The launcher keeps the existing pinned dependency identity check, then
invokes the fixed JSON codec entrypoint exactly once. There is no probe
mode, no run mode and no caller-supplied transaction path. Bootstrap
failures still write one minimal, parsable ``Stopped`` Result to stdout so
hosts never receive empty output from a started process.
"""

from __future__ import annotations

import errno
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

FAILURE_SCHEMA_VERSION = "mingli-runtime-failure/v1"
_FAILURE_SPECS = {
    "bootstrap.unexpected_arguments": ("bootstrap", False),
    "bootstrap.guard_load_failed": ("bootstrap", False),
    "bootstrap.runtime_lock_failed": ("bootstrap", False),
    "bootstrap.runtime_identity_invalid": ("bootstrap", False),
    "runtime.internal_error": ("runtime_internal", False),
    "transient.timeout": ("transient", True),
    "transient.resource_unavailable": ("transient", True),
}
_TRANSIENT_ERRNOS = frozenset(
    {
        errno.EAGAIN,
        errno.EINTR,
        errno.EMFILE,
        errno.ENFILE,
        errno.ENOMEM,
        errno.ETIMEDOUT,
    }
)


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


def _failure_payload(code: str) -> dict[str, object]:
    category, retryable = _FAILURE_SPECS[code]
    return {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "code": code,
        "category": category,
        "retryable": retryable,
    }


def _failure_code_for_exception(error: BaseException) -> str:
    if isinstance(error, TimeoutError):
        return "transient.timeout"
    if isinstance(error, MemoryError):
        return "transient.resource_unavailable"
    if isinstance(error, OSError) and error.errno in _TRANSIENT_ERRNOS:
        return "transient.resource_unavailable"
    return "runtime.internal_error"


def _emit_stop(code: str, diagnostic: str) -> None:
    payload = {
        "kind": "stopped",
        "reason": "error",
        "public_copy": FALLBACK_ERROR_TEXT,
        "state_token": None,
        "input_request": None,
        "failure": _failure_payload(code),
        "continuation_allowed": False,
        "terminal": True,
        "completion_committed": False,
    }
    print(json.dumps(payload, ensure_ascii=False))
    print(f"Mingli runtime stopped: {diagnostic}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    # The codec surface is fixed. Reject retired shell subcommands explicitly
    # instead of silently discarding them and accidentally running a reading.
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        _emit_stop(
            "bootstrap.unexpected_arguments",
            "unexpected adapter arguments",
        )
        return 0
    try:
        guard = _load_guard()
    except Exception as exc:  # noqa: BLE001 - bootstrap remains fail-closed
        _emit_stop("bootstrap.guard_load_failed", str(exc))
        return 0
    try:
        runtime_root = guard.runtime_root_for_executable(sys.executable)
    except Exception as exc:  # noqa: BLE001 - bootstrap remains fail-closed
        _emit_stop("bootstrap.runtime_identity_invalid", str(exc))
        return 0
    try:
        with guard.runtime_lock(runtime_root, exclusive=False):
            try:
                _validated_identity(guard)
            except Exception as exc:  # noqa: BLE001 - no internals on stdout
                _emit_stop("bootstrap.runtime_identity_invalid", str(exc))
                return 0
            try:
                sys.path.append(str(SCRIPTS))
                sys.argv = [str(CODEC)]
                runpy.run_path(str(CODEC), run_name="__main__")
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001 - one lawful Result
                _emit_stop(_failure_code_for_exception(exc), str(exc))
                return 0
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - lock/bootstrap stays lawful
        code = _failure_code_for_exception(exc)
        if code == "runtime.internal_error":
            code = "bootstrap.runtime_lock_failed"
        _emit_stop(code, str(exc))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
