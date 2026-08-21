# 珞琭子三命消息赋 — D2 蒸馏验证

## D2 状态

- d2_status: ready_candidate
- batch: D2-evidence-repair
- scope: 本地规范化全文 `references/fulltext/luming-nayin/luoluzi-sanming/fulltext.md`
- source_status: partial
- source_basis:
  - preferred_source: 维基文库 action=raw 文本
  - anchor_source: CTP 四库本 `https://ctext.org/wiki.pl?if=gb&res=430735`
  - source_note: 维基文库整理本已取得全文；CTP 仅作版本锚点，不作批量下载源
- verified: false

## 覆盖率审计

- chapter_count_total: 78
- chapter_status:
  - done: 78
  - partial: 0
  - pending: 0
  - skipped: 0
  - unavailable: 0
- strict_fulltext_coverage: 100%
  - 78 个章节单元全部进入 `chapter-map.md`
  - 77 个赋文/注文单元有 `quote-index.md` 短引证据
  - `preface/sikuan-tiyao` 为版本提要单元，不强制生成 quote
- quote_exact_match:
  - total: 88
  - exact_hits: 88
  - hit_ratio: 100%
  - max_quote_policy: 所有短引均应保持短句、可在本地全文中 exact-string 命中

## 抽取覆盖审计

- terms: 100 条
- rules: 41 条
- procedures: 5 条
- extraction_scope:
  - 术语、规则、流程按核心命理功能抽取，不强制每个章节单元各生成一条规则
  - `chapter-map.md` 的 `done` 仅表示逐章进入图谱并完成证据覆盖或版本提要标注
  - 徐子平注层主要作为 source_anchor 与解释语境；原赋层优先进入术语、规则、短引
- known_gap:
  - 未把徐子平注层逐条拆为二级术语卡
  - 历史命例尚未做完整逐步推演卡
  - 未与《五行精纪》《李虚中命书》《三命通会》做跨书异同合并

## 章节结构

- 四库提要: 1
- 总论、三才、三元、干支取用: 7
- 阴阳五行、三奇贵格、交差正合: 13
- 根苗、三兽五虎、飞禄走马、冠带衰乡: 7
- 向背、背禄、建禄、禄马同乡、夹禄: 10
- 阴阳男女、伏吟反吟、四煞五鬼、财禄通变: 13
- 方位、五行序位、旺衰、墓鬼、孤寡、二气延生: 13
- 宅墓、干支轻重、裸形夹煞、黄黑道、五神、勾绞、隔角、神煞: 11
- 终篇心法、善恶、处定问动、殊常变旧、公明季主: 3

## 敏感断语 reframe 审计

- 寿夭/疾病/死亡断语:
  - LZ-05-03 身旺鬼绝长年
  - LZ-05-04 鬼旺身衰夭寿
  - LZ-06-05 裸形夹煞至凶
  - LZ-07-04 八孤五墓
  - LZ-07-05 勾绞元亡
  - LZ-08-06 父病妻灾
- 婚配/克妻断语:
  - LZ-05-02 死妻多数而孤
  - LZ-05-05 必克妻
  - LZ-06-03 劫财克妻
  - LZ-08-06 妻灾
- 家庭/孝服/骨肉断语:
  - LZ-07-01 骨肉分离
  - LZ-07-02 灾病连绵
  - LZ-07-04 孤立少骨肉
  - LZ-07-06 孝服哭泣
- policy:
  - 以上内容仅作命书文化研究与术语源流参考
  - 不得铁口断寿、断病、断婚、断灾
  - 不替代医学、法律、心理、婚姻或财务建议

## 排盘约束

- procedures.md 5 条流程全部声明 `tool_dependency: tool.bazi.paipan`
- 禁止 LLM 手算大运、流年、节气浅深、起运岁数
- 所有具体排盘、起运、流年流月计算必须调用工具或可靠排盘程序

## 仍需复核

- 影印本复核:
  - 四库本
  - 守山阁本
  - 可下载公有领域扫描本
- 分层复核:
  - 原赋层
  - 徐子平注层
  - 释昙莹等异注层
- 跨书复核:
  - 《五行精纪》
  - 《李虚中命书》
  - 《三命通会》
  - 《渊海子平》

## 结论

该 pack 可作为 D2 ready candidate：本地全文已逐章进入图谱，短引证据 88/88 exact-match，通过 D2 evidence gate 的单书证据要求。它仍不应升级为最终权威 skill，因为尚未完成影印本逐字校勘、注文分层精修与跨书冲突消解。
