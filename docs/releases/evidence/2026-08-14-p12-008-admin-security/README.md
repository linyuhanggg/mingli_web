# P12-008 Staff 会话与审计本地证据

日期：2026-08-14（Asia/Shanghai）  
范围：Admin Staff Session 查询、单会话强退、CSRF/RBAC、脱敏响应和审计记录；未宣称生产秘密治理、媒体授权或完整员工管理已完成。

## 本轮补齐

- 新增 `GET /api/v1/admin/sessions`，仅 `superadmin` 可读取员工会话元数据；返回员工、状态、最近活动、到期和撤销时间，不返回 `token_hash` 或 `csrf_token_hash`。
- 新增 `POST /api/v1/admin/sessions/{session_id}/revoke`，要求 Admin CSRF、非空操作原因和 `superadmin`；成功后写入 `staff.session.revoked` 审计事件。
- 新增 Staff 状态停用/恢复、角色调整和 `password-reset` 命令；密码只在服务端哈希，变更会撤销目标既有会话，审计只保留原因、目标和撤销数量。
- Admin `/sessions` 页面已接真实 API，展示有效/过期/已撤销状态；强退命令只对有效会话出现，原因输入和服务端失败状态可见。
- Admin `/staff` 页面已接员工列表、状态、角色和密码重置命令；密码输入不会进入列表、响应或审计。
- Admin OpenAPI 已登记 tag、operationId、请求体和安全响应 schema。

## 可复现检查

```text
uv run --project backend pytest \
  backend/tests/test_admin_sessions.py \
  backend/tests/test_openapi_alignment.py \
  backend/tests/test_admin_audit.py \
  backend/tests/test_admin_notifications.py \
  backend/tests/test_admin_reconciliation.py -q
16 passed

pnpm exec vitest run \
  src/components/admin-sessions-surface.test.tsx \
  src/components/admin-audit-surface.test.tsx \
  src/components/admin-notifications-surface.test.tsx \
  src/components/admin-reconciliation-surface.test.tsx
5 files / 11 tests passed

uv run --project backend ruff check \
  backend/app/api/sessions_admin.py backend/app/api/router.py \
  backend/app/commerce/schemas.py backend/tests/test_admin_sessions.py
All checks passed

uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/worker
Success: no issues found in 111 source files

pnpm exec eslint src/components/admin-sessions-surface.tsx \
  src/components/admin-sessions-surface.test.tsx \
  src/components/admin-catalog-page.tsx src/lib/admin-sessions.ts
pnpm exec tsc --noEmit
All passed
```

## 边界

本证据只覆盖本地 Staff Session 查询/撤销、员工角色/状态/密码命令、Admin CSRF/RBAC、响应脱敏和审计写入。员工创建邀请、系统设置/健康面、真实媒体授权、生产密钥轮换和外部 P12 门禁仍未完成，因此 P3-010、P9-004 与 P12-008 继续保持 `IN_PROGRESS`。
