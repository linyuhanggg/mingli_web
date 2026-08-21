---
slug: liuren-miben
file: procedures
source_status: complete_text
---

# 《大六壬秘本》使用流程

## LP-00 先区分“查书”与“用课”

### A. 文本检索

适用于书目、卷次、术语、类象、异文、作者层和原文引用。

1. 从 [chapter-map.md](./chapter-map.md) 定位卷和行界。
2. 从 [terms.md](./terms.md) 确认词义与来源层。
3. 从 [quote-index.md](./quote-index.md) 取得 exact quote。
4. 输出 `quote_id`、normalized 行号、source layer 和校勘状态。
5. 不因为查到一句占辞就声称已完成实际起课。

### B. 实际课断

适用于用户给出具体问题、时间或课盘，要求按大六壬判断。

1. 先执行 LP-01。
2. 字段完整后执行 LP-02。
3. 仅在问题需要时加载类象、射覆或专项分门。
4. 最后执行 LP-06、LP-07。

## LP-01 验证确定性 adapter

- **source evidence**: LM-Q035, LM-Q052, LM-Q053
- **source lines**: L2968-L2982, L3886-L3900
- **source layer**: `transmitted_body` + `mixed_body_commentary`
- **rule card**: LM-R00

### 输入

```yaml
query:
  text: "具体、单一的占问"
  time: "ISO-8601"
  timezone: "IANA timezone"
  location: "required by calendar policy"
adapter:
  name: "required"
  version: "required"
  rule_profile: "required"
  guiren_profile: "required"
  validation_status: "pass"
calendar:
  boundary_policy: "required"
  day_pillar: "required"
  hour_pillar: "required"
  month_general: "required"
chart:
  earth_plate: {}
  heaven_plate: {}
  four_lessons: []
  three_transmissions: []
  heavenly_generals: {}
  xunkong: []
  lesson_type: "required"
  derivation_trace: []
```

### 校验步骤

1. 确认时间、时区和历法边界可复算。
2. 校验日干与时干关系、月将、四课、三传均来自同一 adapter run。
3. 校验四课/三传数量、天地盘映射、天将分布和旬空字段完整。
4. 校验 `lesson_type` 带生成路径，不只是自然语言标签。
5. 将输入和 adapter 版本写入结果 trace。

### 停止

- `validation_status != pass`
- 任一必需字段缺失
- 用户给出的课盘与 adapter 重排不一致且无法确定采用哪一版
- 将本书卷十三/卷十五课名文字直接当排盘算法
- 只有图片中的八字/六壬盘但没有经过结构化识别和复核

停止时返回缺失或冲突字段，不补算、不猜盘。

## LP-02 五要权衡主流程

- **source evidence**: LM-Q039-LM-Q048
- **source lines**: L3105-L3261
- **source layer**: `transmitted_body` + 明标增录/引书层
- **rule cards**: LM-R09-LM-R14

1. **问题分类**：从三十类中选择与当前问题有关的维度。
2. **角色映射**：记录彼此、主客、内外、尊卑；不能复用上一个问题的角色。
3. **事实底盘**：列日辰上神、初中末、生克、旺衰、空陷。
4. **天时地利**：用已声明的 `strength_profile` 与落宫状态。
5. **虚实**：分旬空、落空/陷空、初中末空和填实。
6. **动静**：日辰为静态基础、三传为动态过程，并检查相生/克陷和专门动静标记。
7. **始终**：初传发端、中传移易、末传归计，分别写支持、阻碍和变化。
8. **迟速**：只给相对快慢和候选时间尺度；日期交历法 adapter。
9. **反证检查**：多吉仍查旺鬼，多凶仍查救制；吉将受伤、凶神受制要重新加权。
10. **简法优先**：先写干、三传生克和正时基础解释，再决定是否加入聚散或其他变法。

输出必须保留 `decision_path[]`，让每一结论能回指 adapter 字段和 rule id。

## LP-03 类象检索

- **source evidence**: LM-Q003, LM-Q007, LM-Q013-LM-Q017
- **source lines**: L82-L970
- **source layer**: `transmitted_body` + 个别异文/署名说法
- **rule cards**: LM-R01, LM-R02, LM-R05

1. 选择唯一类象表：
   - 月将/十二支：卷一
   - 十二天将：卷二
   - 六旬神煞：卷三
   - 天官加十二辰：卷五
   - 八卦将神：卷六
   - 五行形色与旺衰：卷七
2. 记录符号、所临、天将、旺衰、空陷和问题域。
3. 只输出满足输入条件的候选，不列出同一支的全部可能。
4. 若需要现实判断，回到 LP-02 用课传结构复核。
5. 神煞只标辅证/冲突；不得改变发用或课名。

## LP-04 射覆流程

- **source evidence**: LM-Q009-LM-Q017
- **source lines**: L377-L970
- **source layer**: `transmitted_body` + mixed variants
- **rule cards**: LM-R03-LM-R05

1. 通过 LP-01 取得刚柔日、日上神、支上神、发用、所临、旺衰和空亡。
2. 刚日先看日上，柔日先看支上，同时记录初传。
3. 先做“有无/虚实”判断；多重空象未解时不继续猜物。
4. 再按五行、旺衰、形状、颜色、新旧、生死、表里顺序生成候选。
5. 卷五、卷六用于缩小候选，不单独决定答案。
6. 输出候选及支持字段，不把射覆结果写成确定的视觉识别事实。

## LP-05 专项分门检索

- **source evidence**: LM-Q018-LM-Q019, LM-Q028, LM-Q049-LM-Q064
- **source lines**: L971-L1764, L2407-L2863, L3544-L5332
- **source layer**: `transmitted_body` + `mixed_body_commentary` + Jin notes
- **rule cards**: LM-R06, LM-R15, LM-R16, LM-R18

1. 先确定 `question_domain`，一次只选一个主门。
2. 按 [chapter-map.md](./chapter-map.md) 选择主卷：
   - 歌诀补充：卷八、卷九
   - 玉田歌分门：卷十二
   - 终身/空亡/争讼/课名：卷十五
   - 人宅/修造/婚产/商贾/诉讼：卷十六
   - 三才/病/盗/行人/逃亡/假借：卷十七
3. 先运行 LP-02，再加载专项段。
4. 选择类神后必须复核空旺、生克、合害和三传。
5. 同一事项跨卷重复时，分别标卷次，不把相邻歌诀拼成新规则。
6. 命中卷十五“两事”结构时只标 `dual_issue_candidate`，回到问题事实核实。
7. 未进入 `rules.md` 的断语标 `text_lookup_only`。

## LP-06 跨书冲突处理

1. 每条证据保留 `source_book`、`quote_id`、行号、source layer 和 adapter profile。
2. 与《大六壬大全》或《六壬指南》一致时可标 `corroborating`。
3. 不一致时标 `conflicting`，并展示各书原句和前置条件。
4. 不以“集大成”“入门书”“秘本”名号自动决定覆盖关系。
5. 计算规则只能来自独立验证的 adapter profile；reference pack 只解释来源差异。
6. 若选择某一 profile，记录选择理由；不能静默混合。

重点冲突见 [conflict-notes.md](./conflict-notes.md)：卷数、旺衰 profile、始入/元首/重审、比邻/知一、返吟/伏吟“入与不入”、空亡例外及注层归属。

## LP-07 引用与影印页校验

- **rule card**: LM-R19

1. 从 [quote-index.md](./quote-index.md) 读取 exact quote。
2. 在 runtime fulltext 声明行逐字命中。
3. 标注 `transmitted_body`、`mixed_body_commentary`、`jin_editorial_note`、`named_copyist_note`、`scan_collated_junction` 或 `normalization_scaffold`。
4. 只有以下三处可给已复核扫描页：
   - L1592 -> NCL 第 72 页
   - L3912 -> NCL 第 179 页
   - L5158 -> NCL 第 234 页
5. 其他 normalized 行不得按比例换算影印页；返回 `scan_page_not_collated`。
6. 字符串命中不等于作者归属正确，也不等于术数预测有效。

## Stop Conditions

- 缺可复算占时、时区、历法边界或 adapter 版本。
- 四课、三传、天将、旬空、课名无结构化生成路径。
- 旺衰、贵人或课名 profile 未声明。
- 卷十三/十五异文会改变算法结果。
- CTP 电子文本无法分清正文与注层，而问题要求精确作者归属。
- 用户要求未校位置的准确影印页码。
- 只有单一神煞、类神或歌诀，缺主课结构。
- 请求把“完整结构索引”说成“每句已规则化”或“全本已校勘”。

## Output Contract

```yaml
source_book: "大六壬秘本"
source_state: "十七卷完整转写；三处章界影印补字；未全本逐页校勘"
query_domain: "required"
chart_source:
  adapter: "name@version"
  rule_profile: "required"
  guiren_profile: "required"
  validation_status: "pass"
selected_rules:
  - rule_id: "LM-Rxx"
    adapter_fields_used: []
decision_path: []
source_evidence:
  - quote_id: "LM-Qxxx"
    normalized_line: "Lx"
    source_layer: "..."
    scan_page: "verified page or null"
conflicts: []
unresolved: []
claim_scope: "source-bounded textual interpretation over deterministic chart facts"
```
