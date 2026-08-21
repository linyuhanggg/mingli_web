# 玉匣记 — Procedures

> 全书可操作流程。前缀 `JP-` = Yuqia-Ji Procedure。
> 严格禁止 LLM 手算；所有具体日期 / 起例由 `mingli-master.selection.v1` 完成。

---

## JP-01 民俗禁忌日查询（彭祖百忌 / 杨公忌 / 月忌日 等）

- **procedure_id**: JP-01
- **purpose**: 给定日期，查询该日是否落在民俗常用禁忌日中（彭祖百忌、杨公忌、月忌日、十恶大败、伏断、上下兀、上朔、火星、长短星、九土鬼、人神所在、神号鬼哭、赤口、四不详、先贤死葬、探病忌日 等）。
- **inputs**:
  - 公历日期（YYYY-MM-DD）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(date=YYYY-MM-DD, query="folk_taboo_days")`。
  2. **不允许 LLM 手算**：所有禁忌日的具体日期由 tool 输出。
  3. 工具返回：`{ pengzu_baiji: { gan_taboo, zhi_taboo }, yanggong_ji: bool, yueji: bool, shi_edabai: bool, fuduan: bool, ... }`。
  4. 若命中医疗禁忌日（JR-11 人神所在 / JR-12 探病忌日），输出时必须强提示"请遵从医疗专业意见"。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当日禁忌日命中清单
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: folk/01-time-tools ~ folk/30-zaji

## JP-02 玉匣记日期（许真君）逐月吉日查询

- **procedure_id**: JP-02
- **purpose**: 给定农历年月，查询本书"许真君日期"列出的逐月宜祭祀 / 沐浴 / 修真 / 上章 / 起造 / 出行 / 嫁娶等吉日。
- **inputs**:
  - 农历年月
  - 用事类型（祭祀 / 修真 / 沐浴 / 起造 / 出行 / 嫁娶 等）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(year_month=lunar_YYYY-MM, source="yuqia-xuzhenjun", event=event_type, query="monthly_lucky_days")`。
  2. 工具返回当月推荐日清单（基于本书逐月日期表）。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当月吉日清单
- **caveats**: 文化参考，非事实判断；与官方协纪辨方书冲突时以官方为准。
- **verified**: false
- **source_chapter**: theory/01-yuqia-riqi

## JP-03 三元五腊圣诞日查询

- **procedure_id**: JP-03
- **purpose**: 给定公历年份，查询当年三元（上中下元）、五腊（天地道民王）、十殿阎君圣诞、雕塑神像吉日的具体公历日期。
- **inputs**:
  - 公历年份（YYYY）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(year=YYYY, query="taoist_festival_dates")`。
  2. 工具返回当年三元 / 五腊 / 十殿阎君诞 / 雕塑神像吉日的公历日期。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当年道教节日 / 神诞清单
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: theory/03-sanyuan-wula, theory/04-shidian-yanjun, theory/05-diaoshu-shenxiang

## JP-04 鹤神方位查询

- **procedure_id**: JP-04
- **purpose**: 给定公历日期，查询当日鹤神所在方位。
- **inputs**:
  - 公历日期（YYYY-MM-DD）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(date=YYYY-MM-DD, query="heshen_position")`。
  2. 工具返回鹤神所在方位（八方之一）。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 当日鹤神方位
- **caveats**: 文化参考，非事实判断；起造 / 出行可参考本方位避忌。
- **verified**: false
- **source_chapter**: folk/21-heshen-fang

## JP-05 出行择日（民俗版 + 诸葛逐年出行图）

- **procedure_id**: JP-05
- **purpose**: 给定查询期与目的地方向，输出本书民俗系出行吉日 + 诸葛武侯逐年出行图的吉凶方位。
- **inputs**:
  - 查询期（YYYY-MM-DD ~ YYYY-MM-DD）
  - 出行方向（八方）
- **steps**:
  1. 仅声明工具依赖：`mingli-master.selection.v1(range=[start, end], direction=direction, source="yuqia-zhuge-chuxing", query="travel_selection")`。
  2. **不允许 LLM 手算**：往亡日 / 归忌日 / 杨公忌 / 月忌日的命中由 tool 输出。
  3. 工具返回：`{ recommended_dates[], rejected_dates_with_reason[], zhuge_year_direction_lucky[] }`。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 出行推荐日清单 + 方位吉凶
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: folk/27-zhuge-chuxing

## JP-06 嫁娶 / 安葬 / 起造（民俗补充）

- **procedure_id**: JP-06
- **purpose**: 在协纪辨方书的官方择日基础上，叠加本书民俗禁忌日（杨公忌 / 月忌日 / 十恶大败 / 九土鬼 / 鹤神方位 等）的二次过滤。
- **inputs**:
  - 用事类型（嫁娶 / 安葬 / 起造）
  - 查询期与方位
- **steps**:
  1. **第一层**：调 `mingli-master.selection.v1(event=event_type, range=range, query="primary_selection")`（官方层）。
  2. **第二层**：调 `mingli-master.selection.v1(event=event_type, range=range, source="yuqia", query="folk_filter")`（民俗补充层）。
  3. 输出"官方推荐日 ∩ 民俗未命中禁忌日"作首推；"官方推荐日 ∩ 民俗命中禁忌日"作次推。
- **tool_dependency**: `mingli-master.selection.v1`
- **outputs**: 双层过滤后的择日清单
- **caveats**: 文化参考，非事实判断
- **verified**: false
- **source_chapter**: folk/28-jiaqu-zaozao

## JP-07 杂占查询（梦 / 耳鸣 / 眼跳 / 禽鸟） ⚠️

- **procedure_id**: JP-07
- **purpose**: 给定杂占类目（梦境内容 / 身体征兆 / 禽鸟征兆），查询本书的占断对应。
- **inputs**:
  - 占类（dream / body_sign / bird / object_sign）
  - 占触发事件（梦境描述 / 征兆类型）
- **steps**:
  1. 在 quote-index.md 中按占类检索对应短引。
  2. **不调用 tool**：杂占无历法计算需求，纯文本查询。
  3. 输出本书原始映射 + 强 caveats。
- **tool_dependency**: 无（纯文本查询）
- **outputs**: 杂占占断对应
- **caveats**: **重要警告**：杂占完全为民俗信仰，无任何科学依据；现代不构成事实判断。仅作文化研究参考；切勿据此作出任何健康 / 财务 / 人际决策。
- **verified**: false
- **source_chapter**: zhanbu/01-meng ~ zhanbu/04-yingerlinger

---

**说明**：共 7 个流程，全部以"工具依赖 + 输入字段 + 输出结构"为核心。本书的所有"具体日子吉凶"问题均收口至 `mingli-master.selection.v1`；杂占（JP-07）不调用工具但必须强 caveats。涉及医疗的禁忌日（JR-11 / JR-12）输出时必须额外强提示。
