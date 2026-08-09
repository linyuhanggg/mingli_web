# Mingli V5.1 Web Phase 2 第一版代码候选

记录日期：2026-08-10（Asia/Shanghai）

状态：**第一版代码候选已在回环代码测试服务器验收 / real staging blocked / production blocked**

结论：本记录不是上线批准。Task 11/12 固定候选 `2fdb7b8` 已进入 `main`；部署配置、真实 PostgreSQL 迁移修复和 Fake 全链路修复形成最终代码测试候选 `bb742b7`，并已通过 SSH 隧道后的回环服务器验收。该服务器固定使用 `local + Fake`，不接真实模型、短信、支付或公网业务流量，因此它不是 staging/production。`real traffic` 保持 disabled，生产不可部署、不可放量。只有仓库内可定位的机制、提交和本轮实际执行结果计入证据，台账状态、计划文字、测试夹具及历史口头结论都不替代原始产物。

## 1. 已有机制与可定位提交

本轮 Task 11/12 功能基线为 `2fdb7b8`，服务器实际验收的固定应用候选为 `bb742b7`。Task 11 API、Task 12 Web 真实 API 接入和 FateRadar UI 分支均已形成可定位提交；下表只说明机制已经存在，不说明生产 Gate 已通过。

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

服务器首次迁移暴露 Alembic 默认 `version_num VARCHAR(32)` 无法写入 0003/0006/0007 长 revision ID；失败事务完整回滚，测试库保持 0 张表。修复提交 `c462934` 先以失败测试稳定复现，再缩短三个 ID，迁移聚焦回归 `29 passed`，完整门禁为后端/合同 `459 passed, 90 skipped`、Web `85 passed`。随后服务器 Fake E2E 暴露 Runtime brief 的 `limit:fake` 与 Preview 合同 `limit:traditional` 不闭合，固定产生 `unknown_limit_ref` 与 `scope_mismatch` 并落入 `delayed`；修复提交 `bb742b7` 同样先红后绿，最终完整门禁为后端/合同 `460 passed, 90 skipped`、Web `85 passed`，Ruff、mypy、ESLint、TypeScript 与 Next production build 全部通过。

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
- 真实 staging 交付入口仍缺失：当前已建立的是 SSH 隧道后的 `local + Fake` 回环代码测试环境，虽有独立数据库、服务器端秘密、`pg_dump`、固定 release、原子 symlink 和回滚手册，但没有真实 Runtime/Model Adapter、真实渠道凭据或 staging trajectory，不得冒充 staging。

## 5. 发布决定与后续填写字段

当前决定固定为：**本地代码候选通过；回环代码测试服务器验收通过；real staging blocked；production blocked；real traffic disabled；不可放量。**

Task 11/12 与 UI 合并候选已形成固定提交 `2fdb7b8`；最终代码测试候选 `bb742b7` 通过本地完整门禁、服务器构建、真实 PostgreSQL 迁移、Fake 端到端和重启复验。允许的下一步是补齐真实 Runtime/Model、固定模型评测、原始 Gate 证据与隔离 staging trajectory；补齐上节生产原始证据前，不得接真实流量。不能直接把本记录改写成“已上线”，也不能用台账勾选代替原始证据。

## 6. 回环代码测试服务器实跑证据

- SSH 入口：`fateradar-prod`；仅通过 `ssh -L 18080:127.0.0.1:8080 fateradar-prod` 访问。Nginx、Web、API 分别监听 `127.0.0.1:8080/3000/8000`，没有新增公网端口或 UFW 规则。
- 固定 release：`bb742b7f2acdeb47344c8f3d8c858e580d527011`；归档 SHA-256 为 `38217033c26422073e1b35e023e337d327b4ae752de03abae7820691ec08659c`，上传前后两端校验一致；`/opt/fateradar/current` 原子指向该目录。
- 运行栈：uv `0.11.6`、CPython `3.13.13`、Node `22.22.1`、npm `9.2.0`、PostgreSQL `18.4`。backend 每版独立 `.venv`，Web 每版独立 `node_modules` 与 standalone 产物。
- 数据库：`fateradar_test` 使用独立 role；真实秘密只在服务器生成并保存在 root:root `0600` 的 `/etc/fateradar/test.env`，没有进入仓库或命令输出。Alembic 到唯一 head `0007_api_idem_verify`，public schema 共 17 张表。
- 备份：迁移前和最终切换前均生成非空 `pg_dump -Fc`、SHA-256 与 manifest，保存在 `/opt/fateradar/shared/backups/`；失败 release 与最终前一版均保留，未原地覆盖。
- 服务：`fateradar-test-api`、`fateradar-test-worker`、`fateradar-test-web` 与 Nginx/PostgreSQL 均 active；三项应用服务均 enabled，最终进程 `NRestarts=0`。`/healthz`、API live/ready、Web 首页全部 200。
- Fake E2E：Guest Session → OTP `246810` → 登录 → Profile 草稿/确认 → Preview → Worker → Accepted → Result → Verification → Idempotency replay 全部通过；最终阅读 `cf6627d9-34c4-4085-8864-5b40549b8b5c` 两次轮询到 `accepted`，数据库状态为 `accepted / complete`，一条模型尝试、一条 Verification，重放返回同一 reading version。
- 浏览器：服务器页面经 SSH 隧道在 1440×900 与 360×800 实测无横向溢出，交互目标没有低于 44px；账户页能从“正在建立安全会话”进入“安全会话已建立”，浏览器控制台无 error/warn。
- 既有公网 Nginx 配置未改：服务器本机验证根站仍为 200，`api.fateradar.cn` 仍保持原占位 503；域名、TLS/letsencrypt、UFW 和宝塔面板均未调整。
- 重启：三项应用服务人工 restart 后健康复验通过。Next standalone 按自身约定在收到 SIGTERM 时退出 143，systemd 会留下 stop 阶段的失败噪音，但无 `Scheduled restart`、`NRestarts=0`，当前 `Result=success`；可后续用 `SuccessExitStatus=143` 消除噪音，不阻塞本次代码测试。
- 回滚边界：最终版是第一份完整 Fake E2E 通过的 release，因此本轮未把 `current` 切回已知有 Fake Guard 缺陷的旧版。首次部署可按 `infra/TEST_SERVER_RUNBOOK.md` 停止三项服务并移除 `current`；数据库和各版备份足以恢复排障，但这不等于生产级恢复演练。
