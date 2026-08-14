# 阶段 4 报告：产品流、工作台与合参入口

日期：2026-08-15（Asia/Shanghai）
状态：**证据就绪，待用户验收**
阶段 4 主提交：待提交

## 范围

- 七个单术入口 `/bazi`、`/ziwei`、`/qizheng`、`/liuyao`、`/qimen`、`/daliuren`、`/jianxiang` 统一为「任务输入 → 输入确认 → 工作台 → 报告与追问」的任务流。
- `/bazi`、`/ziwei`、`/qizheng`、`/liuyao`、`/qimen`、`/daliuren` 保留各自的输入事实、专属盘面结构、服务端确定性生成边界，不在浏览器填充虚构盘面。
- `/jianxiang` 保留照片处理独立同意、本地文件选择和未接入能力的诚实状态；确认后进入工作台，显示「盘面尚未生成」，不上传或保存审计文件。
- `/hecan` 固定为「立命 → 选两术 → 免费互证 → 整合深读」入口，明确八字主术、紫微/七政参证和具体问题入口；`/wenshi` 固定同一问题与时空、六爻先行、再生成大六壬与奇门的流程。
- `/workbench/demo` 只显示不透明句柄恢复与未接入状态；`/_ui-lab` 明确标为验收台 Fixture，未被当作生产路由数据源。
- 修正账户会话测试对异步 `checking → signedIn` 状态的错误即时断言，避免全量测试受运行时序影响。

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
| `node web/scripts/audit-phase4.mjs` | 通过，44/44 route × viewport |

## 真实浏览器证据

- 浏览器：系统 Chrome `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`。
- 服务：`http://127.0.0.1:3000`，本地 dev server。
- 路线：7 个单术入口、`/hecan`、`/wenshi`、`/workbench/demo`、`/_ui-lab`，共 11 条路线。
- 视口：360、768、1024、1440；共 44 组路线 × 视口。
- 证据目录：`web/e2e/screenshots/audit-2026-08-14/phase4/`；截图 44 张，机器报告 `report.json`。
- 负向检查：所有组合 `scrollWidth === innerWidth`；每个生产页唯一可见 `main` / `h1`；无 page error；生产路由没有 `UI 演示数据`、`页面已预制`、provider key、raw JSON 或 snake_case 文案。
- 见相交互：在浏览器内仅选择内存文件并通过授权/确认步骤；360px 工作台为单列，1440px 为双列；未接入状态保持可见。
- UI Lab 只作为显式 Fixture 验收台单独检查，不把它的演示数据算入正常产品路由。

## 待验收边界

本报告记录本地自动化与真实浏览器证据，不代表用户批准。阶段 4 状态保持「证据就绪，待用户验收」，不得写成 `USER_ACCEPTED` 或公开上线。真实 Runtime 结果、账户态合参、见相适配器、支付/权益和用户逐页批准仍是独立门禁。
