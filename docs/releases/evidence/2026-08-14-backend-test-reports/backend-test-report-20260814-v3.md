# 后端测试失败日志整理（2026-08-14，第三版 / 终版核验）

> 本版在第二版（17:41）基础上补了三件事：
> 1. **17:53 全量复跑再次全绿**（730 passed / 92 skipped / 0 failed，66.0s），当前代码状态无失败；
> 2. **用 pytest 源码坐实了 lastfailed"文物化"机制**，并在 17:53 这轮绿跑中现场复现；
> 3. **收窄了失败模式推断**：同文件其他 `upgraded_engine` 用例都通过、只有 owner XOR 4 例失败
>    → 更偏向"约束当轮没建出来（DID NOT RAISE）"，而非整文件 import 崩掉。

## 结论（TL;DR）

- **当前全绿，无稳定缺陷**。记录在案的失败共 3 轮（8/12 worktree、8/14 15:52、8/14 ~17:33），
  全部是同一组用例（owner XOR 迁移约束），全部发生在源码连续编辑窗口内，事后复跑全绿。
- 三轮失败**都没有留下任何 stdout/traceback**（Makefile `backend-test` 不带 tee），
  加上用例 ID 每次收集都变（uuid4），导致至今无法 100% 锁定失败模式——
  **这是流程/基础设施问题，不是代码问题**。
- 最可能根因：测试在"编辑中间态"被执行——收集那一刻，0003 迁移或测试断言处于半保存/重构中间态，
  CHECK 约束没建出来 → 4 例断言 `DID NOT RAISE IntegrityError`。

## 一、日志与证据清单

| 时间 | 位置 | 内容 | 状态 |
|---|---|---|---|
| 8/14 17:53 | `/tmp/backend-test-fresh-20260814-175217.log`（本次核验全量复跑） | `uv run --directory backend pytest tests ../tests/contract -q --tb=short` + tee | ✅ 730 passed, 92 skipped, 66.0s |
| 8/14 17:37 | `backend-test-verify-20260814-1736.log` | 全量复跑（`-p no:cacheprovider`） | ✅ 730 passed, 92 skipped |
| 8/14 17:36 | `/tmp/mingli_verify_rerun_20260814.log` | 单文件 `test_reading_migrations.py` | ✅ 29 passed |
| 8/14 17:33:15 | `backend/.pytest_cache/v/cache/lastfailed` | 4 例 owner XOR（uuid 参数 ID），**无 stdout 存档** | ❌ 事后复跑通过 |
| 8/14 17:17 | `backend-test-20260814-171728.log` | 全量 | ✅ 729 passed, 92 skipped |
| 8/14 15:52 | lastfailed（已被 17:33 覆盖） | 4 例 owner XOR，无 stdout | ❌ 事后复跑通过 |
| 8/12 06:17 | `.qoder/worktrees/production-ha-task0/backend/.pytest_cache/.../lastfailed` | **6 例**（当时 parametrize 是 3 组参数，后被改成 2 组） | ❌ 事后复跑通过 |
| 8/10 06:32 | `/tmp/check_1_pytest.log` | make check 旧基线 | ✅ 460 passed / 90 skipped |

**skip 明细（已核实 `/tmp/skip-reasons.log`）**：92 skipped = 82 个设计跳过
（Linux Runtime gate retired，native-full 是唯一 Gate）+ 10 个缺 `MINGLI_TEST_POSTGRES_URL`
的 reading worker 并发测试。

## 二、失败用例整理

**唯一失败过的测试**：
`backend/tests/test_reading_migrations.py::test_owner_xor_is_enforced_by_the_migrated_database`

**断言语义**：对 `alembic upgrade head` 后的全新 SQLite 库（每用例独立 `tmp_path`），
向 `subject_profiles` / `reading_roots` 插入非法行，必须抛 `IntegrityError`：
1. `owner_user_id` 与 `owner_guest_session_id` 同时为 NULL；
2. 两者同时非空。

即校验 owner XOR CHECK 约束（`ck_subject_profiles_owner_exactly_one`、
`ck_reading_roots_owner_exactly_one`），由迁移 `0003_reading_integrity_constraints.py`
通过 `batch_alter_table` + `create_check_constraint` 添加（已核实：全部 32 个迁移中
**只有 0003 用 batch 重建这两张表**）。

### 失败模式推断（v3 收窄）

- **偏向 A：`DID NOT RAISE IntegrityError`（约束当轮没建出来）**。
  依据：三轮失败都只有 owner XOR 用例失败，而同文件中同样调用
  `command.upgrade(..., "head")` 的其他用例（phase-two 表结构检查、idempotency owner XOR 等）
  不在 lastfailed 里 → 迁移链整体能跑、env.py import 正常、文件收集正常，
  只是这两张表的 CHECK 约束在那一轮不存在。最符合"收集时刻 0003 处于编辑中间态
  （约束块尚未保存/被临时移除/重构中）"。
- **B（整文件 import/收集崩掉）基本排除**：若 env.py 批量 import 撞上坏模块，
  同文件所有 `upgraded_engine` 用例都会 ERROR，不会只挂 4 例。
- 无 traceback，A 仍是推断；**下次复现时带日志跑一次即可一锤定音**（见 P0）。

### 两个已被源码证实的"排查基础设施"缺陷

1. **uuid4 参数 ID**（`tests/test_reading_migrations.py:161-165`）：
   参数值在模块级用 `uuid4().hex` 生成 → 每次收集用例 ID 都变。
2. **lastfailed 文物化机制**（已核实 `.venv/.../pytest/cacheprovider.py`）：
   - `LFPlugin.__init__` 从缓存载入旧 lastfailed；
   - `pytest_runtest_logreport` 只对**精确匹配且通过**的 nodeid 执行 `pop`，失败才 `set`；
   - uuid4 ID 永远不会被再次执行 → 旧条目**永不清除**，`pytest --lf` 也永远选不中它们。
   - **现场复现**：17:53 全绿复跑结束后，lastfailed 仍停留在 17:33:15 的 4 条旧记录
     （mtime 未变）——绿跑也洗不掉它。
3. **nodeids 缓存已被污染**：当前 `cache/nodeids` 有 1391 条（现行套件仅 730 例），
   含约 250 代历史 uuid 参数条目，还有一条两个 nodeid 首尾拼接的**损坏条目**
   （疑似并发运行/写入竞争留下的痕迹）。该缓存已无参考价值。

## 三、时间线

- **8/12 06:17**：worktree `production-ha-task0` 中 6 例失败（当时 parametrize 为 3 组参数；无日志）。
- **8/14 15:09–16:14**：`backend/app/**`、`backend/tests/**`、`tests/contract/**` 连续编辑；
  **15:52** 失败 4 例（无日志）。
- **8/14 17:17**：全量复跑全绿（729 passed）。
- **8/14 17:32:00**：`adapters/model.py`、`adapters/runtime.py`、`readings/output_contracts.py`、
  `readings/service.py` 被保存；**17:33:11**：`tests/test_readings_api.py` 被保存
  （套件用例数 729→730 与此吻合）；**17:33:15**：缓存写入 4 例失败——
  该轮运行恰好横跨上述保存时刻。
- **8/14 17:36 / 17:37**：单文件与全量复跑均绿。
- **8/14 17:53**：本次核验全量复跑全绿（730 passed / 92 skipped）。
  且绿跑未能清除 17:33 的 lastfailed（文物化机制现场复现）。

## 四、排查与改进建议（按优先级）

### P0：修排查基础设施（本轮失败无法诊断的直接原因）

1. **Makefile 固化日志**（当前 `backend-test` 目标不带 tee，是三轮失败零日志的直接原因）。
   改为：
   ```make
   SHELL := /bin/bash
   backend-test:
   	set -o pipefail; uv run --directory backend pytest tests ../tests/contract -q --tb=short 2>&1 | tee backend-test-$$(date +%Y%m%d-%H%M%S).log
   ```
   （`pipefail` 必须有，否则 tee 管道会吞掉 pytest 退出码。）
2. **修掉 uuid4 参数 ID**（`tests/test_reading_migrations.py:161-165`），
   改成固定值 + 显式 ids：
   ```python
   @pytest.mark.parametrize(
       ("owner_user_id", "owner_guest_session_id"),
       [(None, None), ("owner-user-fixed", "owner-guest-fixed")],
       ids=["both-null", "both-set"],
   )
   ```
   修完后 `pytest --lf` 才能复跑历史失败、lastfailed 才能被绿跑正常清除、跨运行才可对齐。
3. **清掉被污染的缓存**（内容已存档于本报告）：
   ```bash
   rm -rf backend/.pytest_cache .qoder/worktrees/production-ha-task0/backend/.pytest_cache
   ```

### P1：失败处置动作规范

4. **见到失败先带日志复跑一次再下结论**：
   ```bash
   uv run --directory backend pytest tests/test_reading_migrations.py -q --tb=long -vv 2>&1 | tee /tmp/rerun-$(date +%H%M%S).log
   ```
   无 traceback 的失败不做根因结论（本报告第二节 A/B 之辨全靠间接证据，就是因为没日志）。
5. **避免在编辑窗口跑全量**。三轮失败全部命中编辑窗口；若必须跑，先确认编辑器自动保存已停，
   或只跑受影响的单文件。注意 17:33 那轮就是运行横跨了 17:32:00 与 17:33:11 两次保存。
6. **不要并发跑多个 pytest**（共享同一个 `.pytest_cache` 会互相污染；
   nodeids 里的拼接损坏条目疑似即由此产生）。

### P2：防御与基线

7. **alembic batch 重建丢约束风险**：SQLite 下 `batch_alter_table` 重建表可能静默丢 CHECK 约束。
   当前只有 0003 触碰这两张表，但今后任何触碰 `subject_profiles` / `reading_roots` /
   `reading_idempotency_keys` 的 batch 迁移，改完必跑：
   `uv run --directory backend pytest tests/test_reading_migrations.py -q`；
   排查时用 `sqlite3 xxx.sqlite3 ".schema subject_profiles"` 看 `ck_*` 是否还在，
   必要时 `alembic downgrade -1` 二分定位。
8. **尽快固化基线**：工作树当前约 891 个已变更文件、358 个未跟踪文件（含 32 个迁移全部未提交
   ——比 17:41 报告时的规模又大了）。不 commit，下一次瞬态失败依旧无法 diff 回溯。

### P3：清理与补强

9. **消化 10 个可执行 skip**：本机 127.0.0.1:5432 已有 Postgres：
   ```bash
   MINGLI_TEST_POSTGRES_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli" make backend-test
   ```
10. （可选）核验类的一次性复跑统一加 `-p no:cacheprovider`，避免污染共享缓存。

## 五、复现命令

```bash
cd /Volumes/Lexar/code/mingli_web
make backend-test                                   # 全量（含 contract）
uv run --directory backend pytest tests/test_reading_migrations.py -q --tb=long -vv
MINGLI_TEST_POSTGRES_URL="postgresql+asyncpg://mingli:mingli-local@127.0.0.1:5432/mingli" make backend-test
```
