#!/bin/bash
cd /Volumes/Lexar/code/mingli_web
OUT=/Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-wenshi-grok.stdout.txt
ERR=/Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-wenshi-grok.stderr.txt
PROMPT=$(cat /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/_grok-wenshi-prompt.txt)
echo "START $(date)" > "$OUT"
echo "CMD /Users/yuhanglin/.grok/bin/grok -p <wenshi-prompt> --model grok-4.6 --reasoning-effort medium --cwd /Volumes/Lexar/code/mingli_web --output-format plain --always-approve" >> "$OUT"
/Users/yuhanglin/.grok/bin/grok -p "$PROMPT" --model grok-4.6 --reasoning-effort medium --cwd /Volumes/Lexar/code/mingli_web --output-format plain --always-approve >> "$OUT" 2> "$ERR"
echo EXIT:$? >> "$OUT"
