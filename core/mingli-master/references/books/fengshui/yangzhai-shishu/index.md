---
title: 阳宅十书
slug: yangzhai-shishu
system: fengshui
school:
  - 阳宅
  - 八宅游年
  - 宅形
  - 修造择日
  - 放水
  - 符镇
source_layer: primary
source_status: complete_chapter_set
source_links:
  - https://zh.wikisource.org/zh-hans/%E6%AC%BD%E5%AE%9A%E5%8F%A4%E4%BB%8A%E5%9C%96%E6%9B%B8%E9%9B%86%E6%88%90/%E5%8D%9A%E7%89%A9%E5%BD%99%E7%B7%A8/%E8%97%9D%E8%A1%93%E5%85%B8/%E7%AC%AC675%E5%8D%B7
  - https://zh.wikisource.org/zh-hans/%E6%AC%BD%E5%AE%9A%E5%8F%A4%E4%BB%8A%E5%9C%96%E6%9B%B8%E9%9B%86%E6%88%90/%E5%8D%9A%E7%89%A9%E5%BD%99%E7%B7%A8/%E8%97%9D%E8%A1%93%E5%85%B8/%E7%AC%AC676%E5%8D%B7
  - https://zh.wikisource.org/zh-hans/%E6%AC%BD%E5%AE%9A%E5%8F%A4%E4%BB%8A%E5%9C%96%E6%9B%B8%E9%9B%86%E6%88%90/%E5%8D%9A%E7%89%A9%E5%BD%99%E7%B7%A8/%E8%97%9D%E8%A1%93%E5%85%B8/%E7%AC%AC677%E5%8D%B7
  - https://zh.wikisource.org/zh-hans/%E6%AC%BD%E5%AE%9A%E5%8F%A4%E4%BB%8A%E5%9C%96%E6%9B%B8%E9%9B%86%E6%88%90/%E5%8D%9A%E7%89%A9%E5%BD%99%E7%B7%A8/%E8%97%9D%E8%A1%93%E5%85%B8/%E7%AC%AC678%E5%8D%B7
version_notes: |
  以维基文库《钦定古今图书集成·博物汇编·艺术典》第675-678卷所收《阳宅十书一至四》为底本。
  题明·王君荣辑；作者归属按传统题署处理，不作无保留史实断定。
  第十《论符镇》与多处宅图含图像资产，本 pack 保留 IMAGE 锚点，但不转写符形，不把符形作为可执行规则。
depends_on:
  - fengshui/huangdi-zhaijing
informs:
  - fengshui/yangzhai-sanyao
core_use_cases:
  - 阳宅外形与宅内形证据
  - 福元、东四位西四位、大游年、穿宫分房的原典来源
  - 开门修造、放水、选择的文本依据与 adapter 需求
  - 阳宅三要、黄帝宅经之间的源流和分工
not_for:
  - 替代罗盘坐向、建筑测量、排水测量或现场勘验
  - 让语言模型手算福元、游年、二十四山、门尺、建除、太阴太阳过宫
  - 直接执行符镇或符形绘制
  - 把阳宅规则混入阴宅葬法或玄空飞星而不标注流派
extraction_targets:
  - terms
  - rules
  - procedures
  - quote_index
  - validation
---

# 阳宅十书 Reference Pack（index）

本 pack 来自完整本地 normalized source，供 `mingli-master` 作为 evidence layer 按需加载。

## Source Scope

| field | value |
|---|---|
| source | `Wikisource 艺术典第675-678卷 rendered transclusion` |
| local_fulltext | `references/fulltext/fengshui/yangzhai-shishu/fulltext.md` |
| source_lines | 3015 |
| source_sha256 | `78ca6fcbc7dec7b361bf4b4922c6834bc4d1320495940d51cc11f411d348110a` |
| structural_units | 10 |
| image_anchors | 248 |
| unidentified_glyph_images | 11 |
| source_status | `complete_chapter_set` |

## Position

《阳宅十书》在 `fengshui` 体系中补上阳宅原典核心层：外形/内形、福元、八宅游年、穿宫分房、开门修造、放水、选择与符镇。它位于《黄帝宅经》的早期宅法之后、《阳宅三要》的门主灶体系之前，适合作阳宅判断的一线 reference，但必须依赖罗盘、历法、布局和水路 adapter。

## Loading Guide

1. 先读本 `index.md` 确认体系与边界。
2. 查章节范围读 `chapter-map.md`。
3. 查术语读 `terms.md`。
4. 查可操作判断读 `rules.md`。
5. 查流程与 adapter 依赖读 `procedures.md`。
6. 引证只用 `quote-index.md` 的短引，必要时再查 fulltext 上下文。
7. 符镇、门尺图、宅图、水法图只可作为图像证据锚点，不得由语言模型凭图意补规则。
