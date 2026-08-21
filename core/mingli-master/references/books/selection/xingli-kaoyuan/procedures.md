# 御定星历考原 — Procedures

> 全书可操作流程。前缀 `KP-` = Kaoyuan Procedure。
> 严格禁止 LLM 手算；本 pack 仅声明"工具依赖与输入字段"。
> 所有择日 / 起例最终由 `mingli-master.selection.v1` 完成。

---

## KP-01 神煞起例考源查询

- **procedure_id**: KP-01
- **purpose**: 给定某神煞名（如"金神七煞"），查询其起例口诀的官方源头与详解。
- **inputs**:
  - 神煞名（中文）
  - 神煞类型（年神 / 月吉神 / 月凶神 / 日神 / 时神）
- **steps**:
  1. 在 chapter-map.md 中按神煞类型定位卷次（卷二年神 / 卷三月吉 / 卷四月凶 / 卷五日时 / 卷六用事）。
  2. 在 quote-index.md 中按神煞名检索短引。
  3. 在 rules.md 中检 KR-* 对应规则，复述官方起例口诀。
  4. 输出"出处卷次 + 起例口诀 + 与协纪辨方书的差异（如有）"。
- **tool_dependency**: 无（纯文本查询）
- **outputs**: 神煞起例考源摘要
- **caveats**: 文化参考，非事实判断；起例口诀仅作"考源"，不作"事实预测"。
- **verified**: false
- **source_chapter**: cross-volumes

## KP-02 年神方位查询（具体年份）

- **procedure_id**: KP-02
- **purpose**: 给定具体公历 / 农历年份，查询当年的太岁、大将军、金神七煞、岁德合等年神方位。
- **inputs**:
  - 公历年（YYYY）或干支年
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(year=YYYY, query="annual_gods")`。
  2. **不允许 LLM 手算**：年干支、九星入中、年神方位的具体推算一律由工具输出。
  3. 工具返回结构：`{ taisui_position, dajiangjun_position, jinshen_qisha_positions[], suidehe_position, ... }`。
  4. 输出年神方位时附 caveats："文化参考，非事实判断"。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当年年神方位结构化数据
- **verified**: false
- **source_chapter**: vol-02-nianshen

## KP-03 月吉凶神查询（具体年月）

- **procedure_id**: KP-03
- **purpose**: 给定具体年月，查询该月的天德 / 月德 / 月空 / 母仓（吉），月建 / 月破 / 月厌 / 月害（凶）。
- **inputs**:
  - 公历年月（YYYY-MM）或农历年月
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(year_month=YYYY-MM, query="monthly_gods")`。
  2. **不允许 LLM 手算**：月建顺序、月吉凶神配位由工具输出。
  3. 工具返回：`{ tian_de, yue_de, yue_kong, mu_cang, yue_jian, yue_po, yue_yan, yue_hai, ... }`。
  4. 与"四废 / 四离 / 四绝"通用日期一并输出。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当月吉凶神结构化数据
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: vol-03-yueji, vol-04-yuexiong

## KP-04 日吉凶查询（具体日期）

- **procedure_id**: KP-04
- **purpose**: 给定具体日期，查询当日的黄道黑道、二十八宿、建除十二神、神煞分布。
- **inputs**:
  - 公历日期（YYYY-MM-DD）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(date=YYYY-MM-DD, query="daily_gods")`。
  2. **不允许 LLM 手算**：日干支、黄黑道、二十八宿配日、当日神煞集合由工具输出。
  3. 工具返回：`{ rigan_zhi, huangdao_god, 28xiu, jianchu_god, daily_shensha[], ... }`。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当日吉凶结构化数据
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: vol-05-rishi

## KP-05 时辰选时（具体日期 + 用事）

- **procedure_id**: KP-05
- **purpose**: 给定具体日期与用事类型，输出该日 12 时辰的吉凶排序与首选吉时。
- **inputs**:
  - 公历日期（YYYY-MM-DD）
  - 用事类型（嫁娶 / 出行 / 上任 / 起造 / 安葬 等）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(date=YYYY-MM-DD, event=event_type, query="hourly_selection")`。
  2. **不允许 LLM 手算**：贵登天门、四大吉时、十二贵人时辰、当日时柱排盘由工具输出。
  3. 工具返回：`{ best_hour, best_hour_reason, all_hours_ranked[], gui_deng_tian_men_hour }`。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 12 时辰吉凶排序 + 首选吉时
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: vol-05-rishi

## KP-06 用事择日（嫁娶 / 安葬 / 起造）

- **procedure_id**: KP-06
- **purpose**: 给定用事类型与查询期（如某月内），输出该期内的官方推荐日。
- **inputs**:
  - 用事类型（六十事项之一）
  - 查询期（YYYY-MM-DD ~ YYYY-MM-DD）
  - 当事人四柱（可选，用于排除冲忌）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(event=event_type, range=[start, end], natal_chart=optional, query="event_selection")`。
  2. **不允许 LLM 手算**：候选日的所有神煞集合由工具输出；按官方"宜 / 忌"通则筛选。
  3. 工具返回：`{ recommended_dates[], rejected_dates_with_reason[], primary_reasoning_chain }`。
  4. 输出时必须附 caveats："文化参考，非事实判断"。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 推荐日清单 + 落选日原因
- **caveats**: 文化参考，非事实判断；不构成事实预测
- **verified**: false
- **source_chapter**: vol-06-yongshi

## KP-07 与协纪辨方书的差异对照查询

- **procedure_id**: KP-07
- **purpose**: 给定某神煞 / 某规则，输出本书（康熙朝考源）与《协纪辨方书》（乾隆朝定本）的差异。
- **inputs**:
  - 神煞名 / 规则标识（KR-* 或 XR-*）
- **steps**:
  1. 在 quote-index.md 与 rules.md 中分别检本书的 KR-*。
  2. 在 selection/xieji-bianfang-shu/quote-index.md 与 rules.md 中检对应 XR-*。
  3. 对照"起例口诀 / 配位 / 吉凶判定"三层差异。
  4. 输出："本书（KR-x）作 X 解；协纪（XR-y）作 Y 解；协纪辨讹卷三十三~三十六注 Z"。
- **tool_dependency**: 无（跨 pack 文本查询）
- **outputs**: 双典对照表
- **verified**: false
- **source_chapter**: cross-pack

---

**说明**：共 7 个流程，全部以"工具依赖 + 输入字段 + 输出结构"为核心；严格禁止 LLM 手算神煞 / 起例 / 选日 / 选时。本书的所有"具体日子吉凶"问题均收口至 `mingli-master.selection.v1`。
