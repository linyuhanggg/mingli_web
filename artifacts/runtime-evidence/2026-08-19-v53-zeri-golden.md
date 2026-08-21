# 2026-08-19 择日 / zeri / selection 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。
计数与寻时 `time-check`、运势 `fortune`、太乙、风水分开；`model-selection` / `model_selection` 不算择日。

## 复跑

```bash
python3 -B /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-zeri-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-zeri-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`

同树另有独立 provider `time-check` / `fortune` / `taiyi` / `fengshui`，择日路径与它们 overlap=0。风水《阳宅十书》「选择」正文 6 行未计入择日。

## 三问

1. **签名制品里择日有哪些正式规则包 / 黄金样例 / CU / provider / output？**
   - Provider：`selection` / `mingli-master.selection.v1`，entrypoint `reading_engine.providers:SelectionProvider`，adapter `1.3.0`，evidence_profile `selection`。
   - Output 10：`event_profile` `calendar_candidates` `date_time_candidates` `eligible_candidates` `eligible_date_time_candidates` `eliminations` `ranking` `lineage_policy` `no_valid_candidate` `source_conditioned_patterns`。extension 1：`bounded_ranked_candidate_facts`。
   - finding_bindings=0。
   - SOURCE_ROUTE 正式两包：`selection/xieji-bianfang-shu`、`selection/xingli-kaoyuan`。民俗对照两包（仅 `include_folk_comparison=true` 才激活）：`selection/yuqia-ji`、`selection/donggong-zeri`。
   - 正式规则包 4 套（`selection/*`，evidence-rules 总 1328 行里择日 68 行）：
     - `donggong-zeri` 10/0/0
     - `xieji-bianfang-shu` 18/1/1
     - `xingli-kaoyuan` 20/1/1
     - `yuqia-ji` 20/0/0
   - runtime_active 且 verified 的 2 条：`xieji-bianfang-shu#XR-18` `xingli-kaoyuan#KR-05`。其余 66 条 `inactive_unverified`。
   - scope `route: selection` 只有 1 条：`xingli-kaoyuan#KR-05`。XR-18 虽 runtime_active+verified，不在 scope binding。
   - CU：`selection.*` / `zeri.*` 签名/工作树都是 `[]`。制品全部 CU 仍是 3 条八字：`month-order` / `ziping` / `tiaohou`。
   - 黄金样例：签名树无 `selection-v51.yaml`（`golden_fixture_in_signed=False`）。

2. **工作树有没有未进签名的择日实现？**
   没有未签名算法/CU。`selection.py` / `selection.json` / 源表 / 事实层 profile / 4 套 `rules.md`+`quote-index.md` + `donggong-zeri/monthly-day-table.md` 与制品字节相同（`hash_mismatch_n=0`）；`SelectionProvider` 类文本相同。`providers.py` 整文件哈希不同，是因为工作树多一条八字 `bazi.day-master-root-support-v1`，择日类未改。core-only 34 份：27 份书目笔记（含 `system-cards/selection.md`、神煞精修矩阵、vendor 摘录）、6 份 test/audit/evaluator、1 份夹具 `selection-v51.yaml`。`unsigned_impl_n=0`，`content_engine_diff=[]`。夹具是测试 oracle，不是未签名实现。`test_v51_model_selection_fallback.py` 是模型选型，未计入择日。

3. **现有 brief / evidence 会不会带上黄金样例？**
   不会。`brief.py` / `evidence_rules.py` 都不读 `references/fixtures`，择日 token hits=0。333 个夹具 id（日历 30 + 公式 222 + 外部对照 30 + 完成 5 + 边界 8 + 用事 7 + 规则 30 + 无候选 1，section_sum=333）在 `brief.py`、`evidence_rules.py`、签名 `selection.py`、`evidence-rules.jsonl`、scope binding 的命中和都是 0。夹具不在签名树，无法进 `ReadingBrief`。`selection.py` 的 `TABLE_PROFILE=xieji-official-cnlunar-v1` 命中 1 次，那是官方历表 profile 名，不加载 `selection-v51.yaml`。2 条已 verified 的 `selection/*#*` 可以进证据选择器，那是正式规则不是黄金样例。finding_bindings 不是 CU。

## 三行结论

1. 签名有 `selection`/`mingli-master.selection.v1`、10 output+1 extension、0 finding_bindings、4 专用规则包（68/2/2）、scope `route:selection`=1（仅 KR-05）、无 `selection.*` CU、无黄金夹具。
2. 工作树无未进签名的择日实现（impl 哈希全同，core-only=34 全是笔记/测试/夹具，unsigned_impl_n=0）。
3. brief/evidence 不会带上黄金样例（333 个夹具 id 命中和=0，brief 不加载 fixtures）。
