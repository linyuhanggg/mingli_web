# Phase 1 本地运行手册

本手册只适用于本地开发。所有默认值都是明确的 Fake 或本地占位，不得把生产密码、证书、商户号、短信密钥、邮件密钥或模型 Key 写进这些文件。

## 一次启动

~~~bash
docker compose --env-file infra/.env.example -f infra/compose.local.yml up --build -d postgres redis
docker compose --env-file infra/.env.example -f infra/compose.local.yml run --rm api alembic upgrade head
docker compose --env-file infra/.env.example -f infra/compose.local.yml up --build api worker web edge
~~~

入口：

- 同源网站与 API：`http://127.0.0.1:8080`
- Next.js 直连调试：`http://127.0.0.1:3000`
- FastAPI 直连调试：`http://127.0.0.1:8000/api/docs`
- 存活检查：`/api/v1/health/live`
- 数据库就绪检查：`/api/v1/health/ready`

## 进程边界

- `web` 只负责页面、私人应用壳和本地 `/api` rewrite；
- `api` 负责 Cookie、CSRF、Guest Session、Login Identity 和 Device Session；
- `worker` 是独立进程，目前只运行空任务源，不伪造 Phase 2 任务；
- PostgreSQL 是持久事实源；Redis 已建立但 Phase 1 的 Fake OTP 仍为进程内状态；
- `edge` 把 `/api/` 和网页保持在同一个浏览器 origin。

## Fake 边界

- OTP 固定本地验证码为 `246810`，只在 local/test 响应中显示；
- Fake Payment 永远不会产生已到账事实；
- Fake Model 只返回 schema 形状，占位稿永远不是 Accepted Copy；
- Fake Runtime 只用于能力合同测试，不执行真实命理计算。

任何真实渠道接入都必须先完成 `docs/PHASE_0_GATES.md` 对应 Gate，并通过独立 Adapter、验签、幂等和脱敏测试。

## 停止

~~~bash
docker compose --env-file infra/.env.example -f infra/compose.local.yml down
~~~

保留 PostgreSQL 数据卷是默认行为。只有明确确认不需要本地数据时，才由操作者自行删除卷。
