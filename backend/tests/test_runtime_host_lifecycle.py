from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from app.adapters.runtime import (
    RUNTIME_TURN_AUDIT_NAME,
    RuntimeStartupError,
    RuntimeTurnAudit,
    WorkerV2MingliRuntimeAdapter,
    failure_for_transport_fault,
    host_runtime_state_root,
    runtime_command_digest,
)
from app.charts.projectors import project_runtime_view_model
from app.main import create_app
from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion
from app.readings.runtime_contracts import Describe, Prepared, RuntimeFailure, Stopped
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

# isort: split
from test_profiles_api import create_confirmed_profile, create_guest
from test_readings_api import seed_runtime_release
from test_runtime_worker_transport import (
    WORKER_STOPPED_COPY,
    _adapter,
    _prepare,
)

V51_RELEASE = Path("/private/tmp/ming21-targeting-main-qa.ExVuOW/runtime/v51-release")
V51_PYTHON = Path("/private/tmp/ming21-targeting-main-qa.ExVuOW/runtime/v51-venv/bin/python")
V51_INTEGRITY = Path(
    "/private/tmp/ming21-targeting-main-qa.ExVuOW/runtime/v51-venv/runtime-integrity.json"
)
V51_LISTING = "93433f7fa9a9bef1115216240767c2c8e12e4ad9f0807124d05a47ddd0701f5d"
V51_AVAILABLE = (
    V51_RELEASE.is_dir()
    and V51_PYTHON.is_file()
    and V51_INTEGRITY.is_file()
    and hashlib.sha256(
        (V51_RELEASE / "scripts/reading_engine/runtime_worker.py").read_bytes()
    ).hexdigest()
    == "b8d05ca1a4d6392598442e8fed80d73a2ce079b757c2d6bc059f5ff13b629e3e"
)
V51_INTEGRITY_SHA256 = (
    hashlib.sha256(V51_INTEGRITY.read_bytes()).hexdigest() if V51_AVAILABLE else ""
)


def _state(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


class InjectedStoppedRuntime:
    adapter_kind = "test-injected-stopped-runtime"

    def __init__(self) -> None:
        self._transport_fault = "injected-transport-fault"
        self.last_turn: RuntimeTurnAudit | None = None

    async def execute(self, command: object) -> Stopped:
        del command
        return Stopped(
            reason="error",
            public_copy=WORKER_STOPPED_COPY,
            failure=RuntimeFailure(
                code="transient.timeout",
                category="transient",
                retryable=True,
            ),
        )


def test_command_digest_redacts_facts_and_query() -> None:
    command = _prepare("ziwei")
    digest = runtime_command_digest(command)
    payload = json.dumps(command.to_dict())
    assert len(digest) == 64
    assert digest != hashlib.sha256(payload.encode()).hexdigest()
    assert "1994" not in digest
    assert "北京市" not in digest
    assert runtime_command_digest(command) == digest
    assert runtime_command_digest(_prepare("bazi")) != digest


def test_host_owners_use_distinct_state_namespaces(tmp_path: Path) -> None:
    configured = _state(tmp_path / "state")
    api = host_runtime_state_root(configured, "chart-api")
    job = host_runtime_state_root(configured, "job-worker")
    assert api == configured / "host-chart-api"
    assert job == configured / "host-job-worker"
    assert api != job
    with pytest.raises(ValueError, match="not admitted"):
        host_runtime_state_root(configured, "shared")


async def test_second_worker_cannot_own_the_same_state_root(tmp_path: Path) -> None:
    first = _adapter(tmp_path)
    second = WorkerV2MingliRuntimeAdapter(
        release_root=tmp_path / "release",
        runtime_python_path=Path(sys.executable),
        state_root=first._state_root,
        expected_listing_sha256="a" * 64,
        expected_runtime_integrity_sha256="b" * 64,
        ready_timeout_seconds=2.0,
        request_timeout_seconds=0.4,
    )
    await first.start()
    with pytest.raises(RuntimeStartupError, match="already owned"):
        await second.start()
    await first.close()
    await second.start()
    await second.close()


async def test_timeout_turn_audit_keeps_typed_failure_and_transport_fault(
    tmp_path: Path,
) -> None:
    adapter = _adapter(tmp_path, behavior="sleep", request_timeout_seconds=0.2)
    await adapter.start()
    result = await adapter.execute(Describe())
    assert isinstance(result, Stopped)
    assert result.failure == failure_for_transport_fault("timeout")
    audit = adapter.last_turn
    assert audit is not None
    assert audit.command_kind == "describe"
    assert audit.result_kind == "stopped"
    assert audit.transport_fault == "timeout"
    assert audit.sequence == 1
    assert audit.worker_pid is not None
    assert audit.failure == {
        "schema_version": "mingli-runtime-failure/v1",
        "code": "transient.timeout",
        "category": "transient",
        "retryable": True,
    }
    lines = (adapter._state_root / RUNTIME_TURN_AUDIT_NAME).read_text(
        encoding="utf-8"
    ).splitlines()
    payload = json.loads(lines[-1])
    assert payload["transport_fault"] == "timeout"
    assert payload["failure"]["code"] == "transient.timeout"
    assert payload["failure"]["schema_version"] == "mingli-runtime-failure/v1"
    assert payload["failure"]["category"] == "transient"
    assert payload["failure"]["retryable"] is True
    await adapter.close()


async def test_chart_fast_path_rollback_keeps_typed_failure_audit(
    database: Any,
    test_settings: Any,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path / "state")
    settings = test_settings.model_copy(
        update={"reading_write_rate_limit": 100, "runtime_state_root": state}
    )
    runtime = InjectedStoppedRuntime()
    application = create_app(
        settings=settings,
        database=database,
        chart_runtime=runtime,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        headers = await create_guest(client)
        profile = await create_confirmed_profile(client, headers)
        await seed_runtime_release(database, settings)
        response = await client.post(
            "/api/v1/readings/ziwei",
            headers={**headers, "Idempotency-Key": "ziwei-audit-not-swallowed"},
            json={
                "profile_version_id": profile["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )

    assert response.status_code == 503, response.text
    assert response.json()["code"] == "chart_runtime_error"
    assert response.json()["detail"] == WORKER_STOPPED_COPY
    audit = runtime.last_turn
    assert audit is not None
    assert audit.result_kind == "stopped"
    assert audit.transport_fault == "injected-transport-fault"
    assert audit.failure == {
        "schema_version": "mingli-runtime-failure/v1",
        "code": "transient.timeout",
        "category": "transient",
        "retryable": True,
    }
    payload = json.loads(
        (state / RUNTIME_TURN_AUDIT_NAME).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert payload["transport_fault"] == "injected-transport-fault"
    assert set(payload["failure"]) == {
        "schema_version",
        "category",
        "code",
        "retryable",
    }
    async with database.sessions() as session:
        counts = {
            "roots": int(await session.scalar(select(func.count()).select_from(ReadingRoot)) or 0),
            "versions": int(
                await session.scalar(select(func.count()).select_from(ReadingVersion)) or 0
            ),
            "jobs": int(
                await session.scalar(select(func.count()).select_from(ReadingJobRecord)) or 0
            ),
        }
    assert counts == {"roots": 0, "versions": 0, "jobs": 0}


@pytest.mark.skipif(not V51_AVAILABLE, reason="admitted v51 worker artifact is missing")
async def test_exclusive_and_namespaced_v51_ziwei_are_prepared_with_twelve_palaces(
    tmp_path: Path,
) -> None:
    command = _prepare("ziwei")

    async def _run(state: Path) -> Prepared:
        adapter = WorkerV2MingliRuntimeAdapter(
            release_root=V51_RELEASE,
            runtime_python_path=V51_PYTHON,
            state_root=state,
            expected_listing_sha256=V51_LISTING,
            expected_runtime_integrity_sha256=V51_INTEGRITY_SHA256,
            ready_timeout_seconds=15.0,
            request_timeout_seconds=2.0,
        )
        await adapter.start()
        try:
            result = await adapter.execute(command)
        finally:
            await adapter.close()
        assert isinstance(result, Prepared), adapter.last_turn
        return result

    exclusive = await _run(_state(tmp_path / "exclusive"))
    configured = _state(tmp_path / "shared-parent")
    api = await _run(host_runtime_state_root(configured, "chart-api"))
    job = await _run(host_runtime_state_root(configured, "job-worker"))
    for result in (exclusive, api, job):
        view = project_runtime_view_model(result.brief.to_dict(), product_id="ziwei")
        assert view is not None
        assert view.schema_version == "ziwei-chart/v1"
        assert len(view.palaces) == 12
