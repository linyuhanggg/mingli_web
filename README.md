# mingli_web

> Runtime 永远装完整 5.1（13 Provider / 55 古籍 / 1328 evidence）；P0 产品只曝光 bazi、fortune、liuyao。生产源只用签名 release + `scripts/verify_frozen_runtime_release.py`，不要拿脏 skill 工作树当源。

当前权威方向是：**先做响应式网站，后做原生 iOS App，共用同一套账户、商品、权益和命理解读后端。** Phase 0 与 Phase 1 已建立可运行基础：Next.js 公共/私人网站壳、FastAPI、PostgreSQL 首版迁移、独立 Worker、Guest Session、手机号/邮箱 Fake OTP、Cookie Device Session、CSRF 和同源 `/api`。

## 文档

**进度、门禁、下一步（唯一清单）：** [docs/CHECKLIST.md](./docs/CHECKLIST.md)

冻结合同（不是进度日志，不随施工改状态）：

- 共同语言：[CONTEXT.md](./CONTEXT.md)
- 视觉：[DESIGN.md](./DESIGN.md)
- 产品方向：[docs/PRODUCT_DIRECTION.md](./docs/PRODUCT_DIRECTION.md)
- 商业与技术蓝图：[docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md](./docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md)
- 算法接入：[docs/MINGLI_V51_WEB_INTEGRATION.md](./docs/MINGLI_V51_WEB_INTEGRATION.md)
- 架构决策：[docs/adr](./docs/adr)
- 机器证据：`docs/releases/evidence/`（只存可复验产物，不写叙事日志）

不要新增 HANDOFF / plans / releases 施工 md；只更新 `CHECKLIST.md` 勾选与断点。

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

如果本机持久 SQLite 开发库曾在 `2026-08-10` 的迁移 ID 修复前跑到旧的
`0003`、`0006` 或 `0007`，先保留数据库备份，再把 `alembic_version`
中的旧 ID 映射为同一份 schema 的短 ID；这一步只用于旧 SQLite 开发库，
不要对 PostgreSQL 执行：

~~~sql
UPDATE alembic_version
SET version_num = CASE version_num
  WHEN '0003_reading_integrity_constraints' THEN '0003_reading_integrity'
  WHEN '0006_generation_attempt_model_receipt' THEN '0006_model_receipt'
  WHEN '0007_reading_api_idempotency_and_verification' THEN '0007_api_idem_verify'
  ELSE version_num
END;
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

## 进度与下一阶段

见 **[docs/CHECKLIST.md](./docs/CHECKLIST.md)**。

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。  
当前总判：`联调主链路已通` · `production blocked` · `real traffic disabled`。浏览器只展示服务端 Accepted Copy / 公开 fact 投影，不在客户端伪造排盘。
