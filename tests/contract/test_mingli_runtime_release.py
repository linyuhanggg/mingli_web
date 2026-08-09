#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "infra" / "mingli-runtime"
REPORT_PATH = RUNTIME_DIR / "release-5.1.json"
LOCK_PATH = RUNTIME_DIR / "requirements-linux-x86_64.lock"
SBOM_PATH = RUNTIME_DIR / "sbom.cdx.json"
VERIFY_PATH = RUNTIME_DIR / "verify_release.py"
DOCKERFILE_PATH = RUNTIME_DIR / "Dockerfile"
BUILD_CONTEXT_PATH = RUNTIME_DIR / "build_context.py"
AUDIT_PATH = RUNTIME_DIR / "audit_runtime.py"
LIMA_GATE_PATH = RUNTIME_DIR / "run_lima_gate.py"
PROVENANCE_PATH = RUNTIME_DIR / "dependency-provenance.json"

EXPECTED_PROVIDERS = {
    "bazi",
    "fengshui",
    "fortune",
    "liuren",
    "liuyao",
    "luming-nayin",
    "meihua",
    "physiognomy",
    "qimen",
    "selection",
    "taiyi",
    "xingming",
    "ziwei",
}
P0_PROVIDERS = {"bazi", "fortune", "liuyao"}
EXPECTED_RELEASE = {
    "name": "mingli-master-portable-core",
    "version": "5.1",
    "source_commit": "494ce0bba174a77800daf9b9c38ce9c9166d9a94",
    "release_manifest_file_count": 217,
    "release_manifest_sha256": (
        "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
    ),
    "skill_sha256": "ee43ae256f2a39c7bf0fde6714d5ff87af2b654cae2283ee0b6d07566502c378",
    "protocol_version": "mingli-portable-interface-v2",
    "describe_digest": "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342",
}


def load_verifier() -> ModuleType:
    assert VERIFY_PATH.is_file(), "Linux Runtime verifier is absent; Gate stays RED"
    spec = importlib.util.spec_from_file_location(
        "mingli_runtime_verifier", VERIFY_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module(path: Path, name: str) -> ModuleType:
    assert path.is_file(), f"required Linux Runtime tool is absent: {path.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_lima_gate() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        return load_module(RUNTIME_DIR / "run_lima_gate.py", "mingli_lima_gate")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def load_audit_runtime() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        return load_module(AUDIT_PATH, "mingli_runtime_audit")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def test_linux_watchdogs_cover_qemu_matrix_and_regression_budgets() -> None:
    audit = load_audit_runtime()
    gate = load_lima_gate()

    assert audit.PROVIDER_MATRIX_TIMEOUT_SECONDS == 10_800
    assert audit.RELEASE_REGRESSION_TIMEOUT_SECONDS == 10_800
    assert gate.PROVIDER_MATRIX_TIMEOUT_SECONDS == (
        audit.PROVIDER_MATRIX_TIMEOUT_SECONDS
    )
    assert gate.PRODUCTION_AUDIT_TIMEOUT_SECONDS == 32_400
    assert gate.PRODUCTION_AUDIT_TIMEOUT_SECONDS > (
        2 * gate.PROVIDER_MATRIX_TIMEOUT_SECONDS
    )
    assert gate.FINALIZER_TIMEOUT_SECONDS == 21_600
    assert gate.FINALIZER_TIMEOUT_SECONDS > (
        audit.RELEASE_REGRESSION_TIMEOUT_SECONDS + 3_000
    )
    source = inspect.getsource(audit.run_production_audit)
    assert source.count("timeout=PROVIDER_MATRIX_TIMEOUT_SECONDS") == 2
    assert "timeout=RELEASE_REGRESSION_TIMEOUT_SECONDS" in inspect.getsource(
        audit.finalize_audit
    )
    controller = inspect.getsource(gate.run_gate)
    assert "timeout=PRODUCTION_AUDIT_TIMEOUT_SECONDS" in controller
    assert "timeout=FINALIZER_TIMEOUT_SECONDS" in controller


def test_command_evidence_records_elapsed_and_fixed_timeout_budget(
    tmp_path: Path,
) -> None:
    audit = load_audit_runtime()
    recorder = audit.CommandRecorder(tmp_path, "sha256:" + "1" * 64)

    record = recorder.run(
        "budget-proof",
        (sys.executable, "-c", "pass"),
        cwd=tmp_path,
        environment=os.environ,
        timeout=7,
    )

    assert record["timeout_seconds"] == 7
    assert isinstance(record["elapsed_seconds"], float)
    assert 0 <= record["elapsed_seconds"] <= record["timeout_seconds"]

    verifier = load_verifier()
    verifier._require_command_budget(
        record,
        expected_timeout_seconds=7,
        label="budget proof",
    )
    for field, value in (
        ("timeout_seconds", 6),
        ("elapsed_seconds", 8.0),
    ):
        tampered = {**record, field: value}
        with pytest.raises(verifier.ReleaseVerificationError):
            verifier._require_command_budget(
                tampered,
                expected_timeout_seconds=7,
                label="budget proof",
            )


def test_launcher_containers_use_ephemeral_writable_overlay(tmp_path: Path) -> None:
    gate = load_lima_gate()
    drill = gate.BackupRestoreDrill(
        object(),
        "sha256:" + "1" * 64,
        {"source": "runtime-state"},
        tmp_path,
    )

    runtime_argv = drill._runtime_argv("runtime-state")
    assert "--rm" in runtime_argv
    assert "--network=none" in runtime_argv
    assert "--read-only" not in runtime_argv
    gate._require_writable_runtime_overlay(runtime_argv, "runtime")

    with pytest.raises(
        gate.GateError,
        match="requires a writable ephemeral container overlay",
    ):
        gate._require_writable_runtime_overlay(
            ["run", "--rm", "--network=none", "--read-only"],
            "runtime",
        )

    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    assert controller.count("_require_writable_runtime_overlay(") >= 4


def test_backup_drill_redacts_pending_token_and_replays_promoted_prepare(
    tmp_path: Path,
) -> None:
    gate = load_lima_gate()
    raw_token = "pending-token-must-never-enter-evidence"

    class FakeVM:
        @staticmethod
        def docker(
            argv: list[str],
            *,
            input_bytes: bytes,
            timeout: int,
        ) -> subprocess.CompletedProcess[bytes]:
            del input_bytes, timeout
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=gate.json_bytes(
                    {
                        "kind": "stopped",
                        "public_copy": "请补充出生资料。",
                        "reason": "need_input",
                        "state_token": raw_token,
                    }
                ),
                stderr=b"",
            )

    drill = gate.BackupRestoreDrill(
        FakeVM(),
        "sha256:" + "1" * 64,
        {"source": "runtime-state"},
        tmp_path,
    )
    _, sanitized = drill.runtime(
        "source-pending-prepare",
        "runtime-state",
        {"kind": "prepare"},
        expected_kind="stopped",
    )

    assert sanitized["kind"] == "stopped"
    assert sanitized["reason"] == "need_input"
    assert (
        sanitized["token_fingerprint"]
        == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    )
    assert raw_token not in "".join(
        path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json")
    )

    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    assert '"source-pending-prepare"' in controller
    assert '"prepared-token-replay"' in controller
    assert "replay_command = dict(source_prepare_command)" in controller


def load_report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), (
        "audited Linux release report is absent; Gate stays RED"
    )
    value = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_linux_release_evidence_is_complete_and_fail_closed() -> None:
    verifier = load_verifier()
    report = load_report()

    verifier.validate_audit_report(report, artifacts_root=RUNTIME_DIR)

    assert report["release"] == EXPECTED_RELEASE
    target = report["target"]
    assert target["os"] == "linux"
    assert target["architecture"] == "x86_64"
    assert target["python_version"] == "3.14.6"
    assert target["release_root"] == "/opt/mingli-master"
    assert target["python_path"] == "/opt/mingli-runtime/venv/bin/python"
    assert target["state_root"] == "/var/lib/mingli"
    assert target["uid"] > 0
    assert target["git_version"] == "2.39.5"

    inventory = report["inventory"]
    assert set(inventory["provider_ids"]) == EXPECTED_PROVIDERS
    assert inventory["provider_count"] == 13
    assert set(inventory["readiness"]) == EXPECTED_PROVIDERS
    assert all(inventory["readiness"].values())
    assert inventory["reference_pack_count"] == 55
    assert inventory["evidence_index_count"] == 1328
    assert inventory["evidence_rule_ids_unique"] is True
    assert inventory["runtime_closure_verified"] is True

    assert set(report["product_policy"]["p0_provider_ids"]) == P0_PROVIDERS
    assert set(report["characterization"]) == EXPECTED_PROVIDERS
    assert all(
        item["status"] == "passed" for item in report["characterization"].values()
    )
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", item["output_sha256"])
        for item in report["characterization"].values()
    )
    assert report["release_regression"]["status"] == "passed"
    assert report["release_regression"]["test_count"] == 1584
    assert report["p0_trajectories"]["status"] == "passed"
    assert report["probes"]["status"] == "passed"
    assert report["backup_restore"]["status"] == "passed"
    assert report["backup_restore"]["prepared_token_restored"] is True
    assert report["backup_restore"]["accepted_token_replayed"] is True

    artifact = report["artifact"]
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["image_digest"])
    assert re.fullmatch(r"[0-9a-f]{64}", artifact["sbom_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", artifact["runtime_integrity_sha256"])
    assert SBOM_PATH.is_file()

    audit = report["audit"]
    assert audit["generator"] == "/opt/mingli-runtime/audit_runtime.py"
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", audit["image_id"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", audit["completed_at"])
    assert audit["commands"]
    for command in audit["commands"]:
        assert isinstance(command["argv"], list) and command["argv"]
        assert command["exit_code"] == 0
        assert re.fullmatch(r"[0-9a-f]{64}", command["stdout_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", command["stderr_sha256"])

    dependencies = report["dependencies"]
    assert dependencies["pyyaml"] == {
        "license": "MIT",
        "version": "6.0.3",
        "filename": (
            "pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64."
            "manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"
        ),
        "sha256": "c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5",
    }
    assert dependencies["sxtwl"]["version"] == "2.0.7"
    assert dependencies["sxtwl"]["sdist_sha256"] == (
        "38b24472389f7f6f3521c2c99e4b5e86c0184c7d6eb02e5409c239d21f0a6512"
    )
    assert dependencies["sxtwl"]["wheel_filename"] == (
        "sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl"
    )
    assert dependencies["sxtwl"]["wheel_sha256"] == (
        "90595ae5a5e311ae019170784c56bff52c176942347836c904e7c8af8d7b5c22"
    )


def test_three_provider_slim_report_is_rejected() -> None:
    verifier = load_verifier()
    slim = copy.deepcopy(load_report())
    slim["inventory"]["provider_ids"] = sorted(P0_PROVIDERS)
    slim["inventory"]["provider_count"] = 3
    slim["inventory"]["readiness"] = {provider: True for provider in P0_PROVIDERS}
    slim["characterization"] = {
        provider: slim["characterization"][provider] for provider in P0_PROVIDERS
    }

    with pytest.raises(verifier.ReleaseVerificationError, match="13 Provider"):
        verifier.validate_audit_report(slim, artifacts_root=RUNTIME_DIR)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda report: report["artifact"].__setitem__("sbom_sha256", "0" * 64),
            "SBOM",
        ),
        (
            lambda report: report["inventory"].__setitem__("evidence_index_count", 1),
            "1328",
        ),
        (
            lambda report: report["characterization"]["bazi"].__setitem__(
                "output_sha256", "0" * 64
            ),
            "output digest",
        ),
        (
            lambda report: report["release_regression"].__setitem__("test_count", 1),
            "1584",
        ),
        (
            lambda report: report["dependencies"]["libatomic1"].__setitem__(
                "sha256", "0" * 64
            ),
            "libatomic",
        ),
        (
            lambda report: report["dependencies"]["git"]["build_config"].__setitem__(
                "sha1_backend", "unsafe"
            ),
            "dependencies",
        ),
    ],
)
def test_verifier_recomputes_evidence_instead_of_trusting_passed_status(
    mutation,
    message: str,
) -> None:  # type: ignore[no-untyped-def]
    verifier = load_verifier()
    tampered = copy.deepcopy(load_report())
    mutation(tampered)

    with pytest.raises(verifier.ReleaseVerificationError, match=message):
        verifier.validate_audit_report(tampered, artifacts_root=RUNTIME_DIR)


def test_release_regression_is_executed_in_the_final_artifact() -> None:
    verifier = load_verifier()
    baseline = copy.deepcopy(load_report())
    artifact_digest = baseline["artifact"]["image_digest"]
    commands = {item["id"]: item for item in baseline["audit"]["commands"]}

    assert baseline["audit"]["image_id"] == artifact_digest
    assert baseline["audit"]["audit_image_id"] == artifact_digest
    assert baseline["release_regression"]["executed_in_image_id"] == artifact_digest
    assert commands["release-regression"]["executed_in_image_id"] == artifact_digest

    report = copy.deepcopy(baseline)
    report["release_regression"]["executed_in_image_id"] = "sha256:" + "0" * 64
    with pytest.raises(
        verifier.ReleaseVerificationError,
        match="final production image",
    ):
        verifier.validate_audit_report(report, artifacts_root=RUNTIME_DIR)

    report = copy.deepcopy(baseline)
    report["audit"]["audit_image_id"] = "sha256:" + "1" * 64
    with pytest.raises(
        verifier.ReleaseVerificationError,
        match="same OCI config digest",
    ):
        verifier.validate_audit_report(report, artifacts_root=RUNTIME_DIR)

    report = copy.deepcopy(baseline)
    next(
        item
        for item in report["audit"]["commands"]
        if item["id"] == "release-regression"
    )["executed_in_image_id"] = "sha256:" + "2" * 64
    with pytest.raises(
        verifier.ReleaseVerificationError,
        match="command image identity mismatch",
    ):
        verifier.validate_audit_report(report, artifacts_root=RUNTIME_DIR)


def test_linux_lock_and_image_are_immutable_and_arch_specific() -> None:
    assert LOCK_PATH.is_file(), "Linux x86_64 dependency lock is absent; Gate stays RED"
    lock = LOCK_PATH.read_text(encoding="utf-8")
    for requirement in (
        "PyYAML==6.0.3",
        "sxtwl==2.0.7",
        "astronomy-engine==2.1.19",
        "cnlunar==0.2.4",
    ):
        assert requirement in lock
    assert lock.count("--hash=sha256:") >= 4
    assert "c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5" in lock
    assert "90595ae5a5e311ae019170784c56bff52c176942347836c904e7c8af8d7b5c22" in lock
    assert "cp314-cp314-manylinux2014_x86_64" in lock
    assert "cp314-cp314-linux_x86_64" in lock
    assert "macosx" not in lock.lower()
    assert "aarch64" not in lock.lower()

    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "ARG PYTHON_IMAGE" not in dockerfile
    external_bases = re.findall(
        r"^FROM\s+(python:3\.14\.6-slim-bookworm@sha256:[0-9a-f]{64})\s+AS\s+\S+",
        dockerfile,
        re.MULTILINE,
    )
    assert len(external_bases) == 4
    assert len(set(external_bases)) == 1
    assert external_bases[0].endswith(
        "ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4"
    )
    assert "FROM production AS audit" in dockerfile
    assert "FROM production AS final" in dockerfile
    assert "python -m venv --copies /opt/mingli-runtime/build-venv" in dockerfile
    assert "python -m venv --copies /opt/mingli-runtime/venv" in dockerfile
    assert "python -m venv /opt/mingli-runtime/venv" not in dockerfile
    assert "test ! -L /opt/mingli-runtime/venv/bin/python" in dockerfile
    production_stage = dockerfile.split(" AS production", 1)[1].split(
        "FROM production AS audit", 1
    )[0]
    assert "apt-get install" not in production_stage
    assert "/usr/sbin/groupadd --gid ${RUNTIME_GID} mingli" in production_stage
    assert "/usr/sbin/useradd --uid ${RUNTIME_UID}" in production_stage
    assert "apt-get install libatomic1" not in production_stage
    assert re.search(
        r"env\s+PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        r"\s+\\\s+/usr/bin/dpkg\s+--install",
        production_stage,
    )
    assert (
        "ADD --checksum=sha256:"
        "fbd4e154a6b444229ea002cc209df099209c0adc09102e5fd21239a3d2b55e2d"
    ) in production_stage
    assert "libatomic1_12.2.0-14+deb12u1_amd64.deb" in production_stage
    assert "snapshot.debian.org/archive/debian/20250501T000000Z" in production_stage
    assert "107ab9f7661a1c47cddfb5cd1def99ec537a50a9a537fbe38cdde1b34b8ba280" in (
        production_stage
    )
    assert "apt-get install -y --no-install-recommends git" not in dockerfile
    assert "for lane in a b; do" in dockerfile
    assert "sxtwl-source-${lane}" in dockerfile
    assert "sxtwl-source /opt/mingli-runtime/sxtwl-source" not in dockerfile
    assert "&& rm -rf build" not in dockerfile
    assert "CC=g++ CXX=g++" in dockerfile
    assert "import _sxtwl,sxtwl" in dockerfile
    assert "sxtwl.fromSolar(2000,1,1)" in dockerfile
    assert "BLK_SHA1" not in dockerfile
    assert dockerfile.count("BLK_SHA256=YesPlease") == 2
    assert "SHA1DCInit" in dockerfile
    assert "blk_SHA256_Init" in dockerfile
    assert "NO_OPENSSL=YesPlease" in dockerfile
    assert "git-2.39.5.tar.gz" in dockerfile
    assert "ca0ec03fb2696f552f37135a56a0242fa062bd350cb243dc4a15c86f1cafbc99" in (
        dockerfile
    )
    assert "/opt/git/bin/git" in dockerfile
    audit_stage = dockerfile.split("FROM production AS audit", 1)[1].split(
        "FROM production AS final", 1
    )[0]
    assert "apt-get" not in audit_stage
    assert "RUN" not in audit_stage
    assert dockerfile.index("COPY verify_release.py") < dockerfile.index(
        "COPY release/ /opt/mingli-master/"
    )
    assert "--release-only" in dockerfile
    assert "/opt/mingli-master" in dockerfile
    assert "/opt/mingli-runtime/venv/bin/python" in dockerfile
    assert "/var/lib/mingli" in dockerfile
    assert "MINGLI_PYTHON=/opt/mingli-runtime/venv/bin/python" in dockerfile
    assert "MINGLI_STORE_ROOT=/var/lib/mingli" in dockerfile
    assert re.search(r"^USER\s+[1-9][0-9]*", dockerfile, re.MULTILINE)

    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    assert provenance["base_image"]["linux_amd64_manifest_digest"] == (
        "sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4"
    )
    assert provenance["node"] == {
        "filename": "node-v26.3.0-linux-x64.tar.gz",
        "license": "MIT",
        "sha256": "a6e65cc653e40c1653b77742f9185dbce3ff1f99fa2746d211bddb53530ef206",
        "source_url": "https://nodejs.org/dist/v26.3.0/node-v26.3.0-linux-x64.tar.gz",
        "version": "26.3.0",
    }
    assert provenance["node"]["sha256"] in dockerfile
    assert provenance["system_runtime"]["libatomic1"] == {
        "architecture": "amd64",
        "fetch_url": (
            "https://snapshot.debian.org/archive/debian/20250501T000000Z/"
            "pool/main/g/gcc-12/libatomic1_12.2.0-14+deb12u1_amd64.deb"
        ),
        "filename": "libatomic1_12.2.0-14+deb12u1_amd64.deb",
        "installed_path": "/usr/lib/x86_64-linux-gnu/libatomic.so.1.2.0",
        "installed_sha256": (
            "107ab9f7661a1c47cddfb5cd1def99ec537a50a9a537fbe38cdde1b34b8ba280"
        ),
        "license": "GPL-3.0-or-later WITH GCC-exception-3.1",
        "origin_url": (
            "https://deb.debian.org/debian/pool/main/g/gcc-12/"
            "libatomic1_12.2.0-14+deb12u1_amd64.deb"
        ),
        "package": "libatomic1",
        "sha256": "fbd4e154a6b444229ea002cc209df099209c0adc09102e5fd21239a3d2b55e2d",
        "soname_path": "/usr/lib/x86_64-linux-gnu/libatomic.so.1",
        "soname_target": "libatomic.so.1.2.0",
        "snapshot_timestamp": "20250501T000000Z",
        "version": "12.2.0-14+deb12u1",
    }
    git = provenance["git"]
    assert git["version"] == "2.39.5"
    assert git["source_url"] == (
        "https://www.kernel.org/pub/software/scm/git/git-2.39.5.tar.gz"
    )
    assert git["source_sha256"] == (
        "ca0ec03fb2696f552f37135a56a0242fa062bd350cb243dc4a15c86f1cafbc99"
    )
    assert git["license"] == "GPL-2.0-only"
    assert git["license_sha256"] == (
        "5b2198d1645f767585e8a88ac0499b04472164c0d2da22e75ecf97ef443ab32e"
    )
    assert git["build_config"]["sha1_backend"] == "sha1dc-built-in"
    assert git["build_config"]["sha256_backend"] == "block-built-in"
    assert git["build_config"]["install_link_strategy"] == "relative-symlinks"
    assert "BLK_SHA256=YesPlease" in git["build_config"]["make_flags"]
    assert "INSTALL_SYMLINKS=YesPlease" in git["build_config"]["make_flags"]
    assert "NO_INSTALL_HARDLINKS=YesPlease" not in dockerfile
    assert re.fullmatch(r"[0-9a-f]{64}", git["installed_binary_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", git["installed_tree_sha256"])
    assert git["installed_tree_entry_count"] == 224
    assert git["installed_tree_regular_file_count"] == 70
    assert git["installed_tree_regular_file_bytes"] == 17_677_827
    assert git["installed_tree_symlink_count"] == 144
    assert git["installed_tree_symlink_target_bytes"] == 1_861
    assert git["installed_tree_content_bytes"] == 17_679_688


def test_build_context_projects_only_the_signed_manifest(tmp_path: Path) -> None:
    projector = load_module(BUILD_CONTEXT_PATH, "mingli_runtime_build_context")
    source = tmp_path / "source"
    source.mkdir()
    payload = source / "SKILL.md"
    payload.write_text("signed bytes\n", encoding="utf-8")
    payload.chmod(0o644)
    source_commit = "1" * 40
    manifest = {
        "files": {"SKILL.md": hashlib.sha256(payload.read_bytes()).hexdigest()},
        "modes": {"SKILL.md": 0o644},
        "release": "mingli-master-portable-core",
        "schema_version": 3,
        "source_commit": source_commit,
    }
    manifest_path = source / ".mingli-release-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (source / "local-only.txt").write_text("must not ship\n", encoding="utf-8")
    destination = tmp_path / "context"

    projector.build_context(
        source,
        destination,
        expected_manifest_sha256=manifest_sha256,
        expected_source_commit=source_commit,
        expected_file_count=1,
    )

    projected = destination / "release"
    assert {path.name for path in projected.iterdir()} == {
        ".mingli-release-manifest.json",
        "SKILL.md",
    }
    assert stat.S_IMODE((projected / "SKILL.md").stat().st_mode) == 0o644
    projector.verify_release_tree(
        projected,
        expected_manifest_sha256=manifest_sha256,
        expected_source_commit=source_commit,
        expected_file_count=1,
        reject_extras=True,
    )
    (projected / "SKILL.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(projector.ProjectionError, match="SHA-256 mismatch"):
        projector.verify_release_tree(
            projected,
            expected_manifest_sha256=manifest_sha256,
            expected_source_commit=source_commit,
            expected_file_count=1,
            reject_extras=True,
        )


def test_runtime_tree_digest_rejects_a_symlink_root(tmp_path: Path) -> None:
    verifier = load_verifier()
    target = tmp_path / "target"
    target.mkdir()
    (target / "payload").write_text("admitted bytes\n", encoding="utf-8")
    link = tmp_path / "root-link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(verifier.ReleaseVerificationError, match="root is a symlink"):
        verifier.runtime_tree_digest(link)


def test_evidence_conflict_reference_requires_a_signed_index_entry(
    tmp_path: Path,
) -> None:
    verifier = load_verifier()
    rules = tmp_path / "rules.md"
    quotes = tmp_path / "quote-index.md"
    rules.write_text(
        "# Rules\n\n## RULE-001 Substantive rule\n\nMentions GHOST-999 only in prose.\n",
        encoding="utf-8",
    )
    quotes.write_text(
        "# Quote Index\n\n| id | quote |\n|---|---|\n| QUOTE-001 | signed anchor |\n",
        encoding="utf-8",
    )
    local_ids = verifier._signed_markdown_index_ids(
        rules,
        "fixture rules",
    ) | verifier._signed_markdown_index_ids(
        quotes,
        "fixture quote index",
    )
    by_pack = {"known/pack": local_ids}

    assert verifier._evidence_reference_is_closed(
        "known/pack#RULE-001",
        set(),
        by_pack,
    )
    assert verifier._evidence_reference_is_closed(
        "known/pack#QUOTE-001",
        set(),
        by_pack,
    )
    assert not verifier._evidence_reference_is_closed(
        "known/pack#GHOST-999",
        set(),
        by_pack,
    )
    assert not verifier._evidence_reference_is_closed(
        "unknown/pack#QUOTE-001",
        set(),
        by_pack,
    )


def test_audit_tar_extractor_handles_root_member_and_requires_empty_target(
    tmp_path: Path,
) -> None:
    gate = load_lima_gate()
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as archive:
        root = tarfile.TarInfo(".")
        root.type = tarfile.DIRTYPE
        archive.addfile(root)
        content = b"verified evidence\n"
        item = tarfile.TarInfo("./evidence/result.txt")
        item.size = len(content)
        archive.addfile(item, io.BytesIO(content))

    destination = tmp_path / "output"
    destination.mkdir()
    gate._extract_safe_tar(payload.getvalue(), destination)
    assert (destination / "evidence/result.txt").read_bytes() == content

    with pytest.raises(gate.GateError, match="start empty"):
        gate._extract_safe_tar(payload.getvalue(), destination)
    with pytest.raises(gate.GateError, match="start empty"):
        gate._extract_safe_tar(payload.getvalue(), tmp_path / "missing")


def test_image_audit_entry_is_present_and_non_agentic() -> None:
    audit = AUDIT_PATH.read_text(encoding="utf-8")
    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    assert "/audit-source/scripts/run_test_suite.py" not in audit
    assert "run_test_suite.py" in audit
    assert "EXPECTED_TEST_COUNT" in audit
    assert "--emit-characterization" in audit
    assert "--emit-runtime-probes" in audit
    assert "--production-audit" in audit
    assert "--finalize-audit" in audit
    assert "production-tree-identity" in audit
    assert "audit-tree-identity" in audit
    assert "production-native-linkage" in audit
    assert "audit-native-linkage" in audit
    assert "--emit-native-linkage" in audit
    assert "--production-audit" in controller
    assert "--finalize-audit" in controller
    assert "production_output" in controller
    assert "production_state" in controller
    assert 'vm.docker(["tag", production_tag, audit_tag])' in controller
    assert "audit_image_id != image_id" in controller
    assert "audit_image_id != image_id" in audit
    for forbidden in ("langchain", "agent.run", "tools=", "function_call"):
        assert forbidden not in audit.lower()


def test_timeout_probe_uses_fixed_interpreter_on_noexec_tmpfs(tmp_path: Path) -> None:
    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    module = load_audit_runtime()
    source = inspect.getsource(module._probe_launcher_timeout)
    release_root = tmp_path / "release"
    scripts = release_root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "run_reading_transaction.sh").write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        'skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\n'
        'exec "$MINGLI_PYTHON" -I -S -B '
        '"$skill_dir/scripts/runtime_launcher.py"\n',
        encoding="utf-8",
    )

    assert "/tmp:rw,noexec,nosuid,nodev" in controller
    assert 'hanging_script = scripts / "runtime_launcher.py"' in source
    assert "hanging_script.chmod(0o600)" in source
    assert 'command = ["/bin/sh", str(probe_launcher)]' in source
    assert '"MINGLI_PYTHON": str(runtime_python)' in source
    assert "shutil.copyfile(source_launcher, probe_launcher)" in source
    assert source.count("verify_release.sha256_file(") == 2
    assert module._probe_launcher_timeout(
        tmp_path,
        release_root=release_root,
        runtime_python=Path(sys.executable),
        timeout_seconds=0.2,
    )


def test_backup_drill_distinguishes_replay_from_true_followup() -> None:
    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    verifier = VERIFY_PATH.read_text(encoding="utf-8")

    for required in (
        "source-pending-prepare",
        "prepared-token-replay",
        "prepared-restored-complete",
        "accepted-followup-prepare",
        "accepted-followup-complete",
        "accepted-followup-token-record",
    ):
        assert required in controller
        assert required in verifier
    assert '"prepared-followup"' not in controller
    assert '"prepared-followup"' not in verifier

    module = load_verifier()
    assert set(module.EXPECTED_BACKUP_FLAGS) == {
        "accepted_followup_created",
        "accepted_token_replayed",
        "complete_public_copy_byte_identical",
        "followup_version_advanced",
        "prepared_replay_byte_identical",
        "prepared_restored_completed",
        "prepared_token_restored",
    }
    assert "verify_release.EXPECTED_BACKUP_FLAGS" in AUDIT_PATH.read_text(
        encoding="utf-8"
    )


def test_backup_restore_validates_describe_and_state_root_identity(
    tmp_path: Path,
) -> None:
    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    verifier = VERIFY_PATH.read_text(encoding="utf-8")
    readme = (RUNTIME_DIR / "README.md").read_text(encoding="utf-8")
    audit = load_audit_runtime()

    tmp_path.chmod(0o700)
    identity = audit._state_root_identity(tmp_path)
    assert identity == {
        "gid": os.getgid(),
        "mode": 0o700,
        "path": str(tmp_path.resolve()),
        "schema_version": "mingli-state-root-identity-v1",
        "st_dev": tmp_path.stat().st_dev,
        "st_ino": tmp_path.stat().st_ino,
        "uid": os.getuid(),
    }
    for command_id in (
        "source-describe",
        "prepared-restore-describe",
        "accepted-restore-describe",
        "source-state-root-identity",
        "prepared-restore-state-root-identity",
        "accepted-restore-state-root-identity",
    ):
        assert command_id in controller
        assert command_id in verifier
    for required in (
        "protocol_version",
        "manifest_digest",
        "EXPECTED_PROVIDERS",
        "st_dev",
        "st_ino",
        "10001:10001",
        "0700",
    ):
        assert required in verifier or required in readme
    assert "device and inode values may change" in readme


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("describe", "manifest digest"),
        ("mode", "state-root invariant"),
        ("identity_pair", "filesystem identity constraints"),
        ("binding", "binding failed"),
    ],
)
def test_backup_restore_machine_evidence_tamper_is_rejected(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    verifier = load_verifier()
    report = copy.deepcopy(load_report())
    artifacts = tmp_path / "artifacts"
    shutil.copytree(RUNTIME_DIR, artifacts)
    backup_path = artifacts / report["evidence"]["backup_restore_path"]
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    commands = {item["id"]: item for item in backup["commands"]}

    def rewrite(
        command_id: str, value: dict[str, Any], binding: dict[str, Any]
    ) -> None:
        payload = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        command = commands[command_id]
        (artifacts / command["stdout_path"]).write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        command["stdout_sha256"] = digest
        binding["sha256"] = digest

    environment = backup["restore_environment"]
    if mutation == "describe":
        binding = environment["describes"]["source"]
        value = json.loads((artifacts / binding["path"]).read_text(encoding="utf-8"))
        value["manifest_digest"] = "0" * 64
        rewrite("source-describe", value, binding)
    elif mutation == "mode":
        binding = environment["state_roots"]["prepared_restore"]
        value = json.loads((artifacts / binding["path"]).read_text(encoding="utf-8"))
        value["mode"] = 0o755
        rewrite("prepared-restore-state-root-identity", value, binding)
    elif mutation == "identity_pair":
        source_binding = environment["state_roots"]["source"]
        source = json.loads(
            (artifacts / source_binding["path"]).read_text(encoding="utf-8")
        )
        binding = environment["state_roots"]["accepted_restore"]
        value = json.loads((artifacts / binding["path"]).read_text(encoding="utf-8"))
        value["st_dev"] = source["st_dev"]
        value["st_ino"] = source["st_ino"]
        rewrite("accepted-restore-state-root-identity", value, binding)
    else:
        environment["describes"]["source"]["sha256"] = "0" * 64

    backup_payload = (
        json.dumps(backup, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    backup_path.write_bytes(backup_payload)
    report["evidence"]["backup_restore_sha256"] = hashlib.sha256(
        backup_payload
    ).hexdigest()

    with pytest.raises(verifier.ReleaseVerificationError, match=message):
        verifier.validate_audit_report(report, artifacts_root=artifacts)


def test_native_linkage_identity_covers_all_runtime_entrypoints() -> None:
    verifier = VERIFY_PATH.read_text(encoding="utf-8")
    audit = AUDIT_PATH.read_text(encoding="utf-8")

    for target in ("git", "node", "python", "sxtwl", "yaml_c_extension"):
        assert f'"{target}"' in verifier
    for command_id in ("production-native-linkage", "audit-native-linkage"):
        assert command_id in verifier
        assert command_id in audit
    assert "inspect_native_linkage" in verifier
    assert "EXPECTED_SXTWL_LINKAGE" in verifier
    assert '"libstdc++.so.6"' in verifier
    assert "sxtwl.fromSolar(2000,1,1)" in verifier
    assert "importlib.util.find_spec" not in verifier
    assert "runtime_native_linkage_identity" in verifier
    assert "runtime_native_linkage_identity" in audit
    assert '"git"' in verifier
    assert "git-smoke" in verifier
    assert "git-smoke" in audit


def test_git_smoke_golden_is_recomputed_and_tamper_rejected() -> None:
    verifier = load_module(VERIFY_PATH, "mingli_runtime_git_smoke_verifier")
    payload = {
        "archive_sha256": (
            "f063d200b64075f2386bfb49351ce97a124b678b550dea39e3949778c446318d"
        ),
        "commit_sha1": "1962116c06237409f15a709948202c12845a446c",
        "exec_path": "/opt/git/libexec/git-core",
        "fixture": {
            "author_date": "2000-01-01T00:00:00Z",
            "author_email": "gate@mingli.invalid",
            "author_name": "Mingli Linux Gate",
            "commit_message": "Mingli V5.1 Git smoke fixture",
            "content_sha256": (
                "571e15a900174642b58c030370d12fff0558d8354ebc7a3ac4fefb90e4671086"
            ),
            "filename": "tracked.txt",
        },
        "ls_files_row": (
            "100644 72556c76839cfdc4f5bd71b141f985a3423e3e3d 0\ttracked.txt"
        ),
        "ls_tree_row": (
            "100644 blob 72556c76839cfdc4f5bd71b141f985a3423e3e3d\ttracked.txt"
        ),
        "operations": [
            "version",
            "init",
            "config-user-name",
            "config-user-email",
            "config-gc-auto",
            "config-maintenance-auto",
            "add",
            "commit",
            "status",
            "ls-files",
            "ls-tree",
            "rev-parse-commit",
            "rev-parse-tree",
            "archive",
            "exec-path",
        ],
        "schema_version": "mingli-git-smoke-v1",
        "status_porcelain": "",
        "templates_exists": True,
        "templates_path": "/opt/git/share/git-core/templates",
        "tree_sha1": "bc699a237960421da8b1ae4197e3475403b515a8",
        "version": "git version 2.39.5",
    }
    assert verifier.validate_git_smoke_payload(payload) == payload

    tampered = copy.deepcopy(payload)
    tampered["tree_sha1"] = "0" * 40
    with pytest.raises(
        verifier.ReleaseVerificationError,
        match="frozen fixture and golden values",
    ):
        verifier.validate_git_smoke_payload(tampered)


def test_git_smoke_bundle_consistent_tamper_is_semantically_rejected(
    tmp_path: Path,
) -> None:
    verifier = load_verifier()
    report = copy.deepcopy(load_report())
    artifacts = tmp_path / "artifacts"
    shutil.copytree(RUNTIME_DIR, artifacts)
    smoke_command = next(
        item for item in report["audit"]["commands"] if item["id"] == "git-smoke"
    )
    smoke_path = artifacts / smoke_command["stdout_path"]
    payload = json.loads(smoke_path.read_text(encoding="utf-8"))
    payload["tree_sha1"] = "0" * 40
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    smoke_path.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    smoke_command["stdout_sha256"] = digest
    report["git_smoke"]["output_sha256"] = digest

    production_path = artifacts / report["evidence"]["production_evidence_path"]
    production = json.loads(production_path.read_text(encoding="utf-8"))
    production_command = next(
        item for item in production["commands"] if item["id"] == "git-smoke"
    )
    production_command["stdout_sha256"] = digest
    production["git_smoke"]["output_sha256"] = digest
    production["files"][smoke_command["stdout_path"]] = digest
    production_bytes = (
        json.dumps(production, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode()
    production_path.write_bytes(production_bytes)
    report["evidence"]["production_evidence_sha256"] = hashlib.sha256(
        production_bytes
    ).hexdigest()

    with pytest.raises(
        verifier.ReleaseVerificationError,
        match="frozen fixture and golden values",
    ):
        verifier.validate_audit_report(report, artifacts_root=artifacts)


def test_sbom_covers_python_node_and_vendored_iztro() -> None:
    report = load_report()
    sbom = json.loads(SBOM_PATH.read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
    components = {
        (item.get("name"), item.get("version")) for item in sbom.get("components", [])
    }
    for expected in (
        ("cpython", "3.14.6"),
        ("node", report["target"]["node_version"]),
        ("iztro", "2.5.8"),
        ("PyYAML", "6.0.3"),
        ("sxtwl", "2.0.7"),
        ("astronomy-engine", "2.1.19"),
        ("cnlunar", "0.2.4"),
        ("libatomic1", "12.2.0-14+deb12u1"),
        ("git", "2.39.5"),
    ):
        assert expected in components
