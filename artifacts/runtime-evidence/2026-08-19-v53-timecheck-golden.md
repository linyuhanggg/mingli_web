# 2026-08-19 寻时定盘 / time-check 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
这份 release 名字就是 v53-time-check。不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-timecheck-golden.py
```

## 三问

1. **签名制品里有什么？** 有 `time-check` provider（`mingli-master.time-check.v1` / `TimeCheckProvider`）：十二时辰候选复用八字 Runtime，加有界结构化事件比较。10 个 output binding（candidates / rankings / event_matches / event_evidence 等）。`evidence_profile_id=bazi`。没有 `time-check.*` CU，没有寻时专用规则包（1328 条命中 0），没有黄金夹具。完整古法校时、候选淘汰和结论未接。
2. **工作树有没有未进签名的实现？** 没有。`time-check.json`、`TimeCheckProvider` 类、`calendar_core.py`、`brief.py` 与制品相同。`providers.py` 整文件不同只因第 4 个八字 CU，不是寻时实现。
3. **现有 brief / evidence 会不会带上？** 不会带寻时 CU 或黄金夹具（没有）。`brief.py` 无 time-check 特化，`finding_bindings` 为空。寻时输出在 calculated facts。`brief.evidence[]` 若出现是复用八字规则选择器，不是寻时黄金样例。

## 实跑数字

见同目录 `2026-08-19-v53-timecheck-golden.stdout.txt`。
