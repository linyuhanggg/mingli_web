# P6-007 PostgreSQL 并发验收证据

日期：2026-08-14（Asia/Shanghai）  
范围：`ReadingJobWorkSource` 的 PostgreSQL claim/lease 事务，以及 `ReadingIdempotencyKey` 的 user/guest owner 并发唯一性。

## 结果

在本机 PostgreSQL 16 测试数据库 `mingli_test` 上运行：

```bash
MINGLI_TEST_POSTGRES_URL='postgresql+asyncpg://<local-role>@127.0.0.1:5432/mingli_test' \
uv run --project backend pytest backend/tests/test_reading_worker.py -q
```

结果：`17 passed in 2.57s`。

其中 P6-007 直接覆盖：

- 两个 worker 同时 claim 同一任务时只有一个事务成功，另一个不会重复领取；
- 同一 user owner 的相同幂等键并发插入最终只保留一条记录；
- 同一 guest owner 的相同幂等键并发插入最终只保留一条记录；
- user 与 guest 使用独立 partial unique index，不再依赖 nullable 三列复合唯一约束。

测试 fixture 只创建随机 schema，结束后删除该 schema；没有修改正式业务表或生产数据库。

## 边界

这份证据证明迁移后的模型和独立事务并发行为在本机 PostgreSQL 上成立。它不替代生产数据库迁移执行、备份恢复演练或 P12 外部环境准入；那些门禁仍按 `docs/CHECKLIST.md` 单独记录。
