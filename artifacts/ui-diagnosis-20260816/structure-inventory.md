# 前端结构盘点报告（Assessment C）：路由与组件重复/臃肿

- 日期：2026-08-16
- 范围：`web/`（公共 Web，Next.js App Router）、`admin/`（独立后台，Next.js App Router），仓库根 `ui/` 共享样式包
- 方法：全只读（`find`/`wc`/`grep`/`cat`/`diff`），未修改仓库任何文件，未做 git 操作；忽略 `.next`/`node_modules`/`.git`
- 口径：`route.ts` 两包均为 0 个（纯前端，无自建 API 路由；`/api/*` 由 next.config rewrites 代理到后端）

---

## 0. 总览计数

| 指标 | web | admin | 合计 |
|---|---|---|---|
| `page.tsx`（URL 路由） | 67 | 42 | **109** |
| `layout.tsx` | 7 | 1 | 8 |
| `route.ts` | 0 | 0 | 0 |
| 路由文件总数 | **74** | **43** | **117** |
| 组件 `*.tsx`（web/src/components） | 94 文件 / 18,279 行 | 65 文件 / 10,792 行 | — |
| CSS 文件 | 60 文件 / 11,139 行 | 27 文件 / 3,803 行 | — |
| `lib/*.ts` | 19 | 26 | — |
| 测试文件 | 72 | 33 | 105 |

- **结构形态**：web 是「大量 9～17 行薄壳 + 少数实页 + 数据驱动 surface」；admin 是「37 个 5~6 行壳全部转发给唯一调度器 `AdminCatalogPage`」。
- **CSS token 纪律极好**：两包 `globals.css` 均只 `@import "../../../ui/tokens.css"` + `../../../ui/base.css`；web/src 与 admin/src 内 **0 处自定义 CSS 变量定义、0 处硬编码 hex 颜色**——所有设计值都走共享 token。冗余主要在「同一语义类名在多个 module 重复实现」与「两包各持一份 ui 组件库副本」。

---

## 1. 路由全量盘点

### 1.1 Web 公共品牌/内容页（Category A，14 路由）

| URL | 文件 | 行数 | 主要 import 组件 | 职责一句话 |
|---|---|---|---|---|
| `/` | `web/src/app/page.tsx` | 199 | `PublicCmsProjection`、`PublicPageShell`、`ButtonLink`、`PRODUCT_CATALOG` | 首页：术数卡片目录（命盘/事件/见相/合参/辅助五组）+ 已发布公告 |
| `/about` | `about/page.tsx` | 38 | `EditorialPage`、`StatusPanel`、`PublicCmsProjection` | 关于与边界（品牌未冻结占位） |
| `/arts` | `arts/page.tsx` | 46 | `PublicPageShell`、`PRODUCT_CATALOG`、`ProductList` | 术数总览目录页（含三术合盘入口） |
| `/methodology` | `methodology/page.tsx` | 73 | `EditorialPage`、`PublicCmsProjection` | 方法与边界（先算再讲管线说明） |
| `/privacy` | `privacy/page.tsx` | 59 | `EditorialPage`、`PolicyMeta`、`PublicCmsProjection` | 隐私政策（开发期说明） |
| `/terms` | `terms/page.tsx` | 55 | `EditorialPage`、`PolicyMeta`、`PublicCmsProjection` | 服务条款（开发期草稿） |
| `/support` | `support/page.tsx` | 51 | `EditorialPage`、`StatusPanel`、`PublicCmsProjection` | 帮助与支持边界说明 |
| `/pricing` | `pricing/page.tsx` | 69 | `EditorialPage`、`StatusPanel` | 价格与交付（测试期展示） |
| `/daily` | `daily/page.tsx` | 15 | `PublicContentSurface`、`publicContentSurfaces` | 每日确定性内容入口 |
| `/library` | `library/page.tsx` | 15 | `PublicContentSurface` | 知识内容索引 |
| `/library/[slug]` | `library/[slug]/page.tsx` | 16 | `PublicContentSurface` | 知识文章详情 |
| `/tools` | `tools/page.tsx` | 15 | `PublicContentSurface` | 工具总览索引 |
| `/_ui-lab`（`%5Fui-lab`） | `%5Fui-lab/page.tsx` | 9 | `UiLab` | 开发期 UI 实验室（production 下 notFound） |
| `/workbench/[handle]` | `workbench/[handle]/page.tsx` | 29 | `PublicPageShell`、`Status`、`lucide` | 任务恢复页（服务未接通，占位） |
| （壳）`/` root layout | `layout.tsx` | 41 | `AccountSessionProvider`、`RouteScrollPolicy`、SWR | 全局布局：会话、滚动策略、字体、globals |

### 1.2 Web 公共产品/工具页（Category B，19 路由）

**B1 术数公开入口——14 个 9 行薄壳，全部只渲染 `<ProductTaskPage productId="X"/>`**

| URL | 文件 | 行数 | 唯一差异 |
|---|---|---|---|
| `/bazi` | `bazi/page.tsx` | 9 | `productId="bazi"` |
| `/liuyao` | `liuyao/page.tsx` | 9 | `productId="liuyao"` |
| `/ziwei` | `ziwei/page.tsx` | 9 | `productId="ziwei"` |
| `/daliuren` | `daliuren/page.tsx` | 9 | `productId="daliuren"` |
| `/qimen` | `qimen/page.tsx` | 9 | `productId="qimen"` |
| `/meihua` | `meihua/page.tsx` | 9 | `productId="meihua"` |
| `/taiyi` | `taiyi/page.tsx` | 9 | `productId="taiyi"` |
| `/qizheng` | `qizheng/page.tsx` | 9 | `productId="qizheng"` |
| `/fengshui` | `fengshui/page.tsx` | 9 | `productId="fengshui"` |
| `/jianxiang` | `jianxiang/page.tsx` | 9 | `productId="jianxiang"` |
| `/hecan` | `hecan/page.tsx` | 9 | `productId="hecan"`（原多盘问答并入） |
| `/wenshi` | `wenshi/page.tsx` | 9 | `productId="wenshi"` |
| `/luming-nayin` | `luming-nayin/page.tsx` | 9 | `productId="luming-nayin"` |
| `/selection` | `selection/page.tsx` | 9 | `productId="selection"` |

每页唯一实际内容 = `metadata`（title/description 各一条）+ 一行 JSX。共同壳 `ProductTaskPage`（44 行）+ 工作台 `ProductTaskExperience`（638 行）。

**B2 合盘入口——3 个 11 行薄壳，只渲染 `<RelationshipTaskPage productId="X"/>`**

| URL | 文件 | 行数 | 差异 |
|---|---|---|---|
| `/bazi/hepan` | `bazi/hepan/page.tsx` | 11 | `productId="bazi"` |
| `/ziwei/hepan` | `ziwei/hepan/page.tsx` | 11 | `productId="ziwei"` |
| `/qizheng/hepan` | `qizheng/hepan/page.tsx` | 11 | `productId="qizheng"` |

**B3 工具动态路由（一页两职）**

| URL | 文件 | 行数 | 主要 import | 职责 |
|---|---|---|---|---|
| `/tools/[tool]` | `tools/[tool]/page.tsx` | 66 | `FiveElementsFactsFlow`/`RhythmFactsFlow`/`ChartSimilarityFlow`/`TimeCheckFlow`/`PublicContentSurface`/`getToolContentSource` | ①4 个特殊工具名硬编码返回真实 React 流程；②其余工具走 CMS surface |

**B4 迁移重定向**

| URL | 文件 | 行数 | 职责 |
|---|---|---|---|
| `/canwen` | `canwen/page.tsx` | 14 | 页面级 `redirect("/hecan")` 兜底（另有 next.config 永久重定向） |

### 1.3 Web 私有应用页 app/*（Category C，10 路由）

| URL | 文件 | 行数 | 职责 |
|---|---|---|---|
| `/app`（layout） | `app/layout.tsx` | 18 | `PrivateShell` 私有壳 + noindex + force-dynamic |
| `/app` | `app/page.tsx` | 6 | `redirect("/account")`（legacy） |
| `/app/bazi` | `app/bazi/page.tsx` | 6 | `redirect("/bazi")`（legacy） |
| `/app/ask/liuyao` | `app/ask/liuyao/page.tsx` | 6 | `redirect("/liuyao")`（legacy） |
| `/app/profiles` | `app/profiles/page.tsx` | 6 | `redirect("/account/profiles")`（legacy） |
| `/app/profile/new` | `app/profile/new/page.tsx` | 6 | `redirect("/account/profiles")`（legacy） |
| `/app/readings` | `app/readings/page.tsx` | 6 | `redirect("/account/history")`（legacy） |
| `/app/readings/[readingId]` | `app/readings/[readingId]/page.tsx` | 11 | `redirect("/account/history/[readingId]")`（legacy） |
| `/app/fortune/today` | `app/fortune/today/page.tsx` | 16 | `FortuneFlow` mode="today"（**唯一真实私有页之一**） |
| `/app/fortune/week` | `app/fortune/week/page.tsx` | 16 | `FortuneFlow` mode="week" |

> 注：`next.config.ts` `legacyRedirects` 已声明 `/app`、`/app/profiles`、`/app/profile/new`、`/app/readings`、`/app/readings/:readingId`、`/app/bazi`、`/app/ask/liuyao` 共 7 条（请求层先于文件路由执行）→ 上面 7 个 legacy 页面文件实际**不可达**；`/app` 还承载 fortune 两个真页，故 `/app` 目录不能整删。

### 1.4 Web 账号与商业页（Category D，28 路由）

| URL | 文件 | 行数 | 主要组件 | 职责 |
|---|---|---|---|---|
| `/account`（layout） | `account/layout.tsx` | 18 | `PrivateShell variant="account"` | 个人中心壳 |
| `/account` | `account/page.tsx` | 17 | `AccountCenter`、`AppPageHeader` | 我的（聚合中心） |
| `/account/history` | `history/page.tsx` | 9 | `AccountHistorySurface` | 任务历史列表 |
| `/account/history/[rootId]` | `history/[rootId]/page.tsx` | 17 | `AccountHistorySurface` | 任务版本/报告历史详情 |
| `/account/orders` | `orders/page.tsx` | 9 | `AccountCommerceSurface kind="orders"` | 订单 |
| `/account/entitlements` | `entitlements/page.tsx` | 5 | `AccountCommerceSurface kind="entitlements"` | 权益 |
| `/account/notifications` | `notifications/page.tsx` | 9 | `AccountNotificationsSurface` | 通知 |
| `/account/invites` | `invites/page.tsx` | 9 | `AccountReferralsSurface` | 邀请 |
| `/account/invitations` | `invitations/page.tsx` | 5 | `AccountReferralsSurface` | **= invites 重复** |
| `/account/profiles` | `profiles/page.tsx` | 6 | `AccountProfilesSurface` | 档案列表 |
| `/account/profiles/[profileId]` | `profiles/[profileId]/page.tsx` | 10 | `AccountProfileDetailSurface` | 档案详情 |
| `/account/settings` | `settings/page.tsx` | 9 | `AccountSettingsSurface` | 设置 hub |
| `/account/settings/security` | `settings/security/page.tsx` | 5 | `AccountSecuritySurface` | 设备安全 |
| `/account/settings/preferences` | `settings/preferences/page.tsx` | 15 | `NotificationPreferencesForm` | 通知偏好 |
| `/account/settings/privacy-data` | `settings/privacy-data/page.tsx` | 5 | `AccountDataRightsSurface` | **= data-rights 重复** |
| `/account/data-rights` | `data-rights/page.tsx` | 9 | `AccountDataRightsSurface` | 数据权利 |
| `/auth`（layout） | `auth/layout.tsx` | 14 | — | noindex + force-dynamic |
| `/auth/login` | `auth/login/page.tsx` | 39 | `PasswordLoginForm`、`SecondarySurfaceFrame` | 密码登录 |
| `/auth/register` | `auth/register/page.tsx` | 38 | `RegistrationForm` | 注册 |
| `/auth/recover` | `auth/recover/page.tsx` | 36 | `PasswordRecoveryForm` | 找回账号 |
| `/auth/verify` | `auth/verify/page.tsx` | 34 | `OtpForm` | OTP 验证 |
| `/auth/consent` | `auth/consent/page.tsx` | 34 | `ConsentForm` | 政策同意 |
| `/auth/set-password` | `auth/set-password/page.tsx` | 33 | `PasswordSetForm` | 设置密码 |
| `/checkout` | `checkout/page.tsx` | 10 | `CommerceSurface` | 订单确认 |
| `/checkout/[orderId]` | `checkout/[orderId]/page.tsx` | 11 | `CommerceSurface` | 订单详情 |
| `/checkout`（layout） | `checkout/layout.tsx` | 14 | — | noindex 壳 |
| `/share/[shareId]` | `share/[shareId]/page.tsx` | 14 | `SharedReadingSurface` | 分享报告 |
| `/share`（layout） | `share/layout.tsx` | 14 | — | noindex 壳 |
| `/invite/[code]` | `invite/[code]/page.tsx` | 14 | `InviteSurface` | 邀请链接 |
| `/invite`（layout） | `invite/layout.tsx` | 14 | — | noindex 壳 |

### 1.5 Admin 页（Category E，42 路由）

| URL | 文件 | 行数 | 内容 |
|---|---|---|---|
| `/`（layout） | `layout.tsx` | 37 | Admin root layout |
| `/` | `page.tsx` | 5 | `redirect("/dashboard")` |
| `/login` | `login/page.tsx` | 78 | 真实登录页（唯一大页） |
| `/dashboard` | `dashboard/page.tsx` | 5 | `AdminOverviewPage` |
| `/[...segments]` | `[...segments]/page.tsx` | 5 | `notFound()` 兜底 |
| `/_ui-lab`（`%5Fui-lab`） | `%5Fui-lab/page.tsx` | 18 | `AdminUiLabWorkbench` |
| `/users` `/users/[id]` | 2 文件 | 5/6 | `AdminCatalogPage` |
| `/subjects` `/subjects/[id]` | 2 文件 | 5/6 | 同上 |
| `/referrals` `/referrals/[id]` | 2 文件 | 5/6 | 同上 |
| `/readings` `/readings/[id]` | 2 文件 | 5/6 | 同上 |
| `/products` `/products/[id]/versions` | 2 文件 | 5/6 | 同上 |
| `/cms/daily` `/cms/help` `/cms/library` `/cms/pages` `/cms/policies` `/cms/tools` | 6 文件 | 各 5 | 同上 |
| `/appeals` `/audit` `/capabilities` `/charts` `/data-rights` `/entitlements` `/health` `/model-profiles` `/notifications` `/observations` `/orders` `/payments` `/reading-jobs` `/reconciliation` `/refunds` `/runtime` `/sessions` `/settings` `/staff` `/support-cases` `/verifications` | 21 文件 | 各 5 | 同上 |

**Admin 壳内容完全一致**：`import { AdminCatalogPage } ... return <AdminCatalogPage pathname="/xxx" />`（详情页多一行取 `params.id`）。共 **37 个壳**，唯一变化是字符串 pathname。

---

## 2. 重复与结构臃肿侦查（带代码证据）

### 2.1 “同一内容多种裸露方式”

**① 术数公开入口：14 壳 = 同一个 6 行模板 × 14**（证据 §1.2-B1）
每个文件逐字重复：
```tsx
import { ProductTaskPage } from "@/components/task/product-task-page";
export default function XxxPage() {
  return <ProductTaskPage productId="xxx" />;
}
```
`/tools/[tool]` 动态页（§1.2-B3）与这 14 个顶层术数路由**并存**，但机制不同：前者吃 CMS product 数据，后者吃 `ProductTaskPage` 组件树。两类都是“产品入口”，存在收敛为 `[product]` 动态段的可能（详见重构候选 R4）。`hecan/wenshi` 另在首页、`/arts` 中以同名卡重复列示。

**② app/* 旧路由：双份重定向**（证据 §1.3）
- `web/next.config.ts` `legacyRedirects`（7 条 + `/canwen` 1 条 = 8 条）在请求层生效；
- 同路径下仍保留 8 个 `page.tsx` 页面级 `redirect()`，且 `legacy-app-route-contract.test.ts`（76 行）逐一断言。App Router 下 config redirect 先于文件系统路由，**7 个 legacy `/app/*` 页面文件不可达**（`/app` 目录还含 fortune 真页，不可整删）。`canwen/page.tsx` 注释自述“next.config.ts 已在请求层…页面级 redirect 作为深链兜底”——双保险是刻意的，但 `/app/*` 这 7 条并非。

**③ /account 平行重复（2 组）**

| 组 | 页面 A | 页面 B | 证据 |
|---|---|---|---|
| 邀请 | `/account/invites`（9 行） | `/account/invitations`（5 行） | `diff` 结果仅差 `metadata` 块与函数名；都 `return <AccountReferralsSurface />` |
| 数据权利 | `/account/settings/privacy-data`（5 行） | `/account/data-rights`（9 行） | 同上；都 `return <AccountDataRightsSurface />` |

并且这两组重复路由被写进了**契约测试**（`secondary-route-inventory.test.ts` `requiredRoutes` 第 27/28、33/34 行 → 两套 URL 都成了“必须存在”的必需路由），清理时需同步改测试清单。

**④ `/arts`（46 行）与首页（`/` 199 行）目录内容同源**：两页都 import 同一 `PRODUCT_CATALOG`（`NATAL_PRODUCTS/EVENT_PRODUCTS/CROSS_PRODUCTS/OBSERVATION_PRODUCTS`），各实现一套卡片渲染（`home.module.css` 卡片梯度 vs `arts.module.css` 列表），视觉 DOM 两套，数据一份。

**⑤ `/library` 与编辑类页面**：web `/library`（PublicContentSurface）与 admin `/cms/library`（AdminCmsSurface prefix="library"）指向同源 CMS 内容（读 vs 管），分属两包、职责分离，**不算重复**（仅收录确认）。

### 2.2 “一行壳”清单（行数 < 40 且只 re-export 一个通用组件）

**web（共 51 个）**

| 壳类型 | 数量 | 行数 | 通用组件 |
|---|---|---|---|
| 术数公开入口 | 14 | 9 | `ProductTaskPage` |
| 合盘入口 | 3 | 11 | `RelationshipTaskPage`（包 Suspense） |
| legacy redirect | 7 | 6–11 | `redirect()` |
| `/canwen` redirect | 1 | 14 | `redirect()` |
| fortune | 2 | 16 | `FortuneFlow` |
| Account 子页 | 13 | 5–17 | `Account*Surface` / `AccountCommerceSurface` / `AccountDataRightsSurface` / `AccountReferralsSurface` |
| 内容壳 | 4 | 15–16 | `PublicContentSurface` |
| checkout / share / invite | 4 | 10–14 | `CommerceSurface` / `SharedReadingSurface` / `InviteSurface` |
| `/_ui-lab` | 1 | 9 | `UiLab` |
| **小计** | **49** | — | web 67 页中 49 个为薄壳（73%） |

**admin（37 个）**：全部 ≤ 6 行，全部 `AdminCatalogPage`.

### 2.3 组件肥胖榜 Top 25

**web/src/components（按行数）**

| # | 文件 | 行数 | 判定 |
|---|---|---|---|
| 1 | `readings/runtime-chart.tsx` | 1433 | **上帝组件**：报告图表渲染总成（时序/柱/盘等多图全家桶 + 交互 + 布局于一文件） |
| 2 | `task/product-input-form.tsx` | 1046 | **上帝组件**：14 术数统一输入表单（表单状态 / 校验 / 分术分支 / 提交 全内联） |
| 3 | `relationship/relationship-task-page.tsx` | 709 | **上帝组件**：3 术合盘全流程（表单+创建+结果+纠错回执） |
| 4 | `readings/reading-result.tsx` | 691 | **上帝组件**：报告正文/披露/追问/核对一体 |
| 5 | `task/product-task-experience.tsx` | 638 | **上帝组件**：产品任务状态机（输入→提交→结果 三态聚合） |
| 6 | `ui/primitives.test.tsx` | 592 | 测试文件（≈与 admin 同文件重复） |
| 7 | `profile-form.tsx` | 569 | 大件：档案表单（可与 input-form 合并复用） |
| 8 | `site-header.tsx` | 527 | 大件：站点头部（导航+会话+品牌 多层） |
| 9 | `liuyao-form.tsx` | 462 | 大件：六爻专项表单（与 product-input-form 职责重叠信号） |
| 10 | `readings/bazi-chart.tsx` | 407 | 大件：八字盘 SVG 渲染 |
| 11 | `time-check-flow.tsx` | 390 | 中件：校时流程 |
| 12 | `readings/need-input-form.tsx` | 361 | 中件 |
| 13 | `otp-form.tsx` | 359 | 中件 |
| 14 | `readings/liuyao-hexagram.tsx` | 336 | 中件 |
| 15 | `dashboard-hub.tsx` | 296 | **疑似死代码**：仅 `private-surfaces.test.tsx` 挂载，无真实页面使用；与 `account-center.tsx`(293) 功能重叠为旧“dashboard 体验” |
| 16 | `ui/table.tsx` | 295 | 通用组件（与 admin 副本 300 行有漂移） |
| 17 | `surfaces/account-notifications-surface.tsx` | 294 | 中件 |
| 18 | `account-center.tsx` | 293 | 中件（真实“我的”聚合；与 dashboard-hub 重叠） |
| 19 | `surfaces/public-content-surface.tsx` | 284 | 中件 |
| 20 | `ui-lab/ui-lab.tsx` | 274 | 开发件 |
| 21 | `surfaces/account-commerce-surface.tsx` | 266 | 中件 |
| 22 | `reading-history.tsx` | 259 | 中件 |
| 23 | `profile-archive.tsx` | 255 | 中件 |
| 24 | `surfaces/account-referrals-surface.tsx` | 236 | 中件 |
| 25 | `fortune-flow.tsx` | 234 | 中件 |

**admin/src/components（按行数）**

| # | 文件 | 行数 | 判定 |
|---|---|---|---|
| 1 | `admin-cms-surface.tsx` | 722 | **上帝组件**：CMS 通用工作台（6 个 CMS 路由共用） |
| 2 | `ui/primitives.test.tsx` | 601 | 测试（≈web 副本） |
| 3 | `admin-catalog-surface.tsx` | 560 | **上帝组件**：通用 Catalog 列表 surface（多数 admin 列表页共用） |
| 4 | `admin-catalog-commands.tsx` | 455 | 大件：命令面板 |
| 5 | `admin-staff-surface.tsx` | 443 | 大件 |
| 6 | `admin-identity-surface.tsx` | 425 | 大件（users/subjects 复用） |
| 7 | `admin-cms-surface.test.tsx` | 403 | 测试 |
| 8 | `admin-reconciliation-surface.tsx` | 357 | 大件 |
| 9 | `admin-catalog-surface.test.tsx` | 306 | 测试 |
| 10 | `ui/table.tsx` | 300 | 通用组件（web 副本 295） |
| 11 | `admin-appeals-surface.tsx` | 299 | 大件 |
| 12 | `admin-support-cases-surface.tsx` | 248 | 中件 |
| 13 | `admin-entitlements-surface.tsx` | 239 | 中件 |
| 14 | `admin-ui-lab-workbench.tsx` | 233 | 开发件 |
| 15 | `admin-referrals-surface.tsx` | 226 | 中件 |
| 16 | `admin-commerce-surface.tsx` | 219 | 中件（orders/payments/refunds 复用） |
| 17 | `admin-notifications-surface.tsx` | 211 | 中件 |
| 18 | `admin-sessions-surface.tsx` | 207 | 中件 |
| 19 | `admin-shell.tsx` | 201 | 壳 |
| 20 | `admin-data-rights-surface.tsx` | 182 | 中件 |
| 21 | `admin-reading-detail-surface.tsx` | 162 | 中件 |
| 22 | `admin-staff-surface.test.tsx` | 151 | 测试 |
| 23 | `admin-identity-surface.test.tsx` | 144 | 测试 |
| 24 | `admin-reading-jobs-surface.tsx` | 140 | 中件 |
| 25 | `admin-reading-detail-surface.test.tsx` | 135 | 测试 |

**上帝组件判定标准**：>600 行且单文件承担（渲染+状态+表单+分派）多职责。web 5 个（runtime-chart / product-input-form / relationship-task-page / reading-result / product-task-experience），admin 2 个（admin-cms-surface / admin-catalog-surface）。

### 2.4 CSS 重复与引用关系

**引用关系（健康）**
- `web/src/app/globals.css` = `@import "../../../ui/tokens.css"; @import "../../../ui/base.css";`（与 admin 完全一致）
- `ui/tokens.css`（104 行，81 个 CSS 变量）+ `ui/base.css`（125 行，reset/排版/滚动条/sr-only/`prefers-reduced-motion`）
- 全仓库组件 CSS **0 处自定义变量、0 处硬编码颜色**；`white`/`black` 命中的全是 `white-space`。
- token 覆盖率抽查：`app-surface.module.css` 153 次 `var()` vs 26 字面 px；`site-chrome` 182 vs 12；`task-shell` 168 vs 25；`admin-catalog-surface` 83 vs 17。字面 px 集中在 `font-size`/`letter-spacing`/`border-width` 等不易 token 化的值，属可接受混合。

**重复/臃肿（问题）**

1. **同一语义类名多文件重复实现**（CSS Modules 不冲突但代码冗余）：

   | 类名 | 出现次数 | 代表文件 |
   |---|---|---|
   | `.field` | 34 | 几乎每个 form 相关 module |
   | `.card` | 29 | home / arts / task-shell / editorial / surfaces… |
   | `.button` | 19 | ui/button + 各业务 module |
   | `.container` | 18 | container + 各页面 |
   | `.hero` | 17 | home / task-shell / editorial / arts… |
   | `.status` | 14 | status + 各 surface |
   | `.item` / `.form` / `.header` / `.section` | 11+ | 各 module |

2. **两处布局类重复定义**：`.accountPage` 同时在 `app-surface.module.css`（第 6 行）与 `secondary-surfaces.module.css`（第 391 行）定义；`dashboard-hub.module.css`（366 行，.hub/.counts/.stateSlot）与 `account-center.module.css`（302 行）是两套“聚合中心”皮肤。
3. **两包各持一份组件库实现而非共享**：`web/src/components/ui/*` 与 `admin/src/components/ui/*` 8 组件 ×2 份（含 `button` 113 vs 109、`table` 295 vs 300、`drawer` 56 vs 64 漂移；`dialog/field/segmented/status/tabs` 一致），外加双份 `primitives.test.tsx`（592/601 行）。根 `ui/` 只含 CSS，**不含 React 组件** → 组件级“复制粘贴”是事实。

**行数最大的 10 个 CSS 文件（web）**

| # | 文件 | 行数 |
|---|---|---|
| 1 | `app-surface.module.css` | 889 |
| 2 | `site-chrome.module.css` | 609 |
| 3 | `ui-lab/ui-lab.module.css` | 590 |
| 4 | `task/task-shell.module.css` | 586 |
| 5 | `private-shell.module.css` | 526 |
| 6 | `surfaces/secondary-surfaces.module.css` | 463 |
| 7 | `dashboard-hub.module.css` | 366 |
| 8 | `app/home.module.css` | 362 |
| 9 | `editorial-page.module.css` | 347 |
| 10 | `relationship/relationship-task-page.module.css` | 303 |

**行数最大的 10 个 CSS 文件（admin）**

| # | 文件 | 行数 |
|---|---|---|
| 1 | `ui/table.module.css` | 402 |
| 2 | `admin-catalog-surface.module.css` | 396 |
| 3 | `ui.module.css` | 266 |
| 4 | `admin-shell.module.css` | 238 |
| 5 | `admin-reconciliation-surface.module.css` | 237 |
| 6 | `admin-cms-surface.module.css` | 231 |
| 7 | `admin-ui-lab-workbench.module.css` | 222 |
| 8 | `admin-staff-surface.module.css` | 192 |
| 9 | `admin-identity-surface.module.css` | 133 |
| 10 | `admin-entitlements-surface.module.css` | 132 |

### 2.5 测试/契约文件与路由对应（只统计数量）

| 项 | web | admin |
|---|---|---|
| 测试文件总数 | 72 | 33 |
| 路由契约测试 | 3（`secondary-route-inventory` 136 行 / `product-route-contract` 107 行 / `legacy-app-route-contract` 76 行） | 2（`admin-route-catalog.test.ts`、`admin-shell-contract.test.ts`，另有 `admin-deployment-contract.test.ts` 属部署契约） |
| 表面契约测试 | `secondary-surfaces.test.tsx`、`ui-lab-contract.test.ts`、`route-scroll-policy` 等 | `admin-catalog-view-model.test.ts`、`admin-permissions.test.ts` |

- 契约与实现**一对一**主要成立：`secondary-route-inventory.test.ts` 用 `existsSync` 断言 requiredRoutes 一一存在，并映射每个路由到 surface 组件——契约质量高。
- **重复契约现象**：① 重复路由（invites/invitations、privacy-data/data-rights）被契约固化，清理需同步 2 份清单（`secondary-route-inventory.test.ts` + `ui-lab-contract.test.ts`）；② 跨包重复：web/admin 各一份 `primitives.test.tsx`（592/601 行，内容同源）；③ `ui-lab-contract.test.ts` 又登记了一批与 route-inventory 相同的路由清单（两份清单各自维护）。

---

## 3. 重构候选 Top 10（建议，不改代码）

> 排序按性价比（节省/风险），行数为估算基线。

| # | 候选 | 涉及文件 | 风险 | 为什么值得 | 预期节省 |
|---|---|---|---|---|---|
| **R1** | **删除 web `app/*` 7 个不可达 legacy 重定向页**（保留 next.config `legacyRedirects`；`/app/fortune/*` 与 `/app/layout.tsx` 不动）；同步 `legacy-app-route-contract.test.ts` 中对 7 个页面的导入断言，整改为只测 next.config | 7 页 + 1 测试 | **低** | 请求层重定向已生效，页面文件是死代码；双编码是“同一映射写两处”的典型反模式 | −约 50 行 + 消除双编码心智税 |
| **R2** | **`/account` 两组等价路由去重**：保留 `/account/invites`、`/account/data-rights`（有 metadata / 被 UI 引用），把 `/account/invitations`、`/account/settings/privacy-data` 收敛为 `redirect()` 兜底；同步 `secondary-route-inventory.test.ts` 与 `ui-lab-contract.test.ts` 将别名标记为“重定向而非独立 surface” | 2 页（改）+ 2 测试 | **低** | 两组路由渲染同一组件，属内容重复；契约把别名固化为必需使清理成本人为抬高 | −约 14 行代码 + 契约清单收敛 |
| **R3** | **admin 导航收敛到 `[...section]/page.tsx` 单一 catch-all + `admin-route-catalog.ts` 数据驱动**，删除 37 个 5 行壳，URL 由路由表计算（保留 `/login` `/dashboard` `/_ui-lab`） | 37 页 + `admin-catalog-page.tsx` + `admin-route-catalog.ts` | **中** | 37 个壳 100% 同构，仅 pathname 字符串不同；`admin-catalog-page.tsx` 的 113 行 if/else 链 + `admin-route-catalog` 41 条已构成“第二路由系统”，三层同义编码应合一 | −约 190 行壳 + 未来新增路由只写一行目录；维护单一路由表 |
| **R4** | **web 14 术数入口收敛为 `[product]/page.tsx` 动态段**（或至少数据化 metadata 模板），hepan 3 壳同理进 `[product]/hepan` | 14+3 页 + `product-route-contract.test.tsx` | **高** | 唯一差异是 `productId` 与 metadata 文案；但**强烈不建议近期做**：SEO 深链、静态目录可读 URL、契约测试全线绑定。列为“低优先级/高成本”，供 IA 方向决策参考 | 纸面 −126+ 行，实际迁移成本大于收益 |
| **R5** | **把根 `ui/` 从“仅 CSS”升级为真正共享组件库**，web/admin 合并 `ui/*` 组件（button/table/drawer 等 8 组件 ×2 份），删除双份 primitives 测试 | 16 组件 + 2 测试 + 两包 build 配置 | **中高** | 组件已漂移（table 295↔300，drawer 56↔64）；两包同一设计系统两份实现，违反 `ADR 0011` 的“ui 仅样式、web/admin 为前台”边界语义 | −约 860 行组件 + 最多 −1200 行重复测试，长期消除漂移 |
| **R6** | **`/tools/[tool]` 一页两职拆分**：4 个真实流程（time-check/rhythm/five-elements/chart-similarity）改为静态子路由或注册表分发，CMS 工具仅走 `getToolContentSource` | `tools/[tool]/page.tsx` 1 文件 | **低** | 当前 `if(tool===...)` 硬编码 4 个分支混在 CMS 分发里；两套渲染模式共用一个 URL 语义 | −约 30 行 + 分支表替换硬编码 |
| **R7** | **`AuthSurface`/`AccountSurface` 包装层处置**：二者仅被 ui-lab 预览与契约测试消费，真实页面直接用具体 surface/表单；判定为“契约数据与渲染双轨”。建议删除未使用 wrapper、保留 spec 数据供 ui-lab（或反向：让真实页消费 specs 消灭手工壳） | `auth-surface.tsx`(90) `account-surface.tsx`(35) + `secondary-surfaces.ts` auth/account 段 | **低** | 消除“页面还写一份、spec 又写一份”的双写内容；当前 597 行 spec 中 auth/account 段约 130 行仅测试用 | −125 行（或重构为真消费） |
| **R8** | **`dashboard-hub.tsx`(296) + `dashboard-hub.module.css`(366) 清理**：无真实页面挂载，仅 `private-surfaces.test.tsx` 用作旧体验探针；迁移测试到 `account-center` 后删除 | 2 文件 + 1 测试 | **低** | 确认的死代码；与 account-center 功能重叠是“hub 双实现” | −662 行 |
| **R9** | **上帝组件拆分（web 5 个 / admin 2 个）**：`runtime-chart`(1433)、`product-input-form`(1046)、`relationship-task-page`(709)、`reading-result`(691)、`product-task-experience`(638)、`admin-cms-surface`(722)、`admin-catalog-surface`(560) 按“渲染/表单/状态机/命令”切分 | ~7 文件拆成 20± | **高** | 单文件多职责使并行修改与测试隔离困难；但改动面大、需契约测试同步，建议放在 UI 重构后期阶段 | 长期可维护性（每件拆 3–4 模块） |
| **R10** | **CSS 收敛**：① 合并两处 `.accountPage` 重复定义到 `secondary-surfaces.module.css` 或 app-surface；② 抽取站点共享壳样式（site-chrome/private-shell/task-shell 三大壳合计 1,721 行，重复的 header/nav/rail 布局）；③ 将高频字面 px `font-size` 收敛进 `--font-size-*` | ~6 CSS 文件 | **低-中** | CSS 总量 web 11,139 + admin 3,803 中约 30% 为语义重复布局；token 已统一，剩余是布局级 DRY | 预估 −800~1,200 行（保守） |

---

## 4. 附：统计口径与命令

- 路由文件：`find web/src/app admin/src/app \( -name 'page.tsx' -o -name 'layout.tsx' -o -name 'route.ts' \) | sort`
- 组件行数：`find <pkg>/src/components -name '*.tsx' -exec wc -l {} + | sort -rn`
- CSS 行数/硬编码色：`find <pkg>/src -name '*.css' | xargs wc -l`；`grep -cE '#[0-9a-fA-F]{3,8}'`；自定义变量 `grep -nE '^\s*--[a-zA-Z-]+:'`
- 测试：`find <pkg>/src -name '*.test.ts' -o -name '*.test.tsx' | wc -l`
- 本报告中间产物全部内存计算，未写仓库；无 git 操作。
