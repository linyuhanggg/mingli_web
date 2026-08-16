# 2026-08-16 测试服务器 Web UI 发布证据

## 结论边界

当前工作区的 Web UI 已发布到测试服务器公网预览入口：

- 地址：`http://106.14.10.235:18080/`
- SSH 主机别名：`fateradar-prod`（实际用途是代码测试服务器）
- 新 release：`/opt/fateradar/releases/ui-preview-20260816-codex-web`
- 旧 release：`/opt/fateradar/releases/ui-preview-20260815-public-products`，仍保留可回滚

这台机器固定是 `MINGLI_ENVIRONMENT=local`、Fake OTP、Fake Runtime、Fake Model、Fake Payment，不能当 staging 或 production。生产域名 `https://fateradar.cn/` 没有被本次操作修改，仍由 `/var/www/fateradar/current` 的静态占位页提供服务。

## 发布过程

服务器使用 Node `v22.22.1`、Next `16.3.0`，在新 release 内完成：

```text
BACKEND_INTERNAL_URL=http://127.0.0.1:8000 NODE_ENV=production npm run build
node scripts/start-standalone.mjs --prepare-only
```

随后通过原子 symlink 切换 `/opt/fateradar/current`，只重启 `fateradar-test-web`。后台、Worker、Admin 沿用原测试 release；没有上传本机 Mac 的 `.next` 产物，也没有上传环境文件或密钥。

## 机器与浏览器证据

- 首页 HTML：`200`，`51,987` bytes。
- 首页引用的 5 个 CSS：全部 `200`，全部为 `Content-Type: text/css`。
- 360px Chrome：`scrollWidth=360`、唯一 `h1=1`、样式表 `5`。
- 1440px Chrome：`scrollWidth=1440`、唯一 `h1=1`、样式表 `5`。
- 正文计算颜色为 `rgb(10, 10, 10)`；导航链接主要为 `rgb(82, 82, 82)`；没有浏览器默认蓝色 `#0000ee` 链接。
- 截图：[360px](./screenshots/360.png)、[1440px](./screenshots/1440.png)。

## 真实边界

这份记录只证明测试服务器上的 Web standalone 构建、CSS 资源和两档实际浏览器渲染通过。它不证明生产域名已部署，不证明真实 Runtime、真实模型、真实支付或用户验收已完成。服务器根盘本次结束时只剩约 `103MB`，没有删除旧 release 来换空间。
