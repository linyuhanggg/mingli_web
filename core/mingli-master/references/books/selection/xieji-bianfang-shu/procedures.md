# 钦定协纪辨方书 — Procedures

> 本文件抽取《协纪辨方书》中可被主 skill 调用的可操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verified`。
> **所有择日 / 选时 / 历算步骤一律以 `mingli-master.selection.v1` 标注，禁止 LLM 手算**。
> procedure_id 前缀 `XP` = Xieji Procedure。

---

## XP-01 官方择日总流程

- **name**：官方择日（协纪辨方系，集大成）
- **inputs**：
  - `event_type`（用事类型）
  - `candidate_dates`（候选日期范围，公历）
  - `place`（事件地，可选）
  - `direction`（坐山方位 / 出行方向，可选）
  - `relevant_bazi`（相关方四柱，可选；如嫁娶男女双方）
- **steps**：
  1. 调用 `mingli-master.selection.v1` 取得各候选日的：干支、月建、节气、二十八宿值日、建除十二客、黄黑道、年家神煞、月家神煞、日家神煞、时家神煞清单。
  2. 按 `event_type` 查 rules.md 对应规则（XR-05~XR-16）。
  3. 检查通用凶日（XR-08）：十恶大败、四废、五墓、月破、月厌、复日、伏断。
  4. 检查通用吉日（XR-08）：天德、月德、天恩、母仓、生气、四相、时德。
  5. 如提供 `direction`，由 `mingli-master.selection.v1` 检查年家三煞、大将军、太岁、月家三煞所在方位。
  6. 如提供 `relevant_bazi`，由 `mingli-master.selection.v1` 检查与四柱相关的避忌（如重丧、嫁娶周堂）。
  7. 输出每个候选日的"官方裁判"吉凶清单。
  8. 如用户同时查阅民间通书（董公 / 玉匣记），按"官方为权威裁判"输出对照说明。
  9. 输出加 caveat："文化参考，非事实判断"。
- **outputs**：候选日的"官方口径"吉凶清单 + 方位避忌
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：vol-12-nianbiao-yi；vol-26/yongshi-ba；vol-32/yongshi-jiu
- **verified**：false

## XP-02 嫁娶择日

- **name**：嫁娶择日（官方系）
- **inputs**：
  - `bride_bazi` / `groom_bazi`（男女四柱，建议必填）
  - `candidate_dates`（候选日期范围）
- **steps**：
  1. 走 XP-01 通用流程取候选日。
  2. 按 XR-05 检查嫁娶专用吉神（不将日、要安、生气、母仓）与凶神（孤辰寡宿、月破、月厌、十恶大败）。
  3. 由 `mingli-master.selection.v1` 检查"嫁娶周堂"忌位（翁、姑、第、堂、夫、妇、父、母）。
  4. 由 `mingli-master.selection.v1` 检查男女双方"本命冲克日"。
  5. 输出"官方裁判"。
  6. **必须 reframe**："文化参考，非事实判断；现代婚姻不以此作决策依据。"
- **outputs**：嫁娶候选日的吉凶清单 + 周堂避忌
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：vol-09-lijing；vol-14/yiji-yi；vol-31/yili-xia
- **verified**：false

## XP-03 起造 / 动土 / 修建择日

- **name**：起造修建择日（官方系）
- **inputs**：
  - `candidate_dates`（候选日期范围）
  - `direction`（坐山方位，建议必填）
  - `house_owner_bazi`（屋主四柱，可选）
- **steps**：
  1. 走 XP-01 通用流程。
  2. 按 XR-06 检查起造吉凶。
  3. 由 `mingli-master.selection.v1` 检查方位避忌：年家三煞、月家三煞、太岁、岁破、大将军、罗㬋、土王用事日。
  4. 如同时上梁/立柱，按"上梁吉日""立柱吉日"专用神煞查询。
  5. 输出"官方裁判"。
  6. **必须 reframe**："文化参考，非事实判断"。
- **outputs**：起造候选日的吉凶清单 + 方位避忌
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：vol-10-yiji-shang；vol-15-nianbiao-si；vol-16-nianbiao-wu
- **verified**：false

## XP-04 丧葬择日

- **name**：丧葬择日（官方系）
- **inputs**：`candidate_dates`（候选日期范围）；`deceased_bazi`（亡者四柱，可选）；`burial_direction`（坐山方位，可选）
- **steps**：
  1. 走 XP-01 通用流程。
  2. 按 XR-07 检查丧葬专用吉凶（鸣吠日、鸣吠对日、不将日 vs 重丧日、三丧日、复日、伏断日）。
  3. 由 `mingli-master.selection.v1` 检查与亡者四柱相关的"重丧""三丧"避忌。
  4. 如提供坐山方位，检查"年克山家""月克山家"。
  5. **必须 reframe**："文化参考，非事实判断；现代殡葬不以此作时间决策。"
- **outputs**：丧葬候选日的吉凶清单 + 方位避忌
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：vol-11-yiji-xia；vol-31/yili-xia
- **verified**：false

## XP-05 出行 / 上任择日

- **name**：出行 / 上任 / 受官择日
- **inputs**：`candidate_dates`（候选日期范围）；`direction`（出行方向，可选）
- **steps**：
  1. 走 XP-01 通用流程。
  2. 按 XR-09 检查出行 / 上任专用吉凶（驿马、天马 vs 往亡日、归忌日、四离四绝、杨公忌）。
  3. 检查 DR-05 黄道吉时（青龙、明堂、金匮、天德、玉堂、司命）。
  4. **必须 reframe**："文化参考，非事实判断"。
- **outputs**：出行 / 上任候选日的吉凶清单 + 吉时
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：vol-13-nianbiao-er；vol-20-yuebiao-si
- **verified**：false

## XP-06 选时（黄黑道吉时）

- **name**：选时（按日支推十二时辰黄黑道）
- **inputs**：`target_date`（目标日期，干支）；`event_type`（用事类型）
- **steps**：
  1. 调用 `mingli-master.selection.v1` 取得目标日的"日支建除"和当日十二时辰的黄黑道分布。
  2. 按 XR-08 取黄道六时（青龙、明堂、金匮、天德、玉堂、司命）为吉。
  3. 排除黑道六时（天刑、朱雀、白虎、天牢、玄武、勾陈）。
  4. 检查贵人登天门时（贵人临亥位）为大吉。
  5. 输出该日的吉时清单。
- **outputs**：当日的黄道吉时清单
- **tool_dependencies**：`mingli-master.selection.v1`（必需）
- **source_chapter**：vol-12-nianbiao-yi
- **verified**：false

## XP-07 辨讹审核

- **name**：辨讹审核（与民间通书冲突时的官方裁判）
- **inputs**：`candidate_dates`（已由民间通书 / 其它书出过的候选日）；`source_pack`（来源 pack，如 donggong-zeri / yuqia-ji）
- **steps**：
  1. 走 XP-01 通用流程取本 pack 的官方裁判。
  2. 与 `source_pack` 对比口径差异。
  3. 按 XR-17 辨讹规则订正：废除"罗天大进、上吉七圣、太极贵人"等无据虚名；订正错误起例；废除"诸事不宜/百事大吉"绝对化判语。
  4. 输出口径差异说明 + 官方裁判。
- **outputs**：差异说明 + 官方裁判
- **tool_dependencies**：`mingli-master.selection.v1`（必需）；`selection/donggong-zeri` / `selection/yuqia-ji`（按需）
- **source_chapter**：vol-33/bian-e-yi~vol-36/bian-e-si
- **verified**：false

---

## 流程总图

```text
[用户问题：择日 / 选时]
       │
       ├─► mingli-master.selection.v1（必需，取干支/神煞/建除/黄黑道/方位）
       │
       ├─► XP-01 官方择日总流程
       │     ├─► XP-02 嫁娶（XR-05）
       │     ├─► XP-03 起造（XR-06）
       │     ├─► XP-04 丧葬（XR-07）
       │     └─► XP-05 出行/上任（XR-09）
       │
       ├─► XP-06 选时（XR-08 黄黑道）
       │
       └─► XP-07 辨讹审核（XR-17，与民间通书冲突时使用）
                 ├─► 对比 selection/donggong-zeri
                 └─► 对比 selection/yuqia-ji
```

---

**严格禁止**：
- 不允许 LLM 手算干支、月建、神煞、建除、黄黑道、年家方位煞。
- 不允许 LLM 直接断"某日吉""某日凶""某方位煞"。
- 所有事实层判断必须经 `mingli-master.selection.v1` 起盘。
- 涉及医事（XR-16），必须强调"不替代任何医疗决策"。

共 7 条流程，Batch D2 evidence-chain 修复。
