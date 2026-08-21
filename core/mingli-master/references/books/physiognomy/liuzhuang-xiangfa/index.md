---
title: 柳庄相法
slug: liuzhuang-xiangfa
system: physiognomy
school:
  - 明代相法
  - 柳庄相法
  - 骨相气色
source_layer: primary
source_status: normalized_ready
source_links:
  - https://ctext.org/wiki.pl?chapter=90958&if=gb&remap=gb
  - https://commons.wikimedia.org/wiki/File:NLC416-12jh003951-48665_柳庄相法.pdf
version_notes: |
  《柳庄相法》旧题明袁珙（柳庄居士）相法，袁忠彻等传整理。现存流传本复杂。
  本 pack 以 CTP Wiki 文本页为 normalized 底本，并保留本地 Wikimedia/NLC PDF 作为影印锚点；PDF 为影像层，未 OCR。
  CTP 文本分“上册”与“中册、永乐百问”，本地不强行复原三卷册页，仅按 CTP 行序覆盖 618 行。
depends_on:
  - shenxiang-quanbian
  - mayi-shenxiang
informs:
  - physiognomy-master-skill
core_use_cases:
  - 明代相法中骨相、五官、五岳、六府、气色、形局的原典参考
  - 与《神相全编》《麻衣神相》对读，区分相法术语层与后世汇编层
  - 作为相法 skill 的 source-layer primary 证据，不作现实人格/健康判断
not_for:
  - 医疗、寿夭、生育、刑伤、贫贱、婚姻确定判断
  - 对真人外貌作价值评判或歧视性归因
  - 手相/面相现代咨询的唯一依据
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与《神相全编》冲突时：本书作柳庄系原典层，《神相全编》作汇编层，需并列说明差异，不强行合并。
  与现代相法或心理学冲突时：现代伦理与安全优先；本书只作历史文本，不作现实判断。
  涉及儿童、孕产、疾病、死亡、刑伤、贫贱、女性德行等内容，必须标记为高风险古籍断语并安全改写。
validation_notes: |
  CTP 行表 618 行已抽取为 normalized fulltext；chapter-map 按 136 个机器识别标题覆盖。
  quote-index 短引均应 exact-ish 命中 fulltext。
modern_notes: |
  现代使用时仅用于相法史与术语解释；不得输出“某外貌必然某命运”的结论。
---

# 柳庄相法 Reference Pack

## Source

- **本地全文**：`references/fulltext/physiognomy/liuzhuang-xiangfa/fulltext.md`
- **文本锚点**：https://ctext.org/wiki.pl?chapter=90958&if=gb&remap=gb
- **影印锚点**：`sources/raw/physiognomy/liuzhuang-xiangfa/wikimedia_nlc_liuzhuang_xiangfa.pdf`
- **覆盖**：CTP 行表 618 行，按标题切 136 个单元。

## Loading Guide

默认加载 `index.md`；需要标题覆盖看 `chapter-map.md`，需要术语看 `terms.md`，需要规则与安全改写看 `rules.md` / `procedures.md`，需要证据看 `quote-index.md`。
