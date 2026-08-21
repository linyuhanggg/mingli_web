# Mingli v7 Inference Graph And Calibration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace free-form rule selection with digest-bound inference graphs and add answer-isolated empirical replay for the entire Mingli routing architecture.

**Architecture:** Add v7 artifacts beside the current v6 pipeline, migrate Da Liu Ren and Bazi first, then make every remaining route use the same fact/inference/render contracts or fail closed. Keep classical packs as provenance, freeze predictions before outcomes, and reduce the legacy regex gate after structural validation is active.

**Tech Stack:** Python 3 standard library, JSON/YAML reference data, existing `sxtwl` and Da Liu Ren adapters, `unittest`, local Hermes pipeline wrappers, SQLite replay extraction, Git.

---

### Task 1: Capture The Outcome-Leak Regression

**Files:**
- Create: `references/regression/cases/real/liuren-stock-loss-v1.input.json`
- Create: `references/regression/cases/real/liuren-stock-loss-v1.outcome.json`
- Create: `scripts/test_prediction_freeze.py`

**Steps:**
1. Copy the exact validated chart and question from the production replay into the input fixture; omit every disclosed outcome.
2. Put the later confirmed loss and source provenance only in the outcome fixture.
3. Write a failing test requiring one frozen prediction digest for the input and rejecting an outcome field in inference input.
4. Write a failing metamorphic test proving that appending outcome disclosure cannot mutate an existing prediction.
5. Run `python3 -m unittest scripts.test_prediction_freeze -v` and verify RED.

### Task 2: Introduce Canonical Inference Artifacts

**Files:**
- Create: `scripts/inference_contract.py`
- Create: `scripts/test_inference_contract.py`

**Steps:**
1. Test canonical digests, question contracts, activation validation, adjudication validation, and forbidden outcome fields.
2. Implement canonical JSON projection and schema validators.
3. Require fact, evidence, question, activation, and adjudication digests.
4. Verify RED then GREEN with the focused test.

### Task 3: Compile Da Liu Ren Rule Activations

**Files:**
- Create: `scripts/liuren_inference.py`
- Create: `references/inference/liuren-rules-v1.json`
- Create: `scripts/test_liuren_inference.py`
- Modify: `scripts/liuren_public_brief.py`

**Steps:**
1. Add failing tests for stock profit/loss recognition, three-transmission stage order, wealth presence, void modifiers, dependency grouping, and `underdetermined` when rules do not separate profit from loss.
2. Encode only rules already traceable to `DLR-*`, `LR-*`, and `LM-*` anchors.
3. Compile activations from exact fact paths; no prose inference.
4. Emit deterministic adjudication and counter-evidence.
5. Verify the stock replay cannot output both polarities and initially abstains unless the encoded rules genuinely resolve it.

### Task 4: Freeze And Score Predictions

**Files:**
- Create: `scripts/prediction_freeze.py`
- Create: `scripts/benchmark_runner.py`
- Modify: `scripts/case_log.py`
- Create: `scripts/test_benchmark_runner.py`

**Steps:**
1. Write failing tests for outcome isolation, immutable prediction files, duplicate case IDs, tampered digests, and separate scoring.
2. Implement `predict` and `score` subcommands; `predict` must never accept an outcome path.
3. Record hit, partial, miss, and abstain separately.
4. Add Brier score only for binary claims with a declared probability mapping.
5. Run focused tests RED then GREEN.

### Task 5: Compile Bazi Rule Activations

**Files:**
- Create: `scripts/bazi_inference.py`
- Create: `references/inference/bazi-rules-v1.json`
- Create: `scripts/test_bazi_inference.py`
- Modify: `scripts/near_time_fortune_adapter.py`
- Modify: `scripts/bazi_fact_adapter.py`

**Steps:**
1. Test month-command, season, strength, structure, flow, Tiaohou, timing activation, and dependent transit relations.
2. Convert `bazi-core-decision-stack.yaml` stages from routing metadata into executable activation records.
3. Keep unresolved strength/structure/Tiaohou conflicts explicit.
4. Prevent ten-god labels from selecting a life scene.
5. Run all Bazi adapter and inference tests.

### Task 6: Bind Public Rendering To Frozen Verdicts

**Files:**
- Create: `scripts/public_answer_contract.py`
- Create: `scripts/test_public_answer_contract.py`
- Modify: `scripts/reading_public_brief.py`
- Modify: `scripts/fortune_public_brief.py`
- Modify: `scripts/liuren_public_brief.py`

**Steps:**
1. Test that an answer contradicting the frozen polarity fails structurally.
2. Test that `underdetermined` cannot become a directional claim in prose.
3. Test chart-before-judgment and follow-up reuse without fixed wording.
4. Add one immutable public-answer manifest bound to the inference digest.
5. Keep the language model responsible only for natural explanation.

### Task 7: Replace The Legacy Gate Incrementally

**Files:**
- Create: `scripts/structural_gate.py`
- Create: `scripts/test_structural_gate.py`
- Modify: `scripts/gate_check.py`

**Steps:**
1. Add structural checks for artifact schemas, digests, verdict scope, and source IDs.
2. Route migrated v7 artifacts through the structural gate first.
3. Retain only legacy fact-claim and private-data leak checks during migration.
4. Add a line-count and responsibility test preventing new inference policy from entering `gate_check.py`.
5. Delete obsolete regex checks only after equivalent structural tests are green.

### Task 8: Build A Provenance-Rich Known-Answer Corpus

**Files:**
- Create: `references/regression/cases/catalog.json`
- Create: `references/regression/cases/README.schema.md`
- Create: `scripts/case_import.py`
- Create: `scripts/test_case_import.py`

**Steps:**
1. Search public contest questions, worked examples, and user-posted cases with explicit outcomes.
2. Store a paraphrased prompt, source URL, capture date, publication date, answer provenance, ambiguity, and leakage risks.
3. Keep copyrighted source text to short anchors; do not copy full posts or books.
4. Reject cases whose outcome is unverifiable, subjective, or embedded in the prediction input.
5. Deduplicate by normalized chart/question/outcome fingerprints.

### Task 9: Champion/Challenger Evaluation

**Files:**
- Create: `references/regression/v7-champion-challenger.json`
- Create: `references/regression/v7-champion-challenger.md`

**Steps:**
1. Run the clean rollback, current v6, and v7 on identical redacted inputs.
2. Score chart correctness, direction, abstention, unsupported claims, calibration, relevance, tool calls, and context bytes separately.
3. Include adversarial outcome-disclosure and paraphrase variants.
4. Do not tune on held-out cases; split development and evaluation fixtures by source group.
5. Record every failure, not only favorable examples.

### Task 10: Migrate All Routes And Deploy

**Files:**
- Modify: `SKILL.md`
- Modify: `references/routing.md`
- Modify: `references/matrices/routing-matrix.md`
- Modify: Hermes wrappers and guards after source tests pass.

**Steps:**
1. Require each route to produce a v7 inference artifact or return `missing_fact_layer`/`underdetermined`.
2. Add independent cross-system artifacts and a conflict-only synthesizer.
3. Run the full source suite, Hermes suite, blind benchmark, and natural-language replay.
4. Pin `mingli-master` against autonomous skill maintenance during the evaluation window.
5. Sync source, Codex, default Hermes, and liujing Hermes only after requirement-by-requirement audit.
6. Restart both gateways and run live smoke tests without outcome leakage.

