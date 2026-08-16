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

## 2026-08-16 账户导航重构补充

本轮按消费 App「我的」页重新整理账户区：桌面端移除永久侧边栏，改为顶部账户导航；移动端保留底部导航；身份卡改为浅色信息卡；入口拆成「主要入口」和「账户工具」；账户页不显示共享私域壳里的「返回公共首页」动作，普通 `/app` 页面仍保留它；登录、权限、URL、接口和账户数据边界不变。`/app` 仍保留原有私人应用侧栏，不受本轮账户页布局影响。

### 本轮门禁

| 项目 | 结果 |
|---|---|
| `cd web && npm run lint` | 通过 |
| `cd web && npm run typecheck` | 通过 |
| `cd web && npm test` | 通过，72 files / 456 tests |
| `cd web && npm run build` | 通过，Next.js 16.3.0 |
| `git diff --check` | 通过 |
| Impeccable mechanical detector | 通过，0 findings |

### 本轮浏览器证据

- 服务：`http://127.0.0.1:3000`，系统 Chrome；视口为 360、768、1024、1440。
- 测试上下文：浏览器测试临时拦截账户接口，返回虚构的 `q***@example.com` 登录态和空历史响应；没有写入真实账户、订单、历史或权益数据。
- 四个视口均满足 `document.documentElement.scrollWidth === innerWidth`；桌面端没有账户侧边栏，移动端使用账户底部导航；桌面顶部账户导航在 768、1024、1440 视口可见。
- 截图：`web/e2e/screenshots/audit-2026-08-14/phase3-account/360.png`、`768.png`、`1024.png`、`1440.png`。

### 发布边界

- 测试服务器 `fateradar-prod` 已切换到 `/opt/fateradar/releases/ui-preview-20260816-account-nav`，`fateradar-test-web` 为 active；只重启了 Web，API、Worker、Admin 沿用原进程。
- 发布前清理了 30 个旧测试 release 和明确的可再生缓存，保留当前前一版 Web release 与 API 正在使用的最近回滚版。根盘从只剩约 99MB 恢复到可用约 27GB。
- `http://106.14.10.235:18080/account` 返回 200，HTML 有 `h1=我的` 且不含「返回公共首页」；页面引用的 5 个 CSS 资源均正常。
- 公网 Chrome 360、768、1024、1440 四档均无横向溢出、无关键资源 4xx、无页面错误；服务器实拍截图为 `web/e2e/screenshots/audit-2026-08-14/phase3-account/server-360.png`、`server-768.png`、`server-1024.png`、`server-1440.png`。
- 生产域名 `https://fateradar.cn/` 没有修改。阶段 3 仍是「证据就绪，待用户验收」，服务器部署完成不等于用户验收完成。
