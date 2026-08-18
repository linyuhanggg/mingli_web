# 八字 G5 密度浏览器证据

日期：2026-08-18

> **数据边界：合成 Fixture，不代表 Runtime 已发布。本目录不是 `BROWSER_VERIFIED`，状态仅为「证据就绪，待用户验收」。**

## 运行边界

- 产品页：生产构建后的 `/_ui-lab/bazi-result`，数据来自 `web/src/fixtures/bazi-evidence-result.ts`。Fixture 补齐 8 步大运及流年、流月、流日层，只用于验证既有结果渲染器的密度和响应式行为。
- 参考页：仓内 `qingnang/site/pages/bazi.html` 及其本地静态资源，由审计脚本临时 HTTP 服务加载；脚本填写 1994-04-30 05:55、男、北京并点击「开启推演（免费）」。镜像没有后端，`/api/*` 固定返回 404，因此只统计页面本地计算后实际可见的结构化盘面，不把仍在等待的 AI 解读算入参考数。
- 浏览器：Playwright `@playwright/test` + 系统 Google Chrome，路径 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`；没有使用 browser MCP。
- `report.json` 的 `gitSha` 是取证时的 HEAD `ac6f77c610a05a15cd7c526c0ad8868c630ae851`；本目录、审计脚本与 Stage F 工作区改动在同一个后续分组提交中落地。

## 可复算命令

```bash
npm --prefix web run build
cd web && PORT=3000 HOSTNAME=127.0.0.1 npm start
cd .. && MINGLI_G5_GIT_SHA="$(git rev-parse HEAD)" node web/scripts/audit-g5-density.mjs
```

脚本：`web/scripts/audit-g5-density.mjs`。机器报告：`report.json`。

## 计数方法

计数单位是一个当前可见、带正文的结构化事实行或事实格，不按字数、字符数或视觉卡片面积计数。

产品选择器：

- `table tbody tr`
- `dl > div`
- `ul > li, ol > li`
- `[role="group"][aria-label="四柱"] > button`

青囊选择器使用上述前三类；另补其结果根节点内“计算样式为 `display: grid` 的容器”的可见叶级子项，因为镜像主要用 `div` 网格表达四柱和盘面事实。表单、导航、tablist、tabpanel，以及包含 table/dl/list/form 的上层容器不计，避免重复算整块文本。

两边都排除不可见项和含“未返回 / 尚未返回 / 未生成 / 暂无可 / 暂不可用”的占位项。正文先折叠连续空白，再以 `类型 + 规范化正文` 去重。产品依次激活本命、大运、流年、流月、流日五层，对五层可见单位取并集；同一条同类型正文跨层出现只算一次。原始逐项正文、类型和字号都保存在 `report.json` 的 `productUnits` / `referenceUnits` 中。

## 实测结果

| 视口 | 本命 | 大运 | 流年 | 流月 | 流日 | 页面最大横向溢出 | 计数事实最小字号 | 截断项 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 360 | 49 | 16 | 9 | 13 | 14 | 0 px | 13 px | 0 |
| 768 | 49 | 16 | 9 | 13 | 14 | 0 px | 13 px | 0 |
| 1024 | 49 | 16 | 9 | 13 | 14 | 0 px | 13 px | 0 |
| 1440 | 49 | 16 | 9 | 13 | 14 | 0 px | 13 px | 0 |

页面级断言是每个视口、每个时间层都满足 `document.documentElement.scrollWidth <= window.innerWidth + 1`。宽表仍可在自己的容器内横滚。计数事实的截断判定覆盖 `text-overflow: ellipsis`，以及横向隐藏且 `scrollWidth > clientWidth + 1` 的情况。

密度并排结果：

| 视口 | mingli_web 五层去重事实 | qingnang/site 可见事实 | 判定 |
|---:|---:|---:|---|
| 768 | 84 | 33 | 84 ≥ 33，通过 |
| 1440 | 84 | 33 | 84 ≥ 33，通过 |

## 证据文件

- `360/`、`768/`、`1024/`、`1440/`：各含 `mingli-natal.png`、`mingli-decadal.png`、`mingli-yearly.png`、`mingli-monthly.png`、`mingli-daily.png`；768/1440 另含 `qingnang-result.png`。
- `comparison-768.png`、`comparison-1440.png`：本产品本命完整页与青囊本地结果完整页并排截图。
- `report.json`：四视口五层布局、字号、截断、计数明细及失败列表；本次 `ok=true`、`failures=[]`。

浏览器审计先真实发现 360/768 页面级横向溢出，以及隐藏面板撑高短时间层的问题；修正公共工作台的横向裁剪和非激活面板布局后，以同一脚本、同一 Fixture、同一参考输入复跑通过。最终状态：**证据就绪，待用户验收**。
