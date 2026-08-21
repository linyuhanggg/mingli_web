# Bazi monthly fortune chat workflow

Use when the user asks quick monthly fortune such as `这个月运势`, `本月怎么样`, `下个月财运/感情/事业`.

## Route

Treat as `八字月运趋势`, not formal date selection and not divination. Use bazi as the primary system.

After validating birth-mode Bazi facts, run `scripts/reading_source_plan.py --system bazi` with the exact monthly query, then compile `scripts/reading_evidence_bundle.py` from the same facts and plan. The bundle must cover every current `required_rule_files` and `required_quote_indexes` path without loading whole files into model context. Compile `scripts/reading_public_brief.py --evidence-file ...` before drafting and run `gate_check.py --mode reading-public --evidence-file ...` on the exact final copy.

## Fact layer minimum

The private brief, even for a short answer, must preserve these facts:

```text
【事实层】Fact tool: mingli-master.bazi_fact_adapter <version>；fact_layer_status=calculated_natal_chart_from_birth_datetime；先验证缓存输入仍与本次出生资料一致。calendar_normalization：当前civil_time YYYY-MM-DD TZ转农历X月X日，干支X年X月X日，节气X后换X月；四柱：年柱X、月柱X、日柱X、时柱X。藏干 hidden_stems：...。十神：...。seasonal_tiaohou_profile：事实层节气月令为X，寒暖燥湿偏X，调候候选X；本次看大运、流年、月令。
```

Do not send this audit block to the user. Public copy begins with the validated status and a compact `四柱/时势` line before judgment. Do not rely on a generic calendar anchor alone. If using a helper such as `sxtwl`, treat it as calendar normalization support only; the bazi chart itself must be a known validated chart or a proper bazi adapter output.

## Output shape for the user

Make the practical verdict prominent and give concrete, user-situated calls. Do not prescribe a fixed opener or section order; generate the presentation from the month's actual phase changes. A monthly fortune must not read like generic astrology.

Required concrete layer:
- Name the active solar-term month and its effect on the user's known chart/current luck.
- Specificity is not noun density. Do not force the reading into snack shop or business, and do not scatter across money, work, relationship, car, home, health, and documents to raise the chance that something sounds right.
- Use the user's known context only when it is naturally relevant or the chart signal points there. Money, work, relationship, vehicle, home, travel, family, health state, messages/documents, purchases, and legal/contract are a candidate pool for routing, not an output checklist.
- Select one evidence-supported primary lens and at most one secondary lens for the month. Omit unsupported domains.
- Give actionable windows by solar terms or week ranges only when the transit fact layer distinguishes those phases; the number and ordering of windows follow the evidence rather than a fixed quota.
- If money is a supported primary/secondary lens, distinguish opportunity, actual到账, spending/leakage, debt/账期, or resource drag instead of mentioning all of them.
- For work/business, only mention 抖店/拼多多/SKU/inventory/supplier when the user asks about that domain or verified context plus the fact layer supports it.
- For relationship/personality, name the trigger pattern and one concrete action only if relationship is a supported primary/secondary lens.
- Mention ordinary wellness only if it changes behavior; do not fill space with generic health advice.

Forbidden empty phrases unless followed by a concrete noun/action/date window:
- “把事情落规则”, “清账”, “修关系”, “稳住”, “别硬刚”, “注意沟通”, “现金流有压力”, “适合推进”, “少冲动”.

Keep it concise. Avoid a long formal report unless the user asks. If gate labels are needed, keep them private or compressed; do not let the gate-passing block replace the useful answer.

## Hard anti-empty-output gate

Before finalizing a monthly fortune, ask: "Could this answer apply to any random person?" If yes, rewrite. It must contain:
- One primary lens and at most one secondary lens, each traceable to a fact-layer signal and source rule.
- Every published time window or phase marker must be distinguished by the fact layer and tied to a specific behavior change; do not create extra windows to satisfy a quota.
- Actions must follow from the selected lenses, not from a generic advice list. No particular verb or sentence pattern is required.

Reject outputs that mainly say "稳住/推进/注意沟通/现金流有压力/别硬刚/少冲动". Also reject noun-stuffed outputs that rotate through unrelated car/home/document/relationship/body scenes, and over-fitted outputs that force every broad fortune into snack-shop operations.

## Wording pitfalls

- Avoid formal selection words: `择日`, `黄道`, `宜忌`, `吉时`, `最佳日期`, `推荐某日` unless a full selection fact layer exists.
- Say `年份/月令趋势` or `窗口`, not `选日子`.
- If giving intra-month timing, phrase as bazi气势 windows: `小暑后`, `大暑后`, `月底金气渐起`, etc.
- Name the decisive current books and rules naturally in the judgment; do not expose `【加载的古籍包】` or `【文本依据】` audit headings.
- Do not over-explain the method in the user-facing answer. The visible answer should still feel like a chat, with its wording and order generated from the current reading rather than a fixed conclusion-reason-action script.
