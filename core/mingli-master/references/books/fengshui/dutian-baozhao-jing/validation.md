---
slug: dutian-baozhao-jing
file: validation
---

# 都天宝照经 校验 / 覆盖率

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: NCC「陽宅堪輿古文 - 都天寶照經」全文，规范化为上篇、中篇、下篇。
- **source_status**: ready
- **reason**: 已完成本地 normalized 文本的全篇蒸馏与短引逐字命中；《地理辨正》刊本/影印本逐字复核仍待做。

## Coverage Metrics

- **chapter_count_total**: 3
- **chapter_count_done**: 3
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 0
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
  - calculation: `(done + skipped_with_valid_reason) / total = (3 + 0) / 3`
- **loose_coverage**: 100%
- **extraction_coverage**: 100%
  - all 3 chapter-map entries are referenced by `terms.md`, `rules.md`, `procedures.md`, or `quote-index.md`.

## Quote Evidence

- **quote_total**: 40
- **quote_exact_hits**: 40
- **quote_hit_ratio**: 100%
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass, no out-of-range line anchors expected

## Status Counts

| status | chapters |
|---|---|
| done | shang-longshui, zhong-konglong, xia-shuifa |
| skipped | none |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all chapters: 与《地理辨正》刊本/影印本逐段复核
  - attribution: 题杨筠松口授、黄妙应笔录之归属与成书时代需版本学考辨
  - layer split: 原典口诀、蒋大鸿疏、后世玄空派解释必须分层使用
  - license: NCC 网页授权未明确，需另寻馆藏/公有领域影印本作最终底本

`verified=false` means photographic/scan collation remains pending; it does not mean the local normalized text was not distilled.

## Conflict Log

- 与《天玉经》：同属《地理辨正》系核心文本，三卦、零正神、玄空、挨星等术语相关，但不可互相替代。
- 与《青囊序》：均重山水阴阳与水法，前者偏口诀与城门/三元语汇，后者偏总纲与水法源流。
- 与形势派：下篇大量水形、玄武、九星龙语汇，需与《撼龙经》《疑龙经》《葬书》互证。
- 与现代玄空派：后世飞星、三元、城门诀解释可能重释本经，master skill 应将现代解释列入 modern/commentary 层。

## last_updated

2026-06-17 (Codex D2)
