# 施工交接快照（2026-08-12）

> 本文是给后续施工会话的准确断点说明。只描述已验证的现状与下一步，不替代任何权威合同。与合同冲突时，以权威合同为准：`docs/PRODUCT_DIRECTION.md`、`docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md`、`docs/adr/`、`docs/PHASE_0_GATES.md`。
>
> 历史快照 [HANDOFF_SNAPSHOT_2026-08-11.md](./HANDOFF_SNAPSHOT_2026-08-11.md) 保持原样不改。

## 当前断点

- `main @ 8c0c66e`（`feat(platform): 增加管理后台与认证感知命理解读体验`）；仓库无 git remote。
- 进行中的工作：生产就绪计划 Task 0，在 worktree 分支 `worktree-production-ha-task0` 执行，尚未合并回 `main`。
- Alembic head：`0008_admin_staff`（单 head）。
- 测试服务器 `fateradar-prod`（阿里云上海 ECS `i-uf67fkafnm3w0abdmz3m`，入口 `106.14.10.235:18080`）current 仍为 `6ec1578`，落后于本地 `main`；本轮未触碰服务器。

## 权威计划

当前实施计划已切换为：[docs/plans/2026-08-12-complete-production-ha-website.md](./plans/2026-08-12-complete-production-ha-website.md)（完整生产网站与高可用，Task 0–13，里程碑 M0–M5）。旧计划 `docs/plans/2026-08-09-mingli-v51-web-integration.md` 的 Phase 0/1 与 Task 1–12 已闭环，作为历史保留。

## Task 0 状态：实现完成，证据已归档

- 根门禁由红转绿：修复 Ruff 4 处、mypy 6 处（仅 import/类型最小修复）。
- admin 控制台新增 Vitest 套件（8 例：登录态/401/CSRF/私人路由），并已把 admin 的 test/lint/typecheck/build 全部纳入根级 `make check`。
- PostgreSQL 16 门禁实测：`MINGLI_TEST_POSTGRES_URL` 指向本机 PG 16.14，`528 passed, 82 skipped`；82 个 skipped 均为已退役 Linux 模拟门禁（原因明确）；原 8 个 PG 并发/恢复门禁实际执行通过。
- Alembic 空库 `0001→0008`、旧 head `0007→head` 升级通过；迁移后应用可启动。
- 证据：[docs/releases/2026-08-12-production-readiness-baseline.md](./releases/2026-08-12-production-readiness-baseline.md)。

## 待用户裁决 / 下一步

1. `.qoder/**` 300+ 文件的性质裁决：正式知识资产 or 生成物（生成物需批准后的非破坏迁移计划，本轮未删除任何文件）。
2. Task 0 审查通过并合并后，进入 Task 1（冻结完成定义、SLO 与生产准入合同）。
3. 并行可做（只读、无成本）：现有 ECS 资产盘点（Task 10 Step 1），纠正 nmem 中「杭州 u2a」选型记录与上海实机的冲突。
4. 任何外部副作用（git remote、云资源变更、商户/备案/短信、真实流量）执行前必须再次获得用户授权。

## 不变的生产保护（尚未上线）

- production SMTP OTP 因内存 challenge/限流被拒；`MINGLI_REAL_TRAFFIC_ENABLED=true` 在 production 被无条件拒绝；生产 Nginx API 路由固定 `503 api_not_deployed`；只有单机 test systemd。
