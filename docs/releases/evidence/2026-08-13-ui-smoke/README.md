# 2026-08-13 UI smoke evidence

本轮在本地生产构建上使用系统 Chrome 执行 Playwright smoke：

- Web：`npm run e2e:smoke`，360/768/1024/1440 共 4/4 通过，入口 `/methodology`。
- Admin：`npm run e2e:smoke`，360/768/1024/1440 共 4/4 通过，入口 `/login`。
- 截图目录：`docs/releases/evidence/2026-08-13-ui-smoke/web/screenshots/<viewport>/methodology.png`、`docs/releases/evidence/2026-08-13-ui-smoke/admin/screenshots/<viewport>/login.png`。
- Web 日志有前端代理访问 `127.0.0.1:8000` 的非关键 API 连接拒绝；页面文档、脚本、样式和字体没有关键 HTTP 错误，测试仍通过。

这份记录只证明自动化 smoke 和四档截图通过，不等同于 P4-007 的用户逐页批准、全路由旅程验收或生产环境验收。
