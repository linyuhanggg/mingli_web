# 疑龙经 — Validation

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: 维基文库《撼龍經/疑龍經》所收《疑龙经》normalized text
- **source_status**: partial
- **reason**: 已完成本地 normalized 文本的全书蒸馏与短引逐字命中；尚未与四库本/影印系统逐字复核。

## Coverage Metrics

- **chapter_count_total**: 16
- **chapter_count_done**: 16
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 0
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
  - calculation: `(done + skipped_with_valid_reason) / total = (16 + 0) / 16`
- **loose_coverage**: 100%
  - calculation: `(done + partial + skipped_with_valid_reason) / total = (16 + 0 + 0) / 16`
- **extraction_coverage**: 100%
  - all 16 chapter-map entries are referenced by `terms.md`, `rules.md`, `procedures.md`, or `quote-index.md`.

## Quote Evidence

- **quote_total**: 35
- **quote_exact_hits**: 35
- **quote_hit_ratio**: 100%
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass, no out-of-range line anchors found by `audit_reference_packs.py`

## Status Counts

| status | chapters |
|---|---|
| done | shangpian, zhongpian, xiapian, wen-1-baoyang, wen-2-gongwei, wen-3-shengshuai, wen-4-yangzhai, wen-5-daxiao, wen-6-zhuke, wen-7-xingzhenjia, wen-8-ganzhi, wen-9-huajia, wen-10-bohuan, weilong, bianxing-shou, bianxing-wei |
| skipped | none |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all chapters: 四库本/影印系统逐字复核未完成
  - attribution and transmission: 杨筠松题名、后世合刊与《撼龙经》关系需版本学复核
  - typography: normalized text contains rare/variant characters and one hidden joiner sequence in Q-34; quote-index preserves local normalized text for exact evidence matching

`verified=false` means photographic/scan collation remains pending; it does not mean the local normalized text was not distilled.

## Tool Dependencies

- `tool.fengshui.luopan`: any坐向/度数/二十四山判断
- `tool.fengshui.terrain`: any地形/来龙/护从/明堂判断
- LLM must not hand-calculate compass bearings, GIS geometry, burial suitability, or real-world site safety.

## Batch Progress

- **D1**: Qoder generated a partial pack with 35 quotes, two quote strings not exact-matching the local normalized text.
- **D2**: Codex corrected chapter statuses, fixed quote exact-match strings, preserved verified=false, and made quote evidence machine-checkable.

## Remaining Work

1. 与四库本/影印系统逐字复核全部 35 短引。
2. 与《撼龙经》的形势派术语分工和优先级需要后续跨书裁判。
3. 阴宅、公位、嗣续等内容必须保留文化研究 caveats，不得直接进入现实建议。

## last_updated

2026-06-16 (Batch D2)
