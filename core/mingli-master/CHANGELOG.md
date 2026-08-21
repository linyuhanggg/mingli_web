# Changelog

All notable changes to the Mingli Master skill are documented here.
Progress receipts live in `docs/plans/2026-07-24-mingli-v51-progress.json`.

## V5.1 Provider Contract Hardened Core (2026-08-08)

V5.1 promotes the independently accepted provider-maintainability work to a
major product release and makes the product identity consistent across public
surfaces, runtime namespaces, fixtures, schemas, tests, documentation, and
provider adapter versions.

### Changed

- Unified all live release identifiers on V5.1, renamed the old protocol,
  fixture, test, and plan filenames to `v51`, and raised the Qimen and Taiyi
  adapter versions to `5.1.0`.
- Added the internal FactContract seam and moved Bazi validation behind its
  provider-owned contract, leaving the other 12 providers on the compatible
  legacy path for deliberate one-by-one migration.
- Restored the original public `validate_payload` signature and historical
  finding order while keeping catalog injection private to tests and internal
  dispatch.
- Updated standalone audit commands to run with `-B`; direct provider audit
  execution disables bytecode writes before importing third-party packages.

### Fixed

- Required-key hooks now fail closed unless they return an exact built-in
  tuple containing exact built-in, non-blank strings. Malicious tuple/string
  subclasses, strings used as iterables, and unhashable values can no longer
  bypass validation or escape exceptions from the facade.
- Provider contract load, origin, finding, payload-conflict, and required-key
  boundaries remain explicit findings rather than uncaught exceptions.
- Removed stale runtime bytecode that could make an otherwise valid installed
  venv fail its identity probe.

### Verification

- Focused contract/runtime regression: 86 tests, 0 failed.
- Full repository suite: 126 targets, 93 modules, 1584 tests, 0 failed.
- Provider completeness: 13/13 ready, findings empty; runtime provisioning,
  vocabulary locality, answer exporter, matrix fingerprint, and diff checks
  passed.

### Release status

- The owner authorized the V5.1 operational rollout to every existing Codex,
  Agent, and Hermes profile installation on the Mac mini, plus the existing
  Codex installation on the MacBook Pro. No new installation roots are to be
  invented.
- Host-model prediction artifacts and strict independent blinded review remain
  separate external-quality gates; operational deployment does not imply that
  those gates passed.

## V5.1 Full-System Intelligent Core — release candidate (2026-07-27)

Source freeze: commit `05f5156` (runtime source identical to `d4ed627`) on
branch `refactor/mingli-v4-minimal-core`.

### Added

- Semantic IntentFrame routing with capability-based resolution; V4 is the
  only live transaction path and no production keyword router remains.
- Deterministic providers and dedicated completeness audits for all 13
  routes, including early Luming/Nayin, Qimen (37 boards), Taiyi (72
  boards), Selection, Fengshui, and Physiognomy.
- Shared `calendar_core`/`ephemeris_core` with pinned astronomy-engine.
- Source-bound classical evidence with applicability predicates, exact
  anchors, and independent cross-system corroboration.
- Outcome calibration records without history rewriting.
- Bounded `caller_view` in prepared bundles: its primary fact index normally
  selects at most 48 facts, while evidence-required references may exceed that
  limit to preserve provenance. Cross-check sides use a separate bounded
  projection and omit `basis_text` above 20,000 UTF-8 bytes; the persisted
  record, evidence references, and digests stay complete.
- Model-independent replay evaluation (`scripts/run_model_replay.py`,
  `tests/replay/`) and the trusted live replay runner with a per-turn
  execution contract.

### Fixed

Commit order on `refactor/mingli-v4-minimal-core`: `7413cc5` is the parent
of the `b65e99d` review baseline, and the increment after `b65e99d` is
`ea0990d` → `d4ed627` → `05f5156` → `74e9d72`.

- Exact instant horizons are accepted (`7413cc5`, parent of `b65e99d`).
- Live replay runner no longer binds a follow-up turn to the wrong final
  reply (`fix: bound live transaction replay context`, `b65e99d`).
- Prepared bundles gained the bounded `caller_view` and week/day-range
  horizon acceptance (`ea0990d`); these changes are contained in every
  subsequent test run and artifact.
- Documented null-bounded `day`/`month`/`year` horizons now bind to the
  request reference period instead of failing as unsupported; explicit
  bounds are never rewritten (`d4ed627`).
- The production launcher now exports `PYTHONDONTWRITEBYTECODE=1` so nested
  provider Python processes cannot create unchecked runtime bytecode and make
  a later probe fail closed with exit 78. A launcher-level regression exercises
  the real parent/child process boundary.
- The production Hermes gateway now consumes V5.1 tool events through the
  transaction observer. The obsolete semantic fact guard was deleted from the
  gateway source instead of being left as a fallback, and the installed venv
  is pinned to the verified private release tree rather than an auto-update
  staging worktree.
- Retired pre-V5.1 architecture, hardening, acceptance, test, migration, and
  rollback documents were removed. They contained executable paths to old
  Skill/Gateway trees and are no longer valid recovery instructions.

### Verification (frozen source `05f5156`)

- Provider matrix: 13/13 ready, findings empty, sha256
  `52df87a50dcee26d7e5c31596653a5e9e3e4cda443eb7221256d3dc697ec708c`,
  fresh-process `--check` zero drift.
- Full repository suite: 1407 tests in 6320.960s, OK (baseline 1262).
- All 13 dedicated provider audits pass; algorithm-source, runtime/
  public-prose/corpus boundary, release archive (854 files), and reference
  catalog (packs=55) audits pass; `git diff --check` clean.
- Shadow replay at Mingli `d4ed627` / Hermes `e7d4924545`: 16/16 cases pass
  automated routing/public/trace/evidence gates (5 cases re-run after
  upstream connection-error windows exceeded the fixed 180s client budget;
  the timeout was never raised and human review was never inferred).
- Legacy-vs-V4 offline comparison manually reviewed: all changed answers
  are fail-closed intake stops or corrected chart-grounded readings.
- Verified runtime artifact (source `d4ed627`): sha256
  `1b2d58cd43043452e58a2226eee7c8d9a40463c26045fcbbbebd89c6686596b8`.

### Release status

- Task 10 (measure model choice honestly): the model replay tooling,
  fixtures, and fail-closed scorer implementation are complete, but the
  external evaluation has never run, so Task 10 overall is partial/blocked
  on external inputs.
- Task 12 (full regression, shadow comparison, and deployment) remains in
  progress/blocked on external evaluation and a supervised live-session
  smoke. On 2026-07-28 the owner explicitly authorized an operational rollout
  before those external quality gates: GitHub `main` and the V5.1 branch were
  advanced to `f566085`, and the same verified release was installed to Codex,
  the default Hermes profile, and the `liujing` profile. This deployment
  receipt is a documentation-only follow-up to that runtime commit.
- The default Hermes gateway is the sole gateway process. It routes `liujing`
  through `multiplex_profiles`/`profile_routes`; `liujing` is not a second
  gateway and no independent `8646` listener is expected.
- `release_blocked: true`, `deployment_allowed: true`,
  `github_push_allowed: true`; operational authorization and release-quality
  acceptance are recorded separately.
- Rollback references were pushed before rollout:
  `backup/production-a59cb6c-before-v51-20260728` for the prior installed
  release and `backup/github-main-before-v51-20260728` for the prior remote
  default branch.
- Remaining gates, in order:
  1. External host-model routing and answer prediction manifests
     (`docs/model-evaluation.md`); they do not exist on this host and must
     never be fabricated.
  2. A separately hash-bound blinded human review manifest; human review
     stays `null` until it exists and is never inferred from automated
     gates.
  3. Score and review those external artifacts without treating the completed
     operational rollout as evidence that the quality gates passed.
  4. Run the remaining supervised live-session smoke through the single
     default gateway, covering both the default and `liujing` profile routes.

## V4 Minimal Intelligent Core (2026-07-22)

- Single-authority V2 reading transaction (`run_reading_transaction.sh`)
  with prepare/complete lifecycle, atomic storage, and public gates.
- Historical pre-V5.1 acceptance and rollback instructions were retired on
  2026-07-28 so they cannot reactivate obsolete deployments.
