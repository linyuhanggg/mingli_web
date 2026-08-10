# Test Server Deploy: 3cd39ed (2026-08-11)

记录日期：2026-08-11（Asia/Shanghai）

状态：**代码测试服务器升级完成 / Task13 服务器轨迹 partial 已归档 / production blocked / real traffic disabled**

本轮用户明确暂时不管备案和支付。本记录不是 production 放量批准。

## 部署前后

- 前：`1c26f0924ce22171b32f0c75a781f7599eec6ed5`
- 后：`3cd39ed88fe642efa8b0a0eb3e543d189f0db538`
- 增量：结论优先 UI 收口、Task13 服务器轨迹 runner/证据、handoff 对齐

## 归档

- 文件：`fateradar-3cd39ed88fe642efa8b0a0eb3e543d189f0db538.tar.gz`
- SHA-256：`2eb3a2c1e7c11bfac26be1add9c7efb2e55b392e04cddda77fb976ad8307948c`
- 路径：`/opt/fateradar/releases/3cd39ed88fe642efa8b0a0eb3e543d189f0db538/`
- 备份：`/opt/fateradar/shared/backups/3cd39ed...-pre-switch.dump` + MANIFEST

## 健康验收

- systemd api/worker/web：active，`NRestarts=0`
- API live/ready：200
- Web `/`、Nginx `8080`、公网 `18080`、`/app/bazi`、`/app/profile/new`：200
- 环境仍为：`local` + OTP `fake` + Runtime `one-shot` + Model `deepseek`

## 关联证据

- Task13 服务器轨迹 partial：`docs/releases/2026-08-11-task13-server-trajectory.md`
- 主导因：真实模型 generate 成功，但 Guard 以 `scope_mismatch` 为主拒绝后进入 delayed

## 仍 blocked（不含备案/支付）

- Task13 稳定 accepted 全轨迹（fortune/liuyao/follow-up/replay）
- 固定模型质量评测 / Guard 红队
- Secret Manager、告警、state volume 恢复演练

`production blocked / real traffic disabled`
