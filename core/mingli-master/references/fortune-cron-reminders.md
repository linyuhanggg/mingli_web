# Interactive Today/Tomorrow Fortune And Scheduled Reminders

Use this route for an interactive today/tomorrow fortune or a scheduled personal reminder. It is a full-birth Bazi transit reading, not a short-event oracle and not the monthly-fortune chat route.

Do not open this reference in ordinary Hermes chat. The main skill already contains the compact interactive command; this file documents the explicit fallback and scheduled-delivery chain.

## Required Contract

Accept only the current near-time payload:

- `schema_version: mingli-near-time-fortune-v2`
- `fact_layer_status: near_time_bazi_transit_facts`
- `contract_version: fortune-public-v6-mechanism-stack`
- adapter `mingli-master.near_time_fortune_adapter` version `2.1.0`
- rule profile `full-birth/transit-mechanism-stack-v4`
- complete `birth_fact_layer`, including natal pillars, day master, month command, hidden stems, ten gods, element inventory, seasonal/Tiaohou facts, and active luck
- target `calendar_normalization`, `transit_layers`, and `mechanism_stack`
- optional `hour_profiles`, which never require a phase narrative
- private analysis schema `mingli-fortune-analysis-bundle-v2`
- `public_claim_contract.user_selected_domains_only: true`

Reject legacy payloads. Do not translate old behavior lenses, domain hypotheses, or phase templates into v6.

## Execution Chain

For an ordinary Hermes `今天/明天` request, run exactly one calculation/source pipeline (substitute the real target and unmodified query):

```bash
~/.hermes/scripts/fortune_calc.py --target <today|tomorrow> --query '<exact user query>' --pipeline
```

The returned `mingli-fortune-pipeline-v2` manifest binds one runtime directory and the hashes of every core adapter, source, evidence, and gate file. It exposes only compact `synthesis_context`; full facts, source plan, and evidence remain in private hash-bound artifacts. Do not print or reread those full files into model context. A successful repair pipeline is not a finished answer: never answer directly from the manifest. Draft from the compact context, write the exact public copy to `delivery_contract.write_public_copy_to`, run its `gate_command`, and deliver only its hash-bound `public_copy`. On failure, rewrite the complete file from the findings and rerun the same gate, up to `maximum_wording_repairs`; keep this inside the current turn and never ask the user to trigger it. Do not add a Bazi input-status tag to a quick daily reading.

Use `--dialogue-state repair` after a complaint and `--dialogue-state probe-answer` after the user answers the one prior probe. Use `--window '<target window>'` instead of `--target` for an explicit time interval. Do not call `date`, `--help`, or this reference before the ordinary pipeline.

Outside Hermes, run the same stages explicitly:

```bash
python3 scripts/near_time_fortune_adapter.py <validated birth args> \
  --window '<target window>' --output /tmp/fortune-facts.json
python3 scripts/adapter_validate.py --system fortune --file /tmp/fortune-facts.json
python3 scripts/fortune_public_brief.py \
  --file /tmp/fortune-facts.json \
  --dialogue-state initial \
  --output /tmp/fortune-analysis.json
```

Do not draft public prose before this brief succeeds. The analysis bundle is private semantic context, never a writing template or public answer.

after the current fact calculation, create current classical evidence:

```bash
printf '%s\n' '<exact user query>' > /tmp/fortune-query.txt
python3 scripts/reading_source_plan.py \
  --system fortune \
  --query-file /tmp/fortune-query.txt \
  --facts-file /tmp/fortune-facts.json \
  --output /tmp/fortune-source-plan.json
python3 scripts/reading_evidence_bundle.py \
  --query-file /tmp/fortune-query.txt \
  --facts-file /tmp/fortune-facts.json \
  --source-plan-file /tmp/fortune-source-plan.json \
  --output /tmp/fortune-evidence.json
```

The evidence bundle must cover the plan's `required_rule_files` and `required_quote_indexes` with current hashes. Hard applicability is evaluated before ranking. Do not inject whole books or choose a familiar quotation by hand.

Draft once, save the exact user-visible copy, and run:

```bash
python3 scripts/gate_check.py \
  --file /tmp/fortune-public.txt \
  --mode fortune-public \
  --query-file /tmp/fortune-query.txt \
  --facts-file /tmp/fortune-facts.json \
  --source-plan-file /tmp/fortune-source-plan.json \
  --evidence-file /tmp/fortune-evidence.json
```

Do not inspect `gate_check.py` to reverse-engineer wording. Use at most two gate attempts total: the first draft and one evidence-preserving repair. Never improvise an ungated third answer.

## Reading The V6 Facts

1. Confirm the requested `今天/明天/今晚` matches `target_date`, `target_window`, timezone, and location.
2. Read `public_time_basis`: natal pillars, active major luck, target date, and target-day ganzhi.
3. Read the natal baseline before transit labels: month command, season, element inventory, Tiaohou, and unresolved boundaries.
4. Read major-luck, year, month, and day layers together. Identify the strongest mechanism and its dependencies.
5. Treat several relations from one transit branch as one dependent source family, not several confirmations.
6. Use queried-hour facts only when the user asks about a time of day or when they materially change the answer. No morning/afternoon/evening paragraph is mandatory.
7. Resolve classical evidence only from applicable records. A rule for another day master, season, timing layer, or topic cannot support the answer regardless of text similarity.
8. State only a domain selected by the user or supported by current event context and applicable evidence.

The analysis must not convert a ten god or branch relation into a stock scene. A 财 signal is not automatically an incoming payment. 印 is not automatically a message or document. 冲 is not automatically an argument, changed appointment, vehicle problem, or house repair. A complete 三合/三会 branch set is not proof that transformation has succeeded; respect `transformation_status`.

## Public Answer

The exact public copy begins with `【玄枢｜MINGLI】`, followed by the manifest's `public_time_basis_line` verbatim before the first judgment. Then give a direct answer and explain at least one decisive current mechanism in ordinary Chinese. State the exact Chinese relation from the primary mechanism; do not shorten `六破` to `破` or otherwise weaken a calculated term.

Internal field names, mechanism IDs, contract names, and category labels are private. Translate their factual content into ordinary Chinese; never copy them into the public answer.

The sentence order and wording are not prescribed. Do not prescribe a reusable sentence skeleton, fixed headings, score, three-part rhythm, mandatory advice, mandatory feeling sentence, or mandatory day phases. The model derives its language from this calculation and the user's actual question.

For broad fortune questions:

- Answer the whole requested period, but only at the resolution the facts support.
- Do not predict money, work, relationships, health, travel, messages, or another life domain merely to sound useful.
- Compare meaning, not surface words, when checking repetition. Variety never authorizes a random new topic.
- Warmth is grounded attention: explain what the supported mechanism changes for this person without inventing an event or hiding uncertainty behind service language.
- Give advice only when it genuinely follows from the judgment; advice is never a substitute for calculation.
- Give timing only when target layers or queried-hour facts distinguish it. Never invent exact clock precision.
- answer first, then optionally ask one open question only when its answer will materially narrow the next reading.

Do not expose tools, JSON, pack paths, hashes, gate output, or a report frame in ordinary chat. Mention a classical source naturally only when it helps explain the judgment and the current evidence bundle contains the actual rule used.

## Dialogue States

### Initial

Calculate the target period, show its compact time basis, give the judgment, and optionally ask one high-information open question. A broad question does not require a domain menu.

### Repair

When the user says `太泛`, `套话`, `官话`, `答非所问`, `牛头不对马嘴`, `没算出来`, or similar, restore the original query with the private marker `MINGLI_FORTUNE_REPAIR_V1`, recalculate the same target, and use `--dialogue-state repair`.

Do not spend the turn explaining the rules. For a broad-day repair, "concrete" means a supported direction, not a fabricated event. Correct the strongest judgment from the current mechanisms. Ask exactly one open question only if a concrete event is needed to improve resolution. Do not switch methods merely to produce a different answer.

### Probe Answer

Use `--dialogue-state probe-answer`, preserve the validated target, and apply the reply only as event context. The user's answer is event context, not proof of the chart. Continue from the mechanism that the new context makes relevant; do not replay a generic whole-day reading.

If the user now asks whether one concrete event will succeed, switch to the correct formal event route when daily Bazi resolution is insufficient.

## Scheduled Delivery

A scheduled reminder uses the same private chain immediately before delivery. Recompute the current target; do not reuse yesterday's facts, evidence, or public copy. The scheduled text may be shorter, but it still requires the visible tag, correct time basis, a supported judgment, the current public gate, and hash-bound delivery.

Deliver only gate output fields `gate_contract`, `public_copy_sha256`, and `public_copy` as authorization metadata; the user receives `public_copy` verbatim. A post-gate edit invalidates delivery.

## Budget

- Maximum six skill-specific tool calls in the quick lane when the Hermes wrapper combines calculation, validation, and analysis compilation, including one evidence-preserving rewrite and re-gate.
- Maximum 8,000 added context tokens.
- No whole book, repeated skill load, repeated full JSON dump, subagent, or historical-reply corpus.
- If the budget cannot cover a valid fact/source/public chain, stop with the precise unresolved layer instead of sending filler.
