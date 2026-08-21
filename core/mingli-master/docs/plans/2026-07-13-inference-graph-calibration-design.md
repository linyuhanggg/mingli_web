# Mingli v7 Inference Graph And Calibration Design

## Problem

The current runtime has a deterministic fact layer and a bounded classical
evidence layer, but it still lets the language model choose the decisive rule,
its weight, and the final polarity. The public gate then validates wording and
fact mentions rather than the inference itself. This permits two opposite
answers to pass for the same chart.

The production stock replay is the minimal example. A Da Liu Ren chart was
first read as `profit`; after the user disclosed `loss`, the same chart was read
as `loss`. The chart did not change. The conclusion changed because outcome
information entered free-form synthesis.

## Goals

1. Make chart calculation, rule activation, conflict resolution, verdict, and
   language synthesis separate artifacts.
2. Freeze every scorable prediction before an outcome is available.
3. Require every conclusion to cite executable rule activations and current
   fact paths.
4. Prefer an explicit `underdetermined` result to unsupported specificity.
5. Measure chart correctness, directional performance, calibration,
   abstention, unsupported claims, and conversational quality separately.
6. Preserve complete local classical reference packs as provenance and
   explanation sources without treating text retrieval as empirical proof.

## Non-Goals

- Claiming that traditional divination is scientifically validated.
- Importing hard-coded life stories or extreme assertions from third-party
  repositories.
- Making all systems executable in one migration.
- Using a second system to conceal an invalid or weak first-system result.

## Chosen Architecture

### 1. Question Contract

Normalize the exact user question into a machine-readable contract:

- system and route;
- subject and relationship to querent;
- requested dimensions such as direction, timing, amount, or cause;
- domain selected by the user;
- time window;
- facts that may be used;
- outcome-like text that must be quarantined during blind prediction.

Classification is deterministic and covered by fixtures. Domain recognition
must include natural variants such as stock profit/loss, not only `money` or
`payment` keywords.

### 2. Fact Artifact

Adapters remain the only authority for calendars and charts. Each artifact has
a canonical digest and records the calculator version, time policy, input, and
validation status. OCR is still transcription only.

### 3. Rule Activation Graph

Each system compiles an inference graph from facts and eligible classical
rules. A node contains:

- `activation_id` and `rule_id`;
- exact fact paths and values that activated it;
- source pack and quote/rule anchors;
- question dimensions to which it applies;
- polarity (`support`, `oppose`, `neutral`, or `uncertain`);
- weight class and dependency group;
- exceptions, stop conditions, and conflicts.

Repeated statements from the same lineage or the same underlying fact remain
one dependency group and cannot be counted as independent votes.

### 4. Deterministic Adjudication

An adjudicator consumes only the question contract, fact digest, and activation
graph. It emits:

- verdict (`support`, `oppose`, `mixed`, or `underdetermined`);
- confidence bucket derived from margin and evidence quality;
- decisive activation IDs;
- counter-evidence IDs;
- unresolved conditions;
- allowed public claim scope;
- a digest binding all inputs.

The language model cannot change verdict or confidence. If the applicable
classical rules do not distinguish the requested alternatives, the result is
`underdetermined`; the model may explain why but may not pick a side.

### 5. Natural Language Rendering

The renderer receives a compact public chart, the frozen adjudication, and
short source anchors. It remains free to write warm, natural Chinese. The only
hard constraints are:

- display the chart or calculated basis before judgment;
- answer the exact requested dimension;
- preserve the frozen verdict and uncertainty;
- do not add an unsupported event, amount, location, motive, or exact time;
- retain conversation state for follow-up questions on the same chart.

There are no mandatory sentence templates, stock headings, or action lists.

### 6. Structural Verification

The primary gate becomes schema- and digest-based:

1. valid chart artifact;
2. valid inference artifact whose fact and evidence digests match;
3. public answer bound to the frozen verdict and allowed claim scope.

The legacy regex gate remains only as a temporary compatibility and leak check
while routes migrate. It must not select content or force repeated rewrites.

### 7. Blind Case Evaluation

Every benchmark case stores input and outcome in separate objects. The runner:

1. loads only the redacted input;
2. calculates facts and inference;
3. writes an immutable prediction with its SHA-256 digest;
4. reveals the outcome to a separate scorer;
5. records hit, partial, miss, abstention, Brier score where applicable, and
   provenance quality.

Known-answer web cases are allowed only when the prediction process cannot see
the answer. Case records preserve source URL, capture date, outcome evidence,
ambiguity, selection method, and possible publication bias.

## System Migration Tiers

### Tier A: executable inference

- Bazi natal and timing where the deterministic adapter has complete outputs.
- Near-time Bazi fortune.
- Da Liu Ren.

These receive question contracts, activation graphs, frozen adjudication, and
blind benchmarks first.

### Tier B: structured-chart inference

- Ziwei, Liuyao, Meihua, Qimen, Taiyi, Xingming, selection, Fengshui, and
  physiognomy when a deterministic adapter or complete validated chart exists.

They use the same artifact contracts but may initially return
`missing_fact_layer` or `underdetermined` rather than hand-calculate.

### Tier C: research only

Incomplete, OCR-only, blocked, or unverified source material remains available
for textual research and cannot activate prediction rules.

## Cross-System Policy

Cross-system corroboration is optional and question-driven. Each system must
produce an independent valid fact and inference artifact. The synthesizer
reports agreement, conflict, and scope differences; it never averages scores or
lets one system repair another system's invalid calculation.

## Accuracy Metrics

Report separate metrics, never one unqualified accuracy percentage:

- calendar/chart exact match;
- requested-dimension directional accuracy;
- coverage and abstention rate;
- unsupported-claim rate;
- confidence calibration and Brier score;
- outcome-source quality;
- follow-up state retention;
- language relevance and warmth, judged independently of correctness.

Minimum stages are 20 exploratory claims, 50-100 useful calibration claims, and
160+ claims before narrow subgroup comparisons. These thresholds do not make
the underlying practice scientifically valid; they only make this product's
behavior measurable.

## Release Policy

- Keep commit `5ed35b4` as the current clean rollback point and preserve the
  current uncommitted work.
- Build v7 artifacts alongside v6 before changing the default runtime.
- The stock contradiction must be a red-capable regression from the start.
- Deploy a route only after the new path wins or safely abstains on blind
  champion/challenger cases and stays within tool/context budgets.
- Pin the installed skill against autonomous optimization during evaluation.

