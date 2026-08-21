# Tool Adapters

This skill is a corpus and evidence router. It must not hand-calculate charts, plates, lessons, calendars, directions, or astronomical positions. Use this file when a user request needs deterministic facts before classical-text interpretation.

## Adapter Contract

Every deterministic tool output should be treated as the fact layer and should include:

```json
{
  "adapter": {
    "name": "tool or library name",
    "version": "tool version or commit",
    "license_status": "verified | unverified | noncommercial | agpl | user_provided",
    "rule_profile": "school or calculation convention",
    "generated_at": "ISO-8601 timestamp"
  },
  "input": {
    "raw_user_input": {},
    "normalized_input": {},
    "timezone": "IANA timezone when relevant",
    "location": "birthplace, event place, property place, or observation place",
    "missing_or_ambiguous": []
  },
  "calendar_normalization": {
    "civil_datetime": "original Gregorian/civil datetime with timezone",
    "location": "place and longitude/latitude when needed",
    "lunar_date": "Chinese lunar date, including leap-month status when relevant",
    "ganzhi": "year/month/day/hour ganzhi or system-specific day/hour stems/branches",
    "solar_terms": "jieqi boundary and month-switch context when relevant",
    "true_solar_time": "value/policy when relevant"
  },
  "output": {},
  "warnings": [],
  "trace": []
}
```

Rules:

- Prefer JSON stdout and logs on stderr.
- Preserve the adapter name, version, timezone, location, and rule profile in the final answer.
- Never silently mix outputs from two adapters with different rule profiles.
- If the output is user-provided, label it `license_status: user_provided` and do not claim tool verification.
- If the adapter license is unclear, use it only as a design reference until the license is reviewed.
- Any time-based calculation must expose a `calendar_normalization` block or equivalent fields. Raw Gregorian/civil time is only input; it is not a traditional fact layer until converted to lunar date, ganzhi, timezone/location, and solar-term boundary where relevant.
- A bare calendar anchor is not a fact layer. Lunar date, weekday, ganzhi, na-yin, or another system's partial output may be recorded under `trace`, but it is incomplete unless the system-specific required fields below are present.
- If the fact output is incomplete, the final answer must stop at "missing fact-layer outputs" and must not choose a day, rank candidates, declare good/bad luck, or interpret a chart/plate.
- For divination, a time anchor plus hand arithmetic is not a fact layer. Meihua and six-line answers require `tool.divination.qiguagua` output or user-provided hexagram facts before interpretation.

## Installed Bazi Adapter

The skill bundles `scripts/bazi_fact_adapter.py`. For every Bazi image, chart, explicit four-pillar input, or civil birth-data input, read `references/bazi-input-and-image-gate.md` and use this script before interpretation. `vision/OCR is transcription only` and must never be treated as adapter output.

Two fact scopes are intentionally distinct:

- `pillars` mode returns `validated_user_provided_four_pillars`. It validates the four Jiazi and deterministically derives static fields, but it does not verify the birth calendar or calculate luck timing. It is valid only for `fact_layer_scope=natal_static`.
- `birth` mode returns `calculated_natal_chart_from_birth_datetime`. Under its declared local-civil-time/Jieqi/major-luck profile, it supplies calendar normalization, static chart fields, and luck cycles.
- `birth` mode preserves reviewed IANA zones for mainland China, Hong Kong,
  Taiwan, Singapore, Malaysia, and Japan. Solar-term instants are converted
  from the dependency's UTC+8 astronomical build into the declared local
  timezone. Country-only locations spanning several zones remain blocked, and
  true-solar-time correction remains a separately declared policy.

If image pillars and birth-mode pillars disagree, the adapter returns `conflict_birth_data_vs_supplied_pillars` with a nonzero exit code. This is a hard stop.

## Installed Da Liu Ren Adapter

The skill bundles `scripts/liuren_fact_adapter.py`. Read `references/liuren-casting-gate.md` before using it. `cast` mode converts a China-standard civil datetime to lunar date, four pillars, surrounding solar terms, and month general, then builds the heaven/earth plate, four lessons, three transmissions, heavenly generals, and rule-profile trace. `chart` mode accepts an already verified day/hour/month-general set and rejects an hour pillar incompatible with the day stem.

Three transmissions are calculated by the local `classical_nine-method_algorithm` under rule profile `daliuren-daquan-wyg-classical-nine-method-v2`: 贼克、比用、涉害、遥克、昴星、别责、八专、伏吟 and 反吟 each have an auditable branch. 涉害 records every traversed ground branch, lodged stem, depth, 孟仲季 tie-break, and 复等 fallback. The adapter vendors the Apache-2.0 `look-fate/liuren-ts-lib` 60x12 table at fixed commit `8e9a7b5` only as a cross-check witness. A full audit finds four method-label disagreements and sixteen transmission-result disagreements; the table never overrides the classical calculation. Normal casts embed only the audit counts; use `python3 scripts/liuren_fact_adapter.py audit-table` for the full 720-record disagreement list.

柔日别责 has two explicit profiles because the body text and its `存疑` note differ: default `daliuren-daquan-body-branch` takes the forward trine branch itself; `daliuren-daquan-upper-over-branch` takes the god above that branch. The selected profile and alternate result are always emitted under `rule_profile`, `selection_trace`, and `conflicts`.

Default heavenly-general profile is `official-corrected`, using the 《协纪辨方书》阳/阴贵人 split cited by the 《六壬大全》四库提要. `traditional-common` is available only for reproducing the book's inherited common profile. Profile changes may alter heavenly generals but must not alter the plate, four lessons, or three transmissions.

## Offline User-Provided Chart Validator

The skill retains `scripts/structured_chart_adapter.py` for offline migration and
structural regression fixtures. It is not a production provider: the live
`STRUCTURED_SYSTEMS` registry is empty, and every production route must use its
dedicated calculator or bounded observation provider. Legacy payloads emit:

- `fact_layer_status=validated_user_provided_chart`
- `fact_layer_scope=supplied_facts_only`
- adapter `mingli-master.structured_chart_adapter`
- rule profile `user-provided-no-recalculation`

This status never proves calculation or image transcription and cannot be
promoted into a live V4 reading. In particular, Fengshui and Physiognomy legacy
payloads fail with a dedicated-provider-required error.

Physiognomy uses `mingli-master.physiognomy.v1`. The current vision-capable
caller may transcribe neutral visible observations, but the provider neither
decodes nor fetches images. It accepts only a strict `physiognomy_spec` with
hash-bound private asset metadata, semantic region anchors, capture quality,
uncertainty, and correction lineage. Private subject/asset/capture identifiers,
hashes, anchors, and transaction protocol fields remain in the private record;
the public basis receives only safe visible facts and source-comparison scope.

```bash
python3 scripts/structured_chart_adapter.py \
  --system divination/meihua \
  --file /tmp/user-chart.json \
  --output /tmp/mingli-facts.json
python3 scripts/adapter_validate.py --system divination --file /tmp/mingli-facts.json
```

## System Requirements

| System | Required fact output | Minimum inputs | Classical packs to load after fact layer |
|---|---|---|---|
| `bazi` | calendar_normalization, Four pillars, 藏干, 十神, 纳音, 节气换月/月令, seasonal profile, 寒暖燥湿/调候 markers, 大运起运, 流年 when needed | birth date/time, sex/gender convention, birthplace/timezone, calendar type, true-solar-time policy | `sanming-tonghui`, `yuanhai-ziping`, then `ziping-zhenquan`, `ditiansui-chanwei`, `qiongtong-baojian` as needed |
| `ziwei` | calendar_normalization with lunar date/leap-month status, 十二宫, 命身宫, 星曜, 四化, 大限/小限/流年 | birth date/time, sex/gender convention, calendar type, leap-month policy | `ziwei-doushu-quanshu`, `taiwei-fu`; add `feixing-ziwei-doushu-yuanzhi` only for observation/borrowed-palace/environment cross-check |
| `xingming` | calendar_normalization, ephemeris source/version, seven observed bodies, four explicitly profiled residual points, 十二宫, 命身度, 十干变曜, 洞微百六限, requested annual layers | birth date/time, IANA timezone, named location, WGS84 longitude/latitude and coordinate source | `guotian-jing`, `xingxue-dacheng`; `xingming-suyuan` only as bounded cross-book interpretation evidence |
| `divination` | calendar_normalization, 卦象, 动爻, casting_method, 本卦/互卦/变卦 for梅花; 世应, 六亲, 六神/六兽, 纳甲 if六爻 | question, casting method, date/time, raw throws, user-provided hexagram, or `tool.divination.qiguagua` generated hexagram | `zengshan-buyi`, `bushi-zhengzong`, `meihua-yishu` |
| `san-shi/liuren` | calendar_normalization, 天地盘, `four_lessons`, `three_transmissions`, `heavenly_generals`, `month_general`, `day_hour`, 旬空, rule profile, conflicts | one concrete question, date/time, place/timezone, Zi-hour and guiren conventions | first read `liuren-casting-gate.md`, run `liuren_fact_adapter.py`, then load `daliuren-daquan`, `liuren-zhiyin`, `liuren-miben` |
| `san-shi/qimen` | calendar_normalization, 局数, 值符值使, 九宫, 星门神仪, 旬空, 格局 flags | date/time, place/timezone,飞盘/转盘/时家 profile, question/use case | `qimen-dunjia-tongzhi` |
| `san-shi/taiyi` | calendar_normalization, 太乙盘, 入局/局数, 太乙所在, 主客算, 始击/文昌/天目/客目 where used | date/time, scope, method profile | `taiyi-shenshu` |
| `selection` | calendar_normalization, calendar candidates,建除,神煞,黄黑道,宜忌,conflicts; then apply event-specific required fields from `references/matrices/selection-fact-layer-profile.yaml`; for travel add 驿马/天马, 往亡/归忌, 四离四绝/杨公忌, 黄道吉时 | date range, place/timezone, action type, user constraints; travel direction when judging 方位避忌; sitting/direction for construction or burial direction checks; participants' bazi for couple-specific wedding selection | `xieji-bianfang-shu`, `xingli-kaoyuan`, then `yuqia-ji`/`donggong-zeri` as comparison |
| `fengshui` | caller-supplied observations with asset hash/region/quality/uncertainty provenance; explicit compass correction; 24 mountains; separate form facts; measured-door-origin Bazhai correspondences; provenance-bound layout resets; exact active rule ids | `chart_data.fengshui_spec` with property scope, selected `form`/`liqi` subprofiles, declared `requested_form_variables`, measurements, declared sitting/facing, chronology, hash-pinned image assets/annotations and a measurement/observation-bound layout graph | form: only source rules activated by actual observations within the declared property scope; Bazhai: `huangdi-zhaijing`, `yangzhai-shishu`, `yangzhai-sanyao` as applicable. Xuankong and Sanhe are unsupported and never inferred from period metadata |
| `physiognomy` | caller-transcribed visible region, neutral descriptor, lighting/angle/focus/resolution/filtering/occlusion quality, uncertainty, safe same-capture conflicts, cross-capture non-equivalence, corrections, and exact active terminology/method rule ids | `chart_data.physiognomy_spec` with one intent-bound subject, requested targets, hash-bound private asset metadata or caller-text provenance, and structured observations; provider accepts no raw media | only exact active rules from `liuzhuang-xiangfa`, `shenxiang-quanbian`, and the admitted historical layer of `mayi-shenxiang`; compiled/mixed layers remain non-independent and no subject verdict is permitted |

The Fengshui provider uses the versioned `references/matrices/fengshui-source-tables-v1.yaml`. Raw degrees must already be finite in `[0, 360)`; wrapping is permitted only after a declared signed correction and remains in the trace. The caller may transcribe an image, but every image observation must keep an asset id plus SHA-256, normalized region anchor, enumerated quality and uncertainty. Form completeness is measured against the declared requested variables. Layout nodes and edges accept only the observation kinds authorized by the layout contract; road/water/terrain observations cannot stand in for room, partition or door-layout provenance. An unmeasured partition door blocks only a selected Liqi calculation, not a form-only request. Bazhai starts only from an explicitly measured entrance/door trigram. If a declared orientation disagrees with measurement, only an explicit `confirmed_measurement_id` resolves it; the selected measurement then controls calculation and the displaced declaration remains visible as a non-blocking audit record. The provider itself never performs vision and never turns an observation into a吉凶 prediction.

The Physiognomy provider uses the hash-pinned
`references/matrices/physiognomy-source-tables-v1.yaml`. Different captures or
lighting conditions are never auto-equated; contradictory descriptors from one
capture remain blocking until an explicit confirmation or same-capture
correction. Missing regions stay missing. Historical terms explain method and
edition layers only and cannot be converted into claims about a person's
wealth, personality, health, lifespan, identity, or future.

## Near-Time Full-Birth Adapter

`~/.hermes/scripts/fortune_calc.py` is the personal Hermes wrapper around `scripts/near_time_fortune_adapter.py`. It recalculates the complete natal chart from birth datetime, verifies expected pillars, finds the active major-luck cycle for the target date, normalizes lunar/ganzhi facts, and then emits a source-family-aware near-time contract. It does not cast a short-event oracle.

Only the current contract is accepted:

- `schema_version=mingli-near-time-fortune-v2`
- `fact_layer_status=near_time_bazi_transit_facts`
- `contract_version=fortune-public-v6-mechanism-stack`
- adapter `mingli-master.near_time_fortune_adapter` version `2.1.0`
- rule profile `full-birth/transit-mechanism-stack-v4`
- complete `birth_fact_layer`, active luck, `calendar_normalization`, and target-date facts
- `transit_layers` for major luck, year, month, and day
- `mechanism_stack` with explicit dependency groups, primary IDs, and cross-layer complete branch sets
- `nominal_element` never proves transformation; `transformation_status` remains unadjudicated until classical conditions are checked
- optional `hour_profiles`; queried hours never force a public phase narrative
- `public_claim_contract.user_selected_domains_only=true`

Do not print a hand-picked subset of the JSON. The full raw payload and `mingli-fortune-analysis-bundle-v2` must remain available to the Hermes delivery guard. Validate facts with `scripts/adapter_validate.py --system fortune` and compile the analysis bundle with `scripts/fortune_public_brief.py` before interpretation.

After the current fact calculation, run `scripts/reading_source_plan.py` and `scripts/reading_evidence_bundle.py` with the exact query and unchanged facts. Hard applicability precedes ranking. If `window_status` is not `ok`, any required v6 field fails, or the current evidence bundle is incomplete, stop. Public output must be checked with all unchanged artifacts:

```bash
python scripts/gate_check.py \
  --file public-fortune.txt \
  --mode fortune-public \
  --query-file query.txt \
  --facts-file fortune-facts.json \
  --source-plan-file fortune-source-plan.json \
  --evidence-file fortune-evidence.json
```

A nonzero gate result blocks delivery. Legacy contracts are retired. A concrete scene is not authorized merely because it sounds compatible with a ten god or branch relation. Broad daily answers require the correct public time basis, a direct judgment, and at least one current decisive mechanism. They do not require phases, feelings, advice, scores, or a life domain.

## Candidate Adapter Sources

Use these as design or integration candidates, not automatic dependencies:

| Project | Useful pattern | License posture |
|---|---|---|
| [china-testing/bazi](https://github.com/china-testing/bazi) | Explicit relation tables and a second implementation for chart cross-tests | No repository LICENSE file observed; behavior/reference only, do not copy code |
| [jinchenma94/bazi-skill](https://github.com/jinchenma94/bazi-skill) | Input-collection and boundary-case checklist | MIT, but prompt/reference only; not a deterministic adapter |
| [Tianfu Agent](https://destinylinker.github.io/MingLi-Bench/) | Tool visibility tiers, callable reasoning rules, uncertainty at each layer | Public design report and benchmark, not a complete open-source implementation |
| [SylarLong/iztro](https://github.com/SylarLong/iztro) | Mature Ziwei astrolabe generation, mutagen checks, palace relationship helpers, plugin/config support | MIT in GitHub metadata; suitable adapter candidate after version pinning |
| [Ficere/tianji](https://github.com/Ficere/tianji) | Agent-skill packaging, script-first Bazi/Ziwei/name outputs, install and validation workflows | MIT in GitHub metadata; suitable design/reference candidate |
| [DestinyLinker/MingLi-Bench](https://github.com/DestinyLinker/MingLi-Bench) | Separates precomputed chart facts from reasoning benchmark prompts | MIT in GitHub metadata; suitable evaluation reference |
| [Sudo-Biao/suangua](https://github.com/Sudo-Biao/suangua) | Pydantic schemas, calculation/API separation, BM25 retrieval, multi-system app architecture | README says MIT badge but API metadata was not conclusive; verify before copying code |
| [FANzR-arch/Numerologist_skills](https://github.com/FANzR-arch/Numerologist_skills) | Gate Check, deterministic calculation handoff, anti-hallucination SOP | License not asserted in API metadata; use as design reference unless reviewed |
| [weizeW/mingli-skills](https://github.com/weizeW/mingli-skills) | Multi-phase SOP, independent evaluator, cross-system verification matrix | License not asserted in API metadata; use as design reference unless reviewed |
| [ai-freer/fortune-skill](https://github.com/ai-freer/fortune-skill) | JSON-first reports, true-solar-time policy, privacy checks, report QA | PolyForm Noncommercial per README; do not copy into commercial or public redistributable work without a license plan |
| [XiaoChu-1208/bazi-life-curves](https://github.com/XiaoChu-1208/bazi-life-curves) | Multi-school scoring, historical backtesting, falsifiable yearly interpretations, open-phase uncertainty | MIT in GitHub metadata; suitable statistical-calibration reference |
| [Horace-Maxwell/horosa-skill](https://github.com/Horace-Maxwell/horosa-skill) | Broad offline metaphysics skill packaging | AGPL-3.0 in GitHub metadata; do not copy code unless AGPL obligations are acceptable |
| [look-fate/liuren-ts-lib](https://github.com/look-fate/liuren-ts-lib) | Fixed 60x12 three-transmission cross-check witness; never the calculation authority | Apache-2.0 at fixed commit `8e9a7b5`; audit finds 4 method-label and 16 transmission-result disagreements |

## Adapter Use Order

1. Check whether the user already supplied a chart/plate/calendar output.
2. For Bazi input, never accept a screenshot or supplied four-pillar string as self-validating. Run `scripts/bazi_fact_adapter.py` in the matching scope and validate its JSON.
3. For one concrete Da Liu Ren question, normalize question/time/timezone/location through `scripts/liuren_fact_adapter.py` and validate with `adapter_validate.py --system liuren`.
4. If not supplied and no installed adapter exists, request a deterministic tool output.
5. Compile the current source plan and bounded evidence bundle only after fact-layer outputs are fixed.
6. If two adapters disagree, stop and report the disagreement before interpretation.

## Incomplete Fact Handling

If only a partial helper was available, label it explicitly:

```text
Fact status: incomplete anchor only
Available anchors: raw civil time / lunar date / ganzhi / weekday / another system's partial output / manually derived hexagram names / bare "Fact tool" label without fields
Missing required outputs: system-specific adapter fields, such as calendar_normalization+四柱+藏干+十神+节气月令+寒暖燥湿/调候 for bazi, calendar_normalization+十二宫+命身宫+星曜+四化 for ziwei, calendar_normalization+ephemeris positions for xingming, calendar_normalization+qiguagua hexagram facts for divination, calendar_normalization+四课三传 for liuren, calendar_normalization+九宫+星门神仪 for qimen, calendar_normalization+太乙盘+主客算 for taiyi, calendar_normalization+建除+神煞+黄黑道+宜忌 for selection, or observation provenance+compass+form/liqi+exact active source rules for fengshui
Action: no final selection judgment
```

Do not upgrade this into a reading. The correct answer is to ask for, generate, or wait for a complete adapter output.

## Output Trace Requirement

When a tool adapter was used, final answers should include a compact trace:

```text
Fact tool: <adapter name> <version>
Rule profile: <profile>
Input caveats: <missing/ambiguous fields>
Classical packs: <system/slug list>
Confidence: fact=<high|medium|low>, text=<high|medium|low>, interpretation=<calibrated|uncalibrated>
```
