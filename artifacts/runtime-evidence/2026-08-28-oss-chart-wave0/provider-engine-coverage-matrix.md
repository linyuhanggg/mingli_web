# Runtime Provider / Engine Coverage Matrix

MING-65 Wave 0A inventory, retrieved 2026-08-28. This is an evidence and migration-decision artifact only; it changes no Provider, contract, dependency or Runtime release.

The machine-readable companion is [`provider-engine-coverage-matrix.json`](./provider-engine-coverage-matrix.json). Its `providers` array is the row-level source of truth; this document follows the same 14-entry order and decisions.

## Baseline and enumeration truth

| Item | Evidence |
|---|---|
| Fresh `origin/main` baseline | commit `fdfbee2ead72145e1c67daad6eba7f63cf4b60e6`, tree `e36435068294f9501cc06eb882fd3ddbffa01542`, parent `f1b7026acd461c0de23abf215a74b77468e02e50` |
| Catalog truth | `core/mingli-master/resources/runtime/catalog-v1.json`, SHA-256 `bf389894f19bdf3b4a1ab7ec02334ef2ca0f8947861b4b73f35f78389fc7fc97`, 14 Provider manifests |
| Dedicated completeness matrix | `core/mingli-master/references/matrices/provider-completeness.yaml`, SHA-256 `387208a3bfb85bad18fcc5f4a31c93d1a776b2927963fd4c6b7d2695324526b0`, 13 Providers |
| Algorithm/source matrix | `core/mingli-master/references/matrices/algorithm-source-dependencies.yaml`, SHA-256 `c3889298cd845a1fe447ffcc19b93cffca6fecf3e3daac2ced84444d7a7c1bdb` |
| Signed V53 evidence | `artifacts/runtime-evidence/2026-08-18-bazi-v53-g1/README.md`: verifier `status=ok`, 220 signed files, 14 Providers |

The catalog and signed V53 evidence agree on 14. The older completeness matrix contains 13 and omits `time-check`; that is an audit-coverage gap, not evidence that the Provider is absent. This inventory therefore enumerates from the catalog and records `time-check` separately as catalog/behavior tested but lacking a dedicated completeness entry.

## Fixed layering and labels

The fixed chain is:

`Birth/Event Input → owned Request Compiler + Time/Policy Normalizer → Runtime Provider → licensed pinned OSS Chart Engine → Engine Adapter → per-art Canonical Facts → owned rules/evidence/adjudication/AI`.

Runtime Canonical Facts remain the only external fact truth. Third-party raw objects and JSON stay private behind the Engine Adapter; they are not Backend, Web, LLM, evidence or snapshot contracts. Timezone, coordinates, true-solar-time, Zi-hour, leap-month, epoch, school and horizon policies remain owned and versioned.

Each catalog Provider receives exactly one dominant mechanical-layer decision:

| Label | Meaning |
|---|---|
| `KEEP` | Licensed pinned engine is already isolated behind a stable internal service; retain it. |
| `WRAP` | Current engine remains the default, but direct/raw coupling or an incomplete Canonical Facts seam needs an explicit Engine Adapter. |
| `REPLACE-CANDIDATE` | A licensed frozen comparator is broad enough for a controlled differential trial; this does not approve adoption. |
| `SELF-OWNED` | No qualified mature OSS engine covers the selected convention, or the capability is observation/policy/composition rather than a standalone chart engine. |

Closed count: `KEEP=1`, `WRAP=3`, `REPLACE-CANDIDATE=2`, `SELF-OWNED=8`, total `14`.

Shared calendar use does not determine the Provider label. For example, a self-owned Liuren algorithm may consume the shared `sxtwl` normalizer without becoming an OSS-wrapped Liuren engine.

## Dependency and license evidence ledger

| Component | Current role and evidence | License posture / gap |
|---|---|---|
| `sxtwl@2.0.7` | Shared solar-term, sexagenary and lunar mechanics. Hash `38b24472…` in `core/mingli-master/requirements-runtime.lock`; official [PyPI 2.0.7](https://pypi.org/project/sxtwl/2.0.7/) and [upstream repository](https://github.com/yuangu/sxtwl_cpp). | Upstream metadata reports BSD-3-Clause. Exact artifact is pinned, but no exact-version provenance plus license/NOTICE is preserved beside it locally. Close under P10-000C. |
| `astronomy-engine@2.1.19` | Apparent-solar equation of time and Xingming ephemeris. Local provenance/license: `core/mingli-master/vendor/astronomy-engine-2.1.19/{PROVENANCE.json,LICENSE}`; commit `61dc0702…`, sdist `95b797b8…`; official [v2.1.19](https://github.com/cosinekitty/astronomy/tree/v2.1.19). | MIT, local pin and license verified. |
| `iztro@2.5.8` | Vendored Ziwei mechanics. Local provenance/license: `core/mingli-master/vendor/iztro-2.5.8/{PROVENANCE.json,LICENSE}`; npm artifact `4b8eca32…`; official [tag 2.5.8](https://github.com/SylarLong/iztro/tree/2.5.8). | MIT and artifact verified. Evidence drift: vendor provenance and upstream tag resolve to `9d39f174…`, while `docs/runtime-dependencies.md` names `2dfe3ecb…`. Reconcile documentation in Wave 2 without changing the pinned artifact. |
| `cnlunar@0.2.4` | Selected Xieji tables for Selection. Local provenance/license: `core/mingli-master/vendor/cnlunar-0.2.4/{PROVENANCE.json,LICENSE}`; annotated tag resolves to commit `71e448a3…`; wheel `19689288…`; official [tag 0.2.4](https://github.com/OPN48/cnlunar/tree/0.2.4). | MIT at the exact pinned tag; local pin, reviewed-file hashes and license verified. |
| `lunar-python@1.4.8` | Frozen independent Selection comparator only. Local provenance/license: `core/mingli-master/vendor/lunar-python-1.4.8/{PROVENANCE.json,LICENSE}`; official [v1.4.8](https://github.com/6tail/lunar-python/tree/v1.4.8). | MIT; never a production dependency or classical authority. |
| `qimen-go@4d3f58f…` | Frozen 30-board compatible-projection comparator in `references/fixtures/qimen-go-v51.yaml`; official [repository](https://github.com/deminzhang/qimen-go). | MIT license hash frozen in fixture. Candidate only because center-hosting and school profiles differ. |
| `kintaiyi@68892c6…` | Frozen 72-board raw comparator and 30 matching reference cases in `references/fixtures/kintaiyi-taiyi-v51.yaml`; official [repository](https://github.com/kentang2017/kintaiyi). | MIT license hash frozen. Bureaus 30, 44 and 66 have declared primary-source differences. |
| `liuren-ts-lib@8e9a7b5…` | 720-row Liuren audit witness only; evidence in `scripts/data/LIUREN-720-NOTICE.md`; official [pinned tree](https://github.com/look-fate/liuren-ts-lib/tree/8e9a7b53245c8ae19fa12773087e1f90b3376d5e). | Not admissible as an engine: Apache-2.0 repository metadata conflicts with a pinned README commercial-use prohibition, and audit finds 4 method-label plus 16 transmission disagreements. |
| `liuyao-engine@v0.1.0` | Discovery-only candidate; official [v0.1.0](https://github.com/yaomancy/liuyao-engine/tree/v0.1.0). | Upstream metadata says Apache-2.0, but no local pin, license copy, school mapping or differential corpus exists. Not admissible. |

License status here is an engineering-evidence status, not legal advice.

## Provider inventory

Unless stated otherwise, shortened paths in this section are relative to `core/mingli-master/`; the JSON companion carries every full repository-relative path.

### 1. `bazi` — 八字 — `WRAP`

- Capability: calculation; `natal`, `near_time_personal`; day/month/year/life.
- Implementation: `resources/runtime/providers/bazi.json` → `reading_engine.providers:BaziProvider`; runtime identity `mingli-master.bazi.v7` / `mingli-bazi-pipeline-v1-interpreted`. Paths: `scripts/reading_engine/providers.py`, `scripts/bazi_calc.py`, `scripts/bazi_fact_adapter.py`, `scripts/reading_engine/calendar_core.py`.
- Current engines: `sxtwl 2.0.7` for lunar/Jie/four-pillar calendar mechanics; `astronomy-engine 2.1.19` for apparent-solar equation of time; owned Bazi fact adapter `1.3.0` for static facts and selected profiles.
- Mechanical coverage: calendar normalization, exact Jie boundary, four pillars, lunar/solar-term context, bounded major-luck mechanics, hidden stems, ten gods, element/branch relations, Nayin, growth stages and Xunkong.
- Still owned: timezone/location/coordinate provenance; time-basis and Zi-hour policies; luck convention; Tiaohou, Shensha, source patterns, evidence and adjudication.
- Canonical Facts: catalog declares `fact_contracts.bazi:BaziFactContract`; 18 bound outputs include `four_pillars`, `luck_cycles` and `calendar_normalization`. Gap is the minimum explicit OSS Engine Adapter seam, not the public fact contract. Raw third-party output remains private.
- Tests/fixtures: `references/fixtures/bazi-fortune-v51.yaml`, 30 qualifying + 34 boundary; `audit_bazi_provider.py`, `test_v51_bazi_provider_audit.py`, `test_bazi_fact_adapter.py`, shared completeness test; ready in the 13-Provider matrix.
- License/candidate: current `sxtwl + Astronomy Engine` is the correct default. Astronomy evidence is complete; local sxtwl license/provenance is incomplete. Decision: retain and wrap, Wave 1.

### 2. `fengshui` — 风水 — `SELF-OWNED`

- Capability: `observation_driven_ready`; `spatial_observation`; instant.
- Implementation: `resources/runtime/providers/fengshui.json` → `FengshuiProvider`; `mingli-master.fengshui.v1` / `1.0.0`; paths `providers.py`, `reading_engine/fengshui.py`.
- Current engine and mechanics: owned bounded-observation engine for provenance/scope, compass correction, 24 mountains, chronology/layout graph, selected form/Liqi facts, active rules, conflicts, uncertainty and missing-input closure.
- Still owned: asset/region/quality/correction provenance, property and measurement authority, source profile, applicability and fail-closed missing observations.
- Canonical Facts: versioned output bindings exist, but no manifest `fact_contract`; this observation contract must not be forced through an unrelated chart engine.
- Tests/fixtures: `fengshui-v51.yaml`, 21 qualifying + 7 boundary; `audit_fengshui_provider.py`, remaining-provider replay and completeness tests; ready.
- License/candidate: repository-owned implementation; no mature candidate evidenced for the provenance-bound contract. Decision: remain self-owned; later order 11.

### 3. `fortune` — 日运 — `SELF-OWNED`

- Capability: calculation; `near_time_personal`; day/week.
- Implementation: `resources/runtime/providers/fortune.json` → `FortuneProvider`; `mingli-master.fortune.v6` / `fortune-public-v6-mechanism-stack`; paths `providers.py`, `near_time_fortune_adapter.py`, `calendar_core.py`.
- Current engines: owned near-time adapter `2.2.1` composing unchanged Bazi facts; shared `sxtwl 2.0.7` calendar mechanics.
- Mechanical coverage: natal pillars/day master, active luck cycle, target day and period layers, calendar normalization and mechanism markers.
- Still owned: target date/horizon normalization, active-luck selection, mechanism-stack composition, source-family and user-domain claim policy.
- Canonical Facts: versioned output bindings exist but no dedicated manifest contract. It must consume Wave 1 Bazi Canonical Facts rather than become a second Bazi chart engine.
- Tests/fixtures: `fortune-v51.yaml`, 36 qualifying + 13 boundary; `audit_fortune_provider.py`, dedicated audit and completeness tests; ready.
- License/candidate: inherited shared-calendar evidence gap; no standalone OSS candidate applies to product-policy composition. Decision: self-owned; later order 6.

### 4. `liuren` — 大六壬 — `SELF-OWNED`

- Capability: calculation; `concrete_event`; instant/day/month.
- Implementation: `resources/runtime/providers/liuren.json` → `LiurenProvider`; `mingli-master.liuren.v8` / `mingli-liuren-pipeline-v6-runtime-contract`; paths `providers.py`, `liuren_calc.py`, `liuren_fact_adapter.py`, `calendar_core.py`.
- Current engines: owned `daliuren-daquan-wyg-classical-nine-method-v2`; shared `sxtwl 2.0.7` calendar/Jie mechanics.
- Mechanical coverage: four lessons, three transmissions, method, month general, Xunkong and core/dimension/timing extensions.
- Still owned: event/time policy, month-general/five-rat profile, nine-method and Shehai trace, Guiren profile and retained source disagreements.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`; local fact adapter remains authoritative.
- Tests/fixtures: `liuren-v51.yaml`, 39 qualifying + 8 boundary; `audit_liuren_provider.py`, `test_liuren_fact_adapter.py`, completeness test; ready.
- License/candidate: `liuren-ts-lib` is an audit witness only and is rejected as an engine due to license-text conflict and audited disagreement. Decision: self-owned; later order 7.

### 5. `liuyao` — 六爻 — `SELF-OWNED`

- Capability: calculation; `concrete_event`; instant.
- Implementation: `resources/runtime/providers/liuyao.json` → `LiuyaoProvider`; `mingli-master.liuyao.v1` / `1.4.0`; paths `providers.py`, `reading_engine/liuyao.py`, `calendar_core.py`.
- Current engines: owned Jingfang eight-palace Najia engine `1.4.0`; shared `sxtwl 2.0.7` event calendar.
- Mechanical coverage: primary/changed hexagrams and moving lines, Najia, Shi-Ying, six relatives/spirits, Xunkong/hidden lines, strength/relations, useful-spirit candidates, casting/calendar facts.
- Still owned: cast-method/raw-throw normalization, event time/location, Jingfang profile, useful-spirit and source-conditioned policy.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`.
- Tests/fixtures: `liuyao-v51.yaml`, 41 qualifying + 11 boundary; `audit_liuyao_provider.py`, Liuyao/Meihua replay and completeness tests; ready.
- License/candidate: `yaomancy/liuyao-engine v0.1.0` is exploratory only—no local legal/provenance bundle, school mapping or frozen diff. Decision: self-owned; later order 8.

### 6. `luming-nayin` — 早期禄命（纳音） — `SELF-OWNED`

- Capability: calculation; `natal`; life.
- Implementation: `resources/runtime/providers/luming-nayin.json` → `LumingProvider`; `mingli-master.luming-nayin.v1` / `1.2.0`; paths `providers.py`, `reading_engine/luming.py`, `calendar_core.py`.
- Current engines: owned source-profiled tables `1.2.0`; shared `sxtwl 2.0.7` when birth data need calendar calculation.
- Mechanical coverage: four pillars, all 60 Jiazi Nayin, three-Yuan profiles, selected Taiyuan, source-named Lu/Ma/Gui and source-conditioned patterns.
- Still owned: birth-versus-pillars scope, time policy, disputed Taiyuan/Renyuan profile separation and lookup applicability.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`.
- Tests/fixtures: `luming-v51.yaml`, 99 qualifying + 7 boundary; `audit_luming_provider.py`, dedicated replay and completeness tests; ready.
- License/candidate: only inherited sxtwl evidence gap; no admitted mature candidate preserving the selected early-Luming profiles. Decision: self-owned; later order 10.

### 7. `meihua` — 梅花易数 — `SELF-OWNED`

- Capability: calculation; `concrete_event`, `supplied_chart`; instant.
- Implementation: `resources/runtime/providers/meihua.json` → `MeihuaProvider`; `mingli-master.meihua.v1` / `1.1.0`; paths `providers.py`, `reading_engine/meihua.py`, `calendar_core.py`.
- Current engines: owned explicit-method engine `1.1.0`; shared `sxtwl 2.0.7` calendar.
- Mechanical coverage: upper/lower trigrams, moving lines, primary/mutual/changed hexagrams, body/use relations, seasonal strength, casting and source-conditioned candidates.
- Still owned: explicit casting method, event versus supplied-chart scope, time/location and body/use/source policies.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`.
- Tests/fixtures: `meihua-v51.yaml`, 30 qualifying + 8 boundary; `audit_meihua_provider.py`, Liuyao/Meihua replay and completeness tests; ready.
- License/candidate: inherited sxtwl evidence gap; no frozen licensed comparator mapped method by method. Decision: self-owned; later order 9.

### 8. `physiognomy` — 相法 — `SELF-OWNED`

- Capability: `observation_driven_ready`; `visible_observation`; instant.
- Implementation: `resources/runtime/providers/physiognomy.json` → `PhysiognomyProvider`; `mingli-master.physiognomy.v1` / `1.1.0`; paths `providers.py`, `reading_engine/physiognomy.py`.
- Current engine and mechanics: owned observation engine for scope, neutral visible observations, missing targets, same-capture conflicts, cross-capture variations, source comparison, uncertainty and accepted fact keys.
- Still owned: private asset/capture provenance, neutral vocabulary, quality/occlusion, correction lineage and the prohibition on identity/health/lifespan/future verdicts.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`; deliberately not a chart-engine problem.
- Tests/fixtures: `physiognomy-v51.yaml`, 21 qualifying + 5 boundary; `audit_physiognomy_provider.py`, remaining-provider replay and completeness tests; ready.
- License/candidate: repository-owned. General vision models cannot become this provenance-bound fact authority. Decision: self-owned; later order 12.

### 9. `qimen` — 奇门遁甲 — `REPLACE-CANDIDATE`

- Capability: calculation; `concrete_event`; instant.
- Implementation: `resources/runtime/providers/qimen.json` → `QimenProvider`; `mingli-master.qimen.v1` / `5.2.0`; paths `providers.py`, `reading_engine/qimen.py`, `calendar_core.py`.
- Current engines: owned `shijia-zhuanpan-chaibu-xieji-v1` rotating-plate engine; shared `sxtwl 2.0.7` exact-term calendar.
- Mechanical coverage: Dun/Ju/Yuan, Chief/Director, nine palaces, instruments/wonders/stars/doors/deities, Xunkong/horse and named patterns.
- Still owned: exact-term policy, Chaibu versus incompatible schools, most-recent Jia/Ji Yuan, always-Kun center hosting, deity and named-pattern profiles.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`; candidate raw boards must be projected into these facts and cannot dictate school policy.
- Tests/fixtures: `qimen-v51.yaml`, 30 qualifying + 9 boundary; `audit_qimen_provider.py`, Qimen completion and completeness tests. The exact-commit `qimen-go-v51.yaml` adds 30 frozen compatible projections.
- License/candidate: `qimen-go` is MIT and a qualified comparator, but center-hosting/profile behavior differs. Decision: permit a compatible-subset differential adapter spike only; later order 3.

### 10. `selection` — 择日 — `WRAP`

- Capability: calculation; `calendar_choice`; day/month/year.
- Implementation: `resources/runtime/providers/selection.json` → `SelectionProvider`; `mingli-master.selection.v1` / `1.3.0`; paths `providers.py`, `reading_engine/selection.py`, `calendar_core.py`.
- Current engines: direct `cnlunar 0.2.4` imports for selected Xieji day/hour mechanics; owned `xieji-official-cnlunar-v1` candidate/constraint/lineage/ranking engine; shared `sxtwl 2.0.7` boundary mechanics.
- Mechanical coverage: date and date-time candidates, eligible sets and eliminations, source-profiled day/hour facts, ranking components, lineage and no-valid-candidate closure.
- Still owned: event/action/date-range normalization, hard constraints and participant/direction requirements, lineage separation, ranking and no-guarantee policy.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`; isolate a narrow `cnlunar` projection and keep ranking/policy outside it.
- Tests/fixtures: `selection-v51.yaml`, 30 qualifying + 8 boundary; `audit_selection_provider.py`, source audit and completeness tests; frozen `lunar-python 1.4.8` comparator has 30 engineering cases.
- License/candidate: exact cnlunar tag/artifact/license verified; lunar-python remains comparator only; shared sxtwl evidence gap remains. Decision: retain and wrap; later order 1.

### 11. `taiyi` — 太乙 — `REPLACE-CANDIDATE`

- Capability: calculation; `macro_historical`; year.
- Implementation: `resources/runtime/providers/taiyi.json` → `TaiyiProvider`; `mingli-master.taiyi.v1` / `5.2.0`; paths `providers.py`, `reading_engine/taiyi.py`, `calendar_core.py`.
- Current engines: owned `taiyi-jinjing-annual-yang-board-v1`; shared `sxtwl 2.0.7` lunar-year boundary.
- Mechanical coverage: calendar/epoch/cycle, board and Taiyi position, Wenchang/Tianmu, Shiji/Kemu, host/guest counts and generals, long-cycle deities, predicates and scope contract.
- Still owned: annual macro-historical scope, lunar-new-year boundary, Jinjing Tang-Jiazi epoch, Yang-72 and separate long-cycle profiles, no modern-event verdict.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`; candidate output remains subordinate to selected source/epoch policy.
- Tests/fixtures: `taiyi-v51.yaml`, 30 qualifying + 10 boundary; `audit_taiyi_provider.py`, independent/source/completeness tests. Frozen kintaiyi evidence covers 72 raw boards and 30 matching boards, with explicit differences at 30/44/66.
- License/candidate: kintaiyi exact commit is MIT and qualified only for partial differential work. Decision: permit a partial mechanical adapter trial; later order 4.

### 12. `time-check` — 寻时定盘 — `SELF-OWNED`

- Capability: calculation; `natal`; life.
- Implementation: `resources/runtime/providers/time-check.json` → `TimeCheckProvider`; `mingli-master.time-check.v1` / `time-check-classical-rectification-v1`; implemented in `providers.py` over `calendar_core.py` and Bazi.
- Current engines: owned `candidate-hours-over-bazi v1`; unchanged `BaziProvider`; shared sxtwl calendar through Bazi.
- Mechanical coverage: 12 double-hour candidates, known range/time policy, structured event evidence, bounded rankings/matches, classical rectification status/conclusion.
- Still owned: range/timezone/location/gender normalization, apparent-solar preservation, event-evidence schema, scoring/negative evidence and unique-candidate rectification.
- Canonical Facts: versioned output bindings, no manifest `fact_contract`.
- Tests/fixtures: behavior tests cover 12 candidates, apparent-solar preservation, structured evidence and rectification in `test_provider_time_policy_matrix.py`; catalog/evidence closure tests also cover the route. Gap: no dedicated legal fixture, audit script or `provider-completeness.yaml` entry.
- License/candidate: inherited Bazi/sxtwl evidence gap; no standalone OSS engine applies to this evidence workflow. Decision: self-owned and close the audit gap first; later order 2.

### 13. `xingming` — 七政四余（星命） — `KEEP`

- Capability: calculation; `natal`, `near_time_personal`; instant/day/month/year/life.
- Implementation: `resources/runtime/providers/xingming.json` → `XingmingProvider`; `mingli-master.xingming.v1` / `1.1.0`; paths `providers.py`, `reading_engine/xingming.py`, `reading_engine/ephemeris_core.py`, `calendar_core.py`.
- Current engines: isolated `astronomy-engine 2.1.19` ephemeris service with version/coordinate/observer/digest metadata; owned Xingming `1.1.0`; shared `sxtwl 2.0.7` calendar.
- Mechanical coverage: seven-body ephemeris, four explicitly profiled residual points, classical positions, Ming/Shen and houses, ten-stem transformations, Dongwei Bailiu limits and source patterns.
- Still owned: timezone/WGS84 provenance, tropical/equal-house/topocentric profiles, residual points, transformations, limits and source applicability.
- Canonical Facts: internal engine schema `mingli-ephemeris-v1` and versioned output bindings already isolate the third party; only a manifest `fact_contract` is missing.
- Tests/fixtures: `xingming-v51.yaml`, 30 qualifying + 30 boundary; `audit_xingming_provider.py`, replay/completion/completeness tests; ready.
- License/candidate: Astronomy Engine is MIT, pinned and fully evidenced. Decision: keep the service and engine unchanged; later order 5 only for typed catalog contract.

### 14. `ziwei` — 紫微斗数 — `WRAP`

- Capability: calculation; `natal`, `near_time_personal`; month/year/life.
- Implementation: `resources/runtime/providers/ziwei.json` → `ZiweiProvider`; `mingli-master.ziwei.iztro` / `1.2.0+iztro-2.5.8`; paths `providers.py`, `ziwei_fact_adapter.py`, `ziwei_runtime.js`, `calendar_core.py`, vendored `iztro.min.js`.
- Current engines: vendored `iztro 2.5.8`; owned fact adapter `1.2.0`; shared `sxtwl 2.0.7` calendar.
- Mechanical coverage: Ming/Shen, twelve palaces, stars, four transformations, major limits and annual/month temporal layers.
- Still owned: birth/time/location/gender normalization; `fixLeap`, `dayDivide`, `yearDivide`, `horoscopeDivide`, `ageDivide`; Zi-hour policy; school warnings, source patterns, candidates, evidence and adjudication.
- Canonical Facts: catalog declares `fact_contracts.ziwei:ZiweiFactContract`; raw iztro astrolabe/horoscope objects remain private. Gap is making that boundary explicit and reconciling provenance documentation drift.
- Tests/fixtures: `ziwei-v51.yaml`, 32 qualifying + 32 boundary; `audit_ziwei_provider.py`, dedicated audit/adapter/completeness tests; ready.
- License/candidate: iztro is mature, MIT, vendored and hash-pinned; no replacement rationale. Decision: retain and wrap, Wave 2.

## Minimum Wave 1 / Wave 2 adapter boundaries

### Wave 1 — Bazi

The owned input is the normalized instant with IANA timezone; location/WGS84 coordinates plus provenance when the selected policy requires them; `time_basis_policy`; `zi_hour_policy`; gender when luck direction is requested; or validated explicit four pillars for static scope.

Only the minimum values required for the pinned `sxtwl` calendar basis and Astronomy Engine equation of time cross into the private engine seam. The private outputs are lunar date, Ganzhi/four-pillar mechanics, solar-term/Jie context, equation-of-time value and engine provenance. A private `BaziEngineFactsV1` projection should contain:

- `calendar_normalization`
- `four_pillars`
- `lunar_date`
- `solar_term_context`
- `boundary_trace`
- `engine_provenance`

Hidden stems, ten gods, elements/relations, Nayin, growth stages, Xunkong, San Yuan, luck convention/timing, Tiaohou, Shensha, source rules, evidence and adjudication stay owned after the adapter. Existing `BaziFactContract` remains the sole public fact contract.

### Wave 2 — Ziwei

The owned input is normalized birth instant/timezone/location/gender; time-basis and Zi-hour policies; the fixed `fixLeap=true`, `algorithm=default`, `yearDivide=normal`, `horoscopeDivide=normal`, `ageDivide=normal` profile; `dayDivide=current` for midnight or `forward` for late-Zi-next-day; and requested life/year/month horizons.

Only minimal date/time-index/gender/options enter iztro. Its astrolabe/horoscope object remains private. The adapter continues to emit `ZiweiFactContract` fields for Ming/Shen, palaces, stars, Sihua, major limit, annual/month layers, engine provenance and rule profile. Source-conditioned patterns, interpretive candidates, school warnings, evidence and adjudication remain owned.

No iztro raw JSON or JavaScript object may enter Backend, Web, LLM, evidence or snapshots.

## Later order and open gaps

After Wave 1 Bazi and Wave 2 Ziwei:

1. Selection: isolate direct cnlunar imports and declare typed facts.
2. Time-check: add legal fixture, dedicated audit, completeness entry and typed facts.
3. Qimen: controlled qimen-go compatible-subset differential spike.
4. Taiyi: partial kintaiyi differential spike preserving 30/44/66 source differences.
5. Xingming: keep engine; add only catalog-declared typed facts.
6. Fortune: bind explicitly to Wave 1 Bazi facts.
7. Liuren: type current facts; external table stays a witness.
8. Liuyao: type facts; independently pin/diff any future candidate.
9. Meihua: type casting-method facts; no admitted candidate.
10. Luming/Nayin: type source-profiled facts; no admitted candidate.
11. Fengshui: type observation facts without inventing an engine dependency.
12. Physiognomy: type observation facts while preserving privacy/uncertainty gates.

Cross-cutting gaps:

- Preserve exact-version sxtwl provenance and license/NOTICE locally.
- Reconcile the iztro commit stated in `runtime-dependencies.md` with the vendored provenance/upstream tag.
- Twelve Providers lack a manifest-declared dedicated `fact_contract`; follow the order above.
- Candidate labels authorize differential evidence only, never automatic adoption.
- P10-000C must retain only redistributable or project-authored goldens and bind each external artifact to version, hash, license and NOTICE evidence.
