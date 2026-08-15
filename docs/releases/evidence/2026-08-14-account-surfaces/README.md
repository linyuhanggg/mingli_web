# 2026-08-14 账户商业与邀请私有投影证据

范围：正式账户页的 owner-scoped 订单/履约、追加式权益账本和邀请活动进度读面。

## 已接通

- `GET /api/v1/account/orders` 只读取当前 device session 的订单，返回商品标签、金额/币种、订单状态、履约状态和时间；不返回支付渠道交易号、其他用户订单或 owner UUID。
- `GET /api/v1/account/entitlements` 只读取当前账户的追加式 `EntitlementEventRecord`，服务端按账本顺序投影可用、发放、预留、消费、释放、冲正和过期数量；事件投影不返回 source ref、支付标识或其他账户记录。
- `GET /api/v1/account/referrals` 只读取当前账户作为 inviter/referred 的活动进度；前台只展示自己的活动、active 邀请码、邀请计数、归因阶段和奖励状态，不展示关联用户、奖励数量、支付尝试或内部 UUID。
- Web 正式 `/account/orders`、`/account/entitlements`、`/account/invitations`、`/account/invites`、`/account/settings` 和 `/account/settings/security` 复用会话门控；旧 `/account/data-rights` 复用真实数据权利表面。未登录不请求私有列表，服务端 401/失败/空数据保持明确状态；页面不生成公开归因链接或本地余额。安全页调用既有 revoke-all 会话命令，设置页只列出已有真实入口。
- 冻结用户 OpenAPI 已包含三个账户读取接口和对应的额外字段禁止响应 schema。

## 验证

```text
Backend account commerce/referral/OpenAPI: 7 passed
Backend full: 714 passed, 92 skipped
Backend Ruff: All checks passed
Backend mypy: Success, no issues found in 130 source files
Web account commerce/referral/security/settings/routes: 14 passed
Web full: 67 files, 427 tests passed
Web typecheck/lint/production build: passed
Admin full: 33 files, 121 tests passed; lint/typecheck/production build passed
```

## 边界

本证据只覆盖本地服务与 UI 读投影。P8-007 仍不是完成态：访客 `/invite/[code]` 的身份归因、公开邀请链接生命周期、真实活动运营和生产通知尚未完成。P7-001/P7-002/P7-007 仍等待真实 Catalog/支付渠道/通知供应商与生产 worker；P7-008 私有媒体和对象存储、P4-006/P4-007 视觉与用户批准、P12 外部发布/凭据/恢复/支付门禁均未被本地测试替代。
