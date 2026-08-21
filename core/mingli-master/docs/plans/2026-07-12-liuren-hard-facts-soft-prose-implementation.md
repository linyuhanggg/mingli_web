# Da Liu Ren Hard Facts, Soft Prose Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the manual, format-heavy Da Liu Ren chat chain with one hash-bound evidence pipeline and a semantic public gate that preserves fact accuracy while allowing compact natural prose.

**Architecture:** A new Hermes wrapper compiles deterministic Liuren facts, a writing brief, a current source plan, and a bounded evidence bundle into private artifacts and returns a compact manifest. The Hermes gateway validates that manifest and the final hash-bound gate copy. The public gate validates every stated chart fact but requires only a compact chart anchor and a real answer, not a fixed report template.

**Tech Stack:** Python 3, `unittest`, `pytest`, JSON manifests, SHA-256 runtime identity, SQLite-backed Hermes traces.

---

### Task 1: Pin soft-prose gate behavior

**Files:**
- Modify: `scripts/test_gate_check.py`
- Modify: `scripts/test_liuren_public_brief.py`

**Step 1:** Add failing tests showing a compact chart with day/hour, `未将`, lesson method, three transmission branches, and xunkong passes without four lessons, relatives, generals, source names, or action advice.

**Step 2:** Add negative controls for a wrong first lesson when it is stated, wrong month general, wrong transmission branch, wrong xunkong, and unsupported guaranteed timing.

**Step 3:** Run:

```bash
PYTHONPATH=scripts python3 -m unittest \
  scripts.test_gate_check.GateCheckTests.test_liuren_soft_prose_compact_chart_passes \
  scripts.test_gate_check.GateCheckTests.test_liuren_soft_prose_stated_wrong_fact_fails
```

Expected: new positive test fails before implementation; negative controls remain red/green as specified.

### Task 2: Relax only the public presentation contract

**Files:**
- Modify: `scripts/gate_check.py`
- Modify: `scripts/liuren_public_brief.py`
- Modify: `references/liuren-casting-gate.md`

**Step 1:** Change the brief contract so `four_lessons`, transmission relatives/generals, source names, condition, and action are optional public expansions.

**Step 2:** Replace exact verdict vocabulary with semantic outcome detection covering timing candidates and ordinary conclusion phrases.

**Step 3:** Accept both `月将为未` and `未将`; parse compact transmission branches while still validating any detailed fields that appear.

**Step 4:** Run focused Liuren gate and brief tests. Expected: compact prose passes; wrong facts still fail.

### Task 3: Build the Liuren pipeline manifest

**Files:**
- Create: `~/.hermes/scripts/liuren_calc.py`
- Modify: `scripts/test_qoder_audit_findings.py`
- Modify: `scripts/test_qoder_final_acceptance_findings.py`

**Step 1:** Add a failing wrapper test for `mingli-liuren-pipeline-v1`, private artifact hashes, runtime identity, exact query binding, and a manifest below 12,000 bytes.

**Step 2:** Implement adapter, validator, brief, source-plan, and evidence compilation in the wrapper.

**Step 3:** Store `query.txt`, `facts.json`, `brief.json`, `source-plan.json`, `evidence.json`, and `public.txt` in a private unique run directory.

**Step 4:** Return compact chart facts, process/question signals, bounded classical evidence, a delivery contract, and the exact gate command.

### Task 4: Validate the pipeline at the Hermes boundary

**Files:**
- Modify: `~/.hermes/hermes-agent/gateway/mingli_fact_guard.py`
- Modify: `~/.hermes/hermes-agent/tests/gateway/test_mingli_fact_guard.py`

**Step 1:** Add failing tests for valid manifest delivery, tampered artifact/hash rejection, wrong query/date/location rejection, stale runtime identity rejection, missing evidence rejection, and missing/failing final gate rejection.

**Step 2:** Implement private-path, artifact, runtime, brief, plan, evidence, and final-gate validation.

**Step 3:** Keep the legacy adapter/source-read path as a compatibility fallback.

**Step 4:** Run the entire Mingli gateway test file. Expected: all tests pass.

### Task 5: Route Hermes through the compact pipeline

**Files:**
- Modify: `SKILL.md`
- Modify: `references/liuren-casting-gate.md`
- Modify: `scripts/test_skill_metadata.py`

**Step 1:** Add a failing metadata test requiring the one-command Liuren pipeline and forbidding six full-file reads in ordinary chat.

**Step 2:** Update the Formal lane to run the wrapper once, draft from `synthesis_context`, write once, gate once, and deliver only `public_copy`.

**Step 3:** Keep the router below 12,000 bytes.

### Task 6: Deploy and verify

**Files:**
- Sync source skill to Codex, Hermes main, and Hermes liujing copies.

**Step 1:** Run both source Python test environments and the full Mingli gateway test file.

**Step 2:** Restart both gateway launch agents.

**Step 3:** Replay the exact flow:

```text
算下今天运势
那你算下我下次收到工资是啥时候
上海
```

**Step 4:** Verify compact chart-first output, gate/public-copy equality, no invented event, no fixed report headings, no more than 4 tool calls after location, and no more than 12,000 added manifest bytes.

**Step 5:** Record automated and explicit human review in a replay artifact and update the acceptance report.
