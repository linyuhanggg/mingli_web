# Test Server Deploy: 6ec1578 (2026-08-11)

记录日期：2026-08-11（Asia/Shanghai）

状态：**代码测试服务器升级完成 / follow-up prepare 合同修复已上线 / production blocked / real traffic disabled**

本轮用户明确暂时不管备案和支付。本记录不是 production 放量批准。

## 部署前后

- 前：`b104245a6e6d9b441eddb1f9cdd703acbf6efd94`
- 后：`6ec15786ac8ce110bbf698b1c8578518123b1a2a`
- 增量：follow-up 改为携带最近 Accepted `state_token`、`transition=null`；归档 `scripts/run_server_task13_http.py`

## 根因

Task13 服务器轨迹在 `b104245` 上已把 preview/today/week/liuyao 推到 accepted，但 follow-up 在 prepare 阶段 `terminal_stopped`（Runtime `reason=error`，文案“本次处理未完成，请稍后重试”）。解密 prepare 后确认：

- follow-up 写入了 `transition=correct`
- `state_token=null`
- 只注入了 `prior_answer`

这与 V5.1 合同不一致：同盘追问应使用最新 Accepted token，transition 为空；`correct` 只用于纠正事实输入。

## 归档

- 文件：`fateradar-6ec15786ac8ce110bbf698b1c8578518123b1a2a.tar.gz`
- SHA-256：`e1655b528250d76192e05c05b36bb5cddb47a61b561f89be19cf5dd0ec5c822d`
- 路径：`/opt/fateradar/releases/6ec15786ac8ce110bbf698b1c8578518123b1a2a/`
- 备份：`/opt/fateradar/shared/backups/6ec15786...-pre-switch.dump` + MANIFEST

## 健康验收

- systemd api/worker/web：active，`NRestarts=0`
- API live/ready：200
- Web `/`、Nginx `8080`、公网 `18080`：200
- 环境仍为：`local` + OTP `fake` + Runtime `one-shot` + Model `deepseek`

## 关联证据

- 修复提交：`6ec1578 fix(readings): pass accepted token on follow-up prepare`
- 前一版 reference closer：`b104245`
- Task13 轨迹文档：`docs/releases/2026-08-11-task13-server-trajectory.md`
- 紫微 UI-only：Task 0–5/7 完成，Task 6 有意跳过

## 仍 blocked（不含备案/支付）

- 固定模型质量评测 / Guard 红队
- Secret Manager、告警、state volume 恢复演练
- 真实公网放量

`production blocked / real traffic disabled`

## Task13 验收（部署后）

目录：`/tmp/task13-server-trajectory-v3/` → 仓库 `docs/releases/evidence/2026-08-11-task13-server-trajectory/run-4-followup-fix/`

| 轨迹 | 结果 |
|---|---|
| preview | accepted |
| today | accepted |
| week | accepted |
| liuyao | accepted |
| followup | accepted |

DB 存量（本轮后）：accepted=20 / delayed=17 / terminal_stopped=3（含历史失败样本）。

## 健康复验

- current：`/opt/fateradar/releases/6ec15786ac8ce110bbf698b1c8578518123b1a2a`
- api/worker/web active，NRestarts=0
- live/ready 200；web/nginx/18080 200

