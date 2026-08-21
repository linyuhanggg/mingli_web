# 钦定协纪辨方书 — Validation

> D2 evidence-chain validation. 本文件证明 reference pack 对本地规范化文本的覆盖与可追溯性，不证明择日规则的现实有效性。

## Source State

- **manifest**：`sources/manifests/xieji-bianfang-shu.yaml`
- **normalized_status**：ready
- **normalized_source_path**：`references/fulltext/selection/xieji-bianfang-shu/fulltext.md`
- **source_text_lines**：11863
- **base_text**：《钦定协纪辨方书（四库全书本）》维基文库整理文本
- **verified_against_image**：false

## D2 Coverage

- **chapter_units_total**：37（front matter 1 + 正文三十六卷 36）
- **chapter_units_done**：37
- **chapter_units_partial**：0
- **chapter_units_pending**：0
- **chapter_units_unavailable**：0
- **strict_coverage**：100%
- **section_map_entries**：2948
- **quote_index_entries**：1504
- **quote_policy**：每条短引来自本地 `fulltext.md` exact-match，压缩后不超过 80 字。

## Ready Candidate Decision

- **D2 ready_candidate**：yes
- **reason**：本地 normalized source 为 ready；front matter 与 36 卷均为 `done`；卷内三级标题已进入 `section-map.md`；quote-index 为 exact-match 原文短引；无 pending / unavailable 章节。
- **scope_limit**：ready_candidate 只表示可作为择日 skill 的官方选择通书 reference pack；具体日期、时辰、神煞、方位仍必须工具计算。

## Remaining Verification

1. 对四库影印逐页校勘维基文库文本，特别是大型表格卷（年表、月表、日表、时辰定局）。
2. 将 `section-map.md` 的小节标题与 `mingli-master.selection.v1` 输出字段建立 crosswalk。
3. 将卷三十三至三十六“辨讹”整理成 master skill 冲突裁判规则。
4. 与 `selection/xingli-kaoyuan` 建立神煞考源与铺注利用之间的引用关系。

## Output Safety

- 本书可作为官方择日 reference，但现实输出仍必须说明“文化参考，非事实判断”。
- 不允许 LLM 手算年/月/日/时神煞、建除、黄黑道、方位。
- 与民间通书冲突时，本书优先，民间书降级为旁证。

## last_updated

2026-06-16 (Batch D2)
