---
slug: taiyi-shenshu
file: procedures
---

# 太乙神数操作流程

> V5.1 的生产事实只来自 `scripts/run_reading_transaction.sh` 调用的确定性 Taiyi
> provider。本文件描述数据契约，不提供手算捷径、固定断语或第二生产入口。

## TP-01 年计起局

- **proc_id**: TP-01
- **status**: verified
- **scope**: `annual_macro_historical_board_facts`
- **inputs**:
  - 共享历法规范化结果及其 `calendar_digest`
  - 公元农历年、年干支、时区和地点
  - 固定 profile `taiyi-jinjing-annual-yang-board-v1`
- **steps**:
  1. 校验共享历法摘要，读取农历年；不得从用户文字猜年份。
  2. 按 `jinjing-annual-tang-jiazi-v1` 计算一算起例积年。
  3. 计算 360 年周期位置、六纪、五子元、72 局和理天/理地/理人。
  4. 计算太乙、天目/文昌、计神、合神和始击/客目。
  5. 沿十六神环计算主客算，再计算主客大将与参将。
  6. 计算各自独立积年 profile 下的卷五长周期诸神。
  7. 生成盘面摘要、来源身份、profile 身份和嵌套摘要。
- **outputs**:
  - `epoch`、`cycle`、`board`
  - `taiyi_position`、`wenchang`、`tianmu`、`shiji`、`kemu`
  - `jishen`、`heshen`、`host_guest_counts`、`four_generals`
  - `long_cycle_deities`、`scope_contract`、`source_rule_ids`
- **failure_policy**: 缺少时间、时区、地点、共享历法摘要或公元年时拒绝计算；不接受用户提供的盘面替代计算。
- **dependency_rules**: TR-01 ~ TR-05、TR-10、TR-12

## TP-02 盘面关系谓词

- **proc_id**: TP-02
- **status**: verified
- **inputs**: TP-01 的摘要绑定盘面
- **steps**:
  1. 只从太乙、二目、四将和门位的确定位置计算关系。
  2. 每个关系记录 `predicate_id`、参与事实路径和精确古籍锚点。
  3. 不在事实层附加现代事件、胜负或灾异结论。
- **outputs**: 掩、击、迫、囚、关、格、对、四郭固、四郭杜、执提、提挟中实际成立的谓词集合
- **dependency_rules**: TR-08、TR-09

## TP-03 卷五诸神

- **proc_id**: TP-03
- **status**: verified
- **inputs**: 公元农历年
- **steps**:
  1. 君基、臣基、民基使用 `upper-jiayin-long-cycle-v1`。
  2. 五福、大游使用 `wufu-dayou-long-cycle-v1`。
  3. 小游、四神、天乙、地乙、直符使用 `xiaoyou-four-deity-v1`。
  4. 每一项同时输出积年、周期余数、位置和 source anchor；禁止复用年计主盘积年。
- **outputs**: 十项位置事实及各自 `epoch_profile`
- **dependency_rules**: TR-10、TR-12

## TP-04 证据绑定

- **proc_id**: TP-04
- **status**: verified
- **inputs**: 最新问题的 IntentFrame、TP-01/TP-02 事实、声明范围
- **steps**:
  1. 起例证据只能绑定对应的 epoch、cycle、bureau 或 placement 事实。
  2. 关系证据只能在同名 `predicate_id` 已计算成立时激活。
  3. 卷五诸神证据必须绑定同一 deity 和 epoch profile。
  4. 零命中保持零；标题、表头、manifest、采集说明和无关历史章节不得进入候选。
- **outputs**: 具有精确事实引用和来源锚点的证据候选；不生成判断或成稿

## TP-05 追问

- **proc_id**: TP-05
- **status**: verified
- **inputs**: 已验证基础盘、最新问题和新的 IntentFrame
- **steps**:
  1. 同一农历年的年计基础盘可复用，但必须重新校验 calculation digest。
  2. 最新问题重新生成事实扩展、证据、反证、判断和回答摘要。
  3. 若补充信息改变农历年或 profile，必须重算，不得沿用旧盘。
- **outputs**: 稳定的 calculation digest 与新的 intent/evidence/judgment digests

## TP-06 范围拒绝

- **proc_id**: TP-06
- **status**: verified
- **provider_scope**: annual macro/historical board facts
- **not_calculated**:
  - 个人命法
  - 个人事件即时占
  - 月计、日计、時計、分计
  - 七术和十六推占的现代应用
  - 现代军事、医疗、法律或灾异决策
- **routing_contract**: resolver 不得把上述请求声明为本 provider 已支持；可选择真正兼容的其他体系，或明确返回能力不匹配。

## 通用完整性契约

- provider 必须通过 72 局主表、30 个固定外部工程参考盘、共享历法边界和来源依赖删除攻击。
- 同一输入的事实摘要必须稳定；来源表、历法、profile 或任一嵌套事实变化都必须改变相应摘要或使校验失败。
- 外部工程项目只作对照；与原典不一致时以经过锚定的原典公式和立成为准并记录差异。
- LLM 只负责 IntentFrame、古籍裁判、反证、内部复核和自然中文表达，不手算盘面事实。
