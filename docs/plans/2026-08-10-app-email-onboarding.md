# FateRadar App & Email Onboarding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the accepted FateRadar homepage design into every private `/app` surface and deliver a testable email-first registration-to-reading journey, while keeping real email credentials and production traffic disabled.

**Architecture:** Preserve the existing internal `User` + `LoginIdentity` model: there is no separate sign-up endpoint; the first verified email creates the user and later verifications log the same user in. Add a staging-capable SMTP `OtpDeliveryAdapter` and per-challenge random codes without widening the public auth contract. Keep the current in-memory OTP stores for local/Fake and single-instance staging only; fail closed in production until a durable Redis/DB store is implemented. Add a narrow reading-history interface so the user journey can end in a real, owner-filtered history page. Frontend work reuses the accepted Eastern Editorial Archive tokens and treats the private product as an Operate surface.

**Tech Stack:** FastAPI, SQLAlchemy asyncio, Pydantic Settings, stdlib SMTP/TLS, Next.js 16, React 19, TypeScript, CSS Modules, React Hook Form, Zod, Vitest, pytest.

---

## Scope and non-goals

- Email verification is the primary P0 browser identity flow. Phone OTP remains supported by the existing backend Fake adapter but is not presented as a ready production channel.
- Real SMTP code is implemented and unit-tested, but no credential is stored in Git or chat and the public test server stays `local + Fake` until a sender domain, SPF/DKIM and SMTP secret are configured.
- Production remains blocked because OTP challenge/rate-limit state is in memory. `environment=production` must reject `fake`, `disabled`, and `smtp` until a durable store exists.
- This iteration adds owner-filtered profile and reading history needed by the journey. It does not add payment, a real Runtime, a real model, or public claims that those capabilities are live.
- UI refines the accepted visual world; it does not redesign the homepage or introduce a second design system.

### Task 1: Freeze email-first auth behavior with failing tests

**Files:**
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_config.py`
- Create: `backend/tests/test_smtp_otp_adapter.py`
- Modify: `web/src/test/otp-form.test.tsx`
- Create: `web/src/test/api-session.test.ts`

**Step 1: Write failing backend tests**

- Assert two non-Fake OTP requests receive different six-digit codes through a recording delivery adapter.
- Assert Fake still receives and exposes `246810` in local/test.
- Assert SMTP refuses the phone channel without exposing destination or code.
- Assert SMTP uses the configured sender, recipient and TLS mode through an injected in-memory SMTP client factory.
- Assert SMTP errors become `OtpDeliveryUnavailable` without leaking credentials.
- Assert `otp_adapter=smtp` requires host, username, password and sender.
- Assert every production OTP adapter currently fails closed with the durable-store message.

**Step 2: Write failing frontend tests**

- Render email as the default and primary identity input.
- Explain “首次验证自动创建账户；已有邮箱直接登录”.
- On successful verify, adopt the returned device CSRF token and route to `/app`.
- Read an existing `mingli_csrf` cookie before creating a new Guest Session.
- Expose a clear resend/change-email recovery path in code-entry state.

**Step 3: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_auth.py backend/tests/test_config.py backend/tests/test_smtp_otp_adapter.py -q
npm --prefix web test -- otp-form.test.tsx api-session.test.ts
```

Expected: failures for the missing SMTP adapter, random-code factory, email-first copy/redirect and cookie-CSRF adoption.

### Task 2: Implement SMTP delivery and random per-challenge codes

**Files:**
- Modify: `backend/app/adapters/otp.py`
- Modify: `backend/app/identity/service.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/.env.example`
- Create: `infra/EMAIL_OTP_RUNBOOK.md`

**Step 1: Implement the minimal SMTP adapter**

- Add `smtp` to `OtpAdapterName`.
- Add `SmtpOtpDeliveryAdapter` using `EmailMessage`, `smtplib.SMTP`/`SMTP_SSL`, `ssl.create_default_context()` and `asyncio.to_thread`.
- Support explicit `smtp_security=starttls|ssl`; never silently downgrade to plaintext.
- Inject an internal SMTP client factory for tests; keep `OtpDeliveryAdapter` as the only external seam.
- Reject non-email channels with the generic unavailable error.

**Step 2: Generate codes at the service seam**

- Replace `AuthService.otp_code` with `otp_code_factory: Callable[[], str]`.
- Fake factory returns the configured test code.
- SMTP factory uses `secrets.randbelow(1_000_000)` and zero-pads to six digits.
- Generate once, then pass the same value to challenge hashing and delivery.
- Keep `development_code` response restricted to local/test + Fake.

**Step 3: Add fail-closed settings**

- Require complete SMTP configuration only when `otp_adapter=smtp`.
- Keep secrets as `SecretStr` and out of repr/logging.
- Reject every OTP adapter in production with a durable-store-required error for now.
- Document sender-domain/SPF/DKIM/TLS setup without provider credentials.

**Step 4: Verify GREEN**

Run the Task 1 backend tests. Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app backend/tests backend/.env.example infra/EMAIL_OTP_RUNBOOK.md
git commit -m "feat: add email OTP delivery adapter"
```

### Task 3: Complete the email-first browser session handoff

**Files:**
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/components/otp-form.tsx`
- Modify: `web/src/components/otp-form.module.css`
- Modify: `web/src/app/account/page.tsx`
- Modify: `web/src/test/otp-form.test.tsx`
- Create: `web/src/test/api-session.test.ts`

**Step 1: Implement CSRF adoption**

- Export a narrow `adoptCsrfToken(token)` helper.
- `getCsrfToken()` first reads the readable `mingli_csrf` cookie, then falls back to creating a Guest Session.
- Successful OTP verification adopts the returned device CSRF token before routing.
- Logout/reset clears the in-memory token and lets the cookie determine the next owner session.

**Step 2: Refine onboarding behavior**

- Default to email and present phone as “稍后开放” rather than a production-ready peer.
- Treat first verification as registration and repeated verification as login in copy only; do not split the backend interface.
- Preserve invalid destination, rate-limit, expired-code, resend and change-email recovery states.
- Route successful verification to `/app` with an honest transitional success message.

**Step 3: Verify GREEN**

```bash
npm --prefix web test -- otp-form.test.tsx api-session.test.ts
npm --prefix web run typecheck
```

Expected: PASS.

**Step 4: Commit**

```bash
git add web/src/lib/api.ts web/src/components/otp-form.tsx web/src/components/otp-form.module.css web/src/app/account/page.tsx web/src/test
git commit -m "feat: complete email onboarding handoff"
```

### Task 4: Add an owner-filtered reading history interface

**Files:**
- Modify: `backend/app/readings/api_schemas.py`
- Modify: `backend/app/readings/repository.py`
- Modify: `backend/app/readings/service.py`
- Modify: `backend/app/api/readings.py`
- Modify: `backend/tests/test_readings_api.py`
- Modify: `contracts/openapi/v1.yaml`
- Modify: `tests/contract/test_openapi_contract.py`
- Modify: `web/src/lib/api.ts`
- Create: `web/src/components/reading-history.tsx`
- Create: `web/src/components/reading-history.module.css`
- Modify: `web/src/app/app/readings/page.tsx`
- Modify: `web/src/test/private-surfaces.test.tsx`

**Step 1: Write failing API and contract tests**

- `GET /api/v1/readings` returns only versions belonging to the current User/Guest.
- Sort by `created_at DESC, id DESC`, cap at 50, and expose only `ReadingVersionSummary` fields.
- Cross-owner records never appear; encrypted prepare/result/token fields never appear.
- Freeze `ReadingListResponse` and the new path in OpenAPI.

**Step 2: Verify RED**

```bash
uv run --project backend pytest backend/tests/test_readings_api.py tests/contract/test_openapi_contract.py -q
```

Expected: 404/missing operation and schema assertions.

**Step 3: Implement the narrow list interface**

- Add repository `list_owned_versions(owner_user_id, owner_guest_session_id, limit=50)`.
- Add service `list_summaries(owner)` reusing the existing public summary projection.
- Define route before `/{reading_version_id}` to avoid path ambiguity.
- Mark response no-store/noindex.

**Step 4: Write failing frontend history tests**

- Loading, empty, error and populated states.
- Links resolve to `/app/readings/{reading_version_id}`.
- Capability/status/date labels are human-readable and do not invent result content.

**Step 5: Implement and verify**

```bash
npm --prefix web test -- private-surfaces.test.tsx
```

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/app backend/tests contracts tests/contract web/src
git commit -m "feat: add private reading history"
```

### Task 5: Turn the profile placeholder into a real archive list

**Files:**
- Create: `web/src/components/profile-archive.tsx`
- Create: `web/src/components/profile-archive.module.css`
- Modify: `web/src/app/app/profiles/page.tsx`
- Modify: `web/src/test/private-surfaces.test.tsx`

**Step 1: Write failing tests**

- Render loading, empty, authenticated-list and error states from `listProfiles()`.
- Every version displays version number and created time without decrypting birth data.
- Primary action starts a new version; each list item links to the appropriate next task rather than exposing encrypted data.

**Step 2: Verify RED, implement, verify GREEN**

```bash
npm --prefix web test -- private-surfaces.test.tsx
```

**Step 3: Commit**

```bash
git add web/src/components/profile-archive* web/src/app/app/profiles/page.tsx web/src/test/private-surfaces.test.tsx
git commit -m "feat: show immutable profile archive"
```

### Task 6: Align the private app shell and forms with the homepage

**Files:**
- Create: `web/src/components/app-page-header.tsx`
- Create: `web/src/components/form-controls.module.css`
- Modify: `web/src/components/private-shell.tsx`
- Modify: `web/src/components/private-shell.module.css`
- Modify: `web/src/components/app-surface.module.css`
- Modify: `web/src/app/app/page.tsx`
- Modify: `web/src/app/app/profile/new/page.tsx`
- Modify: `web/src/app/app/fortune/today/page.tsx`
- Modify: `web/src/app/app/fortune/week/page.tsx`
- Modify: `web/src/app/app/ask/liuyao/page.tsx`
- Modify: `web/src/app/account/page.tsx`
- Modify: `web/src/components/profile-form.tsx`
- Modify: `web/src/components/profile-form.module.css`
- Modify: `web/src/components/fortune-flow.tsx`
- Modify: `web/src/components/fortune-flow.module.css`
- Modify: `web/src/components/liuyao-form.tsx`
- Modify: `web/src/components/liuyao-form.module.css`
- Modify: `web/src/components/otp-form.tsx`
- Modify: `web/src/components/otp-form.module.css`
- Modify: `web/src/test/private-surfaces.test.tsx`
- Create: `web/src/test/form-contract.test.ts`

**Step 1: Load the Impeccable craft floor immediately before editing**

Use the accepted `DESIGN.md`, homepage surface brief and Operate-mode constraints. Do not create a new visual direction.

**Step 2: Write failing design-contract tests**

- All private routes have one h1 through `AppPageHeader` and consistent folio/intro metadata.
- Primary/secondary actions use `--radius-sm`; `999px` remains reserved for short state tags.
- Inputs use `--ivory-50`, visible labels, nearby errors and at least 48px height.
- Disabled controls include a textual reason.
- Mobile nav remains five items with safe-area padding.

**Step 3: Implement shared private materials**

- Extend the paper/ink/gold hierarchy into the shell: compact deep-ink archive rail on desktop, restrained ivory workspace, clear current-page folio and unchanged mobile task order.
- Use `AppPageHeader` for all private routes, with title-scale typography rather than homepage display scale.
- Consolidate repeated field/action styles into `form-controls.module.css`.
- Remove pill-shaped form buttons and inconsistent white inputs.
- Preserve all existing product truth and capability gates.

**Step 4: Verify focused tests**

```bash
npm --prefix web test -- private-surfaces.test.tsx form-contract.test.ts otp-form.test.tsx profile-form.test.tsx reading-flows.test.tsx liuyao-form.test.tsx
```

Expected: PASS.

**Step 5: Commit**

```bash
git add web/src/app web/src/components web/src/test
git commit -m "feat: align private app with FateRadar design"
```

### Task 7: Recompose the reading page as one editorial sheet

**Files:**
- Modify: `web/src/app/app/readings/[readingId]/page.tsx`
- Modify: `web/src/components/readings/reading-result.tsx`
- Modify: `web/src/components/readings/reading-result.module.css`
- Modify: `web/src/components/readings/need-input-form.tsx`
- Modify: `web/src/components/readings/need-input-form.module.css`
- Modify: `web/src/components/readings/verification-form.tsx`
- Modify: `web/src/components/readings/verification-form.module.css`
- Modify: `web/src/components/readings/follow-up-form.tsx`
- Modify: `web/src/components/readings/follow-up-form.module.css`
- Modify: `web/src/test/reading-result.test.tsx`

**Step 1: Write failing reading-anatomy tests**

- Accepted output follows the visible order `01 事实`, `02 判断`, `03 依据与边界`, `04 复核与追问`, so the claim is read after its deterministic facts and before verification or follow-up actions.
- At 68rem the evidence rail uses the existing sticky layout; mobile remains one continuous sheet.
- Empty evidence is explicit and never fabricates a source.
- Waiting, delayed, runtime-unknown, terminal and recovery forms preserve semantics.

**Step 2: Verify RED, implement the one-sheet composition, verify GREEN**

```bash
npm --prefix web test -- reading-result.test.tsx
```

**Step 3: Commit**

```bash
git add web/src/app/app/readings web/src/components/readings web/src/test/reading-result.test.tsx
git commit -m "feat: compose editorial reading result"
```

### Task 8: Add a complete API journey regression

**Files:**
- Create: `backend/tests/test_email_user_journey.py`
- Modify: `infra/TEST_SERVER_RUNBOOK.md`

**Step 1: Write the failing journey**

Exercise one process using local + Fake only:

1. create Guest Session;
2. request email OTP and verify it;
3. assert account has one email identity;
4. create/confirm a fictional profile and assert guest ownership was claimed;
5. start today reading and drive Worker until Accepted;
6. submit Verification;
7. create Follow-up and drive it to Accepted;
8. list readings and reopen both versions;
9. list profiles and assert the same User owns the archive;
10. repeat login with the normalized email and assert the same User.

**Step 2: Verify RED, then implement only missing behavior from earlier tasks**

```bash
uv run --project backend pytest backend/tests/test_email_user_journey.py -q
```

**Step 3: Document the server Fake journey**

- Record exact endpoints and assertions.
- State that the test server is public HTTP, local + Fake and fictional-data only.
- State that real SMTP remains disabled until external sender-domain and secret setup.

**Step 4: Commit**

```bash
git add backend/tests/test_email_user_journey.py infra/TEST_SERVER_RUNBOOK.md
git commit -m "test: cover email registration user journey"
```

### Task 9: Run complete local verification and bounded visual QA

**Files:**
- Modify only files with verified defects found in this pass.

**Step 1: Run focused tests, then full gates**

```bash
make check
make test
```

Expected: backend/contract, Ruff, mypy, Web tests, ESLint, TypeScript and Next production build all PASS.

**Step 2: Run required Impeccable checks once**

```bash
node /Users/yuhanglin/.codex/skills/impeccable/scripts/detect.mjs --json \
  web/src/app/app web/src/app/account web/src/components/private-shell.tsx \
  web/src/components/app-page-header.tsx web/src/components/form-controls.module.css \
  web/src/components/readings
```

- Perform one desktop + mobile screenshot pass at 1440×900 and 360×800.
- Batch-fix all real findings once; perform at most one confirmation pass.
- Verify keyboard focus, reduced motion, 44px targets, no horizontal overflow and no console errors.

**Step 3: Review source diff**

- Remove dead styles, temporary artifacts and duplicated button/field implementations.
- Confirm the worktree contains only intended files.

### Task 10: Deploy the immutable candidate and dogfood the public test flow

**Files:**
- Modify: `docs/releases/<date>-app-email-onboarding.md`

**Step 1: Deploy safely**

- Archive the tested commit; verify SHA-256 locally and remotely.
- Take a non-empty `pg_dump` before any migration (none is expected in this plan, but the deployment gate remains).
- Build backend and Web in a new immutable release directory.
- Atomically switch `/opt/fateradar/current`, restart API/Worker/Web and verify Nginx.
- Keep `MINGLI_ENVIRONMENT=local`, `MINGLI_OTP_ADAPTER=fake`, Fake Runtime and Fake Model.

**Step 2: Dogfood the full browser journey**

At `http://106.14.10.235:18080`, using only fictional data:

- email first verification → automatic account creation → `/app`;
- profile creation and confirmation;
- today reading → Accepted;
- Verification → history → reopen result;
- repeat email login resolves the same User;
- inspect desktop and mobile, console after each significant transition.

**Step 3: Record exact evidence and rollback**

- Save tested commit, archive hash, service state, endpoint status and discovered issues.
- Roll back on any migration, health, auth, ownership, result or visual regression.

### Task 11: Integrate and clean up

**Step 1: Review all subagent patches and rerun critical tests**

Do not accept summaries without inspecting diffs and rerunning the exact focused tests.

**Step 2: Fast-forward or merge into `main` only after all gates and server dogfood pass**

```bash
git switch main
git merge --ff-only codex/app-email-onboarding
git branch -d codex/app-email-onboarding
```

**Step 3: Update release evidence and Nowledge Mem**

Record what is genuinely complete, the deployed commit, and the remaining real-email blockers: sender domain, SPF/DKIM, SMTP credentials and durable OTP state.
