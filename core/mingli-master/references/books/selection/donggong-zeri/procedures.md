# 董公择日 — Procedures

> D2 可操作流程。所有历算、月建、干支、建除十二值、黄黑道、神煞起例一律交给 `mingli-master.selection.v1`；LLM 只做文本检索、证据整合和安全改写。
> `verified=false` 表示尚未对国图影印逐页校勘。

---

## DP-01 董公月日表检索流程

- **inputs**：`target_date` 或 `candidate_dates`；`event_type`；可选 `place` / `direction` / 当事人四柱。
- **steps**：
  1. 调用 `mingli-master.selection.v1`，取得候选日的农历月建、日干支、建除十二值、节气、方位煞和时辰信息。
  2. 用 `month_branch + day_type + day_branch` 检索 `monthly-day-table.md` 的 144 条日课表。
  3. 读取匹配行的 `summary / recommended_uses / avoid_uses / risk_terms`。
  4. 如需原文引用，转查 `quote-index.md` 中对应 `DG-Q007~DG-Q150`。
  5. 输出格式固定为“《董公选择日要览》民间通书口径：……；文化参考，非事实判断”。
- **outputs**：候选日的本书口径摘要、原文锚点、需避开的风险词。
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：month/*
- **verified**：false

## DP-02 事项类型过滤流程

- **inputs**：`event_type`（嫁娶、起造、动土、入宅、出行、安葬、开张、上任、入学等）。
- **steps**：
  1. 将用户事项映射到 `terms.md` 的用事分类。
  2. 在 `monthly-day-table.md` 中优先检查 `recommended_uses` 是否含对应事项。
  3. 再检查 `avoid_uses` 和 `risk_terms` 是否含对应事项或高风险词。
  4. 同一条同时有宜与忌时，不做一字吉凶，输出“原书对不同干支/小大用法有分歧，需人工复核原文”。
- **outputs**：按事项过滤后的文本证据。
- **tool_dependencies**：无计算；必要时回到 DP-01。
- **source_chapter**：month/*；terms.md
- **verified**：false

## DP-03 官方书交叉流程

- **inputs**：DP-01 的候选结果。
- **steps**：
  1. 对同一日期调用官方择日 reference：`selection/xieji-bianfang-shu`。
  2. 对神煞起例调用 `selection/xingli-kaoyuan`。
  3. 若官方书与本书冲突，主结论采用官方书，本书降为“民间旁证”。
  4. 若官方书暂无覆盖，保留本书为“民间通书异说”，不得升级为确定结论。
- **outputs**：官方口径 + 董公口径 + 冲突裁判。
- **tool_dependencies**：`mingli-master.selection.v1`；相关官方 reference pack。
- **source_chapter**：index.md conflict_policy；rules.md DR-09
- **verified**：false

## DP-04 选时流程

- **inputs**：`target_date`；`event_type`；可选具体时间范围。
- **steps**：
  1. 调用 `mingli-master.selection.v1` 取得目标日十二时辰黄黑道、贵人等。
  2. 查 `quote-index.md DG-Q154~DG-Q156` 和 `rules.md DR-07`，只保留本书关于选时的重要性与口诀证据。
  3. 不手排黄黑道，不自行推贵人登天门。
  4. 输出“日课之外仍需看时辰”的证据层说明。
- **outputs**：选时证据与工具计算结果的组合说明。
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：appendix/zeri-xuanshi-gejue；front/lunlue-shisanze
- **verified**：false

## DP-05 中宫煞与高风险词安全改写流程

- **inputs**：匹配到的月日表条目。
- **steps**：
  1. 如果 `risk_terms` 包含煞入中宫、煞集中宫、白虎、黑煞、重丧、大凶、死、损等词，禁止直接复述凶验为事实。
  2. 改写为：“原书将此日列入某类避忌，并使用某些凶验语”。
  3. 对用户现实决策，补充“现代不应以此作为实际决策依据”。
- **outputs**：安全改写后的文化说明。
- **tool_dependencies**：无
- **source_chapter**：front/lunlue-shisanze；month/*
- **verified**：false

## DP-06 多候选日排序流程

- **inputs**：多个候选日期；`event_type`。
- **steps**：
  1. 对每个候选日运行 DP-01。
  2. 先剔除本书明确标“百事不宜 / 百事皆忌 / 煞入中宫 / 白虎入中宫”的候选，但只在文化口径内表述。
  3. 再按事项匹配度排序：明确宜该事项 > 次吉/小用 > 原文分歧 > 明确不宜。
  4. 最终排序必须与官方书交叉，不得只按本书给建议。
- **outputs**：候选日对照表，含本书口径、官方口径、风险 caveat。
- **tool_dependencies**：`mingli-master.selection.v1`；官方 reference pack
- **source_chapter**：monthly-day-table.md；rules.md
- **verified**：false

---

## 严格禁止

- 不允许 LLM 手算干支、月建、神煞、建除、黄黑道。
- 不允许直接断“某日一定吉 / 一定凶”。
- 不允许复述原书凶验为现实预测。
- 不允许本书覆盖《协纪辨方书》《星历考原》的官方口径。

## D2 状态

- 共 6 条流程。
- 已接入 `monthly-day-table.md` 144 条逐日条目。
- 可作为后续择日 skill 的 procedure layer，但仍需影印校勘和官方书交叉。
