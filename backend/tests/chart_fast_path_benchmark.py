"""Opt-in real-Runtime benchmark for the five deterministic chart starts.

Run from ``backend``. The script copies an admitted release to a temporary
directory so removable-volume mode loss does not invalidate startup admission.
It prints JSON only and never sends synthetic profile data outside the process.
"""

# ruff: noqa: E402 -- executable scripts must add the backend root before app imports.

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.adapters.runtime import (
    V53_TIME_CHECK_RELEASE_FILE_COUNT,
    FileSystemRuntimeReleaseInspector,
    OneShotMingliRuntimeAdapter,
    RuntimeStartupGate,
    build_runtime_startup_gate,
    runtime_capability_shape_sha256,
)
from app.config import _RUNTIME_RELEASE_PROFILES, Settings
from app.database import Database
from app.identity.models import Base
from app.main import create_app
from app.readings.capability_policy import V53_TIME_CHECK_RELEASE_CAPABILITY_IDS
from app.readings.repository import SqlReadingRepository
from app.readings.runtime_contracts import Describe, Described
from app.security.envelope import EnvelopeCipher
from httpx import ASGITransport, AsyncClient

QA_LOCKED_BAZI_CALC_SHA256 = (
    "ab35fbf511693d47487aa0601bdba32d13a44cf988888b90c085d6573027249a"
)
_BAZI_CALC_RELATIVE = "scripts/bazi_calc.py"


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 3)


def _distribution(values: list[float]) -> dict[str, float]:
    return {
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_admitted_release(source: Path, destination: Path) -> None:
    source_manifest = source / ".mingli-release-manifest.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    destination.mkdir()
    shutil.copy2(source_manifest, destination / source_manifest.name)
    for relative in manifest["files"]:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    for relative, mode in manifest["modes"].items():
        (destination / relative).chmod(mode)


def _overlay_locked_bazi_calc(release_root: Path, bazi_calc: Path) -> dict[str, str]:
    """Replace signed bazi_calc.py in place and remanifest that one digest."""

    payload = bazi_calc.read_bytes()
    overlay_sha256 = hashlib.sha256(payload).hexdigest()
    if overlay_sha256 != QA_LOCKED_BAZI_CALC_SHA256:
        raise RuntimeError(
            "overlay bazi_calc.py is not the QA-locked SHA-256 "
            f"{QA_LOCKED_BAZI_CALC_SHA256}"
        )
    target = release_root / _BAZI_CALC_RELATIVE
    replaced_sha256 = _sha256_file(target)
    mode = target.stat().st_mode
    target.write_bytes(payload)
    target.chmod(mode)
    manifest_path = release_root / ".mingli-release-manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    if manifest_text.count(replaced_sha256) != 1:
        raise RuntimeError("admitted bazi_calc.py digest is missing or not unique")
    manifest_path.write_text(
        manifest_text.replace(replaced_sha256, overlay_sha256),
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "bazi_calc_path": _BAZI_CALC_RELATIVE,
        "bazi_calc_sha256": overlay_sha256,
        "replaced_bazi_calc_sha256": replaced_sha256,
        "release_name": str(manifest["release"]),
        "source_commit": str(manifest["source_commit"]),
        "release_manifest_sha256": _sha256_file(manifest_path),
        "file_count": str(len(manifest["files"])),
        "diff": "scripts/bazi_calc.py only",
    }


def _copy_clean_runtime_python(source_python: Path, destination: Path) -> Path:
    """Clone the provisioned venv without mutable bytecode caches."""

    source_venv = source_python.parents[1]
    shutil.copytree(
        source_venv,
        destination,
        copy_function=shutil.copy2,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    return destination / "bin" / "python"


async def _seed_release(
    database: Database,
    settings: Settings,
    *,
    release_manifest_digest: str,
    describe_manifest_digest: str,
    source_commit: str,
    release_name: str,
) -> None:
    async with database.sessions() as session, session.begin():
        repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        await repository.create_runtime_release(
            name=release_name,
            version="5.3",
            source_commit=source_commit,
            release_manifest_digest=release_manifest_digest,
            protocol_version="mingli-portable-interface-v2",
            describe_manifest_digest=describe_manifest_digest,
            image_digest=None,
            production_ready=True,
        )


async def _create_profile(
    client: AsyncClient,
    headers: dict[str, str],
) -> str:
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "合成基准夹具"},
    )
    draft.raise_for_status()
    confirmed = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "合成测试地点",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 121.0,
            "latitude": 31.0,
            "coordinate_source": "synthetic-fixture",
        },
    )
    confirmed.raise_for_status()
    return str(confirmed.json()["profile_version_id"])


def _cases(profile_version_id: str) -> dict[str, tuple[str, dict[str, object], str]]:
    event_datetime = "2026-08-14T10:00:00+08:00"
    return {
        "bazi": (
            "/api/v1/readings/preview",
            {"profile_version_id": profile_version_id, "dimension_ids": ["career"]},
            "bazi-chart/v1",
        ),
        "ziwei": (
            "/api/v1/readings/ziwei",
            {"profile_version_id": profile_version_id, "dimension_ids": ["career"]},
            "ziwei-chart/v1",
        ),
        "liuyao": (
            "/api/v1/readings/liuyao",
            {
                "cast": [6, 7, 8, 9, 7, 8],
                "event_datetime": event_datetime,
                "timezone": "Asia/Shanghai",
                "location": "合成测试地点",
                "dimension_ids": ["outcome"],
            },
            "liuyao-chart/v1",
        ),
        "meihua": (
            "/api/v1/readings/meihua",
            {
                "casting_method": "time",
                "event_datetime": event_datetime,
                "timezone": "Asia/Shanghai",
                "location": "合成测试地点",
                "dimension_ids": ["outcome", "state"],
            },
            "meihua-chart/v1",
        ),
        "daliuren": (
            "/api/v1/readings/daliuren",
            {
                "event_datetime": event_datetime,
                "timezone": "Asia/Shanghai",
                "location": "合成测试地点",
                "dimension_ids": ["outcome"],
            },
            "daliuren-chart/v1",
        ),
    }


async def _sample(
    client: AsyncClient,
    headers: dict[str, str],
    path: str,
    payload: dict[str, object],
    schema_version: str,
) -> dict[str, float]:
    started_at = time.perf_counter()
    response = await client.post(path, headers=headers, json=payload)
    post_ms = (time.perf_counter() - started_at) * 1000
    if response.status_code != 201:
        problem = response.json()
        raise RuntimeError(
            f"{path} failed: {response.status_code} {problem.get('detail', problem.get('title'))}"
        )
    body = response.json()
    view_model = body.get("view_model")
    if body.get("status") != "prepared" or not isinstance(view_model, dict):
        raise RuntimeError(f"{path} did not return a prepared ViewModel: {body}")
    if view_model.get("schema_version") != schema_version:
        raise RuntimeError(f"{path} returned the wrong ViewModel schema: {view_model}")
    timing = body["fast_path_timing"]
    version_id = body["reading_version_id"]

    poll_started_at = time.perf_counter()
    poll = await client.get(f"/api/v1/readings/{version_id}")
    first_ready_poll_ms = (time.perf_counter() - poll_started_at) * 1000
    poll.raise_for_status()
    if poll.json()["status"] != "prepared":
        raise RuntimeError(f"{path} first poll was not ready")

    result_started_at = time.perf_counter()
    result = await client.get(f"/api/v1/readings/{version_id}/result")
    result_fetch_ms = (time.perf_counter() - result_started_at) * 1000
    result.raise_for_status()
    if result.json()["view_model"]["schema_version"] != schema_version:
        raise RuntimeError(f"{path} result projection changed")

    return {
        "post_ms": post_ms,
        "api_orchestration_ms": max(
            0.0,
            float(timing["total_ms"])
            - float(timing["runtime_one_shot_ms"])
            - float(timing["db_persistence_ms"]),
        ),
        "queue_wait_ms": float(timing["queue_wait_ms"]),
        "worker_pickup_ms": float(timing["worker_pickup_ms"]),
        "runtime_one_shot_ms": float(timing["runtime_one_shot_ms"]),
        "db_persistence_ms": float(timing["db_persistence_ms"]),
        "first_ready_poll_ms": first_ready_poll_ms,
        "result_fetch_ms": result_fetch_ms,
        # Backend proxy for browser paint: the chart is renderable once the POST
        # body arrives; browser layout/paint remains a user-test measurement.
        "first_renderable_response_ms": post_ms,
    }


async def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
    selected_products = tuple(args.products)
    cases_filter = set(selected_products)
    with tempfile.TemporaryDirectory(prefix="ming21-chart-fast-path-") as temporary:
        temporary_root = Path(temporary)
        release_root = temporary_root / "release"
        _copy_admitted_release(args.release_root, release_root)
        overlay_identity: dict[str, str] | None = None
        if args.overlay_bazi_calc is not None:
            overlay_identity = _overlay_locked_bazi_calc(
                release_root,
                args.overlay_bazi_calc,
            )
        runtime_python = _copy_clean_runtime_python(
            args.runtime_python,
            temporary_root / "runtime-venv",
        )
        state_root = temporary_root / "state"
        state_root.mkdir(mode=0o700)
        database_path = temporary_root / "benchmark.sqlite3"
        expected_manifest_digest = profile["manifest_digest"]
        expected_release_manifest_sha256 = profile["release_manifest_sha256"]
        expected_capability_shape = profile["capability_shape_sha256"]
        if overlay_identity is not None:
            expected_release_manifest_sha256 = overlay_identity["release_manifest_sha256"]
        settings = Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{database_path}",
            cookie_secure=True,
            otp_adapter="fake",
            admin_bootstrap_email="ops@example.com",
            admin_bootstrap_password="correct-horse",
            log_level="WARNING",
            reading_write_rate_limit=max(1000, args.samples * 10),
            runtime_adapter="one-shot",
            runtime_release_profile="v53-time-check",
            runtime_launcher_path=release_root / "scripts" / "run_reading_transaction.sh",
            runtime_python_path=runtime_python,
            runtime_release_root=release_root,
            runtime_state_root=state_root,
            runtime_expected_manifest_digest=expected_manifest_digest,
            runtime_expected_capability_shape_sha256=expected_capability_shape,
            runtime_timeout_seconds=30,
            chart_fast_path_timeout_seconds=2,
        )
        database = Database(settings.database_url)
        # Import model modules before metadata creation.
        for module in (
            "app.profiles.models",
            "app.readings.models",
            "app.admin.models",
            "app.support.models",
            "app.entitlements.models",
            "app.commerce.models",
            "app.referrals.models",
            "app.content.models",
            "app.privacy.models",
            "app.media.models",
        ):
            __import__(module)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        cold_started_at = time.perf_counter()
        runtime = OneShotMingliRuntimeAdapter(
            launcher_path=release_root / "scripts" / "run_reading_transaction.sh",
            runtime_python_path=runtime_python,
            state_root=state_root,
            timeout_seconds=settings.runtime_timeout_seconds,
        )
        described: Described
        if args.skip_admission:
            described_result = await runtime.execute(Describe())
            if not isinstance(described_result, Described):
                raise RuntimeError("diagnostic candidate did not return Described")
            described = described_result
            admission = "diagnostic_skipped"
        elif overlay_identity is None:
            gate = build_runtime_startup_gate(settings)
            described = await gate.startup()
            runtime = gate.runtime
            admission = "passed"
        else:
            described_result = await runtime.execute(Describe())
            if not isinstance(described_result, Described):
                raise RuntimeError("candidate Runtime did not return Described")
            described = described_result
            capability_shape = runtime_capability_shape_sha256(described.capabilities)
            inspector = FileSystemRuntimeReleaseInspector(
                release_root=release_root,
                expected_release_manifest_sha256=expected_release_manifest_sha256,
                expected_release_name=profile["release_name"],
                expected_source_commit=profile["source_commit"],
                expected_capability_ids=V53_TIME_CHECK_RELEASE_CAPABILITY_IDS,
                expected_release_file_count=V53_TIME_CHECK_RELEASE_FILE_COUNT,
            )
            gate = RuntimeStartupGate(
                runtime=runtime,
                release_inspector=inspector,
                expected_manifest_digest=described.manifest_digest,
                expected_release_manifest_sha256=expected_release_manifest_sha256,
                expected_capability_shape_sha256=capability_shape,
                expected_capability_ids=V53_TIME_CHECK_RELEASE_CAPABILITY_IDS,
                expected_release_file_count=V53_TIME_CHECK_RELEASE_FILE_COUNT,
            )
            described = await gate.startup()
            runtime = gate.runtime
            admission = "candidate_remanifested"
        await _seed_release(
            database,
            settings,
            release_manifest_digest=expected_release_manifest_sha256,
            describe_manifest_digest=described.manifest_digest,
            source_commit=(
                overlay_identity["source_commit"]
                if overlay_identity is not None
                else profile["source_commit"]
            ),
            release_name=(
                overlay_identity["release_name"]
                if overlay_identity is not None
                else profile["release_name"]
            ),
        )
        startup_ms = (time.perf_counter() - cold_started_at) * 1000
        application = create_app(
            settings=settings,
            database=database,
            chart_runtime=runtime,
        )
        logging.getLogger("mingli.api").setLevel(logging.WARNING)
        logging.getLogger("mingli.chart_fast_path").setLevel(logging.WARNING)
        try:
            async with AsyncClient(
                transport=ASGITransport(app=application),
                base_url="https://benchmark.local",
            ) as client:
                guest = await client.post("/api/v1/guest-sessions")
                guest.raise_for_status()
                headers = {"X-CSRF-Token": str(guest.json()["csrf_token"])}
                profile_version_id = await _create_profile(client, headers)
                result: dict[str, Any] = {
                    "runtime_startup_ms": round(startup_ms, 3),
                    "runtime_admission": admission,
                    "runtime_identity": {
                        "release_name": (
                            overlay_identity["release_name"]
                            if overlay_identity is not None
                            else profile["release_name"]
                        ),
                        "source_commit": (
                            overlay_identity["source_commit"]
                            if overlay_identity is not None
                            else profile["source_commit"]
                        ),
                        "describe_manifest_digest": described.manifest_digest,
                        "release_manifest_sha256": expected_release_manifest_sha256,
                        "capability_shape_sha256": runtime_capability_shape_sha256(
                            described.capabilities
                        ),
                        "overlay": overlay_identity,
                    },
                    "hot_sample_count_per_product": args.samples,
                    "cold_definition": "first product-specific request after Runtime admission",
                    "hot_definition": (
                        "subsequent request with admitted server and warm filesystem cache"
                    ),
                    "first_paint_note": (
                        "first_renderable_response_ms is the backend boundary; browser "
                        "layout/paint "
                        "requires user-test instrumentation"
                    ),
                    "products": {},
                }
                for product, (path, payload, schema_version) in _cases(
                    profile_version_id
                ).items():
                    if product not in cases_filter:
                        continue
                    try:
                        cold = await _sample(
                            client,
                            headers,
                            path,
                            payload,
                            schema_version,
                        )
                        cold_result: dict[str, object] = {
                            key: round(value, 3) for key, value in cold.items()
                        }
                    except RuntimeError as error:
                        cold_result = {"error": str(error)}
                    hot: list[dict[str, float]] = []
                    hot_errors: list[str] = []
                    for _ in range(args.samples):
                        try:
                            hot.append(
                                await _sample(
                                    client,
                                    headers,
                                    path,
                                    payload,
                                    schema_version,
                                )
                            )
                        except RuntimeError as error:
                            hot_errors.append(str(error))
                    result["products"][product] = {
                        "cold_ms": cold_result,
                        "hot_attempt_count": args.samples,
                        "hot_success_count": len(hot),
                        "hot_error_count": len(hot_errors),
                        "hot_errors": sorted(set(hot_errors)),
                        "hot_ms": (
                            {
                                key: _distribution([sample[key] for sample in hot])
                                for key in hot[0]
                            }
                            if hot
                            else {}
                        ),
                    }
                return result
        finally:
            await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--runtime-python", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--overlay-bazi-calc",
        type=Path,
        help="QA-locked bazi_calc.py absorbed byte-for-byte into the candidate Runtime",
    )
    parser.add_argument(
        "--products",
        nargs="+",
        default=["bazi", "ziwei", "liuyao", "meihua", "daliuren"],
        choices=["bazi", "ziwei", "liuyao", "meihua", "daliuren"],
    )
    parser.add_argument(
        "--skip-admission",
        action="store_true",
        help="diagnostic only: describe candidate without the Backend admission gate",
    )
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    serialized = json.dumps(asyncio.run(benchmark(args)), ensure_ascii=False, indent=2)
    if args.output is None:
        print(serialized)
    else:
        args.output.write_text(f"{serialized}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
