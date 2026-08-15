# P8-007 公开邀请归因本地纵切片

日期：2026-08-14

## 已接通

- `/invite/[code]` 读取真实 `GET /api/v1/referrals/{code}`，只展示服务端活动版本、状态、时间和每邀请人规则；状态明确区分 planned、active、paused、full、ended 和无效码。
- 活动中的访客可用 guest session + CSRF 记录临时归因，也可以幂等清除；重复访问不会制造第二条临时记录。公开响应不返回 inviter、visitor hash、受邀用户或内部 UUID。
- 新用户在同一 guest session 完成 OTP 登录/注册后，服务端只锁定最后一个仍有效的邀请码；旧链接、无效/暂停/结束活动、自邀和既有账户不会写入永久归因。账户创建不因无效邀请失败。
- Admin 活动事实漏斗补充临时归因数量；账户 `/account/referrals`、通知和订单/权益仍保持 owner-scoped 私有投影。
- 静态用户 OpenAPI 与 Web API 客户端同步，公开写接口继续要求 guest CSRF。

## 验收命令

```text
Backend public referral/auth/account/referral/OpenAPI regression: 52 passed
Backend public referral/Admin targeted: 2 passed
Backend OpenAPI contract: 10 passed
Backend Ruff: All checks passed
Backend mypy: Success: no issues found
Backend full via `make check`: 728 passed, 92 skipped
Web invite wiring: 3 passed
Web full via `make check`: 68 files, 431 tests passed
Web typecheck: passed
Admin full via `make check`: 33 files, 121 tests passed
Admin referral wiring: 2 passed
Web/Admin lint, typecheck and production build: passed
Current working-tree browser smoke: Web 85 passed / 7 skipped; Admin 48 passed / 4 skipped
Governance contracts: 11 passed
```

## 未覆盖边界

这份证据只证明本地 FastAPI + SQLite、静态 OpenAPI 和 Web/Admin 代码的事实边界，不把本地测试冒充生产验收。P8-007 仍为 `IN_PROGRESS`：真实身份会话、支付奖励确认、通知供应商与 Worker、生产活动数据库/运营数据、完整站内事件覆盖、P4-007 用户批准以及 P12 的生产凭据、恢复、支付和发布门禁仍未完成。外部用户没有批准前，不新增未批准的前台运营页面合同。
