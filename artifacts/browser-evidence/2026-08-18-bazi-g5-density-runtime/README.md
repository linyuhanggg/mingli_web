# 八字 G5 真实 Runtime 密度浏览器证据

日期：2026-08-18。状态：**证据就绪，待用户验收**。本目录不是 `USER_ACCEPTED`，也不代表测试机或生产发布。

## 数据与运行边界

- 产品页：production build 的真实 `/bazi`。Playwright 在每个视口重新创建 guest session，填写出生资料，创建 ProfileVersion，调用正式 `POST /api/v1/readings/preview`，由 one-shot V53 Worker 处理，再读取同一 guest cookie 所属的 owner result。四个视口对应四个独立 `reading_version_id`，记录在 `report.json`。
- `productDataBoundary`：`signed-runtime-release-owner-result`。没有读取 `/_ui-lab/bazi-result`，没有导入 `web/src/fixtures/**`，没有用 Fixture 补齐 Runtime 缺失字段。
- 签名 release：`.runtime/v53-time-check-release`；`.mingli-release-manifest.json` SHA-256 为 `7996b03356de9918484b83cdf84677b4e2946b1b55d7f0c504dd40cfd5ee7ca6`，由审计脚本在取证时直接计算并写入报告。
- Worker 使用真实签名 one-shot Runtime 生成盘面事实；本地确定性 Model 只用于让产品现有状态机从 `prepared` 进入可展示 owner result 的 `accepted`。密度选择器根节点固定为 `[aria-label="排盘工作台"]`，不统计 Accepted 正文。
- 参考页：仓内 `qingnang/site` 本地镜像，输入仍为 1994-04-30 05:55、男、北京；镜像无后端，仍只统计本地计算后实际可见的结构化盘面。
- 浏览器：Playwright `@playwright/test` + 系统 Google Chrome；没有使用 browser MCP。

## 可复算命令

先用临时数据库跑 Alembic 到 head，登记冻结配置中的 V53 release，再以同一数据库启动 API 与 Worker；production Web 构建时使用 `BACKEND_INTERNAL_URL=http://127.0.0.1:8000`。浏览器审计命令：

```bash
MINGLI_G5_PRODUCT_ROUTE=/bazi \
MINGLI_G5_PRODUCT_DATA_BOUNDARY=signed-runtime-release-owner-result \
MINGLI_G5_OUTPUT_ROOT=artifacts/browser-evidence/2026-08-18-bazi-g5-density-runtime \
MINGLI_G5_GIT_SHA="$(git rev-parse HEAD)" \
node web/scripts/audit-g5-density.mjs
```

API/Worker 必须使用 `MINGLI_RUNTIME_ADAPTER=one-shot`、`MINGLI_RUNTIME_RELEASE_PROFILE=v53-time-check`、当前 release launcher/root 与 Core 固定 Python。完整机器结果和四个 owner reading ID 在 `report.json`。

## 计数口径

口径与 Fixture 版 `artifacts/browser-evidence/2026-08-18-bazi-g5-density/README.md` 完全相同：可见且有正文的 `table tbody tr`、`dl > div`、`ul/ol > li`、四柱按钮；排除不可见项和“未返回 / 尚未返回 / 未生成 / 暂无可 / 暂不可用”占位项；按 `类型 + 规范化正文` 去重。参考站继续补计可见叶级 grid cell。没有改变字号、截断、overflow 或密度阈值。

## 真实字段差额

真实无目标时间的 owner result 只开放本命和大运。`core_facts.year_layers`、`core_facts.month_layers`、`core_facts.day_layers` 未返回，因此流年、流月、流日 tab 为 `data-status=unavailable` 且禁用；三层计数如实记为 0。对应截图保留禁用状态，不冒充层内容。`BaziChart` 内“命中古法”抽屉在四个真实结果上均未渲染，报告记为 `evidenceDrawerRendered=false`，未用 Fixture evidence 补齐。

| 视口 | 本命 | 大运 | 流年 | 流月 | 流日 | 页面最大横向溢出 | 可用层最小字号 | 截断项 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 360 | 41 | 18 | 0（不可用） | 0（不可用） | 0（不可用） | 0 px | 13 px | 0 |
| 768 | 41 | 18 | 0（不可用） | 0（不可用） | 0（不可用） | 0 px | 13 px | 0 |
| 1024 | 41 | 18 | 0（不可用） | 0（不可用） | 0（不可用） | 0 px | 13 px | 0 |
| 1440 | 41 | 18 | 0（不可用） | 0（不可用） | 0（不可用） | 0 px | 13 px | 0 |

每个视口、每个层记录都执行 `document.documentElement.scrollWidth <= window.innerWidth + 1`；20 条记录的 overflow 均为 0。可用层检查字号与截断；不可用层不拿当前可见的大运内容冒充该层计数。

Fixture 版五层去重为 84；真实 Runtime 版为 59，差额为 -25。真实本命 41（Fixture 49），真实大运 18（Fixture 16），其余三层因上述字段缺失不渲染。跨层去重存在重合，-25 不等于各层差额简单相加。

## G5 并排结果

| 视口 | mingli_web 真实可见事实 | qingnang/site 可见事实 | 判定 |
|---:|---:|---:|---|
| 768 | 59 | 33 | 59 ≥ 33，通过 |
| 1440 | 59 | 33 | 59 ≥ 33，通过 |

`report.json` 为 `ok=true / failures=[]`。`comparison-768.png`、`comparison-1440.png` 使用真实 `/bazi` 本命页与参考站同视口并排；各视口目录含五个层状态截图，768/1440 另含参考站截图。

最终状态：**证据就绪，待用户验收**。
