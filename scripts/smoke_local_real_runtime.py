#!/usr/bin/env python3
"""Local real Runtime + (optional) real model smoke entry - fail-closed.

Normally invoked through scripts/run_local_real_runtime_smoke.sh, which loads
the private 0600 env file (~/.config/mingli/local-real-model.env) and validates
paths before calling this script. Can also be run directly after exporting the
same MINGLI_* / DEEPSEEK_API_KEY variables:

    uv run --project backend python scripts/smoke_local_real_runtime.py

Guarantees:
- Never prints DEEPSEEK_API_KEY, state tokens, or the raw narrative prompt.
- Prints only digests, shapes, inventory counts and receipt metadata.
- Exit 0 only when everything that was requested actually succeeded.

Exit codes: 0 ok, 2 configuration missing, 3 runtime startup failed,
4 real model smoke failed, 1 unexpected.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.adapters.model import build_deepseek_model_adapter
from app.adapters.runtime import (
    RuntimeStartupError,
    build_runtime_startup_gate,
)
from app.config import Settings
from app.readings.narrative_contracts import NarrativeRequest
from app.readings.output_contracts import PREVIEW_V1
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_prepare,
)
from app.readings.runtime_contracts import Prepared, Stopped

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_RUNTIME = 3
EXIT_MODEL = 4
EXIT_UNEXPECTED = 1

NARRATIVE_POLICY_VERSION = "policy-v1"


class SmokeConfigError(RuntimeError):
    """Local configuration is missing or invalid; nothing ran."""


class SmokeModelError(RuntimeError):
    """Real model smoke failed."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _build_gate(settings: Settings) -> Any:
    """Fail-closed configuration checks, then build the real Runtime gate."""

    if settings.runtime_adapter != "one-shot":
        raise SmokeConfigError(
            "MINGLI_RUNTIME_ADAPTER must be 'one-shot' "
            f"(got {settings.runtime_adapter!r})"
        )
    required = {
        "MINGLI_RUNTIME_LAUNCHER_PATH": settings.runtime_launcher_path,
        "MINGLI_RUNTIME_PYTHON_PATH": settings.runtime_python_path,
        "MINGLI_RUNTIME_RELEASE_ROOT": settings.runtime_release_root,
        "MINGLI_RUNTIME_STATE_ROOT": settings.runtime_state_root,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise SmokeConfigError(f"missing runtime settings: {', '.join(missing)}")
    for name, value in required.items():
        assert value is not None
        if not value.exists():
            raise SmokeConfigError(f"{name} does not exist: {value}")
    if settings.runtime_expected_manifest_digest is None:
        raise SmokeConfigError("MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST is missing")
    if settings.runtime_expected_capability_shape_sha256 is None:
        raise SmokeConfigError(
            "MINGLI_RUNTIME_EXPECTED_CAPABILITY_SHAPE_SHA256 is missing"
        )
    return build_runtime_startup_gate(settings)


def _describe_summary(settings: Settings, gate: Any, described: Any) -> dict[str, Any]:
    inventory = gate.release_inspector.inspect()
    capability_ids = [str(item["id"]) for item in described.capabilities]
    return {
        "adapter_kind": getattr(gate.runtime, "adapter_kind", "unknown"),
        "protocol_version": described.protocol_version,
        "manifest_digest": described.manifest_digest,
        "capability_shape_sha256": settings.runtime_expected_capability_shape_sha256,
        "capability_count": len(capability_ids),
        "capability_ids": capability_ids,
        "inventory": {
            "release_manifest_sha256": inventory.release_manifest_sha256,
            "release_file_count": inventory.release_file_count,
            "provider_count": len(inventory.provider_ids),
            "reference_pack_count": inventory.reference_pack_count,
            "evidence_record_count": inventory.evidence_record_count,
            "runtime_closure_file_count": inventory.runtime_closure_file_count,
        },
    }


async def _model_summary(settings: Settings, runtime: Any) -> dict[str, Any]:
    """One real bazi prepare + one real model generate; return safe summary."""

    if settings.deepseek_api_key is None:
        raise SmokeConfigError(
            "DEEPSEEK_API_KEY is not set - real-model smoke cannot run. "
            "Add the key to the private env file and re-run (or use --model)."
        )
    if settings.model_price_snapshot_version is None:
        raise SmokeConfigError("MINGLI_MODEL_PRICE_SNAPSHOT_VERSION is missing")

    profile = ConfirmedProfileVersion(
        subject_ref="profile-version:smoke-fixture",
        birth_datetime="1994-04-30T05:55:00+08:00",
        birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
        timezone="Asia/Shanghai",
        location="上海",
        gender="男",
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=121.47,
        latitude=31.23,
        coordinate_source="smoke-fixture",
    )
    prepare = compile_bazi_prepare(
        action="profile_preview",
        query="看一下这个八字",
        profile=profile,
        dimension_ids=("career",),
    )
    result = await runtime.execute(prepare)
    if isinstance(result, Stopped):
        input_request = getattr(result, "input_request", None)
        raise SmokeModelError(
            "bazi prepare stopped: "
            f"reason={result.reason} input_request={input_request}"
        )
    if not isinstance(result, Prepared):
        raise SmokeModelError(f"bazi prepare returned unexpected result: {result.kind}")

    request = NarrativeRequest(
        brief=result.brief,
        narrative_policy_version=NARRATIVE_POLICY_VERSION,
        output_contract=PREVIEW_V1,
        language="zh-CN",
        max_output_chars=PREVIEW_V1.max_output_chars,
    )
    adapter = build_deepseek_model_adapter(settings)
    try:
        generation = await adapter.generate(request)
    except Exception as error:
        raise SmokeModelError(
            f"real model generate failed: {type(error).__name__}: {error}"
        ) from error
    finally:
        await adapter.aclose()

    receipt = generation.receipt
    blocks = list(generation.candidate.blocks)
    if receipt.outcome != "succeeded":
        raise SmokeModelError(
            f"model receipt outcome is {receipt.outcome!r} "
            f"(error_code={receipt.error_code!r})"
        )
    if not blocks:
        raise SmokeModelError("model returned a candidate with no blocks")
    return {
        "receipt_outcome": receipt.outcome,
        "model_profile_id": receipt.model_profile_id,
        "provider": receipt.provider,
        "provider_model_version": receipt.provider_model_version,
        "model_profile_snapshot_digest": receipt.model_profile_snapshot_digest,
        "request_fingerprint": receipt.request_fingerprint,
        "latency_ms": receipt.latency_ms,
        "usage": {
            "input_tokens": receipt.usage.input_tokens if receipt.usage else None,
            "output_tokens": receipt.usage.output_tokens if receipt.usage else None,
        },
        "cost_microunits": (
            int(receipt.cost.microunits) if receipt.cost is not None else None
        ),
        "candidate_block_count": len(blocks),
        "candidate_dimension_ids": sorted({block.dimension_id for block in blocks}),
        "candidate_chars": sum(len(block.text) for block in blocks),
    }


async def _run_async(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    settings = Settings()
    summary: dict[str, Any] = {
        "schema": "mingli-local-real-smoke-v1",
        "started_at": _utc_now(),
        "model_mode": args.model_mode,
        "runtime": None,
        "model": None,
        "status": "failed",
        "exit_code": EXIT_UNEXPECTED,
        "error": None,
    }
    try:
        gate = _build_gate(settings)
        described = await gate.startup()
        runtime_summary = _describe_summary(settings, gate, described)
        summary["runtime"] = runtime_summary
        print(
            "runtime startup   : OK "
            f"({runtime_summary['adapter_kind']} / "
            f"{runtime_summary['capability_count']}/{runtime_summary['capability_count']} describe)"
        )
        print(f"protocol          : {runtime_summary['protocol_version']}")
        print(f"manifest digest   : {runtime_summary['manifest_digest']}")
        print(
            "capability shape  : "
            f"{runtime_summary['capability_shape_sha256']}"
        )
        print(
            "inventory         : "
            f"{runtime_summary['inventory']['release_file_count']} files / "
            f"{runtime_summary['inventory']['provider_count']} providers / "
            f"{runtime_summary['inventory']['reference_pack_count']} reference packs / "
            f"{runtime_summary['inventory']['evidence_record_count']} evidence"
        )
        print(
            "capabilities      : "
            + ", ".join(runtime_summary["capability_ids"])
        )

        run_model = {
            "auto": settings.deepseek_api_key is not None,
            "model": True,
            "skip": False,
        }[args.model_mode]
        if run_model:
            model_summary = await _model_summary(settings, gate.runtime)
            summary["model"] = model_summary
            print(
                "model smoke       : OK "
                f"({model_summary['receipt_outcome']} / "
                f"{model_summary['provider_model_version']} / "
                f"{model_summary['candidate_block_count']} blocks / "
                f"{model_summary['candidate_chars']} chars)"
            )
        else:
            skip_reason = (
                "explicit --skip-model"
                if args.model_mode == "skip"
                else "no DEEPSEEK_API_KEY"
            )
            print(
                f"model smoke       : SKIPPED "
                f"({skip_reason}; Runtime gate only)"
            )
        summary["status"] = "passed"
        summary["exit_code"] = EXIT_OK
        return summary, EXIT_OK
    except SmokeConfigError as error:
        summary["error"] = f"config: {error}"
        summary["exit_code"] = EXIT_CONFIG
        print(f"SMOKE FAIL-CLOSED (config): {error}", file=sys.stderr)
        return summary, EXIT_CONFIG
    except RuntimeStartupError as error:
        summary["error"] = f"runtime: {error}"
        summary["exit_code"] = EXIT_RUNTIME
        print(f"SMOKE FAIL-CLOSED (runtime): {error}", file=sys.stderr)
        return summary, EXIT_RUNTIME
    except SmokeModelError as error:
        summary["error"] = f"model: {error}"
        summary["exit_code"] = EXIT_MODEL
        print(f"SMOKE FAIL-CLOSED (model): {error}", file=sys.stderr)
        return summary, EXIT_MODEL
    except Exception as error:  # noqa: BLE001
        summary["error"] = f"unexpected: {type(error).__name__}: {error}"
        summary["exit_code"] = EXIT_UNEXPECTED
        print(f"SMOKE FAIL-CLOSED (unexpected): {error}", file=sys.stderr)
        return summary, EXIT_UNEXPECTED


def _run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-mode",
        choices=("auto", "model", "skip"),
        default="auto",
        help="auto: run model smoke when DEEPSEEK_API_KEY is present",
    )
    parser.add_argument(
        "--evidence-dir",
        default=None,
        help="write non-sensitive smoke-summary.json here",
    )
    args = parser.parse_args()
    summary, exit_code = asyncio.run(_run_async(args))
    summary["finished_at"] = _utc_now()
    if args.evidence_dir:
        evidence_path = Path(args.evidence_dir)
        evidence_path.mkdir(parents=True, exist_ok=True)
        (evidence_path / "smoke-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(_run())
