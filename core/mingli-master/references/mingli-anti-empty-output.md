# Mingli anti-empty output rule

This reference captures the user's correction from the July 2026 session: the issue was not only monthly fortune. It is a global `mingli-master` output problem.

## Core lesson

For all mingli answers, do not produce technically valid but generic text. Gate labels and fact-layer blocks can pass mechanical checks while still being useless to the user.

**Specificity is not noun density.** Listing contracts, transfers, cars, repairs, family, sleep, and messages does not make a reading specific. If those nouns cannot be traced to the user request, verified context, deterministic fact layer, or a named source rule, they are unsupported scene invention.

**Warmth is not vagueness.** A human answer explains the supported mechanism in language the user can understand, responds to the actual question, and is honest about resolution. It does not invent an event, flatter the user, or hide weak evidence behind soothing language.

Bad pattern:
- `稳住`
- `适合推进`
- `注意沟通`
- `现金流有压力`
- `别硬刚`
- `少冲动`
- `有机会但容易卡`

These phrases are only acceptable when attached to a concrete object, action, and timing/trigger.

## Scope

Applies to the whole `mingli-master` skill:
- 日运 / 月运 / 流年
- 财运 / 事业 / 感情
- 合盘 / 婚恋判断
- 买车买房 / 资产问题
- 短事占 / 合作谈判
- any casual `算一下/看看运势/这个怎么样`

Do not treat it as a `monthly fortune`-only rule.

## Do not overfit or scatter across domains

the user corrected the opposite error too: specificity does not mean forcing every answer into her snack-shop / 抖店 / 拼多多 / SKU / 库存 context.

Mingli inference remains open-domain, but a single answer must not enumerate the whole open set. Possible domains include:
- money, cash, debt, payment, reimbursement, purchase, deposit, refund
- work, business, platform, client, supplier, colleague, project
- relationship, partner, friend, family, intermediary
- car, parking, insurance, repair, traffic, scratches
- home, renovation, property, water/electricity, delivery, keys
- travel, route, hotel, flight, delay, documents
- health state, sleep, stomach, mouth ulcers, headache, shoulder/neck
- contract, signature, message, phone call, account, password
- random errands and small operational delays

Use the user's known context only when it is part of the current query or the user explicitly asks to apply it. Do not make it mandatory. For a broad daily question, stay at the whole-period mechanism level unless the user selects a domain. Omit unsupported domains rather than choosing one for variety.

## Private reasoning transformation

For every practical claim, resolve these items internally. They are an evidence graph, not a public-output template or required sentence order:

1. Signal: what in the fact layer triggered it.
2. Mechanism: how natal structure and current transit/lesson/hexagram interact.
3. Applicability: which classical rule applies to this exact chart, season, layer, and question.
4. Claim boundary: what can be judged, what remains unresolved, and which tempting scene is unsupported.
5. Timing/trigger: only when the fact layer distinguishes a real window or trigger.

Diagnostic rule: a slogan with no chart/lesson mechanism is empty; a cluster of unrelated scene nouns is invented specificity. A useful sentence answers the question and makes its reasoning traceable to the current facts and applicable evidence. Advice is optional and never substitutes for judgment. Do not store a “good sentence” here, because examples tend to become the next template.

For daily fortune v6, preserve evidence dependence:

- read the natal baseline, active major luck, target year/month/day, and Tiaohou before interpreting a label;
- several relations produced by one transit branch remain one dependency group, not independent confirmation;
- queried-hour facts are optional and do not force morning/afternoon/evening prose;
- no ten god, relation, or Shensha promotes a concrete life domain by itself.

For every formal system, preserve source dependence too:

- Current validated facts come first; without them the only valid state is `missing_fact_layer`, not a vague reading.
- Run the current `reading_source_plan.py` after those facts, then compile `reading_evidence_bundle.py` from the exact query, facts, and plan before interpretation.
- A book title in prose is not proof that its rule was consulted. Manual browsing, index-only reads, stale reads, and a bundle from another chart are not evidence.
- Put the compact system chart before judgment: `四柱/命盘`, `卦象`, `课象`, `盘面`, `候选日课`, or `宅局事实`.
- If the chart was supplied by the user and only structurally validated, show the matching `未复算` status and never imply independent calculation.

## Final-answer generation

For the user-facing answers:
- Make the actual answer easy to find; a hard verdict or score is optional, not a required opener.
- Give the strongest current mechanism and only the qualifications that materially change it; do not label them with fixed headings.
- Express uncertainty in ordinary language chosen for this reading. No phrase such as `更像`, `其次`, or `少量可能` is mandatory.
- Apart from `【玄枢｜MINGLI】`, the model must derive wording, order, rhythm, and sentence count from the current calculation/hexagram and user question. Do not use stored scripts, fixed three-part structures, or examples as fill-in-the-blank text.
- Keep audit labels private for quick daily chat, but show its compact `时势` basis before judgment. Public calculation evidence is not an internal tool report.
- Formal deterministic work always shows the appropriate compact chart first, then the source-backed judgment. Hiding the calculated chart and replacing it with smooth prose is an anti-empty failure.
- A Da Liu Ren money/timing answer is empty unless it links the judgment to the current妻财 position and旺衰, three-transmission process, and a supported迟速/应期 rule. Naming three books without using a rule from them is also empty.
- If the answer could apply to any random person, rewrite before sending.
- If the answer names scenes the facts never supplied, remove them before sending.
- If a broad daily answer discusses one unsupported scene, remove it and return to the supported whole-period tendency.
- Name a day phase only when queried-hour facts materially distinguish it; merely saying `上午/下午/晚上` is not evidence linkage.
- Do not invent a numeric fortune score or certainty claim when the fact contract emits neither.
- Match the query's `今天/明天` to the calculated target date and the public wording. If the user discloses distress, acknowledge it directly without claiming the chart proves the feeling.
- If it resembles a recent public fortune in meaning, recompute from the fresh primary signal; do not merely replace a few words.
