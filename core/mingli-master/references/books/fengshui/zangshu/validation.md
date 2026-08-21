# 葬书 — Validation

## D2 Evidence Gate

- **d2_status**: ready_candidate
- **scope**: 吴澄删定本《地理眞詮》一集所收《葬书》normalized text
- **source_status**: partial
- **reason**: 已完成本地 normalized 文本的全书蒸馏与短引逐字命中；尚未与四库本影印逐段复核，所以来源层仍为 partial。

## Coverage Metrics

- **chapter_count_total**: 12
- **chapter_count_done**: 10
- **chapter_count_partial**: 0
- **chapter_count_pending**: 0
- **chapter_count_skipped**: 2
- **chapter_count_unavailable**: 0
- **strict_coverage**: 100%
  - calculation: `(done + skipped_with_valid_reason) / total = (10 + 2) / 12`
- **loose_coverage**: 100%
  - calculation: `(done + partial + skipped_with_valid_reason) / total = (10 + 0 + 2) / 12`
- **extraction_coverage**: 100% for doctrinal chapters
  - 10/10 doctrinal chapters are referenced by `rules.md`, `procedures.md`, or `quote-index.md`.
  - `xu` and `mulu` are version/目录材料, intentionally skipped and documented.

## Quote Evidence

- **quote_total**: 21
- **quote_exact_hits**: 21
- **quote_hit_ratio**: 100%
- **quote_length_gate**: pass, every quote <= 80 normalized characters
- **line_anchor_gate**: pass, no out-of-range line anchors found by `audit_reference_packs.py`

## Status Counts

| status | chapters |
|---|---|
| done | neipian-1, neipian-2, neipian-3, neipian-4, waipian-1, waipian-2, waipian-3, waipian-4, zapian-shang, zapian-xia |
| skipped | xu, mulu |
| partial | none |
| pending | none |
| unavailable | none |

## Verification State

- **verified_chapters**: []
- **pending_verification**:
  - all doctrinal chapters: 四库本影印逐段复核未完成
  - author attribution: 郭璞托名、蔡季通删定、吴澄删定关系需版本学复核
  - textual variants: 世俗二十篇本、蔡季通八篇本、吴澄删定本差异需另建版本对照

`verified=false` does not mean the D2 distillation is absent; it means the local Wikisource-derived normalized text has not been checked against a photographic/scan base text.

## Batch Progress

- **D1**: Qoder generated a partial reference pack with exact quotes but loose coverage accounting.
- **D2**: Codex corrected coverage semantics, marked version-only sections as skipped, promoted doctrinal chapters to done, and made quote evidence machine-checkable.

## Remaining Work

1. 四库本影印逐段复核后，将 eligible chapters 的 `verified` 更新为 true。
2. 若后续要进入《青囊经》《青囊序》《撼龙经》之间的源流和冲突裁判，需要切换 xhigh。
3. 若做主 skill 路由，不应让《葬书》直接给现实葬地建议；只能作为形势派术语与古典源流 reference。

## last_updated

2026-06-16 (Batch D2)
