---
name: 八字全流程逐屏规格与显示内容合同
date: 2026-08-21
task: T-0821-UIUX-1
status: accepted-design-input
role: 五术 flow-spec 样板（紫微/六爻/梅花/大六壬按同一格式展开）
authority: 视觉与交互语言见 DESIGN.md（2026-08-21 版）；字段形状以 web/src/view-models/registry.ts 与 contracts/schemas/views/bazi-chart-v1.schema.json 为准；本文把「每屏显示什么」钉死，算法开发按 ALGO-GAP 清单补数据
---

# 八字全流程逐屏规格

流程是同一路由 `/bazi` 上的状态机（DESIGN §7）：

```text
S0 入口态 → S1 录入 → S2 提交确认（弹层） → S3 盘面态（免费） → S4 深读选择/支付 → S5 报告态
                                              └→ S6 异常态族（贯穿全程）
```

每屏给出：目的 / 布局（360·768·1024·1440）/ **显示内容合同**（区块、字段路径、呈现规则、缺失时行为）/ 交互 / 验收点。字段路径全部对齐 `BaziChartViewModel`（`bazi-chart/v1`）现有定义；需要展示但拿不到的数据标 `ALGO-GAP`，汇总在文末。

**通用红线**（每屏适用）：无 raw JSON / snake_case / 内部 ref；空字段整块不渲染不占位（DESIGN §19.2）；无合成评分与吉凶（G2）；引文原样透传（G1）；页面级不横滚；四视口 + 键盘 + reduced-motion（G6）。

---

## S0 入口态（pristine）

**目的**：让用户 3 秒内明白「这是排八字的地方、我要填什么、我会得到一张什么样的盘」。取代现状的大标题 + 编号承诺清单模板。

**布局**：

- 1440/1024：术标行（印章「八字」+ 术名 20–24px + 一句适用说明）通栏；下方双栏——左录入面板 456–496px，右空盘剪影（最小 420px）。
- 768：单列；术标行 → 剪影横条（88–120px 高的四柱空格结构条）→ 录入面板。
- 360：单列；术标行 → 录入面板；剪影隐藏（不推开首屏表单）。

**显示内容合同**：

| 区块 | 显示什么 | 来源 | 规则 |
|---|---|---|---|
| 术标行 | 印章「八字」+「八字」+ 一句适用说明（如「从出生时刻建立四柱，查看可核验的盘面事实」）| 静态文案 | H1 为术名本身；不用长句喊话标题；适用说明 ≤20 字 |
| 空盘剪影 | `BaziPillarMatrix` 的 `silhouette` 态：年/月/日/时四列表头 + 天干/地支两行空格 + 下方五行五个空计数位 | 静态结构 | 不含任何示例干支或数值；配一句「提交后由服务端生成，可核验」；静态无动效 |
| 能力边界行 | 一句当前能力：免费确定性盘面 + 古法命中可核验；深读按 Offer 状态 | 能力接口 | 不用绿色状态框、不用「已接入」等工程词面向用户 |

**验收点**：首屏（1440×900）同时可见术标行、表单前 4 个字段、剪影；无编号清单；无 30px+ 长句 H1。

---

## S1 录入

**目的**：低摩擦拿到最少必要资料；错误在本机先拦；游客可完整走通。

**字段清单**（现有 `product-input-form` 字段保留，标签不变）：

| 字段 | 必填 | 控件与规则 |
|---|---|---|
| 受测对象 | 否 | 文本；帮助「可以填写“本人”或便于自己识别的称呼」 |
| 历法 | 是 | SegmentedControl 公历/农历 |
| 性别 | 是 | SegmentedControl 男/女；帮助说明用于大运顺逆 |
| 出生日期 | 是 | 年/月/日；360 下 2×2 或分步，禁四列硬塞 |
| 出生时间 | 是* | 时/分 +「不知道出生时间」开关；开关开启时时分禁用并说明影响（时柱与时间层不可用） |
| 出生地点 | 建议 | 国内三级联动 / 海外搜索；选中后自动填时区 |
| 出生时区 | 自动 | 选地点自动带出；海外可改；IANA 名 |
| 高级选项（折叠） | 否 | 时间口径（民用钟表时间/当地视太阳时）、晚子时口径；每项一句人话说明 |
| 档案复用 | 登录后 | 已存受测人档案一键回填 |

**即时反馈**：

- 填完时+分后，时间字段旁显示民用时辰提示：「05:55 属卯时区间（民用钟表口径，未含真太阳时修正，以结果页时间口径为准）」。仅做固定映射的 UI 提示，不做任何排盘推导（DESIGN §17）。不回显农历转换（见 GAP-BZ-05）。
- 校验错误：就近红字 + 顶部错误摘要 + 首错聚焦（现有合同）。

**主按钮**：「排盘」，全宽墨底，48px。

**验收点**：360 无横滚；键盘可完整填写提交；`validation-error` 态首错聚焦；未知时辰路径可提交。

---

## S2 提交确认（弹层，两种触发）

**A. 缺出生地确认**（METIS 两段式的显式化）：

> 标题「未填写出生地」；正文「将按东经 120° 标准时排盘，不做经度修正与真太阳时修正。出生地会影响时柱边界的判定。」；按钮「返回补填」（次）/「按标准时排盘」（主）。

**B. 常规提交摘要**（inline 卡，不是弹层；提交按钮上方常驻）：

| 显示什么 | 来源 | 规则 |
|---|---|---|
| 受测对象 / 性别 / 历法 / 出生日期时间 / 地点 / 已选口径 | 用户输入回显 | 只回显输入与已选项，不做任何客户端推导（不显示农历换算、不显示干支预览） |

**验收点**：弹层焦点圈禁；Esc 关闭返回表单；确认后进入 loading（S3 骨架）。

---

## S3 盘面态（免费确定性盘面）——本流程的主屏

**目的**：把 `bazi-chart/v1` 的全部事实做成一张可扫读、可联动、可核验的盘，密度 ≥ 青囊（G5），零断语（G2）。

**布局**：

- 1440：工作条通栏 → 时间口径条通栏 → 双栏：左盘面区 480–520px（四柱矩阵 + 大运轨），右阅读区（其余模块流），两栏独立滚动。
- 1024：同上，右栏 ≥360px。
- 768/360：单列：工作条（精简）→ 口径条 → 四柱矩阵 → 粘性章节导航 → 模块流。章节锚点：`盘面 / 日主月令 / 五行 / 旺衰证据 / 格局候选 / 大运 / 神煞 / 关系 / 古法命中 / 深读`（无数据的锚点不渲染）。

### 工作条

| 元素 | 来源 | 规则 |
|---|---|---|
| 返回 | 路由 | 回入口态，保留已填表单 |
| 资料摘要 | `subject_ref` 标签 + `core_facts.calendar_normalization.effective_datetime` | 一行：「本人 · 1994-04-30 05:55（已按口径修正）」；分享页按隐私投影不显示精确时刻（G3 边界） |
| 时间层 chips | `time_layers[]`：`layer_id` / `label` / `available` / `unavailable_reason` | available=false 可见但 disabled，tooltip 显示 `unavailable_reason`；当前层朱砂下划线 + 字重（不只靠颜色） |
| 更多 | 保存/导出/分享/历史 | 按登录态与能力显隐；360 收进「更多」抽屉 |

### M1 时间口径条（G3）

| 显示什么 | 字段 | 规则 |
|---|---|---|
| 采用时间策略 | `calendar_normalization.time_basis.policy`、`true_solar_time.status/policy` | 人话标签（「民用钟表时间」/「当地视太阳时」） |
| 修正量 | `time_basis.longitude_correction_seconds` / `equation_of_time_seconds` / `total_correction_seconds`、`standard_meridian_degrees` | tabular 数字；0 也如实显示 |
| 排盘采用时刻 | `calendar_normalization.effective_datetime` | 年月日时分 |
| 边界状态 | `time_basis.boundary.distance_seconds` / `correction_changes_hour_branch` / `within_uncertainty` | 未跨界=收进「详情」折叠；跨界=展开醒目 |
| 晚子时口径与换日 | `calendar_convention.zi_hour_policy` / `day_rollover`、`day_boundary.zi_policy_advanced_day_pillar` | 人话标签 |
| 变柱标注 | `calendar_normalization.changed_pillars[]` | 非空时通栏醒目：「该修正改变了 X 柱」+ 朱砂标注对应矩阵列头 |
| 节气锚点 | `solar_terms.previous/next {name, datetime, is_month_boundary_jie}`、`month_switch_policy` | 「谷雨 → 立夏（月界节）」一行 |

缺失时：`calendar_normalization` 为 null 则整条不渲染（不出现「暂无口径」占位）。

**默认态纪律**：多数盘不跨界——口径条默认是一行平静的信息 +「详情」展开，不做戏剧化提示。

### M2 四柱矩阵（`BaziPillarMatrix`，盘面主体）

结构：列 = 年/月/日/时（`pillars[].position`），行 = 事实类别。日主格（日柱天干）朱砂描边常驻。

| 行 | 字段 | 呈现 |
|---|---|---|
| 天干（大字行） | `pillars[].stem` | 40px 域字，按五行染 `--element-*`（五行归属由 `ten_gods`/`day_master.element` 等服务端事实对应，不做客户端推五行——干支→五行为固定字典，允许前端常量映射用于**染色**，不用于生成事实文本） |
| 天干十神 | `core_facts.ten_gods.heavenly_stems[]`（按 `position` 归列）`ten_god` | 13px 标签；日柱显示「日主」 |
| 地支（大字行） | `pillars[].branch` | 40px 域字，五行染色；被 `xunkong.branches` 命中的地支加「空」角标 |
| 藏干 | `core_facts.hidden_stems[]`（`branch` + `stems[]`） | 每列纵向小字堆叠，28→16px 递减 |
| 藏干十神 | `core_facts.ten_gods.hidden_stems[]` | 与藏干逐一对位 |
| 纳音 | `core_facts.nayin[].name` | 16px |
| 十二长生 | `core_facts.twelve_growth_stages[].stage` | 16px；行头释义走 GAP-BZ-03 词表，只解释「是什么」 |
| 神煞 | `core_facts.shensha_auxiliary.calculated_items[]`（`matched_positions` 归列，显示 `name`） | 中性 chip，不吉凶染色；列内 >3 个折叠「+N」 |
| 关系连线 | `core_facts.branch_relations[]`（`relation_type` / `positions` / `branches`） | 矩阵下缘弧线连接对应列，中性色 + 关系名标签（合/冲/刑/害/会），禁吉凶色 |

缺失时：任一行数据为 null 该行整行不渲染；`core_facts` 为 null 时矩阵只渲染四柱大字（`pillars` 是必有字段）。

交互（DESIGN §21.1/§21.4）：悬停/聚焦/点击锁定任一干支格 → 其藏干、十神、关系连线、五行计数贡献同步高亮（边框+底色+字重）；方向键遍历格位，Esc 解除锁定。语义替代：矩阵同步输出 `<table>` 语义结构。

### M3 日主与月令

| 显示什么 | 字段 |
|---|---|
| 日主 | `core_facts.day_master.stem/element/polarity`（「丙 · 火 · 阳」） |
| 月令 | `core_facts.month_command.branch/label/main_qi/main_qi_element`（「辰月 · 主气 戊（土）」） |
| 季节剖面 | `core_facts.seasonal_profile.season/month_qi/temperature/moisture` |
| 调候标记 | `core_facts.tiaohou_markers.markers[]/temperature/moisture` + `scope` | `scope` 边界句原样显示（「仅作月令气候参照，不等于调候用神结论」） |
| 三垣 | `core_facts.san_yuan.tai_yuan/ming_gong/shen_gong` + `source` + `boundary` |

### M4 五行盘点

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 五行计数（明/藏） | `element_balance[]`（element/value/`display_text`）+ `core_facts.element_inventory.visible_stem_branch_counts[]` / `hidden_stem_occurrence_counts[]` + `scope` | 每行五行名（域色）+ 明/藏两组计数点（不是进度条，无底轨）；`display_text` 原样用作行文案；`scope` 作脚注 |

禁：雷达图总评、主气/次气结论、「食伤旺秀」类标签（青囊反例，G2）。

### M5 旺衰证据（不是评分）

数据根：`core_facts.interpretive_candidates.strength`（`status: "evidence_only"`，`hard_verdict: null`）。

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 月令状态（有据） | `seasonal_state` + `seasonal_state_source_rule_id`；`month_order_adjudication.source_ref{pack, rule_id, source_anchor}` | 「月令状态：相」+ 金线证据徽章（点开走 §19.1 引文卡链路）；`whole_chart_strength_verdict`/`useful_god_verdict` 恒为 null——不渲染任何总判 |
| 同类与生扶计数 | `same_element_occurrences`、`resource_element` + `resource_occurrences`、`all_element_occurrences[]` | 中性两列「同类 X 见 / 生扶 X 见」事实清单 |
| 未裁定边界 | `boundary`、`month_order_adjudication.unresolved_checks[]` | 原样显示，不折叠隐藏 |

### M6 格局候选

`interpretive_candidates.structure`（`status: "candidate_only"`）：`month_main_qi` / `month_main_qi_ten_god` / `main_qi_visible` / `visible_positions[]` / `boundary`。标题固定带「候选」二字；`boundary` 必显。

### M7 合化候选

`interpretive_candidates.following_and_transformation`（`status: "requires_classical_adjudication"`）：`stem_combination_candidates[]`（with_position/stems/candidate_element/status）、`branch_formation_candidates[]`、`boundary`。每条带「待古法裁定」状态词。

`salience_signals[]`（mechanical_candidate）与 `reasoning_tools`（键名不固定）：按 §19.2 遍历渲染，未知键原值显示，`caveats` 必显。此两块默认收进「更多机械候选」折叠。

### M8 大运轨（左盘面区，矩阵下方）

数据根：`core_facts.luck_cycles`。

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 大运序列 | `cycles[]`（sequence/pillar/start_age_years/end_age_years） | 横向轨道，每步一格（干支域字 28px + 年龄区间 tabular）；1440 十步一行，360 横向容器内滚动（保留首格） |
| 起运依据 | `status`/`direction`+`direction_rule`/`start_age_rule`/`start_age_years`/`boundary_term{name,datetime}`/`interval_days`/`approximate_start_datetime` | 收进轨道下「起运依据」折叠行 |
| 缺项 | `unavailable[]` | 原样列出 |

`status: "not_calculated_missing_gender"` 时整轨收缩为一句「未提供性别，无法确定大运顺逆」；`sequence_only` 时显示序列但年龄列整列不渲染。

### M9 流年/流月/流日层（时间层切换后的盘面叠加）

数据根：`core_facts.year_layers[]` / `month_layers[]` / `day_layers[]`。**当前 owner 结果未产出这三组字段（实测 missingRuntimeField，见 GAP-BZ-01），时间层 chips 显示 disabled + 原因；以下为数据到位后的合同**：

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 流年干支与十神 | `year_layers[].year/ganzhi/stem_ten_god/branch_hidden_ten_gods[]` | 矩阵右侧追加「流年柱」列（§21.2：容器不卸载，只过渡新列与标记） |
| 流年与本命关系 | `year_layers[].branch_relations[]`（relation_type/natal_position/natal_branch/transit_branch） | 连线叠加到矩阵对应列，中性标注 |
| 结构变化候选 | `year_layers[].structural_changes`（`status: "mechanical_candidates_only"`，`hard_verdict: null`） | 右栏「本年机械候选」清单，带候选语义 |
| 当年所在大运 | `year_layers[].active_luck_cycle` | 大运轨对应格高亮 |
| 年内分段 | `year_layers[].ganzhi_segments[]`（start/end/ganzhi/…） | 折叠时间轴 |
| 流月/流日 | `month_layers[]`/`day_layers[]`（BaziTemporalLayer：granularity/period/ganzhi_segments/active_transits/structural_changes/…） | 同构呈现，粒度标签区分 |

### M10 神煞明细（右栏）

`core_facts.shensha_auxiliary`：`calculated_items[]`（name/target_branch/anchor_positions/anchor_branches/matched_positions/status）逐条列出「名 + 落柱 + 依何柱起」；`evaluated_rules[]` 供「为什么」展开（rule_id/anchor_position/anchor_branch/target_branch/matched）；`boundary` 与 `cannot_override[]` 原样显示。神煞名释义走 GAP-BZ-03 词表；出处锚点缺失见 GAP-BZ-06。

### M11 免费基础摘要（§8.1 槽位 5）

固定模板、零裁决的机械投影，只允许引用本页已渲染字段：「日主{day_master.stem}{element}（{polarity}）· 生于{month_command.label}，主气{main_qi}；月令状态{seasonal_state}（有据）；五行分布见上；大运{cycles.length}步已列。」缺任一字段则该子句整句去掉。不出现任何强弱/喜忌/吉凶词。

### M12 古籍命中抽屉（§19.1 / §21.3）

| 显示什么 | 字段 | 呈现 |
|---|---|---|
| 收起态计数徽章 | `core_facts.source_conditioned_patterns[].length` | 「命中古法 N 条 · 可核验」金线徽章；N=0 时整块不渲染 |
| 每卡 | `title` / 原文（经 `evidence_ref` 解析的 verbatim quote，域字宋体）/ `predicate_audit`（显式常量表可读化）/ `source_pack`+`source_anchor`（书名+行号） | 三段缺一不可；`fact_paths` 不进正文；边界句「只呈现条件命中，不作断语」 |
| 盘面锚点 | `fact_paths` → 矩阵格位映射 | 命中格位旁金点标记（§21.3 一级），悬停「有 N 条古法涉及此处」（二级），点击滚动至对应卡（三级） |

### M13 深读入口

服务端 Offer 驱动：无 Offer =「测试期未开放」一行（不渲染价格卡）；有 Offer = 名称/范围/价格/`reading_version_id` 绑定，进入 S4。游客点击 → 登录弹层原地接管。

**S3 验收点**：G5 密度并排截图（1440/768 vs 青囊同盘）；矩阵键盘遍历；联动高亮三通路（悬停/键盘/点击锁定）；时间层 disabled 原因可见；G2 自动断言（无档位条/无「偏弱偏强」/无总分）；G3 字段全可见；变柱用例（1985-03-02 00:00 北京）显示「该修正改变了日柱」。

---

## S4 深读选择与支付

现有商业合同（DESIGN §11）不变，本轮只钉显示内容：

| 屏 | 显示什么 | 来源 |
|---|---|---|
| 深读确认 | Offer 名称/覆盖范围（哪些主题、绑定哪张盘哪个版本）/价格/退款边界 | server-owned checkout（`reading_version_id`） |
| 支付中 | 「确认中」+ 订单号 | 服务端订单状态 |
| 成功/失败/超时 | 对应状态 + 下一步（去报告/重试/联系支持） | 服务端支付事实 |
| 生成中 | queued/preparing/generating/validating 四态进度描述 | 任务状态 |

红线：客户端回跳只显示「确认中」；Fake gateway 显示不可用。

---

## S5 报告态（ReadingDocument）

结构按 DESIGN §9 十段。显示内容合同的关键约束：

| 区块 | 内容来源 | 规则 |
|---|---|---|
| 资料与盘面摘要 | S3 已渲染事实的紧凑投影 | 与盘面态一致，不重算 |
| 一句话回答 + 原子判断卡 | `ReadingDocumentV1` blocks；每 block `text` 逐字等于其引用的 `fact.display_text` / `finding.public_text` / `limit.public_text` | P0 红线；不同 block 不复用同一来源；来源不足时停在不可交付状态（S6 的 `delayed/failed` 呈现），**不得**用模型文案凑段 |
| 依据抽屉 | 每卡 evidence refs → §19.1 引文卡 | 金线语言与 S3-M12 一致 |
| 适用边界 / 现实核对 / 资料纠正 / 追问 / 导出分享版本 | 既有合同 | 核对只追加 VerificationEvent；纠正走新 ProfileVersion |

当前可用 Claim Unit 仅 3 类（月令状态、子平格局入口、调候候选次序）——报告正文密度受 GAP-BZ-02 制约；UI 全量预制，正文按可交付来源数收缩。

---

## S6 异常态族（贯穿）

文案基线见 DESIGN §2.5。逐态：

| 态 | 呈现 |
|---|---|
| loading | 盘面骨架 = 四柱矩阵轮廓（列头 + 大字格 + 行骨架），非通用 spinner |
| empty | 「还没有可展示的盘面」+ 回入口态按钮 |
| error | 「读取失败，请重试」+ 重试；不透出英文 ApiError |
| unauthorized | 「需要登录才能看这份结果」+ 登录弹层入口 |
| unavailable / maintenance | 「结果服务暂时不可用，不会展示未确认内容」 |
| partial（部分字段缺失） | 缺失模块整块不渲染；不出现模块级「暂无数据」占位条 |

---

## ALGO-GAP 清单（算法/后端开发的输入）

> 判定标准：UI 需要展示、`bazi-chart/v1` 类型已定义或需要新增、当前真实 owner 结果拿不到的数据。每条给出「缺什么 / 期望形状 / 阻塞什么 / 不阻塞什么」。

### GAP-BZ-01 · 时间层数据未产出（P1，阻塞流年/流月/流日）

- 缺：真实 owner 结果中 `core_facts.year_layers` / `month_layers` / `day_layers` 为空（2026-08-19 runtime-bazi-owner-result 实测 `missingRuntimeField: core_facts.year_layers/month_layers/day_layers`），`time_layers[]` 对应层 `available: false`。
- 期望形状：registry 已定义的 `year_layers[]`（year/ganzhi/stem_ten_god/branch_hidden_ten_gods/branch_relations/structural_changes/ganzhi_segments/active_luck_cycle/…）与 `BaziTemporalLayer`；Runtime/backend 填充 + `time_layers[].available=true`。
- 阻塞：S3-M9 全部；时间层切换交互（§21.2）只剩本命/大运两层可验。
- 不阻塞：S3 其余模块全部可按现有 owner 结果实现（natal + decadal 实测 ready）。

### GAP-BZ-02 · 深读 Claim Unit 供给不足（P1，阻塞 S5 正文密度）

- 缺：带 `public_text` + exact fact/evidence refs 的 Runtime Claim Unit 当前仅 3 类（月令状态、子平格局入口、调候候选次序）。P0 红线要求每个报告 block 逐字引用互不重复的直接来源，3 类撑不起多段正文。
- 期望形状：更多 exact-evidence 闭合的 Claim Unit（候选方向：十神结构描述、神煞落柱描述、纳音描述、大运节点事实），每条 `{public_text, fact_refs[], evidence_refs[], status(未裁定语义)}`。
- 阻塞：S5 报告正文段数；深读 Offer 的「覆盖范围」文案。
- 不阻塞：S4 支付链路（可先按现有 3 类交付最小报告）；S3 全部。

### GAP-BZ-03 · 术语释义常量表（P2，阻塞行头释义与神煞悬停释义）

- 缺：§19.3 允许的「定义式释义」内容源。需要一份带出处的术语定义表：十神名、十二长生位、旬空、纳音、神煞名、合/冲/刑/害/会。只解释「指什么」，不写「主什么」。
- 期望形状：`{term_id, term, definition_text, source_pack?, source_anchor?}` 显式常量（前端常量文件或 contracts 数据均可），核心算法审核出处。
- 阻塞：S3-M2 行头释义 popover、M10 神煞释义。
- 不阻塞：整个盘面（无释义时行头不带 popover 即可）。

### GAP-BZ-04 · 天干层柱间生克连线事实（P3，可选增强）

- 缺：`branch_relations[]` 只覆盖地支关系；若要做青囊式「智能四柱图」的天干生克连线，需要 Runtime 输出天干间关系事实（UI 不得客户端推导生克，§17 浏览器排盘禁令）。
- 期望形状：`stem_relations[]: {relation_type, positions[], stems[]}` 或并入 branch_relations 的同构结构。
- 阻塞：仅矩阵天干行连线这一个视觉增强。
- 不阻塞：M2 其余全部（地支连线可用现有字段做）。

### GAP-BZ-05 · 输入页服务端预览回显（P3，建议放弃）

- 缺：录入页实时农历换算/干支预览需要服务端 echo 端点。
- 处置建议：本轮放弃。S1 只做民用时辰区间提示（固定映射 + 口径边界句），S2 只回显输入。真正的换算结果在 S3 由签名结果给出，避免「预览与结果不一致」的解释成本。
- 阻塞：无（设计已绕开）。

### GAP-BZ-06 · 神煞规则出处锚点未暴露（P2）

- 缺：`shensha_auxiliary.evaluated_rules[]` 有 `rule_id` 无 `source_pack/source_anchor`，神煞「为什么」展开无法给出书名行号级溯源（与 §19.1 证据语言不齐）。
- 期望形状：`evaluated_rules[].source_ref {pack, rule_id, source_anchor, verification_status}`，或在 `source_conditioned_patterns` 中补神煞规则命中卡。
- 阻塞：M10 的溯源展开层。
- 不阻塞：M10 的事实列表与矩阵神煞 chips（现有字段够）。

---

## 实现顺序建议

1. **S3 盘面态**（先做 M1 口径条 + M2 四柱矩阵 + M3–M5 + M8 + M12）：数据已真实签名可用（natal/decadal ready），是「盘面是产品的脸」的落点，验收提升最大。
2. **S0/S1/S2 入口态**：空盘剪影 + 表单移植到新骨架 + 确认弹层。改动小、复用 S3 的矩阵组件 silhouette 态。
3. **S6 异常态族**：随 S3/S0 同步做（骨架屏形状依赖矩阵组件）。
4. **M9 时间层**：等 GAP-BZ-01 数据；chips disabled 态先行。
5. **S4/S5**：支付链路已有合同；报告正文密度等 GAP-BZ-02。

## 其余四术展开顺序建议

1. **六爻**（`liuyao-chart/v1` 字段厚实：纳甲/六亲/六神/世应/用神选取带已核验裁定；2026-08-21 档位裁决刚开放断法区块，正好一次做对）；
2. **梅花**（与六爻共享卦象组件族——爻画、卦名、动爻标记；`meihua-chart/v1` 的体用关系裁定已带 source_refs）；
3. **紫微**（`ZiweiPalaceBoard` 4×4 宫环是最大单体组件，B 档纯事实页，宫格键盘遍历与联动做完即是 G5 密度大户）；
4. **大六壬**（`DaliurenBoard` 天地盘+四课+三传结构最特殊，放最后单独攻）。

每术 flow-spec 按本文格式出：入口剪影 → 录入字段 → 盘面模块逐条对齐各自 ViewModel 字段 → ALGO-GAP。
