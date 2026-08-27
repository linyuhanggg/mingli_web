from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from app.adapters.runtime import (
    RUNTIME_TURN_AUDIT_NAME,
    RuntimeTurnAudit,
    WorkerV2MingliRuntimeAdapter,
    failure_for_transport_fault,
    runtime_command_digest,
)
from app.charts.projectors import project_runtime_view_model
from app.main import create_app
from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion
from app.readings.runtime_contracts import (
    Describe,
    Described,
    Prepared,
    RuntimeFailure,
    Stopped,
)
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

    def __init__(self, failure: RuntimeFailure | None = None) -> None:
        self._transport_fault = "injected-transport-fault"
        self.last_turn: RuntimeTurnAudit | None = None
        self._failure = failure or RuntimeFailure(
            code="transient.timeout",
            category="transient",
            retryable=True,
        )

    async def execute(self, command: object) -> Stopped:
        del command
        return Stopped(
            reason="error",
            public_copy=WORKER_STOPPED_COPY,
            failure=self._failure,
        )


def test_command_digest_redacts_facts_and_query() -> None:
    command = _prepare("ziwei")
    digest = runtime_command_digest(command)
    payload = json.dumps(command.to_dict())
    assert len(digest) == 64
    assert digest != hashlib.sha256(payload.encode()).hexdigest()
    assert "1994" not in digest
    assert "福州" not in digest
    assert "测试" not in digest
    assert runtime_command_digest(command) == digest
    assert runtime_command_digest(_prepare("bazi")) != digest


async def test_two_workers_share_the_same_state_root_without_host_lock(
    tmp_path: Path,
) -> None:
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
    await second.start()
    first_result = await first.execute(Describe())
    second_result = await second.execute(Describe())
    assert isinstance(first_result, Described)
    assert isinstance(second_result, Described)
    assert first.last_turn is not None
    assert second.last_turn is not None
    assert first.last_turn.result_kind == "described"
    assert second.last_turn.result_kind == "described"
    assert first.last_turn.transport_fault is None
    assert second.last_turn.transport_fault is None
    await first.close()
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
    assert "1994" not in json.dumps(payload, ensure_ascii=False)
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
async def test_local_dual_v51_workers_on_same_store_are_both_prepared(
    tmp_path: Path,
) -> None:
    command = _prepare("ziwei")
    shared = _state(tmp_path / "shared")

    async def _run(adapter: WorkerV2MingliRuntimeAdapter) -> Prepared:
        result = await adapter.execute(command)
        assert isinstance(result, Prepared), adapter.last_turn
        assert adapter.last_turn is not None
        assert adapter.last_turn.result_kind == "prepared"
        assert adapter.last_turn.transport_fault is None
        return result

    exclusive_adapter = WorkerV2MingliRuntimeAdapter(
        release_root=V51_RELEASE,
        runtime_python_path=V51_PYTHON,
        state_root=_state(tmp_path / "exclusive"),
        expected_listing_sha256=V51_LISTING,
        expected_runtime_integrity_sha256=V51_INTEGRITY_SHA256,
        ready_timeout_seconds=15.0,
        request_timeout_seconds=2.0,
    )
    first = WorkerV2MingliRuntimeAdapter(
        release_root=V51_RELEASE,
        runtime_python_path=V51_PYTHON,
        state_root=shared,
        expected_listing_sha256=V51_LISTING,
        expected_runtime_integrity_sha256=V51_INTEGRITY_SHA256,
        ready_timeout_seconds=15.0,
        request_timeout_seconds=2.0,
    )
    second = WorkerV2MingliRuntimeAdapter(
        release_root=V51_RELEASE,
        runtime_python_path=V51_PYTHON,
        state_root=shared,
        expected_listing_sha256=V51_LISTING,
        expected_runtime_integrity_sha256=V51_INTEGRITY_SHA256,
        ready_timeout_seconds=15.0,
        request_timeout_seconds=2.0,
    )
    await exclusive_adapter.start()
    try:
        exclusive = await _run(exclusive_adapter)
    finally:
        await exclusive_adapter.close()

    await first.start()
    await second.start()
    try:
        api_side = await _run(first)
        job_side = await _run(second)
    finally:
        await first.close()
        await second.close()

    for result in (exclusive, api_side, job_side):
        view = project_runtime_view_model(result.brief.to_dict(), product_id="ziwei")
        assert view is not None
        assert view.schema_version == "ziwei-chart/v1"
        assert len(view.palaces) == 12


DURABLE_CORE_SOURCE = "21ed7cda2464279102270abf31bb8246b1f655a2"
DURABLE_CORE_PARENT = "adfd7b6bf1c6a5e6df184bdd792bbf4956b009e1"
DURABLE_CORE_TREE = "bf889a009a454a7bf7e6005d76aee10bb52cd446"
DURABLE_CORE_LISTING = "b4395e0047411e5998a53b9c01dfec0c7622fccf85e17484cf85562b6ec29b5d"
DURABLE_CORE_BRANCH = "agent/core/ming-21-failure-fidelity-v2-bf889a0"
DURABLE_CORE_REPO = "https://github.com/linyuhanggg/mingli-master-skill.git"
_V2_PUBLIC_FAILURE = {
    "schema_version": "mingli-runtime-failure/v1",
    "code": "runtime.internal_error",
    "category": "runtime_internal",
    "retryable": False,
}
_V2_AUDIT_FAILURE = {
    **_V2_PUBLIC_FAILURE,
    "schema_version": "mingli-runtime-failure/v2",
    "internal_code": "RuntimeError",
}


async def test_worker_v2_stopped_failure_enters_typed_audit_only(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path, behavior="stopped-v2")
    await adapter.start()
    result = await adapter.execute(Describe())
    assert isinstance(result, Stopped)
    assert result.public_copy == WORKER_STOPPED_COPY
    assert result.failure is not None
    assert result.failure.internal_code == "RuntimeError"
    assert result.failure.to_dict() == _V2_PUBLIC_FAILURE
    assert "internal_code" not in result.to_dict()["failure"]
    audit = adapter.last_turn
    assert audit is not None
    assert audit.isolated is False
    assert audit.transport_fault is None
    assert audit.failure == _V2_AUDIT_FAILURE
    payload = json.loads(
        (adapter._state_root / RUNTIME_TURN_AUDIT_NAME).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert payload["failure"] == _V2_AUDIT_FAILURE
    rendered = json.dumps(result.to_dict(), ensure_ascii=False)
    assert "internal_code" not in rendered
    assert "RuntimeError" not in rendered
    await adapter.close()


async def test_worker_v2_unsafe_internal_code_fail_closes_without_public_leak(
    tmp_path: Path,
) -> None:
    adapter = _adapter(tmp_path, behavior="stopped-v2-unsafe")
    await adapter.start()
    result = await adapter.execute(Describe())
    assert isinstance(result, Stopped)
    assert adapter.isolated is True
    assert result.failure == RuntimeFailure.internal_error()
    assert result.failure is not None
    assert result.failure.internal_code is None
    rendered = json.dumps(result.to_dict(), ensure_ascii=False)
    assert "PRIVATE-PERSON" not in rendered
    assert "/Users/private/runtime" not in rendered
    audit = adapter.last_turn
    assert audit is not None
    assert audit.transport_fault == "result-decode"
    assert audit.failure == RuntimeFailure.internal_error().to_audit_dict()
    await adapter.close()


async def test_chart_fast_path_v2_audit_keeps_internal_code_off_http(
    database: Any,
    test_settings: Any,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path / "state")
    settings = test_settings.model_copy(
        update={"reading_write_rate_limit": 100, "runtime_state_root": state}
    )
    runtime = InjectedStoppedRuntime(
        failure=RuntimeFailure(
            code="runtime.internal_error",
            category="runtime_internal",
            retryable=False,
            schema_version="mingli-runtime-failure/v2",
            internal_code="RuntimeError",
        )
    )
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
            headers={**headers, "Idempotency-Key": "ziwei-v2-audit-redacted"},
            json={
                "profile_version_id": profile["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["code"] == "chart_runtime_error"
    assert body["detail"] == WORKER_STOPPED_COPY
    assert "internal_code" not in json.dumps(body, ensure_ascii=False)
    assert "RuntimeError" not in json.dumps(body, ensure_ascii=False)
    audit = runtime.last_turn
    assert audit is not None
    assert audit.failure == _V2_AUDIT_FAILURE
    payload = json.loads(
        (state / RUNTIME_TURN_AUDIT_NAME).read_text(encoding="utf-8").splitlines()[-1]
    )
    assert payload["failure"] == _V2_AUDIT_FAILURE
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


def _durable_core_checkout(destination: Path) -> Path:
    cached = os.environ.get("MING21_CORE_21ED7CDA")
    if cached:
        source = Path(cached)
        subprocess.run(
            ["git", "clone", "--no-tags", "--local", str(source), str(destination)],
            check=True,
            timeout=60,
        )
    else:
        subprocess.run(
            [
                "git",
                "clone",
                "--no-tags",
                "--single-branch",
                f"--branch={DURABLE_CORE_BRANCH}",
                DURABLE_CORE_REPO,
                str(destination),
            ],
            check=True,
            timeout=120,
        )
    head = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    parent = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD^"],
        text=True,
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD^{tree}"],
        text=True,
    ).strip()
    assert head == DURABLE_CORE_SOURCE
    assert parent == DURABLE_CORE_PARENT
    assert tree == DURABLE_CORE_TREE
    return destination


def _materialize_durable_core_artifact(source: Path, destination: Path) -> str:
    scripts = str(source / "scripts")
    inserted = scripts not in sys.path
    if inserted:
        sys.path.insert(0, scripts)
    previous = sys.modules.pop("release_deploy", None)
    try:
        release_deploy = importlib.import_module("release_deploy")
        files = release_deploy.tracked_release_files(source)
        manifest = release_deploy.build_manifest(source, files, DURABLE_CORE_SOURCE)
        payload = (
            json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        listing = hashlib.sha256(payload).hexdigest()
        assert listing == DURABLE_CORE_LISTING
        destination.mkdir(mode=0o700)
        for relative in manifest["files"]:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
            target.chmod(manifest["modes"][relative])
        manifest_path = destination / ".mingli-release-manifest.json"
        manifest_path.write_bytes(payload)
        manifest_path.chmod(0o600)
        for path in (destination, *destination.rglob("*")):
            if path.is_dir():
                path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o022)
        return listing
    finally:
        sys.modules.pop("release_deploy", None)
        if previous is not None:
            sys.modules["release_deploy"] = previous
        if inserted:
            sys.path.remove(scripts)


async def test_durable_core_stopped_failure_reaches_backend_audit(
    tmp_path: Path,
) -> None:
    from app.readings.runtime_contracts import result_from_dict

    checkout = _durable_core_checkout(tmp_path / "core-src")
    artifact = tmp_path / "release-21ed7cda"
    listing = _materialize_durable_core_artifact(checkout, artifact)
    assert listing == DURABLE_CORE_LISTING
    worker_sha = hashlib.sha256(
        (artifact / "scripts/reading_engine/runtime_worker.py").read_bytes()
    ).hexdigest()
    assert worker_sha == "b8d05ca1a4d6392598442e8fed80d73a2ce079b757c2d6bc059f5ff13b629e3e"
    assert (checkout / "scripts/test_v51_model_selection_fallback.py").is_file()
    assert not (artifact / "scripts/test_v51_model_selection_fallback.py").exists()

    scripts = str(checkout / "scripts")
    inserted = scripts not in sys.path
    if inserted:
        sys.path.insert(0, scripts)
    previous = {
        name: sys.modules.get(name)
        for name in list(sys.modules)
        if name == "reading_engine"
        or name.startswith("reading_engine.")
        or name.startswith("test_v51_")
    }
    for name in previous:
        sys.modules.pop(name, None)
    try:
        fallback = importlib.import_module("test_v51_model_selection_fallback")
        contracts = importlib.import_module("reading_engine.interface_contracts")
        private = (
            "PRIVATE-EXCEPTION-PERSON subject=PRIVATE-SUBJECT /Users/private/runtime"
        )
        fixture = fallback._build_fixture(alpha_raise=private)
        try:
            core_result = fixture.interface().execute(
                contracts.Prepare(
                    query="中性问句",
                    intent=fallback._intent(capability_id="capability.alpha"),
                    facts={"subject:test": {"field.one": "已提供"}},
                )
            )
        finally:
            fixture.cleanup()
    finally:
        for name in list(sys.modules):
            if (
                name == "reading_engine"
                or name.startswith("reading_engine.")
                or name.startswith("test_v51_")
                or name == "release_deploy"
            ):
                sys.modules.pop(name, None)
        for name, module in previous.items():
            if module is not None:
                sys.modules[name] = module
        if inserted:
            sys.path.remove(scripts)

    wire = core_result.to_dict()
    assert wire["failure"]["schema_version"] == "mingli-runtime-failure/v2"
    assert wire["failure"]["internal_code"] == "RuntimeError"
    rendered_core = json.dumps(wire, ensure_ascii=False)
    assert "PRIVATE-EXCEPTION-PERSON" not in rendered_core
    parsed = result_from_dict(wire)
    assert isinstance(parsed, Stopped)
    assert parsed.failure is not None
    assert parsed.failure.to_audit_dict() == _V2_AUDIT_FAILURE
    assert parsed.to_dict()["failure"] == _V2_PUBLIC_FAILURE

    adapter = _adapter(tmp_path / "host")
    await adapter.start()
    adapter._publish_turn(Describe(), parsed)
    audit = adapter.last_turn
    assert audit is not None
    assert audit.result_kind == "stopped"
    assert audit.failure == _V2_AUDIT_FAILURE
    payload = json.loads(
        (adapter._state_root / RUNTIME_TURN_AUDIT_NAME).read_text(encoding="utf-8").splitlines()[-1]
    )
    rendered_audit = json.dumps(payload, ensure_ascii=False)
    assert payload["failure"] == _V2_AUDIT_FAILURE
    assert "PRIVATE-EXCEPTION-PERSON" not in rendered_audit
    assert "internal_code" not in json.dumps(parsed.to_dict(), ensure_ascii=False)
    await adapter.close()
