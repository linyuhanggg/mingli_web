#!/usr/bin/env bash
# Cloud Agent install script for mingli_web.
#
# Idempotent repository bootstrap: installs toolchains and dependencies, prepares
# a local PostgreSQL 16 cluster, applies Alembic migrations, and registers a
# local fake Runtime Release so the free deterministic chart flow works end to
# end with the default fake Runtime/Model/OTP adapters. Safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PATH="$HOME/.local/bin:$PATH"

PG_MAJOR=16
PGBIN="/usr/lib/postgresql/${PG_MAJOR}/bin"
export PGDATA="$HOME/pgdata"
PGRUN="$HOME/pgrun"

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

echo "==> Applying Alembic migrations"
uv run --project backend alembic -c backend/alembic.ini upgrade head

echo "==> Registering local fake Runtime Release (idempotent)"
# The reading pipeline requires a production-ready Runtime Release row. These are
# the frozen v51 identity digests used by the test suite; combined with the
# default fake Runtime adapter they enable the local free-chart flow. This is
# local development seed data only and never a production release.
"${PGBIN}/psql" "postgresql://mingli:mingli-local@127.0.0.1:5432/mingli" -v ON_ERROR_STOP=1 -c "
INSERT INTO runtime_releases
  (id, name, version, source_commit, release_manifest_digest,
   protocol_version, describe_manifest_digest, image_digest, production_ready)
VALUES
  (gen_random_uuid(), 'mingli-master-portable-core', '5.1',
   '494ce0bba174a77800daf9b9c38ce9c9166d9a94',
   'e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68',
   'mingli-portable-interface-v2',
   '7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342',
   NULL, true)
ON CONFLICT (release_manifest_digest)
  DO UPDATE SET production_ready = EXCLUDED.production_ready;"

echo "==> Install complete"
