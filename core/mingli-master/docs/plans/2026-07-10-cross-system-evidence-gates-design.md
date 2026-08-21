# Cross-System Evidence Gates Design

## Problem

The corpus contains 54 D2-ready classical reference packs, but runtime enforcement is uneven.

- Bazi has a deterministic adapter, yet Hermes checks only that the adapter ran. It does not require a current source plan, current classical reads, chart-first public copy, or a passing public gate.
- Daily fortune has deterministic facts and a public gate, but its semantic lenses are not bound to classical packs at answer time.
- Da Liu Ren is the only complete path: deterministic cast, current classical reads, chart-first public copy, and a non-bypassable final gate.
- Ziwei, Xingming, Liuyao/Meihua, Qimen, Taiyi, selection, and Fengshui define required fact fields but have no installed deterministic calculator. Hermes currently allows unsupported readings from these systems to pass unchanged.

This mismatch lets a model name a system, skip its chart and books, and still send generic claims.

## Chosen Design

### Three Authorization Levels

Every calculation-sensitive route receives one of three fact statuses:

1. `deterministic_calculated`: produced by a pinned local adapter and validated against the system schema.
2. `validated_user_provided_chart`: a complete user-supplied chart or plate normalized by a local structural validator. This permits interpretation of the supplied facts only; it never claims that the birth calendar, casting arithmetic, ephemeris, or plate was recalculated.
3. `missing_fact_layer`: incomplete input or no validated adapter output. The response may ask for the smallest missing input set, but it may not contain a chart, outcome, timing, auspicious-date ranking, direction, or other reading.

Existing Bazi, near-time fortune, and Da Liu Ren adapters remain calculation authorities. Other systems use the user-provided-chart path until a separately validated deterministic adapter is installed. Language-model arithmetic, OCR labels, and hand-written `Fact tool` text never authorize a reading.

### Source Plan

A deterministic source-plan compiler maps the validated system, question intent, and available fact scope to:

- required primary packs;
- optional comparison packs;
- exact `rules.md` and `quote-index.md` paths;
- applicable decision-stack layers;
- source caveats and conflicts;
- public chart label and required chart fields.

The source plan does not interpret a chart. It only decides which already-distilled books must be consulted. The agent must open every required rules and quote-index file after the current fact-layer execution. Reading only `index.md`, reading a stale file before the current calculation, or merely naming a book does not count.

Selection is intent-sensitive rather than popularity-driven. For example, formal Bazi always loads the two source anchors, then adds the relevant pattern, strength/flow, Tiaohou, timing, or correction packs. A daily-fortune source plan binds the transit facts to Bazi source anchors and Tiaohou/flow context without turning dependent signals into independent confirmation.

### Public Answer Contract

Formal calculated answers use this order:

1. exact `【玄枢｜MINGLI】` tag and a compact system-appropriate chart;
2. direct answer to the user's actual question;
3. decisive chart mechanism and named classical rule;
4. change conditions, conflicting evidence, and one relevant action when useful;
5. a plain limitation only where the fact or source boundary matters.

The chart label is system-specific: `四柱/命盘`, `卦象`, `课象`, `盘面`, `候选日课`, or `宅局事实`. The first judgment cannot precede the complete compact chart. Public prose remains natural; private audit headings, tool traces, schemas, and checker vocabulary are forbidden.

Daily fortune shows a compact time-basis line containing the validated natal baseline, active luck cycle, and target day before the reading. It must use current classical source evidence, but it must not dump a formal report or invent a life scene merely to sound specific.

### Hermes Enforcement

Hermes buffers every calculation-sensitive Mingli route, not only Bazi and Da Liu Ren. Before delivery, the guard requires:

- current-turn validated facts or an explicit missing-fact stop;
- a source plan matching the current system and question;
- successful reads of all required classical files after the current facts;
- a successful public gate run against the exact final text, exact query, unchanged facts, and source plan;
- no runtime mutation of the installed skill.

Unsupported readings fail closed with a system-specific, conversational request for the smallest missing facts. A source-history or book-comparison question is not a chart reading and may answer from source files without a fact adapter, but it still must not smuggle in a personal prediction.

### Deployment

The distilled-skill repository remains the source of truth. After tests pass, it is synchronized to the Codex skill and both Hermes skill directories. Hermes guard changes are committed separately. Runtime copies are never patched during a live reading.

## Error Handling

- Missing calculator: identify the exact missing chart/plate facts and stop before judgment.
- User-provided chart: expose `未复算` status and restrict claims to the supplied scope.
- Source-plan mismatch or stale source read: block delivery and rerun from the same validated facts.
- Book conflict: preserve the competing rules and select by declared rule profile; do not average them.
- Public gate failure: permit one wording correction using the same facts and sources; never weaken the gate in the live runtime.
- Source-only question: bypass calculation requirements only when no personal outcome is claimed.

## Tests

- Reproduce the current holes: unsupported Ziwei, Liuyao/Meihua, Qimen, Taiyi, selection, and Fengshui drafts must initially pass the old guard and then fail under the new guard.
- All calculation-sensitive systems require buffered delivery.
- Bazi and daily-fortune readings with valid facts but no current source reads fail closed.
- Source reads before the current fact execution, index-only reads, partial pack reads, or book names in prose do not authorize delivery.
- Complete current facts, source plan, required source reads, chart-first copy, and a passing public gate authorize varied natural answers.
- Every system rejects judgment-before-chart and contradictory chart facts.
- Missing-fact responses remain conversational and contain no disguised prediction.
- Source-history questions remain answerable without a chart.
- Existing Bazi, fortune, and Da Liu Ren regression suites remain green.
- All three deployed skill directories are byte-identical, both Hermes gateways listen, and live API replays cover Bazi, daily fortune, Da Liu Ren, one validated user-provided chart, and one unsupported missing-fact route.
