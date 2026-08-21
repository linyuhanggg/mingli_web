# Mingli v6 Champion/Challenger Verification

Date: 2026-07-11

## Compared Versions

- Champion: deployed v5 source commit `45cd32b`.
- Challenger: `rebuild/v6-mechanism-first`, through router commit `1eb1daf`, plus the accuracy-first re-acceptance patches (2026-07-11).
- Production rollback point remains `45cd32b`; Hermes delivery rollback point remains `7fe5dd66c0`.

## Source-vs-runtime status (2026-07-11 fourth-acceptance)

The source skill has been re-verified through FOUR independent audits. The three runtime copies (`~/.codex/skills/mingli-master`, `~/.hermes/skills/research/mingli-master`, `~/.hermes/profiles/liujing/skills/research/mingli-master`) STILL point at the pre-fix `gate_check.py` SHA-256 `8929cedb485f1e35723365e0233892f5c77e35e929d39e6625f13cf1a00eea8f` and were NOT re-synced during the fourth cycle. Sync is intentionally deferred so a subsequent Codex review can decide when the runtime is upgraded. During the 12-replay verification the running Hermes gateway was pointed at the source directory via `MINGLI_SKILL_DIR`; no runtime file on disk was mutated.

Current source SHA-256s (post fourth-acceptance patches):

- `scripts/gate_check.py` = `979db1845c10976a6e43d46e6a73a7771164ec0567b3bbb5a9afb40d377e9451`
- `scripts/adapter_validate.py` = `3ab0d3f21d4d266ea85d0568f78a965369c5c254b16ab907c9520661b5b6cb34`
- `scripts/reading_evidence_bundle.py` = `3a7e8e2929bec6d741e93a4f9b0afeb22ce2639ac3c24b632f4bb62fd56f558e`
- `scripts/near_time_fortune_adapter.py` = `52daeafe2f139586754c349463c2c5233974738f9b2bb0be5bf072ea549f8cdc`

Source `SKILL.md` size: 11,979 bytes (< 12,000). This document does NOT claim `eligible for deployment` or `task complete`; those verdicts remain the responsibility of an independent Codex review after the runtime is synced.

## Verdict

The v6 challenger has improved calculation visibility, source applicability, question relevance, unsupported-claim rejection, and prompt size. This document does not conclude `eligible for deployment`; deployment remains gated on a Codex-driven runtime sync and a downstream re-audit.

This verdict is about execution correctness. It does not establish empirical predictive accuracy.

## Real Regression Case

Fixture: natal `庚辰 / 丙戌 / 己酉 / 丁卯`, 己土 day master, 戌 month command, active `戊子` luck, target `2026-07-11 丙戌`.

V6 applicable evidence:

- 《渊海子平》: `YR-03-02~03` 岁运/流年, `YR-02-20` 旺相休囚, `YH-Q008`.
- 《滴天髓阐微》: `DR-07-03` 岁运合参, `DR-04-01` 寒暖调节, `DT-Q064`.
- 《穷通宝鉴》: `QR-03-07` 三秋己土, `QT-Q034`.

The hard applicability filter excluded unrelated `三春甲木`, `七月丙火`, and longevity material before BM25 ranking.

The historical answer beginning with `白天不算顺` and inventing replies, changed wording, money movement, closing tasks, and chasing responses now fails with:

- `fortune_public_missing_time_basis`
- `fortune_unrequested_specific_domain`
- `fortune_missing_mechanism`
- `fortune_missing_direct_judgment`

A chart-first answer naming the actual target day, 正印, 戌同支, 辰戌冲, and 酉戌害 passes without a score, three day phases, feeling sentence, or mandatory advice. A finance-specific variant passes only when the query itself asks about finance.

## Route Replays

| Case | Challenger result |
|---|---|
| Broad today/tomorrow fortune | V6 facts, applicable evidence, mechanism answer passes; old stock reply fails |
| User-selected daily finance | Domain may be discussed conditionally; payment/receivable event remains unsupported |
| Bazi screenshot | OCR remains transcription only; executable Bazi validation is required |
| Static Bazi career | Compact chart precedes judgment; no luck timing from static pillars |
| User-provided Meihua chart | Structured validation and `未复算` boundary preserved |
| Qimen without a plate | Stops at `missing_fact_layer`; no hand calculation |
| Da Liu Ren concrete event | Complete lesson, three-book evidence, chart-first public gate preserved |
| Negated certainty | `不能据此硬编某件事一定发生` is accepted as a denial, not misread as a prediction |

## Post-Deployment Mechanism Replay

The `2026-07-12 丁亥` replay exposed and then fixed a missing cross-layer structure: transit day `亥`, natal hour `卯`, and transit month `未` form a complete `亥卯未` three-harmony branch set. Near-time adapter `2.1.0` / rule profile `full-birth/transit-mechanism-stack-v4` now promotes that fact to the primary mechanism while recording `nominal_element=木` and `transformation_status=unadjudicated_requires_classical_conditions`. A complete branch set is therefore visible without being mislabeled as proven transformation.

The compact manifest for this fixture is 9,701 bytes. Its primary ID points only to the cross-layer formation, and its members retain their exact natal/transit provenance. The public gate now rejects omission of the primary mechanism, incorrect branch sets, incorrect nominal element or role family, positive or negative unadjudicated transformation claims, direct ten-god-to-scene mappings, reversed five-element relations, and multiple or incorrect month commands.

The production `gpt-5.6-terra` replay reached the API server but the provider returned `429 usage_limit_reached` before its first model response or tool call; the delivery guard correctly returned the fail-closed response. This is an external quota block, not a passing behavioral replay. Two available weaker-provider probes were retained only as adversarial checks: Xiaomi skipped the pipeline and produced unsupported scenes; MiniMax ran the compact pipeline but invented `木泄土`, `酉戌月令`, and unsupported branch relations. The public gate rejected the MiniMax draft and those exact loopholes are now regression cases. Neither weaker model is approved as a production fallback for this skill.

## Size And Runtime

Measured on the real fixture with compact JSON:

| Artifact | V5 | V6 | Result |
|---|---:|---:|---|
| `SKILL.md` | 76,351 bytes | 11,496 bytes | 84.9% smaller |
| Daily route reference | 14,465 bytes | 8,483 bytes | 41.4% smaller |
| V6 facts | n/a | 12,325 bytes | complete natal/transit mechanism facts |
| V6 analysis bundle | n/a | 8,345 bytes | no prose hints or scenes |
| Source plan | n/a | 1,142 bytes | three applicable packs |
| Evidence bundle | n/a | 7,570 bytes | 1,454 rendered evidence characters |

Estimated dynamic quick-lane context for facts + analysis + plan + evidence is 7,575 tokens, below the 8,000-token target. Adapter plus analysis/source/evidence compilation took about 81 ms locally. The quick execution chain uses at most five skill-specific calls.

For transparency, counting the static router and full daily-route reference as well gives an estimated 12,636 tokens. The 8,000 target therefore applies to dynamic reading artifacts, not the complete static skill prompt. Further prompt reduction remains possible, but this is no longer a hundreds-of-thousands-token path.

## Verification Gates

- Source skill: 300 unit/regression tests.
- Skill Creator quick validation: passing.
- Source Python compile: passing.
- Hermes Mingli guard + API suite: 424 tests passing (existing aiohttp warnings only).
- Local scheduled-fortune wrapper/guard suite: 17 tests passing.
- Scheduled v6 guard integration: recomputation, source plan, evidence bundle, public gate, and exact-copy SHA all passed.

## Accuracy Boundary

V6 is more accurate in four measurable senses: correct chart/date facts, correct source applicability, traceable mechanism use, and lower unsupported-event rate. It is not yet statistically calibrated for real-world event prediction. That requires preregistered claims, fixed time windows, confidence buckets, and hit/miss/partial outcomes in `scripts/case_log.py`.

## 2026-07-11 Acceptance-Driven Refactor (Accuracy-First)

A sanitized acceptance replay exposed two blocking gaps in the deployed guard chain:

1. `scripts/gate_check.py` rejected the model's factually-consistent v2 draft (SHA256 `27d09ecb…`) with `fortune_public_missing_time_basis` / `fortune_missing_mechanism` / `fortune_missing_primary_mechanism` / `fortune_missing_directional_judgment`, because the regexes for formation, directional judgment, and ten-god recognition were lexical rather than semantic. Natural-language paraphrases (“亥卯未的完整三合”, “偏忙、偏受外部节奏牵动”, “宜做收口”) failed to match despite matching the fact-side mechanism_stack.
2. `~/.hermes/hermes-agent/gateway/mingli_fact_guard.py` expected `mechanism_stack.dependency_groups` to be exactly the three required transit families, but the skill adapter emitted a fourth `active-timing-layers` entry. This latent mismatch silently replaced the model's genuine passing answer with `DAILY_FORTUNE_BLOCKED_RESPONSE` on the second acceptance replay.

The accuracy-first refactor (Sections 1–10 of `plans/2026-07-11-mingli-v6-mechanism-first-implementation.md`) resolved both:

- `_v6_formation_claims` now accepts curated classical/neutral bridge tokens (`的`, `完整`, `齐见`, `齐会`, `跨层`, `合成`, `构成`, …) between the branch triple and the relation word, but still requires the semantic units (branches / relation / optional element) to match `mechanism_stack.multi_branch_formations`.
- `_v6_mechanism_hits` accepts ten-god aliases (`印星`, `财星`, `官杀`, …) and stem-adjacent variants; a new `fortune_ten_god_fact_mismatch` fires when the text names a wrong ten-god for the target-day stem.
- Directional judgment now recognises polarity terms (positive/negative/mixed) and only ANSWER-level resolution boundaries (`吉凶未定`, `只能判断到…`, `不能据此断`); formation-transformation boundaries and completeness hedges are recorded but do NOT satisfy `direct_judgment`. This is the accuracy-first re-acceptance P0-1 correction to the previous release note, which incorrectly grouped conditional and advisory phrases under a satisfying "semantic group".
- Ten-god scene mapping is now enforced structurally via an allowlist of legitimate ten-god contexts (identity `<干>为<十神>`, position `<十神>临/入/落<位置>`, presence `<命局>有<十神>`, `<五行>归<十神>一类`, negation `不是单看<十神>`, symbolic-with-boundary), plus declarative shortcut and life-scene proximity detectors, plus a strict `mechanism_bridges` schema validated by `adapter_validate.py`. `user_selected_domains_only` no longer grants ten-god causal authorisation.
- New findings: `fortune_stock_scene_leak`, `fortune_overmodern_leak`, `fortune_conflicting_month_command`, `fortune_empty_output`, warning-level `fortune_mechanism_understated`, `fortune_generic_answer_dodge`, `fortune_mechanism_bridge_invalid_schema`.
- `scripts/near_time_fortune_adapter.py::_assert_mechanism_scopes_are_symbolic` fails-fast if any decisive mechanism or formation loses its `_not_specific_event` scope suffix.
- `scripts/near_time_fortune_adapter.py` moves the previously appended `active-timing-layers` entry out of `dependency_groups` into a sibling `active_layer_metadata` object, restoring the exact 3-item `dependency_groups` shape the Hermes guard expects.
- `scripts/reading_source_plan.py` adds a `qiongtong_applicability` block (day_master + solar-term month group → applicable chapter, backed by `references/matrices/qiongtong-applicability.yaml`) and now truly loads the YAML with schema validation, hash-binds it into the plan, and `reading_evidence_bundle._eligible_records()` consumes ONLY the plan's `applicable_chapter` (fact-layer re-derivation removed).
- `scripts/adapter_validate.py` rejects any fact-layer whose `source_tool` is manual/none/human/hand/vision_ocr/llm/gpt/claude, at BOTH top-level and nested `adapter.source_tool`.
- Calendar adapters use the declared `MINGLI_PYTHON` interpreter, or the current interpreter when it is unset. They never switch to a host interpreter implicitly.
- `~/.hermes/scripts/fortune_calc.py` keeps only the fields the Hermes guard actually uses (`delivery_contract.maximum_wording_repairs=1` and top-level `gate_command`); manifest byte size stays comfortably under 12,000.
- New regression corpora: `references/regression/gate-paraphrase-cases.yaml` (updated), and two new audit-driven test files `scripts/test_qoder_audit_findings.py` and `scripts/test_qoder_reacceptance_findings.py` locking every counter-example from both audits as must-fail / must-pass fixtures.

### Post-Fix Sanitized Replay

A daily-fortune fixture was replayed through the production-shaped transaction:

- api_calls=5, tool_calls=5 (skill_view, session_search, `fortune_calc.py --pipeline`, `write_file public.txt`, `gate_check.py`).
- No `date` / `--help` / `skill_manage` prelude.
- The private pipeline artifact remained outside the distributable repository.
- Gate result: `ok: true`, `findings: []`, `public_copy_sha256=b878defedee2a3452234450f0d979dc480e8de2e860d9a9bb7c3318a8b66ca2d`.
- Delivered content SHA256 identical to gate public_copy SHA256 (hash-bound delivery preserved).
- Hermes API mingli guard did not block. Runtime copies (`~/.codex/skills/mingli-master`, `~/.hermes/skills/research/mingli-master`, `~/.hermes/profiles/liujing/skills/research/mingli-master`) were NOT synced during the final-acceptance cycle (see Source-vs-runtime status above). The pre-fix runtime SHA-256 `8929cedb...` remains on all three copies.
- Local suite: 300 unittest cases passing, including the paraphrase-corpus tests and the updated formation/directional/month-command regression cases.

The refactor is textual and structural rather than statistical: it does not change the accuracy of any classical rule, only unblocks factually-consistent natural-language answers that the previous guard chain lexically rejected.
