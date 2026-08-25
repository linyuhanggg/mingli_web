#!/usr/bin/env python3
"""Compare Da Liu Ren Prepare one-shot latency and output equivalence.

Every sample launches the production Runtime shell/codec boundary used by the
Backend adapter.  One process-start sample per variant is kept separate, then
hot samples are paired and their execution order alternates to reduce temporal
bias.  Percentiles use linear interpolation over sorted values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

PAYLOAD = {
    "kind": "prepare",
    "query": "请排出这件事的大六壬课盘。",
    "intent": {
        "subject_refs": ["liuren:ming21-performance-fixture"],
        "object_id": "concrete_event",
        "dimension_ids": ["outcome"],
        "horizon": {
            "kind_id": "instant",
            "start": None,
            "end": None,
        },
        "capability_id": "liuren",
        "comparisons": [],
    },
    "facts": {
        "liuren:ming21-performance-fixture": {
            "event_datetime_or_reference_datetime": (
                "2026-08-14T10:00:00+08:00"
            ),
            "timezone": "Asia/Shanghai",
            "location": "合成测试地点",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": None,
            "latitude": None,
            "coordinate_source": None,
        }
    },
    "state_token": None,
    "transition": None,
}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires at least one sample")
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "p50_ms": round(_percentile(values, 0.50), 3),
        "p95_ms": round(_percentile(values, 0.95), 3),
        "p99_ms": round(_percentile(values, 0.99), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def _run_one(
    *,
    runtime_python: Path,
    release_root: Path,
    store_root: Path,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["MINGLI_PYTHON"] = str(runtime_python)
    environment["MINGLI_STORE_ROOT"] = str(store_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [str(release_root / "scripts/run_reading_transaction.sh")]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        input=json.dumps(PAYLOAD, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if completed.returncode != 0:
        raise RuntimeError(
            f"Runtime exited {completed.returncode}: {completed.stderr.strip()}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Runtime returned invalid JSON") from error
    if result.get("kind") != "prepared":
        raise RuntimeError(
            f"Runtime did not prepare: {result.get('kind')} {result.get('reason')}"
        )
    state_token = result.get("state_token")
    if not isinstance(state_token, str) or not state_token:
        raise RuntimeError("Prepared result has no state token")
    normalized_stdout = completed.stdout.replace(
        state_token,
        "0" * len(state_token),
        1,
    )
    brief = result.get("brief")
    if not isinstance(brief, dict):
        raise RuntimeError("Prepared result has no brief")
    facts = brief.get("facts")
    evidence = brief.get("evidence")
    findings = brief.get("findings")
    if not all(isinstance(item, list) for item in (facts, evidence, findings)):
        raise RuntimeError("Prepared brief collections are malformed")
    return {
        "elapsed_ms": round(elapsed_ms, 3),
        "stdout_bytes": len(completed.stdout.encode("utf-8")),
        "normalized_stdout_sha256": _sha256(
            normalized_stdout.encode("utf-8")
        ),
        "brief_sha256": _canonical_digest(brief),
        "facts_sha256": _canonical_digest(facts),
        "evidence_sha256": _canonical_digest(evidence),
        "findings_sha256": _canonical_digest(findings),
        "fact_count": len(facts),
        "evidence_count": len(evidence),
        "finding_count": len(findings),
        "stderr": completed.stderr,
    }


def _variant_summary(
    cold: dict[str, Any],
    hot: list[dict[str, Any]],
) -> dict[str, Any]:
    output_fields = (
        "stdout_bytes",
        "normalized_stdout_sha256",
        "brief_sha256",
        "facts_sha256",
        "evidence_sha256",
        "findings_sha256",
        "fact_count",
        "evidence_count",
        "finding_count",
    )
    return {
        "cold_ms": cold["elapsed_ms"],
        "hot_samples": len(hot),
        "hot_ms": [sample["elapsed_ms"] for sample in hot],
        "hot_summary": _summary(
            [float(sample["elapsed_ms"]) for sample in hot]
        ),
        "output": {field: cold[field] for field in output_fields},
        "all_samples_output_stable": all(
            all(sample[field] == cold[field] for field in output_fields)
            for sample in hot
        ),
        "all_samples_stderr_empty": not cold["stderr"]
        and all(not sample["stderr"] for sample in hot),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--runtime-python", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 30:
        parser.error("--samples must be at least 30")

    roots = {
        "baseline": args.baseline_root.resolve(strict=True),
        "candidate": args.candidate_root.resolve(strict=True),
    }
    runtime_python = args.runtime_python.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="ming21-liuren-benchmark-") as temp:
        store_base = Path(temp).resolve()
        cold = {
            name: _run_one(
                runtime_python=runtime_python,
                release_root=root,
                store_root=store_base / name,
            )
            for name, root in roots.items()
        }
        hot: dict[str, list[dict[str, Any]]] = {
            "baseline": [],
            "candidate": [],
        }
        for index in range(args.samples):
            order = (
                ("baseline", "candidate")
                if index % 2 == 0
                else ("candidate", "baseline")
            )
            for name in order:
                hot[name].append(
                    _run_one(
                        runtime_python=runtime_python,
                        release_root=roots[name],
                        store_root=store_base / name,
                    )
                )

    summaries = {
        name: _variant_summary(cold[name], hot[name]) for name in roots
    }
    output_fields = tuple(summaries["baseline"]["output"])
    report = {
        "schema_version": "ming21-liuren-prepare-benchmark-v1",
        "method": {
            "cold_samples_per_variant": 1,
            "hot_samples_per_variant": args.samples,
            "hot_order": "paired_alternating",
            "percentile": "linear_interpolation_(n-1)*q",
            "process_model": "fresh_production_runtime_one_shot_per_sample",
        },
        "runtime_python": str(runtime_python),
        "roots": {name: str(root) for name, root in roots.items()},
        "variants": summaries,
        "equivalence": {
            "fields": list(output_fields),
            "all_equal": all(
                summaries["baseline"]["output"][field]
                == summaries["candidate"]["output"][field]
                for field in output_fields
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
