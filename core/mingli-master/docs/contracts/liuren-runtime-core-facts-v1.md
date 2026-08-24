# 大六壬 Runtime 核心事实合同 v1

`runtime_core_facts` 是六壬 provider 在 `fact_extension.facts` 下新增的稳定、只增不改投影。它以真实 `describe → prepare` 链路里的 `liuren_fact_adapter` 与 `extend_liuren_facts` 输出为来源，供 Backend 组装 ReadingDocument；原始 `chart_facts.output` 继续保留，避免破坏现有消费者。

- Schema：`mingli-liuren-runtime-core-facts-v1`
- JSON Pointer：`/fact_extension/facts/runtime_core_facts`
- 生成器：`scripts/reading_engine/liuren_contract.py`
- 脱敏黄金样例：`references/fixtures/liuren-runtime-core-facts-v1.json`
- 语义边界：只输出确定性盘面、维度事实与规则证据，不输出事件成败结论；所有 `rule_evidence.hard_verdict` 固定为 `null`。

## 顶层字段

| 字段 | 类型 | 必填 | null | 省略规则 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `schema_version` | string | 是 | 否 | 不省略 | 固定为 `mingli-liuren-runtime-core-facts-v1` |
| `day_hour` | object | 是 | 否 | 不省略 | `{day, hour}`，沿用 Runtime 实出键 |
| `earth_plate` | string[12] | 是 | 否 | 不省略 | 固定 `子→亥` 顺序 |
| `heaven_plate` | object[12] | 是 | 否 | 不省略 | 每项严格为 `{earth, heaven}`，按地盘顺序 |
| `heavenly_generals` | object[12] | 是 | 否 | 不省略 | 每项严格为 `{earth, heaven, general}`，与天盘对齐 |
| `month_general` | object | 是 | 否 | 不省略 | 严格为 `{branch, name}` |
| `noble_person` | object | 是 | 否 | 不省略 | 天乙贵人支、昼夜、顺逆、落地位、规则 profile 和来源 |
| `lesson_method` | object | 是 | 仅 `direct_direction` 可为 null | 不省略 | 从原始 `transmission_method` 提取稳定字段；不再公开其内部调试 trace |
| `four_lessons` | object[4] | 是 | 否 | 不省略 | `lesson` 固定为 1–4；项键见黄金样例 |
| `three_transmissions` | object[3] | 是 | 否 | 不省略 | `stage` 固定为 `initial → middle → final` |
| `plate_offset` | integer | 是 | 否 | 不省略 | 0–11 |
| `xunkong` | object | 是 | 否 | 不省略 | 严格为 `{xun, branches[2]}` |
| `structural_patterns` | string[] | 是 | 否 | 不省略 | 兼容字段；仅保留现有算法识别的结构名，不承担“可核验”语义 |
| `source_conditioned_patterns` | object[] | 否 | 否 | 旧 v1 payload 可省略；当前生成器总是输出 | GAP-DL-02 additive 投影；无可核验锚点时整项省略，零命中为 `[]` |
| `dimension_facts` | object | 是 | 否 | 不省略 | 只含本次请求维度，保持请求首次出现顺序 |
| `timing_candidates` | object[] | 否 | 否 | 未请求 timing 时省略 | 已请求 timing 但无有界日期候选时输出 `[]` |

`lesson_method` 的严格键集为：`primary`、`use_method`、`direct_direction`、`selected_initial`、`calculated_transmissions`、`calculation_source`、`source_anchor`。原始 Runtime 的键名是 `transmission_method`；稳定投影只使用产品合同名称 `lesson_method`，不会同时输出两个别名。

## `source_conditioned_patterns`

每项严格同构于其他术数已经公开的来源命中对象：

- `rule_id`、`local_rule_id`、`title`：稳定规则身份与当前结构名；
- `source_pack`、`source_anchor`：可回查的 reference pack 与 `fulltext.md#L...` 行锚点；
- `status`：固定为 `predicate_matched_not_verdict`；
- `fact_paths`、`predicate_audit`：指回本次 `structural_patterns` 命中及必要的结构条件；
- `source_dependency_id`：固定为 `liuren.source-conditioned-structural-patterns-v1`。

当前来源表只登记已经通过 reference pack 核对的四项：伏吟 `DLR-09 / DLQ-041 / L7696`、反吟 `DLR-10 / DLQ-043 / L7874`、八专日 `DLR-08 / DLQ-039 / L7556`、四课不备 `DLR-07 / DLQ-012 / L58`。其中“四课不备”的古籍锚点明确限定“三课备”，所以只有四课去重后恰为三课才发布来源对象；两课或其他未收录标签继续保留兼容字符串，但不生成伪锚点。

该数组不是吉凶、成败或应期裁决。它没有 `verdict` 字段，也不允许把 `status` 改成结论态。传输/存量 payload 的稳定身份必须重新绑定到 release-pinned catalog；“四课不备”还会从 `four_lessons[*].upper` 重算去重数并要求恰为 3。来源登记在 `references/inference/liuren-rules-v1.json`；聚焦审计命令为 `python3 -B scripts/audit_liuren_structural_patterns.py`，该审计同时校验 manifest 声明的规范化全文摘要，并在 `source_anchor` 精确行核对短引原文。

## `dimension_facts`

每个维度项都必须先包含下面的信封字段，再包含对应的确定性字段：

| 字段 | 类型 | null/省略 | 说明 |
| --- | --- | --- | --- |
| `requested_dimension` | string | 不可 null/省略 | 必须等于该项 object key |
| `canonical_dimension` | string | 不可 null/省略 | `career→work`、`current_state→state`、`location_direction→location`，其余同名 |
| `status` | string | 不可 null/省略 | 固定 `calculated_facts_not_verdict` |
| `source_rule_ids` | string[] | 不可 null/省略 | 本维度实际激活的确定性规则编号 |
| `rule_evidence` | object | 不可 null/省略 | 证据层；不是裁决层 |

维度专属键集如下，专属键之外的键会被拒绝：

| canonical dimension | 专属字段 |
| --- | --- |
| `outcome` | `subject_object_relation`, `transmissions_to_day`, `initial_final_relation`, `stage_flow` |
| `timing` | `relative_speed`, `candidate_branch`, `candidate_date` |
| `state` | `stage_status`, `general_landing_correspondences` |
| `location` | `stage_branch_directions` |
| `relationship` | `six_relative_stages`, `subject_object_relation`, `stage_flow` |
| `work` | `six_relative_stages`, `stage_status`, `subject_object_relation`, `target_relative`, `target_contract_status`, `target_presence`, `target_strength`, `target_general_modifier` |
| `money` | `wealth_presence`, `wealth_stage_strength`, `wealth_void_status`, `wealth_general_modifier` |

`timing.candidate_branch` 和 `timing.candidate_date` 在 horizon 未提供可计算边界时均为 `null`；有界但没有候选落入范围时，`candidate_branch` 保留而 `candidate_date` 为 `null`。`work.target_relative` 在未绑定类神时为 `null`，同时 `target_contract_status=missing_target_relative`；数组字段即使无命中也保留为 `[]`，不使用“暂无证据”占位字符串。

## 规则证据与来源锚点

`rule_evidence` 的严格键集是 `status`、`hard_verdict`、`requires_school_adjudication`、`matched`、`scope_boundaries`、`not_evaluated`、`catalog_schema`。

- `hard_verdict` 必须为 `null`；`requires_school_adjudication` 必须为 `true`。
- `matched` 和 `scope_boundaries` 记录必须带 `rule_key`、`activation_id`、`rule_id`、`status`、`polarity`、`weight_class`、`dependency_group`、`source_refs`、`fact_paths`、`observation`。
- `not_evaluated` 记录必须带 `rule_key`、`activation_id`、`rule_id`、`status`、`reason`、`source_refs`。
- 每个 `source_refs[]` 必须带 `pack`、`rule_id`、`source_anchor`；`quote_id` 可选。`confidence_ceiling`、`stop_conditions` 仅在规则声明时出现。
- `observation` 是规则特定的事实快照，允许规则定义自己的内部键；固定合同层之外的未知键一律拒绝。

本切片补齐了 `liuren-rules-v1.json` 中此前只有 quote id、没有锚点的规则引用。锚点指向已入库全文行号，不引入新术理或人工 verdict。

## 顺序、未知键与兼容性

- JSON object 的键顺序不作为跨语言语义；黄金样例固定生成顺序，便于 diff。
- 数组顺序是合同：地盘/天盘/天将为 `子→亥`，四课为 1–4，三传为初中末。
- `dimension_facts` 按请求维度首次出现顺序生成；重复维度去重。
- 稳定投影的固定层执行 required-key 和 unknown-key 双向校验。原始 adapter 新增内部 trace 不会自动泄漏到本合同。
- 本合同是 additive v1。若将来需要新增公开字段，应发布新 schema 或先将字段声明为可选；不得静默改变 v1 的键集、null/省略语义或列表顺序。

## Backend 接入

Backend 应优先读取 `/fact_extension/facts/runtime_core_facts`，并以 `schema_version` 分派解析器。现有 `dimension_facts`、`timing_candidates` 和 `chart_facts.output` 绑定继续保留用于兼容；不要从原始 `transmission_method` 的调试 trace 推导产品事实，也不要把规则证据聚合成成败、吉凶或确定日期。
