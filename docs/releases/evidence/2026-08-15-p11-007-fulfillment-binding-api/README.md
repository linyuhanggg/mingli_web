# P11-003/P11-005 本地 Fulfillment 创建与绑定 API

日期：2026-08-15

## 本轮完成

- 新增 owner-scoped `POST /api/v1/readings/{reading_version_id}/fulfillment`。
- 只允许已登录用户；Reading Version、Reading Job 和已确认 Payment 必须属于同一用户。
- 接口先拦截 `failed`、`canceled`、`stopped`、`runtime_unknown` 终止任务，再由 Commerce 负责一次性 `RESERVE` 和 Job 绑定。
- `Idempotency-Key` 在订单范围内生效；首次返回 `201`，重复绑定返回 `200`，不会重复扣权益。
- OpenAPI、请求/响应 schema、CSRF、错误映射和服务层均已同步。

## 本地验证

```text
backend/tests/test_fulfillment.py       8 passed
tests/contract/test_openapi_contract.py 12 passed
make check                              Backend 908 passed / 110 skipped
                                         Web 71 files / 448 tests
                                         Admin 33 files / 121 tests
                                         Ruff / mypy / lint / typecheck / build passed
```

负向回归覆盖跨用户 Payment、游客调用、终止 Job 和重复幂等调用；终止 Job 在权益预留前失败，不留下 `RESERVE`。

## 边界

这是本地真实数据库服务层和 API 接线，不是支付渠道验签、生产权益账本、生产 Worker 或公开生产上线证明。测试服务器仍保持 `local + Fake`，未把本接口写成真实支付完成。

本证据不包含个人出生资料、姓名、密码、SMTP 凭据、API key 或其他秘密。
