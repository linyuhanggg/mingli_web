# 2026-08-14 四视口逐路浏览器验收证据

这轮在本地 standalone 生产构建上执行 Web/Admin 路由矩阵。测试逐路访问、等待文档加载、检查关键浏览器错误与横向溢出，并在证据模式下为每条路由留下当前实际视口截图和 JSON manifest。

## 结果

| 应用 | 路由数 | 视口 | 截图 | Manifest | 结果 |
| --- | ---: | --- | ---: | --- | --- |
| Web | 66 | 360×800、768×1024、1024×768、1440×900 | 264 | [Web manifests](./web/) | 4/4 通过 |
| Admin | 40 | 360×800、768×1024、1024×768、1440×900 | 160 | [Admin manifests](./admin/) | 4/4 通过 |

所有记录的 HTTP 状态为 200，截图文件均存在且为 JPEG；manifest 记录请求路由、最终路径、HTTP 状态、视口、页面实际 `data-state` 集合、截图相对路径、生成时的 Git HEAD、测试名、负向检查和审阅时间。本轮 manifest 的 `reviewStatus` 为 `reviewed`；没有显式传入审阅时间时，工具会标为 `automated-only`。

同一工作树随后运行了现有无障碍浏览器合同：Web `e2e/accessibility.spec.ts` 四视口 20/20 通过，Admin 同文件四视口 20/20 通过。覆盖移动导航键盘操作与焦点恢复、跳过链接、200%/400% 等价视口无横向溢出、reduced motion、表单错误聚焦和命名 landmark。测试期间后端 API 未启动，Next 代理记录了连接拒绝；前端仍按真实 unavailable 状态渲染，这不计作浏览器错误，也不代表后端服务已接通。

## 复现

先分别完成生产构建，并启动：

```bash
cd web && npm run build
cd ../admin && npm run build
```

然后分别以 `PORT=3000` 和 `PORT=3001` 启动 standalone 服务，再运行：

```bash
cd web
GIT_COMMIT=$(git rev-parse HEAD) \
ROUTE_EVIDENCE_REVIEWED_AT=2026-08-14T10:20:00+08:00 \
ROUTE_EVIDENCE_DIR="$PWD/../docs/releases/evidence/2026-08-14-route-acceptance/web" \
BASE_URL=http://127.0.0.1:3000 \
npx playwright test e2e/route-matrix.spec.ts \
  --grep "public and private route matrix"

cd ../admin
GIT_COMMIT=$(git rev-parse HEAD) \
ROUTE_EVIDENCE_REVIEWED_AT=2026-08-14T10:20:00+08:00 \
ROUTE_EVIDENCE_DIR="$PWD/../docs/releases/evidence/2026-08-14-route-acceptance/admin" \
ADMIN_BASE_URL=http://127.0.0.1:3001 \
npx playwright test e2e/route-matrix.spec.ts \
  --grep "Admin route catalog"
```

未设置 `ROUTE_EVIDENCE_DIR` 时，路由矩阵仍只做普通回归，不写截图文件。当前证据对应 Git HEAD `f488fa4d6eaa989b708b14d87b747ee931468829`；工作树另有未提交改动，不能把该 HEAD 当作全部工作树内容的快照。

## 边界

这份证据证明本地 standalone 生产构建的逐路四视口自动化结果，不等同于 P4-006 的来源截图同视口视觉比对，也不等同于 P4-007 的用户逐页批准。后端未启动时页面保留真实的 `需要登录`、`暂不可用` 或错误状态，没有用 fixture 冒充生产数据。
