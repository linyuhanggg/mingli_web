#!/usr/bin/env python3
"""Task 13 real product trajectory evidence runner (server, re-runnable).

Runs the sanitized trajectory payload on the test server fateradar-prod over
SSH and copies the evidence summary back to the repo:

    docs/releases/evidence/2026-08-11-task13-server-trajectory/

The payload itself walks guest session -> email OTP -> profile -> preview /
today / week / liuyao digital_coin / follow-up through the real HTTP + Worker
chain (see scripts/server_task13_trajectory_payload.py). Raw HTTP bodies stay
in a 0700 work dir on the server; only sanitized evidence is copied back.

Usage:
    python3 scripts/run_server_task13_trajectory.py
    python3 scripts/run_server_task13_trajectory.py --ssh-host fateradar-prod

Exit code: 0 when every required trajectory is accepted and no sensitive
marker was found; 1 for an explicit partial result (reasons recorded); 2 when
the summary could not be produced or a sensitive marker was found.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PAYLOAD = _REPO_ROOT / "scripts" / "server_task13_trajectory_payload.py"
_EXPECTED_MAIN_HEAD = "3af1f16"
_EXPECTED_SERVER_CURRENT = "1c26f0924ce22171b32f0c75a781f7599eec6ed5"
_SERVER_BACKEND_PYTHON = "/opt/fateradar/current/backend/.venv/bin/python"
_SERVER_ENV_FILE = "/etc/fateradar/test.env"
_DEFAULT_EVIDENCE_DIR = (
    _REPO_ROOT / "docs" / "releases" / "evidence" / "2026-08-11-task13-server-trajectory"
)


def _run(
    command: list[str],
    *,
    timeout: int = 60,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=cwd,
    )


def _ssh(host: str, script: str, *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, script], timeout=timeout)


def _check_git_head() -> str:
    completed = _run(["git", "rev-parse", "--short", "HEAD"], cwd=_REPO_ROOT)
    head = completed.stdout.strip()
    print(f"local main HEAD: {head} (expected {_EXPECTED_MAIN_HEAD})")
    if head != _EXPECTED_MAIN_HEAD:
        print("WARNING: local HEAD differs from the expected Task 13 base; continuing anyway")
    return head


def _server_baseline(host: str) -> tuple[str, str]:
    script = (
        "set -e; "
        "readlink -f /opt/fateradar/current; "
        "systemctl is-active fateradar-test-api fateradar-test-worker "
        "fateradar-test-web nginx | tr '\\n' ' '; echo; "
        f"test -x {_SERVER_BACKEND_PYTHON} && echo python-ok; "
        f"{_SERVER_BACKEND_PYTHON} -c 'import httpx, asyncpg; print(\"deps-ok\")'"
    )
    completed = _ssh(host, script, timeout=30)
    if completed.returncode != 0:
        print("server baseline check failed:")
        print(completed.stdout + completed.stderr)
        raise SystemExit(2)
    lines = completed.stdout.strip().splitlines()
    current = lines[0]
    services = lines[1] if len(lines) > 1 else ""
    print(f"server current: {current} (expected {_EXPECTED_SERVER_CURRENT})")
    print(f"services active: {services}")
    print(f"backend python + deps: {lines[-1] if lines else 'unknown'}")
    if current != _EXPECTED_SERVER_CURRENT:
        print("WARNING: server current differs from the expected release; continuing anyway")
    return current, services


def _render_markdown(summary: dict[str, Any], *, head: str, current: str) -> str:
    lines = [
        "# Task 13 服务器真实轨迹（runner 输出）",
        "",
        f"- 生成时间（UTC）：{summary.get('generated_at')}",
        f"- 服务器：`{summary.get('server_hostname')}`（SSH 别名 `fateradar-prod`）",
        f"- 本机 main HEAD：`{head}`；服务器 current：`{current}`",
        f"- API 入口：`{summary.get('api_base')}`（nginx 回环同源，浏览器同路径）",
        f"- 身份：{summary.get('identity', {}).get('email_masked')}（虚构邮箱 / 虚构出生资料，原文不落库不落仓）",
        "",
        "## 环境适配器（非秘密键）",
        "",
    ]
    for key, value in summary.get("adapters", {}).items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(
        [
            "",
            "## 轨迹状态",
            "",
            "| 步骤 | 内容 | 结果 | 细节 |",
            "|---|---|---|---|",
        ]
    )
    for step in summary.get("steps", []):
        detail = step.get("detail", {})
        result = "ok" if step["ok"] else "FAIL"
        detail_text = " / ".join(
            str(value)
            for key, value in (
                ("start", detail.get("start_status")),
                ("path", detail.get("status_path")),
                ("terminal", detail.get("terminal_status")),
                ("chars", detail.get("accepted_copy_chars")),
                ("error", detail.get("error")),
                ("reason", detail.get("reason")),
                ("skipped", detail.get("skipped")),
            )
            if value is not None
        )
        lines.append(f"| {step['id']} | {step['name']} | {result} | {detail_text} |")
    scan = summary.get("sensitive_scan", {})
    lines.extend(
        [
            "",
            "## 敏感扫描",
            "",
            f"- 检查标记：{', '.join(scan.get('markers', []))}",
            f"- 发现：{len(scan.get('found', []))} 处",
            "",
            "## delayed 存量（只读 status 计数）",
            "",
            f"- 运行前：`{json.dumps(summary.get('delayed_backlog', {}).get('before'), ensure_ascii=False)}`",
            f"- 运行后：`{json.dumps(summary.get('delayed_backlog', {}).get('after'), ensure_ascii=False)}`",
            "",
            "## 结果",
            "",
            f"- exit_code：`{summary.get('exit_code')}`",
            f"- hard_failure：`{summary.get('hard_failure')}`",
        ]
    )
    if summary.get("partial_reasons"):
        lines.append("- partial 原因：")
        for reason in summary["partial_reasons"]:
            lines.append(f"  - {reason}")
    else:
        lines.append("- partial 原因：无（全部要求的轨迹 accepted）")
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 原始 HTTP 响应体只保留在服务器 0700 工作目录，未复制回仓库。",
            "- 未伪造 delayed：本轮只记录存量与自然结果；Guard 红队仍 pending。",
            "- 本记录是测试服务器联调证据，不等于 staging 合同完成；production blocked。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default="fateradar-prod")
    parser.add_argument("--evidence-dir", default=str(_DEFAULT_EVIDENCE_DIR), type=Path)
    parser.add_argument("--keep-server-work", action="store_true", help="keep raw work dir on server")
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    head = _check_git_head()
    current, services = _server_baseline(args.ssh_host)
    if "active" not in services:
        print(f"services not all active: {services}")
        return 2

    mkdir = _ssh(
        args.ssh_host,
        "d=$(mktemp -d /tmp/mingli-task13-run-XXXXXX) && chmod 700 \"$d\" && echo \"$d\"",
        timeout=20,
    )
    if mkdir.returncode != 0:
        print("failed to create server work dir:")
        print(mkdir.stdout + mkdir.stderr)
        return 2
    work_dir = mkdir.stdout.strip().splitlines()[-1].strip()
    print(f"server work dir: {work_dir}")

    remote_payload = f"{work_dir}/server_task13_trajectory_payload.py"
    push = _run(
        ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
         str(_PAYLOAD), f"{args.ssh_host}:{remote_payload}"],
        timeout=60,
    )
    if push.returncode != 0:
        print("failed to push payload:")
        print(push.stdout + push.stderr)
        return 2

    summary_json = f"{work_dir}/summary.json"
    forwarded_env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("TASK13_QUERY_") or key == "TASK13_EMAIL"
    }
    query_env = " ".join(
        f"{key}={shlex.quote(value)}"
        for key, value in sorted(forwarded_env.items())
    )
    query_prefix = f"{query_env} " if query_env else ""
    command = (
        f"{query_prefix}{_SERVER_BACKEND_PYTHON} {shlex.quote(remote_payload)} "
        f"--work-dir {shlex.quote(work_dir)} "
        f"--summary-json {shlex.quote(summary_json)} "
        f"--env-file {shlex.quote(_SERVER_ENV_FILE)}"
    )
    if query_env:
        print(
            "trajectory overrides: "
            + ", ".join(sorted(forwarded_env))
        )
    print("running trajectory payload on server (may take minutes)...")
    completed = _ssh(args.ssh_host, command, timeout=3600)
    print(completed.stdout)
    if completed.stderr.strip():
        print(completed.stderr[-2000:])

    fetch = _run(
        ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
         f"{args.ssh_host}:{summary_json}", str(evidence_dir / "run-summary.json")],
        timeout=60,
    )
    if fetch.returncode != 0:
        print("failed to fetch summary:")
        print(fetch.stdout + fetch.stderr)
        return 2

    summary = json.loads((evidence_dir / "run-summary.json").read_text(encoding="utf-8"))
    (evidence_dir / "run-summary.md").write_text(
        _render_markdown(summary, head=head, current=current),
        encoding="utf-8",
    )
    print(f"evidence written: {evidence_dir}")

    if not args.keep_server_work:
        cleanup = _ssh(args.ssh_host, f"rm -rf -- {shlex.quote(work_dir)}", timeout=30)
        if cleanup.returncode != 0:
            print("WARNING: server work dir cleanup failed; left in place for inspection")
        else:
            print(f"server work dir removed: {work_dir}")

    exit_code = int(summary.get("exit_code", 1))
    print(f"summary exit_code: {exit_code}")
    if summary.get("partial_reasons"):
        print("partial reasons:")
        for reason in summary["partial_reasons"]:
            print(f"  - {reason}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
