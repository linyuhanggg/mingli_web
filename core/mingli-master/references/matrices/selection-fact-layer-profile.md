# 择日事实层字段矩阵

generated_at: 2026-07-05  
matrix_version: v0.1  
source_status: derived_from_ready_selection_packs  
scope: selection / deterministic calendar-choice candidate generation and validation

本矩阵把择日回答前必须具备的事实字段固定下来。它不替代《钦定协纪辨方书》《御定星历考原》《玉匣记》《董公择日》的 reference pack，而是规定在加载这些书、解释这些书之前，生产 `SelectionProvider`（`mingli-master.selection.v1`）必须先给出哪些可复核字段。

SS-B2 官方择日神煞的起例/裁判/民俗对照依赖关系见 `shensha-ss-b2-selection-refinement.md` / `.yaml`；本文件负责事实字段门槛，SS-B2 负责神煞来源分层和单项因子禁用规则。

## 来源分层

| 层级 | Pack | 职责 | 使用规则 |
|---|---|---|---|
| 官方裁判层 | `selection/xieji-bianfang-shu` | 用事宜忌、建除黄黑道综合、辨讹、与民间通书冲突时裁判 | 一线 reference；冲突时优先 |
| 官方起例层 | `selection/xingli-kaoyuan` | 年神、月神、日神、时神、黄黑道、二十八宿、四离四绝等起例考据 | 解释神煞来源；不单独定最终吉凶 |
| 民俗对照层 | `selection/yuqia-ji` | 彭祖百忌、杨公忌、月忌、往亡、归忌、民俗禁忌日 | 只作二次过滤和通书风格说明 |
| 民俗对照层 | `selection/donggong-zeri` | 董公月日表、民间月日吉凶 | 只作对照；不得压过官方层 |

## 全局硬门槛

择日问题只要进入推荐、排序、判断吉凶、判断适合不适合，就必须先有完整事实层。

必备基础字段：

- `adapter`: name, version, rule_profile, generated_at, license_status。
- `input`: `selection_spec`（含精确 `requested_actions`）、timezone、location、input_digest。
- `calendar_normalization`: status、timezone/location、date_range、逐日 calendar_digests、calendar_profile；农历、闰月、干支与精确节气边界保存在逐候选 `calendar` 和逐时段变体中。
- `calendar_candidates[]`: 每个候选日独立记录，不允许只给一个总表。
- `date_time_candidates[]`: 每个候选日展开为实际时段候选，子时保留两个民用日期片段，节气切换和时区折叠保留多个确定性变体。
- 每个候选日必须有：建除十二神、黄黑道、二十八宿、年/月/日/时神煞、宜忌、冲突/避忌、source_trace。

停止条件：

- 没有 `mingli-master.selection.v1` 的完整确定性事实输出：停止，不选日。
- 只有公历、农历、星期、干支、建除、黄道任一单项：停止，只能称为 anchor，不是事实层。
- 缺 `calendar_normalization`：停止。
- 缺候选日逐日记录：停止。
- 民间通书与官方层冲突：保留冲突，以《协纪辨方书》为主裁判，不平均。
- 最终回答被压缩或改写后，由当前模型基于事实、证据、反证和草稿做一次私有复核；不使用自然语言正则 gate。

## 候选日记录 Schema

每个 `calendar_candidates[]` 条目至少应包含：

```yaml
candidate_id: "YYYY-MM-DD"
civil_date: "YYYY-MM-DD"
calendar: {lunar_date: {}, ganzhi: {}, solar_terms: {}, calendar_digest: ""}
jianchu: {}
mansion: {}
day_path: {}
annual_gods: {}
monthly_gods: {}
daily_shensha: {}
hour_facts: []
official_yiji: {yi: [], ji: []}
official_event_rules: {requested_actions: [], action_assessments: []}
event_specific_facts: {}
directional_facts: {}
eligibility: {}
ranking_components: {}
best_date_time_basis: {}
rejection_reasons: []
source_trace: []
```

## 用事 Profile

### generic_selection

适用：普通择日、选一个较顺的日子、泛用宜忌。

必备字段：

- 建除十二神。
- 黄黑道日与十二时辰黄黑道。
- 二十八宿。
- 年神、月神、日神、时神集合。
- 通用吉神：天德、月德、天恩、母仓、生气、四相、时德等。
- 通用凶神：十恶大败、四废、五墓、月破、月厌、复日、伏断等。
- `source_trace`: `XP-01`, `XR-08`, `KP-04`, `KR-14`, `KR-15`, `KR-17`。

### marriage

适用：嫁娶、纳采、问名、订盟、亲迎、领证择日。

额外输入：

- 男女双方四柱；若用户明确不看双方八字，只能做 general day quality，不能做 couple-specific final selection。

必备字段：

- 不将日、要安、生气、母仓。
- 天德、月德、天德合、月德合、三合、六合。
- 月破、月厌、月刑、月害、四废、五墓。
- 孤辰、寡宿、十恶大败、重丧、三丧、复日、伏断。
- 嫁娶周堂忌位。
- 本命冲克日、与双方四柱冲合刑害。
- `source_trace`: `XP-02`, `XR-05`, `KP-06`, `KR-18`, `JP-06`。

### construction_renovation

适用：起造、修造、动土、上梁、立柱、入宅、安门、安床、装修开工。

额外输入：

- 坐山、动土方位、门向或施工方位。若只给日期，不给方位，不得判断方位避忌；动土/修造类应视为 hard missing。

必备字段：

- 成日、开日、收日。
- 天德、月德、月恩、四相、时德、生气、母仓。
- 土王用事日、月破、月厌、大耗。
- 年家三煞、月家三煞、太岁、岁破、大将军、金神七煞、罗睺。
- 方位是否犯煞及犯煞来源。
- `source_trace`: `XP-03`, `XR-02`, `XR-06`, `KP-02`, `KR-08`, `KR-09`, `KR-10`, `KR-20`, `JP-06`。

### burial_funeral

适用：安葬、启攒、丧葬相关择日。

额外输入：

- 葬向/坐山用于判断方位时必需；亡者八字可选，若缺失则不得做亡命冲克层判断。

必备字段：

- 鸣吠日、鸣吠对日、不将日。
- 成日、开日。
- 重丧日、三丧日、复日、伏断日。
- 月破、月厌、地火、土禁、土王用事。
- 年/月克山家、方位煞命中情况。
- `source_trace`: `XP-04`, `XR-07`, `KP-06`, `KR-19`, `JP-06`。

### travel_office

适用：出行、远行、上任、受官、赴约、谈判出门。

额外输入：

- 出行方向；若只问普通出门而不看方位，可不判方位避忌，但必须声明未判方向。

必备字段：

- 驿马日、天马日。
- 往亡日、归忌日。
- 四离、四绝、杨公忌、月忌日。
- 黄道吉时。
- 上任/受官方向：成日、开日、临政日、天恩日；避破日、死日、闭日。
- 民俗对照：诸葛逐年出行图或玉匣记出行禁忌，只作 comparison。
- `source_trace`: `XP-05`, `XP-06`, `XR-09`, `KP-05`, `JP-05`。

### business_opening_transaction

适用：开张、开业、交易、签约、纳财、立券、求财类择日。

必备字段：

- 用事宜忌中与开张、交易、纳财、立券对应的条目。
- 建除是否为成、开、满等可用日，或破、闭等不利日。
- 天恩、天德、月德、母仓、生气等通用助力。
- 月破、四废、五墓、十恶大败、复日、伏断等通用避忌。
- 若涉及门向/开业方位，加载方位避忌字段。
- `source_trace`: `XP-01`, `XR-08`, `KP-06`, `KR-17`, `DP-02`, `DP-06`。

### medical

适用：求医、服药、针灸、探病日子。

必备字段：

- 天医、月恩、四相、生气等。
- 复日、四废、十恶大败、探病忌日等。
- 医疗边界提示：传统宜忌不得替代现实医疗判断，不得延误就医。
- `source_trace`: `XP-01`, `XR-16`, `KP-06`, `JP-01`。

### folk_comparison

适用：用户明确问通书说法、民俗禁忌、玉匣记/董公是否冲突。

必备字段：

- 彭祖百忌、杨公忌、月忌日、十恶大败、伏断、九土鬼、人神所在等。
- 董公月日表命中项。
- 与官方层的冲突条目。
- 明确 `folk_weight: comparison_only`。
- `source_trace`: `JP-01`, `JP-06`, `DP-01`, `DP-03`, `DP-06`。

## 输出要求

择日最终回答至少保留以下压缩 trace：

```text
Fact provider: mingli-master.selection.v1
Rule profile: <profile>
Input caveats: <missing/ambiguous fields>
Classical packs: selection/xieji-bianfang-shu, selection/xingli-kaoyuan (+ comparison packs if used)
Confidence: fact=<high|medium|low>, text=<high|medium|low>, interpretation=<calibrated|uncalibrated>
```

如果用户只要很短的口语回复，也必须在内部先满足本矩阵，再用自然语言压缩；不能因为输出短就省掉事实层。
