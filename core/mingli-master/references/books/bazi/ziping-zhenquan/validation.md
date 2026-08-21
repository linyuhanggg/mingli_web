---
slug: ziping-zhenquan
file: validation
---

# 子平真诠 校验 / 覆盖率

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: 东里书斋《子平真詮》47 个核心章节，另含前言、凡例、序跋、命例附录与读后附记。
- **source_status**: ready
- **reason**: 47 个核心章节全数进入本地 normalized 文本，reference pack 已覆盖章节地图、术语、规则、流程与短引证据。

## Coverage Metrics

- **chapter_count_total**: 47
- **chapter_count_done**: 47
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 0
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
- **loose_coverage**: 100%
- **extraction_coverage**: 100%

## Quote Evidence

- **quote_total**: 47
- **quote_exact_hits**: 47 expected by construction from `fulltext.md`
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass if `audit_reference_packs.py` reports no out-of-range anchors

## Status Counts

| status | chapters |
|---|---|
| done | zp-01 through zp-47 |
| skipped | none |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all chapters: 与 Wikimedia/NLC 影印 PDF 逐段校勘
  - source layer: 东里书斋整理说明、序跋、命例附录不得进入沈氏原典规则层
  - commentary split: 徐乐吾评注与现代强弱派解释须单独进入 commentary/modern 层

`verified=false` means photographic/scan collation remains pending; it does not mean the local normalized text was not distilled.

## Conflict Log

- 与《滴天髓阐微》：可互证子平法，但《滴天髓》偏气势体用，《子平真诠》偏月令格局。
- 与《三命通会》《渊海子平》：本书多次校正俗书与时说，应保留“沈氏格局法优先”的流派边界。
- 与现代强弱派：不可用身强身弱模板覆盖月令用神、相神、成败救应。

## last_updated

2026-06-17 (Codex D2)
