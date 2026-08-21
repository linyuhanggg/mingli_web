# 星命溯源 · 验收清单

distillation_status: ready_candidate
source_status: normalized_ready
source_scope: "维基文库四库本卷一至卷四；卷五仅见提要著录，未进入本地 source"

---

## D2 证据门

| check | result | evidence |
|---|---:|---|
| required_pack_files | pass | index / chapter-map / terms / rules / procedures / quote-index / validation |
| source_manifest | pass | `sources/manifests/xingming-suyuan.yaml` 标 `normalized_status: ready`、`volumes_acquired: 4`、`volumes_total: 4` |
| chapter_status_vocab | pass | `done / skipped`，无 `digested / not_processed` 等非标准状态 |
| chapter_coverage | pass | 65 done + 1 skipped = 66/66 strict coverage |
| quote_exact_match | pass | 28/28 短引可在 `fulltext.md` 中压缩命中 |
| quote_length | pass | 28/28 短引压缩后 ≤80 字 |
| line_anchors | pass | 锚点最大至 `L460`，不超过本地 fulltext 行数 |
| safety_boundary | pass | 寿夭、死法、疾病、产亡、贬义女命标签封存为 evidence，不进入输出硬断 |

## 完整性口径

- **可蒸馏范围**：本地 normalized source 已收卷一至卷四，按四库本维基文库页面完成 D2 证据修复。
- **卷五处理**：四库提要称有《观星心传口诀补遗》，但本地 source 未收卷五正文；`chapter-map.md` 标为 `skipped`，不得伪造规则或补写摘要。
- **卷四后篇处理**：卷四 L349-L460 含大量寿夭、死法、疾病、子嗣、女命贬义断语；已作为整段 safety-redlines 封存，保留出处，不做真人输出硬断。
- **全书蒸馏原则**：可用源文必须全覆盖；不可用/残缺文本必须显式 `skipped`，不得以概述冒充整本蒸馏。

## 文件完备性

- [x] `index.md`：典籍定位、版本、school_lineage、强制工具依赖、蒸馏边界。
- [x] `chapter-map.md`：66 条章节/条目，65 条 `done`，1 条卷五 `skipped`。
- [x] `terms.md`：40 条术语，与 `guotian-jing` 互通。
- [x] `rules.md`：51 条规则 XR-01-01 至 XR-08-05，含通用 caveats 与 safety-redlines。
- [x] `procedures.md`：7 个流程 XP-01 至 XP-07，含强制工具依赖与输出包装。
- [x] `quote-index.md`：28 条逐字短引，D2 audit 可解析。
- [x] `validation.md`：本文件。

## 工具依赖与硬约束

- [x] 强制 `tool.xingming.bindisk`：起盘、行限、神煞、十一曜、十干化曜。
- [x] 不允许手算排盘 / 起课 / 排限。
- [x] 古书行度因岁差不可直接套用，必须工具校正。
- [x] 本书的“用神”指星曜取用，不得与子平用神混用。

## Safety-Redlines

- [x] XR-04-03 飞廉浮沉羊刃：具体死法全屏蔽。
- [x] XR-04-05 闌干煞缢死：自杀/横死相关内容全屏蔽；遇现实风险转危机干预。
- [x] XR-06 女命专章：所有贬义标签按古代礼教叙事 reframe。
- [x] XR-06-04 妇人产亡：生育健康相关内容转现代妇产医学。
- [x] XR-08：卷二后天口诀与卷四寿夭案例整体封存。

## 与其他书互参点

| 互参方向 | 关系 | 处理 |
|---|---|---|
| ↔ `guotian-jing` | 同属七政四余；本书偏理论原型，果老偏实操扩展 | 起例从果老，心法从本书 |
| ↔ `ditiansui-chanwei` | 七政四余 vs 子平 | 不混用用神、格局、行运概念 |
| ↔ `qiongtong-baojian` | 七政四余 vs 子平调候 | 不以星命结论覆盖子平调候 |
| ↔ `shenxiang-quanbian` | 旁证层 | 相法只作旁证，不反推命盘 |

## 已知限制

1. 卷三多为四字篇名及短段定义，`chapter-map.md` 保留近似行锚（如 `L107 起`），后续可做更细段落锚。
2. 卷四后篇没有把每条寿夭案例做成可操作 rule；这是 safety 设计，不是遗漏。
3. 卷五未入本地 source，当前不能宣称“卷五已蒸馏”。

**验收结论**：当前 pack 可作为 D2 ready candidate 进入后续蒸馏/主 skill 路由，但仅覆盖本地合法缓存中可取得的卷一至卷四；卷五必须保持 skipped，除非以后补到合法全文。
