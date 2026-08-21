# 紫微斗数 (ziwei)

## Deterministic calendar boundary

The vendored iztro chart consumes the same
`mingli-calendar-normalization-v2` identity used by Bazi, Fortune, and
Daliuren. The shared result, including full lunar leap-month state and exact
solar-term context, is retained beside iztro's display fields and bound by
`calendar_digest`; the model may not infer or replace calendar facts.

The pinned engine contract is iztro 2.5.8 with the `default` algorithm,
`fixLeap=true`, natural-year horoscope division, nominal-age division, and an
explicit Zi-hour input index. Natal and requested Da-Xian/Liu-Nian/Liu-Yue
palace, star, and four-transformation placements are emitted as facts only.
《紫微斗数全书》 is the primary calculation identity, 《太微赋》 is an
interpretive source after retrieval, and the Republican observational text is
always marked commentary-only; none of these evidence packs replaces the
calculator.

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `ziwei/feixing-ziwei-doushu-yuanzhi` | 華山陳希夷先生飛星紫微斗數原旨 / 斗數觀測錄 | 民国斗数观测法; 十二宫活用假借; 命盘与阴宅、阳宅、相法、村镇/邻里方位互证; 红鸾大耗、天刑巨门等案例旁证 | 基础排盘事实计算; 古法紫微一线原典; 未给完整紫微盘时直接断当前吉凶; 把疾病、死亡、刑讼等案例铁口化 | 116 页 NLC/Commons 影印本已逐页 OCR 校阅，仍属晚近观测/注释层；题名、作者题署与正文《斗数观测录》关系须保守标注。 |
| `ziwei/taiwei-fu` | 太微赋 | 紫微斗数早期纲领与术语溯源; 星曜入庙/失度/落陷的判断口诀; 格局名（如金舆捧栉、玉袖天香、君臣庆会等）的源头 | 排盘事实计算（不替代 tool.ziwei.bindisk）; 紫微星系的完整定义（应回查《紫微斗数全书》卷二）; 流年/大限断语的精细推演（应优先《斗数骨髓赋》） | - 本赋作者与年代尚无定论。 - 通行本与《紫微斗数全书》卷一所载文本逐句比对待补。 - 赋中"七杀临身命加恶杀，必定死亡"等极端断语必须 reframe 为吉凶倾向参考。 |
| `ziwei/ziwei-doushu-quanshu` | 紫微斗数全书 | 紫微斗数排盘安星法（诸星安例、十二宫起例）; 紫微斗数十二宫断法（命/兄弟/妻妾/子女/财帛/疾厄/迁移/奴仆/官禄/田宅/福德/父母）; 紫微斗数赋文（太微/形性/星垣/斗数准绳/发微论/彀率/增补太微/骨髓/女命骨髓） | LLM 直接手工排紫微斗数盘（必须依赖 tool.ziwei.bindisk）; 子平八字推断（紫微斗数与八字系统不同，星曜/宫位 ≠ 干支/纳音）; 铁口断寿、断病、断婚、断子（古书断语含大量铁口断，须严格 reframe） | 维基文库当前目录与 raw/API 仅列卷一至卷三；/卷四 与 /卷之四 返回 404。本 pack 可代表当前三卷本，不可冒称覆盖另本四卷传本。 |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.
