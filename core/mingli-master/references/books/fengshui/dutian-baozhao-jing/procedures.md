---
slug: dutian-baozhao-jing
file: procedures
---

# 都天宝照经 流程声明

> 本书含大量龙、水、穴、向、三元、城门、五吉星语汇。reference pack 只定义资料调用流程，不让 LLM 手算。

## DTP-01: 文献问答路由

- **purpose**: 回答“《都天宝照经》如何谈龙、水、三元、城门”的文献层问题。
- **steps**:
  1. 先读 `chapter-map.md` 确定上中下篇范围。
  2. 从 `terms.md` 定位术语。
  3. 读取 `rules.md` 中对应规则。
  4. 用 `quote-index.md` 的短引做证据，不直接长引原文。
- **tool_dependency**: none
- **source_chapter**: all
- **verified**: false

## DTP-02: 龙穴水口材料整理

- **purpose**: 把用户给出的地形材料整理为可人工或工具核查的结构化输入。
- **steps**:
  1. 收集来龙、穴场、明堂、水口、砂水、道路/水流图。
  2. 标注哪些信息对应上篇龙水规则、哪些对应下篇水形规则。
  3. 缺罗盘度数、水流方向、地形图时，不进入判断。
- **tool_dependency**:
  - tool.fengshui.terrain
  - tool.fengshui.luopan
- **source_chapter**: shang-longshui, xia-shuifa
- **verified**: false

## DTP-03: 三元与二十四山核查

- **purpose**: 处理天元、地元、人元、子午卯酉、辰戌丑未、寅申巳亥等分组问题。
- **steps**:
  1. 由 `tool.fengshui.luopan` 提供坐山、来龙、水口方位。
  2. 由工具按选定流派映射二十四山三元分组。
  3. 将结果回填到 DTR-04 的文献框架。
  4. 若不同流派分组冲突，输出冲突来源，不裁判现实吉凶。
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.school_profile
- **source_chapter**: shang-longshui, zhong-konglong
- **verified**: false

## DTP-04: 城门诀与空龙查询

- **purpose**: 回答城门、空龙、平洋军州等理气源流问题。
- **steps**:
  1. 读取 DTR-02、DTR-06、DTR-08。
  2. 与 `qingnang-xu` 的山水二路、`tianyu-jing` 的零正神/玄空口径互证。
  3. 若用户要求操作，转入工具核算；本 pack 不给方位结果。
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.watermouth
- **source_chapter**: zhong-konglong
- **verified**: false

## DTP-05: 强断语安全降级

- **purpose**: 处理下篇涉及伤亡、败绝、官禄、财丁等强断语。
- **steps**:
  1. 识别 `rules.md` 中 DTR-10 至 DTR-14 的古代断语。
  2. 输出为“古籍原文中的风险词/象征语”，不输出为现实预测。
  3. 若用户要求现实建议，改答文化解释或建议找合格专业人士与测绘资料。
- **tool_dependency**: none
- **source_chapter**: xia-shuifa
- **verified**: false

## DTP-06: 与《地理辨正》系互证

- **purpose**: 保持原典、蒋大鸿疏、后世玄空派解释的层级边界。
- **steps**:
  1. 当前仅使用 normalized 全文作为临时原文层。
  2. 若后续引入《地理辨正》，必须单独建 commentary 层。
  3. master skill 合并时，以 `source_layer` 区分 primary、commentary、modern。
- **tool_dependency**: none
- **source_chapter**: all
- **verified**: false
