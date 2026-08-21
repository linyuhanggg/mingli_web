# Mingli V5.1 Full-System Intelligent Core Implementation Plan

> **For Claude/Codex/Qoder:** REQUIRED WORKFLOW: execute this plan task-by-task with tests after every task. Preserve existing classical text verbatim; add only verified missing sources or structured indexes. Do not deploy to Hermes or push to GitHub until the final acceptance stage passes.

**Goal:** Replace the split semantic routing, unreliable evidence fallback, stale follow-up evidence, and incomplete deterministic fact layers with one model-agnostic transaction flow, and finish executable or observation-driven production capability for all 13 runtime routes in the same release.

**Architecture:** The current caller model converts the full conversation into an extensible semantic `IntentFrame`; it does not choose behavior through keywords. A generic resolver compares that frame with provider-declared capabilities and conversation state, then the transaction engine performs deterministic calculation, applicability-filtered classical evidence retrieval, versioned follow-up adjudication, and mechanical integrity checks. The current caller model remains responsible for interpretation, cross-source reasoning, self-review, and natural Chinese; no model or provider name is stored in the skill.

**Tech Stack:** Python 3, dataclasses, JSON/JSONL contracts, existing deterministic adapters, existing atomic reading store, unittest/pytest-compatible test suite, shell transaction entrypoint.

---

## Non-negotiable decisions

1. Keep `scripts/run_reading_transaction.sh` as the only production entrypoint.
2. Keep the existing corpus, source provenance, deterministic Bazi/Liuren/Fortune/Ziwei calculations, and reading lineage, then extend them rather than replacing them.
3. Do not add intent keywords, synonym tables, output sentence templates, model names, provider names, or model-specific branches.
4. Do not let the LLM calculate chart facts. It interprets language and evidence; executable providers calculate facts.
5. Do not let the gateway classify Mingli meaning. It verifies transaction identity and delivers accepted output only.
6. Do not run every system for every request. Use one primary system; add a compatible secondary system only for an explicit cross-check purpose.
7. Do not expose internal retries, evidence gaps, artifact states, or repair commands to the user.
8. Do not use semantic regex gates on final prose. Validate structure and provenance mechanically; use the current caller model for semantic review.
9. Treat all 13 runtime routes as mandatory V5.1 release scope. “Validation only”, “future provider”, and “corpus available” are not completion states unless the system is intrinsically observation-driven.
10. Allow small tested commits and internal checkpoints, but do not deploy, publish, or announce completion until the full capability audit passes.

## Four confirmed defects to eliminate

1. **Split routing authority:** V4 accepts a caller-selected system without semantic validation, while missing `action` falls into the legacy V3 regex router.
2. **False evidence binding:** zero-score retrieval falls back to the first record, and unmatched evidence is attached to the first four facts.
3. **Stale continuation:** `continue` reuses the previous evidence and judgment even when the user asks a new dimension.
4. **Incomplete fact horizon:** providers may return only natal/base facts while the answer makes yearly, monthly, timing, health, or event-specific claims that the deterministic calculation never produced.

Provider coverage is a separate capability deficit built on top of these four defects: only Bazi, Fortune, Liuren, and Ziwei currently calculate their own facts; the other systems mostly validate supplied charts.

## Mandatory V5.1 capability scope

All rows below belong to this implementation, not a later roadmap.

| runtime route | required production mode | minimum complete fact layer | primary classical source families |
|---|---|---|---|
| `bazi` | deterministic calculation and horizon extension | calendar normalization, four pillars, hidden stems, Ten Gods, month command, strength/structure, seasonal/tiaohou facts, luck cycles, requested annual/monthly layers | 《三命通会》《渊海子平》《子平真诠》《滴天髓阐微》《穷通宝鉴》 |
| `fortune` | deterministic near-time calculation | natal baseline, active luck cycle, exact target period, target Ganzhi, Ten-God and stem/branch relations, seasonal/tiaohou change | Bazi source stack with near-time applicability |
| `ziwei` | deterministic natal and temporal calculation | calendar normalization, twelve palaces, Ming/Shen, stars, brightness/state where supported, transformations, major limits, requested annual/monthly layers | 《紫微斗数全书》《太微赋》及已标层注释 |
| `luming-nayin` | deterministic early Luming/Nayin calculation | four pillars, Taiyuan when required, Tianyuan/Diyuan/Renyuan, sixty-Jiazi Nayin, Lu/Ma/Gui and source-required early-Luming relations | 《李虚中命书》《珞琭子三命消息赋》《五行精纪》《兰台妙选》 |
| `xingming` | deterministic ephemeris-backed Xingming calculation | calendar normalization, ephemeris/version, geocentric positions, classical bodies/points, houses/degrees, Ming/Shen degrees, transformations and requested limit layers | 《果老星宗》《星命溯源》《星学大成》 |
| `liuyao` | deterministic casting or complete supplied-cast validation | cast provenance, six lines, moving lines, main/changed hexagrams, Najia, Shi/Ying, Six Relatives, Six Spirits, Xunkong, hidden lines, month/day strength | 《增删卜易》《卜筮正宗》《黄金策》《火珠林》 |
| `meihua` | deterministic time/number/observation casting or supplied-cast validation | casting method/provenance, upper/lower trigrams, moving line, main/mutual/changed hexagrams, body/use, seasonal strength | 《梅花易数》及明确依赖的易学基础 |
| `liuren` | deterministic complete casting and requested-dimension extension | calendar normalization, day/hour, month general, heaven/earth plates, four lessons, three transmissions, lesson method, generals, Six Relatives, Xunkong, requested timing/state facts | 《大六壬大全》《六壬指南》《大六壬秘本》 |
| `qimen` | deterministic time-board calculation | calendar normalization, solar-term boundary, Yin/Yang Dun, Ju, Xunshou, Chief/Director, nine palaces, stars, doors, deities, stems, Xunkong and patterns | 《奇门遁甲统宗大全》及已核验起局材料 |
| `taiyi` | deterministic board calculation | calendar normalization, epoch/accumulated-year rule, Ji/Yuan, Taiyi position, major deities, host/guest counts, Wenchang/Shiji/Tianmu/Kemu and declared scope | 《太乙神数》 |
| `selection` | deterministic candidate generation and comparison | event profile, date range, calendar normalization, candidate dates/times, Jianchu, mansions, gods, Huang/Hei, Yi/Ji, conflicts, participant constraints where applicable | 《钦定协纪辨方书》《星历考原》，《董公择日》《玉匣记》作分层旁证 |
| `fengshui` | measurement/observation-driven calculation and validation | observation provenance, compass degree, sitting/facing, 24 mountains, period/year, site/layout/form observations, selected school variables and calculated chart where applicable | 《葬书》《黄帝宅经》《撼龙经》《疑龙经》《阳宅十书》等分流派使用 |
| `physiognomy` | image/user-observation-driven normalization and interpretation | observation provenance, image/lighting quality, visible feature observations, region anchors, uncertainty; no unobserved feature generation | 《神相全编》《柳庄相法》《麻衣神相》等分层使用 |

Every calculable provider must pass at least 30 deterministic fixture cases, including boundary dates and known difficult patterns. Observation-driven providers must pass at least 20 structured fixtures covering complete, partial, conflicting, and low-quality observations. Each classical rule used at runtime must have a local source anchor and an applicability predicate.

## One-run execution protocol

1. Execute this as one V5.1 goal from Task 1 through Task 12; task boundaries are internal checkpoints, not user handoff points.
2. After each checkpoint, run focused tests, record the result, and commit only that coherent change. Continue automatically to the next checkpoint.
3. Maintain a machine-readable progress ledger containing current task, completed tests, unresolved defects, and next command so context compaction can resume without restarting.
4. Do not ask the user to confirm routine implementation choices. Ask only when an external credential, unavailable private source, or irreversible operation genuinely requires owner input.
5. Do not replace an unfinished provider with a stub, `validation_only`, a prompt, or a TODO. Research and close the dependency, or keep the entire V5.1 release incomplete.
6. “Tests pass” means focused, full-suite, fixture, replay, and deployment checks all pass. A partial green subset is not completion.
7. Produce one final implementation and acceptance report only after the final release criteria pass.

## Target transaction

```text
whole conversation
  -> current caller model: IntentFrame
  -> state resolver: new / continue / correct / recast / resume
  -> capability resolver: primary system and optional cross-check purpose
  -> deterministic provider: calculation snapshot and requested extensions
  -> evidence compiler: applicable rules, exceptions, source relationships
  -> adjudication: claim candidates and unresolved conflicts
  -> current caller model: analysis, claim review, natural Chinese answer
  -> mechanical integrity check
  -> accepted version and atomic delivery
```

## Core contracts

### IntentFrame

The caller derives this from the full conversation. Fields are extensible semantic values, not a fixed language vocabulary.

```json
{
  "subject_refs": ["conversation subject identifiers"],
  "calculation_object": "natal|near_time_personal|concrete_event|calendar_choice|spatial_observation|appearance_observation|supplied_chart",
  "question_dimensions": ["timing", "outcome", "state", "location", "relationship", "health", "career"],
  "horizon": {"kind": "instant|day|month|year|life", "start": null, "end": null},
  "requested_method": null,
  "requested_granularity": "directional|period|date|time_window|ranked_alternatives",
  "continuity": {"reading_id": null, "same_subject": false, "same_event": false},
  "facts_present": ["structured fact identifiers"],
  "facts_corrected": [],
  "evidence_questions": ["open semantic questions for classical evidence"],
  "cross_check_requested": false
}
```

### ProviderCapability

Every provider declares what it can calculate. The resolver compares structured capabilities; it never reads raw user prose.

```json
{
  "system": "bazi",
  "mode": "calculation|validation_only|unavailable",
  "objects": ["natal", "near_time_personal"],
  "horizons": ["month", "year", "life"],
  "dimensions": ["career", "relationship", "health", "timing"],
  "required_inputs": ["birth_datetime", "timezone", "location", "gender"],
  "outputs": ["four_pillars", "luck_cycles", "transit_layers"],
  "extension_outputs": ["year_layers", "month_layers"],
  "independent_lineage": "bazi"
}
```

### EvidenceRule

```json
{
  "rule_id": "stable source-bound id",
  "system": "bazi",
  "source_pack": "bazi/qiongtong-baojian",
  "source_layer": "primary|commentary|modern",
  "chapter": "source chapter",
  "quote": "short source-bound excerpt",
  "source_anchor": "path and line/page anchor",
  "topics": ["tiaohou"],
  "required_fact_predicates": [],
  "excluded_fact_predicates": [],
  "exception_rule_ids": [],
  "conflict_rule_ids": [],
  "depends_on_rule_ids": [],
  "record_kind": "substantive_rule"
}
```

### Reading version invariants

- `continue`: same calculation digest unless a deterministic extension is required; always a new intent, evidence, judgment, and answer version.
- `correct`: recalculated digest, same reading lineage, previous version superseded.
- `recast`: new child calculation with root-question lineage retained.
- `resume`: fills the saved intake fields and resumes the original request without asking for the original question again.
- Every material claim records fact IDs, evidence IDs, counter-evidence IDs, scope, and requested dimension.

---

## Task 1: Make V4 the only production routing path

**Files:**
- Modify: `SKILL.md`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `scripts/reading_engine/request_contract.py`
- Modify: `scripts/run_reading_transaction.sh`
- Modify: `references/v2-reading-transaction.md`
- Test: `scripts/test_v4_request_contract.py`
- Test: `scripts/test_reading_transaction_cli.py`
- Test: `scripts/test_audit_v4_runtime_boundary.py`

**Steps:**

1. Add failing tests proving a production `prepare` request without V4 `action` cannot invoke `legacy_v3.routing.route_request`.
2. Make the production CLI require a valid structured V4 request.
3. Move legacy imports and migrations behind a separately named offline migration command; do not leave an implicit runtime fallback.
4. Delete runtime semantic regex dependencies from the V4 transaction path.
5. Run the focused tests and confirm that no V4 request imports `legacy_v3.routing`.
6. Commit as `refactor: make v4 the sole mingli runtime`.

**Acceptance:** A missing `action` or malformed V4 request produces an internal structured contract error before calculation. It never silently changes routing strategy and never emits an internal error as a public reading.

## Task 2: Add semantic IntentFrame and capability-based resolution

**Files:**
- Modify: `scripts/reading_engine/contracts.py`
- Modify: `scripts/reading_engine/request_contract.py`
- Create: `scripts/reading_engine/intent_frame.py`
- Create: `scripts/reading_engine/capability_resolver.py`
- Modify: `scripts/route_capabilities.py`
- Modify: `scripts/reading_engine/providers.py`
- Modify: `scripts/reading_engine/factory.py`
- Modify: `references/routing.md`
- Test: `scripts/test_v4_request_contract.py`
- Create: `scripts/test_v51_capability_resolver.py`
- Modify: `scripts/test_v4_conversation_trajectories.py`

**Steps:**

1. Add a required `intent` object to V4 requests while retaining `query` as the exact user text.
2. Add `ProviderCapability` declarations to each registered provider.
3. Resolve systems in this precedence order: explicit user-requested method; valid same-reading continuation; object/horizon/dimension compatibility; available structured inputs; least unsupported assumptions.
4. Return a structured ambiguity only when two executable providers remain equally suitable and the distinction materially changes the calculation. Do not ask the user merely to choose a school when one valid default exists.
5. Treat validation-only providers as ineligible for automatic casting unless complete supplied chart data exists.
6. Record the selected primary system, considered providers, rejected reasons, and optional cross-check purpose in the private transaction artifact.
7. Test arbitrary natural-language paraphrases by supplying equivalent IntentFrames; prove that raw words never affect the deterministic resolver.
8. Commit as `feat: resolve mingli systems from semantic capabilities`.

**Acceptance:** The same IntentFrame always selects the same executable system regardless of wording. An explicit system request wins when executable. A wrong caller-supplied system is rejected when it cannot satisfy the declared object, horizon, or dimensions.

## Task 3: Correct action and conversation-state resolution

**Files:**
- Modify: `scripts/reading_engine/session_state.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `references/conversational-reading-dialogue.md`
- Test: `scripts/test_v4_followup_state.py`
- Test: `scripts/test_v4_intake_conversation.py`
- Test: `scripts/test_v4_conversation_trajectories.py`

**Steps:**

1. Resolve action from structured continuity and state, not from the latest message text.
2. Bind a short answer such as a city, time, gender, or corrected character to the pending intake field and resume the saved original request.
3. Make `continue` valid only for the same subject and same bound calculation.
4. Convert a changed event, changed subject, or deliberately changed system into `new` or `recast` with explicit lineage.
5. Preserve all known facts and prohibit asking the user to repeat the original question.
6. Add multi-turn tests for city-only replies, photo transcription corrections, same-chart questions, new-event questions, and explicit method changes.
7. Commit as `fix: resolve mingli actions from bound conversation state`.

**Acceptance:** Replying only “北京” resumes the original request. A same-reading question keeps the calculation. A genuinely new event cannot accidentally reuse the old cast.

## Task 4: Replace evidence fallback with applicability-first retrieval

**Files:**
- Create: `scripts/build_evidence_index.py`
- Create: `scripts/reading_engine/evidence_rules.py`
- Modify: `scripts/reading_evidence_bundle.py`
- Modify: `scripts/reading_source_plan.py`
- Modify: `scripts/search_bm25.py`
- Create generated artifact: `references/index/evidence-rules.jsonl`
- Test: `scripts/test_reading_evidence_bundle.py`
- Test: `scripts/test_reading_source_plan.py`
- Test: `scripts/test_evidence_independence.py`
- Create: `scripts/test_v51_evidence_applicability.py`

**Steps:**

1. Compile substantive corpus records into `EvidenceRule` entries with source anchors and fact predicates.
2. Exclude headings, table headers, statistics, manifests, acquisition notes, validation instructions, and quote-index metadata from runtime evidence.
3. Filter by system and required/excluded fact predicates before any relevance ranking.
4. Rank only eligible records using the caller-provided semantic `evidence_questions` plus structured dimensions and fact identifiers.
5. Delete the “first record” fallback. Zero applicable matches must remain zero matches with a structured source-gap reason.
6. Delete arbitrary “first four facts” attachment. A rule receives fact references only when its predicates actually match.
7. Retrieve exceptions, conflicts, and dependent lineage explicitly. Repeated derivative texts do not count as independent corroboration.
8. Require each material claim search to record either applicable counter-evidence or an explicit `no_applicable_counter_evidence` result.
9. Add known regression fixtures for the prior bad matches: statistics records, header rows, `子象`, wrong day-master chapters, generic Liuren entry rules, and empty counter-evidence.
10. Commit as `fix: retrieve only applicable classical evidence`.

**Acceptance:** No selected evidence is metadata. Qiongtong records match the actual day master and month context. Liuren records match the calculated lesson/transmissions and requested dimension. A zero match cannot become a fabricated citation.

## Task 5: Recompile evidence and judgment for every follow-up

**Files:**
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `scripts/reading_engine/session_state.py`
- Modify: `scripts/reading_engine/storage.py`
- Test: `scripts/test_v4_followup_state.py`
- Test: `scripts/test_reading_followup.py`
- Test: `scripts/test_followup_publish.py`

**Steps:**

1. Add a failing test proving two different questions on one reading currently share an evidence digest.
2. Preserve the immutable base calculation for `continue`.
3. Compile a new evidence bundle from the latest IntentFrame and active query.
4. Produce a new judgment and answer version; do not carry the previous judgment as current authority.
5. Carry prior claims only as conversation context, never as automatic answers to the new dimension.
6. Store `calculation_digest`, `intent_digest`, `evidence_digest`, and `judgment_digest` independently per version.
7. Test that a career follow-up and a health follow-up share natal facts but use different applicable evidence and conclusions.
8. Commit as `fix: refresh evidence and judgment on mingli followups`.

**Acceptance:** Same calculation digest, different intent/evidence/judgment digests for different follow-up dimensions. The answer directly closes the latest question and cannot repeat the previous public copy as a fallback.

## Task 6: Add deterministic fact extensions before interpretation

**Files:**
- Modify: `scripts/reading_engine/providers.py`
- Modify: `scripts/reading_engine/fortune.py`
- Modify: `scripts/reading_engine/ziwei.py`
- Modify: `scripts/bazi_fact_adapter.py`
- Modify: `scripts/liuren_calc.py`
- Create: `scripts/test_v51_fact_extensions.py`
- Modify: `scripts/test_v4_providers.py`

**Steps:**

1. Add `extend(calculation, requested_dimensions, horizon)` to the provider interface.
2. For Bazi, calculate every requested year/month layer, active luck cycle, Ten Gods, stem/branch relations, seasonal/tiaohou effects, and exact calendar normalization before allowing claims about that horizon.
3. For Fortune, bind one explicit target period and expose only calculated layers for that period.
4. For Ziwei, add the requested Da Xian/Liu Nian/Liu Yue layers and transformations before temporal interpretation.
5. For Liuren, expose dimension-specific facts and timing candidates with traceable calculation rules; do not infer exact dates from generic lesson metadata.
6. Return a structured unsupported-dimension result when a provider cannot calculate the requested granularity. The caller must narrow the answer, choose a compatible cross-check, or ask for a genuinely missing external fact; it must not extrapolate.
7. Add tests proving that a 2024-2040 answer contains 2024-2040 deterministic layers and that an exact timing answer has a timing-rule trace.
8. Commit as `feat: extend deterministic facts to the requested horizon`.

**Acceptance:** No year, month, date, location, health period, or event-specific conclusion can cite only natal/base facts.

## Task 7: Complete all provider capabilities in this release

**Files:**
- Modify: `scripts/reading_engine/providers.py`
- Modify: `scripts/reading_engine/factory.py`
- Modify: `scripts/route_capabilities.py`
- Create: `scripts/reading_engine/calendar_core.py`
- Create: `scripts/reading_engine/ephemeris_core.py`
- Add dedicated provider modules and tests under `scripts/reading_engine/`
- Modify the matching `references/system-cards/*.md`
- Create: `references/matrices/provider-completeness.yaml`
- Create: `scripts/audit_provider_completeness.py`
- Create: `scripts/test_v51_provider_completeness.py`

### Task 7 preflight: Close algorithm-source dependencies

1. Create `references/matrices/algorithm-source-dependencies.yaml` listing every formula, table, epoch, convention, and lookup required by each provider.
2. For each dependency, record the primary classical anchor, any commentary dependency, edition/source status, local normalized path, hash, and independent fixture source.
3. Audit whether the existing full text actually contains the computational material. A book title or interpretive summary is not proof that its tables and procedures are available.
4. Acquire and normalize missing public-domain or properly licensed source material before implementing the dependent algorithm. For image-only tables, transcribe them and independently verify every row against the image or a second edition.
5. Treat external GitHub implementations as engineering references and test oracles only. They cannot replace primary-source provenance or fixture verification.
6. Keep disputed school conventions as separately named versions; do not silently choose one or merge their tables.
7. Create `scripts/audit_algorithm_sources.py` and fail Task 7 when any provider dependency is missing, unhashed, unanchored, or marked placeholder.
8. Commit as `docs: close mingli algorithm source dependencies`.

### Task 7A: Shared calendar and astronomy foundation

1. Extract one authoritative `calendar_core` from the existing Bazi/Fortune/Liuren implementations instead of keeping separate date logic.
2. Preserve civil datetime, timezone, location, longitude/latitude source, calendar convention, lunar date including leap-month state, four Ganzhi fields, and exact solar-term boundary.
3. Add boundary tests for Zi hour, day rollover convention, leap month, solar-term month change, DST/historical timezone, and locations east/west of the default meridian.
4. Add one versioned ephemeris service for Xingming and any astronomy-dependent calculations. Use a proven library, record version/data files/license, and never hand-roll planetary positions.
5. Require every time-driven provider to consume the shared normalized result and bind its digest.
6. Commit as `refactor: unify mingli calendar and ephemeris facts`.

### Task 7B: Finish Bazi and Fortune

1. Preserve the existing Bazi adapter as the calculation authority.
2. Add requested year/month/day extensions, active luck-cycle facts, stem/branch interactions, structural changes, and seasonal/tiaohou deltas.
3. Keep Shensha as a separately labeled auxiliary layer that cannot override month command, structure, strength, tiaohou, and luck/transit facts.
4. Make Fortune a bounded near-time view over the same verified natal facts rather than a separate simplified interpretation system.
5. Add at least 30 fixtures covering weak/strong/cong/hua disputes, seasonal extremes, luck-cycle boundaries, and long-horizon queries.
6. Commit as `feat: complete bazi and fortune fact horizons`.

### Task 7C: Finish Ziwei natal and transit calculation

1. Preserve the vendored deterministic chart engine and record its version.
2. Add major limit, annual, monthly, and requested transformation layers without letting the LLM place stars or transformations.
3. Emit palace/star/transformation facts independently from classical interpretation.
4. Test leap-month handling, Zi-hour convention, gender/direction rules, limit boundaries, and known reference charts.
5. Connect applicable rules from `ziwei/ziwei-doushu-quanshu` and `ziwei/taiwei-fu`; keep late observational texts in their declared commentary layer.
6. Commit as `feat: complete ziwei temporal calculation`.

### Task 7D: Build the early Luming and Nayin provider

1. Create `scripts/reading_engine/luming.py` using shared calendar/four-pillar facts.
2. Calculate the exact sixty-Jiazi Nayin, Tianyuan/Diyuan/Renyuan, Taiyuan when required, and each source-declared Lu/Ma/Gui relation.
3. Do not translate these concepts into modern Bazi Ten-God logic; preserve the early-Luming system as an independent fact and evidence lineage.
4. Test against at least 30 examples extracted from 《李虚中命书》《五行精纪》《兰台妙选》 and cross-check all sixty Nayin mappings.
5. Change `luming-nayin` from `unavailable` to `calculation` only after the completeness audit passes.
6. Commit as `feat: add deterministic early luming provider`.

### Task 7E: Build the Xingming and Qizheng Siyu provider

1. Create `scripts/reading_engine/xingming.py` on the shared ephemeris service.
2. Calculate the classical bodies/points required by the selected source convention, their longitudes/degrees, houses, Ming/Shen degrees, transformations, and requested limit layers.
3. Record tropical/sidereal, coordinate, precession, house, and classical pseudo-point conventions explicitly; never mix conventions silently.
4. Compare at least 30 reference charts from source examples or independently generated trusted charts, including date and location boundaries.
5. Keep blocked/unverified source packs out of first-line evidence until their provenance audit passes.
6. Commit as `feat: add ephemeris-backed xingming provider`.

### Task 7F: Build the Liuyao provider

1. Create `scripts/reading_engine/liuyao.py` with two valid inputs: a complete supplied cast, or a transaction-created digital coin cast whose random seed and six tosses are generated once and preserved.
2. Never silently substitute time-based Meihua casting for Liuyao.
3. Calculate main/changed hexagrams, moving lines, Najia, Shi/Ying, Six Relatives, Six Spirits, Xunkong, hidden lines, month/day strength, clash/combine/growth/restraint relations, and requested-useful-spirit candidates.
4. Keep useful-spirit selection as evidence-bound adjudication when different schools disagree; preserve the calculated candidate facts.
5. Test all 64 hexagrams, line changes, Shi/Ying placement, Najia tables, Xunkong, month break, day clash, returning growth/restraint, and at least 30 complete classical examples.
6. Connect 《增删卜易》《卜筮正宗》《黄金策》《火珠林》 by source lineage and exception rules.
7. Commit as `feat: add complete deterministic liuyao provider`.

### Task 7G: Build the Meihua provider

1. Create `scripts/reading_engine/meihua.py` supporting time, supplied number, sound/count, observation, and complete supplied-hexagram methods when the caller provides the method facts.
2. Record the exact casting method and input provenance; do not choose a hidden random method.
3. Calculate upper/lower trigram, moving line, main/mutual/changed hexagrams, body/use, five-element relations, and seasonal strength.
4. Test every remainder boundary, moving-line boundary, mutual-hexagram extraction, calendar normalization dependency, and at least 30 source examples from 《梅花易数》.
5. Keep Meihua and Liuyao facts separate even when they produce the same hexagram name.
6. Commit as `feat: add complete deterministic meihua provider`.

### Task 7H: Harden the existing Daliuren provider

1. Preserve the existing four-lessons/three-transmissions calculation and verify all nine method branches.
2. Add requested-dimension extensions for outcome, timing, current state, location direction, relationship, work, and money only when matching deterministic facts and rules exist.
3. Separate casting rules, image/category correspondences, issue-specific judgment rules, and timing rules in the evidence index.
4. Test Fuyin, Fanyin, Shehai, Yaoke, Mao Xing, Bie Ze, Ba Zhuan and boundary casts against at least 30 classical/reference examples.
5. Remove any exact timing conclusion based only on generic metadata.
6. Commit as `fix: complete liuren dimensions and timing trace`.

### Task 7I: Build the Qimen provider

1. Create `scripts/reading_engine/qimen.py` using shared calendar and solar-term facts.
2. Declare and version the selected Ju/Chao convention; calculate Yin/Yang Dun, Yuan/Ju, Xunshou, Chief/Director, nine palaces, nine stars, eight doors, deities, three wonders/six instruments, horse star, Xunkong, and named patterns.
3. Preserve alternative-school differences as separate conventions; never combine incompatible boards.
4. Test solar-term transitions, upper/middle/lower Yuan, Dun direction, Ju boundaries, palace placement, Chief/Director, Xunkong, and at least 30 trusted boards.
5. Connect only rules whose board predicates match from 《奇门遁甲统宗大全》 and other verified packs.
6. Commit as `feat: add complete deterministic qimen provider`.

### Task 7J: Build the Taiyi provider

1. Create `scripts/reading_engine/taiyi.py` with an explicit epoch/accumulated-year convention and declared scope.
2. Calculate Ji/Yuan, Taiyi position, major deities, Wenchang, Shiji, Tianmu/Kemu, host/guest counts and the other facts required by the selected classical method.
3. Keep national/macro historical methods distinct from personal/event usage; routing must not claim a scope the provider does not calculate.
4. Verify the complete cycle/table invariants and at least 30 source/reference boards before setting `provider_ready=true`.
5. Bind evidence from 《太乙神数》 to exact board predicates and declared scope.
6. Commit as `feat: add deterministic taiyi provider`.

### Task 7K: Build the Selection provider

1. Create `scripts/reading_engine/selection.py` that accepts an event profile, date range, location/timezone, hard constraints, and optional participant facts.
2. Generate candidate dates/times rather than requiring the user to supply a precomputed table.
3. Calculate Jianchu, mansions, required year/month/day/hour gods, Huang/Hei, Yi/Ji, clashes, exclusions, and event-specific rules for every candidate.
4. Keep official 《协纪辨方书》《星历考原》 rules separate from folk 《董公择日》《玉匣记》 rules; expose disagreements instead of silently merging them.
5. Return ranked candidates with explicit elimination reasons and no unexplained score.
6. Test boundary dates, event profiles, participant clashes, “no valid candidate” ranges, and at least 30 published calendar examples.
7. Commit as `feat: add deterministic selection candidate engine`.

### Task 7L: Build the Fengshui observation and calculation provider

1. Create `scripts/reading_engine/fengshui.py` with separate `form` and `liqi` subprofiles.
2. Accept compass degree, measurement method, sitting/facing, building completion/occupation period, floorplan/site images, room directions, entrances, roads, water and terrain observations.
3. Normalize compass facts into 24 mountains and calculate only the explicitly selected school variables and charts; do not silently mix Sanhe, Bazhai, Xuankong or other schools.
4. Let the current vision-capable caller transcribe visible floorplan/site observations with region anchors and uncertainty. Require user confirmation only for unreadable or genuinely unmeasured critical facts.
5. Use 《葬书》《撼龙经》《疑龙经》等 for form evidence and 《黄帝宅经》《阳宅十书》等 for their applicable declared layers.
6. Test compass boundaries, period transitions, incomplete floorplans, contradictory measurements, school separation, and at least 20 complete observation fixtures.
7. Mark this route `observation_driven_ready`, not generic `validation_only`.
8. Commit as `feat: add fengshui observation and calculation provider`.

### Task 7M: Build the Physiognomy observation provider

1. Create `scripts/reading_engine/physiognomy.py` accepting images or user-supplied observations.
2. Let the current vision-capable caller produce structured visible observations with image region, lighting/angle/occlusion quality, and uncertainty; the provider validates and normalizes them.
3. Never generate features that are not visible, and never treat two images under different lighting as automatically equivalent.
4. Bind applicable observations to 《神相全编》《柳庄相法》《麻衣神相》等 rules while retaining source disagreements and later accretions.
5. Test full-face, partial, profile, low-light, filtered, contradictory and user-corrected inputs across at least 20 fixtures.
6. Mark this route `observation_driven_ready` only when missing/uncertain observations are handled naturally without inventing them.
7. Commit as `feat: add physiognomy observation provider`.

### Task 7N: Enforce provider completion

1. Generate `references/matrices/provider-completeness.yaml` from actual provider declarations and test results.
2. The audit verifies required fields, fixture counts, boundary coverage, algorithm version, provenance, source applicability, and no placeholder provider.
3. Fail the release when any route remains `unavailable`, generic `validated-user-chart`, or has undeclared missing dimensions.
4. Run every provider twice on identical inputs and require identical fact digests except for a newly created Liuyao random cast; that cast must become deterministic after its seed is persisted.
5. Run the complete provider suite before starting cross-system work.
6. Commit as `test: enforce complete mingli provider matrix`.

**Acceptance:** All 13 routes pass the declared mode and fixture threshold. `provider_ready=true` means the provider produces its complete declared fact layer; `observation_driven_ready` means it can normalize and calculate from real supplied observations without inventing measurements. Corpus presence alone never changes readiness.

## Task 8: Add controlled cross-system corroboration

**Files:**
- Create: `scripts/reading_engine/cross_check.py`
- Modify: `scripts/reading_engine/contracts.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `references/routing.md`
- Create: `scripts/test_v51_cross_system.py`

**Steps:**

1. Cross-book corroboration inside the primary system runs by default when applicable independent sources exist.
2. Cross-system calculation requires an explicit purpose: user request, unresolved primary result, materially conflicting source evidence, or a distinct compatible fact layer that answers the same dimension.
3. Select a secondary provider only when its required inputs already exist or one indispensable external fact can be asked naturally.
4. Preserve each system's facts and conclusions separately. Never merge symbols or treat two schools as duplicate votes.
5. Compare only shared answer dimensions and report agreement, conflict, and the reason for the final priority.
6. Do not invoke a secondary system merely to decorate the answer or inflate confidence.
7. Commit as `feat: add purpose-bound cross-system corroboration`.

**Acceptance:** A Bazi/Ziwei or Liuren/Liuyao comparison is traceable as two independent calculations. Incompatible systems are not combined. A normal simple request still uses one primary system.

## Task 9: Replace semantic prose gates with model-independent claim integrity

**Files:**
- Modify: `SKILL.md`
- Modify: `scripts/reading_engine/answer_contract.py`
- Modify: `scripts/reading_engine/transaction.py`
- Modify: `references/public-reading-contract.md`
- Test: `scripts/test_v4_answer_contract.py`
- Create: `scripts/test_v51_natural_answer_contract.py`

**Steps:**

1. Remove regex checks that attempt to decide whether free Chinese reverses, refuses, or answers the question.
2. Keep only mechanical checks: transaction identity, required structured fields, fact/evidence IDs, lineage, digest consistency, and no internal protocol fields in public output.
3. Require the current caller model to perform one private review using the latest query, IntentFrame, facts, evidence, counter-evidence, draft claims, and draft answer.
4. The review must remove unsupported specificity, resolve contradictions, answer the latest question, and preserve a clear final conclusion.
5. Keep content obligations rather than fixed wording: expose the actual chart/hexagram basis, answer the question directly, explain decisive mechanisms, and state meaningful uncertainty or alternatives when present.
6. Do not prescribe sentences, paragraph counts, canned financial advice, or a fixed response template.
7. On drafting failure after a valid judgment, retry privately within the same transaction. If calculation succeeded but prose generation repeatedly fails, construct a minimal answer from accepted claim content without asking the user to resend or recast.
8. Commit as `refactor: keep mingli facts strict and prose intelligent`.

**Acceptance:** The answer sounds natural across models, gives a definite answer rather than only explaining symbols, and cannot expose “按原题重算”, `missing_facts`, artifact IDs, or internal repair language.

## Task 10: Keep model choice outside the skill and measure it honestly

**Files:**
- Create: `tests/replay/mingli-routing-cases.jsonl`
- Create: `tests/replay/mingli-answer-cases.jsonl`
- Create: `scripts/run_model_replay.py`
- Create: `docs/model-evaluation.md`

**Steps:**

1. Ensure the repository contains no production GPT, GLM, Qwen, Sol, Terra, provider, or reasoning-level selection.
2. Use the model already configured by the caller for IntentFrame creation, evidence adjudication, private review, and prose.
3. Keep one model for the active session at the Hermes host level; changing the host model must require no skill changes.
4. Build an anonymized replay set covering all systems, ordinary non-Mingli questions, paraphrases, images, missing facts, follow-ups, corrections, recasts, and source conflicts.
5. Hold calculation and evidence artifacts constant when comparing models.
6. Score route correctness, unsupported-claim rate, evidence relevance, direct-answer rate, follow-up continuity, naturalness, and token/latency cost.
7. Select a Hermes default from measured results, not from hardcoded skill policy.
8. Commit as `test: add model-independent mingli replay evaluation`.

**Acceptance:** Switching Hermes from one capable model to another changes only interpretation quality, never provider behavior, state continuity, evidence identity, or calculation facts.

## Task 11: Add outcome calibration without rewriting history

**Files:**
- Create: `scripts/reading_engine/outcome_store.py`
- Create: `scripts/record_reading_outcome.py`
- Create: `scripts/test_v51_outcome_calibration.py`
- Create: `docs/outcome-calibration.md`

**Steps:**

1. Store immutable time-bound claims separately from the original reading.
2. When the user later reports an outcome, bind it to the exact claim and record `hit`, `partial`, `miss`, or `unknown` with evidence.
3. Never edit the original prediction after the outcome is known.
4. Aggregate results by provider version, rule ID, source lineage, question dimension, and horizon.
5. Do not produce fake probability percentages from small samples. Use calibration only to find weak rule combinations and regression risk.
6. Apply any future retrieval weighting only after a documented sample threshold and a reversible versioned change.
7. Commit as `feat: add immutable mingli outcome calibration`.

**Acceptance:** Accuracy discussions can reference recorded outcomes instead of impressions, while classical source text and historical readings remain unchanged.

## Task 12: Full regression, shadow comparison, and deployment

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Update: deployment manifests and checksums only after acceptance

**Required regression cases:**

- “算一下我妈现在在哪” starts one complete suitable transaction.
- Replying “北京” to a location intake resumes the original question.
- “明天运势怎么样” returns a complete first-turn answer.
- “下次入账什么时候” and “大概多少钱” remain one reading but refresh evidence by dimension.
- A Bazi image is transcribed and deterministically calculated before interpretation.
- Long-horizon health/career claims have matching yearly facts.
- Ziwei natal and temporal fixtures expose the requested limits and transformations.
- Luming/Nayin remains independent from modern Bazi interpretation and calculates its declared early-Luming facts.
- Xingming positions match the pinned ephemeris and declared classical convention.
- Liuyao completes one preserved six-toss cast with full Najia/line facts.
- Meihua records its casting method and returns main/mutual/changed hexagrams with body/use.
- Liuren exposes complete four lessons/three transmissions and issue-specific evidence.
- Qimen returns a complete board across a solar-term boundary fixture.
- Taiyi returns a complete board under its declared epoch and scope.
- Selection generates and compares dates instead of requiring a precomputed candidate chart.
- Fengshui normalizes real compass/layout observations without mixing schools.
- Physiognomy distinguishes visible observation, uncertainty, and classical interpretation.
- Explicit Ziwei/Luming/Xingming/Liuyao/Meihua/Liuren/Qimen/Taiyi/Selection/Fengshui/Physiognomy requests cannot silently become Bazi.
- Ordinary calculation, coding, and casual questions do not invoke the skill.
- No evidence result contains metadata/header/statistics records.
- No follow-up reuses an unrelated judgment or public answer.
- No public output contains protocol status, retry commands, artifact IDs, or model names.

**Deployment steps:**

1. Run focused tests after every task.
2. Run the complete repository test suite.
3. Run the fixed offline conversation replay set against old and new code.
4. Review every changed public answer where the selected system differs.
5. Build a clean release artifact from the source repository.
6. Verify checksums before installing anywhere.
7. Install to one Hermes gateway in shadow mode and replay saved conversations without double-answering the user.
8. Promote only after zero routing regressions and zero unsupported evidence bindings.
9. Sync the same verified artifact to GitHub, Codex, and both Hermes gateways.
10. Re-run manifest, health, transaction, and real-conversation smoke tests on both gateways.

## Final release criteria

The release is blocked unless all are true:

1. V4 is the only live transaction path.
2. Raw prose is interpreted once by the current caller model; no production keyword router remains.
3. Capability resolution can reject a semantically incompatible caller-selected system.
4. Evidence has applicable fact predicates and exact source anchors.
5. Zero retrieval matches stay zero; no arbitrary record or fact fallback exists.
6. Follow-ups keep the correct calculation but refresh intent, evidence, judgment, and answer.
7. Every requested temporal layer exists in deterministic facts before interpretation.
8. All 13 runtime routes pass `provider-completeness.yaml`; no route remains unavailable, placeholder-backed, or generic `validated-user-chart`.
9. Cross-system corroboration is independent, compatible, purpose-bound, and traceable.
10. Free prose is generated and reviewed by the current model without fixed sentences or model binding.
11. Information-complete requests finish in one turn; pending intake resumes without repeating the question.
12. Public answers show the real chart/hexagram basis, give a direct final answer, and speak ordinary Chinese.
13. Every calculable route passes at least 30 deterministic fixtures; each observation-driven route passes at least 20 structured fixtures.
14. GitHub, Codex, and both Hermes gateways receive one identical verified artifact only after all preceding criteria pass.
