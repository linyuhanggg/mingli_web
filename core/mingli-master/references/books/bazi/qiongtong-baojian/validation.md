---
slug: qiongtong-baojian
title: 穷通宝鉴 — 验证报告
last_updated: 2026-06-16
status: d2_ready_for_local_source
---

# 穷通宝鉴 — 验证报告

## 结论

当前 pack 已按本地 normalized source 完成全结构建图，可作为下游 skill 的 reference evidence layer。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 1764 |
| structural_units_in_chapter_map | 56 |
| digest_status_done | 56 |
| digest_status_partial | 0 |
| digest_status_pending | 0 |
| digest_status_unavailable | 0 |
| quote_index_entries | 56 |

## 版本边界

当前 D2 ready 只表示维基文库整理本全文已建图；与传统余春台编订本、清刊本的章节差异仍需 edition-diff。

## 下游使用

- `chapter-map.md` / `section-map.md` 负责完整目录与行号范围。
- `quote-index.md` 负责精确短引证据。
- `terms.md` / `rules.md` / `procedures.md` 保留概念蒸馏层；如要做 production skill，应从 source map 按需扩充。
