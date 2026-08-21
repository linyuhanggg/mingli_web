# 玉照神应真经 — Validation

distillation_status: ready_candidate
source_status: normalized_ready
batch: D2

---

## D2 证据门

| check | result | evidence |
|---|---:|---|
| required_pack_files | pass | index / chapter-map / terms / rules / procedures / quote-index / validation |
| source_manifest | pass | `sources/manifests/yuzhao-shenying.yaml` 标 `normalized_status: ready`、`extraction_coverage: 100` |
| chapter_status_vocab | pass | 72 条均为 `done`，无 `partial / pending / unavailable` |
| chapter_coverage | pass | 72/72 strict coverage |
| quote_exact_match | pass | 51/51 短引逐字来自本地 `fulltext.md` |
| quote_length | pass | 51/51 短引压缩后 ≤80 字 |
| line_anchors | pass | quote anchors 均落在本地 12 行 fulltext 范围内；chapter-map 外链不作行锚 |
| rules_gap_repair | pass | 已补主题二职业/道德断语 7 条、主题五疾病体质断语 8 条 |
| safety_boundary | pass | 疾病、死亡、寿夭、盗贼/刑讼、职业贬义、婚配/六亲断语均 reframe |

## 完整性口径

- **本地 source**：维基文库四库本一卷，已规范化为 `references/fulltext/luming-nayin/yuzhao-shenying/fulltext.md`。
- **章节地图**：按赋文+注文混排特点切为 72 个主题条目；全部 `done`。
- **规则覆盖**：56 条 rule 覆盖核心方法、主题二职业/道德敏感断语、主题五疾病体质敏感断语、六亲婚配、五行正道。
- **短引覆盖**：51 条 quote 使用原文经句，不使用现代改写句。
- **verified=false**：只表示还未与影印/永乐大典逐句校勘；不影响本地 normalized source 的 D2 evidence chain。

## Safety-Redlines

- [x] 寿夭/死亡：不可铁口断寿、断死法；只作古籍语汇研究。
- [x] 疾病/体质：不得输出医学判断；现实健康问题转现代医学。
- [x] 盗贼/刑讼/官事：不得对真人作违法犯罪或司法预测。
- [x] 职业/身份贬义：僧道、师姑、屠儿、盗贼、孤女等标签全部 reframe 为古代社会分类话语。
- [x] 婚配/六亲/子嗣：不得作现代婚姻、伴侣、子女规划判断。

## 与其他书互参点

| 互参方向 | 关系 | 处理 |
|---|---|---|
| ↔ `li-xuzhong-mingshu` | 同属早期禄命；本书更像断语集 | 并读，不互相覆盖 |
| ↔ `luoluzi-sanming` | 赋文体系相近 | 以珞琭子作理论骨架，本书作断语证据 |
| ↔ `wuxing-jingji` | 后世汇编吸收本书语汇 | 后续若冲突，以五行精纪汇编义为注释层，本书作早期源头 |
| ↔ 子平体系 | 历史上游/旁源 | 不混用格局、用神、调候 |

## 已知限制

1. 原文与张顒注混排，当前 reference pack 按主题切片，没有把每条注文独立编号。
2. 影印本逐句校勘未做，因此全部 `verified=false`。
3. 全书敏感断语密集，后续主 skill 调用时必须默认走 reframe/safety 输出层。

**验收结论**：当前 pack 达到 D2 ready candidate，可进入后续 skill 蒸馏和主 skill 路由；不得直接用于真人疾病、寿夭、司法、婚配硬断。
