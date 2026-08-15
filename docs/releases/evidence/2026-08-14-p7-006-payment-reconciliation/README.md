# P7-006 支付对账本地闭环证据

日期：2026-08-14  
范围：当前未提交工作树；验证对账服务、Admin API 和 `/reconciliation` 页面；未连接真实微信、支付宝、Apple 或生产数据库。

## 本轮补齐

- 新增 `0019_payment_reconciliation`，持久化已验签通知收据、对账批次和逐笔差异。
- `CommerceService.apply_payment_notification` 要求上游验签；同一渠道事件重复投递只复用已有 Payment，不重复追加权益 GRANT；同一事件绑定到另一笔交易会拒绝。
- `CommerceService.reconcile_channel` 接收已规范化的渠道支付/退款快照，按渠道自然交易号和退款号比较本地事实，保存 `matched`、本地独有、渠道独有、金额/币种/状态不一致、退款无支付和退款超额等差异。
- 退款按支付汇总金额比较；多条渠道退款合计超过原支付金额时记录 `refund_amount_exceeds_payment`，不自动补单、不自动冲账。
- 模型注册和从空 SQLite 数据库执行到 `head` 的迁移断言已覆盖三张新表。
- 新增 Admin `/api/v1/admin/reconciliation` 批次列表、`/runs` 执行、`/runs/{id}` 差异详情；`finance`/`ops`/`superadmin` 读取，写入要求 Admin CSRF、操作原因并追加 `payment.reconciliation.run` 审计事件。
- Admin `/reconciliation` 已显示真实批次、差异抽屉和结构化支付/退款快照表单；页面明确快照必须先由渠道适配器验签归一化，不接受 raw JSON 或伪造渠道成功态。

## 可复现检查

```text
uv run --project backend pytest backend/tests/test_payment_reconciliation.py backend/tests/test_migrations.py backend/tests/test_commerce_models.py backend/tests/test_commerce_services.py backend/tests/test_notification_worker.py -q
14 passed

uv run --project backend ruff check backend/app/commerce backend/app/adapters/payment.py backend/tests/test_payment_reconciliation.py backend/alembic/versions/0019_payment_reconciliation.py
All checks passed

uv run --project backend mypy backend/app/commerce backend/app/adapters/payment.py
Success: no issues found

uv run --project backend pytest backend/tests/test_admin_reconciliation.py backend/tests/test_openapi_alignment.py -q
7 passed

npm --prefix admin test -- --run src/components/admin-reconciliation-surface.test.tsx
2 passed

npm --prefix admin run lint
npm --prefix admin run typecheck
All passed
```

## 尚未覆盖

- `FakePaymentGateway` 仍是关闭态；没有真实渠道验签、主动查单、日账单下载或金额/币种由供应商提供的生产适配器。
- 尚未接定时对账 Worker、真实渠道账单下载、补单/双人处理 API 或差异解决状态；当前结果只追加本地事实，不会替 finance 做退款相关补偿。
- 因此 P7-006 更新为 `IN_PROGRESS`，P12-004 仍保持 `NOT_STARTED`；本证据不代表真实支付或生产发布验收。
