#!/usr/bin/env bash
# Cloud Agent start script for mingli_web.
#
# Per-boot reconciliation: ensures PostgreSQL is running and (re)launches the
# four application processes (FastAPI API, async Worker, Web dev server, Admin
# dev server) detached, without creating duplicates, then verifies their local
# health. Logs are written to ~/logs/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PGBIN="/usr/lib/postgresql/16/bin"
PGDATA="$HOME/pgdata"
PGRUN="$HOME/pgrun"
LOG_DIR="$HOME/logs"
PID_DIR="$HOME/.local/state/fateradar-cloud-agent"
ADMIN_ENV_FILE="$HOME/.config/fateradar-cloud-agent/local.env"
PROC_ROOT=/proc
STARTUP_GRACE_SECONDS=1
HEALTH_ATTEMPTS=30
HEALTH_SLEEP_SECONDS=1
SERVICE_WRAPPER='child=; trap '\''[ -z "$child" ] || kill "$child" 2>/dev/null || true'\'' TERM INT EXIT; "$@" & child=$!; wait "$child"; status=$?; trap - EXIT; exit "$status"'
SERVICE_PID=

configure_local_environment() {
  export PATH="$HOME/.local/bin:$PATH"
  export TZ=Asia/Shanghai
  export MINGLI_ENVIRONMENT=local
  export MINGLI_DATABASE_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli"
  export MINGLI_RUNTIME_ADAPTER=fake
  export MINGLI_MODEL_ADAPTER=fake
  export MINGLI_OTP_ADAPTER=fake
  export BACKEND_INTERNAL_URL="http://127.0.0.1:8000"
  export PGDATA
}

load_admin_bootstrap_environment() {
  if { [ -n "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ] && [ -z "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}" ]; } || \
     { [ -z "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ] && [ -n "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}" ]; }; then
    echo "ERROR: set both MINGLI_ADMIN_BOOTSTRAP_EMAIL and MINGLI_ADMIN_BOOTSTRAP_PASSWORD, or neither" >&2
    return 1
  fi

  if [ -n "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ]; then
    export MINGLI_ADMIN_BOOTSTRAP_EMAIL MINGLI_ADMIN_BOOTSTRAP_PASSWORD
    return 0
  fi

  if [ ! -f "$ADMIN_ENV_FILE" ]; then
    echo "ERROR: local Admin bootstrap file is missing; run scripts/cloud-agent/install.sh first or set both bootstrap variables" >&2
    return 1
  fi
  # shellcheck disable=SC1090 -- install.sh creates this local 0600 file.
  source "$ADMIN_ENV_FILE"
  if [ -z "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ] || [ -z "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}" ]; then
    echo "ERROR: ${ADMIN_ENV_FILE} is missing local Admin bootstrap values" >&2
    return 1
  fi
  export MINGLI_ADMIN_BOOTSTRAP_EMAIL MINGLI_ADMIN_BOOTSTRAP_PASSWORD
}

port_listening() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

process_matches() {
  local pid="$1"
  local identity="$2"
  local cmdline="${PROC_ROOT}/${pid}/cmdline"
  local wrapper_arg
  local identity_arg

  [ -r "$cmdline" ] || return 1
  wrapper_arg="$(tr '\0' '\n' <"$cmdline" | sed -n '3p')"
  identity_arg="$(tr '\0' '\n' <"$cmdline" | sed -n '4p')"
  [ "$wrapper_arg" = "$SERVICE_WRAPPER" ] && [ "$identity_arg" = "$identity" ]
}

find_managed_pid() {
  local identity="$1"
  local cmdline
  local pid
  for cmdline in "${PROC_ROOT}"/[0-9]*/cmdline; do
    [ -r "$cmdline" ] || continue
    pid="${cmdline%/cmdline}"
    pid="${pid##*/}"
    if process_matches "$pid" "$identity"; then
      printf '%s\n' "$pid"
      return 0
    fi
  done
  return 1
}

managed_pid() {
  local name="$1"
  local identity="$2"
  local pid_file="${PID_DIR}/${name}.pid"
  local pid=

  if [ -f "$pid_file" ]; then
    pid="$(sed -n '1p' "$pid_file")"
    if process_matches "$pid" "$identity"; then
      printf '%s\n' "$pid"
      return 0
    fi
    rm -f "$pid_file"
  fi

  if pid="$(find_managed_pid "$identity")"; then
    printf '%s\n' "$pid" >"$pid_file"
    printf '%s\n' "$pid"
    return 0
  fi
  return 1
}

service_error() {
  local name="$1"
  local reason="$2"
  echo "ERROR: ${name} ${reason}; see ${LOG_DIR}/${name}.log" >&2
  return 1
}

launch() { # name port_or_empty exact_identity command...
  local name="$1"
  local port="$2"
  local identity="$3"
  local existing_pid=
  local pid_file="${PID_DIR}/${name}.pid"
  shift 3

  SERVICE_PID=
  if existing_pid="$(managed_pid "$name" "$identity")"; then
    SERVICE_PID="$existing_pid"
    echo "    ${name} already running as PID ${SERVICE_PID}${port:+ (port ${port})}"
    return 0
  fi
  if [ -n "$port" ] && port_listening "$port"; then
    service_error "$name" "cannot start because port ${port} belongs to another process"
    return 1
  fi

  echo "    starting ${name}${port:+ (port ${port})}"
  setsid nohup bash -c "$SERVICE_WRAPPER" "$identity" "$@" \
    >"${LOG_DIR}/${name}.log" 2>&1 &
  SERVICE_PID=$!
  printf '%s\n' "$SERVICE_PID" >"$pid_file"
  sleep "$STARTUP_GRACE_SECONDS"
  if ! process_matches "$SERVICE_PID" "$identity"; then
    rm -f "$pid_file"
    service_error "$name" "exited during startup"
    return 1
  fi
}

api_live() {
  curl --fail --silent --show-error --max-time 2 \
    http://127.0.0.1:8000/api/v1/health/live >/dev/null
}

api_ready() {
  curl --fail --silent --show-error --max-time 2 \
    http://127.0.0.1:8000/api/v1/health/ready >/dev/null
}

wait_for_service() { # name identity pid check_function check_args...
  local name="$1"
  local identity="$2"
  local pid="$3"
  local check_function="$4"
  local attempt
  shift 4

  for attempt in $(seq 1 "$HEALTH_ATTEMPTS"); do
    if "$check_function" "$@"; then
      return 0
    fi
    if ! process_matches "$pid" "$identity"; then
      service_error "$name" "exited before becoming healthy"
      return 1
    fi
    sleep "$HEALTH_SLEEP_SECONDS"
  done
  service_error "$name" "did not become healthy"
}

start_main() {
  local api_pid
  local worker_pid
  local web_pid
  local admin_pid

  cd "$REPO_ROOT"
  load_admin_bootstrap_environment
  configure_local_environment
  mkdir -p "$PGRUN" "$LOG_DIR" "$PID_DIR"

  echo "==> Ensuring PostgreSQL is running"
  if ! "${PGBIN}/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
    "${PGBIN}/pg_ctl" -D "$PGDATA" -o "-p 5432" -l "${LOG_DIR}/postgres.log" -w start
  fi
  for _ in $(seq 1 30); do
    "${PGBIN}/pg_isready" -h 127.0.0.1 -p 5432 >/dev/null 2>&1 && break
    sleep 1
  done

  echo "==> Launching application processes"
  launch api 8000 fateradar-cloud-agent-api \
    uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
  api_pid="$SERVICE_PID"
  launch worker "" fateradar-cloud-agent-worker \
    uv run --directory backend python -m worker.main --poll-interval 2
  worker_pid="$SERVICE_PID"
  launch web 3000 fateradar-cloud-agent-web \
    npm --prefix web run dev
  web_pid="$SERVICE_PID"
  launch admin 3001 fateradar-cloud-agent-admin \
    npm --prefix admin run dev
  admin_pid="$SERVICE_PID"

  echo "==> Verifying application health"
  wait_for_service api fateradar-cloud-agent-api "$api_pid" api_live
  wait_for_service api fateradar-cloud-agent-api "$api_pid" api_ready
  wait_for_service web fateradar-cloud-agent-web "$web_pid" port_listening 3000
  wait_for_service admin fateradar-cloud-agent-admin "$admin_pid" port_listening 3001
  if ! process_matches "$worker_pid" fateradar-cloud-agent-worker; then
    service_error worker "exited during health verification"
    return 1
  fi

  echo "==> Start reconciliation complete (API :8000, Web :3000, Admin :3001)"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  start_main "$@"
fi
