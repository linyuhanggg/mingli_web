---
name: 六爻全流程逐屏规格与显示内容合同
date: 2026-08-21
task: T-0821-UIUX-3
status: accepted-design-input
role: 五术 flow-spec 第二份（格式沿用 2026-08-21-bazi-flow-spec.md 样板）
authority: 视觉与交互语言见 DESIGN.md（2026-08-21 版）；字段形状以 web/src/view-models/registry.ts 与 contracts/schemas/views/liuyao-chart-v1.schema.json 为准；六爻已按用户 2026-08-21 裁决开放为 A 档主线，本文按主线产品写
---

# 六爻全流程逐屏规格

流程是同一路由 `/liuyao` 上的状态机（DESIGN §7）：

```text
S0 入口态 → S1 问题与起卦记录 → S2 提交确认（inline 摘要） → S3 卦盘态（免费） → S4 深读选择/支付 → S5 报告态
                                                              └→ S6 异常态族（贯穿全程）
```

每屏给出：目的 / 布局（360·768·1024·1440）/ **显示内容合同**（区块、字段路径、呈现规则、缺失时行为）/ 交互 / 验收点。字段路径全部对齐 `LiuyaoChartViewModel`（`liuyao-chart/v1`）现有定义；需要展示但拿不到的数据标 `ALGO-GAP`（编号 `GAP-LY-xx`），汇总在文末。

**通用红线**（每屏适用，同八字样板）：无 raw JSON / snake_case / 内部 ref；空字段整块不渲染不占位（DESIGN §19.2）；无合成评分与吉凶（G2）——`hard_verdict` 在本合同里恒为 null，UI 任何位置不得出现成败/吉凶断语；引文原样透传（G1）；页面级不横滚；四视口 + 键盘 + reduced-motion（G6）。

**六爻特有红线**：客户端绝不从六个爻值推卦名、纳甲、世应——爻值→卦名是排盘行为，只能由服务端产出（DESIGN §17）。客户端只允许把用户输入的 6/7/8/9 直接映射成爻画图形（阴/阳/动静是输入值的图形等价，不是推导）。

---

## S0 入口态（pristine）

**目的**：让用户 3 秒内明白「这里回答一个具体问题、我要先真实起卦、我会得到一座可核验的爻塔」。

**布局**：

- 1440/1024：术标行（印章「六爻」+ 术名 + 一句适用说明）通栏；下方双栏——左录入面板 456–496px，右空盘剪影（最小 420px）。
- 768：单列；术标行 → 剪影横条（`LiuyaoLineTower` 的 silhouette 压缩为六道空爻位横条，高 88–120px）→ 录入面板。
- 360：单列；剪影隐藏。

**显示内容合同**：

| 区块 | 显示什么 | 来源 | 规则 |
|---|---|---|---|
| 术标行 | 印章「六爻」+「六爻」+ 适用说明（如「就一个具体问题起卦，逐爻核验事实」）| 静态文案 | H1 为术名本身；适用说明 ≤20 字 |
| 空盘剪影 | `LiuyaoLineTower` 的 `silhouette` 态：自下而上六个空爻位框 + 纳甲/六亲/六神三列空表头 + 世/应两个空标记位 | 静态结构 | 不含任何示例爻画/干支/卦名；配「提交后由服务端生成，可核验」；静态无动效 |
| 起卦须知行 | 一句：「需要你先用真实硬币（或既有记录）完成六次起卦，系统不代掷、不补数」 | 静态文案 | 这是六爻与其他术入口的关键差异，必须在首屏说清，避免用户以为点按钮就出卦 |
| 能力边界行 | 一句当前能力：免费确定性卦盘 + 古法命中可核验；深读按 Offer 状态 | 能力接口 | 不用工程词 |

**验收点**：首屏（1440×900）同时可见术标行、起卦须知、表单前 3 个字段、剪影；无编号承诺清单。

---

## S1 问题与起卦记录

**目的**：拿到真实问题 + 真实起卦记录。六爻录入的重心与其他术相反——出生资料退场，**六次起卦过程是主角**，录入器本身就该长成爻塔的方向（自下而上），让用户在填的时候已经在「搭」自己的卦。

**字段清单**（现有 `product-input-form` 字段保留，标签不变；新增一项见 GAP-LY-01）：

| 字段 | 必填 | 控件与规则 |
|---|---|---|
| 当前问题 | 是 | 文本；帮助「一事一卦，问题越具体越好」 |
| 问题类别 | 否（新增） | select：求财 / 暂不指定。选「求财」才会激活盘面上的用神证据模块；其余类别的角色规则未接入前不提供选项（GAP-LY-01/02）。帮助文案：「选择类别后，盘面会给出该类问题的用神角色与古籍出处」 |
| 起卦方式 | 是 | select：三枚硬币 / 手动记录（现有 `focus` 字段值 `coins`/`manual` 不变） |
| 事件时间 | 是 | 年/月/日 + 时/分 + 时区 + 地点（现有字段）；帮助「以实际起卦的时刻为准，用于月建日辰」。六爻现无时间口径选择器，默认民用钟表时间——在帮助句里写明，不新增控件 |
| 六次起卦过程 | 是 | `LineRecorder`（重排现有六个 select，见下） |

**`LineRecorder`（六次起卦记录器）——本屏核心重排**：

- 六行**自下而上**排列：视觉最底行是「初爻 · 第 1 次」，最顶行是「上爻 · 第 6 次」。现状六个平铺下拉从上往下排，与卦的方向相反，用户脑内要倒一次序——这是现状录入最大的认知摩擦。
- 每行 = 行头（初爻/二爻…上爻 + 第 N 次）+ 四个 SegmentedControl 选项：`老阴（6 · 动）`、`少阳（7）`、`少阴（8）`、`老阳（9 · 动）`。每个选项内嵌对应爻画小图（`LineGlyph`，见「共享卦象组件族」）：阴=断横、阳=实横、动爻加标记。选中即时在行头右侧显示该爻画。
- 三枚硬币模式下，行区上方多一张静态对照卡：「三背=老阳 9 · 二背一字=少阳 7 · 一背二字=少阴 8 · 三字=老阴 6」。**只是固定字典的提示图，用户仍然自己选值**——系统不代掷、不从「背/字」输入推值（保持现有「不会随机补数」纪律，帮助文案沿用现有 fieldset 说明）。
- 手动记录模式无对照卡，直接选四值。
- 校验沿现有合同：六次全部完成才能提交；首个未完成行聚焦（现有 `liuyao-line-N` 锚点保留）。
- 360：每行四选项两行换排（2×2），行高 ≥44px；768+ 单行四段。

**明确不做**：页面内摇卦动画/随机起卦按钮。客户端 RNG 生成的「掷币」是伪造起卦事实，违反数据真实性纪律；参考站的「系统摇卦」不采用（reference-analysis 已裁决）。

**验收点**：录入器自下而上、行头爻名可见；六行未完成时提交被拦并聚焦首错；键盘可完整操作四段选择；360 无横滚。

---

## S2 提交确认（inline 摘要）

提交按钮上方常驻摘要卡（非弹层，同八字 S2-B）：

| 显示什么 | 来源 | 规则 |
|---|---|---|
| 问题 / 问题类别 / 起卦方式 / 事件时间与地点 | 用户输入回显 | 只回显输入 |
| 六爻记录小图 | 用户输入的 6 个值 → `HexagramFigure`（输入直显态） | 六个爻画自下而上堆叠 + 动爻标记。**不显示卦名、不显示上下卦名**——那是排盘结果，等服务端 |

**验收点**：摘要卡爻画顺序与录入器一致（下=初爻）；无卦名出现；确认后进入 S3 骨架。

---

## S3 卦盘态（免费确定性卦盘）——本流程的主屏

**目的**：把 `liuyao-chart/v1` 的全部事实做成一座可扫读、可联动、可核验的爻塔；A 档能力（用神角色 + 特定爻 + 月令旺衰三条已验证规则）以证据形式全部上屏，零断语。

**布局**：

- 1440：工作条通栏 → 求测信息条通栏 → 双栏：左盘面区 520–560px（爻塔，六爻比四柱宽——多出六神/伏神/变卦列），右阅读区（其余模块流），两栏独立滚动。
- 1024：同上，右栏 ≥360px；爻塔可收起伏神列（点击列头展开）。
- 768/360：单列：工作条（精简）→ 求测信息条 → 爻塔（窄态：六神列并入行内 chip，变卦列折叠为「查看变卦」切换）→ 粘性章节导航 → 模块流。章节锚点：`卦盘 / 用神证据 / 关系事实 / 古法命中 / 深读`（无数据的锚点不渲染）。

### 工作条

| 元素 | 来源 | 规则 |
|---|---|---|
| 返回 | 路由 | 回入口态，保留已填表单 |
| 求测摘要 | `question`（截断 ≤24 字）+ `subject_ref` 标签 | 一行：「问：这次求财如何？」 |
| 更多 | 保存/导出/分享/历史 | 按登录态与能力显隐 |

（六爻无时间层 chips——没有大运/流年概念，工作条比八字短。）

### M1 求测信息条（G3：起卦口径）

| 显示什么 | 字段 | 规则 |
|---|---|---|
| 问题全文 | `question` | 原样展示，超长折叠「展开」 |
| 起卦方式 | `core_facts.casting_method` | 人话标签（三枚硬币记录 / 手动记录 / 提供完整卦象） |
| 起卦时间与月建日辰 | `core_facts.calendar`、`core_facts.casting`（松散对象，GAP-LY-03 钉形） | 一行：「起卦 2026-08-21 22:10 · 月建酉 · 日辰丙午」。月建日辰是旺衰证据的输入，必须在盘面顶部可见 |
| 旬空 | `core_facts.xunkong`（松散，GAP-LY-03） | 「旬空：辰巳」；同时在爻塔对应爻位加「空」角标 |

缺失时：`core_facts` 为 null 则本条只显示 `question` + 起卦方式回显；`calendar`/`xunkong` 为 null 各自整项不渲染。

### M2 爻塔（`LiuyaoLineTower`，盘面主体）

结构：六行自下而上（`lines[].position` 1→6 = 视觉下→上），行 = 一爻，列 = 事实类别。表头两卦名居顶。

**卦名头**：

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 本卦 | `primary_hexagram.name` + `upper_trigram`/`lower_trigram` | 20px 域字卦名 + 小字「上艮下兑」+ `TrigramGlyph`×2；卦宫/卦性（六冲六合等）见 GAP-LY-04 |
| 变卦 | `changed_hexagram.*`（可为 null） | 同构；null 时整列不渲染（静卦无变卦是正常事实，不显示「无变卦」占位） |

**行列合同**（每行一爻）：

| 列 | 字段 | 呈现 |
|---|---|---|
| 六神 | `core_facts.six_spirits[]`（下标 0=初爻） | 13px 中性 chip（青龙/朱雀/勾陈/腾蛇/白虎/玄武）；不做吉凶染色 |
| 伏神 | `core_facts.hidden_lines[]`（松散，含所伏爻位；GAP-LY-03） | 灰阶小字「伏：子孙巳火」，仅有伏神的爻位渲染；1024 以下折叠进爻位详情 |
| 本卦爻 | `lines[].value/moving` → `LineGlyph`；纳甲 `core_facts.najia[]`（干支+五行，松散；GAP-LY-03）；六亲 `core_facts.six_relatives[]` | 爻画 28px 行高；动爻用传统标记（老阳 ○ / 老阴 ×）+ 朱砂色微点，不只靠颜色；纳甲干支 16px 域字按五行染 `--element-*`（染色用前端固定字典，事实文本一律来自服务端）；六亲 13px 标签 |
| 世应 | `core_facts.shi_ying`（松散；GAP-LY-03） | 「世」「应」两枚 16px 印章式标记挂在对应行，世爻行整行 1px 墨线加重——世应是六爻扫读的第一锚点 |
| 变卦爻 | `core_facts.changed_plate_lines[]` + `changed_najia[]` + `changed_six_relatives[]`（均可 null） | 动爻行显示变出之爻的爻画+纳甲+六亲；静爻行该列淡显本爻（传统排盘惯例：变卦列完整六爻，动爻行是焦点）；三字段任一缺失则该子项不渲染 |

缺失时：`core_facts` 为 null → 爻塔只渲染卦名头 + 六个爻画（`lines` 是必有字段），其余列整列不渲染。松散字段解析失败按缺失处理，不渲染猜测值。

**交互**（DESIGN §21.1/§21.4）：悬停/聚焦/点击锁定任一爻行 → 该爻在用神证据、关系事实、古法命中里的相关条目同步高亮；反向：点击证据条目里的爻引用 → 爻塔对应行高亮并滚动到可视。方向键上下遍历爻行，Esc 解锁。语义替代：爻塔同步输出 `<table>`（行=爻、列=事实）。

### M3 用神证据（A 档核心模块，`core_facts.useful_spirit_selection`）

这是六爻 A 档相对 B 档多出来的主体内容，占右栏首位。全模块的呈现纪律：**角色和强弱是「古籍规则 + 盘面事实」的对齐展示，不是结论**。`reason` 与 `unresolved_checks` 原样人话透传。

**M3a 角色卡**（`role_adjudication`，仅 `status="adjudicated_question_role_set"` 时渲染）：

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 问题类别 | `question_class`（现仅 finance） | 「求财类问题」 |
| 用神 | `primary_relative`（妻财） | 大标签 + 爻塔中所有妻财爻行金线徽章联动 |
| 原神 | `supporting_relatives`（子孙） | 次级标签 |
| 忌仇提示 | `obstacle_attention_relatives`（兄弟/官鬼/父母） | 中性小标签行，文案「传统上需留意的角色」，禁「凶」字 |
| 出处 | `source_ref`（黄金策 HJC-R009，`source_anchor`） | `EvidenceBadge` → 点开 `EvidenceDrawer` 显示原文锚点（同八字 M12 抽屉组件） |
| 未决检查 | `unresolved_checks[]` | 折叠「尚未裁定的检查 N 项」，展开逐条人话 |

`status="not_requested"` 时（未选问题类别）：整卡收缩为一行引导「选择问题类别后可查看用神角色与古籍出处」+ 返回修改入口；不渲染空表。

**M3b 特定爻裁定**（`role_adjudication.specific_line_adjudication`）：

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 裁定状态 | `status` 四枚举 | 人话映射：唯一可见候选已定位 / 单一动爻候选已定位 / 多个候选并存（列出 `visible_candidate_lines`，不替用户挑）/ 卦中不现（提示看伏神） |
| 选中爻 | `specific_line_selection`（可 null） | 非 null 时爻塔对应行金线描边 + 「用神」角标 |
| 依据 | `derivation_basis` + `selection_source_ref`（HJC-R009 或增删卜易 ZR-04-04） | 一句依据 + `EvidenceBadge` |

**M3c 强弱证据表**（`strength_evidence.by_relative`，`status="candidate_only"` 时渲染）：

按六亲分组（妻财/子孙…），每个候选（`candidates[]`）一行：

| 列 | 字段 | 呈现 |
|---|---|---|
| 爻位来源 | `source`（本卦爻/变爻/伏神）+ `line` | 「四爻（本卦）」，点击联动爻塔 |
| 纳甲 | `najia`（松散） | 干支五行小字 |
| 月令状态 | `seasonal_adjudication.seasonal_state`（旺相休囚死）+ `strength_band`（旺相/休囚） | 状态字 + band 标签；`line_element`/`month_element` 进悬停详情；出处 ZR-05-05 `EvidenceBadge` |
| 信号 | `signals[]`（月破/日冲/旬空/动爻/得令/失令） | 中性 chip 列；`value` 为布尔时只在 true 渲染 |

表尾固定一行边界句（来自 `fact_status`/`requires_school_adjudication` 的固定人话）：「以上为月令强弱证据，取用与断事属流派裁定，本页不代作结论」。`status="not_available"` 的六亲整组不渲染。

### M4 关系事实

| 区块 | 字段 | 呈现 |
|---|---|---|
| 爻间关系 | `core_facts.relation_facts[]`（松散；GAP-LY-03） | 「日辰冲二爻」「四爻动化回头生」等事实行，每行可点击联动爻塔 |
| 回头生克 | `core_facts.returning_relations[]` | 同上 |
| 世应动爻关系 | `core_facts.shi_ying_moving_relations` | 「世爻临动爻」等 |
| 月日对爻强弱 | `core_facts.month_day_strength[]` | 每爻一行「初爻子水：月休 · 日克」；已在 M3c 出现过的候选爻不重复成段，此处是全爻清单 |
| 六神档案 | `core_facts.six_spirit_profile` | 折叠卡：起六神的日干依据（「丙日起腾蛇」类事实） |

全部松散对象，键名钉形见 GAP-LY-03；任一为 null 整块不渲染。

### M5 古法命中抽屉（§19.1 / §21.3）

`core_facts.source_conditioned_patterns[]`，与八字 M12 完全同构复用：

| 显示什么 | 字段 |
|---|---|
| 命中条目行 | `title` + `source_pack` 人话名（黄金策/增删卜易） |
| 状态 | `status="predicate_matched_not_verdict"` 固定显示「条件命中，非断语」 |
| 展开 | `source_anchor` 原文锚点、`fact_paths` 映射为爻塔高亮、`predicate_audit` 逐条「为什么命中」 |

### M6 免费基础摘要 + 深读入口

同八字 M11/M13 合同：摘要只复述已上屏事实（本卦变卦、动爻数、世应位置、用神角色——若已裁定），不新增判断；深读入口按 Offer 状态渲染（能力接口），锁定态用 locked 文案基线。

**S3 状态清单**：loading（爻塔结构骨架，六行灰条自下而上）/ ready / partial（`core_facts=null`：卦名+爻画可用，其余模块不渲染，显示一行「本卦已排出，明细事实生成中/暂不可用」按实际状态）/ error（StatusPanel error 态 + 重试）/ unavailable。

**验收点**：1440 双栏独立滚动无页面横滚；爻行↔证据双向联动；键盘可遍历爻行；`hard_verdict`/成败字样全页 0 处；360 变卦列折叠可切换。

---

## S4 深读选择与支付 / S5 报告态 / S6 异常态族

三屏合同与八字 S4/S5/S6 完全同构（bazi-flow-spec 对应章节为准），此处只列差异：

- S4 深读 SKU 文案面向「问事」而不是「命局」；样例引用来自六爻证据（用神/世应），不得出现吉凶承诺。
- S5 报告态 Claim Unit 的证据锚点指向爻塔（爻位/关系/古籍命中），点击回跳 S3 对应高亮；六爻深读文本供给已有真实产出（2026-08-12 dogfood 有 accepted copy），密度与 Claim 类型对齐 §19 的缺口并入 GAP-BZ-02 同族跟踪，不另开编号。
- S6 增加一个六爻特有异常：**起卦记录不完整**（服务端校验拒绝）——错误文案指回 S1 首个缺失爻行。

---

## 共享卦象组件族（与梅花复用，边界钉死）

前端只做一套卦象图形，两术共用。梅花规格（2026-08-21-meihua-flow-spec.md）引用同一清单：

| 组件 | 输入 | 用途 | 归属 |
|---|---|---|---|
| `LineGlyph` | `{ yang: boolean, moving: boolean, size: s/m/l }` | 单爻画：阳实横/阴断横，动爻加传统标记（○/×）+ 朱砂微点 | 共享 |
| `HexagramFigure` | 6×LineGlyph props + `silhouette?` | 六爻画自下而上堆叠；S1/S2 输入直显、S3 卦名头、梅花三卦横列都用它 | 共享 |
| `TrigramGlyph` | `{ name: string }`（乾/兑/离/震/巽/坎/艮/坤） | 三爻小卦画 + 卦名，自绘笔画（不用 Unicode ☰ 系列，字体渲染不可控） | 共享 |
| `HexagramHeader` | `{ name, upper_trigram, lower_trigram }` | 卦名 + 上下卦组成行 | 共享 |
| `LiuyaoLineTower` | `liuyao-chart/v1` | 爻塔：HexagramFigure 拆行嵌入行网格，挂纳甲/六亲/六神/世应/变卦列 | 六爻专属 |
| `MeihuaTriad` | `meihua-chart/v1` | 本互变三卦横列：3×(HexagramHeader + HexagramFigure) + 体用标注 | 梅花专属 |

**复用边界**：纳甲/六亲/六神/世应/伏神单元格是六爻专属行内容，不下沉到共享组件；体/用标注是梅花专属，不进 `HexagramFigure`。共享层只管「画卦」，事实标注各自在专属组件里挂。

---

## ALGO-GAP 清单（算法/后端开发的输入）

### GAP-LY-01 · 问题类别结构化输入未接线（P1，阻塞 A 档用神模块激活）

- 缺什么：`useful_spirit_selection.question_context.classification_source` 要求 `explicit_structured_input`，但 web 任务输入没有问题类别字段，用户无法触发 `role_adjudication`（永远 `not_requested`）。
- 期望：输入合同新增 `question_class` 枚举（首期仅 `finance`），穿过 Request Compiler 到 Runtime；表单按 S1 合同加 select。
- 影响：不补则 M3a/M3b 永不出现，A 档开放对用户不可见。

### GAP-LY-02 · 用神角色集仅覆盖求财（P2）

- 缺什么：schema/registry 把角色裁定硬类型化为 `finance`/妻财一类。婚恋、事业、健康、行人等常见问类无角色规则。
- 期望：按 GAP-LY-01 的枚举逐类扩展，每类角色集必须带已验证古籍 `source_ref`（同 HJC-R009 模式）；没有可验证出处的类别宁缺勿滥。

### GAP-LY-03 · core_facts 松散对象钉形（P1，阻塞爻塔逐行对位）

- 缺什么：`najia`、`hidden_lines`、`shi_ying`、`xunkong`、`calendar`、`casting`、`month_day_strength`、`line_facts`、`relation_facts`、`returning_relations`、`shi_ying_moving_relations`、`six_spirit_profile`、`changed_najia`、`changed_plate_lines` 在 view schema 里全是无键约束的松散对象。数据已真实产出，但前端做爻塔行对位没有稳定键可依赖，只能容错猜测——违反显示合同精神。
- 期望的数据形状（示例）：`najia[i] = { position: 1-6, stem, branch, element }`；`shi_ying = { shi_line: 1-6, ying_line: 1-6 }`；`xunkong = { xun: string, branches: string[] }`；`hidden_lines[i] = { position, relative, stem, branch, element }`；`calendar = { casting_datetime, month_branch, day_stem_branch }`。以 Runtime 实际输出为准钉进 schema + registry，不改算法语义。
- 影响：不补则 M1/M2/M4 只能按通用键值渲染，爻塔退化为定义列表——重蹈八字结果页覆辙。

### GAP-LY-04 · 卦宫与卦性事实未暴露（P2）

- 缺什么：`primary_hexagram` 只有 name/upper/lower。传统卦盘头部的卦宫（「艮宫」）与卦性（六冲/六合/游魂/归魂）是确定性事实且是古籍命中常用前件，schema 无字段。
- 期望：`hexagram` 增加 `palace`、`attributes[]`（枚举），本卦变卦同构。

### 术语释义词表（并入 GAP-BZ-03，不另开编号）

八字词表扩六爻词条：世/应、六神、纳甲、旬空、月破、伏神、用神/原神。同一张常量表，同一交付。

---

## 实现顺序建议

1. **先行（数据已真实可用）**：共享卦象组件族（LineGlyph/HexagramFigure/TrigramGlyph，纯前端）→ S1 `LineRecorder` 重排（纯前端，现有字段）→ S3 爻塔骨架 + 卦名头 + 爻画列（`lines`/`primary_hexagram`/`changed_hexagram` 是必有强类型字段）。
2. **随 GAP-LY-03 钉形跟进**：纳甲/六亲/六神/世应/伏神列 + M1 口径条 + M4 关系事实。
3. **随 GAP-LY-01 接线跟进**：M3 用神证据全模块（view 侧类型已完备，只等输入激活）。
4. M5 古法命中抽屉复用八字 M12 组件，随八字侧组件产出即接。
