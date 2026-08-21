---
title: 火珠林
slug: huozhu-lin
system: divination
school:
  - 六爻
  - 纳甲
  - 火珠林法
  - 飞伏神
source_layer: primary
source_status: complete_text
source_links:
  - https://zh.wikisource.org/wiki/%E7%81%AB%E7%8F%A0%E6%9E%97
version_notes: |
  题麻衣道者；作者归属待考。
  维基文库单页整理本；按本地 normalized 章节标题建图。
  作者归属与版本系统需保守标注；本书为纳甲六爻源流层，实务占断应与《增删卜易》《卜筮正宗》对读。
depends_on: []
informs: []
core_use_cases:
  - 六爻纳甲源流
  - 飞伏神与世应早期法
  - 财官公私用事分类
  - 分门占断古法对照
not_for:
  - 不经六爻/装卦 adapter 手算纳甲、世应、六亲、旬空
  - 把早期断语直接替代《增删卜易》《卜筮正宗》的实务规则
  - 疾病、寿命、讼狱等现实高风险事项的确定结论
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 火珠林 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E7%81%AB%E7%8F%A0%E6%9E%97` |
| local_fulltext | `references/fulltext/divination/huozhu-lin/fulltext.md` |
| source_lines | 1100 |
| source_sha256 | `6239f9ef22be7deb5771b513dacfc9cc1e8eea8cc5e54164f971cd7de86e5293` |
| structural_units | 84 |
| source_status | `complete_text` |

## Position

火珠林 在 `divination` 体系中用于：六爻纳甲源流; 飞伏神与世应早期法; 财官公私用事分类; 分门占断古法对照。

## Loading Guide

1. 先读本 `index.md` 确认体系与边界。
2. 查章节范围读 `chapter-map.md`。
3. 查术语读 `terms.md`。
4. 查可操作判断读 `rules.md`。
5. 查流程与 adapter 依赖读 `procedures.md`。
6. 引证只用 `quote-index.md` 的短引，必要时再查 fulltext 上下文。
7. 计算、排盘、起卦、罗盘与星度一律交给 deterministic adapter。
