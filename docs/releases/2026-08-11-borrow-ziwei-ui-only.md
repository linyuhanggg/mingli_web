# Borrow Ziwei UI Only — Workspace Adoption

记录日期：2026-08-11（Asia/Shanghai）

状态：**UI-only 工作台交互已落地 / 不开放紫微产品入口 / 不借算法 / production blocked 不受本记录影响**

## 借了什么

- 盘面工作台交互语法：时间层 tabs、可点选柱位、聚焦详情抽屉
- 建档页时间口径复述（Task 2，更早提交）
- 解读页“结论优先，盘面作证据”的阅读顺序（八字与非八字解读统一：判断 → 事实 → 依据与边界 → 复核与追问）
- 展示模型 `ChartWorkspaceView`，只映射服务端公开事实

## 明确没借什么

- 不借 `iztro` / `lunar-javascript` / `generateChart` / `astro.bySolar`
- 不借对方 Tailwind / 品牌 / 倪师长文 / 格局自动判定 / 样本数据
- 不新增紫微产品入口，不在前端本地排盘

## 影响页面

- `/app/profile/new`：出生时间口径确认摘要
- `/app/readings/[readingId]`：八字结果页结论优先 + 可聚焦盘面工作台
- 相关组件：`birth-basis-summary`、`chart-workspace-shell`、`time-layer-tabs`、`focus-detail-drawer`、`bazi-chart`

## 测试与门禁

- `npm --prefix web test`：206 passed
- `npm --prefix web run lint`：通过
- `npm --prefix web run typecheck`：通过
- `npm --prefix web run build`：通过（含 `/app/readings/[readingId]`）
- 边界测试 `chart-workspace-boundary.test.ts` 通过；`rg` 仅在测试说明里出现算法禁词

## Task 6

跳过。后端公开事实与 P0 产品能力只暴露 `bazi` / `fortune` / `liuyao`，没有足够公开紫微宫位/星曜结构可供诚实渲染；禁止用散文伪造十二宫盘。

## 非目标

- 不宣称紫微产品上线
- 不改 Runtime / 支付 / 合规 Gate
- 本记录不是 production 放量批准
