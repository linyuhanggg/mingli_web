# 2026-08-19 合盘关系 / hepan / relationship 只读对照（P10-004）

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不把 V52 关系混进 V53。

别名只计 `hepan` / `relationship_signals` / `bazi-relationship` / `ziwei-relationship` / `qizheng-relationship` / `合盘` 及 V52 后处理符号。`source_relationships`、`branch_relations`、三术合参 `convergence`/`合参`、见相 `disagreements` 分开计数，未混入合盘。

V52 `.runtime/v52-relationship-release`（inspector `bef3df25…` / source `da46e7c0…` / 217）只作对照，数字不加入 V53。

## 复跑

```bash
python3 -B /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-hepan-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-hepan-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`
- V52 是另一份制品：`v52_is_other_artifact=True`，`v52_turns_same_as_signed=False`，217 文件。V52 `turns.py` 真值 token 合计 21（`relationship_signals` 11 + 后处理函数名 10），**未计入** V53。

签名树陷阱 token（未计入合盘）：`source_relationships=25` `branch_relations=43` `disagreements=31` `合参=48` `convergence=0` `hecan=0`。evidence-rules 1328 行里合参/见相包命中 `trap_hecan_rows=0`。

## 三问

1. **签名制品里有没有合盘关系 provider / CU / 规则包？**
   没有。14 个 provider 仍是 `bazi` `fengshui` `fortune` `liuren` `liuyao` `luming-nayin` `meihua` `physiognomy` `qimen` `selection` `taiyi` `time-check` `xingming` `ziwei`，无 `hepan` / `relationship` / `bazi-relationship`。无 `RelationshipProvider` / `HepanProvider` 类。CU 仍是 3 条八字：`month-order` / `ziping` / `tiaohou`，合盘 CU=`[]`。evidence-rules 1328 行专用规则包 0（`pack_n=0` `active=0` `verified=0`），合盘提及行 0。路径命中 0。`turns.py` 无 `relationship_signals` / `_append_runtime_relationship`。签名树真值 token 合计 0。catalog / scope `route:hepan|relationship|bazi-relationship` 均为空。签名树无黄金夹具。

2. **工作树源码有没有未进签名的合盘关系实现？**
   没有未签名算法/CU/provider。`turns.py` 与制品字节相同（`turns_hash_same=True`），两边都无后处理。`reading_engine/` 无合盘内容文件（`content_engine_hepan_files=[]` `content_engine_diff=[]`）。extra core providers=0，合盘 CU=`[]`。core-only 内容 7 份、路径命中 0：5 份笔记（含 `bazi-compatibility-reading.md`，签名树没有），2 份 test/audit 只列出 3 个并不存在的 `bazi-relationship-*.md`。真值 token 合计 12 = `合盘` 6 + `bazi-relationship` 6，全在笔记/审计字符串里，无 `relationship_signals`。`unsigned_impl_n=0`。core 夹具目录无 hepan/relationship yaml。

3. **现有 brief / evidence 会不会带上 V52 关系或黄金夹具？**
   不会。`brief.py` / `evidence_rules.py` / `evidence-rules.jsonl` 真值 token 命中 0，45 条 host smoke 黄金 signal id 命中 0，不读 `references/fixtures`，不指向 `v52-relationship-release` / `bef3df25`。两份既有 V53 prepare 的 `relationship_signals` 均为 0。签名/工作树/V52 fixtures 都没有 hepan/relationship 黄金 yaml。45 条黄金 id 只在仓库 host 脚本 `scripts/smoke_local_real_relationship_runtime.py`（6 八字 + 9 紫微 + 30 七政），不进 Runtime brief 选择器。V52 后处理 21 次真值只存在于独立 217 文件制品，未混进 V53。

## 三行结论

1. 签名无合盘 provider/CU/规则包（14 provider 无 hepan，CU=[]，packs=0，turns 无 `relationship_signals`，真值合计 0）；V52 `bef3df25` 是另一份制品。
2. 工作树无未进签名的合盘实现（turns 哈希相同，core-only=7 全是笔记/审计，unsigned_impl_n=0）。
3. brief/evidence 不会带上 V52 关系或黄金夹具（真值/45 条 golden id 命中和=0，prepare 无 `relationship_signals`，不加载 fixtures、不读 V52 路径）。
