---
title: 黄帝宅经
slug: huangdi-zhaijing
system: fengshui
school:
  - 阳宅
  - 相宅
  - 二十四路
  - 阴阳二宅
source_layer: primary
source_status: complete_text
source_links:
  - https://zh.wikisource.org/wiki/%E5%AE%85%E7%B6%93_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29
version_notes: |
  旧题黄帝；四库提要认为依托。
  维基文库《宅经（四库全书本）》；含提要、卷上、卷下。
  旧题黄帝不可当真实作者；二十四路修造规则须与八宅、玄空、形峦分别使用。
depends_on: []
informs: []
core_use_cases:
  - 早期相宅/阳宅源流
  - 二十四路阴阳宅法
  - 修宅次第与福德刑祸方
  - 宅体形势与居住关系原典
not_for:
  - 替代罗盘坐向/建筑测量
  - 直接给现代住宅安全或法务结论
  - 与八宅游年、玄空飞星混为同一体系
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 黄帝宅经 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E5%AE%85%E7%B6%93_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29` |
| local_fulltext | `references/fulltext/fengshui/huangdi-zhaijing/fulltext.md` |
| source_lines | 40 |
| source_sha256 | `04a5901c4908f79dfb74dc5d6a29f9e820181e03c967cc41f947aca3d14939b6` |
| structural_units | 4 |
| source_status | `complete_text` |

## Position

黄帝宅经 在 `fengshui` 体系中用于：早期相宅/阳宅源流; 二十四路阴阳宅法; 修宅次第与福德刑祸方; 宅体形势与居住关系原典。

## Loading Guide

1. 先读本 `index.md` 确认体系与边界。
2. 查章节范围读 `chapter-map.md`。
3. 查术语读 `terms.md`。
4. 查可操作判断读 `rules.md`。
5. 查流程与 adapter 依赖读 `procedures.md`。
6. 引证只用 `quote-index.md` 的短引，必要时再查 fulltext 上下文。
7. 计算、排盘、起卦、罗盘与星度一律交给 deterministic adapter。
