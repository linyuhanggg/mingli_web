from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = (
    "Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收"
    "不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。"
)
POLICY_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "docs" / "MINGLI_V51_WEB_INTEGRATION.md",
    ROOT / "docs" / "PHASE_0_GATES.md",
    ROOT / "docs" / "PRODUCT_BLUEPRINT_WEB_IOS_V2.md",
    ROOT
    / "docs"
    / "plans"
    / "2026-08-09-mingli-v51-web-integration.md",
    ROOT
    / "docs"
    / "adr"
    / "0010-replace-agent-loop-with-an-explicit-reading-orchestrator.md",
    ROOT / "infra" / "mingli-runtime" / "README.md",
)
SLOT_POLICY = (
    "`slots` 和 `max_slots` 表示 signed runner 的加权调度额度，不是操作系统 "
    "PID 数量上限。"
)
SLOT_POLICY_DOCUMENTS = (
    ROOT / "docs" / "MINGLI_V51_WEB_INTEGRATION.md",
    ROOT
    / "docs"
    / "plans"
    / "2026-08-09-mingli-v51-web-integration.md",
    ROOT / "infra" / "mingli-runtime" / "README.md",
)


def test_authoritative_documents_make_native_full_the_only_runtime_gate() -> None:
    missing = [
        str(path.relative_to(ROOT))
        for path in POLICY_DOCUMENTS
        if POLICY not in path.read_text(encoding="utf-8")
    ]

    assert missing == []


def run_contract_pytest(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *args],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )


def test_pure_release_contracts_stay_active_without_starting_linux() -> None:
    completed = run_contract_pytest(
        "tests/contract/test_mingli_runtime_release.py"
    )
    output = completed.stdout + completed.stderr

    assert completed.returncode == 0, output
    summary = re.search(r"(\d+) passed, (\d+) skipped", output)
    assert summary is not None, output
    assert tuple(map(int, summary.groups())) == (53, 17)


def test_retired_linux_execution_contracts_are_skipped_by_pytest() -> None:
    completed = run_contract_pytest(
        "tests/contract/test_mingli_local_gate.py",
        "-k",
        "linux or vz or lima or oci",
    )
    output = completed.stdout + completed.stderr

    assert completed.returncode == 0, output
    assert " skipped" in output
    assert " passed" not in output


def test_native_slot_fields_are_not_documented_as_a_pid_ceiling() -> None:
    missing = [
        str(path.relative_to(ROOT))
        for path in SLOT_POLICY_DOCUMENTS
        if SLOT_POLICY not in path.read_text(encoding="utf-8")
    ]

    assert missing == []
