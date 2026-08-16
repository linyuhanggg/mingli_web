# P10/P11 寻时定盘真实 SQL 纵切片

日期：2026-08-16（Asia/Shanghai）

## 本轮完成

新增真实纵切测试：HTTP API 创建时间校验 Job，V53 one-shot Runtime 负责 `Prepare/Complete`，SQL Worker 在 PostgreSQL 中完成三阶段推进，并在 Accepted 同一事务内落下 `AcceptedCopy + ReadingDocumentV1`。

- API 返回 `201`，`capability_id= time-check`、`product_id= time-check`。
- Worker 三次 `run_once()` 均处理成功，第四次确认队列为空。
- PostgreSQL 中最终为 `ReadingVersion=accepted`、`ReadingJob=complete`、`AcceptedCopy=1`、`ReadingDocument=1`。
- 文档为 `reading-document/v1`，ViewModel 为 `time-check-view/v1`。
- ViewModel 保留 12 个时辰候选、2 条结构化事件、12 条候选排序和 2 条事件匹配，状态为 `candidate_evidence_ranked/structured_evidence`。
- Web `/result` 返回的顶层 `view_model` 与文档中的 `view_model` 完全一致。
- Admin 只展示候选数、事件数、排序数和状态；不返回 `subject_ref`、候选明细、事件 ID/日期、出生资料、坐标、证据分或“最可能时辰”。

## 真实运行证据

测试命令：

```text
MINGLI_RUN_REAL_RUNTIME_TESTS=1 \
MINGLI_TEST_POSTGRES_URL=<local-postgresql-test-url> \
uv run pytest tests/test_time_check_postgres_vertical.py -q -vv
```

结果：`1 passed in 6.11s`。

测试把 V53 release 复制到 APFS 临时目录，并按 release manifest 恢复私有文件模式；PostgreSQL 只使用随机 schema，测试结束自动删除。模型仍为本地 `FakeModelGateway`，所以这份证据证明的是 Runtime、Worker、数据库和文档边界，不是生产模型质量。

## 公开边界

这份证据证明了有界结构化事件证据排序，不等于完整古法校时、候选淘汰规则或“最可能时辰”结论。`known_events` 自由文本仍只计数，只有结构化事件事实参与匹配。

生产域名本轮没有部署：`https://fateradar.cn/` 仍由 Nginx 提供 907 字节静态占位页，生产 API 也尚未接入。新版 UI 只在测试入口 `http://106.14.10.235:18080/`，该入口固定是 `local + Fake`，不能当生产证据。
