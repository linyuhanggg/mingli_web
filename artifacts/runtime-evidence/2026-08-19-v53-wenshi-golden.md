# 2026-08-19 问事 / wenshi / canwen / 参问 只读对照

对照：签名 V53 `.runtime/v53-time-check-release`（inspector `c451de5e…` / source `663543e…` / 220）vs 工作树 `core/mingli-master`。
不改合同、不覆盖 `.runtime`、不 resign、不发明 CU、不把 V52 关系混进 V53。

别名只计 `wenshi` / `canwen` / `问事合参` / `参问` 及 `WenshiProvider` / `CanwenProvider` / `wenshi_one_question` / `compile_*_prepare`。裸 `问事` 出现在 `所问事项` / `问事时间` / `问事分类` 等词里，记为通用占辞，**不计入**问事产品。`合盘`/`hepan`、`合参`/`hecan`/`convergence`、`寻时`/`time-check`、单术 `liuyao`/`qimen`/`liuren` 分开计数，未混入问事。

V52 `.runtime/v52-relationship-release`（inspector `bef3df25…` / source `da46e7c0…` / 217）只作对照，问事真值 0，数字不加入 V53。

## 复跑

```bash
python3 -B /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-wenshi-golden.py
```

stdout：`artifacts/runtime-evidence/2026-08-19-v53-wenshi-golden.stdout.txt`

## 准入

- `pin_ok=True`
- inspector=`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- source_commit=`663543e65ae037843b03dca1dec9486293affc9d`
- manifest_files=220，walk_files=220
- `v52_mix_in_v53_turns=False`
- V52 是另一份制品：`v52_is_other_artifact=True`，217 文件。V52 问事真值合计 0，**未计入** V53。

签名树陷阱 token（未计入问事）：`合参=48` `寻时=2` `time-check=25` `time_check=12` `合盘=0` `hepan=0` `hecan=0` `convergence=0` `relationship_signals=0`。evidence-rules 1328 行里 `合参` 全文行 14、pack/path 合参 0、合盘 0、寻时 0。

## 三问

1. **签名制品里有没有问事 provider / CU / 规则包？**
   没有。14 个 provider 仍是 `bazi` `fengshui` `fortune` `liuren` `liuyao` `luming-nayin` `meihua` `physiognomy` `qimen` `selection` `taiyi` `time-check` `xingming` `ziwei`，无 `wenshi` / `canwen`。无 `WenshiProvider` / `CanwenProvider`。CU 仍是 3 条八字，问事 CU=`[]`。evidence-rules 1328 行专用规则包 0（`pack_n=0` `active=0` `verified=0`），问事提及行 0。路径命中 0。catalog / scope `route:wenshi|canwen` 均为空。签名树无黄金夹具。真值 token 合计 0。裸 `问事` raw=2、residual=0，全在 `san-shi/liuren-miben/rules.md` 的「所问事项」，不是问事产品。单术 `liuren`/`liuyao`/`qimen` 是既有 Provider，未当作问事产品计入。

2. **工作树源码有没有未进签名的问事实现？**
   没有未签名算法/CU/provider。真值 token 合计 0，路径命中 0，问事 CU=`[]`，`reading_engine/` 无问事内容文件。`providers.py` 字节不同（`providers_hash_same=False`），但两边问事真值都是 0；core 多出来的 CU 只有 `bazi.day-master-root-support-v1`，不是问事。`turns.py` / `brief.py` / `evidence_rules.py` / `evidence-rules.jsonl` 与制品哈希相同。core-only 含裸 `问事` 的 7 份全是笔记/测试（5 笔记 + 2 回归/prompt），residual=0，`unsigned_impl_n=0`。core 夹具目录无 wenshi/canwen yaml。问事合参投影在 host `backend/app/charts/projectors.py`，不在签名树、也不在 `core/mingli-master` 实现层。

3. **现有 brief / evidence 会不会带上黄金夹具？**
   不会。`brief.py` / `evidence_rules.py` / `evidence-rules.jsonl` 真值与 12 条 host 黄金 id 命中和=0，不读 `references/fixtures`。两份既有 V53 prepare 的 wenshi/canwen/黄金 id 均为 0。签名/工作树/V52 fixtures 都没有 wenshi/canwen 黄金 yaml。12 条黄金 id 只在仓库 host 测试 `backend/tests/test_runtime_process_adapter.py` / `test_request_compiler.py`（`wenshi:golden-rule-evidence`、`wenshi:synthetic-runtime`、`canwen-synthetic` 等），不进 Runtime brief 选择器。V52 问事真值 0，未混进 V53。

## 三行结论

1. 签名无问事 provider/CU/规则包（14 provider 无 wenshi/canwen，CU=[]，packs=0，真值合计 0；裸问事 residual=0）。
2. 工作树无未进签名的问事实现（真值 0，core-only 7 份全是笔记/测试，unsigned_impl_n=0）。
3. brief/evidence 不会带上黄金夹具（真值/12 条 golden id 命中和=0，prepare 无 wenshi，不加载 fixtures）。
