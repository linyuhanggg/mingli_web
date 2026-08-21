---
title: 神峰通考
slug: shenfeng-tongkao
system: bazi
school:
  - 子平法
  - 明代命理
  - 张神峰病药动静体系
source_layer: primary
source_status: normalized_ready
source_links:
  - https://ctext.org/wiki.pl?if=gb&res=627586
  - https://ctext.org/wiki.pl?chapter=739505&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=552406&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=938428&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=472359&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=153898&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=109247&if=gb&remap=gb
  - https://ctext.org/wiki.pl?chapter=545846&if=gb&remap=gb
version_notes: |
  《神峰通考》明张楠著，通行题《神峰通考命理正宗》。CTP 收为 7 个章节页。
  本 pack 以 CTP Wiki 文本页为 normalized 底本，抽取 3027 行表；未与影印 PDF 逐字校。
  文本含张楠正文、补曰、古赋、歌诀、命例与辑录材料；后续可拆 author/commentary/quotation 层。
depends_on:
  - yuanhai-ziping
  - sanming-tonghui
  - ziping-zhenquan
  - ditiansui-chanwei
informs:
  - bazi-master-skill
core_use_cases:
  - 张神峰对子平旧说的批判，如五星、纳音、合婚、魁罡、日贵等谬说辨析
  - 动静、盖头、病药、雕枯旺弱、损益生长等理论术语
  - 正官、财、杀、印、伤食、从格等子平格局讨论
  - 古赋歌诀与命例的来源索引
not_for:
  - 直接给真人作寿夭疾病刑伤硬断
  - 不经排盘工具手算八字
  - 把辑录古赋当作张楠本人观点而不标层
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与《渊海子平》《三命通会》冲突时，优先说明张楠的批判立场与所反驳对象，不强行合并。
  与《子平真诠》冲突时，二者同属子平但理论重心不同：本书重病药、动静、盖头与辟谬；《子平真诠》重格局成败。
  涉及疾病、寿夭、女命、贫贱等断语必须安全改写为“古籍如何分类风险”。
validation_notes: |
  7 个 CTP 页全部抽取；chapter-map 为 3027 行级单元，quote-index 取 300+ 条跨页短引。
modern_notes: |
  现代 skill 使用时只作理论来源与术语解释，实际排盘需工具。
---

# 神峰通考 Reference Pack

- 本地全文：`references/fulltext/bazi/shenfeng-tongkao/fulltext.md`
- 原始 HTML：`sources/raw/bazi/shenfeng-tongkao/`
- 覆盖策略：CTP 行级全覆盖，每行一个 chapter-map 单元。
