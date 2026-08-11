---
kind: external_dependency
name: PostgreSQL 数据持久化与 Alembic 迁移
slug: postgresql
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
---

项目使用 PostgreSQL（asyncpg）作为唯一关系型数据库，本地默认库名 `mingli`，测试服使用 `fateradar_test`。所有 schema 变更通过 Alembic 版本化迁移（`backend/alembic/versions/0001..0008`），由 `make migrate` 或 `uv run --project backend alembic -c backend/alembic.ini upgrade head` 升级至 head。数据库连接串、认证凭据通过 `MINGLI_DATABASE_URL` 环境变量注入，不入库。