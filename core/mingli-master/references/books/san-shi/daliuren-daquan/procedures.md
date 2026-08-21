# 《大六壬大全》Adapter-first Procedures

> 本文件规定调用顺序和数据契约，不在 reference pack 内重复实现历法或排盘。凡写“调用 adapter”均指 `scripts/liuren_fact_adapter.py` v2；其输出必须再通过 `scripts/adapter_validate.py --system liuren`。

## DLP-01 区分文本研究与实际占事

- **source_layer**: `modern_synthesis`
- **evidence**: DLQ-001, DLQ-007, DLQ-018
- **preconditions**: 收到涉及《大六壬大全》或大六壬的问题。
- **steps**:
  1. 若问题是作者、版本、卷次、术语或原文，走 `text_research`，只查本包。
  2. 若问题要求现实起课、验证现成课盘或据课推断，走 `formal_cast`，强制 DLR-00。
  3. 若问题只有“小六壬”宫名或其他术数盘，不调用本包的取传规则。
- **adapter_fields**: `request_mode`, `question_domain`, `provided_chart_type`。
- **output**: `text_research | formal_cast | route_elsewhere`。
- **stop_or_exception**: 盘式种类无法辨认时先澄清或返回 `chart_type_unknown`，不得把小六壬映射成四课三传。

## DLP-02 占时与问题事实标准化

- **source_layer**: `compendium_body` + `modern_synthesis`
- **evidence**: DLQ-016, DLQ-020
- **preconditions**: `request_mode=formal_cast`。
- **steps**:
  1. 收集具体问题、起课时间、IANA 时区和地点；保存用户原始措辞。
  2. 由历法模块求节气边界、日时干支和月将；不得以农历月份名称代替月将计算。
  3. 校验时干与日干相容，记录子初换日、真太阳时或民用时等显式政策。
  4. 生成不可变 `normalized_input` 并计算输入 hash。
- **adapter_fields**: `question`, `event_datetime`, `timezone`, `location`, `calendar_policy`, `solar_term`, `day_ganzhi`, `hour_ganzhi`, `month_general`, `input_hash`。
- **output**: 可复算的标准化输入。
- **stop_or_exception**: 时间、时区或历法政策缺失且会改变盘面时停止；不默补“当前时间”。

## DLP-03 生成并校验天地盘、四课

- **source_layer**: `compendium_body`
- **evidence**: DLQ-005, DLQ-007, DLQ-020
- **preconditions**: DLP-02 已得到标准化输入。
- **steps**:
  1. adapter 以月将加占时生成天地盘。
  2. 按 DLR-01 核十干寄宫，生成干阳、干阴、支阳、支阴四课。
  3. 每课输出上神、下神、五行、阴阳、克生关系和去重 id。
  4. 运行结构校验：十二支各一次、天盘映射闭合、四课可由盘面重算。
- **adapter_fields**: `earth_plate`, `heaven_plate`, `stem_lodge`, `four_lessons`, `plate_invariants`, `recompute_hash`。
- **output**: 经过不变量校验的盘与四课。
- **stop_or_exception**: 任一不变量失败即返回 `invalid_liuren_plate`，不进入取传。

## DLP-04 按决策树取三传

- **source_layer**: `compendium_body`
- **evidence**: DLQ-006 至 DLQ-015、DLQ-029 至 DLQ-043
- **preconditions**: DLP-03 通过。
- **steps**:
  1. 先标记伏吟、返吟、八专、课数等结构事实，但不因名称跳过直接克。
  2. 执行 DLR-02：下贼优先，再看上克。
  3. 多候选依次执行 DLR-03 比用、DLR-04 涉害。
  4. 无直接克时按结构分流：伏吟 DLR-09、返吟 DLR-10、八专 DLR-08；一般盘走 DLR-05 遥克，再走 DLR-06 昴星或 DLR-07 别责。
  5. 输出每个候选、淘汰理由、采用规则、初中末传和 source quote IDs。
- **adapter_fields**: `special_structure_flags`, `candidate_sets`, `rule_trace`, `initial_transmission`, `middle_transmission`, `final_transmission`, `source_trace`。
- **output**: 唯一三传或明确 unresolved 状态。
- **stop_or_exception**: 柔日别责未选校定 profile、返吟井栏未校定、涉害 trace 不全时停止，不降级为模型猜测。

### 取传优先图

```text
四课
  -> 有下贼？唯一取重审，多项比用/涉害
  -> 无下贼但有上克？唯一取元首，多项比用/涉害
  -> 无直接克
       -> 伏吟专分支
       -> 返吟专分支
       -> 八专两课专分支（不取遥）
       -> 一般盘先遥克
       -> 四课全无遥：昴星
       -> 三课不备无遥：别责
```

## DLP-05 布十二天将并显式处理天乙冲突

- **source_layer**: `siku_editorial_preface` + `compendium_body`
- **evidence**: DLQ-003, DLQ-017, DLQ-021
- **preconditions**: 三传已确定，回答需要天将层。
- **steps**:
  1. 要求调用者选择 `guiren_profile`；不能以隐藏默认继续。
  2. adapter 输出该日干的昼贵、夜贵、昼夜判定、顺逆方向和完整十二将位置。
  3. 以 DLR-11 验证 profile source；正文俗例与官方订正 profile 分开保存。
  4. 若比较口径，复算两份将盘并展示受影响字段，不改变四课三传。
- **adapter_fields**: `day_or_night_policy`, `guiren_profile`, `guiren_mapping`, `guiren_direction`, `heavenly_generals`, `profile_source_ids`。
- **output**: 带 profile 的十二天将，或 `guiren_profile_required`。
- **stop_or_exception**: 未声明 profile、只给全局昼夜二支或来源表缺失时停止布将。

## DLP-06 分层解释而不生成固定套话

- **source_layer**: `siku_editorial_preface` + `compendium_body`
- **evidence**: DLQ-002, DLQ-018, DLQ-028, DLQ-050
- **preconditions**: DLP-04 已有唯一三传；需要天将时 DLP-05 也通过。
- **steps**:
  1. 按用户具体问题分配日辰、初中末、类神和主客，不套用固定“财务/回款/收尾”话术。
  2. 先列四课三传的直接结构，再列旺衰、空亡、刑冲合、天将与救制。
  3. 每个推断绑定事实字段和 quote/rule id；反向因素同列，不删去。
  4. 只说与所问相关的象；盘上其他象放弃输出。
  5. 自然语言由模型临场组织，不在 reference pack 固化句式。
- **adapter_fields**: `question_domain`, `fact_evidence_links`, `supporting_factors`, `counter_factors`, `unresolved_factors`, `confidence_basis`。
- **output**: 与问题相关、证据可回溯的解释草稿。
- **stop_or_exception**: 如果具体结论只有课名或单一神煞支撑，降为“文本含义”而非正式推断。

## DLP-07 查询课经或毕法

- **source_layer**: `compendium_body`
- **evidence**: DLQ-044 至 DLQ-053
- **preconditions**: 已有 adapter facts，或用户纯研究某一课体/毕法。
- **steps**:
  1. 通过 `chapter-map.md` 找 normalized 行段，同时记录可能的 WYG 卷号。
  2. 课经课体按 DLR-13 逐项匹配全部必要条件。
  3. 毕法先由目录定位，再加载逐法正文，按 DLR-14 建条件表。
  4. 法号 51-54 附近先检查编号异常，不按数字偏移猜下一法。
- **adapter_fields**: `pattern_id`, `matched_conditions`, `missing_conditions`, `bifa_rule_number`, `bifa_body_anchor`, `volume_numbering_system`。
- **output**: `confirmed | candidate | not_applicable | unresolved_numbering` 加证据。
- **stop_or_exception**: 只有目录短句、没有正文条件时不执行规则。

## DLP-08 版本与引文审计

- **source_layer**: `siku_editorial_preface` + `kanripo_wyg_witness` + `modern_synthesis`
- **evidence**: DLQ-001, DLQ-023, DLQ-024, DLQ-038, DLQ-051, DLQ-052
- **preconditions**: 输出包含原文、卷次、版本裁定或冲突规则。
- **steps**:
  1. 通过 `quote-index.md` 精确命中 normalized 行。
  2. 需要文渊阁证据时再查 Kanripo 页叶；需要字形最终裁定时标记待影印校勘。
  3. 卷号写明 `normalized` 或 `WYG/Kanripo`。
  4. 冲突项引用 `conflict-notes.md` 的编号，并说明“当前采用”“并列保留”或“停止”。
  5. 把现代转述与古籍原句分段呈现。
- **adapter_fields**: `quote_id`, `normalized_anchor`, `source_layer`, `witness_locator`, `conflict_id`, `collation_status`。
- **output**: 可审计引用包。
- **stop_or_exception**: 找不到 exact quote、没有行号或把提要当正文时阻止发布。

## 最小 adapter 输出示例

```json
{
  "adapter": {"name": "local-liuren", "version": "pinned"},
  "calendar": {
    "input_datetime": "ISO-8601",
    "timezone": "IANA",
    "calendar_policy": "explicit",
    "solar_term": "...",
    "day_ganzhi": "...",
    "hour_ganzhi": "...",
    "month_general": "..."
  },
  "plate": {
    "earth_plate": [],
    "heaven_plate": [],
    "four_lessons": []
  },
  "transmissions": {
    "initial": "...",
    "middle": "...",
    "final": "...",
    "rule_trace": [],
    "source_trace": []
  },
  "generals": {
    "guiren_profile": "explicit-profile-id",
    "day_or_night_policy": "explicit-policy-id",
    "heavenly_generals": []
  },
  "validation": {
    "invariants_passed": true,
    "unresolved_conflicts": []
  }
}
```

此示例是最小字段契约。实际运行以 `mingli-master.liuren_fact_adapter` 2.0.1 的 JSON 为准，不接受语言模型仿写的同形文本。
