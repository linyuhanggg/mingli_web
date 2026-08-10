#!/usr/bin/env python3
"""Task 13 server trajectory payload - runs ON the test server (fateradar-prod).

Walks the real HTTP + Worker chain through the nginx loopback entry
(127.0.0.1:8080/api/v1, the same-origin path a browser would use):

    guest session -> email OTP (development_code=246810) -> verify -> profile
    draft -> confirm -> preview bazi (career) -> accepted -> today fortune ->
    accepted -> week fortune -> accepted -> liuyao digital_coin (supply
    cast 1..6 if waiting_input) -> accepted -> follow-up -> new version
    accepted.

Safety contract:
- Uses only fictional email / fictional birth data; never prints them raw.
- Never prints cookie values, CSRF tokens, API keys or state tokens.
- Raw HTTP bodies are kept only under --work-dir (0700) on the server and are
  never copied back to the repo; the summary JSON is sanitized.
- Scans every response body for state_token / raw birth datetime / prompt key
  / api key markers and for echo of any cookie token value.
- Reads the delayed backlog with a read-only status-count query (no writes).

Exit codes: 0 all required trajectories accepted; 1 partial (reasons recorded
in the summary JSON); 2 sensitive marker found (hard failure).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import socket
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
import httpx

API_BASE_DEFAULT = "http://127.0.0.1:8080/api/v1"
FAKE_OTP_CODE = "246810"
POLL_INTERVAL_S = 3.0
POLL_TIMEOUT_S = 480.0


def _env_query(*names: str, default: str) -> str:
    """Allow constrained re-runs without editing the script defaults.

    Each name is tried in order; the first environment variable that is set
    (even to the empty string) wins. Defaults keep the script reproducible
    with its original wording when no override is supplied.
    """

    import os

    for name in names:
        if name in os.environ:
            return os.environ[name]
    return default

# Fictional identity, deliberately not real personal data (same convention as
# backend/tests/test_email_user_journey.py).
FICTIONAL_PROFILE = {
    "birth_datetime": "1994-04-30T05:55:00+08:00",
    "timezone": "Asia/Shanghai",
    "location": "福建省福州市",
    "gender": "female",
    "time_basis_policy": "civil",
    "zi_hour_policy": "midnight",
    "longitude": 119.2965,
    "latitude": 26.0745,
    "coordinate_source": "user_confirmed",
}
RAW_BIRTH_DATETIME = FICTIONAL_PROFILE["birth_datetime"]
LIUYAO_CAST_VALUES = {"cast_1": 7, "cast_2": 8, "cast_3": 6,
                      "cast_4": 9, "cast_5": 7, "cast_6": 8}

CSRF_COOKIE = "mingli_csrf"
SESSION_COOKIE = "mingli_session"
GUEST_COOKIE = "mingli_guest"

# Non-secret adapter keys read from the server env file for the evidence record.
NON_SECRET_ENV_KEYS = (
    "MINGLI_ENVIRONMENT",
    "MINGLI_OTP_ADAPTER",
    "MINGLI_RUNTIME_ADAPTER",
    "MINGLI_MODEL_ADAPTER",
    "MINGLI_MODEL_ID",
    "MINGLI_MODEL_PROFILE_ID",
)

SENSITIVE_MARKERS: tuple[tuple[str, Any], ...] = (
    ("state_token", re.compile(r"state_token", re.IGNORECASE)),
    ("prompt_key", re.compile(r'"prompt"\s*:', re.IGNORECASE)),
    ("api_key", re.compile(r'"api[_-]?key"\s*:', re.IGNORECASE)),
    ("raw_birth_datetime", RAW_BIRTH_DATETIME),
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _masked_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 3:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***@{domain}"


def _scan_text(text: str) -> list[str]:
    found: list[str] = []
    for label, marker in SENSITIVE_MARKERS:
        if isinstance(marker, re.Pattern):
            if marker.search(text):
                found.append(label)
        elif marker in text:
            found.append(label)
    return found


class TrajectoryRunner:
    def __init__(
        self,
        *,
        api_base: str,
        work_dir: Path,
        env_file: Path,
    ) -> None:
        self.api_base = api_base
        self.work_dir = work_dir
        self.env_file = env_file
        self.raw_dir = work_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(base_url=api_base, timeout=40.0)
        self.steps: list[dict[str, Any]] = []
        self.sensitive_found: list[dict[str, str]] = []
        self.cookie_tokens: set[str] = set()
        self.transcript: list[dict[str, Any]] = []
        self._seq = 0
        self.email = ""

    # -- HTTP helpers ------------------------------------------------------

    def _csrf(self) -> dict[str, str]:
        token = self.client.cookies.get(CSRF_COOKIE)
        return {"X-CSRF-Token": token} if token else {}

    def _record_cookie_tokens(self) -> None:
        for name in (GUEST_COOKIE, SESSION_COOKIE, CSRF_COOKIE):
            value = self.client.cookies.get(name)
            if value:
                self.cookie_tokens.add(value)

    def request(
        self,
        method: str,
        path: str,
        *,
        step_id: str,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[httpx.Response, Any]:
        self._seq += 1
        started = time.monotonic()
        response = self.client.request(
            method,
            path,
            json=json_body,
            headers=headers,
        )
        duration_s = round(time.monotonic() - started, 2)
        body_text = response.text
        body: Any = None
        try:
            body = response.json()
        except ValueError:
            body = {"_non_json_body": body_text[:500]}
        self.transcript.append(
            {
                "seq": self._seq,
                "step_id": step_id,
                "method": method,
                "path": path,
                "status": response.status_code,
                "duration_s": duration_s,
            }
        )
        raw_path = self.raw_dir / f"{self._seq:03d}-{step_id}-{_slug(path)}.json"
        raw_path.write_text(
            json.dumps(
                {"method": method, "path": path, "status": response.status_code,
                 "body": body},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        for label in _scan_text(body_text):
            self.sensitive_found.append(
                {"marker": label, "step_id": step_id, "path": path}
            )
        for token in list(self.cookie_tokens):
            if token and token in body_text:
                self.sensitive_found.append(
                    {"marker": "cookie_token_echo", "step_id": step_id, "path": path}
                )
        self._record_cookie_tokens()
        return response, body

    def wait_terminal(
        self,
        reading_version_id: str,
        *,
        step_id: str,
    ) -> tuple[str, list[str], float]:
        started = time.monotonic()
        transitions: list[str] = []
        terminal = {
            "accepted",
            "delayed",
            "terminal_stopped",
            "runtime_unknown",
        }
        while time.monotonic() - started < POLL_TIMEOUT_S:
            response, body = self.request(
                "GET",
                f"/readings/{reading_version_id}",
                step_id=f"{step_id}-poll",
            )
            status = (body or {}).get("status")
            if status and (not transitions or transitions[-1] != status):
                transitions.append(status)
            if status in terminal:
                return status, transitions, round(time.monotonic() - started, 1)
            time.sleep(POLL_INTERVAL_S)
        return "timeout", transitions, round(time.monotonic() - started, 1)

    def fetch_result(self, reading_version_id: str, *, step_id: str) -> tuple[Any, int]:
        response, body = self.request(
            "GET",
            f"/readings/{reading_version_id}/result",
            step_id=f"{step_id}-result",
        )
        return body, response.status_code

    # -- trajectory steps --------------------------------------------------

    def step_guest_session(self) -> dict[str, Any]:
        step_id = "S1-guest-session"
        response, body = self.request("POST", "/guest-sessions", step_id=step_id)
        ok = response.status_code == 201 and body.get("csrf_token")
        if ok:
            self._record_cookie_tokens()
        return {
            "id": step_id,
            "name": "guest session",
            "ok": bool(ok),
            "http_status": response.status_code,
            "detail": {
                "csrf_matches_cookie": bool(
                    ok and body["csrf_token"] == self.client.cookies.get(CSRF_COOKIE)
                ),
                "expires_at": body.get("expires_at"),
            },
        }

    def step_otp(self, email: str) -> dict[str, Any]:
        step_id = "S2-email-otp"
        response, body = self.request(
            "POST",
            "/auth/otp/request",
            step_id=step_id,
            json_body={"channel": "email", "destination": email},
            headers=self._csrf(),
        )
        ok = response.status_code == 202 and bool(body.get("challenge_id"))
        dev_code = body.get("development_code")
        detail = {
            "development_code_matches": dev_code == FAKE_OTP_CODE,
            "retry_after_seconds": body.get("retry_after_seconds"),
        }
        return {
            "id": step_id,
            "name": "email OTP request",
            "ok": bool(ok and detail["development_code_matches"]),
            "http_status": response.status_code,
            "detail": detail,
            "_challenge_id": body.get("challenge_id"),
        }

    def step_verify(self, challenge_id: str) -> dict[str, Any]:
        step_id = "S3-otp-verify"
        response, body = self.request(
            "POST",
            "/auth/otp/verify",
            step_id=step_id,
            json_body={"challenge_id": challenge_id, "code": FAKE_OTP_CODE},
            headers=self._csrf(),
        )
        ok = response.status_code == 200 and bool(body.get("session_id"))
        if ok:
            self._record_cookie_tokens()
        return {
            "id": step_id,
            "name": "email OTP verify",
            "ok": bool(ok),
            "http_status": response.status_code,
            "detail": {
                "device_session_set": ok,
                "csrf_rotated": bool(
                    ok and body.get("csrf_token") == self.client.cookies.get(CSRF_COOKIE)
                ),
            },
        }

    def step_profile(self) -> dict[str, Any]:
        draft_id: str | None = None
        response, body = self.request(
            "POST",
            "/profiles/drafts",
            step_id="S4-profile-draft",
            json_body={"label": "本人"},
            headers=self._csrf(),
        )
        draft_ok = response.status_code == 201 and bool(body.get("draft_id"))
        if draft_ok:
            draft_id = body["draft_id"]
        detail: dict[str, Any] = {"draft_http_status": response.status_code}
        confirmed: dict[str, Any] = {}
        if draft_id:
            response, body = self.request(
                "POST",
                f"/profiles/drafts/{draft_id}/confirm",
                step_id="S5-profile-confirm",
                json_body=FICTIONAL_PROFILE,
                headers=self._csrf(),
            )
            confirmed = body or {}
            detail["confirm_http_status"] = response.status_code
            detail["profile_version_id"] = confirmed.get("profile_version_id")
            detail["subject_ref"] = confirmed.get("subject_ref")
            detail["private_headers"] = bool(
                response.headers.get("cache-control", "").startswith("private")
            )
        ok = bool(
            draft_ok
            and response.status_code == 201
            and confirmed.get("profile_version_id")
        )
        return {
            "id": "S4-S5-profile",
            "name": "profile draft + confirm (fictional)",
            "ok": ok,
            "http_status": response.status_code,
            "detail": detail,
            "_profile_version_id": confirmed.get("profile_version_id"),
        }

    def step_reading(
        self,
        *,
        step_id: str,
        name: str,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response, body = self.request(
            "POST",
            path,
            step_id=step_id,
            json_body=payload,
            headers={**self._csrf(), "Idempotency-Key": f"t13-{step_id}-{uuid4().hex[:20]}"},
        )
        version_id = (body or {}).get("reading_version_id")
        start_status = (body or {}).get("status")
        if not version_id:
            return {
                "id": step_id,
                "name": name,
                "ok": False,
                "http_status": response.status_code,
                "detail": {"start_status": start_status, "error": (body or {}).get("title")},
            }
        terminal, transitions, poll_s = self.wait_terminal(
            version_id,
            step_id=step_id,
        )
        result: dict[str, Any] = {}
        accepted_copy_digest: str | None = None
        if terminal == "accepted":
            result_body, result_status = self.fetch_result(version_id, step_id=step_id)
            accepted_copy = (result_body or {}).get("accepted_copy") or ""
            result = {
                "result_http_status": result_status,
                "accepted_copy_chars": len(accepted_copy),
                "accepted_copy_sha256": hashlib.sha256(
                    accepted_copy.encode("utf-8")
                ).hexdigest(),
                "verification": (result_body or {}).get("verification"),
            }
            if accepted_copy:
                accepted_copy_digest = result["accepted_copy_sha256"]
        ok = terminal == "accepted" and accepted_copy_digest is not None
        return {
            "id": step_id,
            "name": name,
            "ok": ok,
            "http_status": response.status_code,
            "detail": {
                "reading_version_id": version_id,
                "start_status": start_status,
                "status_path": transitions,
                "terminal_status": terminal,
                "poll_seconds": poll_s,
                **result,
            },
            "_version_id": version_id,
        }

    def step_liuyao(self, profile_version_id: str) -> dict[str, Any]:
        step_id = "S9-liuyao-digital-coin"
        now = datetime.now(UTC).astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
        payload = {
            "cast": "digital_coin",
            "event_datetime": f"{now}+08:00",
            "timezone": "Asia/Shanghai",
            "location": "福建省福州市",
            "subject_ref": "t13",
            "query": _env_query(
                "TASK13_QUERY_LIUYAO",
                default="请用数字卦看最近一次合作的结果走向",
            ),
            "dimension_ids": ["outcome"],
        }
        response, body = self.request(
            "POST",
            "/readings/liuyao",
            step_id=step_id,
            json_body=payload,
            headers={**self._csrf(), "Idempotency-Key": f"t13-{step_id}-{uuid4().hex[:20]}"},
        )
        version_id = (body or {}).get("reading_version_id")
        if not version_id:
            return {
                "id": step_id,
                "name": "liuyao digital_coin",
                "ok": False,
                "http_status": response.status_code,
                "detail": {"start_status": (body or {}).get("status"),
                           "error": (body or {}).get("title")},
            }
        start_status = (body or {}).get("status")
        supplied = False
        input_field_ids: list[str] = []
        if start_status == "waiting_input":
            result_body, _ = self.fetch_result(version_id, step_id=f"{step_id}-needinput")
            requirements = ((result_body or {}).get("input_request") or {}).get(
                "requirements"
            ) or []
            for requirement in requirements:
                for field in requirement.get("any_of") or []:
                    input_field_ids.append(str(field.get("id")))
            if set(input_field_ids) == set(LIUYAO_CAST_VALUES):
                response, body = self.request(
                    "POST",
                    f"/readings/{version_id}/input",
                    step_id=f"{step_id}-supply",
                    json_body={"values": LIUYAO_CAST_VALUES},
                    headers=self._csrf(),
                )
                supplied = response.status_code == 201
        terminal, transitions, poll_s = self.wait_terminal(version_id, step_id=step_id)
        result: dict[str, Any] = {}
        accepted_copy_digest: str | None = None
        if terminal == "accepted":
            result_body, result_status = self.fetch_result(version_id, step_id=step_id)
            accepted_copy = (result_body or {}).get("accepted_copy") or ""
            result = {
                "result_http_status": result_status,
                "accepted_copy_chars": len(accepted_copy),
                "accepted_copy_sha256": hashlib.sha256(
                    accepted_copy.encode("utf-8")
                ).hexdigest(),
            }
            if accepted_copy:
                accepted_copy_digest = result["accepted_copy_sha256"]
        ok = terminal == "accepted" and accepted_copy_digest is not None
        return {
            "id": step_id,
            "name": "liuyao digital_coin",
            "ok": ok,
            "http_status": response.status_code,
            "detail": {
                "reading_version_id": version_id,
                "start_status": start_status,
                "waiting_input": start_status == "waiting_input",
                "input_field_ids": input_field_ids,
                "supplied_six_cast_values": supplied,
                "status_path": transitions,
                "terminal_status": terminal,
                "poll_seconds": poll_s,
                **result,
            },
            "_version_id": version_id,
        }

    def step_follow_up(self, base_version_id: str) -> dict[str, Any]:
        step_id = "S10-follow-up"
        response, body = self.request(
            "POST",
            f"/readings/{base_version_id}/follow-up",
            step_id=step_id,
            json_body={
                "query": _env_query(
                    "TASK13_QUERY_FOLLOWUP",
                    default="针对刚才的事业预览，请再解读接下来三个月的关键节点",
                )
            },
            headers={**self._csrf(), "Idempotency-Key": f"t13-{step_id}-{uuid4().hex[:20]}"},
        )
        version_id = (body or {}).get("reading_version_id")
        if not version_id:
            return {
                "id": step_id,
                "name": "follow-up (new version)",
                "ok": False,
                "http_status": response.status_code,
                "detail": {"error": (body or {}).get("title")},
            }
        terminal, transitions, poll_s = self.wait_terminal(version_id, step_id=step_id)
        result: dict[str, Any] = {}
        accepted_copy_digest: str | None = None
        if terminal == "accepted":
            result_body, result_status = self.fetch_result(version_id, step_id=step_id)
            accepted_copy = (result_body or {}).get("accepted_copy") or ""
            result = {
                "result_http_status": result_status,
                "accepted_copy_chars": len(accepted_copy),
                "accepted_copy_sha256": hashlib.sha256(
                    accepted_copy.encode("utf-8")
                ).hexdigest(),
            }
            if accepted_copy:
                accepted_copy_digest = result["accepted_copy_sha256"]
        ok = terminal == "accepted" and accepted_copy_digest is not None
        return {
            "id": step_id,
            "name": "follow-up (new version)",
            "ok": ok,
            "http_status": response.status_code,
            "detail": {
                "base_reading_version_id": base_version_id,
                "reading_version_id": version_id,
                "status_path": transitions,
                "terminal_status": terminal,
                "poll_seconds": poll_s,
                **result,
            },
            "_version_id": version_id,
        }

    # -- delayed backlog (read-only) ----------------------------------------

    async def db_status_counts(self) -> dict[str, Any]:
        url = self._db_url_from_env()
        if url is None:
            return {"available": False, "reason": "MINGLI_DATABASE_URL not found in env file"}
        if url.startswith("postgresql+asyncpg://"):
            url = "postgresql://" + url[len("postgresql+asyncpg://"):]
        try:
            connection = await asyncpg.connect(url, timeout=10)
            try:
                rows = await connection.fetch(
                    "SELECT status, count(*) AS n FROM reading_versions "
                    "GROUP BY status ORDER BY status"
                )
                total = await connection.fetchval("SELECT count(*) FROM reading_versions")
            finally:
                await connection.close()
        except Exception as error:  # noqa: BLE001 - record any read failure honestly
            return {"available": False, "reason": f"read-only count failed: {type(error).__name__}"}
        counts = {row["status"]: row["n"] for row in rows}
        return {"available": True, "counts": counts, "total": total}

    def _db_url_from_env(self) -> str | None:
        try:
            for line in self.env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("MINGLI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            return None
        return None

    def adapters(self) -> dict[str, str]:
        values: dict[str, str] = {}
        try:
            text = self.env_file.read_text(encoding="utf-8")
        except OSError:
            return values
        for key in NON_SECRET_ENV_KEYS:
            match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
            if match:
                values[key] = match.group(1).strip().strip('"').strip("'")
        return values

    # -- run ----------------------------------------------------------------

    def run(self, email: str) -> dict[str, Any]:
        started = time.monotonic()
        self.email = email
        before = asyncio.run(self.db_status_counts())

        self.steps.append(self.step_guest_session())
        if not self.steps[-1]["ok"]:
            return self._finish(before, started)

        otp_step = self.step_otp(email)
        self.steps.append(otp_step)
        if otp_step["ok"] and otp_step.get("_challenge_id"):
            self.steps.append(self.step_verify(otp_step["_challenge_id"]))
        else:
            self.steps.append(
                {"id": "S3-otp-verify", "name": "email OTP verify",
                 "ok": False, "http_status": None, "detail": {"skipped": True}}
            )

        profile_step = self.step_profile()
        self.steps.append(profile_step)
        profile_version_id = profile_step.get("_profile_version_id")

        preview = self.step_reading(
            step_id="S6-preview-bazi",
            name="preview bazi (career)",
            path="/readings/preview",
            payload={
                "profile_version_id": profile_version_id,
                "query": _env_query(
                    "TASK13_QUERY_PREVIEW",
                    default="请从事业维度预览我的整体运势走向",
                ),
                "dimension_ids": ["career"],
            },
        ) if profile_version_id else {
            "id": "S6-preview-bazi", "name": "preview bazi (career)",
            "ok": False, "http_status": None, "detail": {"skipped": True},
        }
        self.steps.append(preview)

        today = self.step_reading(
            step_id="S7-today",
            name="today fortune",
            path="/readings/today",
            payload={
                "profile_version_id": profile_version_id,
                "query": _env_query(
                    "TASK13_QUERY_TODAY",
                    default="请解读今天的运势",
                ),
            },
        ) if profile_version_id else {
            "id": "S7-today", "name": "today fortune", "ok": False,
            "http_status": None, "detail": {"skipped": True},
        }
        self.steps.append(today)

        week = self.step_reading(
            step_id="S8-week",
            name="week fortune",
            path="/readings/week",
            payload={
                "profile_version_id": profile_version_id,
                "query": _env_query(
                    "TASK13_QUERY_WEEK",
                    default="请解读未来七天的运势",
                ),
            },
        ) if profile_version_id else {
            "id": "S8-week", "name": "week fortune", "ok": False,
            "http_status": None, "detail": {"skipped": True},
        }
        self.steps.append(week)

        liuyao = self.step_liuyao(profile_version_id) if profile_version_id else {
            "id": "S9-liuyao-digital-coin", "name": "liuyao digital_coin",
            "ok": False, "http_status": None, "detail": {"skipped": True},
        }
        self.steps.append(liuyao)

        follow_up = {
            "id": "S10-follow-up", "name": "follow-up (new version)",
            "ok": False, "http_status": None,
            "detail": {"skipped": True, "reason": "no accepted base reading"},
        }
        for candidate in (preview, today, week, liuyao):
            if candidate.get("ok") and candidate.get("_version_id"):
                follow_up = self.step_follow_up(candidate["_version_id"])
                break
        self.steps.append(follow_up)

        after = asyncio.run(self.db_status_counts())
        return self._finish(before, started, after=after)

    def _finish(
        self,
        before: dict[str, Any],
        started: float,
        *,
        after: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        required = [step for step in self.steps if step["id"] not in {
            "S9-liuyao-digital-coin", "S10-follow-up"}]
        required_ok = all(step["ok"] for step in required)
        liuyao_step = next(s for s in self.steps if s["id"] == "S9-liuyao-digital-coin")
        follow_up_step = next(s for s in self.steps if s["id"] == "S10-follow-up")

        partial_reasons: list[str] = []
        for step in self.steps:
            if not step["ok"]:
                reason = step["detail"].get("error") or step["detail"].get(
                    "terminal_status"
                ) or step["detail"].get("skipped", "") or "failed"
                partial_reasons.append(f"{step['id']} {step['name']}: {reason}")
        if self.sensitive_found:
            partial_reasons.append(
                f"sensitive markers found: "
                + ", ".join(f"{item['marker']}@{item['step_id']}" for item in self.sensitive_found)
            )
        hard_failure = bool(self.sensitive_found) or not required_ok

        return {
            "schema": "mingli-task13-server-trajectory-v1",
            "generated_at": _utc_now(),
            "server_hostname": socket.gethostname(),
            "api_base": self.api_base,
            "identity": {
                "email_masked": _masked_email(self.email),
                "profile": "fictional (not recorded raw)",
                "birth_datetime_marker_scanned": RAW_BIRTH_DATETIME,
            },
            "adapters": self.adapters(),
            "steps": [
                {key: value for key, value in step.items() if not key.startswith("_")}
                for step in self.steps
            ],
            "sensitive_scan": {
                "markers": [label for label, _ in SENSITIVE_MARKERS] + ["cookie_token_echo"],
                "found": self.sensitive_found,
            },
            "delayed_backlog": {"before": before, "after": after},
            "transcript_count": len(self.transcript),
            "raw_log_dir": str(self.work_dir),
            "duration_s": round(time.monotonic() - started, 1),
            "hard_failure": hard_failure,
            "partial_reasons": partial_reasons,
            "exit_code": 2 if self.sensitive_found else (0 if not partial_reasons else 1),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=API_BASE_DEFAULT)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--summary-json", required=True, type=Path)
    parser.add_argument("--env-file", default=Path("/etc/fateradar/test.env"), type=Path)
    args = parser.parse_args()

    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.work_dir.chmod(0o700)
    email = f"task13.trajectory.{uuid4().hex[:10]}@example.com"
    runner = TrajectoryRunner(
        api_base=args.api_base,
        work_dir=args.work_dir,
        env_file=args.env_file,
    )
    summary = runner.run(email)
    args.summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for step in summary["steps"]:
        marker = "PASS" if step["ok"] else "FAIL"
        print(f"[{marker}] {step['id']} {step['name']} -> {step['detail'].get('terminal_status', 'ok' if step['ok'] else 'failed')}")
    print(f"sensitive found: {len(summary['sensitive_scan']['found'])}")
    print(f"partial reasons: {len(summary['partial_reasons'])}")
    for reason in summary["partial_reasons"]:
        print(f"  - {reason}")
    print(f"exit_code: {summary['exit_code']}")
    return summary["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
