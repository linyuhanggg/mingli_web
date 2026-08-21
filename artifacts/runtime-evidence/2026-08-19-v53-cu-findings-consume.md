# 消费层对接：签名 3 个 CU 在 prepare findings 的字段路径

Date: 2026-08-19 (CST). 只写说明。未改 FastAPI / 合同 / .runtime，未 resign。
展示接线是消费层的刀，不是算法刀。project_bazi_view_model 目前忽略 findings。

准入：签名 V53 c451de5e / 663543e。
取样：1994 career prepare。1992 同形；乙酉 overview 没有 ziping 这条 finding（随盘）。

## 怎么取

brief.findings[] 里筛 data.claim_unit_id。不要从 finding.interpretive_candidates 编列表。

公共外壳（3 条 CU 相同）：
- ref = finding:{subject}/bazi/public-claim/{month-order-state|ziping-pattern-entry|tiaohou-priority}
- kind_id = kind.tendency
- support_mode = exact
- public_text = 给用户看的未裁定原文（唯一该下发的句子）
- data.claim_unit_id
- data.hard_verdict = null
- fact_refs 指向 calculated facts
- evidence_refs 可空；引文以 brief.evidence[] 为准

brief.findings[0] 是 kind_id=finding.interpretive_candidates，没有 claim_unit_id，也没有 public_text。空着就空着，不要当 CU。

## 三条 CU

1. bazi.month-order-state-v1
   - ref 后缀 /bazi/public-claim/month-order-state
   - data.day_element / data.month_command_element / data.seasonal_state
   - 1994: 火/土/休；1992: 木/金/死；乙酉: 火/火/旺
   - public_text 已写明只确定月令季节状态，整盘身强身弱仍未裁定

2. bazi.ziping-pattern-entry-v1
   - ref 后缀 /bazi/public-claim/ziping-pattern-entry
   - data.status（1994/1992 = adjudicated_pattern_entry）
   - data.pattern_label（1994=食神格入口，1992=正官格入口）
   - 乙酉 overview：finding 不存在，不要补
   - public_text 已写明只确定格局入口，格局成败、救应、旺衰和行运仍未裁定

3. bazi.tiaohou-priority-v1
   - ref 后缀 /bazi/public-claim/tiaohou-priority
   - data.day_stem / data.month_branch / data.priority_stems
   - 1994: 丙 / 辰 / [壬, 甲]
   - public_text 已写明只记录候选与显藏缺失，唯一用神或吉凶仍未裁定

## 消费层不该做

- 不发明 self_sit
- 不把 hard_verdict=null 画成偏强/偏弱条
- 不把 priority_stems 写成唯一用神
- 不把 pattern_label 写成格局已成
- 不接下发第 4 个 bazi.day-master-root-support-v1（不在制品）
- 不改 OpenAPI / DESIGN；有字段再接，没有就空着
