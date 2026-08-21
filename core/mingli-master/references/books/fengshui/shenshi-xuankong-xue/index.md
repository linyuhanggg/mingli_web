---
title: 增广沈氏玄空学
slug: shenshi-xuankong-xue
system: fengshui
school:
  - 玄空飞星
  - 沈氏玄空
  - 三元地理
source_layer: public_topic_transcription
source_status: normalized_ready_with_image_skips
source_links:
  - https://special.rhky.com/mobile/mooc/tocourse/240632071
  - https://books.google.com/books/about/%E5%A2%9E%E5%BB%A3%E6%B2%88%E6%B0%8F%E7%8E%84%E7%A9%BA%E5%AD%B8.html?id=d0mOuAEACAAJ
version_notes: |
  本 pack 以 `special.rhky.com` 公开专题《增广沈氏玄空学 上》158 章为 normalized 底本。
  Google Books 书目记录显示《增廣沈氏玄空學》作者沈竹礽，编辑江志伊、王则先，第三版，发行者沈祖緜，1935。
  当前底本是网页转写层，不是 1935 民国版逐页影印 OCR 校本；图表页和卷标页以 skipped/image_only 保留。
depends_on:
  - dili-bianzheng
  - qingnang-jing
  - tianyu-jing
informs:
  - fengshui-master-skill
core_use_cases:
  - 玄空飞星、九运挨星、下卦起星、到山到向、上山下水等术语解释
  - 阴宅/阳宅案例中的山向、运星、旺衰、反吟伏吟等文本证据定位
  - 与《地理辨正》《天玉经》《青囊》系文献对读
not_for:
  - 现实住宅/墓地吉凶硬断
  - 投资、迁居、医疗、寿夭、灾祸等现实决策
  - 把 image_only 图表页当成已结构化规则
extraction_targets:
  - chapter_map
  - terms
  - rules
  - procedures
  - quote_index
conflict_policy: |
  与蒋大鸿《地理辨正》系文献冲突时：先标明沈氏解释层，不覆盖原典层。
  与形峦派文献冲突时：玄空飞星只作理气派视角，必须保留形峦/理气分歧。
  与现代建筑、法律、安全规范冲突时：现代规范优先。
validation_notes: |
  158 个章节页已缓存原始 HTML；147 个有正文，11 个 image_only/section-title 章节以 skipped 计入覆盖。
  短引均取自 normalized source。
modern_notes: |
  本书虽是玄空派核心近代文本，但下游 skill 只能作文化史与术语解释，不得输出现实风水承诺。
---

# 增广沈氏玄空学 Reference Pack

## Source

- **本地全文**：`references/fulltext/fengshui/shenshi-xuankong-xue/fulltext.md`
- **raw HTML**：`sources/raw/fengshui/shenshi-xuankong-xue/rhky/`
- **网页底本**：https://special.rhky.com/mobile/mooc/tocourse/240632071
- **书目锚点**：Google Books 记录 1935 第三版：作者沈竹礽，编辑江志伊、王则先，发行者沈祖緜。
- **覆盖**：158 章；正文 147 章，image_only/卷标 11 章。

## Loading Guide

默认读 `index.md` 和 `validation.md`。查术语用 `terms.md`；查章节证据用 `chapter-map.md`；抽短引用 `quote-index.md`。涉及挨星图和表格时必须回到 raw HTML / image refs，不能只靠正文。
