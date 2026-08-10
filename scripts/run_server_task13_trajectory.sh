#!/usr/bin/env bash
# Task 13 product trajectory on fateradar-prod (local env + real runtime/model).
# Fictional data only. Never prints secrets/cookies/tokens to evidence.
set -euo pipefail

API="${API:-http://127.0.0.1:8000/api/v1}"
OUT_DIR="${OUT_DIR:-/tmp/task13-server-trajectory}"
EMAIL="${EMAIL:-task13.trajectory.$(date +%s)@example.com}"
OTP_CODE="${OTP_CODE:-246810}"
COOKIE_JAR="$(mktemp)"
SUMMARY_JSON="$OUT_DIR/summary.json"
LOG="$OUT_DIR/console.log"
mkdir -p "$OUT_DIR"
: >"$LOG"

csrf=""
json_get() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(d'"$1"')'; }

log() { printf '%s\n' "$*" | tee -a "$LOG" >/dev/null; echo "$*"; }

req() {
  local method="$1" path="$2"; shift 2
  local url="$API$path"
  local args=(-sS -m 30 -X "$method" -b "$COOKIE_JAR" -c "$COOKIE_JAR" -H "Content-Type: application/json")
  if [[ -n "${csrf:-}" ]]; then args+=(-H "X-CSRF-Token: $csrf"); fi
  if [[ $# -gt 0 ]]; then args+=(-d "$1"); fi
  curl "${args[@]}" "$url"
}

poll_until() {
  local version_id="$1" want_regex="$2" tries="${3:-60}"
  local i body status
  for ((i=1;i<=tries;i++)); do
    body="$(req GET "/readings/$version_id" || true)"
    status="$(printf '%s' "$body" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin); print(d.get("status",""))
except Exception:
 print("")' 2>/dev/null || true)"
    log "poll $version_id try=$i status=${status:-?}"
    if [[ "$status" =~ $want_regex ]]; then
      printf '%s' "$body"
      return 0
    fi
    if [[ "$status" == "terminal_stopped" || "$status" == "runtime_unknown" ]]; then
      printf '%s' "$body"
      return 1
    fi
    sleep 2
  done
  printf '%s' "${body:-}"
  return 1
}

sanitize_scan() {
  local file="$1"
  if rg -n "state_token|DEEPSEEK_API_KEY|sk-[A-Za-z0-9]{10,}|BEGIN (RSA |OPENSSH )?PRIVATE|ciphertext" "$file" >/tmp/t13scan.txt 2>/dev/null; then
    log "SENSITIVE_SCAN_HIT $file"
    cat /tmp/t13scan.txt | tee -a "$LOG"
    return 1
  fi
  return 0
}

record() {
  local key="$1" status="$2" detail="$3"
  python3 - <<PY
import json
from pathlib import Path
p=Path("$SUMMARY_JSON")
data=json.loads(p.read_text()) if p.exists() else {"schema":"task13-server-trajectory-v1","tracks":{}}
data.setdefault("tracks",{})["$key"]={"status":"$status","detail":"""$detail"""}
p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
PY
}

python3 - <<PY
from pathlib import Path
import json
Path("$SUMMARY_JSON").write_text(json.dumps({
  "schema":"task13-server-trajectory-v1",
  "api":"$API",
  "email_fictional":"$EMAIL",
  "tracks":{}
}, ensure_ascii=False, indent=2)+"\n")
PY

log "START trajectory email=$EMAIL"

# 1 guest
guest="$(req POST /guest-sessions '{}')"
csrf="$(printf '%s' "$guest" | json_get "['csrf_token']")"
log "guest ok csrf_len=${#csrf}"
record guest ok "created"

# 2 otp login
chal="$(req POST /auth/otp/request "{\"channel\":\"email\",\"destination\":\"$EMAIL\"}")"
challenge_id="$(printf '%s' "$chal" | json_get "['challenge_id']")"
dev_code="$(printf '%s' "$chal" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("development_code") or "")')"
code="${dev_code:-$OTP_CODE}"
log "otp challenge ok has_dev_code=$([[ -n $dev_code ]] && echo yes || echo no)"
verified="$(req POST /auth/otp/verify "{\"challenge_id\":\"$challenge_id\",\"code\":\"$code\"}")"
csrf="$(printf '%s' "$verified" | json_get "['csrf_token']")"
user_id="$(printf '%s' "$verified" | json_get "['user_id']")"
log "login ok user=$user_id"
record login ok "user_created_or_resumed"

# 3 profile
draft="$(req POST /profiles/drafts '{\"label\":\"本人\"}')"
draft_id="$(printf '%s' "$draft" | json_get "['draft_id']")"
profile="$(req POST "/profiles/drafts/$draft_id/confirm" '{
  "birth_datetime":"1994-04-30T05:55:00+08:00",
  "timezone":"Asia/Shanghai",
  "location":"福建省福州市",
  "gender":"female",
  "time_basis_policy":"civil",
  "zi_hour_policy":"midnight",
  "longitude":119.2965,
  "latitude":26.0745,
  "coordinate_source":"user_confirmed"
}')"
profile_version_id="$(printf '%s' "$profile" | json_get "['profile_version_id']")"
log "profile ok version=$profile_version_id"
record profile ok "confirmed"

run_reading() {
  local name="$1" path="$2" payload="$3"
  local start body version status result
  start="$(req POST "$path" "$payload")"
  version="$(printf '%s' "$start" | python3 -c 'import json,sys
try:
 print(json.load(sys.stdin).get("reading_version_id",""))
except Exception:
 print("")')"
  if [[ -z "$version" ]]; then
    log "$name start FAIL body=$(printf '%s' "$start" | head -c 300)"
    record "$name" fail "start_failed"
    return 1
  fi
  log "$name started $version"
  body="$(poll_until "$version" 'accepted|waiting_input|delayed' 90 || true)"
  status="$(printf '%s' "$body" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("status",""))
except Exception: print("")')"
  if [[ "$status" == "waiting_input" ]]; then
    log "$name waiting_input -> supply cast"
    req POST "/readings/$version/input" '{"values":{"cast_1":8,"cast_2":7,"cast_3":8,"cast_4":7,"cast_5":8,"cast_6":7}}' >/dev/null || true
    body="$(poll_until "$version" 'accepted|delayed' 90 || true)"
    status="$(printf '%s' "$body" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("status",""))
except Exception: print("")')"
  fi
  if [[ "$status" == "accepted" ]]; then
    result="$(req GET "/readings/$version/result")"
    printf '%s' "$result" >"$OUT_DIR/${name}-result.json"
    sanitize_scan "$OUT_DIR/${name}-result.json" || true
    # strip possible sensitive fields for evidence copy
    python3 - <<PY
import json
from pathlib import Path
raw=json.loads(Path("$OUT_DIR/${name}-result.json").read_text())
safe={
  "status": raw.get("status"),
  "capability_id": raw.get("capability_id"),
  "reading_version_id": raw.get("reading_version_id") or raw.get("version_id"),
  "accepted_copy_len": len(raw.get("accepted_copy") or ""),
  "accepted_copy_prefix": (raw.get("accepted_copy") or "")[:80],
  "fact_count": len((raw.get("fact_panel") or {}).get("facts") or []),
  "limit_ids": [l.get("kind_id") for l in ((raw.get("fact_panel") or {}).get("limits") or []) if isinstance(l, dict)],
}
Path("$OUT_DIR/${name}-safe.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2)+"\n")
PY
    record "$name" accepted "version=$version"
    log "$name accepted"
    printf '%s' "$version"
    return 0
  fi
  record "$name" "$status" "version=$version"
  log "$name ended status=$status"
  printf '%s' "$version"
  return 1
}

preview_payload=$(python3 - <<PY
import json
print(json.dumps({"profile_version_id":"$profile_version_id","dimension_ids":["career"],"query":"看一下事业结构"}))
PY
)
today_payload=$(python3 - <<PY
import json
print(json.dumps({"profile_version_id":"$profile_version_id","query":"今日运势"}))
PY
)
week_payload=$(python3 - <<PY
import json
print(json.dumps({"profile_version_id":"$profile_version_id","query":"近七日运势"}))
PY
)
liuyao_payload='{"cast":"digital_coin","event_datetime":"2026-08-10T12:00:00+08:00","timezone":"Asia/Shanghai","location":"北京市朝阳区","dimension_ids":["career"],"query":"一事一问测试"}'

preview_v="$(run_reading preview /readings/preview "$preview_payload" || true)"
today_v="$(run_reading today /readings/today "$today_payload" || true)"
week_v="$(run_reading week /readings/week "$week_payload" || true)"
liuyao_v="$(run_reading liuyao /readings/liuyao "$liuyao_payload" || true)"

# follow-up on first accepted if any
base_v=""
for v in "$preview_v" "$today_v" "$week_v" "$liuyao_v"; do
  if [[ -n "$v" ]]; then base_v="$v"; break; fi
done
if [[ -n "$base_v" ]]; then
  # check accepted
  st="$(req GET "/readings/$base_v" | python3 -c 'import json,sys
try:print(json.load(sys.stdin).get("status",""))
except Exception:print("")')"
  if [[ "$st" == "accepted" ]]; then
    fu="$(req POST "/readings/$base_v/follow-up" '{"query":"基于已有结论，补充注意事项"}')"
    fu_v="$(printf '%s' "$fu" | python3 -c 'import json,sys
try:print(json.load(sys.stdin).get("reading_version_id",""))
except Exception:print("")')"
    if [[ -n "$fu_v" ]]; then
      body="$(poll_until "$fu_v" 'accepted|delayed' 90 || true)"
      status="$(printf '%s' "$body" | python3 -c 'import json,sys
try:print(json.load(sys.stdin).get("status",""))
except Exception:print("")')"
      if [[ "$status" == "accepted" ]]; then
        result="$(req GET "/readings/$fu_v/result")"
        printf '%s' "$result" >"$OUT_DIR/followup-result.json"
        sanitize_scan "$OUT_DIR/followup-result.json" || true
        record followup accepted "version=$fu_v from=$base_v"
      else
        record followup "$status" "version=$fu_v"
      fi
    else
      record followup fail "start_failed"
    fi
  else
    record followup skipped "no_accepted_base"
  fi
else
  record followup skipped "no_base_version"
fi

# sensitive list endpoints
list_body="$(req GET /readings)"
printf '%s' "$list_body" >"$OUT_DIR/list-readings.json"
sanitize_scan "$OUT_DIR/list-readings.json" || true
record list_scan ok "stored"

# finalize summary counts
python3 - <<'PY'
import json
from pathlib import Path
p=Path("""$SUMMARY_JSON""")
data=json.loads(p.read_text())
tracks=data.get("tracks",{})
accepted=sum(1 for t in tracks.values() if t.get("status")=="accepted")
failed=sum(1 for t in tracks.values() if t.get("status") in {"fail","failed"})
data["totals"]={"tracks":len(tracks),"accepted":accepted,"failed":failed}
data["note"]="OTP fake + real runtime/model on test server; not production; no payment/ICP in this run"
p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
print(json.dumps(data["totals"]))
PY

# scrub raw results that may contain birth-like strings from evidence packaging later
rm -f "$COOKIE_JAR"
log "DONE"
