---
slug: huangdi-zhaijing
title: 黄帝宅经 — 验证报告
last_updated: 2026-07-04
status: d2_ready_for_local_source
---

# 黄帝宅经 — 验证报告

## 结论

本 pack 已取得完整本地 normalized source，并完成章节索引、术语、规则、流程、短引证据与边界说明。可作为 `mingli-master` 的 D2 reference pack 使用。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 40 |
| structural_units_in_chapter_map | 4 |
| digest_status_done | 4 |
| quote_index_entries | 7 |

## 版本边界

旧题黄帝不可当真实作者；二十四路修造规则须与八宅、玄空、形峦分别使用。

## 下游使用边界

- 本 pack 是文献依据，不是独立 oracle。
- 任何历法、起卦、罗盘、星度、坐向、行限等事实层必须来自 deterministic adapter。
- 若与既有 pack 冲突，保留书名与流派差异，不做平均化。
