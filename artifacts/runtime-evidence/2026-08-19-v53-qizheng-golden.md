# 2026-08-19 P10-003 七政黄金样例只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / 220）vs 工作树 `core/mingli-master`。
七政 Runtime 名是 `xingming`。不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-qizheng-golden.py
```

## 实跑数字

- 签名 / 工作树 `xingming.*` / `qizheng.*` CU：`[]` / `[]`
- 实现文件哈希相同（xingming.py / xingming.json / 紫气校准表）：`True`
- 签名规则包：{'xingming/guotian-jing': {'n': 32, 'active': 1}, 'xingming/xingming-suyuan': {'n': 46, 'active': 1}, 'xingming/xingxue-dacheng': {'n': 9, 'active': 1}}
- runtime_active 正式规则：['xingming/guotian-jing#GR-01-01', 'xingming/xingming-suyuan#XR-M01', 'xingming/xingxue-dacheng#XXDC-M01']
- 黄金夹具 `references/fixtures/xingming-v51.yaml` 在签名树：`False`；工作树病例数：30
- `xingming.json` `finding_bindings`：`None`
- outputs：['ephemeris', 'classical_positions', 'ming_shen', 'houses', 'transformations', 'major_limits', 'source_conditioned_patterns']

## 三问

### 1. 签名制品里七政有哪些正式规则包/黄金样例/CU

- **Provider**：`mingli-master.xingming.v1`（adapter 1.1.0）
- **规则包三套**：`xingming/guotian-jing`（32，active 1）、`xingming/xingming-suyuan`（46，active 1）、`xingming/xingxue-dacheng`（9，active 1）。SOURCE_ROUTE 三包都用。
- **正式 active+verified 规则三条**：`GR-01-01` 起八字法、`XR-M01` 主曜身宫与经用、`XXDC-M01` 十二宫事实次序
- **CU**：没有 `xingming.*` / `qizheng.*` claim_unit
- **黄金样例**：签名树没有 `xingming-v51.yaml`

### 2. 工作树有没有未进签名的七政实现

没有新的七政算法/CU。实现文件与制品字节相同。工作树多的是书目笔记、审计测试，以及 core-only 回归夹具 `xingming-v51.yaml`（Astronomy Engine 2.1.19 oracle，30 例：18 参考盘 + 4 日界 + 4 地点 + 4 时区）。夹具是测试 oracle，不是未签名实现。

### 3. 现有 brief/evidence 会不会带上黄金样例

不会。夹具 id 不进 `ReadingBrief`。`finding_bindings` 为空，没有七政 CU findings。`GR-01-01` / `XR-M01` / `XXDC-M01` 可以进 `source_conditioned_patterns`，进不进 `brief.evidence[]` 仍走通用选择器，那是规则不是黄金样例。

P10-003 仍是 `IN_PROGRESS`（专用 Provider/VM/黄金样例未收口）。
