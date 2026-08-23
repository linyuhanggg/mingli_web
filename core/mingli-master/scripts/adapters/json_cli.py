#!/usr/bin/env python3
"""One-shot JSON codec CLI for the portable reading interface.

Physical contract: the process reads exactly one Command JSON object from
stdin, writes exactly one Result JSON object to stdout, then exits 0.
``describe``/``prepare``/``complete`` are payload kinds, never shell
subcommands. Malformed input, runtime validation problems and provider or
store failures all surface as a parsable, non-empty ``Stopped`` on stdout;
stderr carries diagnostics only. Only a transport failure (the process could
not start or stdout could not be written) escapes this contract.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))

from reading_engine.interface_contracts import runtime_failure  # noqa: E402

# Human-readable, domain-free fallback; duplicated here so even a broken
# core import still yields a lawful Result on stdout.
FALLBACK_ERROR_TEXT = "本次处理未完成，请稍后重试。"

STORE_ROOT_ENV = "MINGLI_STORE_ROOT"
_STATE_ROOT_PARENT = Path(".local/state/mingli-master/instances")

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


def _stopped_error(
    code: str = "runtime.internal_error",
    text: str = FALLBACK_ERROR_TEXT,
) -> dict[str, object]:
    return {
        "kind": "stopped",
        "reason": "error",
        "public_copy": text or FALLBACK_ERROR_TEXT,
        "state_token": None,
        "input_request": None,
        "failure": runtime_failure(code).to_dict(),
        "continuation_allowed": False,
        "terminal": True,
        "completion_committed": False,
    }


def _failure_code_for_exception(error: BaseException) -> str:
    if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)):
        return "transient.timeout"
    if isinstance(error, MemoryError):
        return "transient.resource_unavailable"
    if isinstance(error, OSError) and error.errno in _TRANSIENT_ERRNOS:
        return "transient.resource_unavailable"
    return "runtime.internal_error"


def resolve_store_root(
    skill_root: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Choose a stable private store for one installed Skill instance.

    A host may deliberately provide a private state *base*.  The canonical
    installation path is always hashed into the final namespace, so two
    profiles sharing either ``HOME`` or one configured base cannot resolve
    one another's opaque tokens.
    """

    values = os.environ if environment is None else environment
    configured = str(values.get(STORE_ROOT_ENV) or "").strip()
    if configured:
        base = Path(configured).expanduser()
        if not base.is_absolute():
            raise ValueError(f"{STORE_ROOT_ENV} must be an absolute path")
        base = base.resolve()
    else:
        home = Path(str(values.get("HOME") or Path.home())).expanduser()
        if not home.is_absolute():
            raise ValueError("HOME must be an absolute path")
        base = (home / _STATE_ROOT_PARENT).resolve()
    installation = Path(skill_root).expanduser().resolve()
    namespace = hashlib.sha256(str(installation).encode("utf-8")).hexdigest()
    return (base / namespace / "readings-v51").resolve()


def run(
    stdin_text: str,
    *,
    skill_root: Path,
    store_root: Path,
    stdout,
    stderr,
) -> int:
    """Decode one command, execute it, encode one result. Always one JSON."""

    result_payload: dict[str, object]
    try:
        try:
            payload = json.loads(stdin_text)
        except json.JSONDecodeError as error:
            print(f"json_cli: malformed input: {error}", file=stderr)
            result_payload = _stopped_error("input_contract.malformed_json")
        else:
            from reading_engine.interface import ReadingInterface
            from reading_engine.interface_contracts import command_from_dict

            try:
                command = command_from_dict(payload)
            except (KeyError, TypeError, ValueError) as error:
                print(f"json_cli: invalid command: {error}", file=stderr)
                result_payload = _stopped_error(
                    "input_contract.invalid_command"
                )
            else:
                interface = ReadingInterface(
                    skill_root=skill_root,
                    store_root=store_root,
                )
                result_payload = interface.execute(command).to_dict()
    except Exception as error:  # noqa: BLE001 - stdout must stay lawful
        print(f"json_cli: internal failure: {error}", file=stderr)
        result_payload = _stopped_error(_failure_code_for_exception(error))
    stdout.write(json.dumps(result_payload, ensure_ascii=False) + "\n")
    stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    # Fixed surface: the production codec takes no caller paths and no
    # subcommands; any argument is a usage error (argparse exits 2).
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        store_root = resolve_store_root(PACKAGE_ROOT)
    except ValueError as error:
        print(f"json_cli: invalid state root: {error}", file=sys.stderr)
        print(
            json.dumps(
                _stopped_error("bootstrap.state_root_invalid"),
                ensure_ascii=False,
            )
        )
        return 0
    return run(
        sys.stdin.read(),
        skill_root=PACKAGE_ROOT,
        store_root=store_root,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
