# P11-005 追问合同本地边界

日期：2026-08-14

## 本地实现

- `ReadingRoot` 保存 `ProductVersion` ID、追问次数、追问窗口和窗口起点的冻结快照；不把商品当前值回读成历史事实。
- Fulfillment 绑定 Reading Job 时写入快照；若初版已经 Accepted，窗口起点取初版 Accepted 时间。
- Follow-up 只允许同一 ReadingRoot 的最新 Accepted 版本；已有后续版本时，旧版本不能再开分支。
- 已 Accepted 的追问版本才计入次数；免费预览没有商品快照，保留原有本地预览行为。
- 窗口过期或次数耗尽返回 409，不创建新的 ReadingVersion/Job。
- 当前工作树新增 `POST /api/v1/readings/{reading_version_id}/recast`：用按 `action` 判别的结构化请求承载 profile/日运/周运和六爻换事件；源版本必须属于当前 owner、已 Accepted 且有 AcceptedCopy，成功后创建独立 ReadingRoot，不把 Recast 串入原 Root。
- Recast 复用现有 Profile/Reading 编译器和幂等存储；同一幂等键重放返回同一新版本，跨 owner 返回 404，未 Accepted 源返回 409，周运仍按 `near_seven` 的付费闸门校验。

## 验收命令

```bash
uv run --project backend pytest \
  backend/tests/test_readings_api.py \
  backend/tests/test_reading_migrations.py \
  backend/tests/test_fulfillment.py \
  backend/tests/test_migrations.py \
  backend/tests/test_commerce_models.py -q
# 71 passed

uv run --project backend ruff check --config backend/pyproject.toml \
  backend/app/readings backend/app/commerce backend/app/api/readings.py \
  backend/tests/test_readings_api.py backend/tests/test_fulfillment.py \
  backend/alembic/versions/0022_followup_contract.py
# All checks passed!

uv run --project backend mypy --config-file backend/pyproject.toml \
  backend/app/readings backend/app/commerce backend/app/api/readings.py
# Success: no issues found in 32 source files

uv run --project backend pytest \
  backend/tests/test_readings_api.py \
  backend/tests/test_dogfood_entitlements.py \
  tests/contract/test_openapi_contract.py \
  backend/tests/test_openapi_alignment.py -k 'recast or openapi' -q
# 16 passed

npm --prefix web test -- --run src/test/api-readings.test.ts
# 5 passed
```

## 未覆盖边界

该证据只证明本地 Reading/API/迁移和付费绑定边界。真实权益账本消费与 Fulfillment Worker/API 仍未接线，Recast 尚未覆盖未发布术数的算法能力，PNG/PDF renderer、真实支付和生产环境门禁也未完成，因此 P11-005 继续为 `IN_PROGRESS`。
