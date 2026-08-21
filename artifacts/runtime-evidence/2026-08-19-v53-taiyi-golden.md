# 2026-08-19 太乙 / taiyi 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不混 V52。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-taiyi-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-taiyi-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`

六壬十二神「太乙」(巳) 未计入太乙神数：liuren 路径「太乙」字面=1，liuren pack 行=61，全部排除。

## 三问

1. **签名制品里太乙有哪些正式规则包 / 黄金样例 / CU / provider / output？**
   - Provider：`taiyi` / `mingli-master.taiyi.v1`，entrypoint `reading_engine.providers:TaiyiProvider`，adapter `5.2.0`，evidence_profile `taiyi`。
   - Output 12：`calendar` `epoch` `cycle` `board` `taiyi_position` `wenchang_tianmu` `shiji_kemu` `host_guest_counts` `four_generals` `long_cycle_deities` `board_predicates` `scope_contract`。extension 1：`calculated_annual_board_scope`。
   - finding_bindings=0。
   - SOURCE_ROUTE packs 1：`san-shi/taiyi-shenshu`。正式规则包只有这一套（n=26 / runtime_active=15 / verified=15）。
   - runtime_active 且 verified 的 15 条：`TR-01` `TR-03` `TR-04` `TR-05` `TR-10` + `TY-P01`…`TY-P10`。其余 11 条 TR-02/06/07/08/09/11/12/13/14/15/16 为 `inactive_unverified`。
   - CU：`taiyi.*` 签名/工作树都是 `[]`。制品全部 CU 仍是 3 条八字：`month-order` / `ziping` / `tiaohou`。`SOURCE_DEPENDENCIES` 6 个 `taiyi.calendar.*` 等是源表依赖 id，不是 CU。
   - 黄金样例：签名树无 `taiyi-v51.yaml` / `kintaiyi-taiyi-v51.yaml`（`golden_in_signed=False,False`）。

2. **工作树有没有未进签名的太乙实现？**
   没有未签名算法/CU。`taiyi.py` / `taiyi.json` / 源表 / `rules.md` / `quote-index.md` 与制品字节相同；`TaiyiProvider` 类文本相同。core-only 12 份：5 份书目笔记、3 份 test、1 份 audit、1 份夹具生成器、2 份夹具（`taiyi-v51.yaml` 44 个 id：epoch 4 + kintaiyi 对照 30 + 历法边界 10；`kintaiyi-taiyi-v51.yaml` raw 72）。`unsigned_impl_n=0`。夹具是测试 oracle，不是未签名实现。

3. **现有 brief / evidence 会不会带上黄金样例？**
   不会。`brief.py` 太乙 token hits=0。116 个夹具 id + `taiyi-v51` / `kintaiyi-taiyi-v51` / `mingli-taiyi-fixtures-v1` / `kintaiyi-taiyi-raw-v1` / `classical_case` 在 `brief.py`、签名 `taiyi.py`、`evidence-rules.jsonl` 的命中和都是 0。夹具不在签名树，无法进 `ReadingBrief`。15 条 TR-*/TY-P* 可以进证据选择器，那是正式规则不是黄金样例。

## 三行结论

1. 签名有 `taiyi`/`mingli-master.taiyi.v1`、12 output+1 extension、0 finding_bindings、1 规则包 `san-shi/taiyi-shenshu`（26/15/15）、无 `taiyi.*` CU、无黄金夹具。
2. 工作树无未进签名的太乙实现（impl 哈希全同，core-only=12 全是笔记/测试/夹具，unsigned_impl_n=0）。
3. brief/evidence 不会带上黄金样例（夹具 id 命中和=0）。
