# 2026-08-19 P10-007 奇门黄金样例只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-qimen-golden.py
```

## 实跑数字

- 签名 / 工作树 `qimen.*` CU：`[]` / `[]`
- 实现文件哈希相同（qimen.py / qimen.json / source-tables）：`True`
- 签名规则包：{'san-shi/qimen-dunjia-tongzhi': {'n': 38, 'active': 38}, 'san-shi/qimen-faqiao': {'n': 2, 'active': 2}}
- runtime_active 正式规则：40 条（QM-P01–P40，缺 P26/P36 在 faqiao）
- 黄金夹具在签名树：`{'qimen-v51.yaml': False, 'qimen-go-v51.yaml': False, 'qimen-pattern-contract-v51.yaml': False}`
- 工作树 core-only 夹具：`qimen-v51.yaml`（source_rule_boards 37 + pattern_coverage 40 + 其它 16）、`qimen-go-v51.yaml`（30 例外工程对照）、`qimen-pattern-contract-v51.yaml`（40 条谓词抄本）
- `qimen.json` `finding_bindings`：`None`
- outputs：['ju', 'chief', 'director', 'palaces', 'instruments_wonders', 'stars_doors_deities', 'xunkong', 'horse', 'named_patterns']

## 三问

### 1. 签名制品里奇门有哪些正式规则包/黄金样例/CU

- **Provider**：`mingli-master.qimen.v1`（adapter 5.2.0，时家转盘拆补）
- **规则包两套**：`san-shi/qimen-dunjia-tongzhi`（38 active+verified）、`san-shi/qimen-faqiao`（2：QM-P26 玉女守门、QM-P36 时墓）。SOURCE_ROUTE 两包都用。
- **正式规则 40 条**：QM-P01–P40 格局谓词，全部 runtime_active / verified
- **CU**：没有 `qimen.*` claim_unit
- **黄金样例**：签名树没有三份 `qimen-*.yaml` 夹具

### 2. 工作树有没有未进签名的奇门实现

没有新的奇门算法/CU。qimen.py / json / 源表与制品字节相同。工作树多的是书目笔记、审计测试，以及 core-only 回归夹具（含 qimen-go 工程对照）。夹具是测试 oracle，不是未签名实现。

### 3. 现有 brief/evidence 会不会带上黄金样例

不会。夹具 id 不进 `ReadingBrief`。`finding_bindings` 为空，没有奇门 CU findings。40 条 QM-P* 可以进盘面 `named_patterns` / 证据选择器，那是规则谓词不是黄金样例。

P10-007 仍是 `IN_PROGRESS`（问题/场景/时空黄金样例未收口）。
