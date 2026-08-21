# 2026-08-19 梅花 / meihua 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 -B /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-meihua-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-meihua-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`

## 三问

1. **签名制品里梅花有哪些正式规则包 / 黄金样例 / CU / provider / output？**
   - Provider：`meihua` / `mingli-master.meihua.v1`，entrypoint `reading_engine.providers:MeihuaProvider`，adapter `1.1.0`，evidence_profile `meihua`。
   - Output 12：`upper_trigram` `lower_trigram` `moving_lines` `primary_hexagram` `mutual_hexagram` `changed_hexagram` `body_use` `body_relation_facts` `seasonal_strength` `interpretive_candidates` `casting_method` `source_conditioned_patterns`。
   - finding_bindings 2：`body_use` / `body_relations`（finding kind，不是 CU）。
   - 梅花专用正式规则包 1 套：`divination/meihua-yishu`（n=34 / runtime_active=4 / verified=4）。4 条：`MR-01-01` `MR-04-01` `MR-04-02` `MR-04-04`。其余 30 条 inactive（unverified 6 + unscoped 24）。
   - SOURCE_ROUTE 另两包是共用古籍，不是梅花专用包：`divination/zhouyi-zhezhong`（n=31 / active=1 / verified=1 = `ZZR-M001`）、`divination/huangji-jingshi`（n=21 / active=1 / verified=1 = `HR-04-01`）。这两条也挂 `route: meihua`。
   - scope binding（`references/matrices/evidence-scope-bindings-v1.yaml`）`route: meihua` = **12** 条：10 条 `MR-*` + `HR-04-01` + `ZZR-M001`。不是黄金样例。
   - CU：`meihua.*` 签名/工作树都是 `[]`。制品全部 CU 仍是 3 条八字：`month-order` / `ziping` / `tiaohou`。
   - 黄金样例：签名树无 `meihua-v51.yaml`（`golden_fixture_in_signed=False`）。

2. **工作树有没有未进签名的梅花实现？**
   没有未签名算法/CU。`meihua.py` / `meihua.json` / 源表 / `rules.md` / `quote-index.md` 与制品字节相同；`MeihuaProvider` 类文本相同。`providers.py` 整文件哈希不同，是因为工作树多一条八字 `bazi.day-master-root-support-v1`，梅花类未改。`liuyao.py` 只把 `time_based_meihua_casting` 标成 blocked，哈希相同。core-only 10 份：6 份书目笔记、3 份 test/audit、1 份夹具 `meihua-v51.yaml`（38 oracle id：classical_case 10 + trigram_remainder 8 + moving_remainder 6 + method_formula 6 + calendar 8；replay 20）。`unsigned_impl_n=0`，`content_engine_diff=[]`。夹具是测试 oracle，不是未签名实现。

3. **现有 brief / evidence 会不会带上黄金样例？**
   不会。`brief.py` / `evidence_rules.py` 都不读 `references/fixtures`。38 个夹具 id + `meihua-v51` / `classical_case` / `mingli-meihua-fixtures-v51` 在 `brief.py`、`evidence_rules.py`、签名 `meihua.py`、`evidence-rules.jsonl`、scope binding 的命中和都是 0。夹具不在签名树，无法进 `ReadingBrief`。4 条 `MR-*` 以及 SOURCE_ROUTE 上已 verified 的 `HR-04-01` / `ZZR-M001` 可以进证据选择器，那是正式规则不是黄金样例。finding_bindings 不是 CU。

## 三行结论

1. 签名有 `meihua`/`mingli-master.meihua.v1`、12 output、2 finding_bindings、1 专用规则包 `divination/meihua-yishu`（34/4/4）、scope `route:meihua`=12、无 `meihua.*` CU、无黄金夹具。
2. 工作树无未进签名的梅花实现（impl 哈希全同，core-only=10 全是笔记/测试/夹具，unsigned_impl_n=0）。
3. brief/evidence 不会带上黄金样例（夹具 id 命中和=0，brief 不加载 fixtures）。
