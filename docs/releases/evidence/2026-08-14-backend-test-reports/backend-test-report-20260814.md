# 后端测试失败日志整理（2026-08-14，第二版）

> 第二版更新：17:33 又复现了一轮同样的 4 例失败（第一版当时误判为"已过期的一次性瞬态失败"）。
> 本轮拿到了关键新证据：**失败运行时源码正在被保存**（见时间线）。当前状态已两次复跑全绿。

## 结论（TL;DR）

- **当前代码状态全绿**：17:36 单文件复跑 29/29 通过；17:37 全量复跑 730 passed / 92 skipped / 0 failed
  （66.9s，日志 `backend-test-verify-20260814-1736.log`）。
- 记录在案的失败共 **3 轮、全部是同一组用例**（owner XOR 迁移约束测试），且 **3 轮都发生在
  文件连续编辑窗口内**，事后复跑全部通过 → 定性为"编辑中间态 + 无日志"的流程问题，
  不是稳定代码缺陷。
- **本轮最大的教训**：3 轮失败都没有留下 stdout/traceback，导致只能靠 `lastfailed` 缓存猜失败模式。
  两个"排查基础设施"缺陷（无日志 + `--lf` 选不中历史失败）是最高优先级修复项。

## 日志清单

| 时间 | 位置 | 内容 | 状态 |
|---|---|---|---|
| 8/14 17:37 | `backend-test-verify-20260814-1736.log`（本次核验全量复跑） | `uv run --directory backend pytest tests ../tests/contract -q --tb=short -p no:cacheprovider` | ✅ 730 passed, 92 skipped |
| 8/14 17:36 | `/tmp/mingli_verify_rerun_20260814.log`（本次单文件复跑） | `pytest tests/test_reading_migrations.py -q --tb=long` | ✅ 29 passed |
| 8/14 17:33 | `backend/.pytest_cache/v/cache/lastfailed`（17:33:15 写入，无 stdout 存档） | 同一 owner XOR 测试 4 例（新 uuid 参数 ID） | ❌ 复跑通过，但**证明会复发** |
| 8/14 17:17 | `backend-test-20260814-171728.log` | 全量 `-q --tb=short` | ✅ 729 passed, 92 skipped |
| 8/14 15:52 | `backend/.pytest_cache/v/cache/lastfailed`（已被 17:33 运行覆盖） | 4 例 owner XOR（无 stdout 存档） | ❌ 复跑通过 |
| 8/12 06:17 | `.qoder/worktrees/production-ha-task0/backend/.pytest_cache/v/cache/lastfailed` | 同一测试 6 例 | ❌ 复跑通过 |
| 8/10 06:32 | `/tmp/check_1_pytest.log`（make check 流水线） | 460 passed / 90 skipped | ✅ 旧基线全绿 |

skip 明细：92 skipped = 82 个设计跳过（Linux Runtime gate retired）+ 10 个缺
`MINGLI_TEST_POSTGRES_URL` 的 reading worker 并发测试（见 `/tmp/skip-reasons.log`）。

## 失败用例整理

**唯一失败过的测试**：
`backend/tests/test_reading_migrations.py::test_owner_xor_is_enforced_by_the_migrated_database`

**断言语义**：对 `alembic upgrade head` 后的全新 SQLite 库（每用例独立 `tmp_path`），
向 `subject_profiles` / `reading_roots` 插入非法行，必须抛 `IntegrityError`：
1. `owner_user_id` 与 `owner_guest_session_id` 同时为 NULL；
2. 两者同时非空。

即校验 owner XOR CHECK 约束（`ck_subject_profiles_owner_exactly_one`、
`ck_reading_roots_owner_exactly_one`，迁移 `0003_reading_integrity_constraints.py`
通过 `batch_alter_table` + `create_check_constraint` 添加）。

**失败模式（仍是推断）**：缓存只留用例 ID、不留 traceback，三轮失败均无 stdout 存档。
可能的模式有两种，当前无法区分——这正是必须先修"日志"的原因：
- A. `DID NOT RAISE IntegrityError`：约束没生效（迁移链/重建丢约束）；
- B. `ERROR`（如 ImportError/CollectionError）：运行中撞上了别的文件保存一半的中间态，
  `alembic/env.py` 导入 `app.*` 模型时失败（env.py 一次性 import 全部领域 models）。

**parametrize 缺陷**：参数值在模块级用 `uuid4().hex` 生成（`tests/test_reading_migrations.py:161-165`），
每次 collect 用例 ID 都变 → `pytest --lf` 永远选不中历史失败，缓存条目成为"文物"，
也无法跨运行对齐失败记录。

## 时间线与根因分析

- **8/12 06:17**：worktree `production-ha-task0` 中 6 例失败（无日志）。
- **8/14 15:09–16:14**：`backend/app/**`、`backend/tests/**`、`tests/contract/**` 连续编辑
  （工作树至今约 40 个已改文件 + 100 个未跟踪文件，其中 22 个新迁移未提交）；
  **15:52** 运行失败 4 例。
- **8/14 17:17**：全量复跑全绿（729 passed）。
- **8/14 17:32:00**：`backend/app/adapters/model.py`、`adapters/runtime.py`、
  `readings/output_contracts.py`、`readings/service.py` 四个文件被保存；
  **17:33:11**：`backend/tests/test_readings_api.py` 被保存（套件用例数 729→730 与此一致）；
  **17:33:15**：pytest 缓存写入 4 例失败 —— 即这轮运行（约 17:31:5x–17:33:15）
  **恰好横跨了上述文件的保存时刻**。
- **8/14 17:36 / 17:37**：单文件与全量复跑均绿。

**最可能根因**：测试套件在源码编辑的中间态被执行（文件保存一半 / 迁移与断言暂时不对齐 /
env.py 批量 import 撞上部分写入的模块）。三轮失败全部命中编辑窗口、事后复跑全部通过，
模式一致。**不是稳定缺陷，但会反复发生**——只要继续"边改边跑全量且不留日志"。

## 排查与改进建议（按优先级）

### P0：修排查基础设施（本轮失败无法诊断的直接原因）

1. **Makefile 固化日志**。`backend-test` 目标改为自带 tee（注意 pipefail，别让管道吞退出码）：
   ```make
   SHELL := /bin/bash
   backend-test:
   	set -o pipefail; uv run --directory backend pytest tests ../tests/contract -q --tb=short 2>&1 | tee backend-test-$$(date +%Y%m%d-%H%M%S).log
   ```
2. **修掉 uuid4 参数 ID**。把 `test_reading_migrations.py:161-165` 的参数改成固定值 + 显式 ids：
   ```python
   @pytest.mark.parametrize(
       ("owner_user_id", "owner_guest_session_id"),
       [(None, None), ("owner-user-fixed", "owner-guest-fixed")],
       ids=["both-null", "both-set"],
   )
   ```
   之后 `pytest --lf` 才能复跑历史失败，缓存条目才可跨运行比对。

### P1：失败处置动作规范

3. **见到失败先带日志复跑一次**：`uv run --directory backend pytest tests/test_reading_migrations.py -q --tb=long -vv 2>&1 | tee ...`。
   无 traceback 的失败不做根因结论（本轮三种"失败模式"全靠猜，就是因为没日志）。
4. **避免在编辑窗口跑全量**，或至少：跑之前确认没有未保存文件 / 编辑器自动保存刚结束。
   本轮 17:33 的失败就是运行横跨了 17:32:00 与 17:33:11 两次保存。

### P2：防御与验证

5. **alembic batch 重建丢约束风险**（保留第一版建议）：SQLite 下 `batch_alter_table` 重建表可能
   静默丢 CHECK 约束。任何触碰 `subject_profiles` / `reading_roots` / `reading_idempotency_keys`
   的 batch 迁移，改完必跑 `uv run --directory backend pytest tests/test_reading_migrations.py -q`；
   排查时用 `sqlite3 xxx.sqlite3 ".schema subject_profiles"` 看 `ck_*` 是否还在，
   必要时 `alembic downgrade -1` 二分定位。
6. **尽快固化基线**：工作树当前 40 个已改文件、100 个未跟踪文件（含 22 个新迁移）。
   尽快 commit，否则下一次瞬态失败依旧无法 diff 回溯。

### P3：清理与补强

7. **清理过期缓存**（内容已存档于本报告，可删）：
   `backend/.pytest_cache` 与 `.qoder/worktrees/production-ha-task0/backend/.pytest_cache`。
8. **消化 10 个可执行 skip**：本机 127.0.0.1:5432 已有 Postgres：
   `MINGLI_TEST_POSTGRES_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli" make backend-test`。

## 复现命令

```bash
cd /Volumes/Lexar/code/mingli_web
make backend-test                                   # 全量（含 contract）
uv run --directory backend pytest tests/test_reading_migrations.py -q --tb=long -vv
MINGLI_TEST_POSTGRES_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli" make backend-test
```
