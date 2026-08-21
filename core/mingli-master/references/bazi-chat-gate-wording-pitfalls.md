# Bazi chat answer gate and wording pitfalls

Use this when producing concise Chinese chat answers for 八字流年、合盘、感情、婚恋趋势, especially after running `scripts/gate_check.py --mode answer`.

## Gate-sensitive wording pitfalls

The gate checker is literal. Avoid accidentally triggering unrelated system gates:

- Do not use `伏吟` casually in bazi answers. The gate no longer treats the bare word as Qimen intent, but plain chat is usually clearer with `同柱重复`, `日柱重复`, or `伴侣宫被重复激活`.
- Do not use formal selection/date language such as `择日`, `最好日期`, `黄道`, `宜忌`, `吉时`, `选日子`, or `推荐某日` unless a complete selection fact layer is present. For year-level bazi use `年份趋势`, `窗口`, `年份气势`, `不定具体日子`.
- If answering bazi only, first run or verify the executable adapter. Keep the private fact layer explicitly bazi-shaped: `Fact tool: mingli-master.bazi_fact_adapter <version>`, its actual `fact_layer_status`, available `calendar_normalization`, `四柱`, `藏干 hidden_stems`, `十神`, `seasonal_tiaohou_profile`, and the permitted 大运/流年 scope.
- The calendar_normalization phrase should be one compact sentence containing: civil birth time, conversion to lunar date, ganzhi/four pillars, solar-term context, timezone/location or true-solar-time note.

## Chat answer pattern for relationship questions

Start with the direct conclusion, then give the key evidence, then practical interpretation. Keep source labels compact but present:

```text
结论：...
【问题分类】八字...
【事实层】Fact tool: mingli-master.bazi_fact_adapter <version>; fact_layer_status=<actual status> ... available calendar_normalization ... 四柱 ... 藏干 hidden_stems ... 十神 ... seasonal_tiaohou_profile ... permitted 大运/流年口径...
【文本依据】...
【综合判断】...
【边界与版本说明】...
```

For iMessage-style answers, it is acceptable to omit long pack explanations, but keep the gate-critical labels and fields.
