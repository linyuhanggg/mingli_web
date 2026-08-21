---
slug: xingxue-dacheng
title: 星学大成 — 验证报告
last_updated: 2026-07-04
status: d2_ready_for_local_source
---

# 星学大成 — 验证报告

## 结论

本 pack 已取得完整本地 normalized source，并完成章节索引、术语、规则、流程、短引证据与边界说明。可作为 `mingli-master` 的 D2 reference pack 使用。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 8177 |
| structural_units_in_chapter_map | 1341 |
| digest_status_done | 1341 |
| quote_index_entries | 10 |

## 版本边界

三十卷文本量大，含星度、行限、神煞、格局、杂著；星度历算必须由天文/星命 adapter 输出，不能直接套古度数或手算。

## 下游使用边界

- 本 pack 是文献依据，不是独立 oracle。
- 任何历法、起卦、罗盘、星度、坐向、行限等事实层必须来自 deterministic adapter。
- 若与既有 pack 冲突，保留书名与流派差异，不做平均化。
