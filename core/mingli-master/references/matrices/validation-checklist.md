# Reference Pack 验收清单 (validation-checklist)

> 每个 reference pack 在 `status` 从 `drafting` 升级到 `ready` 之前，必须逐项通过本清单。
> 任何一项不通过 → 保持 `drafting` 或回退到 `pending`。

## A. Frontmatter 字段完整性（强制）

每个 pack 的 YAML frontmatter 必须包含且非空：

- [ ] `title`：典籍中文名
- [ ] `slug`：英文 slug，小写连字符
- [ ] `system`：所属体系（bazi / luming-nayin / ziwei / xingming / divination / san-shi / selection / fengshui / physiognomy）
- [ ] `school`：派系归属（可填多个）
- [ ] `source_layer`：必须是 `primary` / `commentary` / `modern` 之一
- [ ] `source_status`：`verified` / `partial` / `unverified` 之一
- [ ] `source_links`：至少 1 条；若无，必须 `unverified` 且 `status: blocked`
- [ ] `version_notes`：版本说明（四库本 / 道藏本 / 民国刊本 / CTP / 维基文库）
- [ ] `depends_on`：上游 slug 列表（可空，但必须显式 `[]`）
- [ ] `informs`：下游 slug 列表
- [ ] `core_use_cases`：至少 1 条
- [ ] `not_for`：至少 1 条
- [ ] `extraction_targets`：至少包含 `concepts / terms / rules / cautions` 中的 3 项
- [ ] `conflict_policy`：明文写出与谁冲突、如何裁判
- [ ] `validation_notes`：未核验项 / 待补字段
- [ ] `modern_notes`：现代流派单独区，不与原典规则混写

## B. 正文结构（强制）

正文必须包含以下章节（缺一不可）：

- [ ] `## Source`：版本、刊本、来源链接、是否四库 / 道藏 / 馆藏 / CTP
- [ ] `## Position In Lineage`：在所属体系中的位置（源流 / 主线 / 注释 / 旁证）
- [ ] `## Core Concepts`：核心术语表
- [ ] `## Operational Rules`：核心判断规则（短引 + 解释，不允许大段复制）
- [ ] `## Procedures Or Decision Flow`：操作流程或判断流程
- [ ] `## Cautions And Limits`：使用边界、不适用场景
- [ ] `## Conflicts With Related Texts`：与同体系其他典籍的差异
- [ ] `## Quote Index`：短引索引（每条 ≤ 80 字 + 出处链接 / 章节）
- [ ] `## Routing Keywords`：路由关键词（中文）
- [ ] `## TODO / Verification Gaps`：未核验、未完成项

## C. 内容质量

- [ ] 不存在大段（>200 字）原文复制
- [ ] 每条核心规则都有出处链或"待核验"标记
- [ ] 现代流派内容只出现在 `modern_notes` 或 `## Conflicts With Related Texts` 的现代区
- [ ] 不出现 LLM 自行排盘 / 起卦 / 起课的具体结果
- [ ] 涉及计算的部分必须以"工具需求 + 输入字段"的形式表达，不给计算输出
- [ ] 至少 1 条路由关键词与 1 条禁止使用场景

## D. 出处链

- [ ] 一线 reference（`source_layer: primary`）至少 1 条稳定来源链接（CTP / 维基文库 / 馆藏）或明确版本说明
- [ ] 不能以微博 / 公众号 / 抖音 / 短视频作为一线来源
- [ ] 链接必须是稳定 URL（不要带 session token）
- [ ] 若链接失效或仅在国家/大学图书馆有馆藏 → `source_status: unverified` 且在 `validation_notes` 标注"待馆藏复核"

## E. 依赖与路由

- [ ] `depends_on` 中列出的 slug 必须真实存在于 `manifest.yaml`
- [ ] `informs` 中列出的 slug 必须真实存在于 `manifest.yaml`
- [ ] `routing_keywords` 与 `matrices/routing-matrix.md` 中对应体系的关键词无明显矛盾
- [ ] `conflict_policy` 与 `matrices/conflict-policy.md` 的总裁判顺序一致

## F. 事实层工具声明

凡涉及以下计算的，pack 必须明确声明"工具需求 + 输入字段"，不允许 LLM 自算：

- [ ] 八字排盘（公历转干支、藏干、十神、大运、流年）
- [ ] 紫微排盘（命宫、十二宫、星曜、四化、限运）
- [ ] 七政四余（现代天文位置）
- [ ] 六爻 / 梅花起卦
- [ ] 大六壬起课
- [ ] 奇门排盘（明确飞盘 / 转盘 / 时家）
- [ ] 太乙排盘
- [ ] 择日历算（神煞、黄黑道、值日、宜忌）；若是嫁娶、修造动土、安葬、出行上任、开业交易、医疗或民俗对照，必须声明 `references/matrices/selection-fact-layer-profile.yaml` 对应 profile 的字段需求。
- [ ] 风水坐向（罗盘读数 / 户型图 / 楼层 / 元运）

工具声明必须能映射到 `references/tool-adapters.md` 中的 adapter contract：至少说明输入字段、输出字段、规则口径、缺失字段、版本/工具来源。

## G. 文件大小约束（Batch 0.5 修订）

> **重要**：本节对旧单文件 pack 生效（如 `references/bazi/ziping-zhenquan.md`）。
> Batch 0.5 起引入全书覆盖型文件组（§L.1），各文件分散为 7 个独立文件，单文件行数分别可控。
> 全书文件组的总行数允许超过 1500 行，但**每个单文件**必须满足 §G 的 1500 行限制。
> 具体规则见 §L.13。

- [ ] 旧单文件 pack：总长 ≤ 1500 行；超过 → 拆分为文件组（按 §L.1）。
- [ ] 全书文件组：每个单文件 ≤ 1500 行；超出则拆分该文件为子文件（如 `rules-part1.md` / `rules-part2.md`）。
- [ ] `Quote Index` 短引总数：旧单文件 ≤ 50 条；全书文件组的 `quote-index.md` 不设总数上限（因全书覆盖需要），但每条必须 ≤80 字，超出移入 `terms.md` 或 `rules.md`。

## H. 升级到 `ready` 的最终条件

只有 A-G 全部通过，且至少满足以下两项之一：

1. `source_status: verified`，且与至少 1 个上游 / 下游 pack 形成依赖闭环。
2. `source_status: partial`，但已声明清楚 `validation_notes` 中的全部未核验项，且核心规则可用。

不满足时维持 `drafting` 或 `pending`。

## I. 全局健康检查（manifest 维度）

- [ ] `manifest.yaml` 中每个 system 至少有 1 个 `status: ready` 的 pack（Batch 0 例外）
- [ ] 没有 pack `status: ready` 但 `source_status: unverified`
- [ ] 没有 pack `path` 指向不存在的文件
- [ ] 全部 `depends_on` 关系不构成循环

## J. 自检流程（建议主 skill 加载前执行）

```text
1. 解析 frontmatter → 检查 A 全部字段
2. 扫描正文章节 → 检查 B 全部章节
3. 计算正文长度 → 检查 G
4. 校验 source_links → 检查 D
5. 校验 depends_on / informs → 检查 E
6. 若 status == ready → 必须通过 H
7. 任一不通过 → 停止加载该 pack，回退到上一可用 pack
```

## K. Batch 0 QA Gate 结论（历史记录 + 2026-06-17 状态修正）

> **重要**：§L Full Book Distillation Gate 自 Batch 0.5 起优先于旧 §H/§K 的 ready 判定。以下 QA 记录仅作历史追踪；ready 判定一律按 §L.9。

- **QA1（已更新）**《三命通会》经 Batch 0.5→0.7 三步返工为全书覆盖型文件组，`full_book_coverage: 99%`。按 §L.9 重审后满足全部六项条件，`status` 可升 `ready`。`source_status` 维持 `partial`（四库本影印未复核）。
- **QA2（历史记录，已被 catalog 覆盖）** `ziping-zhenquan` 曾为旧单文件 drafting；当前 canonical catalog 已列为 `d2_status: ready`，实际路径为 `references/books/bazi/ziping-zhenquan/index.md`。使用时仍须区分沈孝瞻原典与徐乐吾评注。
- **QA3** `yuanhai-ziping` Batch 1A-1 已返工为全书覆盖型文件组，`status: ready`。
- **QA4** 双向依赖（`sanming-tonghui ↔ shenfeng-tongkao`、`yuanhai-ziping ↔ sanming-tonghui`）允许，pack 内已写明上下游关系。
- **QA5** `yuanhai-ziping` 的 `informs` 含 `sanming-tonghui, ziping-zhenquan, shenfeng-tongkao`。
- **QA6** `skill-draft/SKILL.md` 保持 `status: draft`；加载规则已改为按需加载文件组（§L.11）。
- **QA7（2026-06-17 修正）** 当前 bazi system 已有 7 个 ready pack：`sanming-tonghui`, `yuanhai-ziping`, `ziping-zhenquan`, `ditiansui-chanwei`, `qiongtong-baojian`, `shenfeng-tongkao`, `mingli-yueyan`。§I 全局健康检查在 bazi system 已满足。
- **QA8** 未核验占大多数属正常；`source_status` 维持 `partial` / `unverified` 直到四库本影印逐章复核。

## L. Full Book Distillation Gate（Batch 0.5 新增，2026-06-16 起生效）

> 本节是**全书覆盖型蒸馏**的强制门槛。在 §A-K 原有检查之上叠加。
> 从本节生效起，**所有** reference pack 必须满足本节才能升级到 `status: ready`。
> 仅做概要、路由、依赖关系而没有章节覆盖率，只能 `status: drafting`。

### L.1 强制目录结构

每个 pack 必须拆为文件组，目录位于 `references/books/{system}/{book-slug}/`：

```text
references/books/{system}/{book-slug}/
  index.md          # 入口索引：frontmatter、source、lineage、use_cases、not_for、loading guide
  chapter-map.md    # 全书章节地图（卷/篇/章/小目 + digest_status）
  terms.md          # 全书术语抽取
  rules.md          # 全书判断规则
  procedures.md     # 全书可操作流程
  quote-index.md    # 短引索引（不放整段长文）
  validation.md     # full_book_coverage、done/pending/skipped/unavailable 章节、版本核验、待核验项
```

### L.2 `index.md` 的职责

- 保留完整的 YAML frontmatter（`title / slug / system / school / source_layer / source_status / source_links / version_notes / depends_on / informs / core_use_cases / not_for / extraction_targets / conflict_policy / validation_notes / modern_notes`）。
- 只做**入口索引**：
  - Source（版本、刊本、来源链接、四库/道藏/馆藏/CTP）
  - Position In Lineage（在所属体系中的位置）
  - Core Use Cases / Not For（适用与不适用）
  - Loading Guide（主 skill 默认加载 index.md；需要细节时再加载 chapter-map / terms / rules / procedures / quote-index / validation）
  - File Map（列出本 pack 其余 6 个文件的职责）
- `index.md` **不** 放大段规则、术语、短引；只做路由与导航。

### L.3 `chapter-map.md` 的强制字段

- 必须覆盖**全书可得版本的全部卷 / 篇 / 章 / 小目**。
- 每个章节条目必须包含：
  - `slug`：章节标识（如 `vol-01/wuxing-shengcheng`）
  - `title`：章节标题（中文名）
  - `digest_status`：`done` / `partial` / `pending` / `skipped` / `unavailable`
  - `function`：一句话功能摘要（该章节在书中做什么）
  - `source_anchor`：出处位置（CTP chapter URL / 四库本卷次 / 影印页码）
  - `verified`：`true` / `false`（是否已对四库本影印复核）
  - `notes`：可选补充说明
- 不允许只列卷名而跳过小目；小目是章节地图的最小单位。
- 若章节极长（如卷八卷九的"日时断"几百条）→ 允许聚合到"日组"粒度，但必须列出全部日组（甲乙丙丁戊己庚辛壬癸各 12 时）。

### L.4 `terms.md` 抽取要求

- 按术语类型分组（如：基础术语 / 神煞 / 格局 / 十神 / 纳音 / 大运流年 等）。
- 每个术语：
  - `term`：术语名（中文）
  - `definition`：一句话定义（≤ 80 字）
  - `source_chapter`：出处章节 slug
  - `cross_system`：是否跨体系出现（若是，注明所属体系）
- 不允许把不同体系的同名词默认同义；必须显式标注所属体系。

### L.5 `rules.md` 抽取要求

- 每条规则：
  - `rule_id`：`R<数字>` 或 `<章节slug>/R<数字>`
  - `rule_statement`：规则陈述（≤ 120 字，短引 + 解释）
  - `source_chapter`：出处章节 slug
  - `applicable_to`：适用的问题类型
  - `caveats`：例外 / 边界 / 冲突
  - `verified`：`true` / `false`
- 不允许大段复制原文（单条规则正文 ≤ 200 字）。
- 每条规则必须有出处链或【待核验】标记。

### L.6 `procedures.md` 抽取要求

- 每个流程：
  - `procedure_id`：`P<数字>`
  - `name`：流程名
  - `inputs`：输入字段（包括工具需求，如 `tool.bazi.paipan`）
  - `steps`：步骤（不允许 LLM 自算排盘 / 起卦 / 起课 / 历算）
  - `outputs`：输出字段
  - `source_chapter`：出处章节 slug
- 涉及事实计算的流程只能写"工具需求 + 输入字段"，不得让 LLM 手算。

### L.7 `quote-index.md` 抽取要求

- 每条短引 ≤ 80 字（超过 → 移到 `terms.md` 或 `rules.md`）。
- 每条必须含：
  - `quote`：短引文本
  - `chapter`：出处章节 slug
  - `source_url`：CTP / 维基文库 / 馆藏链接
  - `verified`：`true` / `false`
- 不允许整段长文（> 200 字）进入本文件。
- 每条短引必须能回到原文定位。

### L.15 准确度与统计校准（新增）

若 pack 或下游 skill 声称“准确度”“命中率”“统计验证”“回测”，必须额外满足：

- 区分事实正确性、文本依据、规则应用、解释判断、用户反馈五层。
- 每个可验证判断必须具备：具体 claim、time_window、confidence_bucket、counter_evidence、outcome_status。
- 不允许用同一案例既调参又作为验证样本。
- 不允许只记录命中案例；miss / partial / unscorable 必须同样记录。
- 输出必须说明 `empirical_uncalibrated` / `empirical_calibrating` / `empirical_calibrated` 状态。
- 高风险或重话题仍受 `safety-and-versioning.md` 的 truth-first policy 约束：可以直说传统判断，但必须保留事实层、出处层、校准状态，不得伪装成现代实证事实。

### L.8 `validation.md` 强制字段

- `full_book_coverage`：0-100% 整数，表示"可得版本的全部章节"的覆盖率。
- `chapter_count_total`：全书可得版本总章节数（以 chapter-map.md 条目数为准）。
- `chapter_count_done`：`digest_status: done` 的条目数。
- `chapter_count_partial`：`digest_status: partial` 的条目数。
- `chapter_count_pending`：`digest_status: pending` 的条目数。
- `chapter_count_skipped`：`digest_status: skipped` 的条目数（需注明跳过原因，如"重复 / 注释 / 现代附录"）。
- `chapter_count_unavailable`：`digest_status: unavailable` 的条目数（需注明不可得原因，如"版本缺失 / 馆藏未开放"）。
- `verified_chapters`：已对四库本影印复核的章节列表。
- `pending_verification`：待核验章节列表 + 原因。
- `batch_progress`：按卷次列出已完成 / 未完成 / 未完成原因。
- `last_updated`：ISO 8601 日期。

### L.9 `status: ready` 的最低条件（替代 §H）

从本节生效起，`status: ready` 必须同时满足：

1. §A-G 原有检查全部通过。
2. L.1-L.8 强制目录结构齐全。
3. `full_book_coverage >= 95%`（按章节数计算，`done + partial + skipped_reason_valid` / `total`）；或明确声明"当前可得文本章节已全部覆盖"。
4. 每个章节条目都有 `digest_status`、`function`、`source_anchor`、`verified` 字段。
5. `validation.md` 的 `batch_progress` 按卷列出所有未完成项的原因。
6. 不允许"只有概要、路由、依赖关系，没有章节覆盖率"的 pack 升级。

**不满足时**：`status` 维持 `drafting`（不得用 `ready`）。`source_status` 维持 `partial` / `unverified`。

### L.9.1 D2 Evidence Gate（2026-06-16 新增）

> 本节修正 D1 批次暴露出的口径漂移：`partial` 可以表示"已做摘要但未逐字复核"，但不得被包装成已经完成的原文证据链。

从 D2 起，任何 pack 进入主 skill 可调用状态之前，必须额外满足：

- `quote-index.md` 只能放**可在本地 `references/fulltext/{system}/{slug}/fulltext.md` 中逐字定位**的短引。
- 模型改写、卷题摘要、规则总结、"某卷内容包括……"一律不得放入 `quote-index.md`；应移入 `rules.md`、`terms.md`、`chapter-map.md notes` 或 `validation.md known_gaps`。
- `quote_hit_ratio = exact_hits / quote_total` 必须 ≥ 90%。低于 90% 的 pack 只能是 `drafting`，不得作为一线 reference。
- `full_book_coverage` 必须同时报告两种口径：
  - `strict_coverage = (done + skipped_with_valid_reason) / chapter_count_total`
  - `loose_coverage = (done + partial + skipped_with_valid_reason) / chapter_count_total`
- `loose_coverage` 只能用于说明"已有草稿覆盖"，不得作为 `ready` 升级依据。
- 任何 `unavailable > 0` 的 pack 必须在 `validation.md` 明确写出不可得章节，并保持 `drafting`，除非它被拆成明确的 section pack（例如 `taiwei-fu`）。
- 粗粒度策略（如"64 卦不逐卦展开"、"数表不展开"、"代表性选录"）必须降级为索引层或 drafting；不得标为 full-book distillation 完成。
- 自动审计命令：

```bash
python3 scripts/audit_reference_catalog.py --require-local-fulltext
```

当前发布目录和统一出处清单位于 `references/catalog/D2_READY_REFERENCE_PACKS.yaml`；
完整转写只作本地研究输入，不进入 GitHub 或发布包。该审计是 D2 以后升级 / 回退 pack
状态的最低仓库证据。

### L.10 "全书覆盖"的精确定义

- "全书覆盖" = 摘要 + 术语抽取 + 规则抽取 + 流程抽取 + 短引索引，**覆盖可得版本的全部章节**。
- 不等于"全文复制"：不允许大段（> 200 字）原文搬运。
- 不等于"综述"：不是写一段 300 字的"本书大意"就算覆盖；必须有**章节级**的 digest。
- 章节级 digest = 该章节的功能摘要 + 术语抽取 + 规则抽取 + 短引索引。
- 大段枚举型章节（如卷八卷九的日时断）允许聚合为"日组"粒度，但必须列出全部日组。

### L.11 主 skill 加载约定

- 默认只加载 `index.md`。
- 需要查具体章节 → 加载 `chapter-map.md`。
- 需要查术语 → 加载 `terms.md`。
- 需要查判断规则 → 加载 `rules.md`。
- 需要查流程 → 加载 `procedures.md`。
- 需要查短引 → 加载 `quote-index.md`。
- 需要校验覆盖率 → 加载 `validation.md`。
- 不允许主 skill 一次性加载全部 7 个文件；按需加载。

### L.12 返工追溯

- 从本节生效起，所有**已有**的概要型 pack 必须返工为文件组结构。
- 返工完成前，对应 pack 的 `status` 必须设为 `drafting`，不得保留 `ready`。
- 返工顺序：先返工《三命通会》（Batch 0.5），再按 Batch 顺序返工其它 pack。

### L.13 文件大小约束修正（Batch 0.8 新增）

> 本节修正旧 §G，专门针对全书覆盖型文件组。

- 旧 §G"单 pack 总长 ≤1500 行"对**旧单文件 pack**（如 `ziping-zhenquan.md`）继续生效。
- 对**全书覆盖型文件组**（7 文件结构，§L.1），该约束改为：
  - **每个单文件** ≤ 1500 行（超出则拆分，如 `rules-part1.md` / `rules-part2.md`）。
  - 文件组总行数不设硬上限（因全书覆盖需要；当前三命通会约 2199 行，7 个单文件各自 ≤720 行）。
- 旧 §G"Quote Index 短引 ≤50 条"对旧单文件 pack 继续生效。
- 对全书覆盖型文件组，`quote-index.md` 短引总数**不设上限**（全书覆盖需要更多短引锚点），但每条必须 ≤80 字（§L.7）。

### L.14 抽取覆盖率（extraction_coverage）（Batch 1A-1.5 新增）

> 本节确保每个章节不仅出现在 `chapter-map.md`，而且确实被抽取产物引用。

- 对全书覆盖型文件组，每个 chapter-map.md 中的章节 slug 必须至少出现在 `terms.md` / `rules.md` / `procedures.md` / `quote-index.md` 中之一。
- 计算方式：`extraction_coverage = 被任一抽取文件引用的章节数 / chapter_count_total`。
- **ready gate 要求**：`extraction_coverage >= 95%`（建议 100%）。
- 若某章节确实不适合抽取规则/术语/流程/短引（例如纯重复条目或版本差异标注），必须在 `validation.md` 中写明原因。
- `validation.md` 必须记录 `extraction_coverage` 数值及未引用章节的配套说明（若有）。

---

## §M Source Acquisition Gate (Batch S0.5)

每本书进入蒸馏前必须通过以下检查：

### M.1 Raw Source 必要条件
- raw_source_status == acquired：本地 raw/ 目录下有完整文件且 checksum_sha256 已验证
- raw_source_status != acquired 的书不得进入 full-book distillation
- 仅有 source_anchor（在线链接）不等于已取得全文
- "可在线阅读" ≠ "已取得整本原文"

### M.2 Normalized Source 必要条件
- normalized_status == ready：normalized/ 目录下有完整标准化文本
- normalized_status != ready 的书不得进入 reference-pack 生成
- 标准化必须基于本地 raw source，不能基于在线浏览逐段拼凑

### M.3 覆盖率统计
- extraction_coverage 必须按卷/篇/章统计实际覆盖率
- 不允许用"有链接""有来源"代替覆盖率
- 覆盖率 = 已获取并标准化的章节数 / 总章节数 × 100%

### M.4 CTP 使用限制
- CTP (ctext.org) 仅可作为 source_anchor（证明出处、版本参考）
- CTP 不可作为 raw source 的默认获取方式
- 自动化批量下载 CTP 违反其 TOS，不允许
- 除非已通过合法渠道（API订阅/官方许可）取得本地全文，不得标记 raw_source_status: acquired

### M.5 Pre-source-acquisition Outputs
- Batch S0.5 之前生成的 reference packs（sanming-tonghui / yuanhai-ziping）为 pre-source-acquisition outputs
- 这些 pack 保持 status: ready，但需在后续用本地全文原文复核
- 复核完成前 source_status 字段注明 "pre-source-acquisition, pending local-text verification"

### M.6 蒸馏前置流程
完整流程：
1. source_anchor（证明出处）→ 
2. raw_source acquisition（合法获取整书原文）→ 
3. normalization（标准化为UTF-8纯文本）→ 
4. coverage QA（覆盖率统计）→ 
5. full-book distillation（全书覆盖型蒸馏）→ 
6. reference pack validation → 
7. skill draft integration
