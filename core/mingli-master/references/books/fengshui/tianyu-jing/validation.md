---
slug: tianyu-jing
file: validation
---

# 天玉经 校验 / 覆盖率

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: 维基文库《天玉經內傳》+《天玉經外編》全文，规范化为 4 篇：内传上、中、下、外编。
- **source_status**: ready
- **reason**: 已完成本地 normalized 文本的全篇蒸馏与短引逐字命中；影印逐字复核仍待做。

## Coverage Metrics

- **chapter_count_total**: 4
- **chapter_count_done**: 4
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 0
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
  - calculation: `(done + skipped_with_valid_reason) / total = (4 + 0) / 4`
- **loose_coverage**: 100%
- **extraction_coverage**: 100%
  - all 3 chapter-map entries are referenced by `terms.md`, `rules.md`, `procedures.md`, or `quote-index.md`.

## Quote Evidence

- **quote_total**: 35
- **quote_exact_hits**: 35
- **quote_hit_ratio**: 100%
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass, no out-of-range line anchors found by `audit_reference_packs.py`

## Status Counts

| status | chapters |
|---|---|
| done | shang-sanban, zhong-aixing, xia-lingshen, waibian-jiuxing |
| skipped | none |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all chapters: 与四库/《地理辨正》/CTP/Internet Archive 影印系统逐段复核
  - attribution: 题唐杨筠松撰之归属与成书时代需版本学考辨
  - layer split: 内传、外编、经文口诀与吴公等注解必须分层使用
  - lacuna: normalized text 保留 `[闕]` 等疑缺标记，需影印复核

`verified=false` means photographic/scan collation remains pending; it does not mean the local normalized text was not distilled.

## Conflict Log

- 与《青囊序》《青囊奥语》：同属理气水法源流，术语相互支援，但不能简单互相替代。
- 与《地理辨正》：本书常被蒋大鸿系统重释；master skill 应把蒋注/后世玄空派作为注释层，不覆盖原典层。
- 三合 vs 玄空：本底本注解中同时使用三合、玄空、挨星等语汇，后续裁判需要 xhigh。

## last_updated

2026-06-17 (Codex D2)
