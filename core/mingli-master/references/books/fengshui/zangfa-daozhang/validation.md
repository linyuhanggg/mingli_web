---
slug: zangfa-daozhang
title: 葬法倒杖 — 验证报告
last_updated: 2026-07-04
status: d2_ready_for_local_source
---

# 葬法倒杖 — 验证报告

## 结论

本 pack 已取得维基文库 6 个章节页完整文本，并完成章节索引、术语、规则、流程、短引证据与边界说明。可作为 `mingli-master` 的 D2 reference pack 使用。

## 覆盖指标

| metric | value |
|---|---:|
| normalized_source_lines | 136 |
| structural_units_in_chapter_map | 6 |
| digest_status_done | 6 |
| quote_index_entries | 30 |
| source_manifest_status | PASS |

## 版本边界

- 旧题唐·杨筠松按传统题名记录，作者归属不作无保留史实断定。
- 本 pack 采用维基文库章节集；CTP 只作版本锚点，不作下载源。
- 第 34 行 `高$山陰龍`、第 67 行 `浮□`、第 110 行 `登□□望龍` 保留为底文风险，未模型补字。
- `倒杖十二法` 本地文本可见 11 个圈点条目；“十二”名目不据模型猜补。

## 下游使用边界

- 本 pack 是阴宅形峦/葬法文献依据，不是独立 oracle。
- 现实场地解释必须先有来龙、穴情、砂水、明堂、四兽、罗盘/坐向等事实层。
- 不用于阳宅、择日、玄空飞星、八字、六爻、梅花等系统。
- 不提供现代墓地处置、施工、安全、法律建议。

## Validation Gates

| gate | result | notes |
|---|---|---|
| V0 completeness | pass | 6/6 chapters acquired. |
| V1 source location | pass | Rules and quotes use fulltext line anchors. |
| V2 source fidelity | pass | No modern doctrine added as original rule. |
| V3 operationality | pass_with_boundary | Procedures describe required fact-layer, not direct field advice. |
| V4 lineage boundary | pass | Fengshui / 形峦 / 阴宅 / 葬法. |
| V5 no calculation hallucination | pass | No calendar, luopan degree, or flying-star calculation performed. |
