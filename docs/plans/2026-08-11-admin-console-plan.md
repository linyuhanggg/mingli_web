# FateRadar Admin Console Plan

> Status: Draft for implementation  
> Date: 2026-08-11  
> Scope: ops/admin console shared by web ops now, reusable Admin API for future internal tools / possible later staff iOS  
> UI authority: `DESIGN.md` + `design-system/mingli-web/MASTER.md` + `design-system/mingli-web/pages/admin.md`  
> Product authority: `docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md` (Refund / Entitlement / Reconcile)

---

## 0. Goal

做一套**和 C 端同一视觉语言**的运营后台，先服务 Web 运营，后端合同可被以后 iOS 用户端以外的内部工具复用。

不是：

- 把 C 端站点塞进“管理菜单”
- 另起一套蓝灰企业后台皮肤
- 现在就做原生 iOS 运营 App

是：

- **同一 FastAPI 单体**上的 Admin API + RBAC + 审计
- **独立 Admin Web 壳**（同仓优先）
- **Eastern Editorial Archive** 的账簿式 UI（更密、更操作向）

---

## 1. Decision summary

| 决策 | 选择 | 理由 |
|------|------|------|
| 后端形态 | 现有 FastAPI 模块化单体 + `/api/v1/admin/*` | 支付/权益/退款要事务一致，不拆微服务 |
| 前端形态 | 同仓独立 `admin/` Next.js App（推荐） | 与 C 端发布/权限隔离；可共享 tokens/组件约定 |
| 备选前端 | `web` 内 route group `/admin` | 更快，但鉴权与样式更易缠死 |
| 视觉 | 复用 C 端 tokens/字体/组件语法 | 用户要求“UI 和前端风格一样” |
| 密度 | Density 7（比 C 端更紧） | 表格/筛选需要；仍禁止 SaaS 灰蓝皮肤 |
| iOS | 只复用 Admin/User API 合同，不做运营 WebView App | ADR 0007：原生 iOS 是用户端 |
| 鉴权 | Staff 身份与普通用户分离 + 角色 + 审计 | 后台面更大，参考既有凭据风险教训 |

**推荐默认：`admin/` 独立应用 + Admin API。**  
若第一周只要最小可用，可用 `web/src/app/admin` 起步，但组件/CSS 从第一天按可拆出 `admin/` 组织。

---

## 2. UI plan (ui-ux-pro-max + project authority)

### 2.1 How recommendations were used

`ui-ux-pro-max` 用于：

- 确认 admin 需要 **data-dense ops shell**、table/filter a11y、loading/submit feedback
- 确认 chart 优先级低：P0 表格优先

**未采用**其默认粉色 accent、Fira 字体、通用 zinc 灰、GSAP 列表弹跳——这些与 `DESIGN.md` 冲突。  
最终视觉合同以项目已有 **Eastern Editorial Archive** 为准，并写入：

- [`design-system/mingli-web/pages/admin.md`](../../design-system/mingli-web/pages/admin.md)

### 2.2 Visual contract (same as C-end)

- 画布象牙 `--ivory-50`，卡片白纸 `--white`
- 主操作墨绿 `--ink-900`
- 金线只做层级/编号，不做大面积填充
- 陶土只做焦点/错误
- 状态：琥珀处理中 / 苔藓成功 / 陶土错误文案
- 标题宋体，操作与表格黑体
- CSS Modules + radix-ui + lucide + motion 轻反馈
- 禁止 Tailwind/shadcn/MUI/AntD 新体系

### 2.3 Admin shell

- 顶栏：品牌、环境徽章（local/test/prod）、员工身份、退出
- 侧栏：总览 / 用户档案 / 订单支付 / 退款审批 / 解读任务 / 对账 / 审计
- 主区：页头职责说明 → 筛选条 → 账簿表/卡 → 详情抽屉
- 桌面优先（≥1024）；移动端表格改卡片，不横爆

### 2.4 P0 screens

1. **登录** — staff only；文案直白；无营销 hero  
2. **总览** — 4 个 KPI chip + 待办队列  
3. **订单/支付** — 查单、状态、渠道事实只读  
4. **退款审批** — 申请、影响预览、通过/驳回+原因  
5. **解读任务** — 失败/卡住列表、允许时重试  
6. **用户/档案只读** — 脱敏默认  
7. **审计日志** — 谁对什么做了什么  

P1：对账看板、权益异常处理、导出。

### 2.5 Interaction rules

- 所有筛选字段有可见 label
- 提交后 loading → success/error，错误靠近字段或 `role="alert"`
- 危险操作二次确认
- 状态不只靠颜色
- PII 默认打码，点开揭示记审计
- 从不展示 `state_token`、密钥、完整渠道原始回调（除非受控 debug 且脱敏）

### 2.6 Component build list

| Component | Purpose |
|-----------|---------|
| `AdminShell` | top + side + main |
| `EnvBadge` | local/test/prod |
| `KpiChip` | overview counts |
| `FilterBar` | search/date/status |
| `LedgerTable` | desktop data |
| `LedgerCards` | mobile data |
| `StatusTag` | state text+color |
| `InspectDrawer` | detail |
| `ConfirmDialog` | refund/retry |
| `AuditLine` | history row |
| `MaskedField` | reveal-on-demand |

优先复用 C 端已有：`button` 语义、form controls、status-panel 思路、tokens。  
不复用 C 端营销壳：`TimeArchive`、首页 hero、task-card 销售语义。

---

## 3. Backend plan

### 3.1 Modules

在 `backend/app/` 增加：

- `admin/` 或 `identity/staff` + `api/admin/*`
- 角色：`support` / `finance` / `ops` / `superadmin`
- 中间件：staff session 校验、CSRF（cookie 方案）、权限守卫
- `admin_audit_events` 表（append-only）

### 3.2 API surface (draft)

OpenAPI：`contracts/openapi/admin-v1.yaml`（与用户 `v1.yaml` 分离）

```
POST   /api/v1/admin/auth/login
POST   /api/v1/admin/auth/logout
GET    /api/v1/admin/me

GET    /api/v1/admin/overview
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{user_id}
GET    /api/v1/admin/orders
GET    /api/v1/admin/orders/{order_id}
GET    /api/v1/admin/payments
GET    /api/v1/admin/refunds
POST   /api/v1/admin/refunds/{id}/approve
POST   /api/v1/admin/refunds/{id}/reject
GET    /api/v1/admin/readings
POST   /api/v1/admin/readings/{id}/retry   # only if domain allows
GET    /api/v1/admin/reconcile/daily
GET    /api/v1/admin/audit-events
```

规则：

- Admin API **不**复用用户 cookie 直接升权；staff 会话独立
- 写操作全进审计
- 领域动作走现有 Payment/Refund/Entitlement/Reading 模块，admin 只编排

### 3.3 Security baseline

- 生产 admin 默认不裸奔公网：IP allowlist / SSH tunnel / 内网
- MFA（至少 superadmin/finance 强制；P0 可先 env gate + strong password，P1 补 MFA）
- 短会话 + 绝对超时
- 速率限制登录
- 脱敏 DTO
- 操作幂等键（approve refund 等）

---

## 4. Repo layout (target)

```
mingli_web/
  design-system/mingli-web/
    MASTER.md
    pages/admin.md          # done in this plan step
  docs/plans/
    2026-08-11-admin-console-plan.md
  contracts/openapi/
    admin-v1.yaml           # to build
  backend/app/
    admin/                  # to build
  admin/                    # recommended Next app
    src/app/...
    src/components/...
  web/                      # C-end stays clean
```

共享策略：

- **共享**：tokens 文档、视觉规则、少量无品牌耦合 primitives（如 button CSS 变量用法）
- **不共享**：C 端 private-shell、营销页、用户 session 逻辑

短期可从 `web` 复制 tokens CSS 起步；中期抽 `packages/ui-tokens` 可选，不阻塞 P0。

---

## 5. Implementation phases

### Phase A — Contract & skeleton (1–2 days)

1. 写 `admin-v1.yaml` 最小路径  
2. Backend staff 模型 + login/me + 权限守卫空壳  
3. Admin app shell 页面（可假数据）  
4. 套用 `pages/admin.md` 视觉  
5. 基础 a11y：skip link、focus、nav labels  

**验收：** 本地打开 admin 壳，风格与 C 端 tokens 一致；未登录进不了业务页。

### Phase B — Read-only ops (2–4 days)

1. users / orders / payments / readings 列表+详情  
2. 脱敏字段  
3. 筛选+分页  
4. 审计读取  

**验收：** 用测试库真实只读数据跑通 4 列表；移动端卡片不炸版。

### Phase C — Write paths (2–3 days)

1. refund approve/reject  
2. reading retry（受 domain 门禁）  
3. 写审计 + 幂等  
4. ConfirmDialog + error states  

**验收：** 退款审批集成测试；重复提交不双退；UI 有明确结果。

### Phase D — Reconcile & harden (P1)

1. 每日对账视图  
2. MFA / IP gate 文档化与实现  
3. 导出  
4. 与 test server runbook 接入  

---

## 6. Task breakdown (dev-ready)

### A1. Design freeze
- [x] Admin surface override 文档
- [x] 本实现计划
- [x] 确认：独立 `admin/` 应用（2026-08-11）

### A2. OpenAPI admin-v1
- [x] 路径、错误模型、角色注解（login/logout/me/overview）

### A3. Backend staff + auth
- [x] migration：staff_users / staff_sessions / admin_audit_events
- [x] login/logout/me + overview stub
- [x] staff session + csrf dependency

### A4. Admin UI shell
- [x] layout + nav + env badge + login（独立 admin/ :3001）
- [x] tokens 接入与基础组件

### A5. Read APIs + pages
- [ ] overview / orders / refunds / readings / users / audit

### A6. Write APIs + pages
- [ ] refund decisions / optional retry

### A7. Tests
- [ ] backend: authz matrix、refund idempotency、masking
- [ ] web: shell nav、filter labels、confirm dialog、table/card switch

### A8. Deploy notes
- [ ] test server 仅回环/隧道
- [ ] prod 暴露策略写进 runbook

---

## 7. Explicit non-goals (this pass)

- 不做用户 App 内嵌后台
- 不做复杂 BI 图表墙
- 不做客服 IM
- 不做任意 SQL 控制台
- 不把 Runtime `state_token` 暴露到后台 UI
- 不引入第二套设计系统

---

## 8. Success criteria

1. 运营能在 admin 完成：查用户、查订单、审退款、看失败解读、看审计  
2. 视觉一眼属于 FateRadar（墨绿/象牙/金线/陶土），不是通用后台模板  
3. Admin API 合同可独立给未来内部工具使用  
4. 无 staff 权限的用户 API token/cookie 调 admin 全 403  
5. 关键写操作有审计且可幂等  

---

## 9. Decision locked

- **2026-08-11：** 独立 `admin/` 应用 + Admin API（选项 1）
- Phase A 落地中：OpenAPI + staff auth 骨架 + admin Next shell
- 本地启动：
  - 后端 bootstrap：`MINGLI_ADMIN_BOOTSTRAP_EMAIL` / `MINGLI_ADMIN_BOOTSTRAP_PASSWORD`（仅 local/test）
  - 前端：`cd admin && npm run dev`（默认 3001）
