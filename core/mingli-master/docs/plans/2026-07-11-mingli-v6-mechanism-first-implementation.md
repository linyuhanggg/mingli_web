# Mingli v6 Mechanism-First Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the daily-fortune label/template pipeline with a compact Bazi mechanism stack and applicability-filtered classical evidence while preserving deterministic calculation, source traceability, and hash-bound delivery.

**Architecture:** Build v6 in parallel on `rebuild/v6-mechanism-first`. The near-time adapter emits only chart facts and mechanisms. Classical evidence is hard-filtered by natal applicability before ranking. A compact analysis bundle feeds one natural-language synthesis, and the public gate checks facts and source scope without prescribing prose.

**Tech Stack:** Python 3 standard library, existing `sxtwl` integration, unittest source regressions, pytest Hermes regressions, Markdown reference packs, Git, rsync for final deployment.

---

### Task 1: Capture The Production Regression

**Files:**
- Modify: `scripts/test_near_time_fortune_adapter.py`
- Modify: `scripts/test_fortune_public_brief.py`
- Modify: `scripts/test_reading_evidence_bundle.py`
- Modify: `scripts/test_gate_check.py`

**Steps:**
1. Add fixtures for the real 己土戌月 / 戊子大运 / 丙戌日 case.
2. Add failing tests proving facts contain no life-domain hypothesis or public vocabulary.
3. Add a failing evidence test requiring `三秋己土`, `岁运合参`, and excluding `三春甲木`, `七月丙火`, and `寿命`.
4. Add a failing public-gate test accepting a mechanism-based answer without morning/evening or action prose.
5. Run the four focused tests and verify RED.
6. Commit the regression tests.

### Task 2: Compile A Deterministic Near-Time Mechanism Stack

**Files:**
- Modify: `scripts/near_time_fortune_adapter.py`
- Modify: `scripts/adapter_validate.py`
- Modify: `scripts/test_near_time_fortune_adapter.py`

**Steps:**
1. Bump the public contract to `fortune-public-v6-mechanism-stack` and adapter rule profile to v3.
2. Include natal month command, element inventory, hidden stems, and full natal ten gods in `birth_fact_layer`.
3. Emit major-luck/year/month/day transit layers with pillar, stem ten god, and branch relations to each natal position.
4. Emit `mechanism_stack` with deterministic relation facts and dependence metadata.
5. Remove `TEN_GOD_PRIMARY_DOMAIN`, `domain_hypotheses`, and scene-selection fields.
6. Make hour probes optional supporting facts; they never become required public phases.
7. Update independent validation for the v6 schema.
8. Run adapter and validator tests until GREEN.
9. Commit the fact-layer change.

### Task 3: Enforce Classical Applicability Before Ranking

**Files:**
- Modify: `scripts/reading_evidence_bundle.py`
- Modify: `scripts/test_reading_evidence_bundle.py`

**Steps:**
1. Teach Bazi fact extraction to read both formal Bazi and nested fortune payloads.
2. Derive natal day master, natal month branch, and season group from `birth_fact_layer`.
3. Add pack-specific hard applicability for `qiongtong-baojian`.
4. Add fortune timing anchors for `yuanhai-ziping` and `ditiansui-chanwei`.
5. Exclude longevity, death, marriage, and unrelated seasonal/day-master records unless requested.
6. Keep BM25 only as a ranking stage inside eligible records.
7. Verify the real fixture selects `QR-03-07`, `QT-Q034`, `DR-07-03`, and `DT-Q064` or equivalent applicable anchors.
8. Run evidence tests until GREEN.
9. Commit the resolver change.

### Task 4: Replace The Writing Brief With An Analysis Bundle

**Files:**
- Modify: `scripts/fortune_public_brief.py`
- Modify: `scripts/test_fortune_public_brief.py`
- Modify: `~/.hermes/scripts/fortune_calc.py`

**Steps:**
1. Bump the brief schema to `mingli-fortune-analysis-bundle-v2`.
2. Remove public vocabulary, action vocabulary, human-experience phrases, and conditional-domain fields.
3. Add public time basis, mechanism stack, applicable classical source plan, unresolved boundaries, and optional queried-hour facts.
4. Do not prescribe sentence order, phases, action, score, or scene.
5. Keep dialogue continuation metadata only for reusing the same validated target and user-selected event context.
6. Update the Hermes wrapper to emit the v6 facts plus analysis bundle without duplicate JSON.
7. Run brief tests until GREEN.
8. Commit the analysis-bundle change.

### Task 5: Reduce The Public Gate To Truth Boundaries

**Files:**
- Modify: `scripts/gate_check.py`
- Modify: `scripts/test_gate_check.py`

**Steps:**
1. Retire v5 lens, phase, human-experience, action, and conditional-domain checks.
2. Require the exact time basis and current evidence bundle.
3. Require at least one current decisive mechanism in a formal daily judgment.
4. Check explicit pillars, luck, target date, ten-god, and relation claims against facts.
5. Allow free natural prose with no mandatory phase or action.
6. Reject fixed scene claims absent from the user query or deterministic facts.
7. Preserve audit-leak checks and hash-bound `public_copy`.
8. Run all gate tests until GREEN.
9. Commit the public-gate change.

### Task 6: Align Hermes Delivery Enforcement

**Files:**
- Modify: `~/.hermes/hermes-agent/gateway/mingli_fact_guard.py`
- Modify: `~/.hermes/hermes-agent/tests/gateway/test_mingli_fact_guard.py`

**Steps:**
1. Add failing tests for v5 rejection and v6 acceptance.
2. Validate the v6 mechanism stack and analysis-bundle schema.
3. Remove requirements for v5 phase/domain writing fields.
4. Preserve current-turn fact/source/public-gate evidence and hash-bound delivery.
5. Run the full Hermes guard and API suites.
6. Commit Hermes changes separately.

### Task 7: Restore A Lightweight Main Skill

**Files:**
- Modify: `SKILL.md`
- Modify: `references/fortune-cron-reminders.md`
- Modify: `scripts/test_skill_metadata.py`

**Steps:**
1. Move long case-specific notes and obsolete v5 instructions out of the router path.
2. Keep only trigger, route, fact adapter, pack loading, conflict, answer, and public verification rules in `SKILL.md`.
3. Document quick/formal/research lanes and hard context/tool budgets.
4. Set a metadata test requiring `SKILL.md` to remain at or below 12 KB.
5. Remove all instructions that force a public sentence skeleton or life scene.
6. Run metadata and quick validation.
7. Commit the router reduction.

### Task 8: Champion/Challenger Verification And Deployment

**Files:**
- Create: `references/regression/v6-champion-challenger.md`
- Modify: `references/regression/natural-language-regression-report.md`

**Steps:**
1. Run the complete source test suite and Ruff.
2. Run the complete Hermes guard and API suites.
3. Replay broad daily fortune, domain-specific daily fortune, Bazi screenshot, static Bazi career, Meihua, Qimen missing facts, and Da Liu Ren.
4. Record output relevance, source applicability, tool calls, prompt bytes/tokens where available, and latency.
5. Confirm no source selects an inapplicable day master, season, or question domain.
6. Confirm v6 beats the deployed version and stays within the design budgets.
7. Sync the source tree to Codex, default Hermes, and liujing Hermes.
8. Restart both gateways and perform one final live daily-fortune replay.
9. Keep the current deployed commit documented as the rollback point.
10. Commit the verification report.
