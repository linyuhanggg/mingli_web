# 2026-08-12 生产就绪基线（Task 0 证据）

> 本文只记录可复验证据，不构成上线批准。整体状态仍是 `production blocked / real traffic disabled`。

## 范围

执行 `docs/plans/2026-08-12-complete-production-ha-website.md` Task 0：固定可信基线并让根门禁全绿。执行环境为独立 worktree 分支 `worktree-production-ha-task0`，基线起点 `main @ 8c0c66e`。

## 修复项（最小改动，不含业务重构）

- Ruff 4 处 import 排序/未用导入：`backend/alembic/env.py`、`backend/app/readings/candidate_reference_closer.py`、`backend/tests/test_reading_worker.py`、`backend/tests/test_profiles_api.py`（自动修复）。
- mypy 6 处：
  - `backend/app/admin/repository.py`：`get_staff_by_email` / `get_active_session` 增加显式类型标注，消除 `no-any-return`。
  - `backend/app/api/admin.py`：`_settings` 改为 `cast(Settings, ...)`；删除 3 处已失效的 `# type: ignore`。
- Admin 测试缺口：`admin/` 新增 Vitest + testing-library（版本与 `web/` 对齐），`admin/src/test/admin-auth.test.tsx` 8 例覆盖 CSRF 头注入、无 Cookie 不带 CSRF、401 问题详情映射、非 JSON 错误回退、401 跳登录、会话展示、非 401 告警、退出登录链路。
- 根门禁收口：`Makefile` 新增 `admin-test` / `admin-check`；`make check` 现在包含 backend、web、admin 的 test/lint/typecheck 与 web、admin 生产构建（替代原独立 `admin-typecheck`）。

## 验证证据（本机，2026-08-12）

- `make check` 退出码 0。
- backend + contract：`528 passed, 82 skipped`（设置 `MINGLI_TEST_POSTGRES_URL=postgresql+asyncpg://localhost:5432/mingli_test`，本机 PostgreSQL 16.14）。
  - 82 个 skipped 全部为已退役的 Linux 模拟通道门禁（`Linux artifact/report acceptance is retired; native-full is the only Gate` / `Linux Runtime certification is retired`），属环境无关、原因明确的跳过。
  - 此前因缺 PG URL 跳过的 8 个并发/恢复门禁（`backend/tests/test_reading_worker.py`）本次实际执行并通过（单文件 15 passed）。
- web：`31 files / 250 passed`；admin：`1 file / 8 passed`；ruff、mypy（71 源文件）、eslint、tsc、Next 生产构建（web + admin）全绿。
- Alembic：空库 `0001 → 0008_admin_staff` 升级通过；旧 head `0007_api_idem_verify → head` 升级通过；`alembic heads` = `0008_admin_staff (head)`（单 head）；迁移后 FastAPI 应用可正常 startup/shutdown（`uvicorn app.main:app`，本机迁移库）。

## 遗留与边界

- 测试服 `fateradar-prod`（`106.14.10.235:18080`）current 仍为 `6ec1578`，落后于本地 `main`；本基线未触碰服务器。
- 仓库无 git remote；CI/CD 仍不存在（Task 9 内容）。
- `.qoder/**` 300+ 文件的资产性质（正式知识资产 vs 生成物）尚未裁决；按计划需用户批准的非破坏迁移方案后才能移出，本任务未删除任何内容。
- web 测试中 `route-scroll-policy.test.tsx`、`app-boundaries.test.tsx` 会打印 React hydration 警告（测试渲染方式导致，测试通过）；记为已知噪音，后续在 Task 12 质量收口时复核。
- `admin/next-env.d.ts` 为 Next 构建自动生成且已被仓库跟踪，本次随构建刷新。
