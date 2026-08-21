---
title: 疑龙经
slug: yilong-jing
system: fengshui
school:
  - 形势派
  - 形峦
  - 江西派
  - 杨公风水
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/撼龍經/疑龍經
  - https://zh.wikisource.org/zh-hans/疑龍經
version_notes: |
  题唐·杨筠松（传）撰，《钦定四库全书》子部术数类收录。
  本 pack 取维基文库整理本（CC BY-SA 4.0；古籍原文公有领域）。
  全书结构：上篇 / 中篇 / 下篇 / 附《疑龙十问》/ 附《卫龙篇》/ 附《变星篇》。
  与《撼龙经》合刊版本居多，本 pack 仅处理疑龙经部分。
  《疑龙十问》部分通行本作正文附录，本 pack 单独切分为 10 章。
  source_status=partial：维基文库整理文本未与四库本影印逐字对校，verified 字段全部为 false，待影印复核。
depends_on:
  - hanlong-jing
informs:
  - 形势派后世风水著作（地理人子须知、地理大全等）
core_use_cases:
  - 形势派寻龙辨穴疑难判别（干枝辨、背面辨、真假辨、形穴辨）
  - 撼龙经九星理论的辨证应用与穴法补充
  - 公位、阳宅阴宅、嗣续等专题疑问之文化研究
  - 风水理论史与杨公派文献研究
not_for:
  - 风水坐向实际测量（不替代 tool.fengshui.luopan）
  - 阴宅选址实务决策（不替代 tool.fengshui.terrain 与现场踏勘）
  - 现代殡葬与公共政策依据
  - 排盘 / 起卦 / 择日等事实计算
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - quote_index
---

# 疑龙经

题唐代杨筠松（救贫）撰，与《撼龙经》合称「撼疑双经」，为形势派峦头风水核心经文。
《撼龙经》主论九星龙脉之"识"，《疑龙经》专论寻龙辨穴之"疑"——
干枝难分、背面难辨、真假难判、形穴难合之处如何取舍。
全书三篇加三附：上中下三篇辨干枝护从、背面鬼官、形穴真伪；
附《疑龙十问》答抱养嗣续、公位、阳宅阴宅、主客山、形真假、博换等十大疑问；
附《卫龙篇》论侍卫龙身之池水形态；附《变星篇》总论九星变换与穴形对应。

## File Map

| file | purpose |
|------|---------|
| chapter-map.md | 三篇 + 十问 + 卫龙 + 变星 共 16 章节摘要 |
| terms.md | 形势派核心术语（干枝/护纒/鬼官/公位/博换/侍卫等） |
| rules.md | 寻龙辨穴判别规则（含阴宅 caveats） |
| procedures.md | 工具依赖型流程（不含 LLM 手算） |
| quote-index.md | 短引索引（每条 ≤80 字） |
| validation.md | 全书覆盖率与抽取统计 |
