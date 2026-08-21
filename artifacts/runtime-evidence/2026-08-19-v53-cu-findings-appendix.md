# 三盘 findings 实测附录（签名 3 个 CU）

Date: 2026-08-19 (CST). 只写附录。未改 FastAPI / 合同 / .runtime，未 resign。
只下发 public_text。乙酉没有 ziping 就空着。第 4 个 root-support 三盘都没有。

## 可复跑

python3 -B artifacts/runtime-evidence/2026-08-19-v53-cu-findings-appendix.py

stdout: artifacts/runtime-evidence/2026-08-19-v53-cu-findings-appendix.stdout.txt

## 1994 career（n_cu_findings=3）

| claim_unit_id | public_text | 关键 data |
|---|---|---|
| bazi.month-order-state-v1 | 月令主气五行为土，日主五行火在该月令状态表中为“休”；这只确定月令季节状态，整盘身强身弱仍未裁定。 | day_element=火；month_command_element=土；seasonal_state=休；hard_verdict=null |
| bazi.ziping-pattern-entry-v1 | 子平月令入口按日干与月令主气的关系确定为“食神格入口”；这里只确定格局入口，格局成败、救应、旺衰和行运仍未裁定。 | status=adjudicated_pattern_entry；pattern_label=食神格入口；hard_verdict=null |
| bazi.tiaohou-priority-v1 | 按丙日主、辰月的已核验调候规则，候选次序为“壬、甲”；当前只记录候选与显藏缺失，唯一用神或吉凶仍未裁定。 | day_stem=丙；month_branch=辰；priority_stems=[壬, 甲]；hard_verdict=null |

## 1992 career（n_cu_findings=3）

| claim_unit_id | public_text | 关键 data |
|---|---|---|
| bazi.month-order-state-v1 | 月令主气五行为金，日主五行木在该月令状态表中为“死”；这只确定月令季节状态，整盘身强身弱仍未裁定。 | day_element=木；month_command_element=金；seasonal_state=死；hard_verdict=null |
| bazi.ziping-pattern-entry-v1 | 子平月令入口按日干与月令主气的关系确定为“正官格入口”；这里只确定格局入口，格局成败、救应、旺衰和行运仍未裁定。 | status=adjudicated_pattern_entry；pattern_label=正官格入口；hard_verdict=null |
| bazi.tiaohou-priority-v1 | 按乙日主、申月的已核验调候规则，候选次序为“丙、癸”；当前只记录候选与显藏缺失，唯一用神或吉凶仍未裁定。 | day_stem=乙；month_branch=申；priority_stems=[丙, 癸]；hard_verdict=null |

## 乙酉 overview（n_cu_findings=2）

| claim_unit_id | public_text | 关键 data |
|---|---|---|
| bazi.month-order-state-v1 | 月令主气五行为火，日主五行火在该月令状态表中为“旺”；这只确定月令季节状态，整盘身强身弱仍未裁定。 | day_element=火；month_command_element=火；seasonal_state=旺；hard_verdict=null |
| bazi.ziping-pattern-entry-v1 | （本盘无此 finding，不要补） | — |
| bazi.tiaohou-priority-v1 | 按丙日主、巳月的已核验调候规则，候选次序为“壬、庚”；当前只记录候选与显藏缺失，唯一用神或吉凶仍未裁定。 | day_stem=丙；month_branch=巳；priority_stems=[壬, 庚]；hard_verdict=null |

三盘都没有 bazi.day-master-root-support-v1。
