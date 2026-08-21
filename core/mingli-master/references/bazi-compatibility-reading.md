# Bazi compatibility / relationship matching reading

Use when the user gives two birth profiles and asks for 性格面貌、合盘、匹配度、适不适合、感情/婚姻匹配.

## Scope

This is a bazi relationship-compatibility reading, not wedding date selection and not a guarantee of relationship outcome. If the user asks for a specific wedding/engagement date, switch to the selection workflow. If the user asks for exact marriage year/timing, switch to bazi marriage-year or luck-cycle workflow.

## Fact layer

Required inputs:
- Both persons' sex/gender convention if relevant.
- Birth civil date/time, birthplace/timezone, and calendar type.
- Calendar normalization for both: lunar date, leap-month status, solar-term month boundary.
- Four pillars, hidden stems, ten gods relative to each day master, na-yin if used.
- Seasonal profile / 寒暖燥湿 / 调候 markers for both.
- True-solar-time policy and boundary risk statement. If true-solar-time correction does not change the hour branch, say boundary risk is low; if it may change the hour branch, stop or present both candidates.

If a full bazi adapter is unavailable and a generic calendar helper such as sxtwl is used, label it clearly as a local deterministic calendar adapter and include the missing pieces you derived or did not derive. Do not overstate accuracy.

## Classical packs

Load bazi/sanming-tonghui and bazi/yuanhai-ziping for 子平骨架. Add qiongtong-baojian when seasonal cold/dry/hot/wet balance materially affects personality or complementarity. Add ziping-zhenquan only if格局成败 is central.

## Interpretation sequence

1. Lead with a direct practical conclusion and an approximate compatibility score.
2. Present compact fact layer for both charts.
3. Read each person separately:
   - day master + month command + dominant elements;
   - visible ten-god pattern;
   - temperament, emotional style, conflict style;
   - 面貌气质 only as traditional symbolic tendency, not a factual claim.
4. Read pair dynamics:
   - same/different day master element and value alignment;
   - spouse-star / relationship-star resonance;
   - branch combinations, clashes, harms, punishments involving day/hour branches;
   - elemental complementarity and 调候互补;
   - likely attraction point and likely repeating conflict.
5. Score by domains rather than one vague score: attraction/emotion, communication, real-life/career/resources, family/marriage, daily intimacy.
6. End with executable relationship advice: what each person should do differently, what agreements to put in writing or discuss explicitly.

## Common pitfalls

- Do not call it formal 合婚择日 unless selection facts are present.
- Do not infer a guaranteed marriage, breakup, cheating, illness, or fertility outcome from natal compatibility alone.
- Do not let神煞 dominate; use them only as secondary color if explicitly needed.
- Do not hide the source limits: interpretation is uncalibrated unless there are known life events or relationship history to validate against.
- For iMessage/WeChat, avoid a giant formal report when the user asks casually; still include the required labels compactly enough for the gate.

## Output skeleton

```text
结论先说：两人属于 <轻松/互补中带冲/强吸引强消耗/...>，综合匹配度约 <score>/100。
【问题分类】八字本命性格与合盘匹配，不做具体择日/不判断必然结果。
【事实层】Fact tool: <adapter>; Rule profile: 子平八字；<person A chart facts>; <person B chart facts>; true-solar-time boundary risk: <low/medium/high>。
【加载的古籍包】bazi/sanming-tonghui、bazi/yuanhai-ziping、<optional>。

女/甲方性格与面貌气质：...
男/乙方性格与面貌气质：...
两人吸引点：...
主要冲突点：...
感情匹配：...
沟通匹配：...
现实与事业匹配：...
家庭与婚姻匹配：...
亲密吸引与日常匹配：...
最实用建议：...
【准确度/校准状态】...
【边界与版本说明】...
```
