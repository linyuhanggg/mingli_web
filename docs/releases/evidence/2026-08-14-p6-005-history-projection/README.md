# P6-005 账户历史 Root/Version 投影证据

状态：`automated-only`。本证据覆盖本地可验证的账户历史 API、静态 OpenAPI 合同和正式账户历史页面接线；不替代真实用户历史数据、ChartTask 生产模型、导出/删除关联或 P4/P12 外部验收。

## 本轮闭环

- 新增设备会话专用 `GET /api/v1/account/history`。
- 服务端按当前 User 所拥有的 ReadingRoot 分组，并在每个 Root 下按版本号倒序返回 ReadingVersion 公共摘要。
- 账户历史响应不返回 `prior_answer`、`input_request`、运行时令牌、密文或其他私有准备载荷。
- 旧的 `GET /api/v1/readings` 平列表保持不变，访客和兼容入口不被账户专用会话合同改写。
- `/account/history` 登录后改读账户投影；未登录仍在会话门控处结束，不发历史请求。
- 账户历史页面保留 Root 分组，并在组内按版本号展示旧版与当前版；兼容平列表页面不变。
- 跨用户 Root 不进入当前账户响应；未验证设备返回 401。

## 定向证据

```text
uv run --project backend pytest backend/tests/test_account_history.py tests/contract/test_openapi_contract.py -q
11 passed

npm --prefix web test -- --run src/test/account-history-wiring.test.tsx src/test/private-surfaces.test.tsx src/test/archive-pages.test.tsx
25 passed
```

P6-005 仍保持 `IN_PROGRESS`：当前只证明本地真实持久化模型和账户页面的安全投影，尚未证明生产 ChartTask 聚合、真实账户数据、导出/删除队列关联以及 P4/P12 外部门禁。
