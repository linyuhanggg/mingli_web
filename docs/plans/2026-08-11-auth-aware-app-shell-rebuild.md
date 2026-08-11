# Auth-aware App Shell and Personal Center Rebuild

**Status:** implemented and verified  
**Priority:** P0  
**Decision:** keep the existing backend identity/session system; rebuild the web product shell around its real state.

Release record: [`docs/releases/2026-08-11-auth-aware-app-shell-rebuild.md`](../releases/2026-08-11-auth-aware-app-shell-rebuild.md)

## Why this is a separate plan

`2026-08-11-borrow-ziwei-ui-only.md` only covers birth-input confirmation, chart focus, time layers, and reading layout. It never included login visibility, a personal home, or an account center.

The audited `Renhuai123/ziwei-doushu` repository cannot fill that gap. At commit [`88194a4`](https://github.com/Renhuai123/ziwei-doushu/commit/88194a404242bfe5c6d5cc512e4117e3e245cdd5), its README explicitly says the open-source version excludes backend APIs, login/SMS, membership, and payment. Its root layout has no authenticated app shell, and its published routes have no login, account, user, or profile area.

What remains useful from that repository is narrow: birth-form confirmation, chart-cell focus, related-cell highlighting, time-layer tabs, and the desktop board-plus-detail concept. FateRadar must not import its algorithms, `iztro`, `lunar-javascript`, prompts, localStorage history, brand copy, Tailwind structure, or purple/blue dark visual language.

## Product diagnosis

The backend identity mechanism already works:

- `GET /api/v1/account` is the current-session `/me` contract and returns only a user id plus masked verified identities.
- OTP verification creates or reuses a user, establishes an HttpOnly device session, and claims guest-owned records server-side.
- the current-device logout endpoint revokes the real server session.
- CSRF and session cookies stay in the existing same-origin API flow; no Auth.js, JWT rewrite, or browser token store is needed.
- an invalid device-session cookie is now distinguished from an ordinary guest request: the 401 response clears the stale device and CSRF cookies so the browser can establish a fresh Guest Session and request OTP again.

The broken part was the web shell:

- public navigation always showed a static account link;
- private navigation never read account state;
- `/app` looked the same for guests and signed-in users;
- `/account` always rendered the OTP form, even for a signed-in device;
- on a signed-in device that duplicate OTP form used device CSRF against a guest-only endpoint and could fail with 403;
- no route was clearly named or presented as the user's home or personal center.

## Information architecture

```text
Public site
  └─ Login | Signed in · My home

Private app shell
  ├─ My home        /app
  ├─ Profiles       /app/profiles
  ├─ Ask            /app/ask/liuyao
  ├─ Readings       /app/readings
  └─ Personal center /account
```

Desktop uses the persistent private sidebar. Mobile uses the same five destinations in a bottom navigation bar. Both surfaces show one of four honest session states: checking, guest, signed in with masked identity, or temporarily unknown.

## Session architecture

```text
GET /api/v1/account
        |
        v
Root AccountSessionProvider
  checking | signedOut | signedIn | error
        |
        +-- public account entry
        +-- private identity chip
        +-- conditional personal center
        +-- OTP refresh after verification
        +-- global visual reset after logout
        +-- invalidation after any private API 401
```

The context never stores a token, full email address, internal UUID, or identity snapshot in localStorage. The root provider survives navigation between public, `/account`, and `/app` layouts; nested boundaries reuse it. Refresh is awaitable, deduplicates concurrent probes and concurrent 401 invalidations, ignores older responses after a forced refresh, and revalidates when a background tab becomes visible or focused again.

## Delivery phases

### Phase A — shared session state

- Add one persistent root account session provider around public/private shell consumers.
- Interpret 401 as signed out and other failures as an explicit unknown/error state.
- Await a successful account refresh after OTP verification, then route to `/app`; mark the shell signed out after logout or another private API 401.
- Preserve the backend OTP/session/CSRF design while clearing only invalid device cookies on stale-session 401 responses.

### Phase B — identity-visible navigation

- Public header: show `登录` when signed out and `已登录 · 我的首页` when signed in.
- Private header: show `游客模式 / 登录或注册` or `已登录 / masked identity` on every route.
- Rename navigation to `我的首页`, `命理档案`, `一事一问`, `解读历史`, and `个人中心`.
- Preserve matching desktop and mobile destinations.

### Phase C — conditional personal center

- Signed out: show the email OTP flow, its real delivery boundary, and account/session explanation.
- Signed in: hide every OTP field and show masked identity, personal destinations, current-device logout, and only truthful capability notes.
- Do not invent a nickname, avatar, device list, order, entitlement, or payment state that the backend does not return.

### Phase D — real personal home

- Define `/app` as `我的命理首页`.
- Load real profile and reading summaries from the service.
- Prioritize waiting input, processing, stopped/delayed, and verification work before generic actions.
- Provide real profile, reading, today, seven-day, bazi, and one-question destinations.
- Keep guest trial behavior visible instead of pretending every private route is already account-protected.

### Phase E — backend account capabilities (deferred)

This is not UI-only work. It needs explicit API/schema design before exposing controls:

- display name or avatar profile;
- other-device session list and selective revoke;
- identity binding or account merge;
- data export and deletion;
- real orders, payments, or entitlements;
- safe `returnTo` after an expired session.

## Acceptance contract

- [x] Public navigation distinguishes signed out and signed in.
- [x] Every private route persistently shows guest or signed-in identity state.
- [x] `/app` is visibly the personal home and uses server-returned records.
- [x] `/account` is visibly the personal center.
- [x] A signed-in account page contains no email-login input.
- [x] A signed-out account page contains the real OTP entry.
- [x] Login establishes the server session, awaits one shared account refresh, and then routes to `/app` without an unmount race or duplicate probe.
- [x] Logout updates shared state and revokes the current device session.
- [x] An expired or server-revoked device session clears stale cookies, creates a fresh Guest Session, and can request OTP again without a 403 loop.
- [x] Any private API 401 invalidates the visible shared identity state.
- [x] Returning to a persistent browser tab revalidates identity so a logout from another tab does not leave stale signed-in chrome.
- [x] No internal user/identity UUID is rendered.
- [x] No account secret or formal record is persisted in localStorage.
- [x] Desktop and mobile navigation expose the same five destinations.
- [x] Full test, lint, typecheck, and production build pass.
- [x] 360 / 768 / 1024 / 1440 visual checks pass for guest and signed-in states.
- [x] Keyboard, focus, and reduced-motion checks pass.

## Verification record

- `npm test`: 31 files and 250 tests passed.
- `npm run lint`: zero warnings or errors.
- `npm run typecheck`: passed with no emitted files.
- `npm run build`: Next.js production build passed for all public and private routes.
- `pytest backend/tests tests/contract`: 520 passed and 90 environment-dependent tests skipped.
- Focused auth/session backend suite: 29 passed; Ruff passed on every changed backend file.
- Real Chrome checks covered 360, 768, 1024, and 1440 pixel widths plus 667 × 375 landscape.
- Guest and signed-in account states, OTP login, post-login routing, logout, public identity visibility, desktop sidebar, mobile bottom navigation, skip-link focus, and client-route main focus were exercised.
- A real stale-session run revoked the active device row while preserving browser cookies, then verified the exact recovery sequence: account 401 → stale-cookie deletion → Guest Session 201 → OTP request 202 → verify 200 → one account probe 200 → focused `/app` main.
- No checked viewport had horizontal overflow; visible interactive controls were at least 44 pixels high in the narrow and landscape checks.

## Main implementation files

- `web/src/components/account-session-context.tsx`
- `web/src/components/account-center.tsx`
- `web/src/components/account-session-control.tsx`
- `web/src/components/otp-form.tsx`
- `web/src/components/private-shell.tsx`
- `web/src/components/site-header.tsx`
- `web/src/components/route-scroll-policy.tsx`
- `web/src/lib/api.ts`
- `web/src/app/app/page.tsx`
- `web/src/app/account/page.tsx`
- `web/src/test/account-experience.test.tsx`
- `backend/app/api/dependencies.py`
- `backend/app/api/errors.py`
- `backend/app/main.py`
- `backend/tests/test_auth.py`

## Non-negotiable boundaries

1. A user account and a subject birth profile remain different domain objects.
2. Guest trial remains supported until product policy and API guards are intentionally changed together.
3. The frontend never calculates or fabricates chart facts.
4. The frontend never fabricates profile, payment, order, device, or entitlement data.
5. FateRadar's accepted Eastern Editorial Archive system remains the visual authority.
