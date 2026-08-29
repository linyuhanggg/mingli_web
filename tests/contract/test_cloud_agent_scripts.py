from __future__ import annotations

import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "cloud-agent" / "install.sh"
START_SCRIPT = REPO_ROOT / "scripts" / "cloud-agent" / "start.sh"
LOCAL_DATABASE_URL = "postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli"
FORBIDDEN_RUNTIME_IDENTITIES = (
    "494ce0bba174a77800daf9b9c38ce9c9166d9a94",
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68",
)


def _write_executable(path: Path, body: str) -> None:
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    path.chmod(0o755)


def _mini_repo(tmp_path: Path, script: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    script_dir = repo / "scripts" / "cloud-agent"
    script_dir.mkdir(parents=True)
    shutil.copy2(script, script_dir / script.name)
    (repo / "backend").mkdir()
    (repo / "web").mkdir()
    (repo / "admin").mkdir()

    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "cloud-agent@test.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Cloud Agent Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)

    home = tmp_path / "home"
    stub_bin = tmp_path / "bin"
    pg_bin = tmp_path / "pgbin"
    state_dir = tmp_path / "state"
    for path in (home, stub_bin, pg_bin, state_dir):
        path.mkdir()
    return repo, home, stub_bin, pg_bin


def _base_env(home: Path, stub_bin: Path, state_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{stub_bin}:{env['PATH']}",
            "STUB_STATE": str(state_dir),
            "STUB_LOG": str(state_dir / "commands.log"),
        }
    )
    env.pop("MINGLI_ADMIN_BOOTSTRAP_EMAIL", None)
    env.pop("MINGLI_ADMIN_BOOTSTRAP_PASSWORD", None)
    return env


def _install_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    repo, home, stub_bin, pg_bin = _mini_repo(tmp_path, INSTALL_SCRIPT)
    state_dir = tmp_path / "state"
    env = _base_env(home, stub_bin, state_dir)

    _write_executable(
        stub_bin / "uv",
        r"""
        #!/usr/bin/env bash
        set -eu
        printf 'uv db=%s args=%s\n' "${MINGLI_DATABASE_URL:-missing}" "$*" >>"$STUB_LOG"
        if [[ "$*" == *"python -c"* ]]; then
          printf 'generated-local-test-password\n'
        fi
        """,
    )
    _write_executable(
        stub_bin / "npm",
        r"""
        #!/usr/bin/env bash
        set -eu
        printf 'npm args=%s\n' "$*" >>"$STUB_LOG"
        """,
    )
    _write_executable(
        stub_bin / "sed",
        r"""
        #!/usr/bin/env bash
        exit 0
        """,
    )
    _write_executable(
        pg_bin / "initdb",
        r"""
        #!/usr/bin/env bash
        set -eu
        while [ "$#" -gt 0 ]; do
          if [ "$1" = "-D" ]; then
            shift
            target="$1"
            break
          fi
          shift
        done
        mkdir -p "$target"
        : >"$target/PG_VERSION"
        : >"$target/postgresql.conf"
        printf 'initdb\n' >>"$STUB_LOG"
        """,
    )
    _write_executable(
        pg_bin / "pg_ctl",
        r"""
        #!/usr/bin/env bash
        set -eu
        if [[ " $* " == *" status "* ]]; then
          test -f "$STUB_STATE/postgres.running"
          exit
        fi
        : >"$STUB_STATE/postgres.running"
        printf 'pg_ctl start\n' >>"$STUB_LOG"
        """,
    )
    _write_executable(
        pg_bin / "pg_isready",
        r"""
        #!/usr/bin/env bash
        exit 0
        """,
    )
    _write_executable(
        pg_bin / "psql",
        r"""
        #!/usr/bin/env bash
        set -eu
        args="$*"
        printf 'psql db=%s args=%s\n' "${MINGLI_DATABASE_URL:-missing}" "$args" >>"$STUB_LOG"
        case "$args" in
          *"SELECT 1 FROM pg_roles"*)
            test ! -f "$STUB_STATE/role.created" || printf '1\n'
            ;;
          *"CREATE ROLE mingli"*)
            : >"$STUB_STATE/role.created"
            ;;
          *"SELECT 1 FROM pg_database"*)
            test ! -f "$STUB_STATE/database.created" || printf '1\n'
            ;;
          *"CREATE DATABASE mingli"*)
            : >"$STUB_STATE/database.created"
            ;;
          *"fateradar-fake-contract"*)
            printf '%s\n' "$args" >>"$STUB_STATE/runtime-seed.log"
            ;;
        esac
        """,
    )
    return repo, home, pg_bin, env


def _run_install(repo: Path, pg_bin: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    harness = textwrap.dedent(
        f"""
        source {repo / "scripts/cloud-agent/install.sh"}
        PGBIN={pg_bin}
        install_main
        """
    )
    return subprocess.run(
        ["bash", "-c", harness],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def _start_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    repo, home, stub_bin, pg_bin = _mini_repo(tmp_path, START_SCRIPT)
    state_dir = tmp_path / "state"
    env = _base_env(home, stub_bin, state_dir)

    admin_dir = home / ".config" / "fateradar-cloud-agent"
    admin_dir.mkdir(parents=True)
    admin_env = admin_dir / "local.env"
    admin_env.write_text(
        "export MINGLI_ADMIN_BOOTSTRAP_EMAIL=cloud-agent-admin@localhost\n"
        "export MINGLI_ADMIN_BOOTSTRAP_PASSWORD=local-test-password\n",
        encoding="utf-8",
    )
    admin_env.chmod(0o600)

    _write_executable(
        pg_bin / "pg_ctl",
        r"""
        #!/usr/bin/env bash
        [[ " $* " == *" status "* ]]
        """,
    )
    _write_executable(
        pg_bin / "pg_isready",
        r"""
        #!/usr/bin/env bash
        exit 0
        """,
    )
    _write_executable(
        stub_bin / "setsid",
        r"""
        #!/usr/bin/env bash
        exec "$@"
        """,
    )
    _write_executable(
        stub_bin / "uv",
        r"""
        #!/usr/bin/env bash
        set -eu
        if [[ "$*" == *"uvicorn"* ]]; then service=api; else service=worker; fi
        printf '%s\n' "$service" >>"$STUB_STATE/launches.log"
        if [ "${FAIL_SERVICE:-}" = "$service" ]; then
          printf '%s failed immediately\n' "$service" >&2
          exit 17
        fi
        test -n "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}"
        test -n "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}"
        : >"$STUB_STATE/$service.started"
        while :; do sleep 60; done
        """,
    )
    _write_executable(
        stub_bin / "npm",
        r"""
        #!/usr/bin/env bash
        set -eu
        if [[ " $* " == *" --prefix web "* ]]; then service=web; else service=admin; fi
        printf '%s\n' "$service" >>"$STUB_STATE/launches.log"
        if [ "${FAIL_SERVICE:-}" = "$service" ]; then
          printf '%s failed immediately\n' "$service" >&2
          exit 17
        fi
        : >"$STUB_STATE/$service.started"
        while :; do sleep 60; done
        """,
    )
    return repo, home, pg_bin, env


def _start_harness(repo: Path, pg_bin: Path, *, twice: bool) -> str:
    second_run = "start_main" if twice else ":"
    return textwrap.dedent(
        f"""
        source {repo / "scripts/cloud-agent/start.sh"}
        PGBIN={pg_bin}
        STARTUP_GRACE_SECONDS=0.2
        HEALTH_ATTEMPTS=2
        HEALTH_SLEEP_SECONDS=0.1

        process_matches() {{
          local state
          state="$(ps -p "$1" -o stat= 2>/dev/null)" || return 1
          [[ "$state" != Z* ]]
        }}
        find_managed_pid() {{ return 1; }}
        port_listening() {{
          case "$1" in
            8000) test -f "$STUB_STATE/api.started" ;;
            3000) test -f "$STUB_STATE/web.started" ;;
            3001) test -f "$STUB_STATE/admin.started" ;;
            *) return 1 ;;
          esac
        }}
        api_live() {{ test -f "$STUB_STATE/api.started"; }}
        api_ready() {{ test -f "$STUB_STATE/api.started"; }}
        cleanup() {{
          local pid_file pid
          for pid_file in "$PID_DIR"/*.pid; do
            [ -f "$pid_file" ] || continue
            pid="$(sed -n '1p' "$pid_file")"
            kill "$pid" 2>/dev/null || true
          done
          sleep 0.1
        }}
        trap cleanup EXIT
        start_main
        {second_run}
        """
    )


def test_scripts_encode_current_local_contracts() -> None:
    install = INSTALL_SCRIPT.read_text(encoding="utf-8")
    start = START_SCRIPT.read_text(encoding="utf-8")

    assert 'export MINGLI_DATABASE_URL="$LOCAL_DATABASE_URL"' in install
    assert "'fateradar-fake-contract', 'test-v1'" in install
    assert 'git -C "$REPO_ROOT" rev-parse HEAD' in install
    for forbidden in FORBIDDEN_RUNTIME_IDENTITIES:
        assert forbidden not in install

    assert "pgrep" not in start
    for identity in ("api", "worker", "web", "admin"):
        assert f"fateradar-cloud-agent-{identity}" in start
        assert f"${{LOG_DIR}}/{identity}.log" in start or "${LOG_DIR}/${name}.log" in start
    assert "/api/v1/health/live" in start
    assert "/api/v1/health/ready" in start


def test_install_is_idempotent_pins_local_database_and_creates_fake_contract(
    tmp_path: Path,
) -> None:
    repo, home, pg_bin, env = _install_fixture(tmp_path)
    env["MINGLI_DATABASE_URL"] = "postgresql+asyncpg://hostile.invalid/not-local"

    first = _run_install(repo, pg_bin, env)
    assert first.returncode == 0, first.stdout + first.stderr
    admin_env = home / ".config" / "fateradar-cloud-agent" / "local.env"
    first_admin_values = admin_env.read_text(encoding="utf-8")

    second = _run_install(repo, pg_bin, env)
    assert second.returncode == 0, second.stdout + second.stderr
    assert admin_env.read_text(encoding="utf-8") == first_admin_values
    assert stat.S_IMODE(admin_env.stat().st_mode) == 0o600
    assert "generated-local-test-password" not in first.stdout + first.stderr
    assert "generated-local-test-password" not in second.stdout + second.stderr

    state_dir = tmp_path / "state"
    command_log = (state_dir / "commands.log").read_text(encoding="utf-8")
    assert "hostile.invalid" not in command_log
    assert f"uv db={LOCAL_DATABASE_URL}" in command_log
    assert command_log.count("initdb\n") == 1
    assert command_log.count("pg_ctl start\n") == 1
    assert command_log.count("CREATE ROLE mingli") == 1
    assert command_log.count("CREATE DATABASE mingli") == 1

    checkout_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    seed_log = (state_dir / "runtime-seed.log").read_text(encoding="utf-8")
    assert seed_log.count("fateradar-fake-contract") == 2
    assert "test-v1" in seed_log
    assert checkout_sha in seed_log
    for forbidden in FORBIDDEN_RUNTIME_IDENTITIES:
        assert forbidden not in seed_log


def test_process_identity_requires_exact_wrapper_and_service_name(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    cmdline = proc_root / "123" / "cmdline"
    cmdline.parent.mkdir(parents=True)
    harness = textwrap.dedent(
        f"""
        source {START_SCRIPT}
        PROC_ROOT={proc_root}
        PID_DIR={tmp_path / "pids"}
        mkdir -p "$PID_DIR"
        printf '%s\\0' /bin/bash -c "$SERVICE_WRAPPER" fateradar-cloud-agent-web >{cmdline}
        process_matches 123 fateradar-cloud-agent-web
        ! process_matches 123 fateradar-cloud-agent-admin
        ! managed_pid admin fateradar-cloud-agent-admin
        test "$(managed_pid web fateradar-cloud-agent-web)" = 123
        """
    )
    completed = subprocess.run(["bash", "-c", harness], text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_start_launches_each_service_once_and_reconciles_without_duplicates(
    tmp_path: Path,
) -> None:
    repo, _home, pg_bin, env = _start_fixture(tmp_path)
    completed = subprocess.run(
        ["bash", "-c", _start_harness(repo, pg_bin, twice=True)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    launches = (tmp_path / "state" / "launches.log").read_text(encoding="utf-8").splitlines()
    assert launches == ["api", "worker", "web", "admin"]
    assert completed.stdout.count("already running as PID") == 4
    assert "local-test-password" not in completed.stdout + completed.stderr


@pytest.mark.parametrize("failed_service", ["api", "worker", "web", "admin"])
def test_start_reports_each_immediate_child_failure(tmp_path: Path, failed_service: str) -> None:
    repo, _home, pg_bin, env = _start_fixture(tmp_path)
    env["FAIL_SERVICE"] = failed_service
    completed = subprocess.run(
        ["bash", "-c", _start_harness(repo, pg_bin, twice=False)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode != 0
    assert f"ERROR: {failed_service} exited during startup" in completed.stderr
    assert f"logs/{failed_service}.log" in completed.stderr


def test_start_fails_clearly_without_local_admin_bootstrap(tmp_path: Path) -> None:
    repo, home, _stub_bin, pg_bin = _mini_repo(tmp_path, START_SCRIPT)
    env = _base_env(home, tmp_path / "bin", tmp_path / "state")
    harness = textwrap.dedent(
        f"""
        source {repo / "scripts/cloud-agent/start.sh"}
        PGBIN={pg_bin}
        start_main
        """
    )
    completed = subprocess.run(
        ["bash", "-c", harness],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "local Admin bootstrap file is missing" in completed.stderr
