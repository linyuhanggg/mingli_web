---
slug: shenxiang-quanbian
title: 神相全编 — 验证报告
source_layer: side_evidence
source_scope: 古今图书集成艺术典第631-639卷辑录本
last_updated: 2026-06-16
status: d2_ready_for_local_source
---

# 神相全编 — 验证报告

## 结论

当前 pack 已从“代表性摘录”修订为“本地源文全结构建图 + 精确短引索引”。可以作为下游 skill 的相法旁证层 reference 使用。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 5109 |
| structural_units_in_chapter_map | 410 |
| digest_status_done | 410 |
| digest_status_partial | 0 |
| digest_status_pending | 0 |
| digest_status_unavailable | 0 |
| quote_index_entries | 410 |
| quote_strategy | 每个结构单元至少 1 条 exact-match 短引 |

## 文件清单

| 文件 | 状态 | 说明 |
|---|---|---|
| index.md | ready | 入口、版本边界、安全红线 |
| section-map.md | ready | 410 个结构单元全目录 |
| chapter-map.md | ready | D2 digest_status 全 done |
| terms.md | ready | 核心术语层，保留旁证 caveat |
| rules.md | ready | 代表规则层，保留 safety-redlines |
| procedures.md | ready | 旁证调用与屏蔽流程 |
| quote-index.md | ready | 410 条可精确匹配短引 |
| validation.md | ready | 本报告 |

## 版本边界

1. 当前源为《钦定古今图书集成·博物汇编·艺术典》第 631-639 卷“相术部汇考”辑录本。
2. 该源覆盖“神相全编一至九”及相术部上下文，但不是独立《神相全编》十二卷刊本。
3. 后续若补国图 PDF 或识典古籍十二卷本，应新增 edition layer，不得直接覆盖本 pack 的版本说明。
4. `context-heading` 与“相儿经 / 论相 / 人相篇”等上下文材料可作旁证，但不能混入“神相全编一至九”的原典层。

## Safety Redlines

- 禁止真人照片 / 视频看相。
- 禁止对具体个人输出富贵贫贱、寿夭、灾厄、婚育、疾病、子嗣硬断。
- 古文贬义标签只作文本研究，输出必须现代化 reframe。
- 命盘冲突时，本书永远只是旁证层。

## 后续补本计划

- 获取并 OCR / 对校国图藏《神相全编》PDF 或识典古籍十二卷本。
- 建立 `edition-diff.md`：比较独立刊本十二卷与古今图书集成辑录本一至九的篇目差异。
- 对长赋类文本再做逐句语义表，但仍保留 safety-redlines。
