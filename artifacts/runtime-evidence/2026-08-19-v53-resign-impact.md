# P10-001 重签影响说明（2026-08-19）

只写说明。**未执行重签，未改 backend config / DESIGN / OpenAPI / frontend / catalog。** P10-001 仍为 `IN_PROGRESS`。

## 现行可接纳身份（不要改）

| 项 | 值 |
|---|---|
| 路径 | `/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release` |
| inspector `manifest_sha256` | `c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b` |
| `source_commit` | `663543e65ae037843b03dca1dec9486293affc9d` |
| describe digest（门禁） | `3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc` |
| capability shape | `fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042` |

两个哈希不要混：`c451de5e` 是 inspector；`3403992c` 是 describe 门禁。`fb9da7fa` 是 capability shape。

## 四个 Claim Unit

签名制品里有三个（已在签名 `scripts/reading_engine/providers.py`，frozen 哈希覆盖该文件；测试独立复验 live `fact_panel.findings` 已跑出 ziping）。某次 prepare brief 是否出现 ziping 随盘：

- `bazi.month-order-state-v1`
- `bazi.ziping-pattern-entry-v1`
- `bazi.tiaohou-priority-v1`

仅源码、不在制品：

- `bazi.day-master-root-support-v1`

记实（2026-08-19 三盘 one-shot，store 仍在）：

| 盘 | ziping | day-master-root | DR-01-01 |
|---|---|---|---|
| 1994-04-30 datetime（`/tmp/mingli-oneshot-v53-time-check-20260819`） | 有 | 无 | `source_conditioned_patterns` 命中，**`evidence_ref` 字段缺失（=null）**；公共 evidence 数组无此条 |
| 乙酉/辛巳/丙午/癸巳 四柱（`.runtime/oneshot-20260819-claim-unit/`） | **无** | 无 | pattern 同样无 `evidence_ref`；公共 evidence 数组有 `evidence:bazi/bazi/ditiansui-chanwei#DR-01-01` |
| 1992-08-17 datetime（`/tmp/mingli-oneshot-v53-fixture2-20260819/out/`） | 有 | 无 | 同 1994：pattern 命中且 `evidence_ref` 缺失；公共 evidence 数组无此条 |

`DR-01-01 evidence_ref=null` 已复现。ziping 随盘（datetime 有、乙酉四柱无）≠「不在制品」。第 4 个 unit 三盘都没有。

## 若重签会发生什么（未授权，不要执行）

- 新制品 `manifest_sha256` **必然 ≠** `c451de5e…993c4b`
- describe digest **很可能 ≠** `3403992c…facc`；capability shape **可能变**。重算后再改门禁，**不要猜新哈希**
- 旧树 `.runtime/v53-time-check-release` 是回滚点：新制品必须放**新目录**；`scripts/verify_frozen_runtime_release.py` + describe 门禁过了、PM 接纳后才切
- `v53-time-check` 仅本地/测试，production 禁止（`backend/app/config.py` 已写死）
- **不要发明重签命令。** 仓库里已找到的 builder：`core/mingli-master/scripts/release_deploy.py`（CHECKLIST 2026-08-18 阶段 G 曾用此路径本地重签）。**PM 未授权运行。** 相邻脚本 `core/mingli-master/scripts/mingli_pack.py`、`provision_runtime.py` 同样未授权。本说明不给出 argv。

## 后端 config 哪些地方要改（只列，不要改文件）

未接纳前不要改。生产默认仍是 `/opt/mingli-master`，与本机 Lexar 测试树分开。

### 环境变量（live Worker / smoke；`Settings` 前缀 `MINGLI_`）

```
MINGLI_RUNTIME_ADAPTER=one-shot
MINGLI_RUNTIME_RELEASE_PROFILE=v53-time-check
MINGLI_RUNTIME_LAUNCHER_PATH=/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release/scripts/run_reading_transaction.sh
MINGLI_RUNTIME_PYTHON_PATH=/Users/yuhanglin/.local/share/mingli-master/venv/bin/python
MINGLI_RUNTIME_RELEASE_ROOT=/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release
MINGLI_RUNTIME_STATE_ROOT=<writable private dir>
MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST=3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc
MINGLI_RUNTIME_EXPECTED_CAPABILITY_SHAPE_SHA256=fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042
```

接纳新树后：`LAUNCHER_PATH` / `RELEASE_ROOT` 改新目录；两个 expected digest 改**重算值**（现填的是现行身份）。

### 文件:键（已 grep）

| 路径 | 键 / 符号 |
|---|---|
| `backend/app/config.py` | `RuntimeReleaseProfile` 含 `"v53-time-check"`；`_V53_TIME_CHECK_DESCRIBE_MANIFEST_DIGEST`；`_RUNTIME_RELEASE_PROFILES["v53-time-check"]` 的 `manifest_digest` / `capability_shape_sha256` / `release_manifest_sha256` / `source_commit`；Settings：`runtime_adapter`、`runtime_release_profile`、`runtime_launcher_path`、`runtime_python_path`、`runtime_release_root`、`runtime_state_root`、`runtime_expected_manifest_digest`、`runtime_expected_capability_shape_sha256`；生产禁 `v53-time-check` |
| `backend/app/adapters/runtime.py` | `OneShotMingliRuntimeAdapter`；`RuntimeStartupGate.expected_manifest_digest` / `expected_capability_shape_sha256`；`runtime_capability_shape_sha256()`；装配处读上述 Settings |
| `backend/app/readings/capability_policy.py` | `"v53-time-check": "v53-time-check-release"` 目录映射；默认 `release_profile="v53-time-check"` |
| `backend/tests/test_config.py` | `runtime_expected_manifest_digest` / `runtime_expected_capability_shape_sha256` |
| `backend/tests/test_runtime_startup_gate.py` | 同上 + 缺 digest / 错 shape fail-closed |
| `backend/tests/test_time_check_postgres_vertical.py` | `_RUNTIME_RELEASE_PROFILES["v53-time-check"]`；`runtime_release_profile` / 两个 expected |
| `backend/tests/test_bazi_deep_vertical.py` | 同上 |
| `backend/tests/test_runtime_process_adapter.py` | `MINGLI_RUNTIME_RELEASE_PROFILE=="v53-time-check"` skip 门 |
| `backend/tests/test_runtime_worker_document_matrix.py` | `MINGLI_RUNTIME_RELEASE_PROFILE`；`runtime_release="mingli-runtime-v53-time-check"` |
| `backend/tests/mingli_paths.py` | `.runtime/v53-time-check-release` |
| `backend/tests/test_capability_policy.py` | `.runtime/v53-time-check-release` |
| `scripts/smoke_local_real_runtime.py` | `MINGLI_RUNTIME_ADAPTER` / `LAUNCHER_PATH` / `PYTHON_PATH` / `RELEASE_ROOT` / `STATE_ROOT` / `EXPECTED_MANIFEST_DIGEST` / `EXPECTED_CAPABILITY_SHAPE_SHA256` |

## 源码侧已空

catalog `pendingModules` 只剩「旺衰贡献」「格局、喜忌与病药依据」= 四个 Claim Unit。没有可写的、非 claim-unit、非用神/吉凶/身强身弱/格局成败的事实层切片。

下一诚实工作若授权：resign 让第 4 个 unit 进制品；或把 `DR-01-01` 选进 public evidence（仍要 resign 才进制品）。格局 / 喜忌 / 用神 / 病药禁止。

三盘复跑清单：`artifacts/runtime-evidence/2026-08-19-oneshot-replay.md`。

## 本说明未执行重签，未改 config。P10-001 仍 IN_PROGRESS。

## V52 relationship 是另一份制品（不要混进当前准入）

本机另有 `.runtime/v52-relationship-release`，inspector `manifest_sha256=bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50`，`source_commit=da46e7c0d565fe781e40a115acbb2874c400a195`。这是 V52 relationship 树，**不是**当前可接纳的 V53 `c451de5e`。

项目经理裁定：不要在 `c451de5e` 上现写关系层；没有的合同就没有；不编 `relationship_signals`；不重签。合盘关系另拍。V52 不能当作 V53 准入，也不能把 V52 信号投影进 `/bazi/hepan`。

V53 签名树对 `relationship_signals` / `_append_runtime_relationship` 为零命中；core 源码同样没有。只有 V52 `turns.py` 在双主体 + dimension=relationship 时追加该 fact。后端 `relationship_engine.py` 只拷贝 Runtime 已有 fact，不重算合冲。

## DR-01-01 `evidence_ref=null` 诊断（2026-08-19，未重签）

裁决：**mixed**。洞在签名树的 public EvidenceBundle 选择器（BM25 零分丢包），不是 backend 投影丢 join。规则记录本身完整。未改签名树，未重签。

### 1. 签名制品里这条规则是完整且 `runtime_active`

`references/index/evidence-rules.jsonl` 第一条（`rule_id=bazi/ditiansui-chanwei#DR-01-01`）：

- `runtime_active`: `true`
- `classical_binding_status`: `verified`
- `classical_sources[0]`: `path=references/fulltext/bazi/ditiansui-chanwei/fulltext.md`，`anchor=fulltext.md#L11`，`verbatim_quote=干为天元，支为地元，支中所藏为人元。`
- `evidence_role`: `methodology_rule`
- 谓词：`/four_pillars` nonempty、`/hidden_stems` nonempty

同条也在 `references/matrices/evidence-scope-bindings-v1.yaml`。`scripts/reading_engine/providers.py` `BaziProvider.SOURCE_ROUTE.packs` 含 `bazi/ditiansui-chanwei`。`rules.md` 标题「DR-01-01 三元一统」，`verification_status=pending_verification`（规则稿状态；索引 classical binding 已是 verified）。

### 2. 签名 prepare 从不把 `evidence_ref` 写进 pattern

三盘 `brief.facts[*].value` 里 `source_conditioned_patterns` **都没有** `evidence_ref` 字段（乙酉 overview 也没有）。`evidence_ref` 只出现在 `brief.evidence[]`。这是制品合同，不是某一盘写丢。

Backend 回填点（只读，未改）：`backend/app/charts/projectors.py`

- `project_bazi_view_model` 把 `brief.evidence` 传给 `_bazi_core_facts`
- `_bazi_source_conditioned_patterns` 调 `_bazi_evidence_refs`：只收 `verification_status=verified_exact` 且 `ref == evidence:bazi/{rule_id}` 的项，做成 `{rule_id: evidence_ref}`
- `pattern.model_copy(update={"evidence_ref": evidence_refs.get(pattern.rule_id)})` —— 不在 `brief.evidence[]` 就是 `null`

`backend/tests/test_runtime_public_core_process.py` L95–115 已把 1994 career 合成盘锁成：6 条 pattern，有 ref 的是 `QR-02-01 QTB-M01 R-01-02 R-02-04 ZPR-01`，**仅 `DR-01-01` 为 `None`**。

### 3. 三盘 prepare 实测字段

**1994** `/tmp/mingli-oneshot-v53-time-check-20260819/out/prepare.stdout.json`  
query=`验证八字核心盘面`，`request_view.dimension_ids=["career"]`，horizon=`life`

- `brief.facts[23].ref` = `fact:profile-version:public-core-synthetic/calculated/bazi/source_conditioned_patterns`
- `value[0].rule_id` = `bazi/ditiansui-chanwei#DR-01-01`，`local_rule_id=DR-01-01`，`status=predicate_matched_not_verdict`，**无 `evidence_ref` 键**
- `brief.evidence` 长度 5，rule_id / evidence_ref / verification_status：
  - `bazi/sanming-tonghui#R-01-02` / `evidence:bazi/bazi/sanming-tonghui#R-01-02` / `verified_exact`
  - `bazi/sanming-tonghui#R-02-04` / `evidence:bazi/bazi/sanming-tonghui#R-02-04` / `verified_exact`
  - `bazi/ziping-zhenquan#ZPR-01` / `evidence:bazi/bazi/ziping-zhenquan#ZPR-01` / `verified_exact`
  - `bazi/qiongtong-baojian#QR-02-01` / `evidence:bazi/bazi/qiongtong-baojian#QR-02-01` / `verified_exact`
  - `bazi/qiongtong-baojian#QTB-M01` / `evidence:bazi/bazi/qiongtong-baojian#QTB-M01` / `verified_exact`
- **没有** `bazi/ditiansui-chanwei#DR-01-01`

**1992** `/tmp/mingli-oneshot-v53-fixture2-20260819/out/prepare.stdout.json`  
同 query / career / life。`value[0]` 同样是 DR-01-01，`status=predicate_matched_not_verdict`，无 `evidence_ref`。`brief.evidence` 5 条（`QR-01-07` 替换 `QR-02-01`，其余同构），**仍无 DR-01-01**。

**乙酉** `.runtime/oneshot-20260819-claim-unit/prepare-out.json` 与 `evidence-array.json`  
query=`请排出本命四柱。`，`dimension_ids=["overview"]`

- pattern 仍无 `evidence_ref` 键，`status=predicate_matched_not_verdict`
- `brief.evidence[3]`（array `[3]`）：
  - `rule_id=bazi/ditiansui-chanwei#DR-01-01`
  - `evidence_ref=evidence:bazi/bazi/ditiansui-chanwei#DR-01-01`
  - `verification_status=verified_exact`
  - `locator=fulltext.md#L11`
  - `supports_fact_refs` = four_pillars / hidden_stems / interpretive_candidates / ten_gods

Career 的 claim_scope **已经包含** `four_pillars` 与 `hidden_stems` 公共 fact。不是缺 fact，是没选进 evidence 数组。

### 4. 选择器机制（签名树）

`scripts/reading_evidence_bundle.py`：

- `_eligible_rules`：pack 在计划内 + `match_rule` 谓词通过即入候选。DR-01-01 在三盘都 match（所以 pattern 在）。
- `_select_ranked` → `_rank_rules`：对每个 pack 做 BM25，`MAX_RULES_PER_PACK=2`。
- `search_bm25.bm25`：**`score > 0` 才返回**；零分文档直接丢掉。
- `_rule_text` = `source_title + chapter + topics + quote`。DR-01-01 文本是「滴天髓阐微 / 三元一统 / 干为天元…论命三元一统…旁参支藏」。

用签名 `search_bm25.tokenize` 实测重叠：

| 查询 | 与 DR-01-01 文本的 CJK 交集 | 该 pack BM25 |
|---|---|---|
| `验证八字核心盘面` + `career` | **空** | 命中 0 → 包不进 bundle |
| `请排出本命四柱。` + `overview` | `命`（来自「论命」） | score≈0.29 → 选进 |

对照：ZPR-01 原文含「八字」，career 能进；QTB-M01 topic 含「四柱盘」，「盘」能进。DR-01-01 没有「八字/盘面/四柱」字面，career 查询打不中。`ditiansui-chanwei` 包当时只有这一条 eligible，零分 = 整包空。

随后 `providers.py` `_public_evidence` 只投影 bundle 里已有、且 `exact_citations` 完整的节点。DR-01-01 的 citations 条件（`runtime_active` + `classical_binding_status=verified`）本身能过——乙酉已证明。career 是根本没进 bundle。

### 5. 不是 FastAPI / projector 消费洞

1994/1992 的 signed prepare **已经**没有 DR-01-01 的 `brief.evidence[]` 项。Backend 无法 join 出 ref，也不应当补造。乙酉 overview 的 prepare **已经**带 `verified_exact` evidence，同一 projector 应按 `rule_id` 回填。不要改 FastAPI 填 career 的 null。

若以后要 career 也带这条引用：改签名选择器（例如 matched+verified methodology 不因 BM25 零分丢包，或给 DR-01-01 稳定 semantic terms）。那是制品变更，必须新目录重签。本次不改、不重签。

