import hashlib
import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from app.adapters.runtime import (
    FakeMingliRuntimeAdapter,
    FileSystemRuntimeReleaseInspector,
    OneShotMingliRuntimeAdapter,
    RuntimeReleaseInventory,
    RuntimeStartupError,
    RuntimeStartupGate,
    WorkerV2MingliRuntimeAdapter,
    build_runtime_startup_gate,
    runtime_capability_shape_sha256,
)
from app.readings.capability_policy import (
    P0_EXPOSED_CAPABILITY_IDS,
    V51_RELEASE_CAPABILITY_IDS,
    CapabilityNotExposedError,
    require_p0_capability,
)
from app.readings.runtime_contracts import Describe, Described
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError


def _production_settings(**overrides: object):  # type: ignore[no-untyped-def]
    from app.config import Settings

    values: dict[str, object] = {
        "environment": "production",
        "cookie_secure": True,
        "otp_adapter": "disabled",
        "identity_hash_key": "production-identity-key",
        "content_encryption_key_b64": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=",
        "content_encryption_key_id": "production-content-v1",
        "runtime_adapter": "worker-v2",
        "runtime_launcher_path": "/opt/mingli-master/scripts/run_reading_transaction.sh",
        "runtime_python_path": "/opt/mingli-runtime/venv/bin/python",
        "runtime_release_root": "/opt/mingli-master",
        "runtime_state_root": "/var/lib/mingli",
        "runtime_expected_manifest_digest": (
            "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
        ),
        "runtime_expected_capability_shape_sha256": (
            "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
        ),
        "model_adapter": "deepseek",
        "deepseek_api_key": "test-only-obviously-not-a-real-key",
        "model_price_snapshot_version": "fixture-price-v1",
        "model_input_price_microunits_per_million_tokens": 1,
        "model_output_price_microunits_per_million_tokens": 1,
    }
    values.update(overrides)
    return Settings(**values)


class StaticReleaseInspector:
    def __init__(self, inventory: RuntimeReleaseInventory) -> None:
        self.inventory = inventory

    def inspect(self) -> RuntimeReleaseInventory:
        return self.inventory


class FailingReleaseInspector:
    def inspect(self) -> RuntimeReleaseInventory:
        raise RuntimeStartupError("release verification failed")


def _write_executable(path: Path, payload: dict[str, object]) -> Path:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(
        f"""#!{sys.executable}
import sys
assert sys.stdin.read() == '{{"kind":"describe"}}\\n'
sys.stdout.write({encoded!r} + "\\n")
""",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _inventory() -> RuntimeReleaseInventory:
    return RuntimeReleaseInventory(
        release_manifest_sha256="e" * 64,
        release_file_count=218,
        physical_file_count=219,
        provider_ids=V51_RELEASE_CAPABILITY_IDS,
        ready_provider_ids=V51_RELEASE_CAPABILITY_IDS,
        reference_pack_count=55,
        evidence_record_count=1328,
        runtime_closure_file_count=218,
    )


async def _fake_description() -> Described:
    result = await FakeMingliRuntimeAdapter().execute(Describe())
    assert isinstance(result, Described)
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_signed_release_fixture(
    root: Path,
    *,
    source_commit: str = "fixture-commit",
) -> str:
    runtime_root = root / "resources" / "runtime"
    providers_root = runtime_root / "providers"
    providers_root.mkdir(parents=True)
    provider_entries: list[str] = []
    for provider_id in V51_RELEASE_CAPABILITY_IDS:
        relative = f"providers/{provider_id}.json"
        provider_entries.append(relative)
        (runtime_root / relative).write_text(
            json.dumps(
                {
                    "schema_version": "provider-manifest-v1",
                    "id": provider_id,
                    "entrypoint": f"reading_engine.providers:{provider_id}Provider",
                    "runtime_capability": {"system": provider_id},
                    "capability": {},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    (runtime_root / "catalog-v1.json").write_text(
        json.dumps(
            {"schema_version": "catalog-v1", "providers": provider_entries},
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    packs: list[dict[str, object]] = []
    source_paths: list[Path] = []
    for index in range(55):
        system = f"system-{index % 13}"
        slug = f"pack-{index:02d}"
        pack_root = root / "references" / "books" / system / slug
        pack_root.mkdir(parents=True)
        rules = pack_root / "rules.md"
        rules.write_text(f"## RULE-{index:02d}\nfixture rule\n", encoding="utf-8")
        (pack_root / "quote-index.md").write_text(
            f"## QUOTE-{index:02d}\nfixture quote\n",
            encoding="utf-8",
        )
        source_paths.append(rules)
        packs.append(
            {
                "system": system,
                "slug": slug,
                "d2_status": "ready",
                "local_fulltext_required_for_runtime": False,
            }
        )
    reference_catalog = root / "references" / "catalog" / "catalog.json"
    reference_catalog.parent.mkdir(parents=True)
    reference_catalog.write_text(
        json.dumps(
            {
                "ready_count": 55,
                "ready_reference_packs": packs,
                "validation": {
                    "reference_pack_files": "PASS 55/55",
                    "source_provenance_entries": "PASS 55/55",
                    "fulltext_checksums_recorded": "PASS 55/55",
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    evidence_index = root / "references" / "index" / "evidence-rules.jsonl"
    evidence_index.parent.mkdir(parents=True)
    evidence_rows = []
    for index in range(1328):
        pack = packs[index % len(packs)]
        source = source_paths[index % len(source_paths)]
        quote = f"fixture quote {index}"
        evidence_rows.append(
            json.dumps(
                {
                    "schema_version": "mingli-evidence-rule-v1",
                    "record_kind": "substantive_rule",
                    "rule_id": f"rule-{index:04d}",
                    "source_pack": f"{pack['system']}/{pack['slug']}",
                    "source_path": source.relative_to(root).as_posix(),
                    "source_sha256": _sha256(source),
                    "quote": quote,
                    "quote_hash": hashlib.sha256(quote.encode()).hexdigest(),
                    "depends_on_rule_ids": [],
                    "exception_rule_ids": [],
                    "conflict_rule_ids": [],
                },
                sort_keys=True,
            )
        )
    evidence_index.write_text("\n".join(evidence_rows) + "\n", encoding="utf-8")

    existing = [path for path in root.rglob("*") if path.is_file()]
    filler_root = root / "release" / "fixture"
    filler_root.mkdir(parents=True)
    runtime_closure = root / "release" / "runtime-closure-v1.json"
    filler_count = 218 - len(existing) - 1
    assert filler_count >= 0
    for index in range(filler_count):
        (filler_root / f"file-{index:03d}.txt").write_text("fixture", encoding="utf-8")
    release_paths = sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    ) + ["release/runtime-closure-v1.json"]
    runtime_closure.write_text(
        json.dumps(
            {
                "schema_version": "mingli-runtime-closure-v1",
                "files": sorted(release_paths),
                "patterns": [],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    files = {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in root.rglob("*")
        if path.is_file()
    }
    assert len(files) == 218
    manifest = root / ".mingli-release-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "release": "fixture-release",
                "source_commit": source_commit,
                "files": files,
                "modes": {
                    relative: stat.S_IMODE((root / relative).stat().st_mode) for relative in files
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return _sha256(manifest)


def _resign_release_fixture(root: Path, relative: str) -> str:
    manifest_path = root / ".mingli-release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][relative] = _sha256(root / relative)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return _sha256(manifest_path)


async def test_startup_gate_admits_all_thirteen_but_product_policy_exposes_only_p0(
    tmp_path: Path,
) -> None:
    description = await _fake_description()
    launcher = _write_executable(tmp_path / "runtime-fixture", description.to_dict())
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=5,
    )
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=StaticReleaseInspector(_inventory()),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(description.capabilities),
    )

    admitted = await gate.startup()
    await gate.readiness_probe()

    assert admitted == description
    assert tuple(capability["id"] for capability in admitted.capabilities) == (
        V51_RELEASE_CAPABILITY_IDS
    )
    assert P0_EXPOSED_CAPABILITY_IDS == ("bazi", "fortune", "liuyao")
    for capability_id in P0_EXPOSED_CAPABILITY_IDS:
        assert require_p0_capability(capability_id) == capability_id
    for capability_id in set(V51_RELEASE_CAPABILITY_IDS) - set(P0_EXPOSED_CAPABILITY_IDS):
        with pytest.raises(CapabilityNotExposedError):
            require_p0_capability(capability_id)


async def test_startup_gate_rejects_fake_runtime_even_when_its_description_is_complete() -> None:
    description = await _fake_description()
    gate = RuntimeStartupGate(
        runtime=FakeMingliRuntimeAdapter(),
        release_inspector=StaticReleaseInspector(_inventory()),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(description.capabilities),
    )

    with pytest.raises(RuntimeStartupError, match="Fake Runtime"):
        await gate.startup()
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


async def test_startup_gate_verifies_release_before_executing_the_launcher(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "launcher-executed"
    launcher = tmp_path / "runtime-fixture"
    launcher.write_text(
        f"""#!/usr/bin/env python3
from pathlib import Path
Path({str(marker)!r}).write_text('executed')
""",
        encoding="utf-8",
    )
    launcher.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=1,
    )
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=FailingReleaseInspector(),
        expected_manifest_digest="f" * 64,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256="a" * 64,
    )

    with pytest.raises(RuntimeStartupError, match="release verification failed"):
        await gate.startup()

    assert not marker.exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("release_manifest_sha256", "0" * 64, "release manifest digest"),
        ("release_file_count", 216, "release manifest is incomplete"),
        ("physical_file_count", 217, "physical inventory is incomplete"),
        ("provider_ids", V51_RELEASE_CAPABILITY_IDS[:-1], "Provider inventory"),
        ("ready_provider_ids", V51_RELEASE_CAPABILITY_IDS[:-1], "13/13 ready"),
        ("reference_pack_count", 54, "55/55"),
        ("evidence_record_count", 1327, "1328"),
        ("runtime_closure_file_count", 216, "closure is incomplete"),
    ),
)
async def test_startup_gate_rejects_incomplete_release_inventory(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    description = await _fake_description()
    launcher = _write_executable(tmp_path / "runtime-fixture", description.to_dict())
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=1,
    )
    inventory = replace(_inventory(), **{field: value})
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=StaticReleaseInspector(inventory),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(description.capabilities),
    )

    with pytest.raises(RuntimeStartupError, match=message):
        await gate.startup()
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("protocol", "runtime_startup_failed"),
        ("manifest", "manifest digest mismatch"),
        ("provider", "exact 13 Provider"),
        ("shape", "capability shape mismatch"),
    ),
)
async def test_startup_gate_rejects_describe_contract_drift(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    description = await _fake_description()
    payload = description.to_dict()
    if mutation == "protocol":
        payload["protocol_version"] = "mingli-portable-interface-v1"
    elif mutation == "manifest":
        payload["manifest_digest"] = "0" * 64
    elif mutation == "provider":
        payload["capabilities"] = payload["capabilities"][:-1]  # type: ignore[index]
    else:
        capabilities = payload["capabilities"]
        assert isinstance(capabilities, list)
        assert isinstance(capabilities[0], dict)
        capabilities[0]["label"] = "被篡改的能力形状"
    launcher = _write_executable(tmp_path / "runtime-fixture", payload)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=1,
    )
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=StaticReleaseInspector(_inventory()),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(description.capabilities),
    )

    with pytest.raises(RuntimeStartupError, match=message):
        await gate.startup()
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


async def test_startup_gate_closes_started_worker_when_admission_fails() -> None:
    description = await _fake_description()

    class StartedRuntime:
        adapter_kind = "runtime-worker-v2"
        started = False
        closed = False

        async def start(self) -> dict[str, object]:
            self.started = True
            return {}

        async def execute(self, command: object) -> Described:
            return description

        async def close(self) -> None:
            self.closed = True

    runtime = StartedRuntime()
    gate = RuntimeStartupGate(
        runtime=runtime,  # type: ignore[arg-type]
        release_inspector=StaticReleaseInspector(_inventory()),
        expected_manifest_digest="0" * 64,
        expected_release_manifest_sha256="e" * 64,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(
            description.capabilities
        ),
    )

    with pytest.raises(RuntimeStartupError, match="manifest digest mismatch"):
        await gate.startup()
    assert runtime.started is True
    assert runtime.closed is True
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


async def test_create_app_closes_owned_runtime_on_lifespan_exit(
    monkeypatch: pytest.MonkeyPatch,
    database: Any,
) -> None:
    description = await _fake_description()
    closed: list[str] = []

    class OwnedRuntime:
        adapter_kind = "runtime-worker-v2"
        isolated = False

        async def start(self) -> dict[str, object]:
            return {}

        async def execute(self, command: object) -> Described:
            return description

        async def close(self) -> None:
            closed.append("closed")
            self.isolated = True

    runtime = OwnedRuntime()

    def fake_build(_settings: object) -> RuntimeStartupGate:
        return RuntimeStartupGate(
            runtime=runtime,  # type: ignore[arg-type]
            release_inspector=StaticReleaseInspector(_inventory()),
            expected_manifest_digest=description.manifest_digest,
            expected_release_manifest_sha256="e" * 64,
            expected_capability_shape_sha256=runtime_capability_shape_sha256(
                description.capabilities
            ),
        )

    monkeypatch.setattr("app.main.build_runtime_startup_gate", fake_build)
    settings = _production_settings(environment="test", cookie_secure=False)
    from app.main import create_app

    application = create_app(settings=settings, database=database)
    async with application.router.lifespan_context(application):
        assert application.state.chart_runtime is runtime
        assert application.state.runtime_gate is not None
    assert closed == ["closed"]


def test_filesystem_release_inspector_recomputes_the_complete_signed_inventory(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(release_root)
    inspector = FileSystemRuntimeReleaseInspector(
        release_root=release_root,
        expected_release_manifest_sha256=manifest_sha256,
        expected_release_name="fixture-release",
        expected_source_commit="fixture-commit",
    )

    inventory = inspector.inspect()

    assert inventory == RuntimeReleaseInventory(
        release_manifest_sha256=manifest_sha256,
        release_file_count=218,
        physical_file_count=219,
        provider_ids=V51_RELEASE_CAPABILITY_IDS,
        ready_provider_ids=V51_RELEASE_CAPABILITY_IDS,
        reference_pack_count=55,
        evidence_record_count=1328,
        runtime_closure_file_count=218,
    )


def test_filesystem_release_inspector_rejects_a_tampered_signed_file(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(release_root)
    (release_root / "resources" / "runtime" / "providers" / "bazi.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeStartupError, match="signed file digest mismatch"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit="fixture-commit",
        ).inspect()


def test_filesystem_release_inspector_rejects_unsigned_extra_files(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(release_root)
    (release_root / "unsigned-runtime-hook.py").write_text(
        "raise RuntimeError('unsigned')\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeStartupError, match="unsigned filesystem entry"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit="fixture-commit",
        ).inspect()


def test_filesystem_release_inspector_rejects_unsigned_empty_directories(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(release_root)
    (release_root / "unsigned-empty-directory").mkdir()

    with pytest.raises(RuntimeStartupError, match="unsigned filesystem entry"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit="fixture-commit",
        ).inspect()


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("provider", "13 Provider catalog"),
        ("reference", "55/55"),
        ("evidence", "1328"),
        ("closure", "all 218"),
    ),
)
def test_filesystem_release_inspector_rejects_resigned_but_incomplete_inventories(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    _build_signed_release_fixture(release_root)
    if mutation == "provider":
        relative = "resources/runtime/catalog-v1.json"
        payload = json.loads((release_root / relative).read_text(encoding="utf-8"))
        payload["providers"].pop()
        (release_root / relative).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    elif mutation == "reference":
        relative = "references/catalog/catalog.json"
        payload = json.loads((release_root / relative).read_text(encoding="utf-8"))
        payload["ready_count"] = 54
        payload["ready_reference_packs"].pop()
        (release_root / relative).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    elif mutation == "evidence":
        relative = "references/index/evidence-rules.jsonl"
        path = release_root / relative
        path.write_text("\n".join(path.read_text(encoding="utf-8").splitlines()[:-1]) + "\n")
    else:
        relative = "release/runtime-closure-v1.json"
        payload = json.loads((release_root / relative).read_text(encoding="utf-8"))
        payload["files"].pop()
        (release_root / relative).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    manifest_sha256 = _resign_release_fixture(release_root, relative)

    with pytest.raises(RuntimeStartupError, match=message):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit="fixture-commit",
        ).inspect()


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"runtime_adapter": "fake"}, "Fake Runtime"),
        ({"runtime_release_profile": "v53-time-check"}, "local/test only"),
        (
            {
                "runtime_adapter": "one-shot",
                "runtime_release_profile": "v51-extension-facts",
            },
            "local/test only",
        ),
        ({"runtime_launcher_path": "relative/launcher"}, "launcher"),
        ({"runtime_launcher_path": "/srv/other/launcher"}, "fixed launcher"),
        ({"runtime_expected_manifest_digest": None}, "manifest digest"),
        ({"runtime_expected_capability_shape_sha256": None}, "capability shape"),
        ({"runtime_expected_capability_shape_sha256": "a" * 64}, "frozen capability"),
        ({"runtime_state_root": None}, "state root"),
    ),
)
def test_production_runtime_configuration_fails_closed(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        _production_settings(**overrides)


def test_production_runtime_configuration_accepts_only_the_frozen_release() -> None:
    from app.config import _RUNTIME_RELEASE_PROFILES

    settings = _production_settings()
    profile = _RUNTIME_RELEASE_PROFILES[settings.runtime_release_profile]

    assert settings.runtime_adapter == "worker-v2"
    assert settings.runtime_release_profile == "v51"
    assert settings.runtime_launcher_path == Path(
        "/opt/mingli-master/scripts/run_reading_transaction.sh"
    )
    assert settings.runtime_python_path == Path("/opt/mingli-runtime/venv/bin/python")
    assert (
        settings.runtime_expected_manifest_digest
        == "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
    )
    assert (
        settings.runtime_expected_capability_shape_sha256
        == "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
    )
    assert profile["release_manifest_sha256"] == (
        "280145cddaaddb693f8256214381d75d8579e620ec731e9a9ce4ec10522bc51d"
    )
    assert profile["source_commit"] == "3f70b9025f828343759aaef22dab9ac5f2879a8c"
    assert profile["worker_sha256"] == (
        "b8d05ca1a4d6392598442e8fed80d73a2ce079b757c2d6bc059f5ff13b629e3e"
    )
    assert profile["worker_protocol"] == "mingli-runtime-worker-v2"
    assert profile["worker_turn_terminal"] == "result-idle-v1"


def test_production_omitted_adapter_defaults_to_worker_v2_and_v51() -> None:
    from app.config import Settings

    values = {
        "environment": "production",
        "cookie_secure": True,
        "otp_adapter": "disabled",
        "identity_hash_key": "production-identity-key",
        "content_encryption_key_b64": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=",
        "content_encryption_key_id": "production-content-v1",
        "runtime_launcher_path": "/opt/mingli-master/scripts/run_reading_transaction.sh",
        "runtime_python_path": "/opt/mingli-runtime/venv/bin/python",
        "runtime_release_root": "/opt/mingli-master",
        "runtime_state_root": "/var/lib/mingli",
        "runtime_expected_manifest_digest": (
            "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
        ),
        "runtime_expected_capability_shape_sha256": (
            "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
        ),
        "model_adapter": "deepseek",
        "deepseek_api_key": "test-only-obviously-not-a-real-key",
        "model_price_snapshot_version": "fixture-price-v1",
        "model_input_price_microunits_per_million_tokens": 1,
        "model_output_price_microunits_per_million_tokens": 1,
    }
    settings = Settings(**values)
    assert settings.runtime_adapter == "worker-v2"
    assert settings.runtime_release_profile == "v51"


def test_process_adapter_rejects_group_or_world_writable_state_root(
    tmp_path: Path,
) -> None:
    launcher = tmp_path / "runtime-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    state_root.chmod(0o770)

    with pytest.raises(RuntimeStartupError, match="group/world writable"):
        OneShotMingliRuntimeAdapter(
            launcher_path=launcher,
            runtime_python_path=Path("/usr/bin/python3"),
            state_root=state_root,
            timeout_seconds=1,
        )


def test_filesystem_release_inspector_rejects_group_or_world_writable_release_root(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(release_root)
    release_root.chmod(0o707)

    with pytest.raises(RuntimeStartupError, match="group/world writable"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit="fixture-commit",
        ).inspect()


def test_filesystem_release_inspector_rejects_writable_directory_inside_release(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(release_root)
    (release_root / "resources" / "runtime" / "providers").chmod(0o770)

    with pytest.raises(RuntimeStartupError, match="group/world writable"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit="fixture-commit",
        ).inspect()


async def test_runtime_startup_gate_factory_requires_one_shot_settings_and_starts_red(
    tmp_path: Path,
) -> None:
    from app.config import Settings

    launcher = tmp_path / "runtime-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    settings = Settings(
        runtime_adapter="one-shot",
        runtime_launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest="f" * 64,
        runtime_expected_capability_shape_sha256="a" * 64,
    )

    gate = build_runtime_startup_gate(settings)

    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


def test_runtime_startup_gate_admits_the_relationship_release_profile(
    tmp_path: Path,
) -> None:
    from app.config import Settings

    launcher = tmp_path / "runtime-relationship-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    settings = Settings(
        runtime_adapter="one-shot",
        runtime_release_profile="v52-relationship",
        runtime_launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=(
            "6118c5f525c87b9cbde95b4d51c945be18bfd18fff8e03306da9fa748b87d917"
        ),
        runtime_expected_capability_shape_sha256=(
            "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
        ),
    )

    gate = build_runtime_startup_gate(settings)

    assert gate.expected_release_manifest_sha256 == (
        "bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50"
    )
    assert gate.release_inspector.expected_release_name == (
        "mingli-master-portable-core-v52-relationship"
    )


_PREVIOUS_V53_TIME_CHECK_LISTING_SHA = (
    "79fd0bbd47fd28568c559383fd1aae0cce0938232056a3e0ad33474fa36e8c40"
)
_PREVIOUS_V53_TIME_CHECK_SOURCE_COMMIT = (
    "b498382e67c0f0a41b0e5563b2773d1e1e3323f5"
)
_CLEAN_443A777_RELEASE_MANIFEST_SHA = (
    "d6e0df3e64e588f67cb500283199ae5413001b641d5b54f445ef610caff40130"
)
_PREVIOUS_COMBINED_OVERLAY_LISTING_SHA = (
    "9700fe96e2c440dc8b14c41aed576264d893c7a23d638708eafe40388771db71"
)
_HEAD_RESERIALIZED_SOURCE_COMMIT = (
    "a3a29546e8b46b608314118bdd2d5faf80955149"
)
_HEAD_RESERIALIZED_LISTING_SHA = (
    "42ac0ab548663bea785ba1c7a1b07a74eee9240ddc637ed100451887c8d04a9a"
)
_ADMITTED_V53_RELEASE_MANIFEST_SHA = (
    "f1deb17a9b4f39b09b2478c8942dcf0761d90bcba95dcbc44a15b8c84f79190b"
)
_ADMITTED_V53_SOURCE_COMMIT = "6db9dd37d8e62cd425798be2c64ad1121c1c1649"
_ADMITTED_V53_WORKER_SHA256 = (
    "e89df2c08df29e65ffc91c05e8e4e5be99f72f67e26b79c5b23a4eb2222ddc9c"
)
_ADMITTED_V53_DESCRIBE_DIGEST = (
    "2da3c62b250959a6f011434ee38fc3cf3851725a5fafb794ef78d978d9367b22"
)
_ADMITTED_V53_CAPABILITY_SHAPE = (
    "9b9193285622a183c06802713fbfb62fa4c76e9190b692d9d422261a418e63af"
)
_LEGACY_V53_RELEASE_MANIFEST_SHA = (
    "d1b49d5842feb5d4143330d1d250af625f42644a930f7d9d9c344c5d0363b090"
)
_LEGACY_V53_SOURCE_COMMIT = "9c615a70f08d5609af09ead100d2b5d90e558fe8"
_LEGACY_V53_WORKER_SHA256 = (
    "3512987322ef18bb91c4798e77d7ef982d2e7e31ae9e2ddd321d78aa90261b50"
)
_ADMITTED_V51_SOURCE_COMMIT = "3f70b9025f828343759aaef22dab9ac5f2879a8c"
_ADMITTED_V51_RELEASE_MANIFEST_SHA = (
    "280145cddaaddb693f8256214381d75d8579e620ec731e9a9ce4ec10522bc51d"
)
_PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT = (
    "adfd7b6bf1c6a5e6df184bdd792bbf4956b009e1"
)
_PREVIOUS_PRODUCTION_V51_LISTING_SHA = (
    "93433f7fa9a9bef1115216240767c2c8e12e4ad9f0807124d05a47ddd0701f5d"
)
_INTERMEDIATE_V51_SOURCE_COMMIT = "fdf008f47fb5ad963f5d2c7979418388260ebbfa"
_INTERMEDIATE_V51_LISTING_SHA = (
    "35325c8553e31e37a07232b2a5b94341844794ec286fb2f8eacbbb581dbd7b62"
)
_ADMITTED_V51_WORKER_SHA256 = (
    "b8d05ca1a4d6392598442e8fed80d73a2ce079b757c2d6bc059f5ff13b629e3e"
)
_ADMITTED_V51_DESCRIBE_DIGEST = (
    "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
)
_ADMITTED_V51_CAPABILITY_SHAPE = (
    "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
)
_FORBIDDEN_UNSIGNED_V51_LISTING_SHA = (
    "251ecf42ea12a64c7d38618a794442007beea7432835e414251006809c2d3611"
)
_PREVIOUS_V51_WITHOUT_WORKER_LISTING_SHA = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)
_WORKER_RELATIVE = "scripts/reading_engine/runtime_worker.py"
_QA_LOCKED_BAZI_CALC_SHA256 = (
    "ab35fbf511693d47487aa0601bdba32d13a44cf988888b90c085d6573027249a"
)
_QA_LOCKED_LIUREN_CALC_SHA256 = (
    "f276643106194766107008dfc08df25ef0c141e9f064c39bd7609d8732668908"
)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_QA_CLEAN_RELEASE_ROOT = Path(
    "/Users/yuhanglin/multica_workspaces_desktop-api.multica.ai/"
    "72222bca-49d3-4729-97ea-4a84e84ddce7/2927841eff9b/qa-runtime-base-443a777"
)
_QA_RUNTIME_PYTHON = Path(
    "/Users/yuhanglin/multica_workspaces_desktop-api.multica.ai/"
    "72222bca-49d3-4729-97ea-4a84e84ddce7/2927841eff9b/"
    "qa-runtime-venv-443a777/bin/python"
)


def _install_locked_worker(release_root: Path) -> Path:
    source = _REPO_ROOT / "core" / "mingli-master" / _WORKER_RELATIVE
    worker = release_root / _WORKER_RELATIVE
    worker.parent.mkdir(parents=True, exist_ok=True)
    worker.write_bytes(source.read_bytes())
    worker.chmod(0o644)
    assert _sha256(worker) == _ADMITTED_V53_WORKER_SHA256
    return worker


def _git_head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def _discover_source_for_commit(commit: str, env_key: str) -> Path | None:
    candidates: list[Path] = []
    raw = os.environ.get(env_key)
    if raw:
        candidates.append(Path(raw).expanduser())
    short = commit[:12]
    candidates.extend(
        (
            Path(f"/tmp/ming21-v51-{short}"),
            _REPO_ROOT / ".runtime-cache" / f"v51-{short}",
        )
    )
    for path in candidates:
        worker = path / _WORKER_RELATIVE
        if (
            worker.is_file()
            and _sha256(worker) == _ADMITTED_V51_WORKER_SHA256
            and _git_head(path) == commit
        ):
            return path
    return None


def _discover_v51_source_root() -> Path | None:
    return _discover_source_for_commit(
        _ADMITTED_V51_SOURCE_COMMIT,
        "MINGLI_V51_RELEASE_SOURCE",
    )


def _install_v51_worker(release_root: Path) -> Path:
    source_root = _discover_v51_source_root()
    if source_root is None:
        pytest.skip("the admitted v51 worker-v2 source is not present")
    source = source_root / _WORKER_RELATIVE
    worker = release_root / _WORKER_RELATIVE
    worker.parent.mkdir(parents=True, exist_ok=True)
    worker.write_bytes(source.read_bytes())
    worker.chmod(0o644)
    assert _sha256(worker) == _ADMITTED_V51_WORKER_SHA256
    return worker


def _dummy_runtime_python(tmp_path: Path) -> Path:
    venv = tmp_path / "dummy-runtime"
    (venv / "bin").mkdir(parents=True, exist_ok=True)
    python = venv / "bin" / "python"
    python.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    python.chmod(0o700)
    integrity = venv / "runtime-integrity.json"
    integrity.write_text("{}\n", encoding="utf-8")
    integrity.chmod(0o600)
    return python


def _v53_worker_settings(
    tmp_path: Path,
    *,
    release_root: Path,
    runtime_python: Path,
) -> Any:
    from app.config import Settings

    launcher = tmp_path / "runtime-rollback-fixture"
    if not launcher.is_file():
        launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o700)
    _install_locked_worker(release_root)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700, exist_ok=True)
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'startup-gate.sqlite3'}",
        runtime_adapter="worker-v2",
        runtime_release_profile="v53-time-check",
        runtime_launcher_path=launcher,
        runtime_python_path=runtime_python,
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=_ADMITTED_V53_DESCRIBE_DIGEST,
        runtime_expected_capability_shape_sha256=_ADMITTED_V53_CAPABILITY_SHAPE,
        chart_fast_path_timeout_seconds=2.0,
    )


def _v51_worker_settings(
    tmp_path: Path,
    *,
    release_root: Path,
    runtime_python: Path,
) -> Any:
    from app.config import Settings

    launcher = tmp_path / "runtime-v51-fixture"
    if not launcher.is_file():
        launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o700)
    _install_v51_worker(release_root)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700, exist_ok=True)
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'startup-gate.sqlite3'}",
        runtime_adapter="worker-v2",
        runtime_release_profile="v51",
        runtime_launcher_path=launcher,
        runtime_python_path=runtime_python,
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=_ADMITTED_V51_DESCRIBE_DIGEST,
        runtime_expected_capability_shape_sha256=_ADMITTED_V51_CAPABILITY_SHAPE,
        chart_fast_path_timeout_seconds=2.0,
    )


def _materialize_core_release(
    destination: Path,
    *,
    source: Path,
    source_commit: str,
    expected_listing: str,
) -> str:
    scripts = str(source / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import release_deploy as rd

    files = rd.tracked_release_files(source)
    manifest = rd.build_manifest(source, files, source_commit)
    payload = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    listing = hashlib.sha256(payload).hexdigest()
    assert listing == expected_listing
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


def _materialize_v51_release(destination: Path) -> str:
    source = _discover_v51_source_root()
    if source is None:
        pytest.skip("the admitted v51 worker-v2 source is not present")
    return _materialize_core_release(
        destination,
        source=source,
        source_commit=_ADMITTED_V51_SOURCE_COMMIT,
        expected_listing=_ADMITTED_V51_RELEASE_MANIFEST_SHA,
    )


def test_runtime_startup_gate_admits_the_exact_v51_candidate_identity(
    tmp_path: Path,
) -> None:
    from app.config import _RUNTIME_RELEASE_PROFILES, Settings

    launcher = tmp_path / "runtime-v51-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    profile = _RUNTIME_RELEASE_PROFILES["v51"]
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    settings = settings.model_copy(update={"runtime_launcher_path": launcher})

    gate = build_runtime_startup_gate(settings)

    assert profile == {
        "manifest_digest": _ADMITTED_V51_DESCRIBE_DIGEST,
        "capability_shape_sha256": _ADMITTED_V51_CAPABILITY_SHAPE,
        "release_manifest_sha256": _ADMITTED_V51_RELEASE_MANIFEST_SHA,
        "release_name": "mingli-master-portable-core",
        "source_commit": _ADMITTED_V51_SOURCE_COMMIT,
        "signed_file_count": 218,
        "physical_file_count": 219,
        "worker_sha256": _ADMITTED_V51_WORKER_SHA256,
        "worker_protocol": "mingli-runtime-worker-v2",
        "worker_turn_terminal": "result-idle-v1",
    }
    assert gate.runtime.adapter_kind == "runtime-worker-v2"
    assert gate.expected_manifest_digest == profile["manifest_digest"]
    assert gate.expected_capability_shape_sha256 == profile["capability_shape_sha256"]
    assert gate.expected_release_manifest_sha256 == profile["release_manifest_sha256"]
    assert gate.release_inspector.expected_source_commit == profile["source_commit"]
    assert gate.release_inspector.expected_release_name == profile["release_name"]
    assert gate.expected_release_file_count == 218
    assert gate.expected_physical_file_count == 219
    assert gate.release_inspector.expected_release_file_count == 218
    assert gate.release_inspector.expected_physical_file_count == 219
    assert len(V51_RELEASE_CAPABILITY_IDS) == 13
    assert gate.expected_capability_ids == V51_RELEASE_CAPABILITY_IDS
    assert profile["release_manifest_sha256"] != _FORBIDDEN_UNSIGNED_V51_LISTING_SHA
    assert profile["release_manifest_sha256"] != _PREVIOUS_V51_WITHOUT_WORKER_LISTING_SHA
    assert profile["release_manifest_sha256"] != _ADMITTED_V53_RELEASE_MANIFEST_SHA
    assert profile["release_manifest_sha256"] != _PREVIOUS_COMBINED_OVERLAY_LISTING_SHA
    assert profile["release_manifest_sha256"] != _CLEAN_443A777_RELEASE_MANIFEST_SHA
    assert profile["release_manifest_sha256"] != _PREVIOUS_PRODUCTION_V51_LISTING_SHA
    assert profile["release_manifest_sha256"] != _INTERMEDIATE_V51_LISTING_SHA
    assert profile["source_commit"] != _ADMITTED_V53_SOURCE_COMMIT
    assert profile["source_commit"] != _PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT
    assert profile["source_commit"] != _INTERMEDIATE_V51_SOURCE_COMMIT
    assert profile["worker_sha256"] != _ADMITTED_V53_WORKER_SHA256
    assert Settings().chart_fast_path_timeout_seconds == 2.0
    assert Settings().runtime_adapter == "fake"


def test_production_v51_rejects_unsigned_and_v53_identities() -> None:
    from app.config import _RUNTIME_RELEASE_PROFILES

    v51 = _RUNTIME_RELEASE_PROFILES["v51"]
    assert v51["release_manifest_sha256"] == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert v51["source_commit"] == _ADMITTED_V51_SOURCE_COMMIT
    assert v51["worker_sha256"] == _ADMITTED_V51_WORKER_SHA256
    assert v51["release_manifest_sha256"] != _FORBIDDEN_UNSIGNED_V51_LISTING_SHA
    assert v51["release_manifest_sha256"] != _PREVIOUS_V51_WITHOUT_WORKER_LISTING_SHA
    assert v51["release_manifest_sha256"] != _ADMITTED_V53_RELEASE_MANIFEST_SHA
    assert v51["release_manifest_sha256"] != _PREVIOUS_COMBINED_OVERLAY_LISTING_SHA
    assert v51["release_manifest_sha256"] != _PREVIOUS_PRODUCTION_V51_LISTING_SHA
    assert v51["release_manifest_sha256"] != _INTERMEDIATE_V51_LISTING_SHA
    assert v51["source_commit"] != _ADMITTED_V53_SOURCE_COMMIT
    assert v51["source_commit"] != _PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT
    assert v51["source_commit"] != _INTERMEDIATE_V51_SOURCE_COMMIT
    assert v51["worker_sha256"] != _ADMITTED_V53_WORKER_SHA256


def test_production_worker_v2_on_v51_admits_locked_worker_and_rejects_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import config
    from app.config import _RUNTIME_RELEASE_PROFILES

    release_root = tmp_path / "mingli-master"
    release_root.mkdir(mode=0o700)
    launcher = release_root / "scripts" / "run_reading_transaction.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    python = _dummy_runtime_python(tmp_path)
    state_root = tmp_path / "mingli-state"
    state_root.mkdir(mode=0o700)
    _install_v51_worker(release_root)
    monkeypatch.setattr(config, "_PRODUCTION_RUNTIME_LAUNCHER", launcher)
    monkeypatch.setattr(config, "_PRODUCTION_RUNTIME_PYTHON", python)
    monkeypatch.setattr(config, "_PRODUCTION_RUNTIME_RELEASE_ROOT", release_root)
    monkeypatch.setattr(config, "_PRODUCTION_RUNTIME_STATE_ROOT", state_root)

    settings = _production_settings(
        runtime_launcher_path=launcher,
        runtime_python_path=python,
        runtime_release_root=release_root,
        runtime_state_root=state_root,
    )
    v51 = _RUNTIME_RELEASE_PROFILES["v51"]
    assert settings.environment == "production"
    assert settings.runtime_adapter == "worker-v2"
    assert settings.runtime_release_profile == "v51"
    gate = build_runtime_startup_gate(settings)
    assert gate.runtime.adapter_kind == "runtime-worker-v2"
    assert gate.expected_release_manifest_sha256 == v51["release_manifest_sha256"]
    assert gate.release_inspector.expected_source_commit == v51["source_commit"]
    assert gate.expected_release_file_count == 218

    drifted = release_root / _WORKER_RELATIVE
    drifted.write_bytes(b"not-the-admitted-v51-runtime-worker\n")
    drifted.chmod(0o644)
    with pytest.raises(RuntimeStartupError, match="worker digest mismatch"):
        build_runtime_startup_gate(settings)


async def test_runtime_startup_gate_rejects_the_previous_b498_manifest_identity(
    tmp_path: Path,
) -> None:
    description = await _fake_description()
    launcher = _write_executable(tmp_path / "runtime-fixture", description.to_dict())
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=1,
    )
    inventory = replace(
        _inventory(),
        release_manifest_sha256=_PREVIOUS_V53_TIME_CHECK_LISTING_SHA,
    )
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=StaticReleaseInspector(inventory),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256=_ADMITTED_V53_RELEASE_MANIFEST_SHA,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(
            description.capabilities
        ),
    )

    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


def test_filesystem_release_inspector_rejects_the_previous_b498_source_identity(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    manifest_sha256 = _build_signed_release_fixture(
        release_root,
        source_commit=_PREVIOUS_V53_TIME_CHECK_SOURCE_COMMIT,
    )

    with pytest.raises(RuntimeStartupError, match="release identity mismatch"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=manifest_sha256,
            expected_release_name="fixture-release",
            expected_source_commit=_ADMITTED_V53_SOURCE_COMMIT,
        ).inspect()


def _discover_clean_v53_release_root() -> Path | None:
    candidates = []
    for key in (
        "MINGLI_MING21_CLEAN_RELEASE_ROOT",
        "MINGLI_RUNTIME_TEST_RELEASE_ROOT",
    ):
        raw = os.environ.get(key)
        if raw:
            candidates.append(Path(raw).expanduser())
    candidates.extend(
        (
            _REPO_ROOT / ".runtime" / "v53-time-check-release",
            _QA_CLEAN_RELEASE_ROOT,
        )
    )
    for path in candidates:
        manifest = path / ".mingli-release-manifest.json"
        if not manifest.is_file():
            continue
        if _sha256(manifest) == _CLEAN_443A777_RELEASE_MANIFEST_SHA:
            return path
    return None


def _discover_runtime_python() -> Path | None:
    candidates = []
    raw = os.environ.get("MINGLI_RUNTIME_TEST_PYTHON")
    if raw:
        candidates.append(Path(raw).expanduser())
    candidates.extend(
        (
            Path("/tmp/ming21-v51-3f70b902-venv/bin/python"),
            _REPO_ROOT / ".runtime-cache" / "v51-3f70b902-venv" / "bin" / "python",
        )
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _copy_clean_runtime_python(source_python: Path, destination: Path) -> Path:
    """Clone the provisioned venv without mutable bytecode caches."""

    shutil.copytree(
        source_python.parents[1],
        destination,
        copy_function=shutil.copy2,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    return destination / "bin" / "python"


def _copy_signed_release(source: Path, destination: Path) -> None:
    manifest = json.loads(
        (source / ".mingli-release-manifest.json").read_text(encoding="utf-8")
    )
    destination.mkdir(mode=0o700)
    shutil.copy2(
        source / ".mingli-release-manifest.json",
        destination / ".mingli-release-manifest.json",
    )
    for relative in manifest["files"]:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    for relative, mode in manifest["modes"].items():
        (destination / relative).chmod(mode)


def _overlay_locked_script(
    release_root: Path,
    relative: str,
    source: Path,
    expected_sha256: str,
) -> None:
    payload = source.read_bytes()
    overlay_sha256 = hashlib.sha256(payload).hexdigest()
    if overlay_sha256 != expected_sha256:
        raise AssertionError(f"{relative} is not the QA-locked SHA-256")
    target = release_root / relative
    replaced_sha256 = _sha256(target)
    mode = target.stat().st_mode
    target.write_bytes(payload)
    target.chmod(mode)
    manifest_path = release_root / ".mingli-release-manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    if manifest_text.count(replaced_sha256) != 1:
        raise AssertionError(f"{relative} digest is missing or not unique")
    manifest_path.write_text(
        manifest_text.replace(replaced_sha256, overlay_sha256),
        encoding="utf-8",
    )


def _materialize_combined_overlay_release(tmp_path: Path) -> Path:
    source = _discover_clean_v53_release_root()
    if source is None:
        pytest.skip("the clean 443a777 Runtime release is not present")
    bazi = _REPO_ROOT / "core" / "mingli-master" / "scripts" / "bazi_calc.py"
    liuren = _REPO_ROOT / "core" / "mingli-master" / "scripts" / "liuren_calc.py"
    if not bazi.is_file() or not liuren.is_file():
        pytest.skip("QA-locked Bazi/Liuren overlay scripts are not present")
    release_root = tmp_path / "combined-overlay-release"
    _copy_signed_release(source, release_root)
    _overlay_locked_script(
        release_root,
        "scripts/bazi_calc.py",
        bazi,
        _QA_LOCKED_BAZI_CALC_SHA256,
    )
    _overlay_locked_script(
        release_root,
        "scripts/liuren_calc.py",
        liuren,
        _QA_LOCKED_LIUREN_CALC_SHA256,
    )
    listing = _sha256(release_root / ".mingli-release-manifest.json")
    assert listing == _PREVIOUS_COMBINED_OVERLAY_LISTING_SHA
    return release_root


def _v53_one_shot_settings(
    tmp_path: Path,
    *,
    release_root: Path,
    runtime_python: Path,
) -> Any:
    from app.config import Settings

    launcher = release_root / "scripts" / "run_reading_transaction.sh"
    if not launcher.is_file():
        launcher = tmp_path / "runtime-fixture"
        launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700, exist_ok=True)
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'startup-gate.sqlite3'}",
        runtime_adapter="one-shot",
        runtime_release_profile="v53-time-check",
        runtime_launcher_path=launcher,
        runtime_python_path=runtime_python,
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=_ADMITTED_V53_DESCRIBE_DIGEST,
        runtime_expected_capability_shape_sha256=_ADMITTED_V53_CAPABILITY_SHAPE,
        chart_fast_path_timeout_seconds=2.0,
    )


def test_v53_profile_pins_one_controlled_release_and_rejects_legacy_tuple(
    tmp_path: Path,
) -> None:
    from app.config import _RUNTIME_RELEASE_PROFILES

    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    settings = _v53_one_shot_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=Path("/usr/bin/python3"),
    )

    gate = build_runtime_startup_gate(settings)
    profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]

    assert profile == {
        "manifest_digest": _ADMITTED_V53_DESCRIBE_DIGEST,
        "capability_shape_sha256": _ADMITTED_V53_CAPABILITY_SHAPE,
        "release_manifest_sha256": _ADMITTED_V53_RELEASE_MANIFEST_SHA,
        "release_name": "mingli-master-portable-core",
        "source_commit": _ADMITTED_V53_SOURCE_COMMIT,
        "signed_file_count": 227,
        "physical_file_count": 228,
        "worker_sha256": _ADMITTED_V53_WORKER_SHA256,
        "worker_protocol": "mingli-runtime-worker-v2",
        "worker_turn_terminal": "result-idle-v1",
    }
    assert gate.expected_release_manifest_sha256 == _ADMITTED_V53_RELEASE_MANIFEST_SHA
    assert gate.release_inspector.expected_source_commit == _ADMITTED_V53_SOURCE_COMMIT
    assert gate.expected_release_file_count == 227
    assert gate.expected_physical_file_count == 228
    assert gate.release_inspector.expected_release_file_count == 227
    assert gate.release_inspector.expected_physical_file_count == 228
    assert profile["release_manifest_sha256"] != _LEGACY_V53_RELEASE_MANIFEST_SHA
    assert profile["source_commit"] != _LEGACY_V53_SOURCE_COMMIT
    assert profile["worker_sha256"] != _LEGACY_V53_WORKER_SHA256


async def test_runtime_startup_gate_rejects_the_clean_443a777_manifest_identity(
    tmp_path: Path,
) -> None:
    description = await _fake_description()
    launcher = _write_executable(tmp_path / "runtime-fixture", description.to_dict())
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=5,
    )
    inventory = replace(
        _inventory(),
        release_manifest_sha256=_CLEAN_443A777_RELEASE_MANIFEST_SHA,
    )
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=StaticReleaseInspector(inventory),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256=_ADMITTED_V53_RELEASE_MANIFEST_SHA,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(
            description.capabilities
        ),
    )

    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


async def test_runtime_startup_gate_rejects_an_arbitrary_wrong_release_manifest_digest(
    tmp_path: Path,
) -> None:
    description = await _fake_description()
    launcher = _write_executable(tmp_path / "runtime-fixture", description.to_dict())
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        state_root=state_root,
        timeout_seconds=5,
    )
    inventory = replace(_inventory(), release_manifest_sha256="0" * 64)
    gate = RuntimeStartupGate(
        runtime=runtime,
        release_inspector=StaticReleaseInspector(inventory),
        expected_manifest_digest=description.manifest_digest,
        expected_release_manifest_sha256=_ADMITTED_V53_RELEASE_MANIFEST_SHA,
        expected_capability_shape_sha256=runtime_capability_shape_sha256(
            description.capabilities
        ),
    )

    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()
    with pytest.raises(RuntimeStartupError, match="not ready"):
        await gate.readiness_probe()


async def test_build_runtime_startup_gate_and_create_app_fail_closed_on_wrong_digest(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "wrong-digest-release"
    release_root.mkdir(mode=0o700)
    (release_root / ".mingli-release-manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    assert _sha256(release_root / ".mingli-release-manifest.json") != (
        _ADMITTED_V51_RELEASE_MANIFEST_SHA
    )
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    gate = build_runtime_startup_gate(settings)
    assert gate.runtime.adapter_kind == "runtime-worker-v2"
    assert gate.expected_release_manifest_sha256 == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert gate.release_inspector.expected_source_commit == _ADMITTED_V51_SOURCE_COMMIT
    assert gate.expected_release_file_count == 218

    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        async with application.router.lifespan_context(application):
            raise AssertionError("create_app must fail closed on a wrong digest")


async def test_build_runtime_startup_gate_and_create_app_fail_closed_on_clean_tree(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "unsigned-clean-release"
    release_root.mkdir(mode=0o700)
    (release_root / ".mingli-release-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "release": "mingli-master-portable-core",
                "source_commit": _ADMITTED_V51_SOURCE_COMMIT,
                "files": {},
                "modes": {},
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    listing = _sha256(release_root / ".mingli-release-manifest.json")
    assert listing != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert listing != _PREVIOUS_V51_WITHOUT_WORKER_LISTING_SHA
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    assert settings.runtime_release_profile == "v51"
    assert (
        settings.runtime_expected_manifest_digest == _ADMITTED_V51_DESCRIBE_DIGEST
    )
    gate = build_runtime_startup_gate(settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        async with application.router.lifespan_context(application):
            raise AssertionError("create_app must reject unsigned or clean-tree listings")


async def test_build_runtime_startup_gate_and_create_app_reject_previous_overlay_listing(
    tmp_path: Path,
) -> None:
    from app.config import _RUNTIME_RELEASE_PROFILES

    v51 = _RUNTIME_RELEASE_PROFILES["v51"]
    assert v51["release_manifest_sha256"] != _PREVIOUS_COMBINED_OVERLAY_LISTING_SHA
    assert v51["release_manifest_sha256"] != _ADMITTED_V53_RELEASE_MANIFEST_SHA
    assert v51["release_manifest_sha256"] != _FORBIDDEN_UNSIGNED_V51_LISTING_SHA
    assert v51["release_manifest_sha256"] != _PREVIOUS_V51_WITHOUT_WORKER_LISTING_SHA
    release_root = tmp_path / "previous-overlay-release"
    release_root.mkdir(mode=0o700)
    (release_root / ".mingli-release-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "release": "mingli-master-portable-core",
                "source_commit": _ADMITTED_V53_SOURCE_COMMIT,
                "files": {},
                "modes": {},
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    listing = _sha256(release_root / ".mingli-release-manifest.json")
    assert listing != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    gate = build_runtime_startup_gate(settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        async with application.router.lifespan_context(application):
            raise AssertionError("create_app must reject the previous overlay listing")


async def _assert_create_app_rejects_release(
    tmp_path: Path,
    release_root: Path,
    *,
    message: str,
    assertion: str,
) -> None:
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    gate = build_runtime_startup_gate(settings)
    assert gate.expected_release_manifest_sha256 == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert gate.release_inspector.expected_source_commit == _ADMITTED_V51_SOURCE_COMMIT
    with pytest.raises(RuntimeStartupError, match=message):
        await gate.startup()

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match=message):
        async with application.router.lifespan_context(application):
            raise AssertionError(assertion)


def _rewrite_release_source_commit(release_root: Path, source_commit: str) -> str:
    manifest_path = release_root / ".mingli-release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_commit"] = source_commit
    payload = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    manifest_path.write_bytes(payload)
    manifest_path.chmod(0o600)
    return hashlib.sha256(payload).hexdigest()


async def test_create_app_rejects_previous_production_v51_identity(
    tmp_path: Path,
) -> None:
    source = _discover_source_for_commit(
        _PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT,
        "MINGLI_V51_PREVIOUS_SOURCE",
    )
    if source is None:
        pytest.skip("the previous production v51 source is not present")
    release_root = tmp_path / "previous-production-v51"
    listing = _materialize_core_release(
        release_root,
        source=source,
        source_commit=_PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT,
        expected_listing=_PREVIOUS_PRODUCTION_V51_LISTING_SHA,
    )
    assert listing == _PREVIOUS_PRODUCTION_V51_LISTING_SHA
    assert listing != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    await _assert_create_app_rejects_release(
        tmp_path,
        release_root,
        message="release manifest digest mismatch",
        assertion="create_app must reject adfd7b6/93433f7",
    )


async def test_create_app_rejects_intermediate_v51_identity(tmp_path: Path) -> None:
    source = _discover_source_for_commit(
        _INTERMEDIATE_V51_SOURCE_COMMIT,
        "MINGLI_V51_INTERMEDIATE_SOURCE",
    )
    if source is None:
        pytest.skip("the intermediate v51 source is not present")
    release_root = tmp_path / "intermediate-v51"
    listing = _materialize_core_release(
        release_root,
        source=source,
        source_commit=_INTERMEDIATE_V51_SOURCE_COMMIT,
        expected_listing=_INTERMEDIATE_V51_LISTING_SHA,
    )
    assert listing == _INTERMEDIATE_V51_LISTING_SHA
    assert listing != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    await _assert_create_app_rejects_release(
        tmp_path,
        release_root,
        message="release manifest digest mismatch",
        assertion="create_app must reject fdf008f/35325c85",
    )


async def test_create_app_rejects_crossed_new_files_previous_source(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "crossed-previous-source"
    listing = _materialize_v51_release(release_root)
    assert listing == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    crossed = _rewrite_release_source_commit(
        release_root,
        _PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT,
    )
    assert crossed != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert crossed != _PREVIOUS_PRODUCTION_V51_LISTING_SHA
    await _assert_create_app_rejects_release(
        tmp_path,
        release_root,
        message="release manifest digest mismatch",
        assertion="create_app must reject new files paired with adfd7b6",
    )


async def test_create_app_rejects_crossed_new_files_intermediate_source(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "crossed-intermediate-source"
    listing = _materialize_v51_release(release_root)
    assert listing == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    crossed = _rewrite_release_source_commit(
        release_root,
        _INTERMEDIATE_V51_SOURCE_COMMIT,
    )
    assert crossed != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert crossed != _INTERMEDIATE_V51_LISTING_SHA
    await _assert_create_app_rejects_release(
        tmp_path,
        release_root,
        message="release manifest digest mismatch",
        assertion="create_app must reject new files paired with fdf008f",
    )


def test_filesystem_inspector_rejects_crossed_source_listing_pairs(
    tmp_path: Path,
) -> None:
    release_root = tmp_path / "admitted-release"
    listing = _materialize_v51_release(release_root)
    assert listing == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=_PREVIOUS_PRODUCTION_V51_LISTING_SHA,
            expected_release_name="mingli-master-portable-core",
            expected_source_commit=_ADMITTED_V51_SOURCE_COMMIT,
        ).inspect()
    with pytest.raises(RuntimeStartupError, match="release identity mismatch"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=_ADMITTED_V51_RELEASE_MANIFEST_SHA,
            expected_release_name="mingli-master-portable-core",
            expected_source_commit=_PREVIOUS_PRODUCTION_V51_SOURCE_COMMIT,
        ).inspect()
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=_INTERMEDIATE_V51_LISTING_SHA,
            expected_release_name="mingli-master-portable-core",
            expected_source_commit=_ADMITTED_V51_SOURCE_COMMIT,
        ).inspect()
    with pytest.raises(RuntimeStartupError, match="release identity mismatch"):
        FileSystemRuntimeReleaseInspector(
            release_root=release_root,
            expected_release_manifest_sha256=_ADMITTED_V51_RELEASE_MANIFEST_SHA,
            expected_release_name="mingli-master-portable-core",
            expected_source_commit=_INTERMEDIATE_V51_SOURCE_COMMIT,
        ).inspect()


async def test_configured_worker_admits_the_real_runtime_before_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readings = importlib.import_module("worker.readings")
    config = importlib.import_module("app.config")
    events: list[str] = []
    admitted_runtime = object()
    built_worker = object()

    class DatabaseFixture:
        def __init__(self) -> None:
            self.sessions = object()

        async def dispose(self) -> None:
            events.append("database-dispose")

    class GateFixture:
        runtime = admitted_runtime

        async def startup(self) -> None:
            events.append("runtime-startup")

    database = DatabaseFixture()
    settings = config.Settings(environment="test", runtime_adapter="worker-v2")

    def build_worker_fixture(**kwargs: Any) -> object:
        events.append("worker-build")
        assert kwargs["runtime"] is admitted_runtime
        return built_worker

    monkeypatch.setattr(readings, "get_settings", lambda: settings)
    monkeypatch.setattr(readings, "Database", lambda _url: database)
    monkeypatch.setattr(readings, "build_runtime_startup_gate", lambda _settings: GateFixture())
    monkeypatch.setattr(readings, "build_reading_worker", build_worker_fixture)

    async with readings.configured_reading_worker() as worker:
        assert worker is built_worker
        assert events == ["runtime-startup", "worker-build"]

    assert events == ["runtime-startup", "worker-build", "database-dispose"]


async def test_configured_worker_fails_closed_when_runtime_startup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readings = importlib.import_module("worker.readings")
    config = importlib.import_module("app.config")
    events: list[str] = []

    class DatabaseFixture:
        async def dispose(self) -> None:
            events.append("database-dispose")

    class GateFixture:
        runtime = object()

        async def startup(self) -> None:
            events.append("runtime-startup")
            raise RuntimeStartupError("describe admission failed")

    settings = config.Settings(environment="test", runtime_adapter="worker-v2")
    monkeypatch.setattr(readings, "get_settings", lambda: settings)
    monkeypatch.setattr(readings, "Database", lambda _url: DatabaseFixture())
    monkeypatch.setattr(readings, "build_runtime_startup_gate", lambda _settings: GateFixture())

    with pytest.raises(RuntimeStartupError, match="describe admission failed"):
        async with readings.configured_reading_worker():
            pytest.fail("Worker must not start after failed Runtime admission")

    assert events == ["runtime-startup", "database-dispose"]


def _core_listing_payload(source_commit: str) -> bytes:
    scripts = str(_REPO_ROOT / "core" / "mingli-master" / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import release_deploy as rd

    core = _REPO_ROOT / "core" / "mingli-master"
    manifest = rd.build_manifest(core, rd.tracked_release_files(core), source_commit)
    return (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _v51_listing_payload(source_commit: str) -> bytes:
    source = _discover_v51_source_root()
    if source is None:
        pytest.skip("the admitted v51 worker-v2 source is not present")
    scripts = str(source / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import release_deploy as rd

    manifest = rd.build_manifest(
        source,
        rd.tracked_release_files(source),
        source_commit,
    )
    return (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _materialize_locked_core_release(destination: Path) -> str:
    scripts = str(_REPO_ROOT / "core" / "mingli-master" / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import release_deploy as rd

    core = _REPO_ROOT / "core" / "mingli-master"
    files = rd.tracked_release_files(core)
    manifest = rd.build_manifest(core, files, _ADMITTED_V53_SOURCE_COMMIT)
    payload = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    listing = hashlib.sha256(payload).hexdigest()
    assert listing == _ADMITTED_V53_RELEASE_MANIFEST_SHA
    destination.mkdir(mode=0o700)
    for relative in manifest["files"]:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(core / relative, target)
        target.chmod(manifest["modes"][relative])
    manifest_path = destination / ".mingli-release-manifest.json"
    manifest_path.write_bytes(payload)
    manifest_path.chmod(0o600)
    for path in (destination, *destination.rglob("*")):
        if path.is_dir():
            path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o022)
    return listing


def test_factory_rejects_fake_adapter_and_keeps_one_shot_as_explicit_rollback(
    tmp_path: Path,
) -> None:
    from app.config import Settings

    launcher = tmp_path / "runtime-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    fake = Settings(
        runtime_adapter="fake",
        runtime_launcher_path=launcher,
        runtime_python_path=Path("/usr/bin/python3"),
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest="f" * 64,
        runtime_expected_capability_shape_sha256="a" * 64,
    )
    with pytest.raises(RuntimeStartupError, match="worker-v2"):
        build_runtime_startup_gate(fake)

    rollback = _v53_one_shot_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=Path("/usr/bin/python3"),
    )
    gate = build_runtime_startup_gate(rollback)
    assert gate.runtime.adapter_kind == "one-shot-process"


def test_factory_rejects_worker_identity_drift(tmp_path: Path) -> None:
    from app.config import Settings

    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    worker = release_root / _WORKER_RELATIVE
    worker.parent.mkdir(parents=True)
    worker.write_bytes(b"not-the-locked-runtime-worker\n")
    worker.chmod(0o644)
    launcher = tmp_path / "runtime-rollback-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    settings = Settings(
        environment="test",
        runtime_adapter="worker-v2",
        runtime_release_profile="v53-time-check",
        runtime_launcher_path=launcher,
        runtime_python_path=_dummy_runtime_python(tmp_path),
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=_ADMITTED_V53_DESCRIBE_DIGEST,
        runtime_expected_capability_shape_sha256=_ADMITTED_V53_CAPABILITY_SHAPE,
    )
    assert _sha256(worker) != _ADMITTED_V53_WORKER_SHA256
    with pytest.raises(RuntimeStartupError, match="worker digest"):
        build_runtime_startup_gate(settings)


def test_factory_rejects_v51_worker_identity_drift(tmp_path: Path) -> None:
    from app.config import Settings

    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    worker = release_root / _WORKER_RELATIVE
    worker.parent.mkdir(parents=True)
    worker.write_bytes(b"not-the-admitted-v51-runtime-worker\n")
    worker.chmod(0o644)
    launcher = tmp_path / "runtime-v51-fixture"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o700)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    settings = Settings(
        environment="test",
        runtime_adapter="worker-v2",
        runtime_release_profile="v51",
        runtime_launcher_path=launcher,
        runtime_python_path=_dummy_runtime_python(tmp_path),
        runtime_release_root=release_root,
        runtime_state_root=state_root,
        runtime_expected_manifest_digest=_ADMITTED_V51_DESCRIBE_DIGEST,
        runtime_expected_capability_shape_sha256=_ADMITTED_V51_CAPABILITY_SHAPE,
    )
    assert _sha256(worker) != _ADMITTED_V51_WORKER_SHA256
    with pytest.raises(RuntimeStartupError, match="worker digest"):
        build_runtime_startup_gate(settings)


async def test_create_app_rejects_head_reserialized_listing(tmp_path: Path) -> None:
    payload = _v51_listing_payload(_HEAD_RESERIALIZED_SOURCE_COMMIT)
    listing = hashlib.sha256(payload).hexdigest()
    admitted = hashlib.sha256(_v51_listing_payload(_ADMITTED_V51_SOURCE_COMMIT)).hexdigest()
    assert admitted == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert listing != _ADMITTED_V51_RELEASE_MANIFEST_SHA
    assert listing != _ADMITTED_V53_RELEASE_MANIFEST_SHA
    assert listing != _PREVIOUS_COMBINED_OVERLAY_LISTING_SHA
    release_root = tmp_path / "head-reserialized-release"
    release_root.mkdir(mode=0o700)
    (release_root / ".mingli-release-manifest.json").write_bytes(payload)
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    gate = build_runtime_startup_gate(settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        await gate.startup()

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match="release manifest digest mismatch"):
        async with application.router.lifespan_context(application):
            raise AssertionError("create_app must reject head-reserialized listing")


async def test_create_app_worker_crash_does_not_fallback_to_one_shot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    (release_root / ".mingli-release-manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    constructed: list[str] = []
    original_one_shot = OneShotMingliRuntimeAdapter.__init__

    def tracking_one_shot(
        self: OneShotMingliRuntimeAdapter,
        *args: object,
        **kwargs: object,
    ) -> None:
        constructed.append("one-shot")
        original_one_shot(self, *args, **kwargs)

    async def crash_start(self: WorkerV2MingliRuntimeAdapter) -> dict[str, object]:
        constructed.append("worker-start")
        raise RuntimeStartupError("Runtime worker READY is invalid")

    def admitted_inventory(self: FileSystemRuntimeReleaseInspector) -> RuntimeReleaseInventory:
        return RuntimeReleaseInventory(
            release_manifest_sha256=_ADMITTED_V51_RELEASE_MANIFEST_SHA,
            release_file_count=218,
            physical_file_count=219,
            provider_ids=V51_RELEASE_CAPABILITY_IDS,
            ready_provider_ids=V51_RELEASE_CAPABILITY_IDS,
            reference_pack_count=55,
            evidence_record_count=1328,
            runtime_closure_file_count=218,
        )

    monkeypatch.setattr(OneShotMingliRuntimeAdapter, "__init__", tracking_one_shot)
    monkeypatch.setattr(WorkerV2MingliRuntimeAdapter, "start", crash_start)
    monkeypatch.setattr(FileSystemRuntimeReleaseInspector, "inspect", admitted_inventory)

    gate = build_runtime_startup_gate(settings)
    assert gate.runtime.adapter_kind == "runtime-worker-v2"
    assert constructed == []
    with pytest.raises(RuntimeStartupError, match="READY is invalid"):
        await gate.startup()
    assert constructed == ["worker-start"]

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match="READY is invalid"):
        async with application.router.lifespan_context(application):
            raise AssertionError("create_app must not fallback after worker crash")
    assert "one-shot" not in constructed


async def test_create_app_v51_worker_crash_does_not_fallback_to_one_shot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_root = tmp_path / "release-root"
    release_root.mkdir(mode=0o700)
    (release_root / ".mingli-release-manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=_dummy_runtime_python(tmp_path),
    )
    constructed: list[str] = []
    original_one_shot = OneShotMingliRuntimeAdapter.__init__

    def tracking_one_shot(
        self: OneShotMingliRuntimeAdapter,
        *args: object,
        **kwargs: object,
    ) -> None:
        constructed.append("one-shot")
        original_one_shot(self, *args, **kwargs)

    async def crash_start(self: WorkerV2MingliRuntimeAdapter) -> dict[str, object]:
        constructed.append("worker-start")
        raise RuntimeStartupError("Runtime worker READY is invalid")

    def admitted_inventory(self: FileSystemRuntimeReleaseInspector) -> RuntimeReleaseInventory:
        return RuntimeReleaseInventory(
            release_manifest_sha256=_ADMITTED_V51_RELEASE_MANIFEST_SHA,
            release_file_count=218,
            physical_file_count=219,
            provider_ids=V51_RELEASE_CAPABILITY_IDS,
            ready_provider_ids=V51_RELEASE_CAPABILITY_IDS,
            reference_pack_count=55,
            evidence_record_count=1328,
            runtime_closure_file_count=218,
        )

    monkeypatch.setattr(OneShotMingliRuntimeAdapter, "__init__", tracking_one_shot)
    monkeypatch.setattr(WorkerV2MingliRuntimeAdapter, "start", crash_start)
    monkeypatch.setattr(FileSystemRuntimeReleaseInspector, "inspect", admitted_inventory)

    gate = build_runtime_startup_gate(settings)
    assert gate.runtime.adapter_kind == "runtime-worker-v2"
    assert constructed == []
    with pytest.raises(RuntimeStartupError, match="READY is invalid"):
        await gate.startup()
    assert constructed == ["worker-start"]

    from app.main import create_app

    application = create_app(settings=settings)
    with pytest.raises(RuntimeStartupError, match="READY is invalid"):
        async with application.router.lifespan_context(application):
            raise AssertionError("create_app must not fallback after v51 worker crash")
    assert "one-shot" not in constructed


async def test_create_app_worker_v2_ready_before_requests_and_five_product_cohort(
    tmp_path: Path,
    database: Any,
) -> None:
    runtime_python = _discover_runtime_python()
    if runtime_python is None:
        pytest.skip("the dedicated Mingli Runtime Python is not installed")
    runtime_python = _copy_clean_runtime_python(runtime_python, tmp_path / "runtime-venv")
    release_root = tmp_path / "locked-v51-release"
    listing = _materialize_v51_release(release_root)
    assert listing == _ADMITTED_V51_RELEASE_MANIFEST_SHA
    settings = _v51_worker_settings(
        tmp_path,
        release_root=release_root,
        runtime_python=runtime_python,
    ).model_copy(update={"reading_write_rate_limit": 200})

    main = importlib.import_module("app.main")
    readings_repository = importlib.import_module("app.readings.repository")
    envelope = importlib.import_module("app.security.envelope")
    profiles_api = importlib.import_module("test_profiles_api")
    create_app = main.create_app
    SqlReadingRepository = readings_repository.SqlReadingRepository
    EnvelopeCipher = envelope.EnvelopeCipher
    create_confirmed_profile = profiles_api.create_confirmed_profile
    create_guest = profiles_api.create_guest

    gate = build_runtime_startup_gate(settings)
    assert gate.runtime.adapter_kind == "runtime-worker-v2"
    application = create_app(settings=settings, database=database)
    runtime = None
    try:
        async with application.router.lifespan_context(application):
            runtime = application.state.chart_runtime
            assert runtime is not None
            assert runtime.adapter_kind == "runtime-worker-v2"
            ready = runtime.ready
            assert ready is not None
            assert ready["protocol"] == "mingli-runtime-worker-v2"
            assert ready["turn_terminal"] == "result-idle-v1"
            assert ready["listing_sha256"] == _ADMITTED_V51_RELEASE_MANIFEST_SHA
            assert ready["runtime_integrity_sha256"]
            boot_pid = ready["pid"]
            async with database.sessions() as session, session.begin():
                repository = SqlReadingRepository(
                    session,
                    EnvelopeCipher.from_settings(settings),
                )
                await repository.create_runtime_release(
                    name="mingli-master-portable-core",
                    version="5.1",
                    source_commit=_ADMITTED_V51_SOURCE_COMMIT,
                    release_manifest_digest=_ADMITTED_V51_RELEASE_MANIFEST_SHA,
                    protocol_version="mingli-portable-interface-v2",
                    describe_manifest_digest=_ADMITTED_V51_DESCRIBE_DIGEST,
                    image_digest=None,
                    production_ready=True,
                )
            async with AsyncClient(
                transport=ASGITransport(app=application),
                base_url="https://testserver",
            ) as client:
                headers = await create_guest(client)
                profile = await create_confirmed_profile(client, headers)
                profile_version_id = profile["profile_version_id"]
                event_datetime = "2026-08-14T10:00:00+08:00"
                cases = {
                    "ziwei": (
                        "/api/v1/readings/ziwei",
                        {
                            "profile_version_id": profile_version_id,
                            "dimension_ids": ["career"],
                        },
                        "ziwei-chart/v1",
                    ),
                    "bazi": (
                        "/api/v1/readings/preview",
                        {
                            "profile_version_id": profile_version_id,
                            "dimension_ids": ["career"],
                        },
                        "bazi-chart/v1",
                    ),
                    "liuyao": (
                        "/api/v1/readings/liuyao",
                        {
                            "cast": [6, 7, 8, 9, 7, 8],
                            "event_datetime": event_datetime,
                            "timezone": "Asia/Shanghai",
                            "location": "北京市朝阳区",
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
                            "location": "北京市朝阳区",
                            "dimension_ids": ["outcome", "state"],
                        },
                        "meihua-chart/v1",
                    ),
                    "daliuren": (
                        "/api/v1/readings/daliuren",
                        {
                            "event_datetime": event_datetime,
                            "timezone": "Asia/Shanghai",
                            "location": "北京市朝阳区",
                            "dimension_ids": ["outcome"],
                        },
                        "daliuren-chart/v1",
                    ),
                }
                ziwei_path, ziwei_payload, ziwei_schema = cases["ziwei"]
                ziwei_times: list[float] = []
                first_view = None
                for index in range(31):
                    started = time.perf_counter()
                    response = await client.post(
                        ziwei_path,
                        headers={
                            **headers,
                            "Idempotency-Key": f"worker-v2-ziwei-{index:02d}",
                        },
                        json=ziwei_payload,
                    )
                    elapsed = time.perf_counter() - started
                    assert response.status_code == 201, response.text
                    body = response.json()
                    assert body["status"] == "prepared"
                    assert body["view_model"]["schema_version"] == ziwei_schema
                    assert body["fast_path_timing"]["queue_wait_ms"] == 0
                    assert body["fast_path_timing"]["worker_pickup_ms"] == 0
                    assert elapsed < 1.0
                    stored = await client.get(
                        f"/api/v1/readings/{body['reading_version_id']}/result"
                    )
                    assert stored.status_code == 200
                    assert stored.json()["view_model"] == body["view_model"]
                    ziwei_times.append(elapsed)
                    if first_view is None:
                        first_view = body["view_model"]
                    else:
                        assert body["view_model"] == first_view
                assert len(ziwei_times) == 31
                for product, (path, payload, schema) in cases.items():
                    response = await client.post(
                        path,
                        headers={
                            **headers,
                            "Idempotency-Key": f"worker-v2-product-{product}",
                        },
                        json=payload,
                    )
                    assert response.status_code == 201, response.text
                    body = response.json()
                    assert body["status"] == "prepared"
                    assert body["view_model"]["schema_version"] == schema
                    assert body["fast_path_timing"]["queue_wait_ms"] == 0
                    assert body["fast_path_timing"]["worker_pickup_ms"] == 0
                    stored = await client.get(
                        f"/api/v1/readings/{body['reading_version_id']}/result"
                    )
                    assert stored.status_code == 200
                    assert stored.json()["view_model"] == body["view_model"]
                    assert stored.json()["status"] == "prepared"
            assert runtime.ready is not None
            assert runtime.ready["pid"] == boot_pid
    finally:
        close = getattr(runtime, "close", None)
        if callable(close):
            await close()
