# 2026-08-19 风水 / fengshui 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 -B /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-fengshui-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-fengshui-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`

八字《神峰通考》`bazi/shenfeng-tongkao` 未计入风水：trap 行=5，全部排除。

## 三问

1. **签名制品里风水有哪些正式规则包 / 黄金样例 / CU / provider / output？**
   - Provider：`fengshui` / `mingli-master.fengshui.v1`，entrypoint `reading_engine.providers:FengshuiProvider`，adapter `1.0.0`，evidence_profile `fengshui`。
   - Output 11：`observation_provenance` `compass` `building_chronology` `layout_graph` `form` `liqi` `active_source_rule_ids` `conflicts` `uncertainties` `critical_missing` `source_conditioned_patterns`。extension 1：`observed_spatial_scope`。
   - finding_bindings=0。
   - SOURCE_ROUTE 静态 `packs=[]`。无输出时规划层只写死两包字面：`fengshui/huangdi-zhaijing`、`fengshui/yangzhai-shishu`；实际 packs 按事实里的 `active_source_rule_ids` / form 观察动态填。
   - 正式规则包 16 套（`fengshui/*`，evidence-rules 总 1328 行里风水 179 行）：
     - `dili-bianzheng` 5/0/0
     - `dutian-baozhao-jing` 14/0/0
     - `hanlong-jing` 15/1/1
     - `huangdi-zhaijing` 7/1/1
     - `qingnang-aoyu` 8/0/0
     - `qingnang-jing` 11/0/0
     - `qingnang-xu` 11/0/0
     - `rudi-yan-quanshu` 7/0/0
     - `shenshi-xuankong-xue` 5/0/0
     - `tianyu-jing` 16/0/0
     - `xuexin-fu` 5/1/1
     - `yangzhai-sanyao` 7/1/1
     - `yangzhai-shishu` 18/2/2
     - `yilong-jing` 25/1/1
     - `zangfa-daozhang` 10/0/0
     - `zangshu` 15/1/1
   - runtime_active 且 verified 的 8 条（与 `route: fengshui` scope 完全同一集合）：`hanlong-jing#R-01` `huangdi-zhaijing#HDZJ-R006` `xuexin-fu#XXF-R01` `yangzhai-sanyao#YZS-R005` `yangzhai-shishu#YZS-R003` `yangzhai-shishu#YZS-R014` `yilong-jing#R-05` `zangshu#R-02`。其余 171 条 `inactive_unverified`。
   - CU：`fengshui.*` 签名/工作树都是 `[]`。制品全部 CU 仍是 3 条八字：`month-order` / `ziping` / `tiaohou`。
   - 黄金样例：签名树无 `fengshui-v51.yaml`（`golden_fixture_in_signed=False`）。

2. **工作树有没有未进签名的风水实现？**
   没有未签名算法/CU。`fengshui.py` / `fengshui.json` / 源表 / 16 套 `rules.md`+`quote-index.md` 与制品字节相同（`hash_mismatch_n=0`）；`FengshuiProvider` 类文本相同。`providers.py` 整文件哈希不同，是因为工作树多一条八字 `bazi.day-master-root-support-v1`，风水类未改。core-only 89 份：81 份书目笔记（含 `system-cards/fengshui.md`）、3 份 test/audit/evaluator、5 份夹具（`fengshui-v51.yaml` + 4 svg）。夹具 56 个 id：asset 4 + compass 24 + observation 21 + special 7；另有 8 条无 id 的八宅卦例。`unsigned_impl_n=0`，`content_engine_diff=[]`。夹具是测试 oracle，不是未签名实现。

3. **现有 brief / evidence 会不会带上黄金样例？**
   不会。`brief.py` / `evidence_rules.py` 都不读 `references/fixtures`，风水 token hits=0。56 个夹具 id + `fengshui-v51` / `mingli-fengshui-fixtures-v51` / `classical_case` 在 `brief.py`、`evidence_rules.py`、签名 `fengshui.py`、`evidence-rules.jsonl`、scope binding 的命中和都是 0。夹具不在签名树，无法进 `ReadingBrief`。8 条已 verified 的 `fengshui/*#*` 可以进证据选择器，那是正式规则不是黄金样例。finding_bindings 不是 CU。

## 三行结论

1. 签名有 `fengshui`/`mingli-master.fengshui.v1`、11 output+1 extension、0 finding_bindings、16 专用规则包（179/8/8）、scope `route:fengshui`=8、无 `fengshui.*` CU、无黄金夹具。
2. 工作树无未进签名的风水实现（impl 哈希全同，core-only=89 全是笔记/测试/夹具，unsigned_impl_n=0）。
3. brief/evidence 不会带上黄金样例（夹具 id 命中和=0，brief 不加载 fixtures）。
