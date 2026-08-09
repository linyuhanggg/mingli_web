# Mingli V5.1 Web Phase 2 第一版代码候选

记录日期：2026-08-10（Asia/Shanghai）

状态：**第一版代码候选 / production blocked**

结论：本记录不是上线批准。`real traffic` 保持 disabled；当前候选不可部署、不可放量。只有仓库内可定位的机制、提交和本轮实际执行结果计入证据，台账状态、计划文字、测试夹具及历史口头结论都不替代原始产物。

## 1. 已有机制与可定位提交

本轮审计所见的已提交代码基线截至 `f083e93`；Task 11/12 位于该基线之上的当前工作树。下表只说明机制已经存在，不说明生产 Gate 已通过。由于候选尚未形成不可变提交，本轮本地绿测也不能替代固定候选复验。

| 机制 | 仓库位置 | 可定位提交 | 当前能证明的范围 |
|---|---|---|---|
| Command、Result、Narrative Candidate、Output Contract | `contracts/schemas/`、`tests/contract/test_mingli_schemas.py` | `92ef5c8` | 共享合同及其形状测试存在 |
| 完整 Runtime inventory 与 P0 产品曝光分离 | `backend/app/readings/`、`tests/contract/test_mingli_runtime_release.py` | `8e09e68` | 13 Provider 的 Runtime 范围没有被 P0 三能力裁剪 |
| Narrative Guard 与确定性正文装配 | `backend/app/readings/narrative_guard.py`、`backend/tests/test_narrative_guard.py` | `fee0eee` | 引用闭合、范围和结构规则已有单元测试；不等于完成红队 |
| 显式 Reading Orchestrator、加密持久化与恢复围栏 | `backend/app/readings/orchestrator.py`、`backend/app/readings/repository.py`、`backend/worker/readings.py` | `c1e9400`、`e775959`、`728f506` | 代码级状态推进、持久化和恢复机制可定位；不等于状态卷恢复演练通过 |
| Mac mini `native-full` 门禁与独立 verifier | `infra/mingli-runtime/local_gate.py`、`infra/mingli-runtime/verify_local_full.py` | `4899607`、`a91ecbb` | 1584/0、600 秒、输入摘要和报告封存的 fail-closed 规则存在；不等于本仓库持有当次原始报告 |
| one-shot Runtime Adapter 与 Worker 启动门禁 | `backend/app/adapters/runtime.py`、`backend/tests/test_runtime_startup_gate.py` | `d529f92`、`a9b33dd` | 固定 one-shot 边界与 fail-closed startup describe 可定位 |
| standalone Model Adapter 与自校验调用回执 | `backend/app/adapters/model.py`、`backend/app/readings/model_contracts.py` | `156de4d`、`f90ab96`、`c73aa46`、`a5cd4b6`、`f083e93` | 单模型调用、回执持久化和敏感日志收敛机制可定位；不等于固定模型质量评测通过 |

## 2. 本轮已实跑的短测

- 工作目录：`/Volumes/Lexar/code/mingli_web`
- 执行日期：2026-08-10（Asia/Shanghai）；本轮没有采集可复核的时分秒，因此不虚构精确钟点。
- 精确命令：

  ```bash
  uv run --project backend pytest tests/contract/test_native_release_policy.py -q
  ```

- 原样结果摘要：`4 passed in 1.05s`
- 证据边界：该短测验证当前 native release policy、纯合同与退役 Linux 执行策略，**没有执行真实 `native-full`，不能作为 1584/0 原始报告或独立 verifier 通过证明**。

## 3. Task 11/12 最终整合后的本地门禁

以下命令于 2026-08-10（Asia/Shanghai）在 `/Volumes/Lexar/code/mingli_web` 实际执行。候选以 `f083e93` 为基线，但执行时包含尚未提交的 Task 11/12 工作树，因此这些结果证明当前工作树通过本地门禁，不构成固定提交的发布签章。

| 命令 | 实跑结果 |
|---|---|
| `make check` | PASS：后端与合同 `458 passed, 90 skipped`；Ruff 通过；mypy `60 source files` 无问题；Web `53 passed`；ESLint、TypeScript 与 Next.js production build 通过，10/10 页面生成完成 |
| `make test` | PASS：独立复跑后端与合同 `458 passed, 90 skipped`；Web `53 passed` |

旧提交或其他工作树的历史绿测不能替代上述结果；同样，上述工作树绿测也不能替代后续固定候选提交上的复跑。

## 4. 当前缺失或依赖外部环境的发布证据

以下项目全部保持 Pending：

- Mac mini `native-full` 原始证据归档缺失。仓库中找不到应成套保存的 `native-full-5.1.json`、`local-native-full-5.1.json`、`native-release-regression.stdout`、`native-release-regression.stderr` 和 `prepared-inputs.json`，因此不能从当前仓库独立复验 126 targets、93 modules、1584 tests、0 failed 或 verifier 结果。
- 完整 13 Provider characterization matrix 与 native release regression 的当次原始输出缺失。
- 55/55 reference-pack 完整性检查的当次原始输出缺失。
- 1328-entry evidence-index 完整性检查的当次原始输出缺失。
- 固定安装路径、UID 和 state volume 上的 Prepared/Accepted token backup/restore 演练及恢复断言缺失；历史 Linux Gate 代码不是当前演练证据。
- 模型供应商 DPA、数据保存期限、训练退出确认和 fixed model eval（固定 Model Profile 质量评测）结果缺失。
- 独立 Narrative Guard red-team 反例集及执行结果缺失；现有单元测试不能替代正式红队。
- Runtime/Model 生产凭据的 Secret Manager 托管、最小权限、轮换和演练记录缺失；本轮没有进行凭据测试。
- `runtime_unknown`、`delayed`、Narrative Guard rejection、model cost 四类生产告警的配置、路由和触发演练缺失。
- Task 13 真实 staging trajectory 缺失，包括 13 Provider describe/依赖证据、八字 need-input 到 Accepted、fortune 日/周、六爻手动/数字、follow-up、Guard 连续拒绝后 delayed 且不 complete，以及 complete 提交后数据库故障的 byte-identical replay/单一 Accepted。

## 5. 发布决定与后续填写字段

当前决定固定为：**production blocked；real traffic disabled；不可部署；不可放量。**

Task 11/12 当前工作树已通过 `make check` 与 `make test`，但后续仍须形成固定候选提交并复跑，同时补齐上节全部原始证据，才能在新的复核中填写证据归档路径及每项 Gate 的审核人和日期。不能直接把本记录改写成“已上线”，也不能用台账勾选代替原始证据。
