# 2026-08-19 运势 / fortune 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-fortune-golden.py
```

## 三问

1. **签名制品里有什么？** 有 `fortune` provider（`mingli-master.fortune.v6`）：日/周近时事实，复用本命八字，不重算命盘。6 个 output binding + `period_markers` 等 extension。SOURCE_ROUTE 用三套八字包（yuanhai-ziping / ditiansui-chanwei / qiongtong-baojian）。没有 `fortune.*` CU，没有 fortune 专用规则包（1328 条里 pack 命中 0），没有黄金夹具。`finding_bindings` 为空。
2. **工作树有没有未进签名的实现？** 没有新的运势算法/CU。`fortune.json`、`near_time_fortune_adapter.py`、`FortuneProvider` 与制品字节相同。core-only 的 `fortune_calc.py` 是同一 adapter 的 CLI 包装；`fortune-v51.yaml`（36）和 `bazi-fortune-v51.yaml`（34）是测试 oracle，不是未签名实现。
3. **现有 brief / evidence 会不会带上黄金样例？** 不会。夹具 id 不进 `ReadingBrief`。`brief.py` 无 fortune 特化，没有 CU findings。`brief.evidence[]` 若出现是八字规则选择器，不是运势黄金样例。

## 实跑数字

见同目录 `2026-08-19-v53-fortune-golden.stdout.txt`。
