---
title: 黄金策
slug: huangjin-ce
system: divination
school:
  - 六爻
  - 纳甲
  - 火珠林法
  - 分门占断
source_layer: primary_or_commentary_mixed
source_status: complete_text
source_links:
  - https://zh.wikisource.org/wiki/%E9%BB%84%E9%87%91%E7%AD%96
version_notes: |
  Wikisource 页头题刘基，并说明电子文按《卜筮正宗》本全文载录。
  本 pack 将《黄金策》作为火珠林法/纳甲六爻分门占断的重要通行文本，不以此证明全部条文皆为刘基原著层。
  正文中出现“注释:”和“註記:”内容，作为后出注释层处理，不混入原典规则。
depends_on:
  - divination/huozhu-lin
informs:
  - divination/bushi-zhengzong
  - divination/zengshan-buyi
core_use_cases:
  - 六爻纳甲总断纲领
  - 分门占断章节索引
  - 用神、世应、动变、日辰月建权重
  - 神煞在六爻中降权为生克制化旁证
not_for:
  - 不经六爻/装卦 adapter 手算本卦、变卦、动爻、纳甲、世应、六亲、旬空、六神
  - 把分门断语脱离问题类别和完整卦象事实层直接套用
  - 把六爻神煞、六神、贵人名目跨体系移植到八字、紫微、择日或风水
  - 疾病、寿命、兵灾、讼狱、逃亡等高风险章节的现代事实判断
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 黄金策 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为六爻/火珠林法 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E9%BB%84%E9%87%91%E7%AD%96` |
| local_fulltext | `references/fulltext/divination/huangjin-ce/fulltext.md` |
| qoder_fulltext | `references/fulltext/divination/huangjin-ce/fulltext.md` |
| source_lines | 1759 |
| source_sha256 | `6a8569490397634b15c821116ebe21d9eff799c3b8c07c51179c4224a3362e77` |
| structural_units | 33 |
| source_status | `complete_text` |

## Position

《黄金策》在 `divination` 体系中定位为火珠林法/纳甲六爻的分门占断集成层。它比《火珠林》更适合直接检索“问某事该看什么爻、哪些组合为吉凶、应期从哪里看”，但仍然必须在完整六爻 fact-layer 之后使用。

## Loading Guide

1. 先读本 `index.md` 确认版本和禁用边界。
2. 用 `chapter-map.md` 将用户问题映射到天时、婚姻、求财、家宅、词讼、出行、行人等章节。
3. 用 `terms.md` 统一用神、世应、主象、日辰、月建、飞伏、空墓合冲等词义。
4. 用 `rules.md` 读取可操作判断规则；每条规则须有完整卦象事实层。
5. 用 `procedures.md` 检查 adapter 输入要求和停止条件。
6. 只用 `quote-index.md` 中的短引作为证据片段；需要上下文时再查 fulltext。
7. 若问神煞，先读 `references/matrices/shensha-cross-system-index.md`，再回到本 pack 的“神煞降权”规则。
