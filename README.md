# mingli_web

当前权威方向是：**先做响应式网站，后做原生 iOS App，共用同一套账户、商品、权益和命理解读后端。** Phase 0 与 Phase 1 已建立可运行基础：Next.js 公共/私人网站壳、FastAPI、PostgreSQL 首版迁移、独立 Worker、Guest Session、手机号/邮箱 Fake OTP、Cookie Device Session、CSRF 和同源 `/api`。

## 权威合同

- 产品方向：[docs/PRODUCT_DIRECTION.md](./docs/PRODUCT_DIRECTION.md)
- 商业化与技术蓝图：[docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md](./docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md)
- 共同语言：[CONTEXT.md](./CONTEXT.md)
- 架构决策：[docs/adr](./docs/adr)
- Phase 0 外部 Gate：[docs/PHASE_0_GATES.md](./docs/PHASE_0_GATES.md)
- Phase 2 第一版代码候选证据：[docs/releases/2026-08-10-mingli-v51-web-phase2.md](./docs/releases/2026-08-10-mingli-v51-web-phase2.md)
- 当前实施计划：[docs/plans/2026-08-09-phase-0-1-web-foundation.md](./docs/plans/2026-08-09-phase-0-1-web-foundation.md)

## 目录边界

~~~text
web/                    Next.js App Router + TypeScript
backend/app/            FastAPI 模块化单体与领域模块
backend/worker/         独立异步任务进程入口
backend/alembic/        PostgreSQL 迁移
contracts/openapi/      同源 API 合同
contracts/schemas/      共享 JSON Schema
infra/                  本地容器、Nginx 与运行手册
tests/contract/         跨模块合同测试
~~~

早期小程序骨架已由 Git 提交 `15cbc95` 完整保全，随后从当前工作树移除。网站不沿用小程序的目录、状态或客户端架构。

## 本机运行

要求：Node.js 22+、Python 3.12、uv、PostgreSQL 16。Docker 可选。

~~~bash
uv sync --project backend --group dev
npm install --prefix web

# 默认连接本机 mingli / mingli-local；需要时用 MINGLI_* 环境变量覆盖
uv run --project backend alembic -c backend/alembic.ini upgrade head

# 分别启动三个进程
uv run --project backend uvicorn app.main:app --app-dir backend --reload --port 8000
uv run --directory backend python -m worker.main --poll-interval 2
npm --prefix web run dev
~~~

浏览器访问 `http://127.0.0.1:3000`。Next.js 把相对 `/api/*` 转发到 `BACKEND_INTERNAL_URL`，默认是 `http://127.0.0.1:8000`；正式浏览器不会看到跨域 API 地址。

如果本机有 Docker Compose，可按 [infra/PHASE_1_RUNBOOK.md](./infra/PHASE_1_RUNBOOK.md) 从 `http://127.0.0.1:8080` 启动完整同源入口。

## 测试与质量门

~~~bash
make test
make check
~~~

等价的独立命令：

~~~bash
uv run --project backend pytest backend/tests tests/contract -q
uv run --project backend ruff check --config backend/pyproject.toml backend tests
uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/worker
npm --prefix web test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
~~~

## Fake 与安全边界

- 本地验证码固定为 `246810`，仅 local/test 响应可见；不会发送真实短信或邮件。
- Fake Payment 永远不能产生到账事实。
- Fake Model 的结构占位永远不是 Accepted Copy。
- Fake Runtime 不执行真实命理计算。
- Cookie 中是随机不透明 token；数据库只保存会话哈希。
- 手机号/邮箱规范化后使用带服务端密钥的 HMAC 标识，业务外键始终是内部 User UUID。
- 仓库没有真实支付、短信、邮件、模型或命理运行时密钥；生产值必须由 Secret Manager/运行环境注入。

Metis 紫薇及其开源仓库只作为信息层级和交互参考，不复制其品牌资产、具体版式、私有 API 或支付参数。

## 下一阶段入口

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

2026-08-10 的 Phase 2 记录当前仅为“第一版代码候选 / production blocked”：Task 11/12 当前工作树的 `make check`、`make test` 已通过，但候选尚未形成不可变提交，生产原始证据和外部门禁仍为 Pending。`real traffic` 保持 disabled，不可部署或放量。

Phase 2 先冻结 Command/Result、Candidate 与 Output Contract 四组 JSON Schema，再深化 Runtime/Model Ports、三类 Request Compiler、Narrative Guard 和显式 Reading Orchestrator。真实 Runtime 在 Mac mini 原生全量回归通过后才可接入，不再等待 Linux 模拟认证。当前建档、今日、近七日、六爻与结果页均调用同源 API；浏览器只展示服务端返回的 Accepted Copy，不在客户端伪造排盘结果。
