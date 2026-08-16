# P12-003 测试 PostgreSQL 备份恢复演练（2026-08-14）

## 结果

状态：`IN_PROGRESS`。备案前可以做的测试数据库恢复演练已完成，但这不是生产恢复门禁的完整通过。

```text
server: fateradar-prod（代码联调与验收机）
backup: ui-preview-20260814-ce402f0923ec-pre-migration.dump
backup_sha256: 已在服务器对应 .sha256 文件核对
restore_database: 临时唯一数据库，演练后已删除
restored_alembic_version: 0014_reading_delivery
restored_public_tables: 43
restored_runtime_release_rows: 8
temporary_restore_artifacts: 已清理
```

## 演练过程

1. 迁移前生成非空 PostgreSQL custom-format dump，并核对 SHA-256。
2. 由于备份目录是 root-only，先由 root 将 dump 复制到 `postgres:postgres 0600` 的临时路径。
3. 用 `pg_restore --exit-on-error --no-owner --no-privileges` 恢复到临时数据库。
4. 核对 `alembic_version`、public 表数量和 Runtime Release 行数。
5. 删除临时数据库和临时 dump；持久测试数据库没有被恢复过程覆盖。

## 尚未覆盖

对象存储、Runtime 状态盘、生产 PostgreSQL、跨主机恢复、恢复时间目标和真实用户数据恢复仍未演练；因此 P12-003 保持 `IN_PROGRESS`。
