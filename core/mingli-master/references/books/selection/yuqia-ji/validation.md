# 玉匣记 — Validation

> D2 evidence-chain validation. 本文件证明 reference pack 对本地规范化文本的覆盖与可追溯性，不证明民间择日或杂占现实有效性。

## Source State

- **manifest**：`sources/manifests/yuqia-ji.yaml`
- **normalized_status**：ready
- **normalized_source_path**：`references/fulltext/selection/yuqia-ji/fulltext.md`
- **source_text_lines**：4119
- **base_text**：维基文库《玉匣记》整理文本
- **verified_against_image**：false
- **source_risk**：版本众多，道藏《许真君玉匣记》和增广本差异需后续校勘。

## D2 Coverage

- **chapter_units_total**：265（按原文 `##` 小节）
- **chapter_units_done**：265
- **chapter_units_partial**：0
- **chapter_units_pending**：0
- **chapter_units_unavailable**：0
- **strict_coverage**：100%
- **section_map_entries**：265
- **quote_index_entries**：743
- **quote_policy**：每条短引来自本地 `fulltext.md` exact-match，压缩后不超过 80 字。

## Ready Candidate Decision

- **D2 ready_candidate**：yes
- **reason**：本地 normalized source 为 ready；全部原文小节均为 `done`；quote-index 为 exact-match 原文短引；无 pending / unavailable 章节。
- **scope_limit**：ready_candidate 只表示可作为民间通书 reference pack 的材料层；不可作为官方择日结论。

## Remaining Verification

1. 对道藏《许真君玉匣记》和增广本逐条校勘，标注哪些条目为后出增补。
2. 与《协纪辨方书》《星历考原》《董公选择日要览》建立冲突裁判和同名神煞 crosswalk。
3. 将医疗禁忌、杂占、身体征兆占断整理为安全改写模板。
4. 对嫁娶、出行、安葬、起造、农事、商事等用事条目建立事项路由。

## Output Safety

- 医疗、疾病、探病、针灸、服药相关内容只作民俗史材料，必须提示遵循现代医学。
- 杂占篇不得作现实预测。
- 具体日期换算、神煞、建除和方位必须调用 `mingli-master.selection.v1`。
- 与官方书冲突时，本书降级为民间旁证。

## last_updated

2026-06-16 (Batch D2)
