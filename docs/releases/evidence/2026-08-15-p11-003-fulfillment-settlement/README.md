# P11-003/P11-005 本地 Fulfillment 结算与终止释放

日期：2026-08-15

## 本轮完成

- Worker 在同一数据库事务中处理 Reading Job 结果：`Accepted` 且已经存在合法 `ReadingDocument` 时，通过 `CommerceService.deliver_fulfillment_for_job` 幂等写入一次 `CONSUME`；`terminal_stopped` 通过 `release_fulfillment_for_job` 幂等写入一次 `RELEASE`。
- `delayed` 和 `runtime_unknown` 不触发释放，继续保留预留，等待恢复或人工处理。
- `waiting_input` 记录进入时间；达到 7 天后由 Reading Worker 原子改为终止状态、幂等 `RELEASE`，并为登录用户写入去重的 `reading.failed` 站内通知；未到期限的任务保持等待。
- 用户补资料会恢复原有 waiting Job，不创建第二个 Job，因此原 Fulfillment 绑定在恢复后仍然有效；已有活动 Job 时返回冲突，不覆盖并发任务。
- 一个 `reading_job_ref` 只能绑定一个 Fulfillment；宿主侧先拒绝重复绑定，数据库新增唯一索引 `0037_fulfillment_job_unique` 处理并发竞态。
- 结算入口重新读取 AcceptedCopy 与 ReadingDocument，不能只凭 Job 状态消费权益；缺任一交付物会失败并回滚当前 Worker 事务。

## 已验证

```text
backend/tests/test_fulfillment.py                 5 passed
backend/tests/test_reading_worker.py              20 passed / 10 skipped
backend/tests/test_reading_migrations.py          30 passed
backend/tests/test_reading_repository.py           12 passed
backend/tests/test_readings_api.py                供应/超时定向回归通过
backend Ruff / mypy                               passed
```

覆盖了 AcceptedCopy/ReadingDocument 缺失不消费、成功重放不重复消费、同一 Job 拒绝第二个 Fulfillment、终止状态只释放一次，以及数据库唯一索引存在。

## 仍未完成

本地结算边界已经接通，但 P11-003/P11-005 仍不能标记完成：真实支付确认、生产权益消费、真实 PostgreSQL 故障注入、生产 Worker 和最终用户旅程仍缺。自动 Fulfillment 创建/绑定 API 已在 2026-08-15 的后续本地切片补齐，详见 `2026-08-15-p11-007-fulfillment-binding-api`；该证据不代表真实支付、生产账务或公开上线。

本证据不包含个人出生资料、密码、SMTP 凭据、API key 或其他秘密。

## 测试服务器热更新（2026-08-15）

- 在 `/opt/fateradar/shared/cache/p11-waiting-timeout-20260815/` 保留了后端源码、Worker、Alembic 和依赖清单的回退副本；没有删除旧 release 或业务数据。
- 测试 PostgreSQL 从 `0035_physiognomy_media` 迁移到 `0039_export_ck_names`，`0036`、`0037`、`0038` 和导出约束命名修复迁移均成功；真实服务器 `alembic check` 返回 `No new upgrade operations detected`。
- 修复热更新同步时带入的源码目录权限后，`fateradar` 用户导入 `app.main`/`worker.main` 成功；API、Worker、Web、Admin、Nginx 均 active，`NRestarts=0`。
- `GET /api/v1/health/live`、`GET /api/v1/health/ready`、测试 Nginx `/healthz`、`/bazi`、`/tools/five-elements`、`/tools/rhythm` 和 `/api/openapi.json` 均返回 200。
- 测试机继续保持 `local + Fake`，只用于页面浏览和测试数据验收，不代表真实生产 Runtime、真实支付或 P12 准入。
