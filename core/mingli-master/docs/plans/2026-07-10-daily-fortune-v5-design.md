# Daily Fortune V5 Design

## Problem

The interactive daily-fortune route can run deterministic tools and still produce an irrelevant answer. The captured failure was:

- Query: `算下明天运势`
- Output: a narrow story about old topics, boundaries, and arguments.

The same story had already been sent for the current day. The existing checker accepted it.

## Root Causes

1. Repeated observations of one day-level signal were treated as independent evidence.
2. Multiple relations produced by one transit branch were counted as separate evidence families.
3. Neutral branch relations were translated directly into life scenes such as old relationships.
4. Equal scores used an alphabetical tie-breaker, so an implementation detail selected the public topic.
5. The helper ignored the known birth datetime and current major-luck cycle.
6. The public gate checked keywords and actions, but not query relevance, whole-day coverage, or phase coverage.
7. Hermes widened the live runtime checker to accept a new contract instead of changing the source of truth.

## Chosen Design

### Fact Layer

`fortune_calc.py` must load the complete validated birth profile through `bazi_fact_adapter.py birth`. It must expose natal facts, active major luck, current year/month/day/hour facts, and raw relation codes. It must never emit concrete event stories.

Signals carry a `source_family` and `temporal_scope`. Repeated probes of a day-level source remain one evidence family. Multiple relations from the same transit branch remain dependent evidence. Day/hour phase differences are preserved separately.

### Interpretation Contract

The fact contract supplies:

- evidence resolution and limitations;
- one day-wide primary behavior lens;
- optional auxiliary relation tendencies;
- morning, afternoon, and evening phase profiles;
- explicit prohibition on inventing a life domain for a broad query.

Relations are auxiliary and cannot become the primary public lens without another independent evidence family. No alphabetical tie-breaker may select meaning.

### Public Answer

A broad today/tomorrow question must answer the whole question in natural prose. It needs an overall tendency, a meaningful time contour when supported, the main behavior implication, and one useful action. These are information requirements, not fixed sentences or a template.

Specific money, work, relationship, health, home, transport, or document scenes may appear only when the user asks about that domain or deterministic evidence explicitly supports it. Warmth means speaking to the person's likely experience without fabricating an event.

### Hermes Enforcement

The gateway buffers broad daily-fortune replies, requires a successful current-contract `fortune_calc.py --window` execution, and applies the same semantic gate to the exact final text. A failure returns a concise recalculation stop instead of a guessed reading.

Runtime skill copies are deployment artifacts. An agent must not patch a live copy merely to make a rejected answer pass.

## Tests

- The two captured old-topic replies fail the public gate.
- Paraphrases that contain only one narrow scene also fail.
- Natural answers with different wording but complete information pass.
- Source-family deduplication prevents pseudo-convergence.
- The complete birth adapter and active major-luck cycle are present.
- Broad queries cannot be dominated by an unrequested domain.
- Main and liujing runtime copies are byte-identical after deployment.
