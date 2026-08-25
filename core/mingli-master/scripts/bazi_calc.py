#!/usr/bin/env python3
"""Private deterministic fact calculator used by the portable provider."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CALCULATION_CONTRACT = "mingli-bazi-pipeline-v1-interpreted"
MAX_LOCATION_CHARS = 100
RUNTIME_FILES = (
    "scripts/bazi_calc.py",
    "scripts/runtime_python.py",
    "scripts/bazi_fact_adapter.py",
    "scripts/reading_engine/calendar_core.py",
    "scripts/adapter_validate.py",
)


def _skill_candidates() -> list[Path]:
    configured = os.environ.get("MINGLI_SKILL_DIR")
    if configured:
        return [Path(configured).expanduser().resolve()]
    # A copied portable artifact remains self-contained when its legacy CLI
    # is called directly. It must never discover a host-specific install.
    return [Path(__file__).resolve().parents[1]]


def _find_skill_dir() -> Path:
    for candidate in _skill_candidates():
        if all((candidate / relpath).is_file() for relpath in RUNTIME_FILES):
            return candidate
    if os.environ.get("MINGLI_SKILL_DIR"):
        raise RuntimeError("MINGLI_SKILL_DIR does not contain a complete Bazi runtime")
    raise RuntimeError("mingli-master Bazi runtime is incomplete")


def _import_skill_module(skill_dir: Path, name: str) -> Any:
    scripts_dir = str(skill_dir / "scripts")
    sys.path.insert(0, scripts_dir)
    try:
        return importlib.import_module(name)
    finally:
        try:
            sys.path.remove(scripts_dir)
        except ValueError:
            pass


def _run_adapter(skill_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Run the deterministic adapter inside the validated Runtime process.

    ``runtime_launcher`` has already validated and loaded the pinned Runtime
    before a production Provider reaches this seam.  Starting the same Python
    again here repeated both the Runtime probe and the complete signed evidence
    index validation.  Calling the bundled adapter module directly preserves
    that dependency identity while allowing its evidence-rule cache to be
    shared with the enclosing Prepare.

    The previous subprocess boundary normalized the adapter payload through
    JSON before returning it.  Keep that byte-level shape (sorted object keys,
    tuples converted to arrays, and only JSON values) so this optimization
    cannot change the Provider contract.
    """

    adapter = _import_skill_module(skill_dir, "bazi_fact_adapter")
    try:
        question_contract = {
            "domains": list(getattr(args, "reasoning_domains", None) or ()),
            "gender": args.gender,
        }
        if args.mode == "birth":
            payload, conflict = adapter.build_from_birth(
                args.civil_datetime,
                timezone_name=args.timezone,
                location=args.location,
                gender=args.gender,
                expected_pillars=args.expected_pillars,
                zi_hour_policy=args.zi_hour_policy,
                longitude=getattr(args, "longitude", None),
                latitude=getattr(args, "latitude", None),
                coordinate_source=getattr(args, "coordinate_source", None),
                coordinate_accuracy_meters=getattr(
                    args, "coordinate_accuracy_meters", None
                ),
                time_basis_policy=(
                    getattr(args, "time_basis_policy", None) or "civil"
                ),
                question_contract=question_contract,
            )
        else:
            payload = adapter.build_from_pillars(
                args.pillars,
                gender=args.gender,
                source=args.source,
                source_ref=args.source_ref,
                question_contract=question_contract,
            )
            conflict = False
        normalized = json.loads(
            json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError(str(exc) or "Bazi adapter failed") from exc
    if not isinstance(normalized, dict):
        raise RuntimeError("Bazi adapter returned a non-object")
    if conflict or normalized.get("conflicts"):
        raise RuntimeError("Bazi birth data conflict with the supplied four pillars")
    return normalized


def _validate_facts(skill_dir: Path, facts: dict[str, Any]) -> None:
    module = _import_skill_module(skill_dir, "adapter_validate")
    result = module.validate_payload("bazi", facts)
    if not result.get("ok"):
        codes = ", ".join(result.get("codes") or ["unknown_validation_error"])
        raise RuntimeError("Bazi fact validation failed: " + codes)



def _resolve_as_of(value: str, timezone_name: str) -> str:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"invalid reading timezone: {timezone_name}") from exc
    if value == "now":
        resolved = datetime.now(zone)
    else:
        try:
            resolved = datetime.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError(f"invalid --as-of: {value}") from exc
        resolved = (
            resolved.replace(tzinfo=zone)
            if resolved.tzinfo is None
            else resolved.astimezone(zone)
        )
    return resolved.isoformat(timespec="seconds")



def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    birth = subparsers.add_parser("birth")
    _add_common(birth)
    birth.add_argument("--datetime", required=True, dest="civil_datetime")
    birth.add_argument("--timezone", required=True)
    birth.add_argument("--location", required=True)
    birth.add_argument("--longitude", type=float)
    birth.add_argument("--latitude", type=float)
    birth.add_argument("--coordinate-source")
    birth.add_argument("--coordinate-accuracy-meters", type=float)
    birth.add_argument(
        "--time-basis-policy",
        choices=("civil", "longitude_mean_solar-v1", "local_apparent_solar-v1"),
        default="civil",
    )
    birth.add_argument("--gender", required=True)
    birth.add_argument("--expected-pillars", nargs="+")
    birth.add_argument(
        "--zi-hour-policy",
        choices=("midnight", "late-zi-next-day"),
        default="midnight",
    )
    pillars = subparsers.add_parser("pillars")
    _add_common(pillars)
    pillars.add_argument("--pillars", nargs="+", required=True)
    pillars.add_argument("--gender")
    pillars.add_argument(
        "--source",
        choices=("image", "text", "user_chart", "user_text", "screenshot"),
        default="text",
    )
    pillars.add_argument("--source-ref")
    return parser


def _validate_inputs(args: argparse.Namespace) -> None:
    if args.mode == "birth":
        args.location = str(args.location or "").strip()
        if not args.location:
            raise RuntimeError("location must not be blank")
        if len(args.location) > MAX_LOCATION_CHARS:
            raise RuntimeError(
                f"location is too long; maximum is {MAX_LOCATION_CHARS} chars"
            )


def main() -> int:
    args = _parser().parse_args()
    try:
        _validate_inputs(args)
        skill_dir = _find_skill_dir()
        facts = _run_adapter(skill_dir, args)
        _validate_facts(skill_dir, facts)
        rendered = json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
