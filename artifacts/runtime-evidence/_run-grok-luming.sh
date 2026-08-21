#!/bin/bash
set -euo pipefail
exec /Users/yuhanglin/.grok/bin/grok -p \
  --model grok-4.6 \
  --reasoning-effort high \
  --cwd /Volumes/Lexar/code/mingli_web \
  --output-format plain \
  --always-approve \
  --disable-web-search \
  --prompt-file /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/_grok-luming-prompt.txt
