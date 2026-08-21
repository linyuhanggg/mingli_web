---
title: 入地眼全书
slug: rudi-yan-quanshu
system: fengshui
school:
  - 形峦
  - 龙砂水向
  - 理气合参
  - 阳宅
source_layer: primary
source_status: complete_text
source_links:
  - https://zh.wikisource.org/wiki/%E5%85%A5%E5%9C%B0%E7%9C%BC%E5%85%A8%E6%9B%B8
version_notes: |
  宋·静道题；现存传本经后世刊刻。
  维基文库单页整理本；含序跋、例言、天星、龙法、砂法、水法、向法、阳宅。
  龙、砂、水、向、阳宅多层混排；须按层读取，不可跨层混成一句风水结论。
depends_on: []
informs: []
core_use_cases:
  - 龙砂水向全流程
  - 形峦与理气合参
  - 入首/祖宗/父母山判断
  - 水法形象优先与立向消纳
  - 阳宅门路灶宫星生克
not_for:
  - 替代实地踏勘、罗盘测量或地形数据
  - 单凭文字为现实墓宅定吉凶
  - 把双山长生、八卦水法等争议法混成统一规则
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 入地眼全书 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E5%85%A5%E5%9C%B0%E7%9C%BC%E5%85%A8%E6%9B%B8` |
| local_fulltext | `references/fulltext/fengshui/rudi-yan-quanshu/fulltext.md` |
| source_lines | 255 |
| source_sha256 | `f15e1a215fe1a0a6d0955ca52a3dfb4760d23660961bdfa30d4a6b2ecd69f1a4` |
| structural_units | 7 |
| source_status | `complete_text` |

## Position

入地眼全书 在 `fengshui` 体系中用于：龙砂水向全流程; 形峦与理气合参; 入首/祖宗/父母山判断; 水法形象优先与立向消纳; 阳宅门路灶宫星生克。

## Loading Guide

1. 先读本 `index.md` 确认体系与边界。
2. 查章节范围读 `chapter-map.md`。
3. 查术语读 `terms.md`。
4. 查可操作判断读 `rules.md`。
5. 查流程与 adapter 依赖读 `procedures.md`。
6. 引证只用 `quote-index.md` 的短引，必要时再查 fulltext 上下文。
7. 计算、排盘、起卦、罗盘与星度一律交给 deterministic adapter。
