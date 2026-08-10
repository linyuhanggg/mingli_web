#!/usr/bin/env python3
"""Task 13 trajectory checklist runner - local/fake auto coverage + pending map.

Task 13 (docs/plans/2026-08-09-mingli-v51-web-integration.md) requires the full
staging trajectory suite plus operational drills before real traffic. Most of
the state-machine trajectories are already covered by local Fake/contract
tests; the isolated-staging runs and drills are not. This runner:

- lists the 13 checkpoints (id, name, coverage, evidence convention);
- runs every automatically-covered checkpoint with the exact pytest node IDs;
- records skips (e.g. PostgreSQL concurrency tests without
  MINGLI_TEST_POSTGRES_URL) and marks genuinely-pending checkpoints with the
  reason nothing can run locally;
- writes a non-sensitive markdown + JSON summary into
  docs/releases/evidence/2026-08-11-task13-prep/ (or --out-dir).

Usage:
    uv run --project backend python scripts/task13_trajectory_runner.py
    uv run --project backend python scripts/task13_trajectory_runner.py --dry-run
    uv run --project backend python scripts/task13_trajectory_runner.py \
        --with-real-smoke --out-dir docs/releases/evidence/2026-08-11-task13-prep

Exit code: 0 when every auto checkpoint passed (pending/skip are recorded, not
fatal); 1 when any auto checkpoint failed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUT_DIR = _REPO_ROOT / "docs" / "releases" / "evidence" / "2026-08-11-task13-prep"

CHECKPOINTS: list[dict[str, Any]] = [
    {
        "id": "T13-01",
        "name": "Runtime startup gate：13/13 describe + 冻结 manifest digest / capability shape",
        "auto": True,
        "pytest": ["backend/tests/test_runtime_startup_gate.py"],
        "real_command": "scripts/run_local_real_runtime_smoke.sh --skip-model",
        "pending_reason": None,
        "notes": "真实启动用 run_local_real_runtime_smoke.sh（需本机 0600 env）",
    },
    {
        "id": "T13-02",
        "name": "Release inventory 完整性：217 签名文件 / 55 古籍 / 1328 evidence / 13 Provider",
        "auto": True,
        "pytest": [
            ("backend/tests/test_runtime_startup_gate.py::"
            "test_filesystem_release_inspector_recomputes_the_complete_signed_inventory"),
            ("backend/tests/test_runtime_startup_gate.py::"
            "test_filesystem_release_inspector_rejects_a_tampered_signed_file"),
            ("backend/tests/test_runtime_startup_gate.py::"
            "test_filesystem_release_inspector_rejects_unsigned_extra_files"),
            ("backend/tests/test_runtime_startup_gate.py::"
            "test_filesystem_release_inspector_rejects_resigned_but_incomplete_inventories"),
        ],
        "real_command": "scripts/run_local_real_runtime_smoke.sh --skip-model",
        "pending_reason": None,
        "notes": "真实 inventory 数字见 smoke-summary.json（inventory 段）",
    },
    {
        "id": "T13-03",
        "name": "bazi need_input：新单 → Stopped(need_input) → 续单 → Prepared",
        "auto": True,
        "pytest": ["backend/tests/test_reading_orchestrator_prepare.py"],
        "real_command": "scripts/run_local_real_runtime_smoke.sh --model",
        "pending_reason": None,
        "notes": "真实 prepare 冒烟随 smoke 脚本执行",
    },
    {
        "id": "T13-04",
        "name": "bazi accepted：prepare → 一次模型调用 → guard → accepted（receipt 持久化）",
        "auto": True,
        "pytest": [
            "backend/tests/test_reading_orchestrator_complete.py",
            "backend/tests/test_email_user_journey.py",
        ],
        "real_command": "scripts/run_local_real_runtime_smoke.sh --model",
        "pending_reason": None,
        "notes": "真实单次 generate 随 smoke 脚本执行（有密钥时）",
    },
    {
        "id": "T13-05",
        "name": "fortune day：today 精确目标区间 → accepted",
        "auto": True,
        "pytest": [
            ("backend/tests/test_readings_api.py::"
            "test_today_and_week_jobs_reach_accepted_under_default_local_fake_stack"),
            "backend/tests/test_readings_api.py::test_today_and_week_project_server_horizons",
            ("backend/tests/test_request_compiler.py::"
            "test_fortune_compiler_uses_server_normalized_profile_time"),
        ],
        "real_command": None,
        "pending_reason": "隔离 staging 真实 fortune 轨迹需服务端密钥/部署，未配置",
        "notes": "本地 Fake 全链路已绿；真实区间证据留在 staging 跑",
    },
    {
        "id": "T13-06",
        "name": "fortune week：near_seven → accepted",
        "auto": True,
        "pytest": [
            ("backend/tests/test_readings_api.py::"
            "test_today_and_week_jobs_reach_accepted_under_default_local_fake_stack"),
            "backend/tests/test_readings_api.py::test_today_and_week_project_server_horizons",
            ("backend/tests/test_request_compiler.py::"
            "test_fortune_compiler_uses_server_normalized_profile_time"),
        ],
        "real_command": None,
        "pending_reason": "隔离 staging 真实 fortune 轨迹需服务端密钥/部署，未配置",
        "notes": "同 T13-05；day/week 由同一组本地用例覆盖",
    },
    {
        "id": "T13-07",
        "name": "liuyao manual：手动六爻（6..9 自下而上）→ accepted",
        "auto": True,
        "pytest": [
            ("backend/tests/test_request_compiler.py::"
            "test_liuyao_compiler_preserves_manual_order_or_explicit_digital_coin"),
            ("backend/tests/test_readings_api.py::"
            "test_liuyao_need_input_supply_enqueues_a_tokenized_job"),
        ],
        "real_command": None,
        "pending_reason": "隔离 staging 真实 liuyao 轨迹需服务端密钥/部署，未配置",
        "notes": "本地 compiler + API 假链路已覆盖",
    },
    {
        "id": "T13-08",
        "name": "liuyao digital：digital_coin 数字卦 → accepted",
        "auto": True,
        "pytest": [
            ("backend/tests/test_request_compiler.py::"
            "test_liuyao_compiler_preserves_manual_order_or_explicit_digital_coin"),
            ("backend/tests/test_readings_api.py::"
            "test_liuyao_need_input_supply_enqueues_a_tokenized_job"),
        ],
        "real_command": None,
        "pending_reason": "隔离 staging 真实 liuyao 轨迹需服务端密钥/部署，未配置",
        "notes": "同 T13-07；manual/digital 由同一组本地用例覆盖",
    },
    {
        "id": "T13-09",
        "name": "follow-up：prior_answer 注入新 brief → accepted 新版本",
        "auto": True,
        "pytest": [
            ("backend/tests/test_readings_api.py::"
            "test_follow_up_creates_a_new_version_with_projected_prior_answer"),
        ],
        "real_command": None,
        "pending_reason": "隔离 staging 真实 follow-up 需已 accepted 的真实成稿，未配置",
        "notes": "本地 API 假链路已覆盖 prior_answer 投影",
    },
    {
        "id": "T13-10",
        "name": "Guard 连续拒绝 → delayed，永不到 complete",
        "auto": True,
        "pytest": [
            ("backend/tests/test_reading_orchestrator_complete.py::"
            "test_guard_failure_retries_the_same_model_once_then_succeeds"),
            ("backend/tests/test_reading_orchestrator_complete.py::"
            "test_exhausted_guard_failures_never_call_complete"),
            ("backend/tests/test_reading_orchestrator_complete.py::"
            "test_safe_failed_model_receipt_is_persisted_with_the_failed_attempt"),
        ],
        "real_command": None,
        "pending_reason": "真实模型 Guard 拒绝轨迹需 staging 真实模型，未配置",
        "notes": "本地 orchestrator 用例已覆盖 delayed 状态机",
    },
    {
        "id": "T13-11",
        "name": "complete 落库后 crash → byte-identical replay → 单 Accepted",
        "auto": True,
        "pytest": [
            "backend/tests/test_reading_orchestrator_recovery.py",
            ("backend/tests/test_reading_worker.py::"
            "test_postgresql_complete_transport_retry_is_delayed_and_exact"),
        ],
        "real_command": None,
        "pending_reason": None,
        "notes": "worker 并发用例需要 MINGLI_TEST_POSTGRES_URL，本地无则 skip",
    },
    {
        "id": "T13-12",
        "name": "敏感数据边界：state_token / 出生资料 / Prompt / 密钥不泄漏",
        "auto": True,
        "pytest": [
            "backend/tests/test_sensitive_payloads.py",
            "backend/tests/test_model_data_boundary.py",
            ("tests/contract/test_openapi_contract.py::"
            "test_phase_two_contracts_never_expose_runtime_or_birth_secrets"),
            ("backend/tests/test_standalone_model_adapter.py::"
            "test_safe_audit_log_excludes_api_key_prompt_and_candidate"),
            ("backend/tests/test_standalone_model_adapter.py::"
            "test_provider_metadata_can_never_echo_the_api_key_into_a_receipt"),
            ("backend/tests/test_standalone_model_adapter.py::"
            "test_traceback_locals_never_retain_the_key_prompt_or_authorized_request"),
        ],
        "real_command": None,
        "pending_reason": None,
        "notes": "仓库级边界扫描；staging 侧浏览器/日志/DB 检查仍 pending",
    },
    {
        "id": "T13-13",
        "name": "运维 Gate：Guard 红队 / state volume backup-restore / 告警演练 / Secret Manager",
        "auto": True,
        "pytest": [
            ("tests/contract/test_mingli_runtime_release.py::"
            "test_backup_drill_redacts_pending_token_and_replays_promoted_prepare"),
            "tests/contract/test_mingli_local_gate.py",
        ],
        "real_command": None,
        "pending_reason": (
            "Guard 红队用例集、生产告警演练（runtime_unknown/delayed/guard/model cost）、"
            "Secret Manager 密钥托管与轮换、真实 state volume backup/restore 均需隔离 "
            "staging/生产凭据，仓库内不可自动跑"
        ),
        "notes": "契约级 backup-drill 与 local gate 已自动覆盖；实战演练 pending",
    },
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _slug(checkpoint: dict[str, Any]) -> str:
    return checkpoint["id"].lower().replace("-", "_")


def _parse_pytest_tail(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for label in counts:
        match = re.search(rf"(\d+)\s+{label}", output)
        if match:
            counts[label] = int(match.group(1))
    return counts


def _run_pytest(checkpoint: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    node_ids = checkpoint["pytest"]
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{_slug(checkpoint)}.log"
    command = [
        "uv",
        "run",
        "--project",
        "backend",
        "pytest",
        *node_ids,
        "-q",
        "--no-header",
        "-p",
        "no:cacheprovider",
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": "pytest timed out after 1800s",
            "exit_code": None,
            "duration_s": round(time.monotonic() - started, 1),
            "log": str(log_path),
        }
    duration_s = round(time.monotonic() - started, 1)
    output = completed.stdout + completed.stderr
    log_path.write_text(output, encoding="utf-8")
    counts = _parse_pytest_tail(output)
    if completed.returncode == 0 and counts["failed"] == 0 and counts["errors"] == 0:
        status = "passed"
    elif completed.returncode == 5:
        status = "skipped"
    else:
        status = "failed"
    return {
        "status": status,
        "exit_code": completed.returncode,
        "duration_s": duration_s,
        "counts": counts,
        "log": str(log_path),
    }


def _run_real_smoke(out_dir: Path) -> dict[str, Any]:
    env_file = Path.home() / ".config" / "mingli" / "local-real-model.env"
    if not env_file.exists():
        return {
            "status": "unavailable",
            "reason": f"local env file missing: {env_file}",
        }
    command = [
        str(_REPO_ROOT / "scripts" / "run_local_real_runtime_smoke.sh"),
        "--skip-model",
        "--evidence-dir",
        str(out_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "stdout_tail": (completed.stdout + completed.stderr).strip().splitlines()[-12:],
    }


def _write_summary(
    out_dir: Path,
    rows: list[dict[str, Any]],
    real_smoke: dict[str, Any] | None,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema": "mingli-task13-trajectory-checklist-v1",
        "generated_at": _utc_now(),
        "dry_run": dry_run,
        "checkpoints": rows,
        "real_smoke": real_smoke,
        "totals": {
            "auto": sum(1 for row in rows if row["auto"]),
            "passed": sum(1 for row in rows if row["result"]["status"] == "passed"),
            "skipped": sum(1 for row in rows if row["result"]["status"] == "skipped"),
            "failed": sum(1 for row in rows if row["result"]["status"] == "failed"),
            "pending": sum(1 for row in rows if not row["auto"] or row["pending_reason"]),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "task13-trajectory-checklist.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Task 13 轨迹清单（runner 输出）",
        "",
        f"- 生成时间：{_utc_now()}（UTC）",
        f"- dry-run：{'是' if dry_run else '否'}",
        "",
        "| ID | 轨迹 | 覆盖 | 状态 | 本地结果 | 下一步 |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        result = row["result"]
        status = result["status"]
        if status == "passed":
            counts = result.get("counts")
            result_text = (
                f"{counts['passed']} passed / {counts['skipped']} skipped"
                if counts
                else "ok"
            )
        elif status == "failed":
            result_text = f"failed (exit {result.get('exit_code')})"
        elif status == "skipped":
            result_text = "skipped（环境缺依赖）"
        else:
            result_text = "pending"
        coverage = "pytest 自动" if row["auto"] else "手动/待定"
        next_step = row["pending_reason"] or (
            row["real_command"] or "staging 真实轨迹"
        )
        lines.append(
            f"| {row['id']} | {row['name']} | {coverage} | {status} | "
            f"{result_text} | {next_step} |"
        )
    lines.extend(
        [
            "",
            "## 约定",
            "",
            "- 证据目录：`docs/releases/evidence/2026-08-11-task13-prep/`",
            ("  - `task13-trajectory-checklist.json` / `.md`：本清单"
            "（含每次 pytest 的 exit code、耗时、计数）"),
            "  - `logs/T13-XX.log`：每个自动检查点的 pytest 原始输出",
            "  - `smoke-summary.json`：真实 Runtime smoke 摘要（无密钥/无 token）",
            "- `pending` 不代表失败：表示该检查点需要隔离 staging/生产凭据，仓库内不可自动跑。",
            ("- Task 13 未完成；production blocked / real traffic disabled（见 "
            "docs/releases/2026-08-11-task13-prep-real-path-replay.md）。"),
        ]
    )
    (out_dir / "task13-trajectory-checklist.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list checkpoints only")
    parser.add_argument(
        "--with-real-smoke",
        action="store_true",
        help="also run the real Runtime smoke (runtime-only) when the local env exists",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="evidence output directory",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for checkpoint in CHECKPOINTS:
        row = dict(checkpoint)
        if args.dry_run or not checkpoint["auto"]:
            row["result"] = {
                "status": "pending" if not checkpoint["auto"] else "not-run",
                "reason": "dry-run（未执行）" if args.dry_run else checkpoint["pending_reason"],
            }
        else:
            row["result"] = _run_pytest(checkpoint, out_dir)
        rows.append(row)
        status = row["result"]["status"]
        marker = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP", "pending": "PEND"}.get(
            status, "----"
        )
        print(f"[{marker}] {row['id']} {row['name']} -> {status}")

    real_smoke: dict[str, Any] | None = None
    if args.with_real_smoke and not args.dry_run:
        print("[----] running real Runtime smoke (runtime-only)...")
        real_smoke = _run_real_smoke(out_dir)
        print(f"[{real_smoke['status'].upper()}] real Runtime smoke -> {real_smoke['status']}")

    summary = _write_summary(out_dir, rows, real_smoke, dry_run=args.dry_run)
    print(f"summary written: {out_dir}")
    totals = summary["totals"]
    print(
        f"totals: auto={totals['auto']} passed={totals['passed']} "
        f"skipped={totals['skipped']} failed={totals['failed']} pending={totals['pending']}"
    )
    return 0 if totals["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
