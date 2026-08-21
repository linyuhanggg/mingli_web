# 2026-08-19 P10-008 大六壬黄金样例只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-liuren-golden.py
```

## 实跑数字

- 签名 / 工作树 `liuren.*` / `daliuren.*` CU：`[]` / `[]`
- 实现文件哈希相同（adapter / calc / json / 源表）：`True`
- 签名规则包：{'san-shi/daliuren-daquan': {'n': 18, 'active': 10}, 'san-shi/liuren-miben': {'n': 23, 'active': 3}, 'san-shi/liuren-zhiyin': {'n': 20, 'active': 10}}
- runtime_active 正式规则：23 条
- 黄金夹具 `references/fixtures/liuren-v51.yaml` 在签名树：`False`；工作树 classical_cases 39 + calendar_boundaries 8
- `liuren.json` `finding_bindings`：['dimension_facts', 'timing']（不是 CU）
- outputs：['four_lessons', 'three_transmissions', 'lesson_method', 'month_general', 'xunkong']

## 三问

### 1. 签名制品里大六壬有哪些正式规则包/黄金样例/CU

- **Provider**：`mingli-master.liuren.v7`（adapter 2.0.1）
- **规则包三套**：`san-shi/daliuren-daquan`（18，active 10）、`san-shi/liuren-zhiyin`（20，active 10）、`san-shi/liuren-miben`（23，active 3）
- **正式 active+verified 23 条**：课体/三传（DLR-02–10、17；LR-02–08、17–19）+ 秘本类象/求财/候期（LM-R01、R20、R21）
- **CU**：没有 `liuren.*` / `daliuren.*` claim_unit
- **黄金样例**：签名树没有 `liuren-v51.yaml`

### 2. 工作树有没有未进签名的大六壬实现

没有新的六壬 CU。adapter / calc / json / 源表与制品字节相同。工作树多书目笔记、审计测试、`liuren-v51.yaml` 回归夹具，以及未挂进签名 adapter 的 `liuren_current_state.py` / `liuren_process.py` 辅助脚本。这些不进当前 V53 输出。

### 3. 现有 brief/evidence 会不会带上黄金样例

不会。夹具 id 不进 `ReadingBrief`。findings 只有 `dimension_facts` / `timing`，没有 CU。23 条正式规则可以进 evidence 选择器，那是规则不是黄金样例。

P10-008 仍是 `IN_PROGRESS`（问题/侧重/时空黄金样例未收口）。
