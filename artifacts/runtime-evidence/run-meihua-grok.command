#!/bin/bash
cd /Volumes/Lexar/code/mingli_web
OUT=/Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-meihua-grok.stdout.txt
ERR=/Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-meihua-grok.stderr.txt
PROMPT=$(cat /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/_grok-meihua-prompt.txt)
echo "START $(date)" > "$OUT"
echo "CMD /Users/yuhanglin/.grok/bin/grok -p <meihua-prompt> --model grok-4.6 --effort medium --cwd /Volumes/Lexar/code/mingli_web --output-format plain --always-approve" >> "$OUT"
/Users/yuhanglin/.grok/bin/grok -p "$PROMPT" --model grok-4.6 --effort medium --cwd /Volumes/Lexar/code/mingli_web --output-format plain --always-approve >> "$OUT" 2> "$ERR"
echo EXIT:$? >> "$OUT"
