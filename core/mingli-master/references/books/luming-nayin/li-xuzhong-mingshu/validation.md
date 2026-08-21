# 李虚中命书 — Validation

distillation_status: ready_candidate
source_status: normalized_ready
batch: D2

---

## D2 证据门

| check | result | evidence |
|---|---:|---|
| required_pack_files | pass | index / chapter-map / terms / rules / procedures / quote-index / validation |
| source_manifest | pass | `sources/manifests/li-xuzhong-mingshu.yaml` 标 `normalized_status: ready`、`volumes_acquired: 3`、`volumes_total: 3` |
| chapter_status_vocab | pass | 120 条均为 `done`，无 `partial / pending / unavailable` |
| chapter_coverage | pass | 120/120 strict coverage |
| quote_exact_match | pass | 120/120 短引逐字来自本地 `fulltext.md` |
| quote_length | pass | 120/120 短引压缩后 ≤80 字 |
| line_anchors | pass | `fulltext.md` 行锚均落在 85 行范围内 |
| sixty_jiazi_rules | pass | 卷上 60 甲子已完整展开为 LX-01-01~LX-01-60 |
| safety_boundary | pass | 寿夭、疾病、婚配、贫贱、职业断语均要求 caveats/reframe |

## 完整性口径

- **本地 source**：维基文库四库本三卷，已规范化为 `references/fulltext/luming-nayin/li-xuzhong-mingshu/fulltext.md`。
- **章节地图**：三卷共 120 条，全部 `done`。
- **规则覆盖**：104 条 rule；卷上 60 甲子不再是抽样，而是完整展开。
- **短引覆盖**：120 条 quote；前 60 条覆盖六十甲子，后 60 条覆盖贵神、卷中理论、卷下运限与六合。
- **verified=false**：表示未与影印本逐句校勘；不影响本地 normalized source 的 D2 evidence chain。

## Safety-Redlines

- [x] 寿夭/疾病：不可作真人寿命、疾病预测；现实健康问题转现代医学。
- [x] 婚配/子嗣/六亲：不得作现代伴侣、子女、亲属关系硬断。
- [x] 贫贱/贵贱：只保留古代阶层话语，不作现代社会地位判断。
- [x] 职业/身份：不以纳音条文给出现代职业判定。
- [x] 跨体系隔离：本书为禄命纳音，不混用子平用神、调候或紫微星曜。

## 与其他书互参点

| 互参方向 | 关系 | 处理 |
|---|---|---|
| ↔ `luoluzi-sanming` | 同为禄命上游，珞琭子偏赋文理论 | 并读；本书提供六十甲子与三元九命骨架 |
| ↔ `yuzhao-shenying` | 玉照偏断语与神将，本书偏纳音总枢 | 本书为祖本，玉照作断语旁证 |
| ↔ `wuxing-jingji` | 五行精纪为后世汇编 | 后续冲突以五行精纪为汇编注释，本书作早期源头 |
| ↔ 子平体系 | 历史上游/旁源 | 不替代日主、格局、用神、调候 |

## 已知限制

1. 正文与小字注混排，当前 rules/quotes 以正文为主；注文未逐条独立编号。
2. 四库影印逐句校勘未做，因此全部 `verified=false`。
3. 原书前半与后半时代层混杂，四库已指出后半多宋人增饰；调用时须保留传本层说明。

**验收结论**：当前 pack 达到 D2 ready candidate，可进入后续 skill 蒸馏和主 skill 路由；不可直接用于真人寿夭、疾病、婚配、贫贱硬断。
