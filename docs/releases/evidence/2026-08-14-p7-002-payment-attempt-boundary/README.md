# P7-002 支付尝试确认边界

日期：2026-08-14（Asia/Shanghai）  
范围：当前未提交工作树；只验证本地支付事实状态，不连接真实渠道。

## 本轮补齐

- `confirm_payment` 要求传入渠道与创建 `PaymentAttempt` 时的渠道完全一致。
- 同一 `PaymentAttempt` 首次确认后，同交易号重放返回原 `Payment`；不同交易号拒绝，不再追加第二笔 `Payment` 或第二次 `GRANT`。
- 已到账订单拒绝迟到的其他 `PaymentAttempt`；同一退款渠道流水号不能错绑另一笔 Payment。
- `payments.attempt_id` 新增 `uq_payments_attempt_id`，由 `0023_payment_attempt_unique` 在数据库层保证一次尝试最多一笔 Payment。

## 可复现检查

```text
uv run --project backend pytest backend/tests/test_commerce_services.py backend/tests/test_payment_reconciliation.py -q
10 passed

uv run --project backend pytest backend/tests/test_migrations.py -q
2 passed

uv run --project backend ruff check backend/app/commerce/models.py backend/app/commerce/service.py backend/tests/test_commerce_services.py backend/tests/test_migrations.py
All checks passed!

uv run --project backend mypy backend/app/commerce/models.py backend/app/commerce/service.py
Success: no issues found in 2 source files

MINGLI_DATABASE_URL=sqlite+aiosqlite:////tmp/mingli-alembic-check-20260814.sqlite3 uv run --project backend alembic -c backend/alembic.ini upgrade head
MINGLI_DATABASE_URL=sqlite+aiosqlite:////tmp/mingli-alembic-check-20260814.sqlite3 uv run --project backend alembic -c backend/alembic.ini check
No new upgrade operations detected.
```

## 未覆盖边界

该证据只证明本地服务层和数据库约束。真实支付适配器的验签、主动查单、重复通知生产演练、支付 Worker/API 接线和生产凭据仍未完成，因此 P7-002 继续为 `IN_PROGRESS`，P12-004 也不变。
