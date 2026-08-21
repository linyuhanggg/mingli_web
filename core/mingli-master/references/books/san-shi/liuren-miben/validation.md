---
slug: liuren-miben
file: validation
validated_at: 2026-07-10
behavioral_evaluation_status: not_run
---

# 《大六壬秘本》Validation

## Source State

**十七卷完整可检索转写已入库；三处 CTP 章界乱码已据 NCL-06572 第 72、179、234 页补齐；尚未完成全书逐页逐行校勘。**

`source_status: complete_text` 只表示书题/目录、卷一至卷十七和录竟款都在可检索全文中。它不表示影印定本完成、每行作者归属确定、每句断语已规则化，或术数预测准确度得到验证。

## Static Validation Results

Run date: 2026-07-10

| check | result | measured detail |
|---|---|---|
| `source-manifest.yaml` parse | PASS | PyYAML parser |
| `test-prompts.json` parse | PASS | Python JSON parser |
| normalized extent | PASS | 5354 lines; 295312 bytes |
| normalized checksum | PASS | `44ea31ef43f874ffc9da03c6ed6c01eee62081db6c2faf11593ec9bbe47847e0` |
| runtime fulltext exact copy | PASS | byte-for-byte equal to normalized source |
| runtime fulltext checksum | PASS | same SHA-256 as normalized |
| manifest local-file checksums | PASS | 8 / 8 local files matched |
| body replacement character | PASS | 0 in L1-L5332 |
| body missing-character placeholder | PASS | 0 in L1-L5332 |
| quote id sequence | PASS | LM-Q001-LM-Q069; 69 unique |
| quote exact hits | PASS | 69 / 69 quotes hit the declared runtime line |
| rule-card schema | PASS | 20 / 20 cards contain source, quote, preconditions, execution, stop/exception, adapter and confidence fields |
| rule quote references | PASS | 45 unique referenced quote ids; 0 missing |
| normalized line ranges | PASS | 0 out-of-range anchors across chapter map, terms, rules, procedures and conflicts |
| structural coverage | PASS | catalog/title + 17 / 17 juan + collation record |
| test prompt structure | PASS | 20 cases: 10 should-trigger, 5 should-not-trigger, 5 edge |
| behavioral blind test | NOT RUN | `evaluation_status=not_run`; no pass rate claimed |
| full scan collation | NOT RUN | only three CTP junctions page-collated |
| deterministic adapter tests | PASS IN SKILL INTEGRATION | this pack only consumes facts; bundled `liuren_fact_adapter` v2 passed 8,640-combination invariants and classical fixtures separately |

## Cangjie Gates

| gate | status | evidence / limitation |
|---|---|---|
| V0 completeness | PASS WITH QUALIFICATION | Complete searchable 17-juan transcription; scan is acquired; full page collation pending |
| V1 location | PASS | Every final rule has normalized line location and one or more quote ids |
| V2 source fidelity | PASS WITH OPEN RISKS | Explicit Jin/copyist/scan layers separated; flattened unattributed commentary remains `mixed_body_commentary` |
| V3 operationality | PASS | 20 cards provide required fields, execution, decision effect and stop conditions |
| V4 lineage boundary | PASS | Pack is independent; no automatic 《大全》/《指南》 override |
| V5 no calculation hallucination | PASS | Actual casting requires deterministic adapter output and trace |
| V6 structure vs extraction honesty | PASS | 17-juan structure is complete; rule extraction explicitly selective |
| V7 conflict preservation | PASS | Volume 13/15 lesson-name conflicts, strength profiles and xingnian variants remain visible |
| V8 small-liuren isolation | PASS | Historical comparison note is preserved in fulltext but no small-liuren execution or routing rule is created |

## Rule Coverage Claim

The pack contains:

- 29 source-bounded terms/aliases;
- 20 executable or gating rule cards;
- 8 named procedures plus stop/output contracts;
- 69 exact short quotes;
- 20 pressure-test prompts;
- a complete 17-juan structure map.

These numbers describe the reference pack artifacts, not “percent of predictions covered.” The following material remains searchable but is not exhaustively carded:

- all month-general and heavenly-general imagery combinations;
- the complete heaven-general x branch and trigram x general object tables;
- every line of the two Hundred-Chapter Songs;
- every specialty saying in the Jade Field Song, Guan Lu Divine Book, Heart Mirror Classic and Three Talents appendix;
- every named spirit table and every historical example.

When an uncarded saying is needed, use `text_lookup_only`, cite its line and source layer, and do not label it a validated rule.

## Behavioral Test Status

`test-prompts.json` has passed JSON/schema inspection only. It has **not** been run through an independent model judge. Therefore:

- no behavioral pass percentage is reported;
- `minimum_pass_rate` is only an acceptance target;
- no prompt is marked empirically passed;
- model behavior must still be checked after the pack is integrated into the main skill.

The future blind run should pay special attention to:

1. whether missing adapter facts stop an actual reading;
2. whether Volume 13/15 lesson-name prose is incorrectly used to generate transmissions;
3. whether strength profiles are silently mixed;
4. whether a single shensha or class deity overrides the main chart;
5. whether “中末总弃” is wrongly generalized beyond shefu;
6. whether uncollated normalized lines receive invented scan pages;
7. whether the L3351 small-liuren comparison creates an unwanted route;
8. whether cross-book disagreement is hidden by an automatic “higher authority.”

## Scan-Collation Status

| body line | restored text role | NCL page | result |
|---|---|---:|---|
| L1592 | Volume 9 song at CTP chapter boundary | 72 | exact restored |
| L3912 | Volume 15 “two matters” commentary at CTP boundary | 179 | exact restored |
| L5158 | Volume 17 punctuation completing a song line | 234 | exact restored |

The normalized audit record is L5335-L5354. No other line has a verified NCL page mapping in this pack.

## Remaining Risks

1. **Full page collation**: 243 scan pages have not been aligned to all 5354 normalized lines.
2. **Flattened layout**: CTP transcription can merge base text, double-line notes, red annotations and marginal notes.
3. **Authorship**: “清·金正音辑” does not make all included works or explanations his original writing.
4. **Volume metadata**: catalog metadata says 20 juan while scan contents and text contain 17.
5. **Lesson names**: Volume 13 and Volume 15 contain conflicting or ambiguous labels; they are disabled for chart generation.
6. **Strength models**: seasonal and two-day/daily profiles coexist and require separately named adapter implementations.
7. **Xingnian models**: multiple cited lineages coexist in L2948; no default was selected here.
8. **Specialty sayings**: many remain only text-indexed; their wording is premodern and context-specific.
9. **Predictive validity**: exact transcription and traceability do not establish statistical accuracy.
10. **Behavioral integration**: no independent blind test has yet evaluated the main skill with this rebuilt pack.

## Acceptance Boundary

This pack is ready for:

- complete-book navigation;
- exact-quote retrieval;
- source-layer-aware comparison;
- conditional imagery lookup;
- five-essentials and process interpretation over verified chart facts;
- specialty routing with explicit uncarded-text status.

It is not:

- a deterministic liuren adapter;
- a full critical edition;
- a proof of predictive accuracy;
- a small-liuren implementation;
- a license to infer chart facts from prose.
