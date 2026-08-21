# 2026-08-19 P10-002 紫微黄金样例只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-ziwei-golden.py
```

## 实跑数字

- 签名 / 工作树 `ziwei.*` CU：`[]` / `[]`
- 实现文件哈希相同（adapter / runtime.js / ziwei.json / iztro.min.js）：`True`
- 签名紫微规则包：{'ziwei/feixing-ziwei-doushu-yuanzhi': {'n': 14, 'active': 0, 'verified': 0}, 'ziwei/taiwei-fu': {'n': 21, 'active': 1, 'verified': 1}, 'ziwei/ziwei-doushu-quanshu': {'n': 60, 'active': 1, 'verified': 1}}
- runtime_active 正式规则：['ziwei/taiwei-fu#TR-01', 'ziwei/ziwei-doushu-quanshu#ZW-M01']
- 黄金夹具 `references/fixtures/ziwei-v51.yaml` 在签名树：`False`；工作树病例数：32
- `ziwei.json` `finding_bindings`：`None`
- outputs：['ming_shen', 'palaces', 'stars', 'sihua', 'interpretive_candidates', 'source_conditioned_patterns']

## 三问

### 1. 签名制品里紫微有哪些正式规则包/黄金样例/CU

- **Provider**：`mingli-master.ziwei.iztro`（adapter 1.2.0 + iztro 2.5.8）
- **规则包三套**：`ziwei/ziwei-doushu-quanshu`（60，active 1）、`ziwei/taiwei-fu`（21，active 1）、`ziwei/feixing-ziwei-doushu-yuanzhi`（14，active 0）。SOURCE_ROUTE 只用前两包。
- **正式 active+verified 规则两条**：`ZW-M01` 十二宫次序、`TR-01` 至玄至微
- **CU**：没有 `ziwei.*` claim_unit
- **黄金样例**：签名树没有 `ziwei-v51.yaml`，不随制品走

### 2. 工作树有没有未进签名的紫微实现

没有新的紫微算法/CU。四份实现文件与制品字节相同。工作树多的是书目笔记、审计测试，以及 core-only 回归夹具 `ziwei-v51.yaml`（含 `known-public-1970` 等 32 例）。夹具是测试 oracle，不是未签名实现。

### 3. 现有 brief/evidence 会不会带上黄金样例

不会。夹具 id 不进 `ReadingBrief`。`finding_bindings` 为空，没有紫微 CU findings。`ZW-M01` / `TR-01` 可以进 `source_conditioned_patterns`，进不进 `brief.evidence[]` 仍走通用选择器，那是规则不是黄金样例。

P10-002 仍是 `IN_PROGRESS`（专用 Provider/VM/黄金样例未收口）。
