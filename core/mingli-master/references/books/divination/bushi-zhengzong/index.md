---
title: 卜筮正宗
slug: bushi-zhengzong
system: divination
school:
  - 六爻
  - 纳甲筮法
  - 清代卜筮实务
source_layer: primary
source_status: normalized_ready
source_links:
  - https://ctext.org/wiki.pl?if=gb&res=112056
  - https://ctext.org/wiki.pl?chapter=889452&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=801184&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=944578&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=909268&if=gb&remap=gb
version_notes: |
  《卜筮正宗》清王洪绪辑。CTP 收为 4 个章节页，本 pack 以其 Wiki 文本为 normalized 底本。
  原 source manifest 误题《卜法正宗》，本次更正为《卜筮正宗》，slug 采用全局矩阵既有 `bushi-zhengzong`。
  CTP 文本含卷目、启蒙、十八论、黄金策直解、十八问答等内容，个别行首/行尾有 OCR/截断异文，需影印校。
depends_on:
  - zengshan-buyi
  - zhouyi-zhezhong
informs:
  - divination-master-skill
core_use_cases:
  - 六爻纳甲断卦实务的用神、世应、原神忌神、飞伏神、旬空月破等基础规则
  - 黄金策总断/天时/年时/国朝/婚姻/疾病/求财/家宅等分类占断
  - 与《增删卜易》对读，处理六爻实务分歧
not_for:
  - 不经起卦/装卦工具手算六爻
  - 对现实疾病、寿命、诉讼、失踪作确定结论
  - 将神煞旧断语直接输出给用户
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与《增删卜易》冲突时：本书代表较早的清代卜筮正宗体系，《增删卜易》多有修正和实战辨误；主 skill 应并列来源并说明差异。
  与梅花易数冲突时：二者起法与断法不同，不混用。
validation_notes: |
  4 个 CTP 页全部抽取；chapter-map 行级覆盖 3472 单元，quote-index 跨页短引 303 条。
modern_notes: |
  现代使用需起卦/装卦工具；LLM 只做术语解释、流程路由与古籍依据索引。
---

# 卜筮正宗 Reference Pack

- 本地全文：`references/fulltext/divination/bushi-zhengzong/fulltext.md`
- 原始 HTML：`sources/raw/divination/bushi-zhengzong/`
- 覆盖策略：CTP 行级全覆盖，每行一个 chapter-map 单元。
