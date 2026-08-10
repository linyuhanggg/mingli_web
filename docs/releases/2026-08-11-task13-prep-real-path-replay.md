# Task 13 前置：真实路径可复跑脚本与轨迹清单脚手架

记录日期：2026-08-11（Asia/Shanghai）

状态：**本机真实 Runtime + 真实模型路径已固化为可复跑脚本 / 13 条轨迹清单与本地自动覆盖已固化 / Task 13 仍未完成 / production blocked / real traffic disabled**

结论：本记录不构成上线批准。它把之前靠手敲跑出来的真实链路冒烟变成一条命令，并把 Task 13 要求的轨迹拆成 13 个检查点，能自动跑的先自动跑、跑不了标 pending 写清原因。隔离 staging 全轨迹、Guard 红队、告警演练、密钥托管和外部合规 Gate 依然缺，缺一个都不能宣称 Task 13 完成。

## 1. 本轮交付

### 1.1 真实 Runtime + 真实模型可复跑脚本

- `scripts/run_local_real_runtime_smoke.sh`：加载本机私密 env（`~/.config/mingli/local-real-model.env`，600），fail-closed 校验四个 Runtime 路径与两个冻结 digest，然后调 Python 入口。默认「有密钥就顺带跑真实模型冒烟」；`--skip-model` 只跑 Runtime；`--model` 强制模型冒烟、缺密钥直接失败。
- `scripts/smoke_local_real_runtime.py`：真实启动 `build_runtime_startup_gate(...).startup()`，打印 13/13 describe、manifest digest、capability shape、inventory（217 文件 / 55 古籍 / 1328 evidence / 13 Provider）；有密钥时 prepare 一条 bazi 夹具 + 真实模型 generate 一次，确认 receipt `succeeded` 且 content 非空。

密钥边界：env 文件只在脚本内被 source，任何路径都不打印、不回显、不提交其内容；摘要 JSON 只含 digest、shape、计数与 receipt 元数据。

### 1.2 Task 13 轨迹清单 / runner

`scripts/task13_trajectory_runner.py` 把 Task 13 的轨迹要求拆成 13 个检查点，输出到 `docs/releases/evidence/2026-08-11-task13-prep/`：

| 检查点 | 内容 | 自动覆盖 | 状态 |
|---|---|---|---|
| T13-01 | Runtime startup gate：13/13 describe + 冻结 digest/shape | pytest 全文件 + 真实 smoke | 已可复跑 |
| T13-02 | Release inventory：217 文件 / 55 古籍 / 1328 evidence / 13 Provider | pytest 完整性用例 + 真实 smoke | 已可复跑 |
| T13-03 | bazi need_input：新单 → Stopped → 续单 → Prepared | orchestrator prepare 用例 + 真实 prepare | 已可复跑 |
| T13-04 | bazi accepted：prepare → 一次模型 → guard → accepted | orchestrator complete + 全链路 API 用例 + 真实模型 | 已可复跑 |
| T13-05 | fortune day：today 精确区间 → accepted | 本地 Fake 全链路 + compiler 冻结快照 | 本地绿 / 真实 staging pending |
| T13-06 | fortune week：near_seven → accepted | 同上 | 本地绿 / 真实 staging pending |
| T13-07 | liuyao manual：手动爻 → accepted | compiler 冻结快照 + API 假链路 | 本地绿 / 真实 staging pending |
| T13-08 | liuyao digital：digital_coin → accepted | 同上 | 本地绿 / 真实 staging pending |
| T13-09 | follow-up：prior_answer 注入 → accepted 新版本 | API follow-up 用例 | 本地绿 / 真实 staging pending |
| T13-10 | Guard 连续拒绝 → delayed，永不到 complete | orchestrator delayed 用例 | 本地绿 / 真实模型拒绝轨迹 pending |
| T13-11 | complete 落库后 crash → byte-identical replay → 单 Accepted | orchestrator recovery 用例（PG 并发用例本地 skip） | 本地绿 / staging 实战 pending |
| T13-12 | 敏感数据边界：state_token / 出生资料 / Prompt / 密钥 | sensitive-payloads + model-data-boundary + 审计泄漏用例 + OpenAPI 契约 | 已自动覆盖 |
| T13-13 | 运维 Gate：Guard 红队 / backup-restore / 告警 / Secret Manager | 契约级 backup-drill + local gate 用例 | 契约级绿 / 实战演练 pending |

`pending` 的含义：需要隔离 staging/生产凭据或真实模型/服务器，仓库内不可自动跑；它不代表失败，但代表 Task 13 还没完成。

## 2. 用法

```bash
# 真实 Runtime 冒烟（有密钥时顺带跑一次真实模型，消耗一次调用）
scripts/run_local_real_runtime_smoke.sh --evidence-dir docs/releases/evidence/2026-08-11-task13-prep

# 只跑真实 Runtime 启动（不花钱）
scripts/run_local_real_runtime_smoke.sh --skip-model

# 13 条轨迹清单：先看 dry-run，再全量跑本地自动覆盖 + 真实 smoke
uv run --project backend python scripts/task13_trajectory_runner.py --dry-run
uv run --project backend python scripts/task13_trajectory_runner.py --with-real-smoke
```

退出码约定：smoke `0` 成功 / `2` 缺 env 或路径 / `3` Runtime 启动失败 / `4` 模型冒烟失败；runner `0` 全部自动检查点通过、`1` 有自动检查点失败。缺环境时两者都 fail-closed 并写明缺什么，不会编造成功。

## 3. 本机实跑结果（脱敏）

证据目录：`docs/releases/evidence/2026-08-11-task13-prep/`

- `smoke-summary.json`：真实 Runtime startup `OK`（`one-shot-process` / 13/13 describe），manifest digest 与 capability shape 匹配冻结值，inventory 217/55/1328/13；真实模型 generate `succeeded`（deepseek-v4-flash，candidate blocks 非空）。
- `task13-trajectory-checklist.json` / `.md`：13 个检查点的 pytest 结果、exit code、耗时、计数与 pending 原因。
- `logs/`：每个自动检查点的 pytest 原始输出。

所有输出均不含 API Key、state_token、出生资料原文或 Prompt。

## 4. 仍 blocked / 还差什么

- 隔离 staging 真实轨迹：fortune day/week、liuyao manual/digital、follow-up、真实模型 Guard 拒绝 delayed、byte-identical replay 的服务端证据。
- Guard 红队用例集；state volume backup/restore 实战；runtime_unknown / delayed / Guard 拒绝 / 模型成本四类生产告警演练。
- Runtime / Model 生产凭据进 Secret Manager 与轮换演练（本机与测试服务器的 0600 env 只是联调口径）。
- 固定 Model Profile 质量评测与盲测。
- 支付 / 短信 / 邮件 / ICP / 公安联网等外部 Gate。

在以上补齐前：`real staging blocked / production blocked / real traffic disabled`；测试服务器出现过的 `accepted` 只是联调通路，不构成 Task 13 完成。

## 5. 禁止项复查

- 仓库未写入任何 API Key / 密码 / OTP / 商户证书。
- 未启动 VZ/Rosetta/QEMU/linux-certify；未裁剪 13 Provider / 55 古籍 / 1328 evidence。
- 未改前端 UI；未动测试服务器与生产配置。
- 默认业务路径仍是 Fake；不注入密钥时不得宣称真实成稿链路已通。

下一断点仍见 [HANDOFF_SNAPSHOT_2026-08-11.md](../HANDOFF_SNAPSHOT_2026-08-11.md)。
