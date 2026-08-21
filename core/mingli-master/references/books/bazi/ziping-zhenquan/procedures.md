---
slug: ziping-zhenquan
file: procedures
---

# 子平真诠 流程声明

> 本 pack 只定义格局法的资料调用流程，不排盘、不手算。

## ZPP-01: 月令用神路由
- **purpose**: 将八字问题路由到月令用神框架。
- **steps**:
  1. 调用排盘工具取得四柱、月令、藏干、透干。
  2. 读取 ZPR-01 与 `chapter-map.md` 的 zp-08。
  3. 判断问题属于善神顺用还是恶神逆用。
- **tool_dependency**:
  - tool.bazi.chart
  - tool.bazi.hidden_stems
- **source_chapter**: zp-08
- **verified**: false

## ZPP-02: 成败救应检查
- **purpose**: 在初定格局后检查成败、救应、变化、纯杂。
- **steps**:
  1. 读取 zp-09 至 zp-13。
  2. 按透干、会支、合冲刑害检查成败与救应。
  3. 输出“原典规则命中 + 不确定项”，不直接下现实断语。
- **tool_dependency**:
  - tool.bazi.relations
- **source_chapter**: zp-09-zp-13
- **verified**: false

## ZPP-03: 相神与杂气核查
- **purpose**: 处理相神、杂气、墓库、四吉四凶的中层判断。
- **steps**:
  1. 读取 zp-15 至 zp-20。
  2. 若月令为辰戌丑未，先走杂气取用。
  3. 若见四吉/四凶，不按名称直接判吉凶，先看是否破格或成格。
- **tool_dependency**:
  - tool.bazi.hidden_stems
  - tool.bazi.relations
- **source_chapter**: zp-15-zp-20
- **verified**: false

## ZPP-04: 十神分格与取运
- **purpose**: 路由到正官、财、印、食神、偏官、伤官、阳刃、建禄月劫各篇。
- **steps**:
  1. 根据已定用神选择 zp-31 至 zp-46 对应章。
  2. 分开读取“本格规则”和“取运规则”。
  3. 大运由工具给出，只解释原典如何看运。
- **tool_dependency**:
  - tool.bazi.luck_cycles
- **source_chapter**: zp-31-zp-46
- **verified**: false

## ZPP-05: 外格/杂格降级策略
- **purpose**: 防止滥用外格、杂格。
- **steps**:
  1. 先确认月令是否无用。
  2. 月令有用时，不另寻外格。
  3. 只有正格无法成立且原文条件满足时，才读取 zp-22 或 zp-47。
- **tool_dependency**:
  - tool.bazi.chart
- **source_chapter**: zp-22, zp-47
- **verified**: false

## ZPP-06: 与现代流派分层
- **purpose**: 避免把徐乐吾评注、现代强弱派、整理者按语混入沈氏原典。
- **steps**:
  1. 输出前检查引用是否来自 47 个核心章节。
  2. 若引用序跋/整理说明，标注为 version_notes。
  3. 若引用徐乐吾或现代命理，只能进入 commentary/modern 层。
- **tool_dependency**: none
- **source_chapter**: all
- **verified**: false
