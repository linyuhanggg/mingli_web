# Phase 0/1 Web Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the versioned, testable Phase 0/1 foundation for the FateRadar responsive website without deleting or reusing the legacy mini-program architecture.

**Architecture:** A Next.js App Router application serves public and private shells and proxies same-origin `/api` requests to a FastAPI modular monolith. PostgreSQL is the durable fact source; identity, guest, and device sessions are modeled separately, while OTP delivery and all not-yet-enabled external capabilities are hidden behind explicit Fake adapters. API and Worker share backend modules but run as separate processes.

**Tech Stack:** Next.js, React, TypeScript, CSS Modules, Vitest, Testing Library, Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, pytest, Ruff, mypy, Docker Compose, Nginx.

---

### Task 1: Preserve the legacy baseline and record Phase 0 gates

**Files:**
- Create: `.gitignore`
- Create: `docs/PHASE_0_GATES.md`
- Preserve unchanged: `app.js`, `app.json`, `app.wxss`, `pages/`, `utils/`, `i18n/`, `project*.json`, `sitemap.json`

**Step 1: Establish the baseline**

Run: `git init -b main && git add <legacy-and-contract-files>`

Expected: the old mini-program files and authority documents are staged without `project.private.config.json`.

**Step 2: Commit the historical skeleton**

Run: `git commit -m "chore: preserve legacy miniapp baseline"`

Expected: a root commit exists before any website implementation.

**Step 3: Record external gates without inventing completion**

Create a checklist that marks operating entity, domain/ICP, payment merchant approval, model data location, and production credentials as `pending external confirmation`. Do not add secrets or claim a production gate passed.

### Task 2: Freeze the first contracts and scaffold both runtimes

**Files:**
- Create: `contracts/openapi/v1.yaml`
- Create: `contracts/schemas/auth-session.schema.json`
- Create: `contracts/schemas/health.schema.json`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Test: `tests/contract/test_openapi_contract.py`

**Step 1: Write the failing contract test**

```python
def test_phase_one_paths_are_frozen(openapi_document: dict[str, object]) -> None:
    paths = openapi_document["paths"]
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths
    assert "/api/v1/guest-sessions" in paths
    assert "/api/v1/auth/otp/request" in paths
    assert "/api/v1/auth/otp/verify" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/account" in paths
```

**Step 2: Verify RED**

Run: `uv run --project backend pytest tests/contract/test_openapi_contract.py -q`

Expected: FAIL because the frozen OpenAPI document does not exist.

**Step 3: Add the minimal OpenAPI and JSON Schemas**

Define only Phase 1 resources, common problem details, cookie authentication, and request/response identifiers. Keep future Profile, Reading, Billing, and Model operations out of the active paths.

**Step 4: Verify GREEN**

Run: `uv run --project backend pytest tests/contract/test_openapi_contract.py -q`

Expected: PASS.

### Task 3: Implement liveness, readiness, configuration guards, and observability

**Files:**
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/database.py`
- Create: `backend/app/observability.py`
- Test: `backend/tests/test_health.py`
- Test: `backend/tests/test_config.py`

**Step 1: Write failing behavior tests**

```python
def test_liveness_is_process_only(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}

def test_every_response_has_request_id(client):
    response = client.get("/api/v1/health/live")
    assert response.headers["x-request-id"]
```

Readiness must execute `SELECT 1` through the configured database and return 503 with a non-sensitive problem body when the dependency is unavailable.

**Step 2: Verify RED**

Run: `uv run --project backend pytest backend/tests/test_health.py backend/tests/test_config.py -q`

Expected: FAIL because the application factory and health routes are missing.

**Step 3: Implement the minimum application factory and middleware**

Use typed settings, JSON request logs without cookies or sensitive bodies, a request ID, and separate liveness/readiness probes.

**Step 4: Verify GREEN**

Run the same focused tests and expect PASS.

### Task 4: Add the PostgreSQL identity migration and Guest Session

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_identity_foundation.py`
- Create: `backend/app/identity/models.py`
- Create: `backend/app/identity/repository.py`
- Create: `backend/app/identity/service.py`
- Create: `backend/app/api/guest_sessions.py`
- Test: `backend/tests/test_guest_sessions.py`
- Test: `backend/tests/test_migrations.py`

**Step 1: Write a failing Guest Session test**

```python
def test_guest_session_uses_an_opaque_httponly_cookie(client):
    response = client.post("/api/v1/guest-sessions")
    assert response.status_code == 201
    cookie = response.headers["set-cookie"]
    assert "mingli_guest=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=86400" in cookie
    assert response.json()["expires_at"]
```

Add tests that the database stores only a SHA-256 token hash, creates a readable CSRF cookie, and uses a 24-hour expiry.

**Step 2: Verify RED**

Run: `uv run --project backend pytest backend/tests/test_guest_sessions.py backend/tests/test_migrations.py -q`

Expected: FAIL because models, migration, and route are missing.

**Step 3: Implement immutable identifiers and token hashing**

Create `users`, `login_identities`, `device_sessions`, `guest_sessions`, and `audit_events`; use UUID business keys and never use phone/email as foreign keys. Store only hashes for session secrets.

**Step 4: Verify GREEN**

Run the focused tests and expect PASS.

### Task 5: Implement phone/email OTP Fake adapters and Cookie Device Sessions

**Files:**
- Create: `backend/app/adapters/otp.py`
- Create: `backend/app/identity/schemas.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/account.py`
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/test_csrf.py`

**Step 1: Write failing tests for the external behavior**

```python
def test_verified_phone_otp_creates_a_user_and_device_session(client, csrf_headers):
    requested = client.post(
        "/api/v1/auth/otp/request",
        headers=csrf_headers,
        json={"channel": "phone", "destination": "13800138000"},
    )
    verified = client.post(
        "/api/v1/auth/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200
    assert "mingli_session=" in verified.headers["set-cookie"]
    assert verified.json()["user_id"]
```

Also test email normalization, generic OTP request responses, invalid/expired codes, attempt limits, CSRF mismatch, repeat login resolving the same User, authenticated account lookup, logout revocation, and absence of raw destinations/session tokens from persistent rows.

**Step 2: Verify RED**

Run: `uv run --project backend pytest backend/tests/test_auth.py backend/tests/test_csrf.py -q`

Expected: FAIL because the adapter and auth routes are missing.

**Step 3: Implement the ports and Fake adapter**

The Fake adapter returns the fixed development code only outside production. Production settings must reject accidental Fake delivery activation. Device Session cookies are `HttpOnly`, `SameSite=Lax`, `Secure` outside local/test, and backed by a revocable token hash.

**Step 4: Verify GREEN**

Run the focused tests and expect PASS.

### Task 6: Add Fake external capability ports and a separate Worker skeleton

**Files:**
- Create: `backend/app/adapters/payment.py`
- Create: `backend/app/adapters/model.py`
- Create: `backend/app/adapters/runtime.py`
- Create: `backend/worker/__init__.py`
- Create: `backend/worker/main.py`
- Test: `backend/tests/test_fake_adapters.py`
- Test: `backend/tests/test_worker.py`

**Step 1: Write failing adapter contract tests**

Assert that Fake Payment never reports a real settlement, Fake Model returns schema-shaped placeholder output, Fake Runtime exposes only allowlisted capabilities, and one Worker iteration exits cleanly when no task exists.

**Step 2: Verify RED**

Run: `uv run --project backend pytest backend/tests/test_fake_adapters.py backend/tests/test_worker.py -q`

Expected: FAIL because the ports do not exist.

**Step 3: Implement minimal typed protocols and deterministic Fakes**

Do not add provider SDKs, credential fields, real callbacks, or production transaction behavior.

**Step 4: Verify GREEN**

Run the focused tests and expect PASS.

### Task 7: Build the owned design system and responsive home page

**Files:**
- Create: `web/src/app/globals.css`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`
- Create: `web/src/components/brand-mark.tsx`
- Create: `web/src/components/button-link.tsx`
- Create: `web/src/components/site-header.tsx`
- Create: `web/src/components/site-footer.tsx`
- Create: `web/src/components/task-card.tsx`
- Create: `web/src/test/home.test.tsx`

**Step 1: Write the failing home behavior test**

```tsx
it("offers the three frozen first tasks", () => {
  render(<HomePage />);
  expect(screen.getByRole("link", { name: "免费建立命理档案" })).toBeVisible();
  expect(screen.getByText("今日与近七日")).toBeVisible();
  expect(screen.getByRole("link", { name: "问一件具体的事" })).toBeVisible();
});
```

Add tests for public navigation landmarks, meaningful heading order, pricing disclosure, and the AI/traditional-culture boundary.

**Step 2: Verify RED**

Run: `npm --prefix web test -- home.test.tsx`

Expected: FAIL because the page and components are missing.

**Step 3: Implement the visual system and page**

Use original deep-ink-green, ivory, and muted-gold tokens; system fonts; 44px targets; a single-column 360px layout; multi-column desktop layouts; visible focus; and reduced-motion overrides. Do not import or copy Metis assets or legacy mini-program styles.

**Step 4: Verify GREEN**

Run the focused Vitest file and expect PASS.

### Task 8: Add public pages, private shell, and account OTP UI

**Files:**
- Create: `web/src/app/pricing/page.tsx`
- Create: `web/src/app/methodology/page.tsx`
- Create: `web/src/app/support/page.tsx`
- Create: `web/src/app/privacy/page.tsx`
- Create: `web/src/app/terms/page.tsx`
- Create: `web/src/app/app/layout.tsx`
- Create: `web/src/app/app/page.tsx`
- Create: `web/src/app/account/layout.tsx`
- Create: `web/src/app/account/page.tsx`
- Create: `web/src/components/otp-form.tsx`
- Test: `web/src/test/public-pages.test.tsx`
- Test: `web/src/test/otp-form.test.tsx`

**Step 1: Write failing content and interaction tests**

Test the ¥0/¥29.90/¥9.90 catalog wording, support/data-rights entry points, privacy/terms boundaries, `robots` metadata on private layouts, phone/email mode selection, and same-origin API requests from the OTP form.

**Step 2: Verify RED**

Run: `npm --prefix web test -- public-pages.test.tsx otp-form.test.tsx`

Expected: FAIL because pages and form are missing.

**Step 3: Implement only the Phase 1 surface**

The `/app` page is an honest shell that labels Profile/Reading work as the next phase; it must not fake a calculated result. The account page can create a Guest Session, request Fake OTP, verify it, read `/api/v1/account`, and log out.

**Step 4: Verify GREEN**

Run the focused tests and expect PASS.

### Task 9: Enforce same-origin routing, private caching rules, and local infrastructure

**Files:**
- Modify: `web/next.config.ts`
- Create: `web/src/app/robots.ts`
- Create: `web/src/app/manifest.ts`
- Create: `web/src/test/security-config.test.ts`
- Create: `infra/compose.local.yml`
- Create: `infra/docker/backend.Dockerfile`
- Create: `infra/docker/web.Dockerfile`
- Create: `infra/nginx/app.conf`
- Create: `infra/.env.example`
- Create: `infra/PHASE_1_RUNBOOK.md`

**Step 1: Write a failing configuration test**

Assert that `/api/:path*` rewrites to the internal FastAPI origin, `/app/:path*` and `/account/:path*` receive `private, no-store` plus `X-Robots-Tag: noindex`, public responses receive the frozen security headers, and robots disallows private paths.

**Step 2: Verify RED**

Run: `npm --prefix web test -- security-config.test.ts`

Expected: FAIL until configuration is complete.

**Step 3: Add local PostgreSQL/Redis, independent API/Worker processes, and Nginx same-origin routing**

All example environment values are non-secret. Production-only values are documented as external secret injection and never filled in.

**Step 4: Verify GREEN**

Run the focused test and `docker compose -f infra/compose.local.yml config`; both must pass.

### Task 10: Full verification, review, and implementation commit

**Files:**
- Modify: `README.md`
- Create: `Makefile`
- Review: all newly tracked Phase 0/1 files

**Step 1: Run backend quality gates**

Run:

```bash
uv run --project backend ruff check backend tests
uv run --project backend mypy backend/app backend/worker
uv run --project backend pytest backend/tests tests/contract -q
```

Expected: all pass with no warnings or secret-bearing output.

**Step 2: Run frontend quality gates**

Run:

```bash
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web test -- --run
npm --prefix web run build
```

Expected: all pass; public routes render and private routes are dynamic/no-store.

**Step 3: Run migration and infrastructure checks**

Run:

```bash
uv run --project backend alembic upgrade head
docker compose -f infra/compose.local.yml config
```

Expected: the identity migration reaches head and Compose resolves without real credentials.

**Step 4: Review against the authority contracts**

Check directory boundaries, legacy preservation, User/Login Identity separation, opaque Cookie sessions, Fake-only external adapters, same-origin API, public/private cache rules, and Phase 2 deferrals. Fix every actionable finding and rerun the affected gate.

**Step 5: Commit the implementation**

Run: `git add <Phase-0-and-1-files> && git commit -m "feat: build phase 0 and 1 web foundation"`

Expected: a focused implementation commit, with any unrelated concurrent workspace files left untouched.
