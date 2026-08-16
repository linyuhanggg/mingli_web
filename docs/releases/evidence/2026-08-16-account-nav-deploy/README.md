# 2026-08-16 账户中心导航测试发布

## 发布范围

- 目标：测试服务器 `fateradar-prod`，公网入口 `http://106.14.10.235:18080/`。
- 新 release：`/opt/fateradar/releases/ui-preview-20260816-account-nav`。
- 当前指针：`/opt/fateradar/current -> ui-preview-20260816-account-nav`。
- 只重启 `fateradar-test-web`；API、Worker、Admin 和数据库没有重启或迁移。
- 生产域名 `https://fateradar.cn/` 没有修改。

## 代码与构建

- 本地 overlay 包 SHA-256：`411ba12eb9878af2ae8b7d84cbf066b502bc903e3ff728400dbe8f401d898115`。
- overlay 只包含账户页、私域壳、共享页面样式和账户测试文件；没有上传本机 `.next`、环境文件或密钥。
- 服务器使用 Node `v22.22.1`、Next `16.3.0` 完成 `npm ci`、`BACKEND_INTERNAL_URL=http://127.0.0.1:8000 NODE_ENV=production npm run build` 和 `node scripts/start-standalone.mjs --prepare-only`。
- 构建生成 34 个静态页面，standalone `server.js` 可在临时 3010 端口启动。

## 空间清理

- 清理前根盘仅剩约 99MB；清理后可用约 27GB。
- 删除 30 个旧测试 release：21 个旧提交目录和 9 个旧 `ui-preview-*` 目录。
- 保留当前前一版 Web release `ui-preview-20260816-codex-web`，以及 API 正在使用的回滚版 `ui-preview-20260815-public-products`。
- 清理 root npm、pip、uv、Node compile 和 apt archive 可再生缓存。
- 未删除 `/opt/fateradar/shared`、数据库、日志或通用工具目录。

## 线上验证

- `/account` 返回 HTTP 200，页面 `h1` 为「我的」，不包含「返回公共首页」和「私人档案区」。
- 账户页 CSS 资源 5/5 返回 HTTP 200。
- 公网 Chrome 360、768、1024、1440 四个视口均无横向溢出、无关键资源 4xx、无页面错误。
- 360px 使用移动底部导航；768px、1024px、1440px 使用顶部账户导航。
- 截图位于 `web/e2e/screenshots/audit-2026-08-14/phase3-account/server-*.png`。

这份记录证明测试服务器上的 Web release 已切换并完成浏览器核验，不代表生产发布或用户验收完成。
