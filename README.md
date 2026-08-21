# mingli_web

`mingli_web` 是一个响应式命理产品网站与独立管理后台。产品开发遵守三层边界：

- 自有 `mingli-master` Runtime 是盘面、算法事实、古籍证据与连续状态的唯一权威；
- 青囊实站审计用于确定产品层级、功能入口与“免费确定性盘面 → 深度解读”的任务模式；
- METIS 实站与其公开 MIT 仓库用于确定表单、组件、工作台、信息密度和响应式表现。

当前正式产品没有品牌名。旧 `FateRadar` 名称、墨绿金色皮肤和旧三能力页面均已废弃；代码、域名或运维文件中的同名标识只作为待迁移的历史基础设施标识，不是产品权威。

## 唯一开发权威

范围、依赖、进度、门禁、证据和下一步只看 [docs/CHECKLIST.md](./docs/CHECKLIST.md)。

冻结合同各司其职，不互相复制：

- 共同语言：[CONTEXT.md](./CONTEXT.md)
- 视觉、组件、交互与响应式：[DESIGN.md](./DESIGN.md)
- 算法、Provider、Orchestrator 与 `ReadingDocumentV1`：[docs/MINGLI_V51_WEB_INTEGRATION.md](./docs/MINGLI_V51_WEB_INTEGRATION.md)
- 不可逆架构决策：[docs/adr](./docs/adr)
- 可复验机器与浏览器证据：`docs/releases/evidence/`

禁止新增平行的 `HANDOFF`、`docs/plans/*`、产品蓝图或第二份 checklist。新需求进入 `docs/CHECKLIST.md` 对应 backlog；改变已经验收的产品地图、页面层级或视觉合同，必须先记录影响并由用户明确批准。

## 当前开发基线

当前 `main` 是唯一基线。保留后端身份、档案、解读编排、Worker、Runtime/Model Adapter、Guard、数据库迁移、合同和基础设施；公共 Web 与 Admin 的产品表现层按新权威重建。旧 UI 分支只用于取证，不整体合并。

测试版先预制公共站、用户区、全部产品流程和完整后台的全路由、全状态、全尺寸 UI；真实产品路由不允许 Fixture、假盘、假支付或 raw JSON。只有 `/_ui-lab` 可以展示明确标记的 UI 演示数据。

## 目录边界

```text
web/                    Next.js 公共站、产品任务与账户区
admin/                  独立 Next.js 管理后台
backend/app/            FastAPI 模块化单体与领域模块
backend/worker/         独立异步任务进程
backend/alembic/        PostgreSQL 迁移历史
contracts/openapi/      同源 API 合同
contracts/schemas/      共享 JSON Schema 与 ViewModel 合同
core/mingli-master/     从 mingli-master-skill 移植的算法源码
infra/                  本地容器、Nginx 与运行手册
tests/contract/         跨模块与权威文档合同测试
docs/releases/evidence/ 机器、浏览器和发布证据
```

## 本机运行

要求：Node.js 22+、Python 3.12、uv、PostgreSQL 16。Docker 可选。

```bash
uv sync --project backend --group dev
npm install --prefix web
npm install --prefix admin

uv run --project backend alembic -c backend/alembic.ini upgrade head

uv run --project backend uvicorn app.main:app --app-dir backend --reload --port 8000
uv run --directory backend python -m worker.main --poll-interval 2
npm --prefix web run dev
npm --prefix admin run dev
```

Web 默认访问 `http://127.0.0.1:3000`，相对 `/api/*` 由 Next.js 转发到 `BACKEND_INTERNAL_URL`。完整同源入口参见 [infra/PHASE_1_RUNBOOK.md](./infra/PHASE_1_RUNBOOK.md)。Admin 仍是独立应用与 Staff Session，不与普通用户会话混用。

如果旧本机 SQLite 开发库曾使用长迁移 ID，先备份再按 [infra/PHASE_1_RUNBOOK.md](./infra/PHASE_1_RUNBOOK.md) 的既有映射修复；不得对 PostgreSQL 猜测或重写迁移历史。

## 测试与质量门

```bash
make test
make check
```

需要单独定位时使用：

```bash
uv run --project backend pytest backend/tests tests/contract -q
uv run --project backend ruff check --config backend/pyproject.toml backend tests
uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/worker
npm --prefix web test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix admin run lint
npm --prefix admin run typecheck
npm --prefix admin run build
```

自动化绿灯只说明对应合同通过。UI 完成还必须在 360、768、1024、1440 四档真实浏览器逐路点击、截图、检查键盘/焦点/响应式，并由用户亲自确认；DOM 存在、CSS 正则或 checklist 勾选都不能替代。

## Fake、数据与安全边界

- Fake Runtime、Model、OTP 与 Payment 只用于本地测试或 `/_ui-lab`，不能产生生产事实。
- 浏览器不排盘，不猜 Provider 字段，不展示 raw JSON、snake_case 或内部引用。
- 用户本人和有权限的后台页面可完整显示业务资料；数据库静态存储仍加密。
- 密码只存不可逆哈希；验证码、Cookie、`state_token`、API Key、数据库口令和模型秘密永不进入用户或后台页面。
- 支付回跳不是到账事实；服务端验签通知或主动查单才可授予权益。
- 迁移历史只追加。旧 dogfood grant 不是正式商业账本，待正式账本落地后用新迁移退出。

## Runtime 发布门禁

Runtime Release 始终完整包含 13 个 Provider、55 个古籍 reference pack 与 1328 条 evidence index；产品地图不会反向裁剪发布物。13 个 Provider 是内部能力模块，不是 13 个用户产品入口。

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

生产源只使用固定、可验签的 Runtime Release，不把任意 Skill 工作树当发布物。完整实施顺序和当前阻塞见 [docs/CHECKLIST.md](./docs/CHECKLIST.md)。
