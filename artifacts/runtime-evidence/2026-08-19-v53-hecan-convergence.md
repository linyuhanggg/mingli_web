# 2026-08-19 P10-005 / P10-010 合参只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
合参产品投影在 `backend/app/charts/projectors.py`，不在签名树里。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-hecan-convergence.py
```

## 实跑数字

- 签名 py/json 里 `convergence`：0 个文件 / 0 次
- 工作树 core py/json 里 `convergence`：0 个文件 / 0 次
- 签名 `brief.py`：`convergence=0` `disagreements=0`
- 签名 `disagreements` 出现在：['resources/runtime/providers/physiognomy.json', 'scripts/bazi_reasoning_tools.py', 'scripts/liuren_fact_adapter.py', 'scripts/reading_engine/physiognomy.py', 'scripts/reading_engine/providers.py']
- core 多出来的 disagreements 文件：['scripts/test_liuren_fact_adapter.py', 'scripts/test_v51_physiognomy_completion.py', 'scripts/fixtures/kintaiyi_taiyi_fixture_generator.py']（测试/矩阵，不是合参实现）
- `physiognomy.py` / `physiognomy.json` / `liuren_fact_adapter.py` / `brief.py` 与制品哈希相同：{'scripts/reading_engine/physiognomy.py': True, 'resources/runtime/providers/physiognomy.json': True, 'scripts/liuren_fact_adapter.py': True, 'scripts/reading_engine/brief.py': True}

## 三问

### 1. 签名制品里 convergence / disagreements 是空还是有结构

签名 Runtime **没有** `convergence` 字段（0 文件）。
`disagreements` 有，但不是三术合参：相学 `source_comparison.disagreements`（来源层保留）、大六壬 adapter 审计、八字 `preserved_disagreements`。`ReadingBrief` 不收这两键。

合参这两个键只存在于**消费层** `canwen-view/v1` / `hecan-view/v1` / `wenshi-view/v1`：

- Canwen/HeCan：`disagreements` 恒为空元组；`convergence` 默认空，仅当所选术都有 `dimension_fact_scope` 时填一句「范围均已提供；尚未形成实质性互证结论」
- Wenshi：两者都硬写成 `()`

CHECKLIST 仍写：`convergence`/`disagreements` 仍为空，不能记为互证或分歧裁决。P10-005 / P10-010 `IN_PROGRESS`。

### 2. 工作树有没有未进签名的合参实现

没有。core 里 `convergence` 仍是 0。`liuyao`/`providers` 合参结论相关实现未增。backend projector 只消费已有单术事实，不写互证，也不进签名树。

### 3. 现有 brief/evidence 会不会带上它们

不会。`brief.py` 不投影这两键；`brief.evidence[]` / `brief.findings[]` 没有 convergence/disagreements。合参页上的空槽是 projector 自填，不是 Runtime 输出。
