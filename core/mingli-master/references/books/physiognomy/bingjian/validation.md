# 冰鉴 — D2 蒸馏验证

## D2 状态

- d2_status: ready_candidate
- batch: D2-evidence-repair
- scope: 本地规范化全文 `references/fulltext/physiognomy/bingjian/fulltext.md`
- source_status: partial
- source_layer: side_evidence
- source_basis:
  - preferred_source: 维基文库整理本
  - local_text: 本地 normalized fulltext
  - source_note: 作者归属有争议；本 pack 只作相法旁证层，不作权威归属断言
- verified: false

## 覆盖率审计

- chapter_count_total: 9
- chapter_status:
  - done: 9
  - partial: 0
  - pending: 0
  - skipped: 0
  - unavailable: 0
- strict_fulltext_coverage: 100%
  - 民国简沙侣序、七篇正文、清吴荣光跋全部进入 `chapter-map.md`
  - 序跋仅作版本流传与文献线索，不进入规则抽取
- quote_exact_match:
  - total: 28
  - exact_hits: 28
  - hit_ratio: 100%
  - repair_note: D2 已修正 quote-index 表格列顺序，并将省略号拼接句改为连续 exact short quotes

## 抽取覆盖审计

- terms: 23 条
- rules: 31 条
- procedures: 6 条
- extraction_scope:
  - 七篇正文均进入术语、规则、流程、短引层
  - 序跋只进入短引与版本说明，不抽取相法规则
  - 规则输出必须走旁证层，不得替代命盘主线

## Safety 与旁证层约束

- 不接收照片、图像、视频，不做“AI 看相”
- 不凭相貌单独决定命运、富贵、贫贱、寿夭、子嗣、婚姻
- 与八字、紫微、禄命等命盘系统冲突时，命盘主线优先；《冰鉴》只作文化解释或旁证
- 贬义判语必须 reframe 为“古典语义还原”，不得作为现实人格、能力、道德判断
- 涉及寿命、灾祸、贫富、子嗣、女命等内容，必须走 safety-redlines

## 仍需复核

- 清刊本影印逐字校勘
- 作者归属考证：罗祖真人、曾国藩托名、原撰不详等说法
- 与《神相全编》《柳庄相法》的神骨、五官、声音、气色条目对照
- 现代心理学映射只可放 commentary 层，不应写入原典 reference pack

## 结论

该 pack 可作为 D2 ready candidate：9 个章节单元全部完成证据图谱，28/28 短引 exact-match，通过单书证据链审计。它仍只能作为“相法旁证层”加载，不应成为主结论源。
