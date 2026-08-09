import hashlib
import importlib
import json
import stat
import sys
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
        "runtime_adapter": "one-shot",
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
        release_file_count=217,
        provider_ids=V51_RELEASE_CAPABILITY_IDS,
        ready_provider_ids=V51_RELEASE_CAPABILITY_IDS,
        reference_pack_count=55,
        evidence_record_count=1328,
        runtime_closure_file_count=217,
    )


async def _fake_description() -> Described:
    result = await FakeMingliRuntimeAdapter().execute(Describe())
    assert isinstance(result, Described)
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_signed_release_fixture(root: Path) -> str:
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
    filler_count = 217 - len(existing) - 1
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
    assert len(files) == 217
    manifest = root / ".mingli-release-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "release": "fixture-release",
                "source_commit": "fixture-commit",
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
        timeout_seconds=1,
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
        release_file_count=217,
        provider_ids=V51_RELEASE_CAPABILITY_IDS,
        ready_provider_ids=V51_RELEASE_CAPABILITY_IDS,
        reference_pack_count=55,
        evidence_record_count=1328,
        runtime_closure_file_count=217,
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
        ("closure", "all 217"),
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
    settings = _production_settings()

    assert settings.runtime_adapter == "one-shot"
    assert settings.runtime_launcher_path == Path(
        "/opt/mingli-master/scripts/run_reading_transaction.sh"
    )
    assert (
        settings.runtime_expected_capability_shape_sha256
        == "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
    )


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
    settings = config.Settings(environment="test", runtime_adapter="one-shot")

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

    settings = config.Settings(environment="test", runtime_adapter="one-shot")
    monkeypatch.setattr(readings, "get_settings", lambda: settings)
    monkeypatch.setattr(readings, "Database", lambda _url: DatabaseFixture())
    monkeypatch.setattr(readings, "build_runtime_startup_gate", lambda _settings: GateFixture())

    with pytest.raises(RuntimeStartupError, match="describe admission failed"):
        async with readings.configured_reading_worker():
            pytest.fail("Worker must not start after failed Runtime admission")

    assert events == ["runtime-startup", "database-dispose"]
