# P7-007 通知 Outbox 投递状态证据

日期：2026-08-14（Asia/Shanghai）  
范围：站内/邮件/短信偏好已经入队后的本地投递边界：claim lease、fencing token、尝试次数、失败重试、终态失败和 Admin 状态管理。

## 已验证行为

- `NotificationOutbox` 保存 `attempt_count`、`processing_until` 和 `processing_token`；
- claim 只取到期的 pending 或 processing 记录，并用数据库锁和 token 防止旧 worker 覆盖新 worker；
- 投递成功进入 `sent`，清理处理租约和错误；
- 投递失败按最大尝试次数回到 `pending`，设置下一次 `available_at`；达到上限进入 `failed`，不再自动领取；
- `NotificationWorker` 只负责状态机和注入的 sender，不伪造邮件/SMS 供应商调用；
- 迁移 `0018_notification_delivery_state` 已加入 Alembic head，旧 commerce 行为保持通过。
- 新增 Admin `/api/v1/admin/notifications` 状态列表和 `/{id}/retry` 重排接口；仅 `superadmin` 可读写，写入要求 CSRF、原因和 `notification.retry` 审计；响应不含通知 payload。
- Admin `/notifications` 已接真实 Outbox 状态、错误摘要和失败重试原因表单；页面不展示用户通知正文。
- 新增迁移 `0031_notification_in_app_state`，为 Outbox 持久化 `read_at`/`deleted_at` 和按 owner/time 的查询索引；用户 API 新增站内通知列表、未读筛选、单条已读、全部已读和软删除。
- 用户 API 只允许当前账户读取 `channel=in_app` 记录，响应投影为标题、摘要、时间、已读状态和固定原任务入口；不返回 owner、kind、payload、投递错误、邮件或短信记录，跨用户操作统一返回 404。
- Web `/account/notifications` 已复用账户会话门控，真实接入上述列表与命令；未登录不发列表请求，页面具备全部/未读筛选、未读数、已读、删除和空/错/过期状态。

## 定向结果

```bash
uv run --project backend pytest backend/tests/test_notification_worker.py -q
```

结果：`4 passed`。

迁移、模型、账本和通知回归：`12 passed`；定向 Ruff、mypy 通过。

```bash
uv run --project backend pytest backend/tests/test_admin_notifications.py backend/tests/test_openapi_alignment.py -q
```

结果：`7 passed`。

```bash
uv run --project backend pytest backend/tests/test_account_notifications.py backend/tests/test_data_rights.py backend/tests/test_notification_worker.py backend/tests/test_commerce_services.py -q
```

结果：`21 passed`；OpenAPI 对齐 `5 passed`，Web 通知/路由合同 `7 passed`，Web 全量 `62 files / 417 tests`。

Fresh SQLite 从空库升级到 `0031_notification_in_app_state` 后运行 `alembic check`，结果为 `No new upgrade operations detected`。

```bash
npm --prefix admin test -- --run src/components/admin-notifications-surface.test.tsx
```

结果：`2 passed`；Admin lint、typecheck 通过。

## 边界

这份证据证明本地 Outbox 状态机、用户站内通知投影、Admin 状态管理和可注入 worker 的持久化行为。真实 SMTP/SMS 供应商、投递 worker 部署、退信处理、全业务事件覆盖、Admin 运营策略和生产 SLO/告警仍未完成，因此 P7-007 保持 `IN_PROGRESS`；不替代 P4-007 或 P12 外部准入。
