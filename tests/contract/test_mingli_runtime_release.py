#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import re
import stat
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
        "bd03d0b56d81112d87ad340a3d65458059497dc33496b1938fb23056dfe8ba80"
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
    assert "bd03d0b56d81112d87ad340a3d65458059497dc33496b1938fb23056dfe8ba80" in lock
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
    assert len(external_bases) == 3
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
    assert "apt-get install -y --no-install-recommends git" in dockerfile
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
    assert "--production-audit" in controller
    assert "--finalize-audit" in controller
    assert "production_output" in controller
    assert "production_state" in controller
    for forbidden in ("langchain", "agent.run", "tools=", "function_call"):
        assert forbidden not in audit.lower()


def test_backup_drill_distinguishes_replay_from_true_followup() -> None:
    controller = LIMA_GATE_PATH.read_text(encoding="utf-8")
    verifier = VERIFY_PATH.read_text(encoding="utf-8")

    for required in (
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
    ):
        assert expected in components
