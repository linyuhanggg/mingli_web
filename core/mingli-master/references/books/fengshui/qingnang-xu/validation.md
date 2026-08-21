# 青囊序 — Validation

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: 维基文库通行本《青囊序》normalized text, divided into 8 semantic stanzas
- **source_status**: partial
- **reason**: 已完成本地 normalized 文本的全篇蒸馏与短引逐字命中；尚未与《地理辨正》及各校本影印系统逐段复核。

## Coverage Metrics

- **chapter_count_total**: 8
- **chapter_count_done**: 8
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 0
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
  - calculation: `(done + skipped_with_valid_reason) / total = (8 + 0) / 8`
- **loose_coverage**: 100%
  - calculation: `(done + partial + skipped_with_valid_reason) / total = (8 + 0 + 0) / 8`
- **extraction_coverage**: 100%
  - all 8 stanza entries are referenced by `terms.md`, `rules.md`, `procedures.md`, or `quote-index.md`.

## Quote Evidence

- **quote_total**: 17
- **quote_exact_hits**: 17
- **quote_hit_ratio**: 100%
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass, no out-of-range line anchors found by `audit_reference_packs.py`

## Status Counts

| status | chapters |
|---|---|
| done | s1-cixiong, s2-shanshui, s3-24shan, s4-jingyinyang, s5-shengwang, s6-jintui, s7-gongwei, s8-zongmiao |
| skipped | none |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all stanzas: 《地理辨正》及各校本影印逐段复核未完成
  - attribution: 曾文迪/曾求己作者归属与杨筠松师承关系待考
  - segmentation: 8 stanza 是本 pack 的语义分段，不声明为传统底本分章

`verified=false` means photographic/scan collation remains pending; it does not mean the local normalized text was not distilled.

## Batch Progress

- **D1**: Qoder generated a partial pack and used loose coverage semantics.
- **D2**: Codex corrected all stanza statuses to done, preserved verified=false, and made quote evidence machine-checkable.

## Remaining Work

1. 与《地理辨正》及各校本逐段复核。
2. 补充《青囊奥语》《天玉经》《都天宝照经》之后，再做同源理气文本的冲突裁判。
3. 跨书源流、二十四山/四十八局/雌雄水法优先级裁判需要 xhigh。

## last_updated

2026-06-16 (Batch D2)
