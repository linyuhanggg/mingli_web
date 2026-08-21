# 2026-08-19 P10-006 / P10-009 六爻旺衰救应只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-liuyao-wangshuai-jiuying.py
```

## 实跑数字

- 签名 CU：`['bazi.month-order-state-v1', 'bazi.ziping-pattern-entry-v1', 'bazi.tiaohou-priority-v1']`（3 个，全是 bazi）
- 工作树 CU：`['bazi.month-order-state-v1', 'bazi.day-master-root-support-v1', 'bazi.ziping-pattern-entry-v1', 'bazi.tiaohou-priority-v1']`（多 `bazi.day-master-root-support-v1`，仍无 liuyao.*）
- `liuyao.py` 哈希相同：`True`
- `providers/liuyao.json` 哈希相同：`True`
- 签名 liuyao `finding_bindings`：['dimension_candidates', 'line_relations']

## 三问

### 1. 签名制品里有没有旺衰/救应 CU 或 provider

有 **liuyao provider**（`resources/runtime/providers/liuyao.json` + `scripts/reading_engine/liuyao.py` 1.4.0），没有 **旺衰/救应 Claim Unit**。
`providers.py` 只声明三个 bazi CU。

已进制品的是盘面计算，不是 CU：

- `month_day_strength` / `_strength_state`：爻的旺/相/休/囚/死
- `useful_spirit_selection.strength_evidence`：绑 `divination/zengshan-buyi#ZR-05-05`（四时旺相），`hard_verdict=null`，`requires_school_adjudication=true`
- 求财角色：`HJC-R009`、两现取动 `ZR-04-04`（不判旺衰/救应）
- 「动变生克与救应」「月日旺衰与空破冲合」只写在 `unresolved_checks` 里

证据索引里带「旺衰/救应」字样的 divination 规则都是 `runtime_active=false`（如 `HJC-R005` 伤需救）。`ZR-05-05` 标题是「四时旺相」，是季节档，不是救应 CU。

### 2. 工作树有没有未进签名的实现

没有。`liuyao.py` 与 `liuyao.json` 和制品字节级相同。工作树多出来的 CU 只有 `bazi.day-master-root-support-v1`。没有 `fact_contracts/liuyao.py`，没有 `liuyao.*` claim_unit_id。core-only 里出现「旺衰/救应」的是书目笔记和 replay 夹具，不是未签名实现。

### 3. 现有 brief/evidence 会不会带上它们

- **不会**带旺衰/救应 CU：两边都没有 `claim_unit_id`，`_bazi_public_claim_findings` 只服务 bazi。
- liuyao 的 `brief.findings` 只有 `dimension_candidates`（用神候选）和 `line_relations`（世应动关系），没有 claim_unit。
- **救应**不会进 `brief.evidence[]`：没有 active 救应规则，只是未决检查文案。
- **旺衰事实**会走盘面输出：`month_day_strength`、`useful_spirit_selection.strength_evidence`（内嵌 ZR-05-05 source_ref）。这是 calculated 事实，不是 CU。`ZR-05-05` 也可能进 `source_conditioned_patterns`（谓词命中），进不进 `brief.evidence[]` 仍走通用选择器，不是旺衰/救应单位。

CHECKLIST 原文仍写：旺衰救应、成败应期未完成，P10-006 / P10-009 保持 `IN_PROGRESS`。
