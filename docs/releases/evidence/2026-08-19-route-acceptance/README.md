# 2026-08-19 G6 / §18 全站路由验收证据

本目录对应 `ba41648e7f30f030b46f61704ecd35f11b9fe081` 之上的当前工作树。Web 与 Admin 使用 Playwright 调用系统 Google Chrome，在 standalone 生产构建上逐路检查 360×800、768×1024、1024×768、1440×900 四档视口；本地 API、Worker 与隔离 PostgreSQL 使用签名 Runtime release `c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`。这份自动化证据已就绪，仍待用户逐页验收。

## 结果

| 范围 | 唯一路由 / 状态 | 视口 | 实测记录 | 最终失败 |
| --- | ---: | ---: | ---: | ---: |
| Web 正常路由 | 71 | 4 | 284 | 0 |
| Admin 正常路由 | 40 | 4 | 160 | 0 |
| UI Lab 七态专项 | 7 | 4 | 28 | 0 |
| 正式工作台组件布局 | 1 | 4 | 4 | 0 |
| `/bazi` 真实 Runtime owner result | 1 | 4 | 4 | 0 |

根报告为 [`report.json`](./report.json)。它包含 444 条逐路由逐视口实测记录和总 `failures[]`；最终状态为 `evidence-ready-user-acceptance-pending`，`failures=[]`。正常路由截图位于 [`web/`](./web/) 与 [`admin/`](./admin/)，每档 JSON 均保留 route、最终路径、HTTP 状态、viewport、状态、布局、可访问性、reduced motion、禁词检查、截图和逐路失败。

## 路由清单

Web 71 条：

`/`、`/about`、`/account`、`/account/data-rights`、`/account/entitlements`、`/account/history`、`/account/history/demo-root`、`/account/invitations`、`/account/invites`、`/account/notifications`、`/account/orders`、`/account/profiles`、`/account/profiles/demo-profile`、`/account/settings`、`/account/settings/preferences`、`/account/settings/privacy-data`、`/account/settings/security`、`/app`、`/app/ask/liuyao`、`/app/bazi`、`/app/fortune/today`、`/app/fortune/week`、`/app/profile/new`、`/app/profiles`、`/app/readings`、`/app/readings/demo-reading`、`/arts`、`/auth/consent`、`/auth/login`、`/auth/recover`、`/auth/register`、`/auth/set-password`、`/auth/verify`、`/bazi`、`/bazi/hepan`、`/canwen`、`/checkout`、`/checkout/demo-order`、`/daily`、`/daliuren`、`/fengshui`、`/hecan`、`/invite/demo-code`、`/jianxiang`、`/library`、`/library/demo-article`、`/liuyao`、`/luming-nayin`、`/meihua`、`/methodology`、`/pricing`、`/privacy`、`/qimen`、`/qizheng`、`/qizheng/hepan`、`/selection`、`/share/demo-share`、`/support`、`/taiyi`、`/terms`、`/tools`、`/tools/chart-similarity`、`/tools/dream`、`/tools/five-elements`、`/tools/name`、`/tools/rhythm`、`/tools/time-check`、`/wenshi`、`/workbench/demo-handle`、`/ziwei`、`/ziwei/hepan`

Admin 40 条：

`/`、`/appeals`、`/audit`、`/capabilities`、`/charts`、`/cms/daily`、`/cms/help`、`/cms/library`、`/cms/pages`、`/cms/policies`、`/cms/tools`、`/dashboard`、`/data-rights`、`/entitlements`、`/health`、`/login`、`/model-profiles`、`/notifications`、`/observations`、`/orders`、`/payments`、`/products`、`/products/demo/versions`、`/reading-jobs`、`/readings`、`/readings/demo`、`/reconciliation`、`/referrals`、`/referrals/demo`、`/refunds`、`/runtime`、`/sessions`、`/settings`、`/staff`、`/subjects`、`/subjects/demo`、`/support-cases`、`/users`、`/users/demo`、`/verifications`

## 判据与实测

- 页面级横向溢出上限为 `window.innerWidth + 1px`；444 条记录的最大 `overflowPx=0`。
- 444 条记录均有且仅有一个可见 `h1`，各有一个 Skip Link；首次 Tab 聚焦、可见焦点、未被 sticky 遮挡和 Enter 后目标获焦均为 0 失败。
- 444 条记录在 `prefers-reduced-motion: reduce` 下长动画最大值为 0，内容保留失败为 0。
- 444 条正常路由的 Fixture、raw JSON、snake_case 和 FateRadar 旧品牌命中记录均为 0。
- 正常稳定快照自然覆盖 `empty=128`、`error=24`、`processing=80`、`unavailable=36`、`unauthorized=84`。瞬态 `loading` 与冻结态 `locked` 没有为凑数强塞进正常路由。
- 七态库存另在 [`ui-lab-fixture-states/`](./ui-lab-fixture-states/) 对 `loading / empty / error / processing / unavailable / unauthorized / locked` 各跑四视口。每条均标记 `fixtureOnly=true`、`countedAsNormalPass=false`，不计入 444 条正常通过。
- 同一专项用正式 `WorkbenchShell + ReadingShell` 测工作台：360/768 单栏；1024 为盘面 520px、右侧阅读 430px；1440 右侧阅读 846px。双栏最小右侧宽度为 430px，满足 `>=360px`。该容器仍属于 UI Lab Fixture 专项，不冒充正常数据路由。
- [`runtime-bazi-owner-result/report.json`](./runtime-bazi-owner-result/report.json) 记录真实 `/bazi` 填写、ProfileVersion、preview、Worker、owner result 四视口链；`productDataBoundary=signed-runtime-release-owner-result`，release SHA 为 `c451de5e…993c4b`，`failures=[]`。768/1440 可见结构事实均为 `77 >= 33`，并保留证据抽屉键盘检查和同视口参考图。

## 与 2026-08-14 版的差异

- Web 路由从 66 增至 71，新增当前库存中的 `/fengshui`、`/luming-nayin`、`/meihua`、`/selection`、`/taiyi`；Admin 仍为 40 条。
- 旧版主要记录 HTTP、关键浏览器错误与横向溢出；本版逐条追加唯一 h1、Skip Link、焦点可见与无遮挡、键盘目标、reduced motion、禁用表面文本和 canonical state。
- 旧版后端未启动，只能看到真实 unavailable 降级；本版连接隔离的真实 API/Worker/PostgreSQL，Admin 以临时本地员工真实登录，并另跑签名 Runtime 的 `/bazi` owner result。
- 本版把 UI Lab 状态库存明确隔离，Fixture 不计正常路由通过；同时增加工作台实际列宽记录与根聚合报告。

## 本轮失败与修复

最终 `failures[]` 为空。首轮审计如实发现并在本轮修复后重跑：四个工具页缺唯一 h1；`/jianxiang` 直接显示观察枚举内部键；Admin `/login` 缺 Skip Link；`/capabilities`、`/sessions`、`/audit` 与 `/observations` 暴露内部键或 Fixture 字样。另有 Skip Link 动画尚未结束便采样造成的误报，修正为等待既有 180ms 动画结束后检测，没有修改阈值。

## 复现口径

正常路由使用 `web/e2e/route-matrix.spec.ts` 与 `admin/e2e/route-matrix.spec.ts`，Playwright 配置自动寻找 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`。Admin 证据运行时通过环境变量注入临时本地员工凭据；凭据不写入仓库。UI Lab 仅在开发态设置 `UI_LAB_E2E=1` 后运行 `web/e2e/ui-lab-state-inventory.spec.ts`。根报告复现命令：

```bash
EXPECTED_RELEASE_MANIFEST_SHA256=c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b \
node scripts/build-route-acceptance-report.mjs
```

## 边界

这份证据只证明当前本地工作树的机器可判定门和真实签名 Runtime 接线，不代表生产部署、真实 Model/OTP/Payment、付费深读上线或用户批准。`/liuyao`、`/meihua` 仍维持 B 档且等待用户裁决。2026-08-19 测试服务器发布的授权来源仍待用户确认，本轮未 push、未上传、未部署，也未切换 `/opt/fateradar/current`。
