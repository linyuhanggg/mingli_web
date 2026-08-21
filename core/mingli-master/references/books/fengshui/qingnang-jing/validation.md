# 青囊经 — Validation

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: 维基文库通行本《青囊经》正文三卷 + 蒋大鸿注三段 normalized text
- **source_status**: partial
- **reason**: 已完成本地 normalized 文本的全书蒸馏与短引逐字命中；尚未与蒋大鸿《地理辨正》影印系统逐段复核。

## Coverage Metrics

- **chapter_count_total**: 6
- **chapter_count_done**: 6
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 0
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
  - calculation: `(done + skipped_with_valid_reason) / total = (6 + 0) / 6`
- **loose_coverage**: 100%
  - calculation: `(done + partial + skipped_with_valid_reason) / total = (6 + 0 + 0) / 6`
- **extraction_coverage**: 100%
  - all 6 chapter-map entries are referenced by `terms.md`, `rules.md`, `procedures.md`, or `quote-index.md`.

## Quote Evidence

- **quote_total**: 15
- **quote_exact_hits**: 15
- **quote_hit_ratio**: 100%
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass, no out-of-range line anchors found by `audit_reference_packs.py`

## Status Counts

| status | chapters |
|---|---|
| done | shang-huashi, zhong-huaji, xia-huacheng, jiang-zhu-shang, jiang-zhu-zhong, jiang-zhu-xia |
| skipped | none |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all chapters: 蒋大鸿《地理辨正》影印系统逐段复核未完成
  - attribution: "黄石公授赤松子"源流需版本学考辨
  - layer split: 正文三卷与蒋注三段在使用时必须保持 primary/commentary 分层

`verified=false` means photographic/scan collation remains pending; it does not mean the local normalized text was not distilled.

## Batch Progress

- **D1**: Qoder generated a partial pack and used loose coverage semantics.
- **D2**: Codex corrected all chapter statuses to done, preserved verified=false, and made quote evidence machine-checkable.

## Remaining Work

1. 与蒋大鸿《地理辨正》影印系统逐段复核。
2. 将正文层与蒋注层在 downstream master skill 中分层加载。
3. 与《青囊序》《青囊奥语》《天玉经》的理气源流冲突裁判需要 xhigh。

## last_updated

2026-06-16 (Batch D2)
