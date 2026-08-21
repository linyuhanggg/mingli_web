# procedures: 葬法倒杖

> 本文件只描述 `mingli-master` 如何读取本 pack；不提供现实墓地操作建议。

## ZFD-P001: Pack Loading Procedure

1. 确认问题属于 `fengshui/阴宅/形峦/穴法/葬法`。
2. 读取 `index.md` 与 `validation.md`，确认 source_status 为 `complete_chapter_set`。
3. 若问题只是术语解释，读取 `terms.md`。
4. 若问题涉及判断，读取 `rules.md` 与 `quote-index.md`。
5. 若需要上下文，回到 `references/fulltext/fengshui/zangfa-daozhang/fulltext.md`。

## ZFD-P002: Fact Layer Requirements Before Interpretation

使用本 pack 解释具体场地前，事实层至少需要：

| fact field | required content |
|---|---|
| site_type | 阴宅/墓地/穴法研究，且合法合规语境明确 |
| terrain_profile | 来龙起止、穴场、山体急缓、凹凸、脉息窟突 |
| water_and_mingtang | 水分水合、金鱼水界、小明堂、前案、堂气 |
| sand_and_guard | 龙虎、四兽、护砂、关锁、外山外水 |
| luopan_or_direction | 坐向/来去水方位；若缺则不能进入理气/向法 |
| evidence | 图片、地形图、现场笔记或专业勘测摘要 |

缺任一关键事实时，输出应停在“需要哪些事实”，不要给“宜用某杖/某葬法”的结论。

## ZFD-P003: Reading Order For Internal Logic

1. `認太極`：先查是否有圆晕、金鱼水界、小明堂（fulltext.md L8-L12）。
2. `分兩儀`：再查凹凸、阴穴阳穴、阴龙阳龙、饶减（L15-L19）。
3. `求四象`：辨脉、息、窟、突（L22-L26）。
4. `倍八卦`：按高山/平地、阴龙/阳龙、脉势/穴象选择细法（L29-L53）。
5. `倒杖十二法`：若问题专问倒杖名目，再映射到顺、逆、缩、离等（L56-L81）。
6. `二十四砂葬法`：只有在具体形类与砂水事实匹配时才引用条目（L84-L136）。

## ZFD-P004: Stop Conditions

- 用户问阳宅、办公室、卧室、开门、灶位：转 `huangdi-zhaijing`、`yangzhai-shishu`、`yangzhai-sanyao`，不要用本 pack。
- 用户问择日、吉时、出行日：转 `selection/xieji-bianfang-shu` 等，不用本 pack。
- 用户只给出生八字或流年：转 bazi，不用本 pack。
- 用户给现实墓地问题但无合法合规与现场事实：只解释文本，不给操作建议。
- 规则依赖 `浮□`、`登□□望龍` 等缺字处：标为校勘待定。

## ZFD-P005: Conflict Handling

- 与《葬书》冲突时：《葬书》作形势源头总纲，本 pack 作穴法细化；并列说明层级。
- 与《撼龙经》《疑龙经》冲突时：先区分寻龙/疑龙/葬法三个功能层，不强行合并。
- 与《入地眼全书》冲突时：标注后世综合书对本法的再解释，不反向改写《葬法倒杖》原文。
- 与玄空理气书冲突时：说明本 pack 是形峦穴法，不解决元运、坐向、飞星、水法计算。
