# P4-005 可访问性证据（2026-08-13）

本目录记录当前工作树对 P4-005 的真实浏览器合同。测试运行在本地 production build 上，使用系统 Chrome；它们验证可观察的键盘、焦点、表单错误、重排和 reduced-motion 行为。

## 结果

- Web `e2e/accessibility.spec.ts`：4 个 Playwright 项目（360/768/1024/1440），共 `20 passed`。
- Admin `e2e/accessibility.spec.ts`：4 个 Playwright 项目（360/768/1024/1440），共 `20 passed`。
- Web `npm run typecheck`、`npm run lint`：通过。
- `git diff --check`：通过。

覆盖内容：

- 移动 Web 术数抽屉、Admin 运营抽屉可用键盘 Enter 打开、Escape 关闭，并把焦点交还触发按钮。
- Web `/bazi` 空提交会播报顶部“请先修正以下输入”错误摘要，错误项链接到控件，首个错误控件获得焦点。
- Web/Admin 在 640px 与 320px CSS 视口（分别作为 200% 与 400% 重排等价检查）无页面级横向溢出。
- Web/Admin 在 `prefers-reduced-motion: reduce` 下没有长于 50ms 的运行中动画。

## 解释边界

320/640 是 WCAG reflow 的等价 CSS 视口检查，不冒充操作系统浏览器缩放的录像；完整的真实屏幕阅读器、逐页 200/400% 人工检查和视觉并排审阅仍需后续证据。测试期间页面向本地 `127.0.0.1:8000` API 的请求会出现连接拒绝，这是后端未启动造成的非关键代理噪声，不影响文档、脚本、样式或上述合同结果。

这份证据不替代 P4-007 用户亲自浏览批准，也不替代 P12 真实机器、凭据、备份、支付和发布门禁。
