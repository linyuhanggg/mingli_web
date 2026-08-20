#!/usr/bin/env bash
# Cloud Agent start script for mingli_web.
#
# Per-boot reconciliation: ensures PostgreSQL is running and (re)launches the
# four application processes (FastAPI API, async Worker, Web dev server, Admin
# dev server) detached, without creating duplicates, then returns. Logs are
# written to ~/logs/. All adapters default to the local fakes (OTP/Runtime/
# Model), so no external secrets are required.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PATH="$HOME/.local/bin:$PATH"
export TZ=Asia/Shanghai
export MINGLI_ENVIRONMENT=local
export MINGLI_DATABASE_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli"
export BACKEND_INTERNAL_URL="http://127.0.0.1:8000"

PGBIN="/usr/lib/postgresql/16/bin"
export PGDATA="$HOME/pgdata"
LOG_DIR="$HOME/logs"
mkdir -p "$HOME/pgrun" "$LOG_DIR"

echo "==> Ensuring PostgreSQL is running"
if ! "${PGBIN}/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  "${PGBIN}/pg_ctl" -D "$PGDATA" -o "-p 5432" -l "${LOG_DIR}/postgres.log" -w start
fi
for _ in $(seq 1 30); do
  "${PGBIN}/pg_isready" -h 127.0.0.1 -p 5432 >/dev/null 2>&1 && break
  sleep 1
done

port_listening() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

launch() { # name  port_or_empty  pgrep_pattern  command...
  local name="$1"; local port="$2"; local pattern="$3"; shift 3
  if { [ -n "$port" ] && port_listening "$port"; } || pgrep -f "$pattern" >/dev/null 2>&1; then
    echo "    ${name} already running${port:+ (port ${port})}"
    return 0
  fi
  echo "    starting ${name}${port:+ (port ${port})}"
  setsid nohup "$@" >"${LOG_DIR}/${name}.log" 2>&1 &
}

echo "==> Launching application processes"
launch api    8000 "uvicorn app.main:app" \
  uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
launch worker ""   "worker.main" \
  uv run --directory backend python -m worker.main --poll-interval 2
launch web    3000 "next dev" \
  npm --prefix web run dev
launch admin  3001 "next dev -p 3001" \
  npm --prefix admin run dev

echo "==> Start reconciliation complete (API :8000, Web :3000, Admin :3001)"
