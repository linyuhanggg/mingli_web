---
title: 奇门遁甲统宗大全
slug: qimen-dunjia-tongzhi
system: san-shi
school:
  - 奇门遁甲
  - 三式
  - 选择
  - 占法
source_layer: secondary
source_status: normalized_ready
source_links:
  - https://book.taiyi.me/%E5%8D%9C/%E5%A5%87%E9%97%A8%E9%81%81%E7%94%B2%E7%BB%9F%E5%AE%97%E5%A4%A7%E5%85%A8
  - https://ctext.org/wiki.pl?if=gb&res=535687
  - https://upload.wikimedia.org/wikipedia/commons/e/e6/NLC416-12jh003951-48665_%E5%A5%87%E9%96%80%E9%81%81%E7%94%B2%E7%B5%B1%E5%AE%97.pdf
version_notes: |
  本 pack 以 Taiyi 公共网页《奇门遁甲统宗大全》抽取正文为 normalized 底本；CTP《奇门遁甲统宗》为部分卷次章节锚点，NLC/Wikimedia PDF 为影印校勘锚点。
  Taiyi 文本含源流、凡例、卷一至三、合并卷四至九“奇门演义”、卷十至十二“玄机赋”；因卷四至九未逐页影印校勘，skill 生成时必须保留“web transcription with scan anchor”版本标记。
depends_on:
  - san-shi-master-skill
informs:
  - qimen-dunjia-skill
core_use_cases:
  - 奇门遁甲术语、格局、门奇、值符值使、三奇六仪等概念蒸馏
  - 奇门选择与占法原则的文本证据定位
  - 与《奇门遁甲秘笈大全》《奇门五总龟》等同类文本互证
not_for:
  - 现实事件事实预测
  - 医疗、法律、投资、灾祸等重大决策
  - 未经排盘工具验证的起局计算
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与影印本、CTP 或其他古籍发生冲突时，优先标注版本差异；Taiyi 文本先作蒸馏底稿，不作最终校勘本。
validation_notes: |
  9 个章节段落全部抽取，quote-index 短引均来自本地 normalized fulltext。
modern_notes: |
  输出必须标明传统术数文本性质，不得包装成确定性预测或现实决策依据。
---

# 奇门遁甲统宗大全 Reference Pack

## Source

- **本地全文**：`references/fulltext/san-shi/qimen-dunjia-tongzhi/fulltext.md`
- **raw 抽取文本**：`sources/raw/san-shi/qimen-dunjia-tongzhi/taiyi/taiyi-qimen-tongzong-daquan_extracted.md`
- **Taiyi 来源页**：https://book.taiyi.me/%E5%8D%9C/%E5%A5%87%E9%97%A8%E9%81%81%E7%94%B2%E7%BB%9F%E5%AE%97%E5%A4%A7%E5%85%A8
- **CTP 部分卷次锚点**：https://ctext.org/wiki.pl?if=gb&res=535687
- **NLC/Wikimedia 影印锚点**：`sources/raw/san-shi/qimen-dunjia-tongzhi/NLC416-12jh003951-48665_qimen-dunjia-tongzong.pdf`
- **覆盖**：9 个网页章节段落全部入库；卷四至九在 Taiyi 中合并为“奇门演义”。

## Loading Guide

默认读 `index.md`；查卷次用 `chapter-map.md`，查术语用 `terms.md`，查规则与安全边界用 `rules.md` / `procedures.md`，查证据短引用 `quote-index.md`。
