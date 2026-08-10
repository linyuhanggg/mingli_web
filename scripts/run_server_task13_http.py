#!/usr/bin/env python3
"""Direct HTTP Task13 trajectory against local API on test server."""
from __future__ import annotations
import json, re, sys, time, uuid
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/v1"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/task13-server-trajectory-v2")
OUT.mkdir(parents=True, exist_ok=True)
SENS = re.compile(r"state_token|DEEPSEEK_API_KEY|sk-[A-Za-z0-9]{10,}|BEGIN (RSA |OPENSSH )?PRIVATE", re.I)

class C:
    def __init__(self):
        self.jar=CookieJar(); self.op=build_opener(HTTPCookieProcessor(self.jar)); self.csrf=""
    def req(self, method, path, body=None):
        data=None if body is None else json.dumps(body).encode()
        h={"Content-Type":"application/json","Accept":"application/json"}
        if self.csrf: h["X-CSRF-Token"]=self.csrf
        r=Request(API+path, data=data, headers=h, method=method)
        try:
            with self.op.open(r, timeout=60) as resp:
                raw=resp.read().decode(); code=resp.getcode()
        except HTTPError as e:
            raw=e.read().decode("utf-8","replace"); code=e.code
        except URLError as e:
            return 0, {"error":str(e)}, str(e)
        try: parsed=json.loads(raw) if raw else None
        except Exception: parsed={"raw":raw[:400]}
        return code, parsed, raw

def log(m):
    print(m, flush=True)
    with (OUT/"console.log").open("a") as f: f.write(m+"\n")

def poll(c, vid, want, tries=90):
    last={}
    for i in range(1,tries+1):
        code,body,raw=c.req("GET", f"/readings/{vid}")
        st=str((body or {}).get("status") or "")
        log(f"poll {vid} #{i} http={code} status={st or '?'}")
        if isinstance(body,dict): last=body
        if st in want: return st,last
        if st in {"terminal_stopped","runtime_unknown"}: return st,last
        time.sleep(2)
    return str(last.get("status") or "timeout"), last

def save_safe(name, body):
    panel=body.get("fact_panel") or {}
    safe={"status":body.get("status"),"capability_id":body.get("capability_id"),"reading_version_id":body.get("reading_version_id"),"accepted_copy_len":len(body.get("accepted_copy") or ""),"accepted_copy_prefix":(body.get("accepted_copy") or "")[:80],"fact_count":len(panel.get("facts") or []), "limit_ids":[i.get("kind_id") for i in (panel.get("limits") or []) if isinstance(i,dict)]}
    (OUT/f"{name}-safe.json").write_text(json.dumps(safe,ensure_ascii=False,indent=2)+"\n")

def run_reading(c, report, name, path, payload):
    code,body,raw=c.req("POST", path, payload)
    if SENS.search(raw or ""): log(f"SENSITIVE {name}-start")
    vid=(body or {}).get("reading_version_id") if isinstance(body,dict) else None
    if code not in {200,201} or not vid:
        report[name]={"status":"fail","detail":f"start_http={code} body={str(body)[:180]}"}
        log(f"{name} start fail {code}")
        return None
    log(f"{name} started {vid}")
    st,summary=poll(c, vid, {"accepted","waiting_input","delayed"})
    if st=="waiting_input":
        c.req("POST", f"/readings/{vid}/input", {"values":{"cast_1":8,"cast_2":7,"cast_3":8,"cast_4":7,"cast_5":8,"cast_6":7}})
        st,summary=poll(c, vid, {"accepted","delayed"})
    if st=="accepted":
        code,result,raw=c.req("GET", f"/readings/{vid}/result")
        if SENS.search(raw or ""): log(f"SENSITIVE {name}-result")
        if isinstance(result,dict): save_safe(name,result)
        report[name]={"status":"accepted","version_id":vid}
        log(f"{name} accepted")
        return vid
    report[name]={"status":st or "fail","version_id":vid}
    log(f"{name} ended {st}")
    return vid

def main():
    (OUT/"console.log").write_text("")
    c=C(); report={}
    email=f"task13.fix.{uuid.uuid4().hex[:10]}@example.com"
    log(f"START {API} {email}")
    code,body,raw=c.req("POST","/guest-sessions",{})
    assert code==201 and isinstance(body,dict), body
    c.csrf=str(body.get("csrf_token") or ""); report["guest"]={"status":"ok"}
    code,body,raw=c.req("POST","/auth/otp/request",{"channel":"email","destination":email})
    assert code in {200,202}, body
    cid=body.get("challenge_id"); codev=body.get("development_code") or "246810"
    code,body,raw=c.req("POST","/auth/otp/verify",{"challenge_id":cid,"code":codev})
    assert code==200, body
    c.csrf=str(body.get("csrf_token") or c.csrf); report["login"]={"status":"ok","user_id":body.get("user_id")}
    code,body,raw=c.req("POST","/profiles/drafts",{"label":"本人"})
    assert code==201 and body.get("draft_id"), body
    did=body["draft_id"]
    code,body,raw=c.req("POST", f"/profiles/drafts/{did}/confirm", {
        "birth_datetime":"1994-04-30T05:55:00+08:00","timezone":"Asia/Shanghai","location":"福建省福州市","gender":"female",
        "time_basis_policy":"civil","zi_hour_policy":"midnight","longitude":119.2965,"latitude":26.0745,"coordinate_source":"user_confirmed"
    })
    assert code==201 and body.get("profile_version_id"), body
    pvid=body["profile_version_id"]; report["profile"]={"status":"ok","profile_version_id":pvid}
    preview=run_reading(c,report,"preview","/readings/preview",{"profile_version_id":pvid,"dimension_ids":["career"],"query":"看一下事业结构"})
    today=run_reading(c,report,"today","/readings/today",{"profile_version_id":pvid,"query":"今日运势"})
    week=run_reading(c,report,"week","/readings/week",{"profile_version_id":pvid,"query":"近七日运势"})
    liuyao=run_reading(c,report,"liuyao","/readings/liuyao",{"cast":"digital_coin","event_datetime":"2026-08-10T12:00:00+08:00","timezone":"Asia/Shanghai","location":"北京市朝阳区","dimension_ids":["career"],"query":"一事一问测试"})
    base=next((v for v in (preview,today,week,liuyao) if v and report.get(next(k for k,val in report.items() if val.get("version_id")==v),{}).get("status")=="accepted"), None)
    # simpler base selection
    base=None
    for name in ("preview","today","week","liuyao"):
        if report.get(name,{}).get("status")=="accepted":
            base=report[name]["version_id"]; break
    if base:
        code,body,raw=c.req("POST", f"/readings/{base}/follow-up", {"query":"基于已有结论，补充注意事项"})
        fu=(body or {}).get("reading_version_id") if isinstance(body,dict) else None
        if fu:
            st,summary=poll(c,fu,{"accepted","delayed"})
            if st=="accepted":
                code,result,raw=c.req("GET", f"/readings/{fu}/result")
                if isinstance(result,dict): save_safe("followup", result)
                report["followup"]={"status":"accepted","version_id":fu,"from":base}
            else:
                report["followup"]={"status":st or "fail","version_id":fu,"from":base}
        else:
            report["followup"]={"status":"fail","detail":str(body)[:180]}
    else:
        report["followup"]={"status":"skipped","detail":"no_accepted_base"}
    code,body,raw=c.req("GET","/readings")
    report["list_scan"]={"status":"ok" if code==200 else "fail","http":code}
    accepted=sum(1 for v in report.values() if v.get("status")=="accepted")
    summary={"schema":"task13-server-trajectory-v2","api":API,"tracks":report,"totals":{"tracks":len(report),"accepted":accepted},"fix":"candidate_reference_closer deployed"}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    log(f"DONE {summary['totals']}")
    product=[k for k in ("preview","today","week","liuyao","followup") if report.get(k,{}).get("status")=="accepted"]
    return 0 if product else 1

if __name__=="__main__":
    raise SystemExit(main())
