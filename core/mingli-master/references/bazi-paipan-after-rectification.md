# Bazi paipan after birth-time rectification

Use this when the user first sent an app screenshot with a placeholder time, then later provides the corrected civil birth datetime.

## Durable workflow

1. Treat the corrected civil datetime as authoritative over the screenshot placeholder. Do not blend the old chart with the new one.
2. Recompute the full bazi fact layer from scratch:
   - civil datetime, birthplace, timezone
   - lunar date
   - solar-term month boundary
   - four pillars
   - hidden stems
   - ten gods relative to the new day master
   - seasonal_tiaohou_profile
3. If the birth time is near an hour boundary, check approximate true solar time for the birthplace. If true solar time remains in the same two-hour branch, say so and do not overcomplicate.
4. For a full paipan, include dayun direction and start age:
   - Rule source: month pillar as base; 男阳女阴顺行、男阴女阳逆行.
   - Start age: distance to the relevant previous/next solar term divided by 3 days per year.
   - Give approximate start month/year and note software may differ by a few days.
   - If the user reports an app says a very different start age (for example 7岁起 vs calculated 1岁多), do not silently switch. Recompute both previous-term and next-term distances, state the conventional rule used, and explain that multi-year gaps usually mean input/公历农历/虚岁/排盘规则 settings differ. Ask for the app's 大运页 screenshot if they want exact reconciliation. You may provide an “app-aligned年份版” separately, but keep the pillar order and conventional calculation distinct.
5. Keep the answer chart-first. The user usually wants a usable plate, not a long theory report.
5. Keep the answer chart-first. The user usually wants a usable plate, not a long theory report.

## Pitfalls

- If the screenshot had `12:00`, it is often just an app placeholder. Once the user provides a real time, discard the placeholder chart completely.
- Do not claim bazi can infer exact clock minutes. It can usually narrow to a two-hour 时辰; exact minutes need birth certificate/hospital/family record.
- Do not keep the old day master in the interpretation after a date correction. A one-day correction can change the day pillar and all ten gods.

## Compact output shape

Start with:

`排好了。她的准确八字按这个来：年柱、月柱、日柱、时柱。日主是X，女命，现在走X大运。`

Then include the required gate labels compactly: `【问题分类】`, `【事实层】`, `【加载的古籍包】`, `【文本依据】`, chart rows, dayun rows, `【综合判断】`, `【边界与版本说明】`.
