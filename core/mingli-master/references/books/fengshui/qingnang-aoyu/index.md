---
title: 青囊奥语
slug: qingnang-aoyu
system: fengshui
school:
  - 理气
  - 玄空
  - 青囊系
  - 二十四山
  - 水法
source_layer: primary
source_status: complete_text
source_links:
  - https://zh.wikisource.org/wiki/%E9%9D%92%E5%9B%8A%E5%A5%A7%E8%AA%9E
  - https://zh.wikisource.org/wiki/%E9%9D%92%E5%9B%8A_(%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC)
  - https://ctext.org/wiki.pl?if=gb&res=772303
version_notes: |
  本 pack 以维基文库《青囊奥语》单篇为底本。
  旧题杨筠松，青囊系传承题署与版本系统复杂，作者归属只按传统题名记录。
  与《青囊序》《天玉经》《都天宝照经》《地理辨正》互文密切，不能脱离流派、坐向、元运、水法事实层独断。
depends_on:
  - fengshui/qingnang-jing
  - fengshui/qingnang-xu
informs:
  - fengshui/tianyu-jing
  - fengshui/dutian-baozhao-jing
  - fengshui/dili-bianzheng
core_use_cases:
  - 青囊系玄空/理气术语溯源
  - 二十四山、雌雄、金龙、天心十道、水法等短句定位
  - 与青囊序、天玉经、都天宝照经、地理辨正对读
not_for:
  - 替代罗盘坐向、元运、挨星或水法计算
  - 直接为现实住宅/墓地断吉凶
  - 把口诀当作可手算流程
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 青囊奥语 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E9%9D%92%E5%9B%8A%E5%A5%A7%E8%AA%9E` |
| local_fulltext | `references/fulltext/fengshui/qingnang-aoyu/fulltext.md` |
| source_lines | 38 |
| source_sha256 | `0718b133e0aaef6f7010d6d985809702ae0d8a2d92924e9fae591fc0431ffdc5` |
| structural_units | 5 |
| source_status | `complete_text` |

## Position

《青囊奥语》是青囊系理气/玄空短篇，适合作术语和口诀源头，不适合作单独“算风水”。实际读法必须加载罗盘/坐向/水路/元运事实层，并与《青囊序》《天玉经》《都天宝照经》《地理辨正》对读。

## Loading Guide

1. 先确认用户问题是否属于玄空/理气/水法，而不是形峦阴宅或阳宅八宅。
2. 读 `terms.md` 明确口诀词义和互文关系。
3. 读 `rules.md` 只取可转为 adapter 需求的规则。
4. 需要证据时查 `quote-index.md`，必要时回 fulltext。
5. 若缺坐向、二十四山、水路、元运/流派口径，停止在事实层请求。
