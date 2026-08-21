---
slug: wuxing-jingji
title: 五行精纪 — 验证报告
last_updated: 2026-06-16
status: d2_ready_for_local_source
---

# 五行精纪 — 验证报告

## 结论

当前 pack 已按本地 normalized source 完成全结构建图，可作为下游 skill 的 reference evidence layer。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 8591 |
| structural_units_in_chapter_map | 709 |
| digest_status_done | 709 |
| digest_status_partial | 0 |
| digest_status_pending | 0 |
| digest_status_unavailable | 0 |
| quote_index_entries | 709 |

## 版本边界

宋廖中《五行精纪》当前源为 Wikisource 单页全文；正文无完整 Markdown 章题，本次按裸卷题/论题正则建图，仍需版本校勘层。

## 下游使用

- `chapter-map.md` / `section-map.md` 负责完整目录与行号范围。
- `quote-index.md` 负责精确短引证据。
- `terms.md` / `rules.md` / `procedures.md` 保留概念蒸馏层；production skill 可基于 source map 继续扩充细则。
