---
slug: yangzhai-shishu
title: 阳宅十书 — 验证报告
last_updated: 2026-07-04
status: d2_ready_for_local_source
---

# 阳宅十书 — 验证报告

## 结论

本 pack 已取得维基文库《钦定古今图书集成·博物汇编·艺术典》第675-678卷展开正文，并完成章节索引、术语、规则、流程、短引证据与边界说明。可作为 `mingli-master` 的 D2 reference pack 使用。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 3015 |
| structural_units_in_chapter_map | 10 |
| digest_status_done | 10 |
| quote_index_entries | 20 |
| image_anchors_preserved | 248 |
| unidentified_glyph_images | 11 |

## 来源与版本

- 底本：维基文库 rendered transclusion，源自《钦定古今图书集成·博物汇编·艺术典》第675-678卷所收《阳宅十书一至四》。
- CTP 页面只作在线锚点，不作下载源。
- 书名题署“明·王君荣辑”按传统版本记录；作者归属与版本系统保守标注。

## 质量边界

- 第十《论符镇》含大量符图；本 pack 保留 `[IMAGE:...]` URL 锚点，不转写符形、不生成符法执行步骤。
- 宅图、门尺图、水法图、太阴太阳过宫图均需图像/表格 adapter 校勘后才能结构化使用。
- 文本中有 11 处“请帮助识别此字”图像提示；相关局部不可作为强规则。

## 下游使用边界

- 本 pack 是文献依据，不是独立 oracle。
- 任何罗盘、坐向、二十四山、福元、游年、穿宫、择日、门光星、太阴太阳过宫等事实层必须来自 deterministic adapter。
- 若与《黄帝宅经》《阳宅三要》或玄空/形势/阴宅 pack 冲突，保留书名与流派差异，不做平均化。
