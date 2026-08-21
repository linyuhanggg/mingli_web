# Global Direct Reading Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply one evidence-bound, detailed, no-category-taboo public-reading
contract across every `mingli-master` system and deploy it to all runtime
copies.

**Architecture:** A single contract matrix drives output terminology, default
detail, direct-scene resolution, and follow-up behavior. Existing deterministic
adapters and source bundles remain the authority for facts; public gates enforce
fact matching and coverage rather than suppressing categories.

**Tech Stack:** Python 3 standard library, YAML reference matrices, unittest,
Hermes gateway pytest, shell deployment scripts.

---

### Task 1: Capture the current behavioral baseline

**Files:**
- Create: `references/regression/global-direct-reading-cases.yaml`
- Create: `scripts/test_global_direct_reading_contract.py`
- Test: `scripts/test_global_direct_reading_contract.py`

1. Add representative cases for all systems, including current-state,
   relationship, gambling, secret, location, daily fortune, selection, and
   missing-fact questions.
2. Add failing tests for the current regressions: `卦象` label, default detailed
   current-state response, same-lesson detail follow-up, sensitive categories
   without an unsupported-category refusal, and system-correct terminology.
3. Run the focused test and record the expected failures before implementation.
4. Commit: `test: define global direct-reading regressions`.

### Task 2: Add the public-reading contract matrix

**Files:**
- Create: `references/matrices/public-reading-contract.yaml`
- Create: `references/matrices/public-reading-contract.md`
- Modify: `scripts/test_skill_metadata.py`

1. Define per-system `display_basis`, `default_depth`, `direct_scene_policy`,
   `location_resolution`, `followup_mode`, and required fact scope.
2. Include all supported systems and their aliases; never use one global
   `卦象` label for charts, houses, or environmental observations.
3. Write tests that validate every routing system has exactly one contract and
   that no contract declares a category-level taboo.
4. Commit: `feat: define public reading contract matrix`.

### Task 3: Compile contracts into public briefs

**Files:**
- Modify: `scripts/reading_public_brief.py`
- Modify: `scripts/liuren_public_brief.py`
- Modify: `scripts/liuren_calc.py`
- Modify: `scripts/fortune_public_brief.py`
- Test: `scripts/test_liuren_public_brief.py`
- Test: `scripts/test_fortune_public_brief.py`

1. Write failing tests for an `answer_profile` emitted from each brief.
2. Add the smallest loader for the contract matrix and emit `answer_profile`
   into each current pipeline's synthesis context.
3. For concrete current-state questions, emit detail axes: action, people,
   setting, privacy, money/entertainment, direction/location, and timing only
   when applicable.
4. Keep the existing facts, sources, hashes, and delivery contracts unchanged.
5. Commit: `feat: bind public answer profiles to reading briefs`.

### Task 4: Replace conflicting prompt and terminology rules

**Files:**
- Modify: `SKILL.md`
- Modify: `references/routing.md`
- Modify: `references/liuren-casting-gate.md`
- Modify: `references/conversational-reading-dialogue.md`
- Modify: `references/matrices/routing-matrix.md`
- Test: `scripts/test_liuren_routing_contract.py`
- Test: `scripts/test_skill_metadata.py`

1. Write tests that reject `课象` as the required public DLR label and reject
   the stale short-event route conflict.
2. Replace compact/follow-up-only/sensitive-category-refusal language with the
   approved global contract.
3. Preserve method-specific fact limits: a limit must explain the actual
   missing layer or resolution, never hide a category.
4. Commit: `fix: align whole-skill public reading instructions`.

### Task 5: Update gates without weakening fact integrity

**Files:**
- Modify: `scripts/gate_check.py`
- Modify: `scripts/adapter_validate.py` if schema validation needs the profile
- Test: `scripts/test_gate_check.py`
- Test: `scripts/test_global_direct_reading_contract.py`

1. Write tests proving `卦象` passes DLR public validation and direct language
   about socializing, gambling, secrets, and location does not fail merely for
   category vocabulary.
2. Require a matching `answer_profile` and enough multi-factor support for a
   scene claim; retain the existing wrong-chart, wrong-time, one-general, and
   wrong-question failures.
3. Ensure detailed answers are not rejected for length unless they expose
   internal artifacts or become genuinely report-sized.
4. Commit: `fix: gate direct scenes by evidence instead of category`.

### Task 6: Repair whole-skill follow-up and routing behavior

**Files:**
- Modify: `gateway/mingli_fact_guard.py`
- Modify: `gateway/platforms/api_server.py` only if context propagation needs it
- Modify: `gateway/run.py` only if context propagation needs it
- Test: `tests/gateway/test_mingli_fact_guard.py`

1. Add conversation tests for `具体解读一下`, `说细一点`, and `按原课重写`.
2. Assert no original-question replay, no accidental recast, and preservation
   of the selected system.
3. Add natural-language routing tests for all high-risk categories and for
   explicit-system precedence.
4. Commit: `fix: preserve detailed reading context across follow-ups`.

### Task 7: Audit adjacent failure modes

**Files:**
- Create: `scripts/audit_public_reading_contract.py`
- Create: `scripts/test_public_reading_contract_audit.py`
- Modify: `references/regression/natural-language-regression.yaml`

1. Audit canonical docs and runtime copies for conflicting terminology,
   category-taboo language, stale system routes, and hash drift.
2. Run the audit against canonical, Codex, default Hermes, and liujing Hermes.
3. Add replay cases for image inputs, missing facts, historical event times,
   target-location replies, source disagreement, and cross-system requests.
4. Commit: `test: audit cross-system public reading consistency`.

### Task 8: Verify, deploy, and publish

**Files:**
- Modify only generated regression reports that are intentionally versioned

1. Run `python3 -m unittest discover -s scripts -p 'test_*.py' -q`.
2. Run `./.venv/bin/pytest -q tests/gateway/test_mingli_fact_guard.py`.
3. Run `scripts/audit_public_reading_contract.py` on all four copies.
4. Execute live Hermes replays for every high-risk case; inspect the first
   answer for directness, detail, fact consistency, and no category refusal.
5. Sync the canonical skill into Codex/default Hermes/liujing Hermes, restart
   both gateways, and repeat the audit.
6. Commit: `feat: deploy global direct reading contract`.
7. Push the branch to the private `1960697431/mingli-master-skill` repository
   only after all checks pass.
