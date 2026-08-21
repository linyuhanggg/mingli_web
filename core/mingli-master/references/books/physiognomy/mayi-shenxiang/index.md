---
title: 麻衣相法（麻衣神相系）
slug: mayi-shenxiang
system: physiognomy
school:
  - 麻衣相法
  - 相法
  - 五官十二宫
source_layer: mixed
source_status: normalized_ready
source_links:
  - https://www.quanxue.cn/qt_mingxiang/mayixf/mayixf02.html
  - https://commons.wikimedia.org/wiki/Category:%E9%BA%BB%E8%A1%A3%E7%9B%B8%E6%B3%95
  - https://ctext.org/library.pl?if=gb&res=4355683
version_notes: |
  本 pack 的 normalized source 完整收入全学网《麻衣相法》mayixf01-mayixf14 网页文字。
  第 2-11 页为可作为“麻衣相法/麻衣神相系”通行文本参考的古籍转写层；第 1 页和第 12-14 页含现代说明、现代医学/交通语汇，只能作现代附益层。
  本地另存 Wikimedia/NLC《麻衣相法》两卷 PDF 影印锚点，但尚未逐页 OCR 校勘；因此本 pack 是“通行网页转写 D2 证据包”，不是 NLC 影印本逐字校本。
depends_on:
  - shenxiang-quanbian
  - liuzhuang-xiangfa
informs:
  - physiognomy-master-skill
core_use_cases:
  - 麻衣系相法的五官、十二宫、骨肉、四肢、气色、石室神异赋、金锁赋术语索引
  - 与《神相全编》《柳庄相法》对读，区分相法原典/汇编/现代附益
  - 作为相法史与术语解释的 source-layer 证据
not_for:
  - 医疗、寿夭、刑伤、贫贱、婚配、生育等现实硬断
  - 对真人外貌、身体特征作价值评判或歧视性归因
  - 将第 1 页或第 12-14 页现代附益当作古籍原文
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与《神相全编》冲突时：本书作麻衣系通行文本层，《神相全编》作明代汇编层；不强行合并。
  与《柳庄相法》冲突时：分别标注麻衣系/柳庄系，保留派系差异。
  与现代医学、心理学、伦理规范冲突时：现代安全规范优先；古籍断语只作历史文本解释。
validation_notes: |
  已完整抓取 mayixf01-mayixf14 并生成 normalized fulltext；reference pack 覆盖 14 个网页单元。
  短引均取自 normalized source；现代附益层单独标注，不进入一线规则。
modern_notes: |
  现代使用仅作文化史、术语和文本解释；涉及真人相貌时必须安全改写，避免决定论和歧视。
---

# 麻衣相法（麻衣神相系）Reference Pack

## Source

- **本地全文**：`references/fulltext/physiognomy/mayi-shenxiang/fulltext.md`
- **网页底本**：全学网《麻衣相法》`mayixf01`-`mayixf14`
- **影印锚点**：`sources/raw/physiognomy/mayi-shenxiang/mayi-xiangfa-v1.pdf`、`mayi-xiangfa-v2.pdf`
- **覆盖**：14 个网页单元全量收录；第 2-11 页为古籍转写层，第 1、12-14 页为现代附益层。

## Loading Guide

默认先读 `index.md` 和 `validation.md`。抽取术语看 `terms.md`，原文定位看 `chapter-map.md`，证据短引看 `quote-index.md`。执行相法类问答时只能把本书当作历史文本来源，不可对真人作现实断语。
