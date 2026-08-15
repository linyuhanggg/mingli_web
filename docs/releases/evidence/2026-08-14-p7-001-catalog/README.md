# P7-001 Catalog 生命周期基础

日期：2026-08-14（Asia/Shanghai）  
范围：当前未提交工作树；验证本地 Catalog 服务、Admin Catalog API、Admin 商品管理命令面和商品页真实读取，不连接真实支付渠道或生产 Admin。

## 本轮补齐

- 新增 `CatalogService`，可创建 `ProductFamily`、草稿 `ProductVersion` 与渠道 `ProductOffer`。
- ProductVersion 只有在存在启用 Offer 时才能从 `draft` 发布为 `active`；重复发布是幂等的。
- 已发布版本可以退役；退役后保留价格、币种、合同和追问快照，并拒绝新增 Offer 或重新启用 Offer。
- Offer 可以独立启用/停用，不改写已发布版本语义。
- 输入边界覆盖空值、负价格/追问参数、重复 family/version/channel SKU 和三位币种规范化。
- Admin Catalog API 已提供商品族、版本、Offer 的读取/创建、发布、退役和报价启停；写请求要求 Staff CSRF、`ops`/`superadmin` 角色和操作原因，并追加 `AdminAuditEvent`。
- Admin `/products` 与 `/products/[id]/versions` 已读取真实 Catalog 响应；`ops`/`superadmin` 可在带操作原因的命令面创建商品族、版本、报价，并发布/退役版本、启停报价；命令通过服务端 CSRF/RBAC/状态校验并在成功后刷新真实 Catalog，不把通用演示写入当作真实操作。

## 可复现检查

```text
uv run --project backend pytest backend/tests/test_catalog_service.py backend/tests/test_commerce_models.py backend/tests/test_commerce_repository.py backend/tests/test_commerce_services.py backend/tests/test_payment_reconciliation.py -q
17 passed

uv run --project backend pytest backend/tests/test_admin_catalog.py backend/tests/test_openapi_alignment.py -q
7 passed

npm --prefix admin test -- --run
11 test files / 62 tests passed

npm --prefix admin run lint
npm --prefix admin run typecheck
npm --prefix admin run build
All passed.

uv run --project backend pytest backend/tests/test_migrations.py -q
2 passed

uv run --project backend ruff check backend/app/commerce backend/tests/test_catalog_service.py
All checks passed!

uv run --project backend mypy backend/app/commerce
Success: no issues found in 8 source files

MINGLI_DATABASE_URL=sqlite+aiosqlite:////tmp/mingli-catalog-check.0LzObc/db.sqlite3 uv run --project backend alembic -c backend/alembic.ini upgrade head
All revisions through 0023_payment_attempt_unique applied.

MINGLI_DATABASE_URL=sqlite+aiosqlite:////tmp/mingli-catalog-check.0LzObc/db.sqlite3 uv run --project backend alembic -c backend/alembic.ini check
No new upgrade operations detected.
```

## 未覆盖边界

该证据只证明本地服务层、Admin API、商品管理命令面和商品页读取能承载 Catalog 生命周期。P7-001 仍为 `IN_PROGRESS`：真实商品发布审批、支付渠道映射、外部支付/生产 Admin 接线尚未完成；不把这组本地测试当作 P4 用户 UI 验收或 P12 外部环境准入。
