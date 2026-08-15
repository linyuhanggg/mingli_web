# P4-006 同视口差距审阅准备记录

审阅日期：2026-08-14（Asia/Shanghai）  
当前 Git HEAD：`f488fa4d6eaa989b708b14d87b747ee931468829`  
状态：`P4-006 NOT_STARTED`，本文件不是用户视觉批准，也不是同视口并排验收结论。

## 当前可复核材料

仓库内已存在两份文字版参考审计：

- [青囊登录态产品、免费流程与响应式审计](../2026-08-12-reference-site-audits/qingnang-authenticated-product-audit.md)
- [METIS 生产站与开源仓审计](../2026-08-12-reference-site-audits/metis-live-responsive-ui-audit.md)

当前工作树已有本地浏览器截图：

| 视口 | Web | Admin |
| --- | --- | --- |
| 360 | [首页](../../../../web/e2e/screenshots/360/home-task-selector.png)、[八字工作台](../../../../web/e2e/screenshots/360/bazi-workbench-unavailable.png)、[双人合盘](../../../../web/e2e/screenshots/360/bazi-relationship-input.png) | [登录](../../../../admin/e2e/screenshots/360/login.png) |
| 1440 | [首页](../../../../web/e2e/screenshots/1440/home-task-selector.png)、[八字工作台](../../../../web/e2e/screenshots/1440/bazi-workbench-unavailable.png) | [登录](../../../../admin/e2e/screenshots/1440/login.png) |

自动化路由矩阵另已在 360、768、1024、1440 检查页面级横向溢出、关键浏览器错误和静态资源响应；这只能证明布局没有出现已观测的硬故障，不能替代参考站截图的同尺寸并排判断。

本轮另完成了与来源参考图无关的本地 standalone 四视口逐路自动化证据：[2026-08-14-route-acceptance](../2026-08-14-route-acceptance/README.md)。它补充 Web/Admin 每条已登记路由的状态、视口、截图与 manifest，但不改变本页的 P4-006 `NOT_STARTED` 和 P4-007 `NOT_STARTED` 结论。

## 已整理的对照维度

| 对照维度 | 参考审计给出的约束 | 当前本地证据 | 结论边界 |
| --- | --- | --- | --- |
| 导航断点 | 青囊在 767/768px 切换移动底栏与桌面导航 | Web 路由矩阵已覆盖 767/768 导航切换；360/1440 截图可读 | 可做本地合同判断，不能宣称视觉等价 |
| 360 输入与首页 | 单列任务入口、控件不能压成不可点的小格、页面不横溢 | Web 360 首页/八字旅程/合盘截图与产品旅程测试 | 已抽查，无可复现横溢或控件裁切；仍缺参考截图并排 |
| 360 工作台 | 盘面与阅读区纵向重排，保留章节导航与状态边界 | Web 360 八字工作台截图、正式 Workbench/ReadingShell 组件 | 已抽查，无可复现重叠；不能替代参考站同屏审阅 |
| 768 工作台 | METIS 右侧阅读区过窄，不能照搬固定 520px 左栏 | Web 768 路由矩阵与工作台无横溢检查 | 需要同视口截图和内容宽度实测，当前不标通过 |
| 1024/1440 工作台 | 1024 起双栏可用；1440 保持最大宽与独立阅读 | Web 1440 工作台截图及四档矩阵 | 只有本地 spot-check，未完成参考站并排 |
| Admin 响应式 | 参考审计没有 Admin 对照；本项目要求 1024 以下抽屉导航 | Admin 360/1440 登录截图、四档路由矩阵与抽屉合同 | 可证明本地 Admin 合同，不产生外部视觉批准 |
| 参考站缺陷不复制 | METIS 的 iframe/hydration 问题、青囊过窄控件不应照搬 | 代码未采用同源 iframe；任务输入在 360 采用可重排布局 | 这是设计决策记录，不是视觉相似度评分 |

## 阻塞项与下一步

参考审计目录没有 PNG、JPEG、WebP 或其他同视口截图，只有 Markdown 文字记录。因此当前不能诚实地完成“青囊/METIS 同视口并排差距审阅”，也不能从文字审计反推出像素级差距。

完成 P4-006 还需要：

1. 取得授权的青囊与 METIS 360、768、1024、1440 参考截图，或由用户在同一轮浏览中提供可核验截图。
2. 以相同 Web/Admin 本地截图逐视口并排检查导航、任务输入、工作台、状态、最大宽和 Admin 抽屉。
3. 在此目录追加每个差距的页面、视口、复现步骤和处理结论；处理完成后再把 `docs/CHECKLIST.md` 的 P4-006 状态改为 `VERIFIED`。

在上述材料到位前，P4-006 保持 `NOT_STARTED`；P4-007 仍需用户本人逐页浏览批准，P10–P12 生产门禁也不因本报告改变。
