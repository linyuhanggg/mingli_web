# 命理大师 V5.1 — Provider 可维护性重构一期：最终验证记录

日期：2026-08-07。分支：`qoder/mingli-v51-provider-maintainability-20260807`。
环境契约：`unset MINGLI_STORE_ROOT`；`PYTHONDONTWRITEBYTECODE=1`；
`MINGLI_RESEARCH_ROOT=~/.codex/skills/mingli-master`（只读）；
`MINGLI_PYTHON` 指向 mktemp 隔离的 runtime 副本（`/tmp/mingli-runtime.0bnusd`，
pyc 漂移隔离，不修改安装目录）。未安装任何依赖。

## 1. 红→绿过程

- 提交 2（939196f）：compat characterization 首次运行 2 例失败（我对
  fact_layer_status 与 trace 变异的假设错误），采集真实行为后用冻结字典
  逐字固定 → 9 tests 绿。
- 提交 3（483fdb2）：seam 测试先行，首跑 14 红 → 实现
  `scripts/fact_contracts/` 与 facade 接线后 23 绿。
- 提交 5（89bab61）：locality/deletion 追加后首跑 1 失败 2 错误（既有
  system 上契约与遗留校验器并行）→ 引入 `replaces_legacy_validation`
  接管语义 + 契约自持 required 集合后 31 绿。

## 2. 聚焦与回归实测

| 套件 | 结果 | 耗时 |
| --- | --- | --- |
| `test_v51_fact_contracts` + `test_v51_fact_validation_compat` | 31 tests OK | 1.443s |
| 八字/审计/catalog/evidence 8 模块聚焦（含 bazi_fact_adapter、model_replay、catalog_driven_registry、algorithm_source_dependencies、evidence_source_integrity、bazi_provider_audit） | 177 tests OK | 37.045s |
| `test_v51_release_surface` + `test_release_deploy` | 25 tests OK | 5.609s |
| 完整规范 runner `run_test_suite.py -j 3 --research-root …` | **125 targets / 92 modules / 1546 tests / 0 failed** | 1037.66s |
| answer exporter `--check` | 9 production-exported answer cases OK | — |
| `audit_provider_completeness.py --write` | **13/13 ready，findings=[]** | — |
| `generate_classical_evidence_bindings.py` 重跑 | 零漂移（records=571 / verified=185 / inactive=386，git diff 为空） | — |
| `audit_algorithm_sources.py` | 通过 | — |
| `git diff --check` / `git status --short --branch` | 干净 | — |

全量测试数比上一轮基线（1515）增加 31，恰为本轮新增测试数（22 契约 +
9 兼容）。全量耗时 1037.66s 超出"十分钟"目标，属本机当前负载下的实测；
未删除、未跳过任何测试，未做任何为提速的裁剪（见风险记录）。

## 3. 静态确认（未触碰清单）

`git diff --name-only main..HEAD` 共 20 个文件（含 9 个 checkpoint 用户资产
与本轮 11 个重构/文档文件），其中 **没有任何 Gateway 文件、SKILL.md、complete
事务逻辑或生产部署脚本**。describe/prepare/complete 与 Accepted.public_copy
语义由 1546 项全量测试与 replay/exporter 检查背书。未 push；分支仅存在于
本地。

## 4. 验收对照（任务书第八节）

- describe/prepare/complete 兼容：全量 0 失败 + release surface 测试通过。
- validate_payload 调用方无需修改：compat characterization 逐字段冻结通过。
- 八字专属校验不再堆在 adapter_validate.py：3047→2574 行，八字块整体位于
  `scripts/fact_contracts/bazi.py`；deletion test 证明删掉 manifest 声明即
  删掉全部 bazi_ 行为。
- 新增 FactContract 不改通用 dispatch：locality 测试（新系统与既有系统）通过。
- 新增算法/古籍 locality：`AlgorithmAndClassicalSourceLocalityTests` 通过。
- 通用层无新增命理术语/关键词/正则：manifest 禁键回归测试 + 13 个生产
  manifest 递归扫描通过。
- 无第二层回答拦截：Accepted 后无二次拦截的既有测试在全量中继续通过。
- 任意失败返回明确结果：registry 全部失败路径 → 显式 finding，无空回复。
- 13 Provider 全部可用：completeness 13/13 ready。
- Gateway、8642/8645、部署、依赖安装、push：全部未触碰。

## 5. 提交列表（时间序，均可独立回滚）

1. `b5b2863` fix: harden partial bazi fact boundaries（checkpoint，仅 9 个用户资产）
2. `77002da` docs: add provider maintainability refactor plan
3. `939196f` test: characterize fact validation compatibility
4. `483fdb2` refactor: add internal fact contract seam
5. `961ca9c` refactor: move bazi validation behind fact contract
6. `89bab61` test: add extension locality and deletion coverage
7. `d42bdde` docs: document adding algorithms and classical sources
8. `e4a83e5` chore: refresh generated matrices and replay artifacts
9. `3aa1c7f` fix: include fact contracts package in the runtime release closure
10. 本提交 docs: record final verification

偏离与兜底记录见计划文档第 11 节。

## 6. 审查修复轮记录（2026-08-07，合并后审查）

三位独立审查员（完整性/正确性/影响面）审查通过、无 Critical；合并后发现
的三个问题已全部修复，均为小提交：

| 问题 | 修复 | 提交 |
| --- | --- | --- |
| 必修 1（Major）：validate_payload 永不抛异常契约被击穿——fact_contracts.registry import 在守卫之外（混合版本安装 ImportError 逃逸）；catalog._read_json 未覆盖 UnicodeDecodeError/OSError（非 UTF-8 文件、catalog-v1.json 为目录） | _read_json 将 OSError/UnicodeDecodeError 转 CatalogError；_load_fact_contract 把 import 移入守卫并对任意异常失败封闭；新增 FactContractFailClosedTests 三场景（非 UTF-8、目录、import 失败）红→绿 | `cfbc7b3` fix: keep fact contract loading fail-closed under io corruption |
| 必修 2（Minor）：registry 先执行模块代码后做 Skill 根检查 | 改为 importlib.util.find_spec 解析 origin 并通过 Skill 根校验后才 import_module，拒绝发生在任何候选代码执行之前；残余说明（dotted 名的父包导入）写入代码注释与提交说明 | `d858915` fix: verify fact contract trust before module execution |
| 必修 2 返工（P1，2026-08-07 独立验收返工）：独立对抗复测证明 d858915 的口径对 dotted 名不成立——`importlib.util.find_spec` 解析 `outsidepkg.child` 时先导入并执行 Skill 根外的父包 `__init__.py`，之后才报 escapes the Skill root（parent_executed_before_rejection=True） | 信任校验改为零导入：顶层名用 `PathFinder.find_spec` 纯路径扫描定位，dotted 余部在受信包目录下做纯文件系统遍历（中间层必须是包，末层可为模块），全链符号链接解析后确认位于 Skill 根内才 import_module；新增对抗测试：根外父包 `__init__.py` 写 marker，断言拒绝前 marker 未写入且无残留 sys.modules 项（红→绿）；生产 dotted 入口 `fact_contracts.bazi:BaziFactContract` 与 `json:JSONDecoder` 拒绝用例行为不变。至此"拒绝发生在任何候选代码执行之前"对顶层与 dotted 入口均由实测背书 | `ff6fa2a` test: prove dotted fact-contract entrypoints execute outside parents before rejection；`13200ab` fix: verify the full dotted fact-contract chain before executing anything |
| 必修 3（Minor）：5 个拒绝路径测试 assertRaises(Exception) 过宽 | 收紧为 assertRaises(FactContractError) | `b3966d0` test: tighten registry rejections and add algorithm locality proof |

建议项处理：

1. 算法类目正向 locality 证明：新增
   `test_new_algorithm_declaration_is_found_and_verified_by_the_audit`
   （category=`calendar_formula_and_epoch`，生产真实类目），与古籍类目并列
   （随 `b3966d0`）。
2. 计划文档 §7 deletion test 描述改为与实现一致的"临时 catalog 目录 +
   catalog_root 注入"（随本提交）。
3. registry catalog 解析加模块级缓存（随 `d858915`）：catalog 是只读声明，
   失败永不缓存，所有测试使用唯一临时目录，无状态污染风险。

本轮复验实测（环境契约同前，新 runtime 副本 `/tmp/mingli-runtime.Bu1ddM`）：

- 新增失败封闭测试红→绿：先 3 errors → 修复后 34 tests OK（1.37s）
- 聚焦 10 模块（八字/replay/catalog/算法来源/证据完整性/八字审计/契约/兼容/release）：**206 tests OK**（41.98s）
- 完整规范 runner：**125 targets / 92 modules / 1550 tests / 0 failed**（1083.38s；较上轮 +4 恰为本轮新增测试）
- provider completeness `--write`：**13/13 ready，findings=[]**（指纹刷新随 `ffaf088`）
- answer exporter `--check`：9 cases OK
- `git diff --check` / `git status`：干净；Gateway/SKILL.md/complete/部署仍未触碰；未 push

偏离（2026-08-07 验收返工更正）：上段所称"find_spec 对 dotted 名可能先导入
父包的限制"已被独立对抗复测证实为真实缺陷（P1），不再是可接受的残余限制；
`13200ab` 起信任校验全程零导入，该偏离已消除，"拒绝发生在任何候选代码执行
之前"口径由 `test_dotted_entrypoint_parent_outside_root_never_executes` 实测支撑。

## 7. 基线口径复测（独立审计，2026-08-07）

本文档第 2、6 节记录的全量耗时（1037.66s / 1083.38s）均采用自选的
`-j 3` 降并行口径，"超出十分钟目标"的表述仅适用于该口径，会误导后续
验收，特此更正。

独立审计按基线口径复测全量：README 规范命令
`scripts/run_test_suite.py --research-root ~/.codex/skills/mingli-master`
（不带 `-j`，默认并行度 10 workers），实测
**125 targets / 92 modules / 1550 tests / 0 failed，elapsed 456.28s**——
低于十分钟目标，且快于 512.09s 的上一轮基线。

今后全量测试验收以 README 规范命令（默认并行度）为唯一口径；`-j 3`
等降并行运行仅作为受限环境下的参考记录保留。

## 8. 第二次独立验收返工记录（2026-08-07，FAIL 返工）

第二次独立验收判定 FAIL（1 P1 + 4 P2 + 1 P3）。返工按测试先行纪律逐项修复，
提交链从 `c0dc361` 起：

| 缺陷 | 修复 | 提交（红→绿） |
| --- | --- | --- |
| P1 Registry 拒绝前执行 Skill 根外父包 | 零导入信任校验（见 §6 必修 2 返工行） | `ff6fa2a` → `13200ab`（文档 `707de65`） |
| P2 FactContract 返回契约与异常归一（dict 返回击穿 facade、构造 RuntimeError 泄漏、空 contract_id 被接受） | 构造异常全部归一为 FactContractError；contract_id 非空校验；`_normalize_contract_findings` 逐项验证 hook 返回 | `b18c47e`/`934a39b` → `ed7926c` |
| P2 八字知识残留通用 facade（qimen payload 泄漏 conflicting_bazi_facts；required-output 双份维护；deletion test 前缀漏检） | 冲突状态检测与八字 required-output 权威全部移入 BaziFactContract；deletion 断言改为 code 含 bazi 子串 | `7d8d3ae` → `f53c0e2` |
| P2 deletion test 验收语义（仅断言字符串消失） | registry 新增 `is_declared()`；facade 对 declared-but-contractless 系统发 `fact_contract_unavailable` 结构化 finding，真未知体系保持冻结的 `unknown_system` | `a2c9e46` → `60be1f3`（指纹 `536b99e`） |
| P2 古籍 locality 仅证第一环 | 全链路演练 `ClassicalExtensionFullChainLocalityTests`：临时树合成新书，走完 source pack → binding → scope → 生成器 → index → 运行时匹配；pin 拒绝未审计新书（零命中保持零命中），全程零 Python 改动 | `c288c7a` |
| P3 提交混改 | 本轮严格执行测试/生产/文档/chore 分离提交 | 全链 |

行为兼容证据：compat characterization（9 tests）、bazi adapter（50 tests）、
fact contracts + compat 聚焦（47 tests）、`test_v51_*` 全集（1120 tests）与
completeness 快照（13/13 ready）在修复后全部绿。环境教训：临时 runtime 副本
混入 `__pycache__` pyc 会触发 "unchecked runtime bytecode is forbidden" 的
runtime probe 假失败，须先清除 pyc 再跑聚焦回归。

## 9. 第三次独立验收返工与最终回执（2026-08-08）

第三次独立验收在 1571 tests / 0 failed 的绿灯之外发现 1 个 P1、1 个 P2、
1 个 P3，并补充指出正式 runtime venv 的 pyc 环境告警。本轮按测试先行完成：

| 缺陷 | 修复 | 回归证据 |
| --- | --- | --- |
| P1 required-key hook 可用字符串绕过必填检查，或以不可哈希项让 facade 抛 `TypeError` | 新增 `_normalize_contract_required_keys`，只接受精确内建 tuple，且每个元素必须是精确内建的非空 str；非法返回统一生成 `fact_contract_invalid_return`，不迭代、不回显、不抛异常 | 字符串 output、字符串 calendar、`[{}]`、恶意 tuple/str 子类五个 hostile 回归 |
| P2 公开签名新增 `catalog_root`，冲突 finding 顺序晚于 missing findings | 公开 `validate_payload` 恢复原签名；catalog 注入下沉到私有 `_validate_payload`；payload conflict hook 恢复到通用 envelope 校验之前 | `inspect.signature` 与 `codes[0] == conflicting_bazi_facts` 冻结 |
| P3 最终回执停在 1550 tests | 本节记录第三次返工与最终规范 runner 实测；README 同步当前测试数 | 文档与 runner 汇总对齐 |
| 正式 venv 内旧 pyc 触发 runtime probe 假失败 | 直接执行 provider audit 时在第三方导入前禁写 bytecode；README 两条单独审计命令补 `-B`；清理正式 venv 的 24 个旧 pyc | 干净临时 venv 对照：无 `-B` 旧实现写 23 个，修复后写 0 个；正式 venv 清理后 `provision_runtime --check` 通过，连续审计与全量后仍为 0 |

首轮 TDD 红灯：新增 6 个测试并强化 1 个既有断言，共产生 8 个预期断言失败；
最小修复后 7 个回归点全绿。终审再补 2 个恶意内建类型子类回归，均先红后绿。

最终独立验收（正式 venv，未使用临时副本）：

- 聚焦回归：FactContract 52 + 兼容性 10 + runtime 24 = **86 tests / 0 failed**。
- README 默认全量命令：**125 targets / 92 modules / 1579 tests / 0 failed，elapsed 436.32s**。
- Provider completeness `--write` 与最终 `--check`：**13/13 ready，findings=[]**。
- answer exporter：9 production-exported cases OK。
- vocabulary locality：`ok=true，findings=[]`。
- `provision_runtime.py --check`：通过；正式 venv 与工作树 pyc/pyo 均为 0。
- `git diff --check`：通过；未部署、未 push。
