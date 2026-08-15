# P7-004 付费交付幂等边界

日期：2026-08-14

## 本地实现

- 新增 `FulfillmentRecord`，以订单唯一、以订单+幂等键唯一，保存 Payment、购买目标、Reading Job、Accepted Copy、ReadingDocumentV1 引用及交付状态。
- `CommerceService.reserve_fulfillment` 只接受已确认 Payment，并为订单权益追加一次 `RESERVE`。
- `bind_fulfillment_job` 校验 Reading Job 与 Reading Version 的归属和绑定关系，重复绑定同一 Job 返回已有记录。
- `mark_fulfillment_delivered` 校验真实 `AcceptedCopy`、`ReadingDocumentRecord` 与已 Accepted 的 Reading Version，再追加一次 `CONSUME`。
- `release_fulfillment` 对终态失败追加一次 `RELEASE`，重复释放不覆盖原失败原因。

## 验收命令

```bash
uv run --project backend pytest backend/tests/test_fulfillment.py backend/tests/test_commerce_models.py backend/tests/test_migrations.py -q
# 9 passed

uv run --project backend ruff check --config backend/pyproject.toml \
  backend/app/commerce/models.py \
  backend/app/commerce/service.py \
  backend/tests/test_fulfillment.py \
  backend/alembic/versions/0020_fulfillment.py
# All checks passed!

uv run --project backend mypy --config-file backend/pyproject.toml \
  backend/app/commerce backend/tests/test_fulfillment.py
# Success: no issues found in 8 source files

uv run --project backend alembic -c backend/alembic.ini heads
# 0023_payment_attempt_unique (head)

# 在全新临时 SQLite 库 upgrade head 后执行：
uv run --project backend alembic -c backend/alembic.ini check
# No new upgrade operations detected.
```

## 未覆盖边界

该证据只证明当前工作树的本地服务、模型、迁移和状态边界。真实渠道验签/查单、生产 Worker 调度、正式用户 API、真实数据库部署和 P12-004 仍未完成，因此 P7-004 与 P12 不更新为完成。
