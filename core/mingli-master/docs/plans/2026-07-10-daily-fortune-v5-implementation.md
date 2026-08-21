# Daily Fortune V5 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make broad daily-fortune answers fact-complete, query-relevant, non-repetitive, and naturally human without prescribing fixed prose.

**Architecture:** Add a generic near-time Bazi adapter to the skill and keep the Hermes personal helper as a thin profile wrapper. Replace pseudo-convergence with source-family-aware evidence, extend the public gate with broad-query coverage and repetition checks, and enforce the same fact contract at Hermes delivery time.

**Tech Stack:** Python 3, `sxtwl`, `unittest`, Hermes gateway Python, Markdown skill references.

---

### Task 1: Lock The Captured Failure

**Files:**
- Modify: `scripts/test_gate_check.py`
- Modify: `~/.hermes/scripts/test_daily_fortune_quality.py`

**Steps:**
1. Add the exact July 10 `算下明天运势` query, bad reply, prior repeated reply, and v5-shaped facts as fixtures.
2. Assert the bad reply is rejected for narrow-scene dominance, missing whole-day coverage, and repetition.
3. Add three differently worded warm, complete replies that must pass.
4. Run the focused tests and confirm they fail for the expected missing behavior.

### Task 2: Build The Generic V5 Fact Adapter

**Files:**
- Create: `scripts/near_time_fortune_adapter.py`
- Create: `scripts/test_near_time_fortune_adapter.py`
- Modify: `scripts/adapter_validate.py`

**Steps:**
1. Test full birth normalization, active major luck, current year/month/day/hour, source-family deduplication, phase profiles, invalid windows, and no concrete scene output.
2. Confirm failures before implementation.
3. Implement the adapter by calling `bazi_fact_adapter.build_from_birth` and deriving only neutral transit facts.
4. Validate the v5 schema and rerun focused tests.

### Task 3: Replace The Hermes Personal Helper

**Files:**
- Modify: `~/.hermes/scripts/fortune_calc.py`
- Modify: `~/.hermes/scripts/test_daily_fortune_quality.py`

**Steps:**
1. Add tests requiring the known birth datetime, active `戊子` cycle on 2026-07-11, recent public reply retrieval, and byte-for-byte preservation of the generic v5 contract.
2. Confirm the old helper fails.
3. Turn the helper into a thin wrapper around the skill adapter and append the last five public fortune replies from the Hermes session database.
4. Rerun the external tests.

### Task 4: Make The Public Gate Semantic

**Files:**
- Modify: `scripts/gate_check.py`
- Modify: `scripts/test_gate_check.py`

**Steps:**
1. Require broad-query coverage: overall tendency, supported human-experience implication, and at least two supported day phases when the contract has phase contrast.
2. Reject an unrequested life domain as the dominant answer and reject auxiliary relation lenses promoted to the primary conclusion.
3. Compare against recent public replies and reject a repeated single-lens answer or high-similarity rewrite.
4. Accept varied prose and do not require sentence order, scores, headings, or stock phrases.
5. Run focused and complete skill tests.

### Task 5: Update Skill Behavior And Regression Corpus

**Files:**
- Modify: `SKILL.md`
- Modify: `references/fortune-cron-reminders.md`
- Modify: `references/mingli-anti-empty-output.md`
- Modify: `references/regression/natural-language-regression.yaml`
- Modify: `references/regression/natural-language-regression-report.md`

**Steps:**
1. Replace the old stable-lens wording with the v5 source-family contract.
2. State that warmth is grounded attention to likely experience, not invented scenes or canned reassurance.
3. Forbid runtime checker patching to bypass a failed contract.
4. Add the two captured failures and varied passing answers to natural-language regression.
5. Run metadata, regression, and quick validation.

### Task 6: Enforce V5 At Hermes Delivery

**Files:**
- Modify: `~/.hermes/hermes-agent/gateway/mingli_fact_guard.py`
- Modify: `~/.hermes/hermes-agent/tests/gateway/test_mingli_fact_guard.py`
- Modify only if needed: `~/.hermes/hermes-agent/gateway/run.py`

**Steps:**
1. Add tests showing broad today/tomorrow requests buffer delivery and fail without a successful v5 `fortune_calc.py --window` execution.
2. Add tests for wrong target date, invalid window, old contract, the captured bad reply, warm varied replies, and non-fortune questions.
3. Implement extraction and semantic enforcement without changing unrelated Bazi/Liuren behavior.
4. Run the Hermes focused suite.

### Task 7: Audit Similar Failures

**Files:**
- Modify tests or references only when a new reproduced defect requires it.

**Steps:**
1. Mine recent Hermes daily-fortune and reminder outputs for repeated motifs, unsupported scenes, missing adapters, wrong dates, and runtime patches.
2. Replay representative failures through the new gates.
3. Add minimal regression cases for every reproduced class.
4. Run all skill, external fortune, and Hermes guard tests.

### Task 8: Deploy And Verify

**Files:**
- Sync source skill to Codex, Hermes main, and Hermes liujing runtime directories.

**Steps:**
1. Commit source skill changes and relevant Hermes source changes separately.
2. Sync runtime copies without touching deprecated `ai-now`.
3. Verify hashes for the skill, adapter, gate, and reference files.
4. Restart both launchd-managed Hermes gateways.
5. Replay the captured bad response and confirm rejection.
6. Run a fresh `算下明天运势` fact flow and inspect that the generated answer contract is whole-day, non-repetitive, and naturally worded.
