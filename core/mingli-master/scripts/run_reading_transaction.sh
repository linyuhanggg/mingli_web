#!/bin/sh
# Optional POSIX bootstrap for the JSON codec. One exec, no probe, no
# subcommands: the Python interface is the cross-host authority. When the
# pinned runtime is missing, still emit one minimal parsable Stopped Result
# on stdout so a started process never returns empty output.
set -eu

skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
emit_stopped() {
    printf '%s\n' '{"kind":"stopped","reason":"error","public_copy":"本次处理未完成，请稍后重试。","state_token":null}'
    printf '%s\n' "$1" >&2
}

if [ -n "${MINGLI_PYTHON:-}" ]; then
    runtime=$MINGLI_PYTHON
elif [ -n "${HOME:-}" ]; then
    runtime="$HOME/.local/share/mingli-master/venv/bin/python"
else
    emit_stopped "Mingli runtime is unavailable: HOME is not set"
    exit 0
fi
export PYTHONDONTWRITEBYTECODE=1

case "${runtime##*/}" in
    python*) : ;;
    *)
        emit_stopped "MINGLI_PYTHON is not a pinned Python runtime: $runtime"
        exit 0
        ;;
esac

if [ ! -x "$runtime" ]; then
    emit_stopped "Mingli runtime is unavailable: $runtime"
    printf '%s\n' "Run scripts/provision_runtime.py before starting a reading." >&2
    exit 0
fi

if [ ! -r "$skill_dir/scripts/runtime_launcher.py" ]; then
    emit_stopped "Mingli runtime bootstrap is unavailable"
    exit 0
fi

if exec "$runtime" -I -S -B "$skill_dir/scripts/runtime_launcher.py" "$@"; then
    exit 0
fi
emit_stopped "Mingli runtime bootstrap could not start"
exit 0
