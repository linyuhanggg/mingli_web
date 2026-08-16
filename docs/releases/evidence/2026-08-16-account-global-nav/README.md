# 2026-08-16 账户页全局导航与 sticky 账户导航

## 目标

补回账户页缺失的公共功能导航，并让账户导航在滚动时固定在页头下方、桌面端居中。范围只涉及 Web 展示层，不改变 URL、接口、权限、账户数据或生产环境。

## 代码范围

- `web/src/components/site-header.tsx`
  - 抽出可复用的 `SitePrimaryNavigation`，公共页头和账户页共用同一套「术数、合参、工具、每日、知识内容、更多」入口。
- `web/src/components/private-shell.tsx`
  - 账户变体恢复公共主导航；普通 `/app` 侧栏和「返回公共首页」行为保持不变。
- `web/src/components/private-shell.module.css`
  - 账户导航使用 `position: sticky`，桌面端 `justify-content: center`，小屏横向浏览。
- `web/src/test/account-experience.test.tsx`
  - 锁定账户页公共主导航的入口和链接目标。

## 本地验证

- `npm run lint`：通过，0 warnings。
- `npm run typecheck`：通过。
- `npm test`：72 files / 456 tests 通过。
- `npm run build`：通过，Next.js 16.3.0，34 pages。
- Chrome 真实浏览器：360、768、1024、1440 通过；无水平溢出。桌面端六个公共入口可见，账户导航容器为 sticky；滚动 520px 后仍在页头下方。

## 测试服务器发布

- 地址：[http://106.14.10.235:18080/account](http://106.14.10.235:18080/account)
- release：`/opt/fateradar/releases/ui-preview-20260816-account-global-nav`
- 当前指针：`/opt/fateradar/current -> ui-preview-20260816-account-global-nav`
- 构建：服务端 `npm ci`、`BACKEND_INTERNAL_URL=http://127.0.0.1:8000 NODE_ENV=production npm run build` 和 standalone 准备均通过。
- 发布时发现新目录继承临时覆盖包的 0700 权限，systemd 报 `CHDIR Permission denied`；上一版已自动回滚。修正新 release 的 `web` 目录为 0755 后重新切换成功。
- 当前 `fateradar-test-api`、`fateradar-test-worker`、`fateradar-test-web`、`fateradar-test-admin` 均为 `active`。
- 公网返回 HTTP 200，HTML 有 `h1=我的`，不含「私人档案区」；页面在 1440、1024、768、360 四档无横向溢出。

## 生产边界

本次只发布到测试服务器。`https://fateradar.cn/` 生产环境没有修改。证据就绪，待用户验收。
