# Cross-System Evidence Gates Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every calculation-sensitive Mingli route fail closed unless it has current validated facts, current required classical source reads, chart-first public copy, and a passing final gate.

**Architecture:** Add one deterministic source-plan/public-contract compiler shared by all systems, plus a structural adapter for complete user-provided charts where no calculator exists. Keep the existing Bazi, near-time fortune, and Da Liu Ren calculators as authorities. Extend the source skill gates and Hermes delivery guard so runtime evidence, not prompt wording, authorizes a reading.

**Tech Stack:** Python 3 standard library, existing `sxtwl`-backed adapters, standalone source-skill regression scripts, pytest for Hermes, Markdown/YAML reference packs, rsync deployment.

---

### Task 1: Reproduce Cross-System Guard Holes

**Files:**
- Modify: `~/.hermes/hermes-agent/tests/gateway/test_mingli_fact_guard.py`

**Step 1: Write failing parameterized tests**

Add tests proving that calculation-sensitive Ziwei, Liuyao, Meihua, Qimen, Taiyi, selection, Fengshui, physiognomy, and Luming/Bazi readings require buffered delivery and reject a generic tagged prediction with no fact evidence.

```python
@pytest.mark.parametrize("query", FORMAL_SYSTEM_QUERIES)
def test_formal_mingli_routes_are_buffered(query):
    assert requires_buffered_delivery(query, []) is True

@pytest.mark.parametrize("query,draft", UNSUPPORTED_DRAFTS)
def test_formal_mingli_routes_block_unsupported_predictions(query, draft):
    result = enforce_mingli_bazi_fact_gate(
        message_text=query,
        response=draft,
        history=[],
        agent_messages=[],
    )
    assert result.blocked is True
    assert result.reason == "missing_formal_mingli_fact_evidence"
```

Also add a source-history control such as `《滴天髓》主要讲什么` that must not be treated as a personal chart reading.

**Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 -m pytest tests/gateway/test_mingli_fact_guard.py -k "formal_mingli_routes" -q
```

Expected: unsupported routes are not buffered and drafts are not blocked.

**Step 3: Commit tests only**

```bash
git add tests/gateway/test_mingli_fact_guard.py
git commit -m "test: expose unsupported mingli delivery routes"
```

### Task 2: Compile Deterministic Source Plans

**Files:**
- Create: `scripts/reading_source_plan.py`
- Create: `scripts/test_reading_source_plan.py`
- Modify: `references/routing.md`
- Modify: `references/system-cards.md`

**Step 1: Write failing source-plan tests**

Cover at least:

- generic Bazi -> `sanming-tonghui` + `yuanhai-ziping` plus pattern/strength/Tiaohou layers;
- Bazi timing -> add timing rule layers;
- near-time fortune -> `yuanhai-ziping`, `ditiansui-chanwei`, `qiongtong-baojian`;
- Liuyao vs Meihua -> different pack sets;
- Ziwei, Xingming, Qimen, Taiyi, selection, Yangzhai, Yinzhai, Xuankong, physiognomy, and Luming -> system-appropriate packs;
- every required pack contributes an existing nonempty `rules.md` and `quote-index.md`;
- blocked packs are never selected.

Expected schema:

```json
{
  "schema_version": "mingli-reading-source-plan-v1",
  "system": "bazi",
  "question_type": "timing",
  "required_rule_files": [],
  "required_quote_indexes": [],
  "required_packs": [],
  "comparison_packs": [],
  "decision_layers": [],
  "chart_contract": {"label": "四柱", "required_fields": []},
  "source_caveats": []
}
```

**Step 2: Run and verify RED**

```bash
python3 scripts/test_reading_source_plan.py
```

Expected: import or file-not-found failure.

**Step 3: Implement the minimal compiler**

Use explicit data tables backed by the existing routing/system-card decisions. Validate every emitted path under `references/books`; do not infer blocked status from prose and do not search the whole corpus at answer time.

CLI:

```bash
python3 scripts/reading_source_plan.py \
  --system bazi \
  --query-file /tmp/mingli-query.txt \
  --facts-file /tmp/mingli-facts.json \
  --output /tmp/mingli-source-plan.json
```

**Step 4: Run tests and commit**

```bash
python3 scripts/test_reading_source_plan.py
python3 scripts/test_skill_metadata.py
git add scripts/reading_source_plan.py scripts/test_reading_source_plan.py references/routing.md references/system-cards.md
git commit -m "feat: compile system-specific classical source plans"
```

### Task 3: Validate Complete User-Provided Charts

**Files:**
- Create: `scripts/structured_chart_adapter.py`
- Create: `scripts/test_structured_chart_adapter.py`
- Modify: `scripts/adapter_validate.py`
- Modify: `references/tool-adapters.md`

**Step 1: Write failing tests**

Test `ziwei`, `xingming`, `divination/liuyao`, `divination/meihua`, `qimen`, `taiyi`, `selection`, `fengshui`, and `physiognomy` profiles.

Each accepted payload must contain:

```json
{
  "fact_layer_status": "validated_user_provided_chart",
  "fact_layer_scope": "supplied_facts_only",
  "system": "qimen",
  "adapter": {
    "name": "mingli-master.structured_chart_adapter",
    "rule_profile": "user-provided-no-recalculation"
  },
  "input": {"provenance": "user_provided"},
  "output": {}
}
```

Reject missing required groups, copied `Fact tool` labels, unsupported systems, and claims that the calendar or plate was recalculated.

**Step 2: Run and verify RED**

```bash
python3 scripts/test_structured_chart_adapter.py
```

**Step 3: Implement the adapter and validator profiles**

The script normalizes and validates supplied JSON only. It does not calculate charts. Preserve raw provenance and emit a visible `未复算` boundary for the public contract.

**Step 4: Run tests and commit**

```bash
python3 scripts/test_structured_chart_adapter.py
python3 scripts/test_bazi_fact_adapter.py
python3 scripts/test_liuren_fact_adapter.py
git add scripts/structured_chart_adapter.py scripts/test_structured_chart_adapter.py scripts/adapter_validate.py references/tool-adapters.md
git commit -m "feat: validate complete user-provided mingli charts"
```

### Task 4: Build a Shared Chart-First Public Contract

**Files:**
- Create: `scripts/reading_public_brief.py`
- Create: `scripts/test_reading_public_brief.py`
- Modify: `scripts/fortune_public_brief.py`
- Modify: `scripts/test_fortune_public_brief.py`

**Step 1: Write failing brief tests**

Require the brief to include validated fact status, source-plan digest, required current source paths, compact chart fields, answer dimensions extracted from the query, unsupported claims, and the rule that the first judgment follows the compact chart.

For daily fortune, require a `classical_basis` with current Bazi rule and quote files plus a public time-basis line containing natal baseline, active luck, and target day.

**Step 2: Run and verify RED**

```bash
python3 scripts/test_reading_public_brief.py
python3 scripts/test_fortune_public_brief.py
```

**Step 3: Implement minimal deterministic briefs**

Do not generate public sentences. The brief is a semantic contract and source manifest only.

**Step 4: Run tests and commit**

```bash
python3 scripts/test_reading_public_brief.py
python3 scripts/test_fortune_public_brief.py
git add scripts/reading_public_brief.py scripts/test_reading_public_brief.py scripts/fortune_public_brief.py scripts/test_fortune_public_brief.py
git commit -m "feat: add shared chart-first reading contracts"
```

### Task 5: Add the General Public Reading Gate

**Files:**
- Modify: `scripts/gate_check.py`
- Modify: `scripts/test_gate_check.py`
- Modify: `scripts/test_natural_language_regression.py`
- Modify: `references/regression/natural-language-regression.yaml`

**Step 1: Write failing public-gate cases**

Add `reading-public` mode tests for:

- judgment before chart;
- missing or altered chart facts;
- missing requested answer dimension;
- named books without required source-plan evidence;
- empty phrases and advice-only copy;
- audit scaffolding;
- invented timing or unsupported precision;
- complete natural Bazi and validated-user-chart answers that pass;
- missing-fact stop that contains no disguised prediction.

**Step 2: Run and verify RED**

```bash
python3 scripts/test_gate_check.py
python3 scripts/test_natural_language_regression.py
```

**Step 3: Implement `reading-public`**

CLI:

```bash
python3 scripts/gate_check.py \
  --mode reading-public \
  --file /tmp/mingli-public.txt \
  --query-file /tmp/mingli-query.txt \
  --facts-file /tmp/mingli-facts.json \
  --source-plan-file /tmp/mingli-source-plan.json
```

Validate values against structured facts/source plan rather than relying only on keywords. Keep existing `fortune-public` and `liuren-public` behavior intact.

**Step 4: Run tests and commit**

```bash
python3 scripts/test_gate_check.py
python3 scripts/test_natural_language_regression.py
git add scripts/gate_check.py scripts/test_gate_check.py scripts/test_natural_language_regression.py references/regression/natural-language-regression.yaml
git commit -m "feat: gate chart-first public readings across systems"
```

### Task 6: Make Bazi and Daily Fortune Source-Bound

**Files:**
- Modify: `SKILL.md`
- Modify: `references/bazi-input-and-image-gate.md`
- Modify: `references/fortune-cron-reminders.md`
- Modify: `references/bazi-monthly-fortune-chat.md`
- Modify: `references/mingli-anti-empty-output.md`
- Modify: `scripts/test_skill_metadata.py`
- Modify: `scripts/test_natural_language_regression.py`

**Step 1: Add failing contract tests**

Require formal Bazi and daily fortune instructions to run the source-plan/brief flow, read the current required rules and quote indexes, expose the compact chart/time basis before judgment, and gate the exact final copy. Remove any instruction that lets daily fortune skip classical source selection.

**Step 2: Run and verify RED**

```bash
python3 scripts/test_skill_metadata.py
python3 scripts/test_natural_language_regression.py
```

**Step 3: Update the skill and references**

Keep `SKILL.md` as routing logic and put detailed contracts in references. Do not embed fixed output sentences.

**Step 4: Run tests and commit**

```bash
python3 scripts/test_skill_metadata.py
python3 scripts/test_natural_language_regression.py
git add SKILL.md references scripts/test_skill_metadata.py scripts/test_natural_language_regression.py
git commit -m "fix: bind bazi and daily fortune to classical sources"
```

### Task 7: Enforce the Contract in Hermes

**Files:**
- Modify: `~/.hermes/hermes-agent/gateway/mingli_fact_guard.py`
- Modify: `~/.hermes/hermes-agent/tests/gateway/test_mingli_fact_guard.py`

**Step 1: Extend failing tests**

Cover:

- all formal routes buffer;
- no facts -> system-specific missing-fact response;
- valid facts but no source plan -> block;
- source plan but stale/index-only/partial reads -> block;
- valid Bazi or daily facts but no current classical reads -> block;
- public gate before final edit or failed gate -> block;
- full current evidence -> preserve natural answer;
- source-history questions remain unblocked;
- runtime skill mutation remains blocked.

**Step 2: Run and verify RED**

```bash
python3 -m pytest tests/gateway/test_mingli_fact_guard.py -q
```

**Step 3: Implement generalized evidence extraction**

Track the last current fact execution, source-plan execution, successful required file reads, exact public-copy write, and successful final gate. Keep the existing specialized Da Liu Ren checks and reuse their ordering semantics.

**Step 4: Run focused and API regressions**

```bash
python3 -m pytest tests/gateway/test_mingli_fact_guard.py -q
python3 -m pytest tests/test_api_server.py tests/test_api_server_session.py -q
```

**Step 5: Commit**

```bash
git add gateway/mingli_fact_guard.py tests/gateway/test_mingli_fact_guard.py
git commit -m "fix: enforce evidence-bound mingli delivery across systems"
```

### Task 8: Full Validation and Deployment

**Files:**
- Modify: `references/regression/natural-language-regression-report.md`

**Step 1: Run the complete source-skill suite**

```bash
python3 scripts/test_bazi_fact_adapter.py
python3 scripts/test_near_time_fortune_adapter.py
python3 scripts/test_fortune_public_brief.py
python3 scripts/test_liuren_fact_adapter.py
python3 scripts/test_liuren_public_brief.py
python3 scripts/test_reading_source_plan.py
python3 scripts/test_structured_chart_adapter.py
python3 scripts/test_reading_public_brief.py
python3 scripts/test_gate_check.py
python3 scripts/test_natural_language_regression.py
python3 scripts/test_skill_metadata.py
python3 scripts/test_optimization_tools.py
python3 scripts/audit_shensha_traces.py --json
```

Expected: all pass with no lint errors.

**Step 2: Run Hermes regressions**

```bash
python3 -m pytest tests/gateway/test_mingli_fact_guard.py -q
python3 -m pytest tests/test_api_server.py tests/test_api_server_session.py -q
```

Expected: all pass; unrelated existing warnings only.

**Step 3: Update the regression report and commit**

Record exact counts, authorization levels, remaining uninstalled deterministic adapters, and live replay results.

```bash
git add references/regression/natural-language-regression-report.md
git commit -m "docs: record cross-system evidence-gate validation"
```

**Step 4: Synchronize runtime copies**

Sync the source-of-truth skill to:

- `~/.codex/skills/mingli-master/`
- `~/.hermes/skills/research/mingli-master/`
- `~/.hermes/profiles/liujing/skills/research/mingli-master/`

Use `rsync -a --delete --exclude .git`, then verify all three with `rsync -ani` dry runs.

**Step 5: Restart gateways and run live API replays**

Replay:

1. formal Bazi from supplied pillars;
2. broad tomorrow fortune;
3. Da Liu Ren concrete question;
4. validated user-provided Meihua or Liuyao chart;
5. unsupported Qimen request with no plate.

Expected: the first four show the appropriate compact chart before judgment and use current classical sources; the unsupported route asks for the missing deterministic plate and contains no prediction.

**Step 6: Final integrity check**

- source repository clean;
- Hermes repository contains only pre-existing unrelated user modifications;
- ports 8642, 8645, and 8646 listen;
- no GitHub push unless explicitly requested.
