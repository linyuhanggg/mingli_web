# 御定星历考原 — Validation

> D2 evidence-chain validation. 本文件证明 reference pack 对本地规范化文本的覆盖与可追溯性，不证明择日规则的现实有效性。

## Source State

- **manifest**：`sources/manifests/xingli-kaoyuan.yaml`
- **normalized_status**：ready
- **normalized_source_path**：`references/fulltext/selection/xingli-kaoyuan/fulltext.md`
- **source_text_lines**：1404
- **base_text**：《御定星历考原（四库全书本）》维基文库整理文本
- **verified_against_image**：false

## D2 Coverage

- **chapter_units_total**：7（四库提要 1 + 正文六卷 6）
- **chapter_units_done**：7
- **chapter_units_partial**：0
- **chapter_units_pending**：0
- **chapter_units_unavailable**：0
- **strict_coverage**：100%
- **quote_index_entries**：375
- **quote_policy**：每条短引来自本地 `fulltext.md` exact-match，压缩后不超过 80 字。
- **anchor_policy**：卷六末行为 `fulltext.md L1404`，已移除旧的 line 1405 坏锚。

## Ready Candidate Decision

- **D2 ready_candidate**：yes
- **reason**：本地 normalized source 为 ready；提要与六卷均为 `done`；quote-index 为 exact-match 原文短引；无 pending / unavailable 章节；无坏行号锚点。
- **scope_limit**：ready_candidate 只表示可作为择日 skill 的官方考源 reference pack；具体日期与时辰仍必须工具计算。

## Remaining Verification

1. 对四库影印逐页校勘维基文库文本，尤其卷六用事宜忌的末尾条目。
2. 与《钦定协纪辨方书》对应神煞条目建立 crosswalk。
3. 与民间通书《玉匣记》《董公选择日要览》建立冲突裁判样例。
4. 为 `mingli-master.selection.v1` 定义输出字段：月建、日干支、建除十二值、黄黑道、神煞、用事宜忌。

## Output Safety

- 本书可作为“官方考源层”引用，但现实择日仍必须说明“文化参考，非事实判断”。
- 不允许 LLM 手算神煞落点、日时、方位。
- 与民间通书冲突时，本书优先，民间书降级为旁证。

## last_updated

2026-06-16 (Batch D2)
