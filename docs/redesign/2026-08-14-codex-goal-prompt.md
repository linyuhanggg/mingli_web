# Codex Goal 模式任务提示词 — mingli_web「方向 C」全站 UI/IA 重构（阶段 2 收官 + 3/4/5）

> 用法：把本文件全文粘贴给 Codex 并以 goal 模式（长时自动续轮）执行。目标仓库：`/Volumes/Lexar/code/mingli_web`。
> 编制日期：2026-08-15（依据 2026-08-14 grilling 决策 + 阶段 0/1 已完成 + 阶段 2 文件已落地的一次性状态审计）。

---

## 目标

以「方向 C · 现代 SaaS 锐感」视觉合同完成 mingli_web **剩余的全站 UI/IA 重构**，并按仓库验收合同为每个阶段留下真实浏览器证据、通过全部质量门禁，最后以分阶段 commit 交付。你**没有权限**替用户批准 UI——每个阶段完成后把证据与报告归档并明确标记「证据就绪，待用户验收」。

## 0. 动手前必读（按序）

1. `/Volumes/Lexar/code/mingli_web/DESIGN.md` — 视觉、组件、交互、响应式唯一权威合同（2026-08-14 已修订为方向 C，注意 frontmatter `revision_basis`）
2. `/Volumes/Lexar/code/mingli_web/docs/CHECKLIST.md` — 范围/进度/门禁/证据唯一年账（第 0 节变更纪律、第 15 节变更记录）
3. `/Volumes/Lexar/code/mingli_web/CONTEXT.md` — 统一领域名词（「命盘合参」吸收「多盘问答」已生效）
4. `/Volumes/Lexar/code/mingli_web/docs/MINGLI_V51_WEB_INTEGRATION.md` — Runtime/Provider/模型边界；**营销文案的真实事实来源**（§2.1/§3.3：13 个 Provider 体系、55 个古籍 reference pack、1328 条 evidence index）
5. `/Volumes/Lexar/code/mingli_web/docs/redesign/2026-08-14-visual-audit.md` 与 `2026-08-14-direction-c-decision.md` — 审计与全部决策
6. `/Volumes/Lexar/code/mingli_web/web/AGENTS.md` — web 工作规则 + Next.js 破变化提示（Node 26 / Next 16，改代码前读 `web/node_modules/next/dist/docs/` 对应指南）

## 1. 已冻结的视觉合同要点（红线，不可违反）

- **Token**：统一用 `ui/tokens.css`（浅灰底 `--color-canvas:#fafafa`、白面、单蓝 accent `--color-accent:#2563eb`、8px 圆角、`--shadow-card-hover` 单层淡阴影）。业务组件禁止硬编码色值，禁止渐变/玻璃拟态/发光描边/多层彩色阴影。
- **字阶**：页面只允许 12/13/14/16/18/20/24/30 及 Hero 带 40–64（clamp 合理值）。豁免：盘面大字（`--font-domain` 宋体，干支/宫位）、等宽代码（ui-monospace）。禁止 9px 诸如凑版面。
- **动效**：仅 CSS opacity/transform，反馈 ≤160ms、浮层 ≤220ms、页面 ≤280ms；支持 `prefers-reduced-motion`；禁止常驻动画/滚动劫持/视差。
- **可访问性**：触达目标 ≥44px（可点区域）、focus-visible ≥2px 不被遮挡、每个表单真实 Label+就近错误、`aria-live`/`role=alert`、键盘全流程（导航/表单/菜单/抽屉/购买）、Skip Link、唯一 h1、盘面有语义列表替代。
- **内容真实**：不伪造评价、成交量、价格、假社会证明；首页 Hero 文案固定为已批准版（见 §4-阶段2）；「测试期未开放」等状态照现状诚实表达。
- **技术栈**：CSS Modules + 语义 token；图标仅 lucide-react；复杂交互仅 radix-ui；动画仅 motion/react 或 CSS。**禁止新增依赖**（Tailwind/GSAP/Lottie/UI 库都不行）——如需必须改 DESIGN.md 并记录理由（实际预期不需要）。
- **不改**：后端；admin/ 的非视觉业务结构；表单字段名/顺序（autofill/analytics 依赖）；URL 语义（唯一例外：已批准的 `/canwen → /hecan` 重定向，已生效不可回退）。

## 2. 已完成进度（先验证现状，不要重做）

### 阶段 0 ✅ 文档解冻（已提交用户批准）
- `DESIGN.md` §2/§3/§4/§6.1/§6.3/§8.3/§8.5/§10 修订为方向 C；`CONTEXT.md` 术语；`docs/CHECKLIST.md` §3/§15；决策记录 `docs/redesign/2026-08-14-direction-c-decision.md`。

### 阶段 1 ✅ 基础层（已全绿）
- `ui/tokens.css` + `ui/base.css` 重写：新色板/圆角/字阶（新增 `--font-size-aux:13px`、`--font-size-page:30px`、`--font-size-hero:56px`）、h1/h2 紧字距 -0.02em、small=13px。
- 全部 web（47 个 module.css）与 admin（2 个 module.css）字阶收口（297 处字号 + 14 处圆角），硬编码颜色清零；3 个样式契约测试放宽为语义断言。
- 门禁：web typecheck/lint/test（439 通过）；admin typecheck/lint/test（121 通过）。证据：`web/e2e/screenshots/audit-2026-08-14/phase1/`（32 张 + report.json）。

### 阶段 2 ⚠️ 文件已落地，但门禁/证据/批准未完成
以下文件经审计确认**完整可用**（tsc 0 错、首页单测通过、dev server 渲染新首页、/canwen 308 重定向生效），**不要重做，先补齐验证**：
- `web/next.config.ts`（legacyRedirects 含 `/canwen→/hecan` permanent:true）
- `web/src/products/catalog.ts`（hecan→「命盘合参」，CROSS_PRODUCTS=[hecan,wenshi]）
- `web/src/components/site-header.tsx`（divinationGroups 去多盘问答；新增「合参」CrossMenu 下拉）
- `web/src/app/page.tsx` + `web/src/app/home.module.css`（新首页：Hero「十三术同根，五十五部古籍为证」+ CTA 开始排盘/多术合参 + 机制三条 + 命盘/事件任务卡 + 见相横条 + 合参两卡 + 辅助区 + CMS 公告）
  - **Hero 事实（不可改数字）**：13 个术数体系、55 部古籍 reference pack、1328 条证据索引；副标只讲机制与规模。
- `web/src/test/home.test.tsx`（已同步：新 H1、12 条入口矩阵、无 /canwen 与「多盘问答」「三术合参」、四 region、合参恰好 2 条链接）
- `web/src/app/canwen/page.tsx`（页面级 `redirect("/hecan")` 兜底）
- 样板：`web/src/app/%5Fui-lab/redesign-c/`（方向 C 视觉参照，保留到验收）

**阶段 2 待办（本轮第一步）**：
1. 清理残留：确认 `web/src/app/.layout.tsx.swp` 不存在（已删，若重现则删）。
2. 全量门禁：`web/` 下 `npm run lint`（0 warnings）、`npm run typecheck`、`npm test`（全绿，基线 439 前后对比）、`npm run build`。`admin/` 下同跑 lint/typecheck/test（若 package.json 有对应脚本）。
3. 四视口真实浏览器证据：dev server `http://127.0.0.1:3000`（已有进程；若需重启：`lsof -ti tcp:3000` 取 PID kill 后 `cd /Volumes/Lexar/code/mingli_web/web && npm run dev` 后台）。Playwright **无内置浏览器**，用系统 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`；参照 `web/scripts/audit-phase1.mjs` 写 `web/scripts/audit-phase2.mjs`。路由：`/`、`/hecan`、`/wenshi`、`/canwen`（验证最终 URL=/hecan）、`/liuyao`、`/jianxiang`、`/account`、`/auth/login`、`/daily`、`/tools`、`/library`、`/about`、`/pricing`、`/methodology`、`/workbench/demo`、`/_ui-lab`；视口 360/768/1024/1440。断言：无横向滚动（scrollWidth<=innerWidth+1）、首页唯一 h1、主要 region、合参区恰好 2 个入口。截图存 `web/e2e/screenshots/audit-2026-08-14/phase2/{viewport}/{route}.png`。
4. 可访问性抽查（手写 evaluate）：主导航 Tab 可达、「合参」trigger aria-expanded、菜单项键盘可开合、首页唯一 h1。
5. 写阶段报告 `docs/redesign/2026-08-14-phase2-report.md`（证据路径 + 门禁结果 + 截图清单），commit 阶段 2 相关文件（只加你改的文件，**严禁 `git add -A`**——仓库有大量与本次重构无关的既有未提交改动，不要碰）。
6. 标记「证据就绪，待用户验收」。**注意**：按 CHECKLIST 合同，未获用户批准不得宣称阶段完成；批准由用户本人在本会话外给出。

## 3. 阶段 3：账户区重建（DESIGN §10）

- `/account` 重建为**消费 App「我的」页**：顶部身份卡（昵称/账号状态/权益摘要，`useAccountSession` 数据，注意 guest/signed-in/checking 三态与隐私——不显示未授权的真实信息）+ 宫格入口（受测人档案 /account/profiles、推演历史 /account/history、订单与权益 /account/orders（或 entitlements）、通知、账户设置、邀请有礼——按既有路由与 RBAC 现状照实呈现，不造新页面）+ 下方最近交付与待处理事项（复用 reading-history / status-panel 事实组件，不虚构数据）。
- 移动优先同构加宽桌面；沿用方向 C 卡片网格语言（token）。
- 子页（profiles/history/orders/notifications/settings/invitations/data-rights）视觉对齐新合同（标题走 `--font-size-page/section`、正文 16、元信息 12–13），**不改业务文案与权限逻辑**。
- 更新/新增 `web/src/test/` 对应契约测试（account-page-contract 等既有测试若断言旧结构需同步，但不得删减既有覆盖意图）。
- 门禁与证据同阶段 2 规范；报告 `docs/redesign/2026-08-14-phase3-report.md`；commit。

## 4. 阶段 4：产品流 / 工作台换皮 + 合参入口落地

- 七个基础术数（八字/紫微/七政/六爻/奇门/大六壬/见相）录入页、输入确认、盘面组件（`web/src/components/readings/*`）、报告（`ReadingDocument` 渲染面、证据抽屉、核对、追问）、全部状态面板（status-panel：loading/empty/error/processing/unavailable/unauthorized/locked）按方向 C 契约对齐（token + 字阶 + 表格/盘面响应式，双栏工作台右侧阅读区 ≥360px，768 以下单列）。
- 无条件展示 raw JSON / Provider key / snake_case / 内部 ref（现状即禁止，复查无回归）。
- 合参入口：命盘合参 `/hecan` 页面标题与文案用「命盘合参」，按 DESIGN §8.3 的固定流程（立命 → 选两术 → 免费互证 → 整合深读）与「可带着具体问题进入（原多盘问答流程）」呈现任务结构；`/wenshi` 问事合参按 §8.4 固定流程；能力未接的部分按现状诚实显示「适配中/暂不可用」，**永不加载 Fixture 到正常产品路由**。
- 正常路由的盘面字段以既有 ViewModel 为准，不新增未经 Runtime 声明的结论。
- 门禁 + 四视口证据（覆盖各流程的主要状态与 `/_ui-lab` 的 fixture 页面）+ 报告 `docs/redesign/2026-08-14-phase4-report.md` + commit。

## 5. 阶段 5：Admin token 对齐（admin/ 独立应用）

- `admin/` 已通过 `../ui/tokens.css` 吃到新 token（阶段 1 已确认）。逐页检查 `admin/src/app/**` 与组件（admin-shell.module.css、ui.module.css）与方向 C 一致性：密度/圆角/字阶/状态颜色；顶栏 56–64px、1024 起 240px 侧栏、操作目标 ≥44px、写操作确认弹层、表格移动端摘要行不横滚——按现状校正排版，不改权限与业务。
- admin 门禁：`npm run lint/typecheck/test`（既有 121 基线）+ 四视口截图（admin 侧重点 1024/1440，360/768 桌面断点也过一遍）+ 报告 + commit。

## 6. 收尾

1. **删除样板页**：`web/src/app/%5Fui-lab/redesign-a/`、`redesign-b/`、`redesign-c/`（含 module.css 与 `web/e2e/screenshots/audit-2026-08-14/redesign-{a,b,c}/`），理由=视觉方向已定案、样板使命完成；删除前确认不再被引用（lib/grep）。
2. `docs/CHECKLIST.md` 第 15 节追加变更记录（每个阶段的日期/范围/门禁结果/证据路径/待用户验收），不要改写历史行。
3. 最终全量：web + admin 的 `npm run lint / typecheck / test / build` 全绿记录。
4. 分阶段 commit（每个阶段一个或多个 commit，message 用 Conventional Commits，只含该阶段文件）。
5. 汇总终稿 `docs/redesign/2026-08-14-final-report.md`：各阶段证据索引、截图目录、验收状态表（哪些已 USER_ACCEPTED、哪些证据就绪待批准——你只能标后者）。

## 7. 每阶段完成定义（gate，缺一不可）

- [ ] `npm run lint` 0 warning、`npm run typecheck` 0 error、`npm test` 全绿、build 通过（web 与 admin 各自，按对应 package.json）
- [ ] 360/768/1024/1440 四视口截图证据落盘（`web/e2e/screenshots/audit-2026-08-14/phase{N}/`），无横向滚动，字阶在冻结刻度（可复用 audit-phase1 的 metrics 思路复查）
- [ ] 不新增依赖；不回归 DESIGN.md 红线（无渐变/玻璃/发光；动效合规；a11y 抽查通过）
- [ ] 阶段报告 `docs/redesign/2026-08-14-phase{N}-report.md` 写入并 commit
- [ ] 状态明确标注：证据就绪 → 等待用户验收（你没有批准权）

## 8. 环境与工具事实

- 根：`/Volumes/Lexar/code/mingli_web`（web/ 与 admin/ 各自有 package.json；仓库根无 package.json，`npm` 命令务必 `cd` 到子目录）
- dev server：http://127.0.0.1:3000（next dev；next.config 改动需重启才生效）
- Playwright 浏览器未预装：统一 `chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" })`
- 既有替代脚本范式：`web/scripts/audit-phase1.mjs`（截图+指标双用）
- git：工作树存在大量与重构无关的既有未提交改动（backend/admin/docs/scripts 等数百文件）——**严禁 `git add -A` / `git checkout .` / `git reset`**；只 add 你明确改动的文件。不确定的改动先 `git log` 与 diff 查证。
- 若遇到 Next.js 16 破变化（API/约定与训练数据不同），读 `web/node_modules/next/dist/docs/` 内对应指南，不要凭记忆写。
