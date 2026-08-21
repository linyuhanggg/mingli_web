---
title: 星学大成
slug: xingxue-dacheng
system: xingming
school:
  - 七政四余
  - 星命
  - 五星推命
  - 三辰通载
source_layer: primary
source_status: complete_text
source_links:
  - https://zh.wikisource.org/wiki/%E6%98%9F%E5%AD%B8%E5%A4%A7%E6%88%90_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29
version_notes: |
  明·万民英。
  维基文库《星学大成（四库全书本）》主页面 + 卷一至卷三十。
  三十卷文本量大，含星度、行限、神煞、格局、杂著；星度历算必须由天文/星命 adapter 输出，不能直接套古度数或手算。
depends_on: []
informs: []
core_use_cases:
  - 七政四余大全式资料库
  - 星曜图例与十二宫法
  - 变曜/天元禄主/福财官田等主星
  - 观星节要与空实夹拱
  - 三辰通载与星曜格局源流
not_for:
  - 语言模型手排星盘、行度、行限或岁差校正
  - 把古星度表直接当现代天文位置
  - 对寿夭疾病等古断语作现实确定结论
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 星学大成 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `https://zh.wikisource.org/wiki/%E6%98%9F%E5%AD%B8%E5%A4%A7%E6%88%90_%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29` |
| local_fulltext | `references/fulltext/xingming/xingxue-dacheng/fulltext.md` |
| source_lines | 8177 |
| source_sha256 | `099ddc76d4143ad5e41601337c0ecb777b77adaf67737067339b9814784cb980` |
| structural_units | 1341 |
| source_status | `complete_text` |

## Position

星学大成 在 `xingming` 体系中用于：七政四余大全式资料库; 星曜图例与十二宫法; 变曜/天元禄主/福财官田等主星; 观星节要与空实夹拱; 三辰通载与星曜格局源流。

## Loading Guide

1. 先读本 `index.md` 确认体系与边界。
2. 查章节范围读 `chapter-map.md`。
3. 查术语读 `terms.md`。
4. 查可操作判断读 `rules.md`。
5. 查流程与 adapter 依赖读 `procedures.md`。
6. 引证只用 `quote-index.md` 的短引，必要时再查 fulltext 上下文。
7. 计算、排盘、起卦、罗盘与星度一律交给 deterministic adapter。
