#!/usr/bin/env bash
# Cloud Agent install script for mingli_web.
#
# Idempotent repository bootstrap: installs toolchains and dependencies, prepares
# a local PostgreSQL 16 cluster, applies Alembic migrations, and registers a
# local fake Runtime contract so the deterministic chart flow works end to end
# with the default fake Runtime/Model/OTP adapters. Safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PG_MAJOR=16
PGBIN="/usr/lib/postgresql/${PG_MAJOR}/bin"
PGDATA="$HOME/pgdata"
PGRUN="$HOME/pgrun"
LOCAL_DATABASE_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli"
LOCAL_PSQL_URL="postgresql://mingli:mingli-local@127.0.0.1:5432/mingli"
ADMIN_CONFIG_DIR="$HOME/.config/fateradar-cloud-agent"
ADMIN_ENV_FILE="${ADMIN_CONFIG_DIR}/local.env"

configure_local_environment() {
  export PATH="$HOME/.local/bin:$PATH"
  export PGDATA
  export MINGLI_ENVIRONMENT=local
  # Never let an inherited database target redirect local migrations or seed data.
  export MINGLI_DATABASE_URL="$LOCAL_DATABASE_URL"
}

ensure_admin_bootstrap_environment() {
  mkdir -p "$ADMIN_CONFIG_DIR"
  chmod 700 "$ADMIN_CONFIG_DIR"

  if [ -f "$ADMIN_ENV_FILE" ]; then
    chmod 600 "$ADMIN_ENV_FILE"
    if ! (
      set -u
      # shellcheck disable=SC1090 -- this is the file created just below.
      source "$ADMIN_ENV_FILE"
      [ -n "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ]
      [ -n "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}" ]
    ); then
      echo "ERROR: ${ADMIN_ENV_FILE} is missing local Admin bootstrap values" >&2
      return 1
    fi
    echo "==> Reusing local Admin bootstrap file at ${ADMIN_ENV_FILE}"
    return 0
  fi

  if { [ -n "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ] && [ -z "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}" ]; } || \
     { [ -z "${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-}" ] && [ -n "${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}" ]; }; then
    echo "ERROR: set both MINGLI_ADMIN_BOOTSTRAP_EMAIL and MINGLI_ADMIN_BOOTSTRAP_PASSWORD, or neither" >&2
    return 1
  fi

  local email="${MINGLI_ADMIN_BOOTSTRAP_EMAIL:-cloud-agent-admin@example.com}"
  local password="${MINGLI_ADMIN_BOOTSTRAP_PASSWORD:-}"
  if [ -z "$password" ]; then
    password="$(uv run --project backend python -c 'import secrets; print(secrets.token_urlsafe(24))')"
  fi

  (
    umask 077
    {
      printf 'export MINGLI_ADMIN_BOOTSTRAP_EMAIL=%q\n' "$email"
      printf 'export MINGLI_ADMIN_BOOTSTRAP_PASSWORD=%q\n' "$password"
    } >"$ADMIN_ENV_FILE"
  )
  chmod 600 "$ADMIN_ENV_FILE"
  echo "==> Created local Admin bootstrap file at ${ADMIN_ENV_FILE}"
  echo "    Admin email: ${email}; read the password from that 0600 file"
}

register_local_fake_runtime() {
  local checkout_sha
  checkout_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"

  # This row is a local fake-adapter contract keyed to this checkout. It is not
  # a formal Runtime release and must never be copied to staging or production.
  "${PGBIN}/psql" "$LOCAL_PSQL_URL" -v ON_ERROR_STOP=1 \
    -v checkout_sha="$checkout_sha" -c "
INSERT INTO runtime_releases
  (id, name, version, source_commit, release_manifest_digest,
   protocol_version, describe_manifest_digest, image_digest, production_ready)
VALUES
  (gen_random_uuid(), 'fateradar-fake-contract', 'test-v1', :'checkout_sha',
   rpad(:'checkout_sha', 64, '0'),
   'mingli-portable-interface-v2', repeat('f', 64), NULL, true)
ON CONFLICT (release_manifest_digest)
  DO UPDATE SET production_ready = EXCLUDED.production_ready;"
}

install_main() {
  cd "$REPO_ROOT"
  configure_local_environment

  echo "==> Ensuring system dependencies (PostgreSQL ${PG_MAJOR}, uv)"
  if [ ! -x "${PGBIN}/initdb" ]; then
    echo "    Installing PostgreSQL ${PG_MAJOR} via apt"
    sudo apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
      "postgresql-${PG_MAJOR}" "postgresql-client-${PG_MAJOR}"
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "    Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi

  echo "==> Installing backend Python dependencies (uv)"
  uv sync --project backend --group dev

  echo "==> Installing web dependencies (npm)"
  npm install --prefix web

  echo "==> Installing admin dependencies (npm)"
  npm install --prefix admin

  ensure_admin_bootstrap_environment

  echo "==> Preparing PostgreSQL cluster at ${PGDATA}"
  mkdir -p "$PGRUN"
  if [ ! -f "${PGDATA}/PG_VERSION" ]; then
    "${PGBIN}/initdb" -D "$PGDATA" -U postgres --auth-local=trust --auth-host=trust
    sed -i "s/^#*listen_addresses.*/listen_addresses = '127.0.0.1'/" "${PGDATA}/postgresql.conf"
    sed -i "s|^#*unix_socket_directories.*|unix_socket_directories = '${PGRUN}'|" "${PGDATA}/postgresql.conf"
  fi

  echo "==> Starting PostgreSQL (idempotent)"
  if ! "${PGBIN}/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
    "${PGBIN}/pg_ctl" -D "$PGDATA" -o "-p 5432" -l "$HOME/logs-postgres.log" -w start
  fi
  for _ in $(seq 1 30); do
    "${PGBIN}/pg_isready" -h 127.0.0.1 -p 5432 >/dev/null 2>&1 && break
    sleep 1
  done

  echo "==> Ensuring database role and database"
  "${PGBIN}/psql" -U postgres -h 127.0.0.1 -p 5432 -tc \
    "SELECT 1 FROM pg_roles WHERE rolname='mingli'" | grep -q 1 || \
    "${PGBIN}/psql" -U postgres -h 127.0.0.1 -p 5432 -c \
    "CREATE ROLE mingli LOGIN PASSWORD 'mingli-local'"
  "${PGBIN}/psql" -U postgres -h 127.0.0.1 -p 5432 -tc \
    "SELECT 1 FROM pg_database WHERE datname='mingli'" | grep -q 1 || \
    "${PGBIN}/psql" -U postgres -h 127.0.0.1 -p 5432 -c \
    "CREATE DATABASE mingli OWNER mingli"

  echo "==> Applying Alembic migrations to the local database"
  uv run --project backend alembic -c backend/alembic.ini upgrade head

  echo "==> Registering local fake Runtime contract (idempotent)"
  register_local_fake_runtime

  echo "==> Install complete"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  install_main "$@"
fi
