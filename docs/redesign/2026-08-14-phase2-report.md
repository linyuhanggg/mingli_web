# 阶段 2 报告：公共壳、新首页与营销页族
日期：2026-08-15（Asia/Shanghai）
状态：**证据就绪，待用户验收**

## 范围

- 公共壳：桌面/移动导航、合参菜单、旧 `/canwen` 路由重定向。
- 首页：方向 C Hero、真实规模事实、七术/见相/合参/辅助任务入口与四个语义分区。
- 公共页族：阶段 2 路由的响应式与导航回归。
- 共享 Button：修复 `asChild` 接收单元素数组时的运行时崩溃，并加入回归测试。

## 自动门禁

| 项目 | 结果 |
|---|---|
| `cd web && npm run lint` | 通过，0 warnings |
| `cd web && npm run typecheck` | 通过 |
| `cd web && npm test` | 通过，70 files / 439 tests |
| `cd web && npm run build` | 通过 |
| `cd admin && npm run lint` | 通过，0 warnings |
| `cd admin && npm run typecheck` | 通过 |
| `cd admin && npm test` | 通过，33 files / 121 tests |
| `cd admin && npm run build` | 通过 |
| `node web/scripts/audit-phase2.mjs` | 通过，64/64 route × viewport |

## 真实浏览器证据

- 浏览器：系统 Chrome `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`。
- 服务：`http://127.0.0.1:3000`，本地 dev server。
- 视口：360、768、1024、1440；路线：16 条阶段 2 路由，共 64 个组合。
- 证据目录：`web/e2e/screenshots/audit-2026-08-14/phase2/`。
- 截图：64 张 PNG；机器报告：`web/e2e/screenshots/audit-2026-08-14/phase2/report.json`。
- 负向检查：页面级 `scrollWidth <= innerWidth + 1` 全部通过；`/canwen` 最终 URL 为 `/hecan`。
- 首页抽查：唯一 `main`、唯一 `h1`、命盘/事件判断/合参/辅助各一个 region，合参区恰好两个入口。
- 键盘/ARIA：移动或桌面导航可由 Tab 到达；桌面合参 trigger 的 `aria-expanded` 可由 Enter/Escape 开合。

## 待验收边界

本报告记录本地自动化与真实浏览器证据，不代表用户批准。阶段 2 状态保持「证据就绪，待用户验收」，不得写成 `USER_ACCEPTED` 或公开上线。生产支付、真实 Runtime/模型、外部测试机与用户逐页批准仍是独立门禁。
