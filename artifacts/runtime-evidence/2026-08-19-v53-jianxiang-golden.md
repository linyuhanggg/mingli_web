# 2026-08-19 见相 / jianxiang / physiognomy 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

别名只计 `physiognomy` / `jianxiang` / `mianxiang` / `见相` / `面相` / `相术`。八字、风水、择日、合参分开计数，未混入见相。

## 复跑

```bash
python3 -B /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-jianxiang-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-jianxiang-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`

其他系统 evidence 行未计入见相：八字 273、风水 179、择日 68、合参 0。这些包里见相别名命中 `trap_other_alias=0`。

## 三问

1. **签名制品里见相有哪些正式规则包 / 黄金样例 / CU / provider / output？**
   - Provider：`physiognomy` / `mingli-master.physiognomy.v1`，entrypoint `reading_engine.providers:PhysiognomyProvider`，adapter `1.1.0`，evidence_profile `physiognomy`。
   - Output 9：`observation_scope` `normalized_visible_observations` `missing_targets` `observation_conflicts` `cross_capture_variations` `source_comparison` `uncertainties` `critical_missing` `accepted_observation_fact_keys`。extension 1：`visible_observation_scope`。
   - finding_bindings=0。
   - SOURCE_ROUTE 静态 `packs=[]`。运行时按 `active_source_rule_ids` 从 SOURCE_PRIORITY 三包填：`physiognomy/liuzhuang-xiangfa`、`physiognomy/shenxiang-quanbian`、`physiognomy/mayi-shenxiang`。`bingjian` 不在 SOURCE_PRIORITY。
   - 正式规则包 4 套（`physiognomy/*`，evidence-rules 总 1328 行里见相 90 行）：
     - `bingjian` 31/0/0
     - `liuzhuang-xiangfa` 5/1/1
     - `mayi-shenxiang` 5/1/1
     - `shenxiang-quanbian` 49/1/1
   - runtime_active 且 verified 的 3 条（与 `route: physiognomy` scope 完全同一集合）：`liuzhuang-xiangfa#LZ-R01` `mayi-shenxiang#MR-02` `shenxiang-quanbian#SR-02-04`。其余 87 条 `inactive_unverified`。
   - catalog 4 书：`bingjian` `liuzhuang-xiangfa` `mayi-shenxiang` `shenxiang-quanbian`。
   - CU：`physiognomy.*` / `jianxiang.*` / `mianxiang.*` 签名/工作树都是 `[]`。制品全部 CU 仍是 3 条八字：`month-order` / `ziping` / `tiaohou`。
   - 黄金样例：签名树无 `physiognomy-v51.yaml`（`golden_fixture_in_signed=False`）。

2. **工作树有没有未进签名的见相实现？**
   没有未签名算法/CU。`physiognomy.py` / `physiognomy.json` / 源表 / 4 套 `rules.md`+`quote-index.md` 与制品字节相同（`hash_mismatch_n=0`）；`PhysiognomyProvider` 类文本相同。`providers.py` 整文件哈希不同，是因为工作树多一条八字 `bazi.day-master-root-support-v1`，见相类未改。core-only 37 份：22 份书目笔记（含 `system-cards/physiognomy.md`）、3 份 test/audit/oracle、12 份夹具（`physiognomy-v51.yaml` + annotation-manifest + 10 svg）。夹具 26 个 case_id：complete 21 + boundary 5；另有 algorithm-source-samples 3 条（`physiognomy-region-quality` / `physiognomy-no-invisible-feature` / `physiognomy-user-correction`，均不在签名树）。`unsigned_impl_n=0`，`content_engine_diff=[]`。夹具是测试 oracle，不是未签名实现。

3. **现有 brief / evidence 会不会带上黄金样例？**
   不会。`brief.py` / `evidence_rules.py` / `physiognomy.py` 都不读 `references/fixtures`，见相 token hits=0。26 个 case_id + `physiognomy-v51` / 3 条 algorithm key 在 `brief.py`、`evidence_rules.py`、签名 `physiognomy.py`、`evidence-rules.jsonl`、scope binding 的命中和都是 0。夹具不在签名树，无法进 `ReadingBrief`。源表 `physiognomy-source-tables-v1.yaml` 只把 3 个 boundary case_id 写成 algorithm_sample_contract 指针（needle 命中和=10），不加载夹具、不进入 brief/evidence 选择器。3 条已 verified 的 `physiognomy/*#*` 可以进证据选择器，那是正式规则不是黄金样例。finding_bindings 不是 CU。

## 三行结论

1. 签名有 `physiognomy`/`mingli-master.physiognomy.v1`、9 output+1 extension、0 finding_bindings、4 专用规则包（90/3/3）、scope `route:physiognomy`=3、无 `physiognomy.*` CU、无黄金夹具。
2. 工作树无未进签名的见相实现（impl 哈希全同，core-only=37 全是笔记/测试/夹具，unsigned_impl_n=0）。
3. brief/evidence 不会带上黄金样例（夹具 id 命中和=0，brief 不加载 fixtures）。
