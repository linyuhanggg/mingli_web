---
title: 葬法倒杖
slug: zangfa-daozhang
system: fengshui
school:
  - 形峦
  - 阴宅
  - 葬法
  - 倒杖
  - 杨公风水
source_layer: primary
source_status: complete_chapter_set
source_links:
  - https://zh.wikisource.org/wiki/%E6%92%BC%E9%BE%8D%E7%B6%93/%E8%91%AC%E6%B3%95%E5%80%92%E6%9D%96
  - https://ctext.org/wiki.pl?chapter=470367&if=gb
version_notes: |
  本 pack 以维基文库《撼龍經/葬法倒杖》6 个章节页为底本。
  旧题唐·杨筠松，作者归属按传统题署保留；CTP 页面只作版本锚点。
  本书属于阴宅形峦/穴法/倒杖层，不可外推为阳宅八宅、玄空理气或择日规则。
depends_on:
  - fengshui/zangshu
  - fengshui/hanlong-jing
  - fengshui/yilong-jing
informs:
  - fengshui/rudi-yan-quanshu
core_use_cases:
  - 阴宅形峦中穴场、圆晕、四象、倒杖术语定位
  - 葬法倒杖十六法、十二法、二十四砂葬法的原文证据层
  - 与《葬书》《撼龙经》《疑龙经》《入地眼全书》对读
not_for:
  - 阳宅风水判断
  - 玄空飞星、坐向理气、择日择时计算
  - 缺现场来龙、砂水、明堂、罗盘、地形事实层时直接断吉凶
  - 现代墓地处置、法律、工程或安全建议
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 葬法倒杖 Reference Pack（index）

本 pack 来自完整本地 normalized chapter set，供 `mingli-master` 在风水形峦/阴宅葬法语境下作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E6%92%BC%E9%BE%8D%E7%B6%93/%E8%91%AC%E6%B3%95%E5%80%92%E6%9D%96` |
| local_fulltext | `references/fulltext/fengshui/zangfa-daozhang/fulltext.md` |
| source_lines | 136 |
| source_sha256 | `2b396a6ad135e50b38c85ba9611f795adc9dca369c258df8592be41795b4414f` |
| structural_units | 6 |
| source_status | `complete_chapter_set` |

## Position

《葬法倒杖》是形峦阴宅体系中从“认穴”走向“下杖/葬法”的细化文本：先认太极圆晕，再辨两仪阴阳、四象脉息窟突，继而展开盖、粘、倚、撞等具体作法，最后列十二杖与二十四砂葬法。

## Loading Guide

1. 先确认问题属于阴宅形峦/穴法研究；阳宅、择日、玄空理气不从本 pack 起手。
2. 读 `chapter-map.md` 确定章节层级。
3. 读 `terms.md` 明确圆晕、两仪、四象、倒杖诸名。
4. 读 `rules.md` 只取可追溯的文献规则，不把穴法句子改写成现代现场结论。
5. 需要操作流程时读 `procedures.md`，并先要求现场事实层。
6. 需要证据时查 `quote-index.md`，必要时回 fulltext。
