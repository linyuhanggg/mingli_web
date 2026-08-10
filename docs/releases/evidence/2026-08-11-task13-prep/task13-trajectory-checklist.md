# Task 13 轨迹清单（runner 输出）

- 生成时间：2026-08-10T21:01:20+00:00（UTC）
- dry-run：否

| ID | 轨迹 | 覆盖 | 状态 | 本地结果 | 下一步 |
|---|---|---|---|---|---|
| T13-01 | Runtime startup gate：13/13 describe + 冻结 manifest digest / capability shape | pytest 自动 | passed | 36 passed / 0 skipped | scripts/run_local_real_runtime_smoke.sh --skip-model |
| T13-02 | Release inventory 完整性：217 签名文件 / 55 古籍 / 1328 evidence / 13 Provider | pytest 自动 | passed | 7 passed / 0 skipped | scripts/run_local_real_runtime_smoke.sh --skip-model |
| T13-03 | bazi need_input：新单 → Stopped(need_input) → 续单 → Prepared | pytest 自动 | passed | 7 passed / 0 skipped | scripts/run_local_real_runtime_smoke.sh --model |
| T13-04 | bazi accepted：prepare → 一次模型调用 → guard → accepted（receipt 持久化） | pytest 自动 | passed | 12 passed / 0 skipped | scripts/run_local_real_runtime_smoke.sh --model |
| T13-05 | fortune day：today 精确目标区间 → accepted | pytest 自动 | passed | 4 passed / 0 skipped | 隔离 staging 真实 fortune 轨迹需服务端密钥/部署，未配置 |
| T13-06 | fortune week：near_seven → accepted | pytest 自动 | passed | 4 passed / 0 skipped | 隔离 staging 真实 fortune 轨迹需服务端密钥/部署，未配置 |
| T13-07 | liuyao manual：手动六爻（6..9 自下而上）→ accepted | pytest 自动 | passed | 3 passed / 0 skipped | 隔离 staging 真实 liuyao 轨迹需服务端密钥/部署，未配置 |
| T13-08 | liuyao digital：digital_coin 数字卦 → accepted | pytest 自动 | passed | 3 passed / 0 skipped | 隔离 staging 真实 liuyao 轨迹需服务端密钥/部署，未配置 |
| T13-09 | follow-up：prior_answer 注入新 brief → accepted 新版本 | pytest 自动 | passed | 1 passed / 0 skipped | 隔离 staging 真实 follow-up 需已 accepted 的真实成稿，未配置 |
| T13-10 | Guard 连续拒绝 → delayed，永不到 complete | pytest 自动 | passed | 3 passed / 0 skipped | 真实模型 Guard 拒绝轨迹需 staging 真实模型，未配置 |
| T13-11 | complete 落库后 crash → byte-identical replay → 单 Accepted | pytest 自动 | passed | 5 passed / 1 skipped | staging 真实轨迹 |
| T13-12 | 敏感数据边界：state_token / 出生资料 / Prompt / 密钥不泄漏 | pytest 自动 | passed | 12 passed / 0 skipped | staging 真实轨迹 |
| T13-13 | 运维 Gate：Guard 红队 / state volume backup-restore / 告警演练 / Secret Manager | pytest 自动 | passed | 50 passed / 65 skipped | Guard 红队用例集、生产告警演练（runtime_unknown/delayed/guard/model cost）、Secret Manager 密钥托管与轮换、真实 state volume backup/restore 均需隔离 staging/生产凭据，仓库内不可自动跑 |

## 约定

- 证据目录：`docs/releases/evidence/2026-08-11-task13-prep/`
  - `task13-trajectory-checklist.json` / `.md`：本清单（含每次 pytest 的 exit code、耗时、计数）
  - `logs/T13-XX.log`：每个自动检查点的 pytest 原始输出
  - `smoke-summary.json`：真实 Runtime smoke 摘要（无密钥/无 token）
- `pending` 不代表失败：表示该检查点需要隔离 staging/生产凭据，仓库内不可自动跑。
- Task 13 未完成；production blocked / real traffic disabled（见 docs/releases/2026-08-11-task13-prep-real-path-replay.md）。
