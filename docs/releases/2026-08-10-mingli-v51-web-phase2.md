# Mingli V5.1 Web Phase 2 第一版代码候选

记录日期：2026-08-10（Asia/Shanghai）

状态：**第一版代码候选已冻结进 `main` / staging blocked / production blocked**

结论：本记录不是上线批准。固定候选 `2fdb7b8` 已通过本地代码门禁并进入 `main`，但当前没有可审计的 staging 主机、隔离配置/数据库及备份回滚流程，因此本轮没有上传测试服务器。`real traffic` 保持 disabled，生产不可部署、不可放量。只有仓库内可定位的机制、提交和本轮实际执行结果计入证据，台账状态、计划文字、测试夹具及历史口头结论都不替代原始产物。

## 1. 已有机制与可定位提交

本轮审计所见的固定代码候选为 `main` 的 `2fdb7b8`。Task 11 API、Task 12 Web 真实 API 接入和 FateRadar UI 分支均已形成可定位提交；下表只说明机制已经存在，不说明生产 Gate 已通过。

| 机制 | 仓库位置 | 可定位提交 | 当前能证明的范围 |
|---|---|---|---|
| Command、Result、Narrative Candidate、Output Contract | `contracts/schemas/`、`tests/contract/test_mingli_schemas.py` | `92ef5c8` | 共享合同及其形状测试存在 |
| 完整 Runtime inventory 与 P0 产品曝光分离 | `backend/app/readings/`、`tests/contract/test_mingli_runtime_release.py` | `8e09e68` | 13 Provider 的 Runtime 范围没有被 P0 三能力裁剪 |
| Narrative Guard 与确定性正文装配 | `backend/app/readings/narrative_guard.py`、`backend/tests/test_narrative_guard.py` | `fee0eee` | 引用闭合、范围和结构规则已有单元测试；不等于完成红队 |
| 显式 Reading Orchestrator、加密持久化与恢复围栏 | `backend/app/readings/orchestrator.py`、`backend/app/readings/repository.py`、`backend/worker/readings.py` | `c1e9400`、`e775959`、`728f506` | 代码级状态推进、持久化和恢复机制可定位；不等于状态卷恢复演练通过 |
| Mac mini `native-full` 门禁与独立 verifier | `infra/mingli-runtime/local_gate.py`、`infra/mingli-runtime/verify_local_full.py` | `4899607`、`a91ecbb` | 1584/0、600 秒、输入摘要和报告封存的 fail-closed 规则存在；不等于本仓库持有当次原始报告 |
| one-shot Runtime Adapter 与 Worker 启动门禁 | `backend/app/adapters/runtime.py`、`backend/tests/test_runtime_startup_gate.py` | `d529f92`、`a9b33dd` | 固定 one-shot 边界与 fail-closed startup describe 可定位 |
| standalone Model Adapter 与自校验调用回执 | `backend/app/adapters/model.py`、`backend/app/readings/model_contracts.py` | `156de4d`、`f90ab96`、`c73aa46`、`a5cd4b6`、`f083e93` | 单模型调用、回执持久化和敏感日志收敛机制可定位；不等于固定模型质量评测通过 |
| Task 11 Profile/Reading API、持久化幂等与 OpenAPI | `backend/app/api/`、`backend/app/profiles/`、`backend/app/readings/`、`contracts/openapi/v1.yaml` | `f0e7dcc` | 当前固定候选上的 API、所有权、CSRF、限流和幂等机制可定位；进程内限流不等于生产 Redis 限流 |
| Task 12 Web 真实 API 流程与 FateRadar UI | `web/src/`、`DESIGN.md`、`PRODUCT.md` | `66b76ef`、`2fdb7b8` | 建档、今日/近七日、六爻、结果/核对/追问及 UI 合并历史可定位；未接通能力保持 empty/disabled，不伪造结果 |

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

以下命令于 2026-08-10（Asia/Shanghai）在 `/Volumes/Lexar/code/mingli_web` 的固定合并候选 `2fdb7b8` 上实际执行。测试执行时 merge 内容已经全部暂存且无未解决冲突；随后生成的 merge commit 与被测索引内容一致，`main` 以 fast-forward 指向该提交。

| 命令 | 实跑结果 |
|---|---|
| `make check` | PASS：后端与合同 `458 passed, 90 skipped`；Ruff 通过；mypy `60 source files` 无问题；Web `85 passed`；ESLint、TypeScript 与 Next.js production build 通过，10/10 页面生成完成 |
| `make test` | PASS：独立复跑后端与合同 `458 passed, 90 skipped`；Web `85 passed` |

浏览器冒烟覆盖 1440×900 与 360×800：首页、私人首页和建档页均无横向溢出；首页与建档页可见控件没有低于 44px 的目标，建档输入均有可访问标签，动态解读路由只保留 `/app/readings/[readingId]`。本地控制台仅出现 React 开发模式在浏览器扩展 CSP 下不支持 `eval()` 的提示；生产构建不使用该调试路径。

分支收口结果：`codex/ui-fateradar-web` 以普通 merge 保留四个独有提交历史；四个 patch-equivalent `supervisor/*` 分支未重复合并；所有临时 worktree 与已吸收分支均已移除。当前只有 `main` 分支和 `/Volumes/Lexar/code/mingli_web` 一个 worktree。

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
- 测试服务器交付入口缺失：仓库未配置 Git remote，也没有明确 staging 主机、非交互部署脚本、staging 专用环境变量/数据库、`pg_dump` 备份恢复与回滚演练记录。现有 `infra/` 是 production edge 占位配置和本地 Compose，不得冒充 staging 运行手册。

## 5. 发布决定与后续填写字段

当前决定固定为：**本地代码候选通过；staging upload blocked；production blocked；real traffic disabled；不可放量。**

Task 11/12 与 UI 合并候选已形成固定提交 `2fdb7b8` 并通过 `make check` 与 `make test`。允许的下一步是先建立隔离 staging 目标、凭据、数据库、备份恢复和回滚流程，再上传该固定提交跑 Fake 端到端；补齐上节生产原始证据前，不得接真实流量。不能直接把本记录改写成“已上线”，也不能用台账勾选代替原始证据。
