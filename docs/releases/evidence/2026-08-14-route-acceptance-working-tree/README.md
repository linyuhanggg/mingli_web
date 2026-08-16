# 2026-08-14 当前工作树四视口逐路验收

这份证据对应当前未提交工作树的 standalone 生产构建，不是 `HEAD` 快照。Web 与 Admin 都逐路访问了四个视口：360×800、768×1024、1024×768、1440×900。当前工作树追加运行 Web `64 passed`、Admin `36 passed` 的 route/accessibility 套件；后端未启动时，CMS 公共投影请求降级回原有明确空态。

本轮 Web 公共编辑页/CMS/SEO 接线的四份 manifest 位于 [`web-editorial-cms-smoke`](./web-editorial-cms-smoke/)，Admin 创建草稿切片的四份 manifest 位于 [`admin-cms-create-smoke`](./admin-cms-create-smoke/)。两组均只代表自动化工作树证据，不代表用户逐页批准。

| 应用 | 路由数 | 截图 | 结果 |
| --- | ---: | ---: | --- |
| Web | 66 | 264 | 4/4 通过；route/accessibility `64 passed` |
| Admin | 40 | 160 | 4/4 通过；route/accessibility `36 passed` |

四份 manifest 均为 `reviewStatus: automated-only`，Git 标识为 `f488fa4d6eaa989b708b14d87b747ee931468829+working-tree`。只读完整性检查确认每条记录 HTTP 200、截图存在且非空、视口与 manifest 一致；没有把自动化结果标成用户审阅。

## Admin unavailable 状态

本轮复核了后端 8000 未启动时的 `/staff`、`/health`、`/capabilities`、`/support-cases`、`/appeals` 与 CMS 路由。Admin 现在显示“运营平台暂时不可用；当前页面保留只读结构”，不再渲染代理层原始“请求失败（500）”或服务端返回标题；`/health` 仍诚实显示“健康检查 API 尚未接入”和“暂无可核验的实时结论”，能力策略、客服案件、邀请申诉和 CMS 页也不渲染假数据或假操作结果。该边界由 Admin unavailable/API 合同覆盖，并随 Admin standalone build、route matrix `16 passed` 和 accessibility `20 passed` 复核。

## 边界

这份证据证明当前工作树的本地自动化与 unavailable 状态降级，不等于 P4-006 的青囊/METIS 授权来源截图并排审阅，也不等于 P4-007 的用户逐页批准。P4-006、P4-007 与 P12 外部准入仍按 `docs/CHECKLIST.md` 保持未完成或阻塞。
