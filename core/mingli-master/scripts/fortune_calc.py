#!/usr/bin/env python3
"""Optional profile wrapper around the deterministic near-time adapter."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from runtime_python import runtime_command


REQUIRED_PROFILE_FIELDS = (
    "birth_datetime",
    "timezone",
    "location",
    "gender",
    "expected_pillars",
)
V6_CONTRACT = "fortune-public-v6-mechanism-stack"
RUNTIME_FILES = (
    "scripts/runtime_python.py",
    "scripts/near_time_fortune_adapter.py",
    "scripts/reading_engine/calendar_core.py",
    "scripts/adapter_validate.py",
)


def _skill_candidates() -> list[Path]:
    configured = os.environ.get("MINGLI_SKILL_DIR")
    if configured:
        return [Path(configured).expanduser().resolve()]
    hermes_home = Path(
        os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    ).expanduser()
    candidates = [
        hermes_home / "skills" / "research" / "mingli-master",
    ]
    unique = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def _find_skill_dir() -> Path:
    for candidate in _skill_candidates():
        adapter = candidate / "scripts" / "near_time_fortune_adapter.py"
        if all((candidate / relpath).is_file() for relpath in RUNTIME_FILES):
            try:
                if V6_CONTRACT in adapter.read_text(encoding="utf-8"):
                    return candidate
            except OSError:
                continue
    if os.environ.get("MINGLI_SKILL_DIR"):
        raise RuntimeError(
            "MINGLI_SKILL_DIR does not point to one complete mingli-master v6 skill"
        )
    raise RuntimeError("mingli-master near-time adapter v6 is not installed")


def _load_profile(configured: str | Path | None = None) -> dict[str, Any]:
    value = configured or os.environ.get("MINGLI_FORTUNE_PROFILE")
    if not value:
        raise RuntimeError(
            "MINGLI_FORTUNE_PROFILE must point to a private natal profile"
        )
    path = Path(value).expanduser()
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("MINGLI_FORTUNE_PROFILE is missing or unsafe")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise RuntimeError("MINGLI_FORTUNE_PROFILE must use mode 0600")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("MINGLI_FORTUNE_PROFILE contains invalid JSON") from exc
    if not isinstance(profile, dict):
        raise RuntimeError("MINGLI_FORTUNE_PROFILE must contain a JSON object")
    missing = [field for field in REQUIRED_PROFILE_FIELDS if not profile.get(field)]
    if missing:
        raise RuntimeError(
            "MINGLI_FORTUNE_PROFILE is missing: " + ", ".join(missing)
        )
    pillars = profile.get("expected_pillars")
    if not isinstance(pillars, list) or len(pillars) != 4:
        raise RuntimeError("MINGLI_FORTUNE_PROFILE expected_pillars must contain four pillars")
    return {field: profile[field] for field in REQUIRED_PROFILE_FIELDS}


def _run_adapter(
    skill_dir: Path,
    args: argparse.Namespace,
    profile: dict[str, Any],
) -> dict[str, Any]:
    adapter = skill_dir / "scripts" / "near_time_fortune_adapter.py"
    command = [
        *runtime_command(),
        str(adapter),
        "--birth-datetime",
        profile["birth_datetime"],
        "--timezone",
        profile["timezone"],
        "--location",
        profile["location"],
        "--gender",
        profile["gender"],
        "--expected-pillars",
        *profile["expected_pillars"],
        "--window",
        args.window,
        "--at",
        args.at,
        "--source-tool",
        "fortune_calc.py",
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "near-time adapter failed")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("near-time adapter returned invalid JSON") from exc


def _resolve_window(args: argparse.Namespace, profile: dict[str, Any]) -> str:
    if args.window:
        return args.window
    timezone = ZoneInfo(profile["timezone"])
    if args.at == "now":
        generated_at = datetime.now(timezone)
    else:
        try:
            generated_at = datetime.fromisoformat(args.at)
        except ValueError as exc:
            raise RuntimeError(f"invalid --at datetime: {args.at}") from exc
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone)
        else:
            generated_at = generated_at.astimezone(timezone)
    offset = 1 if args.target == "tomorrow" else 0
    target_date = (generated_at.date() + timedelta(days=offset)).isoformat()
    return f"{target_date} 00:00-{target_date} 23:59"


def _validate(skill_dir: Path, payload: dict[str, Any]) -> None:
    path = skill_dir / "scripts" / "adapter_validate.py"
    scripts_dir = str(path.parent)
    spec = importlib.util.spec_from_file_location("mingli_adapter_validate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load mingli adapter validator")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, scripts_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(scripts_dir)
        except ValueError:
            pass
    result = module.validate_payload("fortune", payload)
    if not result["ok"]:
        raise RuntimeError("near-time fact validation failed: " + ", ".join(result["codes"]))



def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--window")
    target.add_argument("--target", choices=("today", "tomorrow"))
    parser.add_argument("--at", default="now", help="Generation timestamp; target time comes from --window")
    parser.add_argument("--history-db", help=argparse.SUPPRESS)
    parser.add_argument("--output")
    return parser


def _validate_fortune_inputs(args: argparse.Namespace) -> None:
    """Section 8 hardening: reject malformed inputs before touching the adapter."""
    if args.target not in (None, "today", "tomorrow") and args.window is None:
        raise RuntimeError(f"invalid --target: {args.target!r}")
    if args.at != "now":
        try:
            datetime.fromisoformat(args.at)
        except ValueError as exc:
            raise RuntimeError(f"invalid --at datetime: {args.at}") from exc


def main() -> int:
    args = _parser().parse_args()
    try:
        profile = _load_profile()
        args.window = _resolve_window(args, profile)
        _validate_fortune_inputs(args)
        skill_dir = _find_skill_dir()
        rendered_payload = _run_adapter(skill_dir, args, profile)
        _validate(skill_dir, rendered_payload)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    rendered = json.dumps(rendered_payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
