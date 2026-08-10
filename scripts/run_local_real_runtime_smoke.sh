#!/usr/bin/env bash
#
# Local real Runtime + (optional) real model smoke - fail-closed, secret-safe.
#
# Purpose
#   Re-runnable version of the local real-path smoke that was previously done by
#   hand: admit the real one-shot Runtime via build_runtime_startup_gate(...)
#   and, when a key is present, run one real bazi prepare + one real model
#   generate against the frozen P0 profile.
#
# Secrets
#   The private env file (~/.config/mingli/local-real-model.env, mode 600) is
#   sourced but NEVER printed, echoed, diffed or committed. This script and the
#   Python entry it calls must never write DEEPSEEK_API_KEY (or any credential)
#   to stdout, logs or the evidence directory.
#
# Usage
#   scripts/run_local_real_runtime_smoke.sh [--model] [--skip-model]
#       [--env-file PATH] [--evidence-dir DIR]
#
#   Default (auto)   : Runtime startup gate always runs. The real-model smoke
#                      runs only when DEEPSEEK_API_KEY is present in the env.
#   --model          : force the real-model smoke; fail-closed when the key or
#                      the price snapshot is missing.
#   --skip-model     : never run the real-model smoke (Runtime gate only).
#   --env-file PATH  : override the private env file location.
#   --evidence-dir   : write non-sensitive summaries (console log + JSON) here.
#
# Exit codes
#   0  ok
#   2  local env file / runtime paths / key missing (clear message, nothing run)
#   3  real Runtime startup admission failed
#   4  real model smoke failed (network, model rejection, or missing key when
#      --model was forced)
#   1  unexpected failure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODE="auto"
ENV_FILE="${MINGLI_LOCAL_REAL_MODEL_ENV:-$HOME/.config/mingli/local-real-model.env}"
EVIDENCE_DIR=""

usage() {
    sed -n '2,30p' "$SCRIPT_DIR/run_local_real_runtime_smoke.sh" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --model) MODE="model" ;;
        --skip-model) MODE="runtime-only" ;;
        --env-file)
            [ $# -ge 2 ] || { echo "error: --env-file needs a path" >&2; exit 2; }
            ENV_FILE="$2"
            shift
            ;;
        --evidence-dir)
            [ $# -ge 2 ] || { echo "error: --evidence-dir needs a path" >&2; exit 2; }
            EVIDENCE_DIR="$2"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
    shift
done

fail_closed() {
    # shellcheck disable=SC2059
    printf 'SMOKE FAIL-CLOSED: %s\n' "$1" >&2
    exit 2
}

# --- 1. private env file -----------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    fail_closed "private env file not found: $ENV_FILE
Create it with mode 600, e.g.:
  install -m 600 /dev/null ~/.config/mingli/local-real-model.env
and set MINGLI_RUNTIME_ADAPTER=one-shot, the four MINGLI_RUNTIME_* paths,
the MINGLI_RUNTIME_EXPECTED_* digests, and (for the real-model step)
DEEPSEEK_API_KEY. Nothing is committed; keys live only on this machine."
fi

mode_octal="$(stat -f %Lp "$ENV_FILE" 2>/dev/null || stat -c %a "$ENV_FILE" 2>/dev/null)"
if [ -z "$mode_octal" ] || [ $(( 8#$mode_octal & 8#044 )) -ne 0 ]; then
    fail_closed "private env file must not be group/world readable (got mode $mode_octal): $ENV_FILE
Run: chmod 600 $ENV_FILE"
fi

# Source without echoing anything. The shell is never set -x here.
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

# --- 2. fail-closed runtime configuration checks -----------------------------
if [ "${MINGLI_RUNTIME_ADAPTER:-}" != "one-shot" ]; then
    fail_closed "MINGLI_RUNTIME_ADAPTER must be 'one-shot' (got '${MINGLI_RUNTIME_ADAPTER:-<unset>}') in $ENV_FILE"
fi

MISSING=""
for var in MINGLI_RUNTIME_LAUNCHER_PATH MINGLI_RUNTIME_PYTHON_PATH \
           MINGLI_RUNTIME_RELEASE_ROOT MINGLI_RUNTIME_STATE_ROOT \
           MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST \
           MINGLI_RUNTIME_EXPECTED_CAPABILITY_SHAPE_SHA256; do
    if [ -z "${!var:-}" ]; then
        MISSING="$MISSING $var"
    fi
done
if [ -n "$MISSING" ]; then
    fail_closed "missing runtime settings in $ENV_FILE:$MISSING"
fi

for var in MINGLI_RUNTIME_LAUNCHER_PATH MINGLI_RUNTIME_PYTHON_PATH; do
    if [ ! -f "${!var}" ]; then
        fail_closed "$var does not point to a file: ${!var}"
    fi
done
if [ ! -x "$MINGLI_RUNTIME_LAUNCHER_PATH" ]; then
    fail_closed "runtime launcher is not executable: $MINGLI_RUNTIME_LAUNCHER_PATH"
fi
for var in MINGLI_RUNTIME_RELEASE_ROOT MINGLI_RUNTIME_STATE_ROOT; do
    if [ ! -d "${!var}" ]; then
        fail_closed "$var does not point to a directory: ${!var}"
    fi
done

# --- 3. real-model gating ----------------------------------------------------
MODEL_FLAG="auto"
if [ "$MODE" = "model" ]; then
    if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
        fail_closed "DEEPSEEK_API_KEY is not set in $ENV_FILE (required by --model)"
    fi
    MODEL_FLAG="model"
elif [ "$MODE" = "runtime-only" ]; then
    MODEL_FLAG="skip"
elif [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo "note: DEEPSEEK_API_KEY absent - running Runtime startup only (use --model to force)."
    MODEL_FLAG="skip"
fi

# --- 4. run ------------------------------------------------------------------
ARGS=(--model-mode "$MODEL_FLAG")
if [ -n "$EVIDENCE_DIR" ]; then
    mkdir -p "$EVIDENCE_DIR"
    ARGS+=(--evidence-dir "$EVIDENCE_DIR")
fi

echo "runtime launcher : $MINGLI_RUNTIME_LAUNCHER_PATH"
echo "release root     : $MINGLI_RUNTIME_RELEASE_ROOT"
echo "state root       : $MINGLI_RUNTIME_STATE_ROOT"
echo "model mode       : $MODEL_FLAG"

set +e
(
    cd "$REPO_ROOT"
    uv run --project backend python scripts/smoke_local_real_runtime.py "${ARGS[@]}"
)
rc=$?
set -e
echo "SMOKE_EXIT_CODE=$rc"
exit "$rc"
