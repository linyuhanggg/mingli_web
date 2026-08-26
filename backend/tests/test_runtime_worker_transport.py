from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
from app.adapters.runtime import (
    FakeMingliRuntimeAdapter,
    RuntimeReleaseInventory,
    RuntimeStartupError,
    RuntimeStartupGate,
    WorkerV1MingliRuntimeAdapter,
    generic_runtime_stopped,
    one_shot_spawn_argv,
    runtime_capability_shape_sha256,
)
from app.readings.capability_policy import V51_RELEASE_CAPABILITY_IDS
from app.readings.runtime_contracts import Describe, Described, Prepare, Prepared, Stopped
from mingli_paths import MINGLI_CORE_ROOT

WORKER_RELATIVE = "scripts/reading_engine/runtime_worker.py"
WORKER_STOPPED_COPY = "本次处理未完成，请稍后重试。"

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PYTHON = Path(
    os.environ.get(
        "MINGLI_RUNTIME_TEST_PYTHON",
        str(Path.home() / ".local/share/mingli-master/venv/bin/python"),
    )
)
RUNTIME_PYTHON_AVAILABLE = RUNTIME_PYTHON.is_file()
LISTING_SHA256 = "a" * 64
INTEGRITY_SHA256 = "b" * 64

_FAKE_WORKER = r"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_BEHAVIOR_PATH = ROOT / "behavior"
BEHAVIOR = _BEHAVIOR_PATH.read_text(encoding="utf-8").strip() if _BEHAVIOR_PATH.exists() else "ok"
LOG = ROOT / "commands.log"
BOOT = ROOT / "boot.count"


def _count_boot() -> None:
    current = int(BOOT.read_text()) if BOOT.exists() else 0
    BOOT.write_text(str(current + 1), encoding="utf-8")


def _read_frame() -> dict[str, object]:
    header = sys.stdin.buffer.read(4)
    if len(header) != 4:
        raise SystemExit(2)
    length = int.from_bytes(header, "big")
    body = sys.stdin.buffer.read(length)
    if len(body) != length:
        raise SystemExit(2)
    return json.loads(body.decode("utf-8"))


def _write_frame(payload: object) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    body = rendered.encode("utf-8")
    sys.stdout.buffer.write(len(body).to_bytes(4, "big") + body)
    sys.stdout.buffer.flush()


def _argv_value(flag: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1]


def _ready() -> dict[str, object]:
    return {
        "type": "ready",
        "protocol": "mingli-runtime-worker-v1",
        "runtime_protocol": "mingli-portable-interface-v2",
        "identity_sha256": "c" * 64,
        "listing_sha256": _argv_value("--expected-listing-sha256"),
        "runtime_integrity_sha256": _argv_value("--expected-runtime-integrity-sha256"),
        "single_in_flight": True,
        "replay_policy": "forbidden",
        "fallback_policy": "forbidden",
        "max_frame_bytes": 4 * 1024 * 1024,
        "sequence_start": 1,
        "pid": os.getpid(),
        "boot_nonce": "d" * 64,
    }


def _described_result(command: dict[str, object]) -> dict[str, object]:
    return {
        "type": "result",
        "protocol": "mingli-runtime-worker-v1",
        "identity_sha256": command["identity_sha256"],
        "request_id": command["request_id"],
        "sequence": command["sequence"],
        "worker_action": "continue",
        "result": {
            "kind": "described",
            "protocol_version": "mingli-portable-interface-v2",
            "manifest_digest": "0" * 64,
            "capabilities": [],
        },
    }


_count_boot()
if BEHAVIOR == "sleep-ready":
    time.sleep(5)
if BEHAVIOR == "malformed":
    sys.stdout.buffer.write(b"not-a-frame")
    sys.stdout.buffer.flush()
    time.sleep(1)
    raise SystemExit(0)
if BEHAVIOR == "truncate":
    sys.stdout.buffer.write((20).to_bytes(4, "big") + b"{")
    sys.stdout.buffer.flush()
    time.sleep(1)
    raise SystemExit(0)
if BEHAVIOR == "duplicate-key":
    body = b'{"type":"ready","type":"other"}'
    sys.stdout.buffer.write(len(body).to_bytes(4, "big") + body)
    sys.stdout.buffer.flush()
    time.sleep(1)
    raise SystemExit(0)
if BEHAVIOR == "wrong-identity":
    ready = _ready()
    ready["listing_sha256"] = "e" * 64
    _write_frame(ready)
    time.sleep(1)
    raise SystemExit(0)

_write_frame(_ready())
if BEHAVIOR == "ready-extra-stdout":
    sys.stdout.buffer.write(b"EXTRA")
    sys.stdout.buffer.flush()
    time.sleep(1)
    raise SystemExit(0)

command = _read_frame()
LOG.write_text(json.dumps(command) + "\n", encoding="utf-8")
if BEHAVIOR == "crash-after-read":
    os._exit(9)
if BEHAVIOR == "sleep":
    time.sleep(5)
if BEHAVIOR == "two-results":
    _write_frame(_described_result(command))
    _write_frame(_described_result(command))
    time.sleep(1)
    raise SystemExit(0)
if BEHAVIOR == "result-extra-stdout":
    _write_frame(_described_result(command))
    sys.stdout.buffer.write(b"SECOND")
    sys.stdout.buffer.flush()
    time.sleep(1)
    raise SystemExit(0)
if BEHAVIOR == "result-extra-stderr":
    _write_frame(_described_result(command))
    sys.stderr.write("second-channel\n")
    sys.stderr.flush()
    time.sleep(1)
    raise SystemExit(0)
if BEHAVIOR == "isolate":
    payload = _described_result(command)
    payload["worker_action"] = "isolate"
    payload["result"] = {
        "kind": "stopped",
        "reason": "error",
        "public_copy": "本次处理未完成，请稍后重试。",
        "state_token": None,
        "input_request": None,
    }
    _write_frame(payload)
    raise SystemExit(70)
if BEHAVIOR == "invalid-result":
    payload = _described_result(command)
    payload["result"] = {"kind": "unknown"}
    _write_frame(payload)
    time.sleep(1)
    raise SystemExit(0)

_write_frame(_described_result(command))
while True:
    header = sys.stdin.buffer.read(4)
    if len(header) != 4:
        raise SystemExit(0)
    length = int.from_bytes(header, "big")
    body = sys.stdin.buffer.read(length)
    command = json.loads(body.decode("utf-8"))
    LOG.write_text(json.dumps(command) + "\n", encoding="utf-8")
    _write_frame(_described_result(command))
"""


_BIRTH_FACTS = {
    "birth_datetime": "1994-04-30T05:55:00",
    "timezone": "Asia/Shanghai",
    "location": "福建省福州市",
    "gender": "female",
    "time_basis_policy": "civil",
    "zi_hour_policy": "midnight",
    "longitude": 119.3,
    "latitude": 26.08,
    "coordinate_source": "declared",
}
_EVENT_FACTS = {
    "event_datetime": "2026-08-03T09:00:00+08:00",
    "timezone": "Asia/Shanghai",
    "location": "上海",
    "time_basis_policy": "civil",
    "longitude": 121.4737,
    "latitude": 31.2304,
    "coordinate_source": "declared",
}
_PRODUCT_CASES = {
    "bazi": (
        "natal",
        "life",
        {
            "birth_datetime_or_four_pillars": _BIRTH_FACTS["birth_datetime"],
            "timezone": _BIRTH_FACTS["timezone"],
            "location": _BIRTH_FACTS["location"],
            "gender": _BIRTH_FACTS["gender"],
            "time_basis_policy": _BIRTH_FACTS["time_basis_policy"],
        },
    ),
    "ziwei": ("natal", "life", _BIRTH_FACTS),
    "liuyao": (
        "concrete_event",
        "instant",
        {"cast": [6, 7, 8, 9, 7, 8], **_EVENT_FACTS},
    ),
    "meihua": (
        "concrete_event",
        "instant",
        {"casting_method": "time", **_EVENT_FACTS},
    ),
    "liuren": (
        "concrete_event",
        "instant",
        {
            "event_datetime_or_reference_datetime": _EVENT_FACTS["event_datetime"],
            **_EVENT_FACTS,
        },
    ),
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _prepare(product_id: str, *, suffix: str = "") -> Prepare:
    object_id, horizon_id, facts = _PRODUCT_CASES[product_id]
    return Prepare(
        query=f"测试 {product_id}{suffix}",
        intent={
            "subject_refs": ["subject:client"],
            "object_id": object_id,
            "dimension_ids": [],
            "horizon": {"kind_id": horizon_id, "start": None, "end": None},
            "capability_id": product_id,
            "comparisons": [],
        },
        facts={"subject:client": facts},
    )


def _write_fake_worker(release_root: Path, *, behavior: str = "ok") -> Path:
    worker = release_root / WORKER_RELATIVE
    worker.parent.mkdir(parents=True, exist_ok=True)
    worker.write_text(_FAKE_WORKER, encoding="utf-8")
    worker.chmod(0o644)
    (worker.parent / "behavior").write_text(behavior, encoding="utf-8")
    return worker


def _state_root(tmp_path: Path) -> Path:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    state.chmod(0o700)
    return state


def _adapter(
    tmp_path: Path,
    *,
    behavior: str = "ok",
    **overrides: Any,
) -> WorkerV1MingliRuntimeAdapter:
    release_root = tmp_path / "release"
    _write_fake_worker(release_root, behavior=behavior)
    options: dict[str, Any] = {
        "release_root": release_root,
        "runtime_python_path": Path(sys.executable),
        "state_root": _state_root(tmp_path),
        "expected_listing_sha256": LISTING_SHA256,
        "expected_runtime_integrity_sha256": INTEGRITY_SHA256,
        "ready_timeout_seconds": 2.0,
        "request_timeout_seconds": 0.4,
    }
    options.update(overrides)
    return WorkerV1MingliRuntimeAdapter(**options)


def test_generic_stopped_is_opaque() -> None:
    stopped = generic_runtime_stopped()
    assert stopped.reason == "error"
    assert stopped.public_copy == WORKER_STOPPED_COPY
    assert stopped.state_token is None


async def test_worker_start_binds_ready_and_execute_is_single_result(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    ready = await adapter.start()
    assert ready["protocol"] == "mingli-runtime-worker-v1"
    assert ready["listing_sha256"] == LISTING_SHA256
    assert ready["single_in_flight"] is True
    assert " $( " not in " ".join(adapter.spawn_argv())
    result = await adapter.execute(Describe())
    assert isinstance(result, Described)
    command_log = (tmp_path / "release" / WORKER_RELATIVE).parent / "commands.log"
    log = json.loads(command_log.read_text())
    assert log["sequence"] == 1
    assert log["request_id"]
    await adapter.close()


async def test_worker_does_not_fallback_or_replay_after_a_written_crash(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path, behavior="crash-after-read")
    await adapter.start()
    first = await adapter.execute(Describe())
    assert isinstance(first, Stopped)
    assert first.public_copy == WORKER_STOPPED_COPY
    assert adapter.isolated is True
    boot = tmp_path / "release" / WORKER_RELATIVE
    assert boot.parent.joinpath("boot.count").read_text() == "1"
    second = await adapter.execute(Describe())
    assert isinstance(second, Stopped)
    assert boot.parent.joinpath("boot.count").read_text() == "1"
    with pytest.raises(RuntimeStartupError, match="isolated"):
        await adapter.start()


@pytest.mark.parametrize(
    "behavior",
    (
        "malformed",
        "truncate",
        "duplicate-key",
        "wrong-identity",
        "ready-extra-stdout",
    ),
)
async def test_worker_ready_failures_isolate_without_ready(tmp_path: Path, behavior: str) -> None:
    adapter = _adapter(tmp_path, behavior=behavior, ready_timeout_seconds=0.8)
    with pytest.raises(RuntimeStartupError):
        await adapter.start()
    assert adapter.isolated is True
    assert adapter.ready is None
    result = await adapter.execute(Describe())
    assert isinstance(result, Stopped)
    assert result.public_copy == WORKER_STOPPED_COPY


@pytest.mark.parametrize(
    "behavior",
    (
        "two-results",
        "result-extra-stdout",
        "result-extra-stderr",
        "isolate",
        "invalid-result",
        "sleep",
        "crash-after-read",
    ),
)
async def test_worker_request_faults_return_generic_stopped(tmp_path: Path, behavior: str) -> None:
    adapter = _adapter(tmp_path, behavior=behavior, request_timeout_seconds=0.3)
    await adapter.start()
    result = await adapter.execute(Describe())
    assert isinstance(result, Stopped)
    assert result.reason == "error"
    assert result.public_copy == WORKER_STOPPED_COPY
    assert result.state_token is None
    assert adapter.isolated is True
    await adapter.close()


async def test_worker_startup_timeout_is_independent_of_request_timeout(tmp_path: Path) -> None:
    adapter = _adapter(
        tmp_path,
        behavior="sleep-ready",
        ready_timeout_seconds=0.2,
        request_timeout_seconds=2.0,
    )
    started = asyncio.get_running_loop().time()
    with pytest.raises(RuntimeStartupError, match="READY timed out"):
        await adapter.start()
    elapsed = asyncio.get_running_loop().time() - started
    assert elapsed < 1.0


async def test_startup_gate_starts_worker_before_describe() -> None:
    started: list[str] = []
    fake = FakeMingliRuntimeAdapter()
    description = await fake.execute(Describe())
    assert isinstance(description, Described)
    capability_ids = tuple(str(item["id"]) for item in description.capabilities)

    class _Worker:
        adapter_kind = "runtime-worker-v1"

        async def start(self) -> dict[str, object]:
            started.append("start")
            return {"type": "ready"}

        async def execute(self, command: object) -> Described:
            started.append(type(command).__name__)
            return description

    class _Inspector:
        def inspect(self) -> RuntimeReleaseInventory:
            return RuntimeReleaseInventory(
                release_manifest_sha256="e" * 64,
                release_file_count=217,
                provider_ids=capability_ids,
                ready_provider_ids=capability_ids,
                reference_pack_count=55,
                evidence_record_count=1328,
                runtime_closure_file_count=217,
            )

    gate = RuntimeStartupGate(
        runtime=_Worker(),  # type: ignore[arg-type]
        release_inspector=_Inspector(),  # type: ignore[arg-type]
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(
            description.capabilities
        ),
        expected_capability_ids=capability_ids,
    )
    admitted = await gate.startup()
    assert admitted == description
    assert started == ["start", "Describe"]
    assert capability_ids == V51_RELEASE_CAPABILITY_IDS


def _release_paths(core_root: Path) -> list[str]:
    closure_path = core_root / "release/runtime-closure-v1.json"
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    tracked = subprocess.run(
        ["git", "-C", str(core_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    candidates = {item.decode("utf-8") for item in tracked if item} | {WORKER_RELATIVE}
    selected = set(closure["files"])
    for pattern in closure["patterns"]:
        matches = {
            relative
            for relative in candidates
            if PurePosixPath(relative).match(pattern)
        }
        assert matches, pattern
        selected.update(matches)
    assert WORKER_RELATIVE in selected
    return sorted(selected)


def _materialize_release(destination: Path, core_root: Path) -> str:
    destination.mkdir(mode=0o755)
    files: dict[str, str] = {}
    modes: dict[str, int] = {}
    for relative in _release_paths(core_root):
        source = core_root / relative
        assert source.is_file(), relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        target.parent.chmod(0o755)
        shutil.copyfile(source, target)
        mode = 0o755 if os.access(source, os.X_OK) else 0o644
        target.chmod(mode)
        files[relative] = _sha256(target.read_bytes())
        modes[relative] = mode
    source_commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = {
        "schema_version": 3,
        "release": "mingli-master-portable-core",
        "source_commit": source_commit,
        "files": files,
        "modes": modes,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    manifest_path = destination / ".mingli-release-manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    manifest_path.chmod(0o600)
    return _sha256(manifest_bytes)


def _clone_runtime(destination: Path) -> tuple[Path, str]:
    source_root = RUNTIME_PYTHON.resolve().parents[1]
    shutil.copytree(
        source_root,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    python = destination / "bin/python"
    assert python.is_file()
    integrity = _sha256((destination / "runtime-integrity.json").read_bytes())
    return python, integrity


@pytest.mark.skipif(not RUNTIME_PYTHON_AVAILABLE, reason="pinned Runtime Python is missing")
@pytest.mark.skipif(
    not (MINGLI_CORE_ROOT / WORKER_RELATIVE).is_file(),
    reason="worker is not in Core overlay",
)
async def test_real_worker_ready_five_products_and_one_shot_shell_100644(
    tmp_path: Path,
) -> None:
    from app.charts.projectors import project_runtime_view_model

    release_root = tmp_path / "release"
    listing = _materialize_release(release_root, MINGLI_CORE_ROOT)
    python, integrity = _clone_runtime(tmp_path / "runtime")
    state_root = _state_root(tmp_path)
    adapter = WorkerV1MingliRuntimeAdapter(
        release_root=release_root,
        runtime_python_path=python,
        state_root=state_root,
        expected_listing_sha256=listing,
        expected_runtime_integrity_sha256=integrity,
        ready_timeout_seconds=15.0,
        request_timeout_seconds=2.0,
    )
    ready = await adapter.start()
    assert ready["listing_sha256"] == listing
    assert ready["runtime_integrity_sha256"] == integrity
    assert ready["single_in_flight"] is True
    assert ready["replay_policy"] == "forbidden"
    assert len(ready["capability_ids"]) == 14

    products = ("ziwei", "bazi", "liuren", "meihua", "liuyao")
    worker_results: dict[str, dict[str, object]] = {}
    for product_id in products:
        result = await adapter.execute(_prepare(product_id, suffix=f"-{product_id}"))
        assert isinstance(result, Prepared), (product_id, result)
        worker_results[product_id] = result.to_dict()
        view_model = project_runtime_view_model(result.brief.to_dict(), product_id=product_id)
        assert view_model is not None

    shell = release_root / "scripts" / "run_reading_transaction.sh"
    assert stat.S_IMODE(shell.stat().st_mode) == 0o644
    assert one_shot_spawn_argv(shell) == ("/bin/sh", str(shell))
    chmod_before = stat.S_IMODE(shell.stat().st_mode)
    for product_id, worker_payload in worker_results.items():
        one_shot_state = tmp_path / f"one-shot-{product_id}"
        one_shot_state.mkdir(mode=0o700)
        environment = {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_PYTHON": str(python),
            "MINGLI_STORE_ROOT": str(one_shot_state),
            "PATH": "/opt/node/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": "/dev/null",
            "TZ": "UTC",
        }
        payload = json.dumps(_prepare(product_id, suffix=f"-{product_id}").to_dict()) + "\n"
        process = await asyncio.create_subprocess_exec(
            "/bin/sh",
            str(shell),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(payload.encode("utf-8")),
            timeout=8,
        )
        assert process.returncode == 0, stderr
        one_shot_payload = json.loads(stdout.decode("utf-8"))
        worker_normalized = json.loads(json.dumps(worker_payload))
        one_shot_normalized = json.loads(json.dumps(one_shot_payload))
        worker_normalized["state_token"] = "<state-token>"
        one_shot_normalized["state_token"] = "<state-token>"
        assert worker_normalized == one_shot_normalized
        view = project_runtime_view_model(worker_payload["brief"], product_id=product_id)
        assert view is not None
    assert stat.S_IMODE(shell.stat().st_mode) == chmod_before == 0o644
    await adapter.close()


@pytest.mark.skipif(not RUNTIME_PYTHON_AVAILABLE, reason="pinned Runtime Python is missing")
@pytest.mark.skipif(
    not (MINGLI_CORE_ROOT / WORKER_RELATIVE).is_file(),
    reason="worker is not in Core overlay",
)
async def test_real_worker_release_drift_returns_generic_stopped(tmp_path: Path) -> None:
    release_root = tmp_path / "release"
    listing = _materialize_release(release_root, MINGLI_CORE_ROOT)
    python, integrity = _clone_runtime(tmp_path / "runtime")
    adapter = WorkerV1MingliRuntimeAdapter(
        release_root=release_root,
        runtime_python_path=python,
        state_root=_state_root(tmp_path),
        expected_listing_sha256=listing,
        expected_runtime_integrity_sha256=integrity,
        ready_timeout_seconds=15.0,
        request_timeout_seconds=2.0,
    )
    await adapter.start()
    (release_root / WORKER_RELATIVE).write_bytes(
        (release_root / WORKER_RELATIVE).read_bytes() + b"\n"
    )
    result = await adapter.execute(Describe())
    assert isinstance(result, Stopped)
    assert result.public_copy == WORKER_STOPPED_COPY
    assert adapter.isolated is True
    await adapter.close()
