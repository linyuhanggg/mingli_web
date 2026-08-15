# P7-005 Admin 权益调整证据

日期：2026-08-14（Asia/Shanghai）  
范围：Admin 认证后的权益发放、补偿、撤回，以及追加式权益账本和操作审计。

## 已验证行为

- `grant` 追加 `GRANT` 事件；相同 `source_ref` 重放返回原事件，不重复写账本或审计；
- `compensate` 使用独立 `admin_compensation` 来源和独立 entitlement id，仍遵守正式账本的追加式语义；
- `revoke` 根据当前账本状态选择 `RELEASE`、`EXPIRE` 或 `REVERSE`，不修改余额字段；
- 写操作必须同时通过 Admin session、CSRF 和 `finance`/`ops`/`superadmin` 角色门禁；
- 每个新调整写入 `AdminAuditEvent`，记录操作人 session、原因、对象、事件类型、数量和来源引用；
- 事件历史可按用户和 entitlement 查询，响应保持 private/no-store 边界。

## 定向结果

```bash
uv run --project backend pytest \
  backend/tests/test_admin_entitlements.py \
  backend/tests/test_openapi_alignment.py -q
```

结果：`7 passed`。

## 全量回归

同日 `make check` 结果：Backend `622 passed, 92 skipped`；Ruff、mypy（103 source files）、Web Vitest `54 files / 388 tests`、Admin Vitest `11 files / 60 tests`、两端 lint/typecheck/production build 全通过。

## 边界

证据使用本地 SQLite API fixture 和冻结 Admin OpenAPI 合同，证明本地账本生命周期、权限、审计和重放行为；不代表真实支付渠道、生产运营人员、生产数据库或 P12 备份/恢复/发布门禁。`/entitlements` 页面仍由 P3/P9 的 Admin 页面接线任务负责，本证据不把现有通用页面冒充完整运营 UI，也不替代 P4-006/P4-007。
