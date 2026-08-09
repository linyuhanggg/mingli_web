# Test Deployment and Branch Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the current Phase 2 working tree into an auditable candidate, consolidate safe branch work into `main`, and decide from evidence whether that exact `main` commit may be deployed to a test server.

**Architecture:** Treat `main` as the integration fixed point and preserve every existing user change. Review code, product-contract alignment, branch ancestry, and deployment security independently; commit functionality, documentation, and infrastructure in separate reversible units; then fast-forward `main` only after the merged commit passes the repository gates. A test deployment is permitted only through a documented staging path with fake or explicitly approved adapters, isolated credentials, backup/rollback, and no real traffic.

**Tech Stack:** Git/worktrees, Python 3.12 + FastAPI + pytest/Ruff/mypy, Next.js 16 + TypeScript + Vitest/ESLint, PostgreSQL/Alembic, Nginx/Docker Compose, macOS native mingli Runtime gate.

---

### Task 1: Freeze the repository evidence

**Files:**
- Inspect: `.git/`
- Inspect: `README.md`
- Inspect: `docs/releases/2026-08-10-mingli-v51-web-phase2.md`
- Inspect: `docs/plans/2026-08-09-mingli-v51-web-integration.md`

**Step 1: Capture the dirty-tree inventory**

Run: `git status --short --branch`

Expected: branch `feat/mingli-v51-web-integration` with the Task 11/12 candidate plus separately reviewable design and infrastructure files.

**Step 2: Capture branch and worktree ancestry**

Run: `git branch -vv --all`

Run: `git worktree list --porcelain`

Run: `git log --oneline --decorate --graph --all --max-count=120`

Expected: every local branch is classified as merged, ancestor-equivalent, unique-but-obsolete, or still active.

**Step 3: Confirm the integration fixed point**

Run: `git rev-parse --verify main`

Run: `git diff --stat main...HEAD`

Expected: `main` resolves and the feature diff is non-empty.

### Task 2: Review the candidate on independent axes

**Files:**
- Review: `backend/`
- Review: `contracts/`
- Review: `web/`
- Review: `infra/`
- Review: `DESIGN.md`
- Review: `web/AGENTS.md`

**Step 1: Run the standards review**

Compare committed and working-tree changes against repository instructions, security boundaries, and documented quality gates. Report concrete file/line findings only.

**Step 2: Run the specification review**

Compare Task 11/12 implementation against `docs/plans/2026-08-09-mingli-v51-web-integration.md`, `docs/MINGLI_V51_WEB_INTEGRATION.md`, and the Phase 2 release note. Report missing, partial, or out-of-scope behavior.

**Step 3: Audit deployment inputs**

Inspect Nginx, SSH, certificate, Compose, environment, migration, backup, restart, health-check, and rollback instructions. Never print or test leaked credentials.

**Step 4: Resolve blocking findings**

Make only scoped fixes supported by tests. Keep unrelated user files untouched.

### Task 3: Verify the exact candidate

**Files:**
- Test: `backend/tests/`
- Test: `tests/contract/`
- Test: `web/src/test/`

**Step 1: Run the full repository gate**

Run: `make check`

Expected: backend/contract tests, Ruff, mypy, web tests, ESLint, TypeScript, and the Next production build all pass.

**Step 2: Run the independent test gate**

Run: `make test`

Expected: all backend, contract, and web tests pass independently of the build chain.

**Step 3: Validate migrations without production data**

Run the repository's documented empty-database Alembic upgrade/downgrade or migration-alignment checks against an isolated database only.

Expected: schema reaches Alembic head and the Phase 2 migration contract is consistent.

### Task 4: Form auditable commits

**Files:**
- Commit group A: `backend/`, `contracts/`, `tests/`, `web/src/`
- Commit group B: `README.md`, `docs/`, `DESIGN.md`, `web/AGENTS.md`
- Commit group C: `infra/`

**Step 1: Review each path before staging**

Run: `git diff -- <path>` and `git diff --no-index /dev/null <untracked-file>` as applicable.

Expected: no secrets, private keys, live credentials, generated certificate state, or unrelated assets enter a commit.

**Step 2: Commit Task 11/12 functionality**

Stage only the tested API, migration, contract, and web-flow changes.

Expected commit subject: `feat: expose phase 2 reading workflows`

**Step 3: Commit durable documentation separately**

Stage only reviewed product/release/design instructions.

Expected commit subject: `docs: record phase 2 candidate gates`

**Step 4: Commit infrastructure only if security review passes**

Exclude host keys, private keys, ACME state, secrets, runtime data, and machine-specific material.

Expected commit subject: `ops: add test deployment runbook`

### Task 5: Consolidate branches into `main`

**Files:**
- Update: Git refs only

**Step 1: Recompute branch containment after candidate commits**

Run: `git branch --merged feat/mingli-v51-web-integration`

Run: `git cherry feat/mingli-v51-web-integration <branch>` for every remaining branch.

Expected: no unique commit is deleted or silently discarded.

**Step 2: Integrate the feature branch**

Switch to `main` only with a clean working tree, then fast-forward it to the reviewed feature candidate.

Run: `git merge --ff-only feat/mingli-v51-web-integration`

Expected: `main` points at the exact reviewed and tested commit, with no merge rewrite.

**Step 3: Remove only proven-redundant worktrees and branches**

Remove a worktree only after verifying it is clean and its branch commits are contained in `main`. Delete local branches only after `git merge-base --is-ancestor <branch> main` succeeds.

Expected: active or unique branches remain; fully contained obsolete branches are removed.

### Task 6: Re-verify merged `main` and decide staging eligibility

**Files:**
- Verify: merged repository
- Verify: `infra/README.md`
- Verify: `docs/PHASE_0_GATES.md`
- Verify: `docs/releases/2026-08-10-mingli-v51-web-phase2.md`

**Step 1: Run critical merged-main checks**

Run focused API/contract tests and the production web build from `main`.

Expected: results match the pre-merge candidate.

**Step 2: Apply the staging decision gate**

Allow upload only when a real test-server target and access path are documented, deployment uses isolated staging secrets and database, migrations/backups/rollback are rehearsed, HTTPS and health checks are defined, and all real payment/traffic switches remain disabled.

Expected: one explicit result: `staging deployable`, `code-test deployable with fakes`, or `blocked`, with named blockers.

**Step 3: Deploy only if the gate passes**

Deploy the immutable `main` commit, run migrations, start web/API/Worker, verify health and one fake end-to-end flow, and record the deployed commit plus rollback command. Do not enable production traffic or real payment.

**Step 4: Record the final checkpoint**

Update the Phase 2 release note and Nowledge Mem with the tested commit, branch cleanup result, deployment outcome, and remaining production gates.
