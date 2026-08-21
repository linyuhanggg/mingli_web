# Model-independent replay evaluation

This protocol measures how a host model turns a production `ReadingBrief`
into a useful answer. It is development-only: the runner never calls or
selects a model, and no score can block `Complete`, `Accepted`, or delivery.

## Frozen inputs

There are two separate suites:

1. `tests/replay/mingli-routing-cases.jsonl` covers routing and conversation
   control.
2. `tests/replay/mingli-answer-cases.jsonl` covers answer drafting from the
   public production boundary.

Answer briefs are not hand-written approximations. Regenerate or verify all
8 behavior-orthogonal cases by executing the real portable interface with
synthetic inputs and an isolated temporary store:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts "$MINGLI_PYTHON" -B \
  scripts/export_v51_answer_cases.py --check
```

After the check, materialize the exact per-case generation inputs and frozen
Skill copies. Supply a previously materialized baseline Skill file; the tool
does not choose commits or models:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -B \
  scripts/export_v51_answer_cases.py \
  --materialize-packets /path/to/packet-set \
  --skill-snapshot run-a=/path/to/baseline.SKILL.md \
  --skill-snapshot run-b=SKILL.md
```

`generation-manifest.json` records case order, canonical packet hashes, Skill
hashes, and the procedural-isolation boundary. It deliberately records no
model choice or fabricated telemetry; the external run record must separately
state the actual host profile and retry policy available to that host.

The exporter runs each selected case through
`ReadingInterface.execute(Prepare)`, including one required comparison, a real
`Prepare -> Complete -> Prepare` continuation, and a real correction. The
cases cover broad-plus-ambient, one-sentence, plain judgment, cross-scope,
zero-evidence, continuation, correction, and horizon-boundary behavior.
Provider completeness belongs to the existing Provider contract suites, not
this answer-delivery suite. The exporter freezes `Prepared.brief.to_dict()`
byte-for-byte plus its canonical `brief_sha256`. A fixture contains no state
token, reading id, private staged artifact, or private counter-evidence.

That deletion is intentional. Answer replay starts after `Prepared`; copying
private digests into a prediction did not test provider invariance and let
hand-made artifacts masquerade as production data. Provider calculations,
storage, and state invariants remain covered by their own contract tests.

The synthetic briefs may contain synthetic birth/event inputs and synthetic
asset metadata because production publishes input facts. They contain no real
user record, name, local path, credential, image bytes, or production token.

`limit.source_gap` is public only when `brief.evidence` is empty. An internal
`no_applicable_counter_evidence` audit record is not presented as “no citable
source” beside real citations.

## External row formats

Routing prediction:

```json
{"case_id":"route-bazi-natal","prediction":{"invoke_skill":true,"action":"new","system":"bazi","calculation_object":"natal","dimensions":["career"]}}
```

Answer prediction:

```json
{"case_id":"answer-bazi-career","brief_sha256":"...","prediction":{"main_answer":"...","claim_traces":[{"fact_refs":["brief fact ref"],"evidence_refs":["brief evidence ref"]}]}}
```

Every substantive answer claim needs a trace. A trace may cite only public
refs in that case's `brief`; a private/counter-evidence ref is a violation.
The scorer rejects a stale `brief_sha256` and rejects the obsolete
`artifact_identity` field.

Usage is optional because some hosts do not expose per-call telemetry. If it
is available, add the complete object below; partial, negative, non-finite,
or fabricated values are invalid. Missing usage is reported honestly as less
than full coverage with `null` means, not converted to zero.

```json
{"usage":{"input_tokens":500,"output_tokens":300,"latency_ms":1800,"reported_cost":0.01}}
```

Review row, stored in a separate file after predictions are frozen:

```json
{"case_id":"answer-bazi-career","prediction_sha256":"...","reviewer":{"reviewer_id":"reviewer-anonymous-1","reviewer_kind":"independent_agent","independent":true,"blinded_run_label":"run-a"},"direct_answer":true,"evidence_relevant":true,"naturalness":4,"main_point_clear":true,"plain_language":4,"useful_specificity":4,"certainty_calibrated":true,"ambient_context_clean":true,"template_smell":false,"main_answer_claims_complete":true,"claim_reviews":[{"claim_index":0,"claim_text":"...","trace_indexes":[0],"unsupported":false}]}
```

`reviewer_kind` is explicitly `human` or `independent_agent`; the report
counts both and never calls an agent review human. `independent=true` and the
reviewer id are procedural attestations, not authenticated identities.

## Three-packet blind protocol

1. **Generation packet:** canonical JSON for one `brief` plus the complete
   `SKILL.md` from that arm. The drafting side returns only `main_answer` and
   `claim_traces`.
2. **Ambient injection:** for an `ambient_context_noise` case, inject each
   listed string as an earlier ordinary user message, in order, outside the
   brief. Both arms get identical messages and they are not labeled as noise.
3. **Review packet:** after predictions are immutable, give the reviewer the
   brief, prediction, ambient messages (if any), and `review_rubric`.

Never give the drafting side `review_rubric`, `coverage_tags`, labeled
`ambient_context`, other cases, thresholds, or arm identity. The reviewer
must not see the Skill version or the arm mapping.

Do not point the drafting side at the full answer-case JSONL and merely tell
it to ignore private fields. Before generation, materialize one immutable
packet per case whose only keys are `case_id`, `brief_sha256`, and `brief`;
give the drafting task only that packet path and one immutable Skill snapshot
as named inputs, and forbid other reads. A task directly pointed at a file
containing rubric or tags is invalid even if the prompt says not to read those
fields. Freeze and hash both Skill snapshots before the first invocation;
never reread a mutable worktree Skill between cases. If the evaluation host
cannot enforce an OS-level filesystem sandbox, record this as procedural
isolation rather than claiming cryptographic input isolation.

Write predictions under neutral stems such as `run-a.jsonl` and `run-b.jsonl`.
`prediction_sha256` is the canonical SHA-256 of the parsed prediction row.
Every review's `reviewer.blinded_run_label` must equal its prediction file
stem; the review filename itself is unrestricted.

## Baseline versus candidate

Both arms use the same exported briefs, host settings, retry policy, and
review rubric. Only drafting instructions differ: the baseline uses
`SKILL.md` from `8e4fa505`; the candidate uses the current `SKILL.md`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -B \
  scripts/run_model_replay.py \
  --kind answer \
  --cases tests/replay/mingli-answer-cases.jsonl \
  --predictions /path/to/run-a.jsonl /path/to/run-b.jsonl \
  --reviews /path/to/review-a.jsonl /path/to/review-b.jsonl
```

Reveal the arm mapping only after both review manifests are frozen and the
score command succeeds.

## Review fields and metrics

The independent reviewer enumerates every substantive claim in
`main_answer`. `trace_indexes` may be empty so an untraced claim remains
measurable. Missing fields, stale hashes, incomplete enumeration, invalid
types, or scores outside 1–5 fail closed as evaluation-protocol errors.

`unsupported` does not mean that the answer must repeat the brief verbatim.
A bounded semantic translation is supported when the cited public facts or
evidence reasonably ground it, the claim stays inside an admitted claim
scope, and its certainty respects the published ceiling. Mark it unsupported
only when no reasonable public grounding exists, it contradicts the brief,
or it adds an unlicensed domain, specific event, date, amount, or guarantee.
Review meaning clusters rather than splitting one judgment into every clause;
this keeps the metric about support, not punctuation.

- `direct_answer`, `evidence_relevant`, and `naturalness` retain their prior
  meanings.
- `main_point_clear`: an ordinary reader can state the core judgment after
  one reading.
- `plain_language` (1–5): specialist material is translated, not replaced by
  equally opaque synonyms.
- `useful_specificity` (1–5): the answer reaches a real behavior, situation,
  or choice without inventing an event.
- `certainty_calibrated`: directness obeys the public claim scope and ceiling.
- `ambient_context_clean`: nothing appears solely because it was in ambient
  host memory.
- `template_smell`: the answer reads like a canned report or persona imitation.

Hard release evidence requires: `brief_invariance_rate=1`,
`reference_violation_rate=0`, `unsupported_claim_rate=0`,
`untraced_claim_rate=0`, `evidence_relevance_rate=1`,
`direct_answer_rate=1`, and ambient contamination `=0`. Expression targets
are `main_point_clear_rate>=0.90`, `plain_language_mean>=4.0`,
`useful_specificity_mean>=4.0`, `naturalness_mean>=4.0`,
`certainty_calibrated_rate>=0.95`, and `template_smell_rate<=0.10`.

These thresholds are release evidence only. Do not implement them as a
production keyword check, regular expression, second model, completion gate,
Gateway observer, or delivery interceptor.
