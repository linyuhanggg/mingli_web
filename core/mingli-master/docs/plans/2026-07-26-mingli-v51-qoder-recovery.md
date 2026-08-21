# Mingli V5.1 Qoder Interruption Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resume the interrupted V5.1 implementation from `5e53a9e`, preserve the useful Task 8 draft, close its missing production contracts, and then finish Tasks 9–12 without treating narrow green tests as release acceptance.

**Architecture:** Keep the primary transaction artifacts unchanged and isolate every secondary system behind a private, digest-bound cross-check artifact. The prepared response exposes a safe side-specific fact/evidence view to the current caller model; the caller submits the semantic agreement/conflict review, while `complete` validates provenance mechanically and persists the review with both systems. Long-running provider-matrix generation and the complete repository suite run only after Tasks 8–11 are code-frozen, then Task 12 performs shadow deployment and release checks.

**Tech Stack:** Python 3.11, dataclasses, JSON/JSONL contracts, existing deterministic providers, atomic reading store, `unittest`, YAML-derived provider matrix, shell transaction entrypoint.

---

## Recovered baseline

- Branch: `refactor/mingli-v4-minimal-core`
- HEAD: `5e53a9e` (`docs: record task 7n follow-up acceptance`)
- Local branch position: 68 commits ahead of `origin/refactor/mingli-v4-minimal-core`
- Canonical plan: `docs/plans/2026-07-24-mingli-v51-routing-evidence-core.md`
- Completed and committed: canonical Tasks 1–7N, including the reopened Task 7N provider-identity remediation.
- Protected pre-existing file: `docs/plans/2026-07-22-mingli-v4-minimal-intelligent-core.md`; never add, modify, delete, stash, or commit it as part of V5.1.
- Recovered Task 8 draft files:
  - Modify: `references/routing.md`
  - Modify: `scripts/reading_engine/contracts.py`
  - Modify: `scripts/reading_engine/transaction.py`
  - Create: `scripts/reading_engine/cross_check.py`
  - Create: `scripts/test_v51_cross_system.py`
  - Generated but not accepted: `references/matrices/provider-completeness.yaml`
- Verified again after the interruption:
  - `scripts.test_v51_cross_system`: 14 passed
  - Task 8 related regression group: 160 passed
  - runtime/public-prose/corpus boundary audit: pass with zero findings
  - `git diff --check`: pass
- The provider matrix was written at 2026-07-26 08:47 +08:00 with input fingerprint `6043a24008bf45bb800363eb13b00d9165dbbf3f58ced006a29800cde8374749` and file SHA-256 `06880a98731f55d87b52760e61aed973064e17d4e30656f34d55253521239ac2`; Qoder left no completion receipt for the second read-only `--check`, so it is not accepted evidence.

## Why the current Task 8 draft is not complete

1. `scripts/reading_engine/factory.py::_adjudicate` deliberately returns `dimensions=()`. The production cross-check therefore emits `unassessed`, never a real agreement or conflict.
2. The secondary `CalculationResult`, `EvidenceBundle`, fact index, and judgment envelope are discarded after `prepare`; only their digests and basis text survive.
3. `ReadingRecord` does not persist the prepared cross-check when `complete` commits the reading.
4. `AnswerDraft` and `validate_answer_contract` accept only primary fact/evidence references, so a visible cross-system claim cannot be mechanically traced to the secondary system.
5. Only `caller_requested` reaches the runtime. `unresolved_primary`, `material_source_conflict`, and `distinct_compatible_fact_layer` exist as labels but are not wired end to end.
6. The input planner compares incompatible aliases such as `birth_or_four_pillars` and `birth_datetime_or_four_pillars`; a missing input can be misclassified as available.
7. `need_one_fact` exists only in the pure planner. The transaction silently skips it instead of using the existing intake/resume path.
8. The production integration test pins Bazi + Luming/Nayin. It does not prove either acceptance pair named by the canonical plan: Bazi/Ziwei or Liuren/Liuyao.
9. The helper for primary-system cross-book corroboration is tested only in isolation; default production evidence relationships are not proved end to end by Task 8 tests.

## Execution rules

1. Treat the recovered Task 8 code as a useful prototype, not a checkpoint eligible for commit.
2. Use TDD for every repair: write the failing contract, run it to prove the failure, implement the smallest coherent change, rerun focused tests, then run related regressions.
3. Do not rerun the 40-minute provider-matrix write/check or the 100-minute repository suite after each intermediate edit. Keep the release blocked, freeze Tasks 8–11, then run each long gate once in Task 12.
4. Do not deploy, install, publish, or push before every final release criterion passes.
5. Stage explicit paths only. Never use `git add -A` while the protected pre-existing plan is present.

### Task 1: Repair the recovery ledger before changing code

**Status:** Completed during the 2026-07-26 recovery audit. Future executors should rerun the read-only checks and continue at Task 2 unless the state has changed.

**Files:**

- Modify: `docs/plans/2026-07-24-mingli-v51-progress.json`
- Verify only: `docs/plans/2026-07-22-mingli-v4-minimal-intelligent-core.md`

**Step 1: Record the actual working tree**

Run:

```bash
git status --short --branch
git log -1 --oneline
git stash list
```

Expected: HEAD `5e53a9e`; the five Task 8 source/test files plus the generated matrix, recovery ledger, and this recovery plan are dirty; the protected plan remains untracked; stash is empty.

**Step 2: Update the ledger**

Set the current phase to `task8_acceptance_repair`, record the 14/160 green recovery tests as partial evidence, list the nine acceptance gaps above, and point `next_action` to Task 2 of this recovery plan.

**Step 3: Validate JSON**

Run:

```bash
jq empty docs/plans/2026-07-24-mingli-v51-progress.json
```

Expected: exit 0.

### Task 2: Write RED tests for the missing Task 8 production contract

**Files:**

- Modify: `scripts/test_v51_cross_system.py`
- Modify: `scripts/test_v51_capability_resolver.py`
- Modify: `scripts/test_v4_answer_contract.py`
- Modify: `scripts/test_reading_engine_v2.py`
- Modify: `scripts/test_reading_followup.py`

**Step 1: Prove Bazi/Ziwei preserves two complete sides**

Add `test_bazi_ziwei_prepared_bundle_preserves_secondary_artifacts` with an explicit `requested_secondary_system="ziwei"`. Assert:

```python
assert prepared.cross_check.secondary.system == "ziwei"
assert prepared.cross_check.secondary.calculation.system == "ziwei"
assert prepared.cross_check.secondary.fact_index
assert prepared.cross_check.secondary.evidence.system == "ziwei"
assert prepared.cross_check.secondary.calculation.result_hash != prepared.calculation_digest
assert not ({f.fact_id for f in prepared.fact_index} &
            {f.fact_id for f in prepared.cross_check.secondary.fact_index})
```

**Step 2: Prove Liuren/Liuyao cast persistence**

Add `test_liuren_liuyao_secondary_cast_is_seeded_once_and_replays`. Use an explicit Liuyao secondary digital cast, reload the pending record, and assert the six tosses, seed source, secondary calculation digest, and cross-check digest are identical after round-trip.

**Step 3: Prove the caller must submit a real comparison**

Add `test_complete_requires_traceable_cross_check_review`. A draft without a cross-check review must return `AnswerRepairRequired`; a review with one primary trace and one secondary trace must be accepted.

**Step 4: Prove accepted persistence**

Add `test_committed_reading_roundtrip_preserves_cross_check_artifacts_and_review`. Reload the committed record and assert both side digests, the review digest, shared dimensions, and priority reason survive.

**Step 5: Prove every runtime purpose**

Add separate tests for:

- `caller_requested` from the structured IntentFrame.
- `unresolved_primary` from an actually unsupported primary dimension.
- `material_source_conflict` from an applicable `SourceRelationship(relation="conflict")`.
- `distinct_compatible_fact_layer` from an explicit semantic intent field.

Each test must assert the purpose in the prepared private record, not merely call `plan_cross_check` directly.

**Step 6: Prove missing-input behavior**

Add:

```python
def test_missing_input_alias_cannot_be_reported_ready(): ...
def test_explicit_secondary_with_one_missing_fact_enters_intake(): ...
def test_two_missing_secondary_facts_do_not_block_primary(): ...
```

The first test covers both `birth_or_four_pillars` and `birth_datetime_or_four_pillars`. The second must resume through the existing intake record without repeating the original question.

**Step 7: Prove target selection and cross-book defaults**

Add tests showing an explicitly requested Ziwei secondary cannot silently become Luming/Nayin, and that a normal primary-only request still exposes applicable independent cross-book `source_relationships` without running a second provider.

**Step 8: Run RED tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B -m unittest \
  scripts.test_v51_cross_system \
  scripts.test_v51_capability_resolver \
  scripts.test_v4_answer_contract \
  scripts.test_reading_engine_v2 \
  scripts.test_reading_followup -v
```

Expected: failures specifically show missing secondary artifacts, missing review/persistence, unreachable purposes, alias misclassification, and absent intake integration.

### Task 3: Make cross-check intent and selection explicit

**Files:**

- Modify: `scripts/reading_engine/intent_frame.py`
- Modify: `scripts/reading_engine/capability_resolver.py`
- Modify: `scripts/reading_engine/contracts.py`
- Modify: `scripts/reading_engine/cross_check.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `references/routing.md`

**Step 1: Extend the semantic frame without reading raw prose**

Add optional typed fields while retaining the existing boolean for current V4 callers:

```python
cross_check_purpose: str | None = None
requested_secondary_system: str | None = None
```

Validate purpose against the four-value contract. When `cross_check_requested` is true and no purpose is supplied, canonicalize to `caller_requested`. Reject a secondary system equal to the primary requested method.

**Step 2: Stop reconstructing missing inputs from aliases**

Change `plan_cross_check` to accept `secondary_missing_inputs: tuple[str, ...]` directly from `missing_required_inputs(candidate, request)`. The planner must count that tuple and never infer availability by subtracting differently named fields.

**Step 3: Honor an explicit secondary target**

If `requested_secondary_system` is set, evaluate only that system. If no target is set, order eligible systems by declared `default_priority` and stable system ID; do not use alphabetical order alone.

**Step 4: Wire one-fact intake**

For an explicit caller-requested secondary with exactly one missing external fact, save the existing `IntakeRecord` with the original primary request and return `NeedUserFact`. On resume, merge the supplied fact and rerun the same primary/secondary plan. For automatic purposes, a missing secondary fact must not block an otherwise valid primary reading.

**Step 5: Derive runtime purposes at the correct phase**

- Before returning `UnsupportedDimension`, attempt `unresolved_primary` only for the exact unsupported dimension.
- After evidence compilation, set `material_source_conflict` only when an applicable selected relationship is `conflict`.
- Accept `distinct_compatible_fact_layer` only from the structured caller frame.
- Never infer a purpose from query keywords.

**Step 6: Run focused tests**

Run the command from Task 2. Expected: intent, purpose, target selection, alias, and intake tests pass; artifact/review tests may remain RED until Tasks 4–5.

### Task 4: Persist full side-specific artifacts without merging namespaces

**Files:**

- Modify: `scripts/reading_engine/contracts.py`
- Modify: `scripts/reading_engine/fact_index.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `scripts/reading_engine/storage.py`
- Modify: `scripts/test_v51_cross_system.py`
- Modify: `scripts/test_reading_engine_v2.py`

**Step 1: Separate private artifacts from the public view**

Replace the summary-only secondary side with a private record containing its exact `CalculationResult`, `EvidenceBundle`, `Judgment` envelope, lineage, and digest. Keep primary artifacts in their existing top-level fields.

**Step 2: Build a safe side-local fact index**

Do not flatten primary and secondary facts into one ID space. The public cross-check view must carry a side namespace plus a side-local fact index; existing primary `FactRef` IDs remain backward compatible.

**Step 3: Bind every artifact**

The cross-check digest must bind:

- reading ID and version
- purpose and requested secondary system
- primary calculation/evidence/judgment digests
- complete secondary calculation/evidence/judgment digests
- both independent lineages
- shared dimensions
- candidate selection audit and failure reasons

**Step 4: Persist through completion**

Add optional cross-check fields to `ReadingRecord` and its `to_dict`/`from_dict` path. `complete` must copy the prepared cross-check into the committed record instead of dropping it.

**Step 5: Keep projections privacy-safe**

Reuse the existing bounded public projections for Liuyao, Selection, Fengshui, and Physiognomy. Do not expose raw media, private observation provenance, store paths, or full oversized candidate tables through the secondary view.

**Step 6: Run artifact tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B -m unittest \
  scripts.test_v51_cross_system \
  scripts.test_reading_engine_v2 \
  scripts.test_atomic_pipeline_publish -v
```

Expected: two-side prepare and pending/committed round-trip tests pass; answer-review tests remain RED until Task 5.

### Task 5: Make the caller own semantic comparison and validate it mechanically

**Files:**

- Modify: `scripts/reading_engine/contracts.py`
- Modify: `scripts/reading_engine/answer_contract.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `references/public-reading-contract.md`
- Modify: `scripts/test_v4_answer_contract.py`
- Modify: `scripts/test_v51_cross_system.py`

**Step 1: Add a caller-supplied review contract**

Add an optional `cross_check_review` to `AnswerDraft`. Each shared dimension carries:

```python
dimension
status  # agreement|conflict|primary_only|secondary_only|unresolved
primary_conclusion
secondary_conclusion
priority_system
priority_reason
primary_fact_refs / primary_evidence_refs / primary_counter_evidence_refs
secondary_fact_refs / secondary_evidence_refs / secondary_counter_evidence_refs
visible_text
visible_span
```

The caller model decides semantic agreement/conflict. The runtime must not compare prose strings or vote across systems.

**Step 2: Validate structure and provenance only**

Require exactly the prepared shared dimensions, reject `unassessed` at completion, validate every reference against the correct side, require visible text/span alignment, and restrict `priority_system` to the two selected systems. A `secondary_only` priority is valid only when the prepared primary side recorded that exact dimension as unsupported.

**Step 3: Persist the accepted review**

Bind the review digest into `AcceptedReading` and the committed `ReadingRecord`. Preserve the primary calculation/evidence/judgment digests unchanged for gateway compatibility.

**Step 4: Protect public output**

Extend private-protocol scanning to the cross-check digests, namespaces, provider identities, fact IDs, and evidence IDs. The public answer may explain both systems naturally but cannot print internal contract data.

**Step 5: Run focused tests**

Run the Task 2 command. Expected: all Task 8 RED tests pass.

### Task 6: Close Task 8 and commit only the coherent checkpoint

**Files:**

- All Task 8 files from Tasks 2–5
- Modify: `docs/plans/2026-07-24-mingli-v51-progress.json`
- Do not stage: `references/matrices/provider-completeness.yaml`
- Do not stage: `docs/plans/2026-07-22-mingli-v4-minimal-intelligent-core.md`

**Step 1: Run the focused and related suites**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B -m unittest scripts.test_v51_cross_system -v

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B -m unittest \
  scripts.test_v51_cross_system scripts.test_reading_engine_v2 \
  scripts.test_reading_followup scripts.test_followup_publish \
  scripts.test_reading_transaction_cli scripts.test_v51_capability_resolver \
  scripts.test_v51_fact_extensions scripts.test_atomic_pipeline_publish \
  scripts.test_single_authority_contract scripts.test_skill_metadata \
  scripts.test_v4_answer_contract scripts.test_v4_conversation_trajectories \
  scripts.test_v4_followup_state scripts.test_v4_intake_conversation \
  scripts.test_v4_providers scripts.test_v4_request_contract \
  scripts.test_v4_skill_minimalism
```

Expected: all pass with a count greater than the recovered 160.

**Step 2: Run static gates**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B scripts/audit_v4_runtime_boundary.py
git diff --check
```

Expected: all three audit sections pass with empty findings; diff check exits 0.

**Step 3: Perform a fresh read-only review**

Review the complete Task 8 diff against the nine gaps in this plan. No P1/P2 finding may remain. Any finding reopens the focused RED/GREEN loop.

**Step 4: Update the ledger and commit explicit paths**

Record exact test counts and review results. Stage only reviewed Task 8 source, tests, routing docs, recovery plan, and ledger. Verify `git diff --cached --name-only` before committing.

Commit:

```bash
git commit -m "feat: add traceable purpose-bound cross-system corroboration"
```

### Task 7: Execute canonical Task 9 without weakening Task 8 traces

**Files:**

- Modify: `SKILL.md`
- Modify: `scripts/reading_engine/answer_contract.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `references/public-reading-contract.md`
- Modify: `scripts/test_v4_answer_contract.py`
- Create: `scripts/test_v51_natural_answer_contract.py`

**Steps:**

1. Write RED tests proving semantic prose regexes cannot accept/reject meaning, while mechanical privacy, span, digest, primary trace, and cross-check trace checks remain strict.
2. Remove only semantic wording gates; retain mechanical protocol/digest leakage checks.
3. Require one private caller-model review over both primary and optional secondary artifacts.
4. Test natural answers across paraphrases, direct conclusions, counter-evidence, and cross-system conflict.
5. Run focused tests, related regressions, runtime boundary audit, and `git diff --check`.
6. Commit `refactor: keep mingli facts strict and prose intelligent`.

### Task 8: Execute canonical Task 10 with fixed artifacts

**Files:**

- Create: `tests/replay/mingli-routing-cases.jsonl`
- Create: `tests/replay/mingli-answer-cases.jsonl`
- Create: `scripts/run_model_replay.py`
- Create: `docs/model-evaluation.md`

**Steps:**

1. Build anonymized cases for all 13 systems, non-Mingli negatives, intake/resume, follow-up/correct/recast, images, source conflict, and both accepted cross-system pairs.
2. Freeze calculation, evidence, and cross-check artifacts across model comparisons.
3. Score routing, unsupported claims, evidence relevance, direct answer, continuity, naturalness, cost, and latency.
4. Prove changing the host model changes no provider, digest, state, or artifact identity.
5. Commit `test: add model-independent mingli replay evaluation`.

### Task 9: Execute canonical Task 11 with immutable outcomes

**Files:**

- Create: `scripts/reading_engine/outcome_store.py`
- Create: `scripts/record_reading_outcome.py`
- Create: `scripts/test_v51_outcome_calibration.py`
- Create: `docs/outcome-calibration.md`

**Steps:**

1. Write RED tests for immutable claim identity, hit/partial/miss/unknown outcomes, duplicate reports, and tampering.
2. Bind outcomes to accepted claim and optional cross-check review digests without modifying the original reading.
3. Aggregate only by versioned provider/rule/source/dimension/horizon; do not create unsupported probability estimates.
4. Run focused and related regressions, then commit `feat: add immutable mingli outcome calibration`.

### Task 10: Run the single final matrix/full-suite gate and release Task 12

**Files:**

- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/plans/2026-07-24-mingli-v51-progress.json`
- Regenerate: `references/matrices/provider-completeness.yaml`
- Update deployment manifests/checksums only after all source acceptance passes

**Step 1: Freeze source and regenerate once**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B scripts/audit_provider_completeness.py --write
shasum -a 256 references/matrices/provider-completeness.yaml
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B scripts/audit_provider_completeness.py --check
```

Expected: 13/13 ready, empty findings, and a second process reports zero drift.

**Step 2: Run the complete repository suite**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts .venv/bin/python -B -m unittest discover -s scripts -p 'test_*.py'
```

Expected: all tests pass; count must exceed the Task 7N baseline of 1262.

**Step 3: Run all audits and replay gates**

Run all 13 dedicated provider audits, algorithm-source verification, runtime/public-prose/corpus audit, release archive audit, reference catalog audit, model replay, legacy-vs-V4 shadow replay, and `git diff --check`. Any failure reopens the owning task.

**Step 4: Review changed public answers**

Manually inspect every replay where the selected primary system, secondary system, cross-check status, direct answer, or source priority changed.

**Step 5: Build one clean artifact**

Build from a clean detached worktree, record checksums, and prove the archive contains the exact reviewed files. Do not include the protected pre-existing plan.

**Step 6: Fix and verify both Hermes gateways in shadow mode**

The active gateway still has regex semantic authority, and the Liujing gateway is disabled against an obsolete tree. Remove gateway meaning classification, bind the private V5.1 artifact contract, restart each service separately, and verify CLI and Desktop independently with a fresh Desktop Quest. Never infer Desktop success from CLI success.

**Step 7: Promote only after zero regressions**

After shadow replay shows zero routing regressions and zero unsupported evidence/cross-check bindings, install the identical checksum artifact to GitHub, Codex, the default Hermes gateway, and the Liujing gateway. Re-run manifest, health, transaction, and real-conversation smoke tests on each target.

**Step 8: Final commit and release record**

Update the ledger with exact hashes, test counts, replay results, gateway checks, and deployment identities. Only then mark Tasks 8–12 and the final release criteria complete.

---

## Stop conditions

- Do not mark Task 8 complete while production comparisons can remain `unassessed`.
- Do not mark Task 8 complete if the accepted record cannot reconstruct both calculation/evidence sides and the caller review.
- Do not accept one missing-input unit test as proof of intake/resume behavior.
- Do not accept Bazi/Luming alone as proof of the canonical Bazi/Ziwei or Liuren/Liuyao acceptance pair.
- Do not treat a matrix `--write` as proof that a fresh `--check` passed.
- Do not deploy or push while `release_blocked` is true.
