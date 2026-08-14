# 阶段 3 报告：账户区「我的」重建

日期：2026-08-15（Asia/Shanghai）
状态：**证据就绪，待用户验收**
阶段 3 主提交：`192a534`

## 范围

- `/account` 改为消费 App「我的」页：身份卡、账号状态、权益摘要和六个现有账户入口。
- 保留 guest / signed-in / checking / error 会话状态、OTP 登录、当前设备退出和隐私边界。
- 登录态历史复用 `ReadingHistory accountScoped`，状态来自服务端 ReadingRoot/ReadingVersion 摘要，不生成待办或权益假数据。
- 账户子页继续复用既有 API、RBAC 和 `SecondaryStatus` / `StatusPanel` 门控；统一私域导航首项为「我的」。

## 自动门禁

| 项目 | 结果 |
|---|---|
| `cd web && npm run lint` | 通过，0 warnings |
| `cd web && npm run typecheck` | 通过 |
| `cd web && npm test` | 通过，70 files / 439 tests |
| `cd web && npm run build` | 通过，Next.js 16.3.0 |
| `cd admin && npm run lint` | 通过，0 warnings |
| `cd admin && npm run typecheck` | 通过 |
| `cd admin && npm test` | 通过，33 files / 121 tests |
| `cd admin && npm run build` | 通过 |

## 真实浏览器证据

- 浏览器：系统 Chrome `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`。
- 服务：`http://127.0.0.1:3000`，本地 dev server。
- 路线：`/account`、`/account/profiles`、`/account/history`、`/account/orders`、`/account/notifications`、`/account/settings`、`/account/invites`、`/account/data-rights`。
- 视口：360、768、1024、1440；共 8 路线 × 4 视口 = 32 组。
- 证据目录：`web/e2e/screenshots/audit-2026-08-14/phase3/`；截图 32 张，机器报告 `report.json`。
- 通过项：每页一个可见 `main` 和 `h1`；`/account` h1 为「我的」、游客身份卡和六个入口可见；账户子页显示「需要登录」；32 组 `scrollWidth === innerWidth`；无 page error。
- 状态边界：本机没有监听 8000 端口，真实 rewrite 请求返回 500；审计上下文因此明确拦截账户探测为 401、游客会话为 CSRF 响应，只验证真实 Chrome 渲染的游客 UI，不注入用户、订单、历史或权益数据。该限制已写入 `phase3/report.json`，不代表真实账户态已验收。

## 待验收边界

本报告记录本地自动化与真实浏览器游客态证据，不代表用户批准。阶段 3 状态保持「证据就绪，待用户验收」，不得写成 `USER_ACCEPTED` 或公开上线。真实 signed-in 数据、后端可用性、支付/权益和逐页用户批准仍是独立门禁。
