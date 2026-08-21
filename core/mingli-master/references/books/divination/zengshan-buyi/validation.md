---
slug: zengshan-buyi
title: 增删卜易 — 验证报告
last_updated: 2026-06-16
status: d2_ready_for_local_source
---

# 增删卜易 — 验证报告

## 结论

当前 pack 已按本地 normalized source 完成全结构建图，可作为下游 skill 的 reference evidence layer。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 6898 |
| structural_units_in_chapter_map | 155 |
| digest_status_done | 155 |
| digest_status_partial | 0 |
| digest_status_pending | 0 |
| digest_status_unavailable | 0 |
| quote_index_entries | 155 |

## 版本边界

作者名号与卷篇划分各本不同；当前 D2 ready 只表示本地维基文库整理本全源建图，现代录入者说明与附录须与原典层区分。

## 下游使用

- `chapter-map.md` / `section-map.md` 负责完整目录与行号范围。
- `quote-index.md` 负责精确短引证据。
- `terms.md` / `rules.md` / `procedures.md` 保留概念蒸馏层；production skill 可基于 source map 继续扩充细则。
