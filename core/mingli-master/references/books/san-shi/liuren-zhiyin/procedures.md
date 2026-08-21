# 《六壬指南 / 六壬指南注解》Procedures

## LP-01 Load and provenance gate

1. 先读 `source-manifest.yaml`，确认状态是“完整可检索注本已入库、原本影印已取得、未全本逐页校勘”。
2. 读 `chapter-map.md` 选语义段；不要从 normalized 的 `Source Chapters` 包装表取引文。
3. 读 `conflict-notes.md` 检查章数、卷次、异文和现代增补边界。
4. 任何引用先在 `quote-index.md` 取 `quote_id`，再执行 `LR-14` 来源层守门。
5. 若用户要求 NLC 精确页码或版面字形，而当前没有页图对照记录，返回 `scan_page_not_collated`，不伪造页码。

## LP-02 Deterministic chart contract

### Required input

- `query_time.local_datetime`
- `query_time.timezone`
- `calendar_policy.solar_term_boundary`
- `time_policy`，例如正时或用户明确指定的其他口径
- `location`，仅在所用 adapter 明确需要经度或真太阳时参数时提供
- `question_domain`

### Required adapter output

- 日干、日支及阴阳
- 月将、占时、天地盘
- 四课上下神、去重课数、直接克关系
- 伏吟、反吟、八专标志
- 初中末三传及生成路径
- 十二天将、旺相休囚、空亡、刑冲合害
- 六壬本系统神煞及每项来源 profile

缺任一取用关键字段就停止，不由语言模型补算。

## LP-03 Core use-taking decision tree

```text
INPUT: validated plate from LP-02

1. Resolve direct overcoming relations with LR-01.
   a. Any lower-overcomes-upper candidate exists:
      ignore every upper-overcomes-lower candidate.
   b. One candidate -> use it.
   c. Multiple candidates -> LR-02.
   d. Otherwise inspect upper-overcomes-lower in the same one/multiple way.

2. If a direct candidate resolved, stop branch selection and chase middle/final
   transmissions on the heaven plate.

3. If there is no direct overcoming:
   a. is_fuyin -> LR-06.
   b. is_fanyin -> LR-07.
   c. is_bazhuan / two distinct lessons -> LR-08; do not try remote overcoming.

4. For the remaining three- or four-lesson plates, try remote overcoming with LR-03.
   a. Upper gods overcoming the day stem -> 蒿矢.
   b. Only if none, day stem overcoming upper gods -> 弹射.
   c. A resolved remote candidate ends branch selection.

5. If there is no direct or remote overcoming:
   a. three distinct lessons -> LR-05 别责.
   b. four distinct lessons -> LR-04 昴星.
   c. any other geometry -> inconsistent_chart_or_lineage.

6. Any tie that survives the cited rule -> unresolved_by_this_pack.
   Do not import an unlabelled tie-break from another lineage.
```

### Decision record

每次运行至少保存：`selected_rule_id`、候选列表、被排除候选及原因、初中末生成路径、adapter 版本、冲突或停止状态。

## LP-04 Interpretation stack

按以下顺序解释，后层不得反向改写前层：

1. **课体与发用**：记录取用规则、日辰主客和直接/遥克方向。
2. **初中末**：按 `LR-09` 分为发端、移易、归计。
3. **问题字段**：按 `LR-11` 加载卷二分类入口或卷三对应章节。
4. **神将与旺衰**：按 `LR-10` 修饰作用方式和强弱。
5. **刑冲合害、空墓进退**：作为结构关系，不以单字机械下断。
6. **神煞**：最后调用 `LR-12`，只作同向辅证或冲突提示。
7. **占验**：只作历史/现代案例比较，永不从单例反推必然规则。

## LP-05 卷三案例检索

1. 在 `chapter-map.md` 的 1-29 章中按问题域选章。
2. 对每个案例分别截取“课例字段”“原断/旧断”“张洪史注或复盘”，不要把相邻行合并成一个作者声音。
3. 遇 `增补课例`、1998 年、潍坊、工商局、现代金额或现代机关语境，标 `modern_case` 或 `modern_weifang_case`。
4. 第 30 章始终加 `chapter_30_anomaly=true`；可用 `LR-13`，但不能归入陈公献 1-29 章主体。
5. 案例与规则冲突时，保留冲突到 `conflict-notes.md`，不为追求“应验”改写规则。

## LP-06 卷四神煞复核

1. 由 adapter 计算神煞，输出神煞名、起例、落宫、来源 profile。
2. 回到卷四对应层：岁煞 L2533-L2561，月/季煞 L2562-L2753，旬煞 L2754-L2757，干煞 L2758-L2779，支煞 L2780-L2796。
3. 检查同向核心因素：干支、初中末、神将、旺衰、刑克至少一项明确支持。
4. 没有同向支持则标 `unconfirmed_shensha`；表格疑字则标 `scan_collation_required`。
5. 只输出“辅证/不支持/冲突”，不让神煞选初传、单独断事或跨系统复用。

## LP-07 Citation check

1. 从 `quote-index.md` 取得 `quote_id`、短引、normalized 行号和 `source_layer`。
2. 在 fulltext 指定行逐字命中短引。
3. 检查该行不属于 normalization scaffold。
4. 检查规则卡中的 `normalized_lines` 包含该引文行。
5. 输出格式至少包含：`quote_id`、`fulltext.md Lx`、`source_layer`、归属置信度。

## Stop conditions

- 时间、月将、四课或盘式来源不完整。
- 候选经本书分支后仍并列。
- 用户要求影印页码但尚无逐页映射。
- 只有现代课例，找不到可定位规则。
- 神煞表格疑似因空格、简繁或 OCR 失真。
- 来源层不能确定且用户要求精确作者归属。
- 请求把文化文本当医疗、法律、投资、婚育、灾祸等现实保证。

## Output contract

```yaml
source_book: "六壬指南 / 六壬指南注解"
source_state: "完整可检索注本已入库、原本影印已取得、未全本逐页校勘"
chart_source: "adapter name and version"
selected_rule_id: "LR-xx"
decision_path: []
source_evidence:
  - quote_id: "LZ-Qxxx"
    normalized_line: "Lx"
    source_layer: "..."
conflicts: []
shensha_role: "not_used | corroborating | conflicting | unconfirmed"
claim_scope: "textual interpretation, not factual prediction"
```
