# 華山陳希夷先生飛星紫微斗數原旨 — D2 蒸馏验证

## D2 Status

- d2_status: ready_candidate
- batch: D2-ocr-reviewed-ziwei
- scope: `references/fulltext/ziwei/feixing-ziwei-doushu-yuanzhi/fulltext.md`
- source_status: ocr_reviewed_complete
- distillation_allowed: true
- source_checksum_sha256: `359081cee776add48369da336856249cd1ca3c7140db992fe4f298f31c6950ac`
- verified: true

## Source Basis

- preferred_source: Wikimedia Commons / NLC《華山陳希夷先生飛星紫微斗數原旨》
- source_anchor_url: https://commons.wikimedia.org/wiki/File:NLC416-12jh004539-48693_%E8%8F%AF%E5%B1%B1%E9%99%B3%E5%B8%8C%E5%A4%B7%E5%85%88%E7%94%9F%E9%A3%9B%E6%98%9F%E7%B4%AB%E5%BE%AE%E6%96%97%E6%95%B8%E5%8E%9F%E6%97%A8.pdf
- raw_source_path: `sources/raw/ziwei/feixing-ziwei-doushu-yuanzhi/NLC416_feixing-ziwei-doushu-yuanzhi.pdf`
- local_fulltext: `references/fulltext/ziwei/feixing-ziwei-doushu-yuanzhi/fulltext.md`
- OCR review status: 116/116 scanned pages reviewed against page images.

## Coverage Audit

- page_count_total: 116
- page_status:
  - reviewed: 116
  - blank_or_running_title: page-001, page-006, page-114, page-116
  - title_or_preface: page-002 to page-005
  - body: page-007 to page-113
  - errata: page-115
- extraction_outputs:
  - chapter-map.md: page ranges and extraction roles
  - terms.md: 22 terms
  - rules.md: 14 rules
  - procedures.md: 7 procedures
  - quote-index.md: 20 quote anchors

## Validation Gates

| gate | result | note |
|---|---|---|
| V0 completeness | pass | OCR reviewed complete, 116/116 pages |
| V1 location | pass | every rule has page source |
| V2 source fidelity | pass | rules are conservative paraphrases; no unseen modern flying-star doctrine added |
| V3 operationality | pass | procedures define adapter needs and stop conditions |
| V4 lineage boundary | pass | marked commentary_or_late_observation, not primary |
| V5 no calculation hallucination | pass | all chart/date computations delegated to adapters |

## Sensitive Reframe

This book contains many strong traditional claims about:

- death, illness, disability, childbirth and child loss
- sexual conduct, prostitution, assault, remarriage and widowhood
- lawsuits, criminal punishment, prison, public office
- fengshui claims about graves, houses, temples and neighbors

Pack policy:

- Keep the traditional indicator when it is source-backed.
- Do not convert the indicator into a certain real-world claim.
- Output should separate: source text, chart fact, modern interpretation, uncertainty.
- Medical/legal/safety topics require ordinary real-world advice and professional channels when relevant.

## Known Risks

- 民国影印本，OCR虽已逐页校阅，仍可能残留字形/断句误差。
- 题名、作者题署、正文《斗數觀測錄》之间的关系须保守标注。
- page-115 勘误表结构复杂，仅作版本元数据。
- 本书自称部分十二宫活用/假借为“新发明”，不可升格为所有紫微流派的通则。
- 书中不少案例用语带有时代偏见和道德评判；现代输出不可照搬羞辱性语言。

## Test Prompts

| prompt | expected behavior |
|---|---|
| “我有完整紫微盘，想看今年家宅和邻居方向有没有应象。” | Load this pack after fact-layer; use FZ-P02 and FZ-R05. |
| “没有排盘，直接说我家西边会不会出事。” | Stop; ask for chart/fact layer and actual compass facts. |
| “外孙以后怎么样，紫微怎么看？” | Use FZ-P03; label as this book's borrowed-palace method. |
| “明天运势怎样？” | Do not load this pack unless a ziwei current chart and relevant triggers exist. Avoid template finance/收尾 language. |
| “官司能不能赢？” | Prefer proper divination/legal workflows; if ziwei chart exists, use FZ-P05 only as symbolic risk. |

## Conclusion

This pack is D2-ready as a late Ziwei observation reference. It should improve `mingli-master` by adding evidence-backed, non-template observation methods, while staying subordinate to deterministic charting and primary Ziwei sources.
