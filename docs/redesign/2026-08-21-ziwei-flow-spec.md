---
name: 紫微斗数全流程逐屏规格与显示内容合同
date: 2026-08-21
task: T-0821-UIUX-4
status: accepted-design-input
role: 五术 flow-spec 第四份（格式沿用 2026-08-21-bazi-flow-spec.md 样板）
authority: 视觉与交互语言见 DESIGN.md（2026-08-21 版）；字段形状以 web/src/view-models/registry.ts 与 contracts/schemas/views/ziwei-chart-v1.schema.json 为准
---

# 紫微斗数全流程逐屏规格

流程是同一路由 `/ziwei` 上的状态机（DESIGN §7）：

```text
S0 入口态 → S1 录入 → S2 提交确认 → S3 十二宫盘面态（免费） → S4 深读选择/支付 → S5 报告态
                                      └→ S6 异常态族（贯穿全程）
```

每屏给出：目的 / 布局（360·768·1024·1440）/ **显示内容合同**（字段路径、呈现规则、缺失时行为）/ 交互 / 验收点。字段路径全部对齐 `ZiweiChartViewModel`（`ziwei-chart/v1`）；缺口标 `GAP-ZW-xx`，汇总在文末。

**通用红线**（同前三份样板）：无 raw JSON / snake_case / 内部 ref；空字段整块不渲染不占位（§19.2）；无合成评分与吉凶（G2）；引文原样透传（G1）；页面级不横滚；四视口 + 键盘 + reduced-motion（G6）。

**紫微特有约定**：星曜名、亮度、四化、宫位归属全部来自服务端事实；前端唯一允许的「固定字典计算」是**宫位几何**——三方四正（对宫 +6、三合 ±4）是十二宫的固定几何关系，允许前端据此做**高亮联动**，但不得据此生成任何事实文本或关系描述（同八字的五行染色字典边界，DESIGN §17）。

---

## S0 入口态（pristine）

**布局**：同八字 S0（术标行通栏 → 1440/1024 双栏、768 剪影横条、360 隐藏剪影）。

**显示内容合同**：

| 区块 | 显示什么 | 来源 | 规则 |
|---|---|---|---|
| 术标行 | 印章「紫微」+「紫微斗数」+ 适用说明（如「从出生时刻安十二宫星曜，逐宫核验」）| 静态文案 | H1 为术名；≤20 字 |
| 空盘剪影 | `ZiweiPalaceBoard` silhouette：4×4 空宫格 + 中宫空资料位 | 静态结构 | 无示例星曜/干支；配「提交后由服务端生成，可核验」 |
| 能力边界行 | 免费确定性盘面 + 古法命中可核验；深读按 Offer 状态 | 能力接口 | 不用工程词 |

---

## S1 录入 / S2 提交确认

出生资料字段与八字 S1 **完全同一套**（现有表单本就共享 bazi/ziwei 出生段：历法/性别/出生日期/时间/地点/时区/口径/档案复用），合同以 bazi-flow-spec S1/S2 为准，不重抄。紫微差异仅两点：

1. **时间层目标**（现有字段保留）：紫微可另填目标年/月/日（`targetYear/targetMonth/targetDate`），帮助句「留空默认查看本命盘；填写后可切换到对应时间层」。目标输入只决定请求哪些层，不做任何客户端换算。
2. 未知出生时间的影响说明改为紫微口径：「命宫与身宫依赖时辰，未知时辰将无法定盘」——紫微对时辰缺失比八字更硬（八字缺时柱仍可排三柱，紫微不能安命宫），若运行时确认不可降级排盘，未知时辰路径在紫微下禁用并说明原因（以服务端能力为准，前端不擅自放行）。

**验收点**：同八字 S1/S2；紫微下未知时辰开关的禁用态有可见理由句。

---

## S3 十二宫盘面态（免费确定性盘面）——本流程的主屏

**目的**：把 `ziwei-chart/v1` 的十二宫、星曜、四化、大限做成一张可扫读、可联动、可核验的环盘。信息密度是五术之最（12 宫 × 每宫最多三层星曜 + 四套十二神），密度分级是本屏成败关键。

**布局（含 360 降级方案，钉死）**：

- **1440**：工作条通栏 → 口径条通栏 → 双栏：左盘面区 640–720px（`ZiweiPalaceBoard` 4×4 环盘，正方形优先），右阅读区（命身卡、四化表、大限轨、星曜明细、古法命中），两栏独立滚动。
- **1024**：同构；环盘缩至 560–600px，宫格内星曜密度降一档（杂曜折叠为「+N」，点击宫格展开）。
- **768**：单列。环盘保持 4×4（紫微的身份就是环盘，768 不拆）但进入**紧凑密度**：每宫只显主星（含亮度角标+四化徽章）+ 宫名 + 干支 + 大限区间；辅星/杂曜/四套十二神全部收进宫位详情抽屉（点宫格打开）。中宫只显命主/身主/五行局三行。
- **360（环转列表，明确方案）**：环盘几何放弃，转为**宫位列表 + 粘性缩略宫格**：
  - 顶部粘性缩略图：3×4 迷你宫格（每格仅宫名首字 + 命/身标记点），当前阅读宫高亮；点任一格滚动到对应卡片。缩略图高 ≤88px，不含星曜。
  - 列表主体：十二张宫位横条卡，**从命宫起按宫序排列**（`palaces[]` 原始顺序按 `life_palace_id` 旋转，只是显示排序，不改数据）；每卡 = 宫名+干支行 → 主星行（亮度角标+四化徽章）→ 折叠「辅星与杂曜 +N」→ 大限区间小字。
  - 中宫资料（命身/五行局）成为列表首卡。
  - 缩略图与列表双向同步滚动位置；这套「环转列表」是 `ZiweiPalaceBoard` 的内建 `list` 形态，不是独立组件。
- 768/360 章节锚点：`盘面 / 命身 / 四化 / 大限 / 星曜明细 / 古法命中 / 深读`（无数据的锚点不渲染）。

### 工作条

同八字工作条合同（返回 / 资料摘要 / 时间层 chips / 更多）。时间层 chips 消费 `time_layers[]`（`layer_id/label/available/unavailable_reason`），disabled 态 tooltip 显示原因——**当前 VM 只有层的可用性声明，没有任何层数据字段**，切层后的盘面内容合同见 GAP-ZW-01；补齐前 chips 按真实 `available` 渲染（大概率只有本命层可用），不做假切换。

### M1 口径条（G3，复用八字 M1 组件模式）

| 显示什么 | 字段 | 规则 |
|---|---|---|
| 历法与生辰 | `core_facts.chinese_date` | 「农历甲戌年三月二十 卯时」一行 |
| 排盘口径 | `core_facts.chart_convention`（松散 Record，GAP-ZW-03 钉形） | 闰月处理/子时口径/流派设定等；钉形前只显示 `chinese_date`，口径项缺失不占位 |

### M2 十二宫环（`ZiweiPalaceBoard`，盘面主体）

**宫格合同**（每宫，`palaces[]` 逐项）：

| 层 | 字段 | 呈现 |
|---|---|---|
| 主星行 | `major_stars[]`（纯星名）+ 亮度（由 `core_facts.star_facts[]` 按 `name`+`palace_branch` 关联取 `brightness`，服务端事实的关联展示，非推导；覆盖确认见 GAP-ZW-02）+ 四化徽章（由 `core_facts.transformations[]` 按 `star`+`palace_branch` 关联，显示 化禄/化权/化科/化忌 单字徽章） | 18px 域字星名 + 13px 亮度角标（庙/旺/得/利/平/不/陷，中性墨色不做吉凶染色）+ 四化单字金线徽章（四化是古籍证据入口，用证据金，不用红绿） |
| 辅星行 | `minor_stars[]`（`name/brightness/star_type`） | 14px；亮度角标同上 |
| 杂曜行 | `adjective_stars[]` | 12px 灰阶；1024 以下折叠「+N」 |
| 十二神足注 | `changsheng12` / `boshi12` / `jiangqian12` / `suiqian12` | 11px 底行四枚小字，密度开关「精简/完整」控制显隐（默认精简=只显 `changsheng12`）；null 项不渲染 |
| 宫名行 | `label` + `heavenly_stem`+`earthly_branch` | 左下角：宫名 14px 加重 + 干支 12px |
| 大限行 | `decadal.age_start–age_end`（虚岁区间）+ `ages[]`（小限岁数，折叠进宫位详情） | 右下角 12px「34–43」 |
| 命身标记 | `palace_id === life_palace_id` → 「命」；`=== body_palace_id` → 「身」 | 印章式角标，命宫格 1px 墨线加重（扫读第一锚点，同六爻世爻行） |

**中宫**（4×4 中央 2×2 区）：命主 `core_facts.ming_shen.soul_star` / 身主 `ming_shen.body_star` / 五行局 `five_elements_class` / 大限起始 `major_limit_starting_age` + 顺逆 `major_limit_direction.direction`（含依据小字：性别+年干阴阳，来自 `direction.gender/year_polarity`）。`ming_shen` 为 null 时中宫只显五行局；全 null 显示资料摘要（subject 标签）。

**交互**（§21.1/§21.4）：
- 点击/聚焦任一宫 → 该宫锁定高亮，其**三方四正**三宫同步次级高亮（前端固定几何，仅高亮不生成文本）；四化表、星曜明细、古法命中里涉该宫条目联动高亮；再点解锁。
- 方向键在十二宫间按环序移动，Home/End 跳命宫/身宫；宫格 Enter 打开宫位详情抽屉（768/1024 密度降级后的完整星曜清单在此）。
- 语义替代：环盘同步输出语义表格（宫 × 星曜/干支/大限）。

### M3 命身与五行局卡（右栏首位）

`ming_shen`（命宫地支/身宫地支/命主/身主）+ `five_elements_class` + `major_limit_direction`。全部已在中宫出现——本卡是 768/360 下中宫内容的宿主（列表首卡），1440/1024 下折叠为一行摘要避免与中宫重复。

### M4 四化表

`core_facts.transformations[]` 按 `scope` 分组（本命/大限等，以服务端 scope 值为准）：

| 列 | 字段 |
|---|---|
| 星 | `star`（点击联动宫格） |
| 化 | `transformation`（禄/权/科/忌单字徽章） |
| 所在宫 | `palace` + `palace_branch` |

null 整块不渲染。

### M5 大限轨（复用八字 M8 大运轨组件模式）

`core_facts.major_limits[]`（或 `major_limit_sequence[]`，两者并存时以 `major_limits` 为准）：横向轨道，每格 = `sequence` 序 + `palace`宫名 + `heavenly_stem/earthly_branch` + `age_start–age_end`。当前大限高亮依据 `core_facts.active_major_limit`（松散，GAP-ZW-03；钉形前不做「当前」标记，只列轨道）。点击限格 → 环盘对应宫高亮。**点击不切换时间层数据**（层数据缺失，GAP-ZW-01）——补齐前限格只做定位联动，不承诺展示该限盘面。

### M6 星曜明细（右栏折叠区）

`core_facts.star_facts[]` 全量清单：星名/类型/亮度/所在宫，按宫分组，支持文本过滤。这是环盘密度降级后的完整性兜底（G5：信息不因布局丢失）。

### M7 古法命中抽屉（§19.1/§21.3，复用八字 M12 组件）

`core_facts.source_conditioned_patterns[]`（紫微已类型化）：合同与八字 M12 完全一致（title/source_pack/source_anchor/status=predicate_matched_not_verdict/fact_paths/predicate_audit），`fact_paths` 映射为宫格/星曜高亮。

### M8 免费基础摘要 + 深读入口

同八字 M11/M13：摘要只复述已上屏事实（命宫主星、五行局、当前可见大限段），不新增判断。

**S3 状态清单**：loading（4×4 宫格骨架）/ ready / partial（`core_facts` 为 null 或缺项：环盘 + 命身标记 + 大限行可用——全来自必有字段 `palaces/life_palace_id/body_palace_id`；M1/M3–M7 按缺失合同逐块不渲染）/ error / unavailable。

**验收点**：1440 环盘无页面横滚；360 环转列表 + 缩略图双向同步；宫格键盘可遍历、三方四正高亮不产生任何文本断语；亮度/四化无红绿吉凶色；密度开关生效；partial 态无空壳模块。

---

## S4 深读选择与支付 / S5 报告态 / S6 异常态族

与八字 S4/S5/S6 同构（bazi-flow-spec 为准），差异：

- S4 SKU 样例引用来自宫位与四化证据；不得出现吉凶承诺。
- S5 报告 Claim Unit 锚点指向宫格/星曜/四化，点击回跳 S3 高亮；深读文本供给缺口并入 GAP-BZ-02 同族跟踪。
- S6 增加紫微特有异常：**未知时辰不可定盘**（若服务端如此裁定）——录入页即拦截并说明，不进入排盘失败流。

---

## ALGO-GAP 清单

### GAP-ZW-01 · 时间层数据结构未定义（P1，阻塞大限/流年盘面切换）

- 缺什么：`time_layers[]` 只声明层的可用性；VM 没有任何分层盘面数据字段（对照 `bazi-chart/v1` 的 `natal/decadal/year_layers[]` 结构）。切到大限/流年层后宫盘该显示什么（流曜？宫位重标注？限内四化？）无数据可依。
- 期望：按八字模式定义紫微层数据合同（最小可用：大限层 = `active_major_limit` 钉形 + 限内 `transformations` scope 区分即可点亮大限层；流年层需流曜/岁建事实），或明确「切层 = 重新请求投影」的接口合同。与 GAP-BZ-01 同族，建议一并评估。
- 影响：不补则工作条时间层 chips 只有本命层可用，M5 大限轨只做定位不做切换。

### GAP-ZW-02 · 主星亮度覆盖待确认（P2）

- 缺什么：`palaces[].major_stars` 是纯字符串，亮度只能从 `core_facts.star_facts[]` 关联。需确认真实 Runtime 的 `star_facts` 覆盖全部 14 主星且带 `brightness`（现无紫微 runtime 结果证据，2026-08-19 验收只抓了八字）。
- 期望：若已覆盖，仅需在合同测试断言覆盖性；若未覆盖，`star_facts` 补主星亮度，或把 `major_stars` 升级为 star 对象数组（与 `minor_stars` 同构，动 schema 需两侧同步）。

### GAP-ZW-03 · 松散对象钉形（P2）

- 缺什么：`chart_convention`（口径条依赖）、`active_major_limit`（当前大限高亮依赖）、`interpretive_candidates`（若紫微有裁定证据应同梅花模式类型化）三个松散 Record。
- 期望：按真实 Runtime 输出钉进 schema + registry（同 GAP-LY-03 模式）。

### 术语释义词表（并入 GAP-BZ-03，不另开编号）

紫微词条量为五术之最：14 主星、亮度七级、四化、五行局、长生/博士/将前/岁前四套十二神、命主/身主。建议词表分域分片交付，紫微片优先级排在八字/六爻之后。

---

## 实现顺序建议

1. **先行（必有字段即成盘）**：`ZiweiPalaceBoard` 4×4 环盘 + 命身标记 + 宫格星曜（`palaces/life_palace_id/body_palace_id` 全部强类型必有）+ 360 环转列表形态。中宫与 M3 随 `ming_shen`（已类型化）同步实现。
2. 随后：M4 四化表 + M5 大限轨 + M6 星曜明细 + M7 古法命中（全部已类型化，`star_facts` 关联亮度按容错处理，等 GAP-ZW-02 确认后收紧）。
3. 时间层切换（工作条 chips 的实际切层）等 GAP-ZW-01；补齐前 chips 按 `available` 如实渲染。
